#!/usr/bin/env python3
"""Repair script for MemoryNest database consistency.

Checks for and optionally fixes:
- ChromaDB vectors with no corresponding SQLite chunk
- SQLite chunks with no corresponding document
- Uploaded files with no corresponding document
- Documents with no chunks (orphaned documents)

Safety: --fix only applies changes when also given --yes, so the database
path is always shown and confirmed before anything is modified.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.database import get_connection
from app.services import vector_service
from app.utils import config

# Default DB path from config (env/.env aware), resolved at script start.
DEFAULT_DB_PATH: Path = config.DB_PATH


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repair MemoryNest database consistency")
    parser.add_argument("--fix", action="store_true", help="Actually fix issues (default: dry run)")
    parser.add_argument("--yes", action="store_true",
                        help="Confirm that the shown database path is correct (required with --fix)")
    parser.add_argument("--db-path", type=Path, help="Path to SQLite database (default: from config)")
    return parser.parse_args()


def get_db_path(args: argparse.Namespace) -> Path:
    """Get database path from args or the configured default."""
    if args.db_path:
        return args.db_path
    return DEFAULT_DB_PATH


def check_orphan_vectors(db_path: Path, fix: bool = False) -> tuple[int, int]:
    """Check for ChromaDB vectors with no corresponding SQLite chunk."""
    print("\n=== Checking for orphan ChromaDB vectors ===")

    # Get all chunk chroma_ids from SQLite
    conn = get_connection(db_path)
    try:
        rows = conn.execute("SELECT chroma_id FROM document_chunks").fetchall()
        sqlite_chroma_ids = {row["chroma_id"] for row in rows}
    finally:
        conn.close()

    # Get all vectors from ChromaDB
    vs = vector_service.get_vector_service()
    all_chroma = vs.collection.get(include=[])
    chroma_ids = set(all_chroma["ids"])

    orphan_ids = chroma_ids - sqlite_chroma_ids
    print(f"  ChromaDB vectors: {len(chroma_ids)}")
    print(f"  SQLite chunks: {len(sqlite_chroma_ids)}")
    print(f"  Orphan vectors: {len(orphan_ids)}")

    if fix and orphan_ids:
        vs.collection.delete(ids=list(orphan_ids))
        print(f"  Deleted {len(orphan_ids)} orphan vectors")

    return len(chroma_ids), len(orphan_ids)


def check_chunks_without_document(db_path: Path, fix: bool = False) -> tuple[int, int]:
    """Check for SQLite chunks with no corresponding document."""
    print("\n=== Checking for chunks without document ===")

    conn = get_connection(db_path)
    try:
        # Find chunks where document doesn't exist
        rows = conn.execute("""
            SELECT c.id, c.chroma_id, c.document_id
            FROM document_chunks c
            LEFT JOIN documents d ON c.document_id = d.id
            WHERE d.id IS NULL
        """).fetchall()

        orphan_chunks = rows
        total_chunks = conn.execute("SELECT COUNT(*) FROM document_chunks").fetchone()[0]
        print(f"  Total chunks: {total_chunks}")
        print(f"  Chunks without document: {len(orphan_chunks)}")

        if fix and orphan_chunks:
            chroma_ids = [row["chroma_id"] for row in orphan_chunks]
            # Delete from ChromaDB
            vs = vector_service.get_vector_service()
            vs.collection.delete(ids=chroma_ids)
            # Delete from SQLite
            conn.execute("DELETE FROM document_chunks WHERE document_id NOT IN (SELECT id FROM documents)")
            conn.commit()
            print(f"  Deleted {len(orphan_chunks)} orphan chunks")

    finally:
        conn.close()

    total_chunks = 0
    conn = get_connection(db_path)
    try:
        total_chunks = conn.execute("SELECT COUNT(*) FROM document_chunks").fetchone()[0]
    finally:
        conn.close()

    return total_chunks, len(orphan_chunks)


def check_files_without_document(db_path: Path, fix: bool = False) -> tuple[int, int]:
    """Check for uploaded files with no corresponding document."""
    print("\n=== Checking for files without document ===")

    # Get all document stored_paths
    conn = get_connection(db_path)
    try:
        rows = conn.execute("SELECT stored_path FROM documents").fetchall()
        db_files = {row["stored_path"] for row in rows}
    finally:
        conn.close()

    # Scan upload directory
    upload_files = set()
    upload_dir = config.UPLOAD_DIR
    if upload_dir.is_dir():
        for user_dir in upload_dir.iterdir():
            if user_dir.is_dir():
                for file_path in user_dir.iterdir():
                    if file_path.is_file():
                        upload_files.add(str(file_path))

    orphan_files = upload_files - db_files
    print(f"  Files in upload dir: {len(upload_files)}")
    print(f"  Files in database: {len(db_files)}")
    print(f"  Orphan files: {len(orphan_files)}")

    if fix and orphan_files:
        deleted = 0
        for file_path in orphan_files:
            try:
                Path(file_path).unlink()
                deleted += 1
            except OSError as e:
                print(f"  Failed to delete {file_path}: {e}")
        # Try to remove empty user directories
        for user_dir in upload_dir.iterdir():
            if user_dir.is_dir() and not any(user_dir.iterdir()):
                try:
                    user_dir.rmdir()
                except OSError:
                    pass
        print(f"  Deleted {deleted} orphan files")

    return len(upload_files), len(orphan_files)


def check_documents_without_chunks(db_path: Path, fix: bool = False) -> tuple[int, int]:
    """Check for documents with no chunks."""
    print("\n=== Checking for documents without chunks ===")

    conn = get_connection(db_path)
    try:
        rows = conn.execute("""
            SELECT d.id, d.filename, d.chunk_count
            FROM documents d
            LEFT JOIN document_chunks c ON d.id = c.document_id
            WHERE c.id IS NULL AND d.status = 'ready'
        """).fetchall()

        orphan_docs = rows
        total_ready = conn.execute("SELECT COUNT(*) FROM documents WHERE status='ready'").fetchone()[0]
        print(f"  Ready documents: {total_ready}")
        print(f"  Documents without chunks: {len(orphan_docs)}")

        if fix and orphan_docs:
            for row in orphan_docs:
                doc_id = row["id"]
                conn.execute("UPDATE documents SET status = 'error', error_message = 'No chunks found - marked by repair' WHERE id = ?", (doc_id,))
            conn.commit()
            print(f"  Marked {len(orphan_docs)} documents as error")

    finally:
        conn.close()

    return total_ready, len(orphan_docs)


def run_checks(db_path: Path, fix: bool = False) -> int:
    """Run all consistency checks; return the total number of issues found."""
    total_issues = 0
    _, n = check_orphan_vectors(db_path, fix=fix)
    total_issues += n
    _, n = check_chunks_without_document(db_path, fix=fix)
    total_issues += n
    _, n = check_files_without_document(db_path, fix=fix)
    total_issues += n
    _, n = check_documents_without_chunks(db_path, fix=fix)
    total_issues += n
    return total_issues


def main() -> int:
    args = parse_args()

    # Always show the database path that will be read/modified.
    db_path = get_db_path(args)

    print("MemoryNest Database Consistency Check")
    print("=" * 50)
    print(f"Database: {db_path}")

    if args.fix and not args.yes:
        print("Refusing to modify the database without confirmation.")
        print(f"Review the database path above, then re-run with: --fix --yes")
        return 2

    if args.fix:
        print("MODE: FIX (will modify data)")
    else:
        print("MODE: DRY RUN (no changes)")

    total_issues = run_checks(db_path, fix=args.fix)

    print("\n" + "=" * 50)
    print(f"Total issues found: {total_issues}")

    if not args.fix:
        if total_issues:
            print("Run with --fix --yes to fix issues.")
        return 0 if total_issues == 0 else 1

    # After fixing, re-run the checks to see what remains.
    remaining = run_checks(db_path, fix=False)
    print(f"Issues remaining after fix: {remaining}")
    return 0 if remaining == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
