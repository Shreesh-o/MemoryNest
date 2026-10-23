#!/usr/bin/env python3
"""Rebuild document links for all users.

This script rebuilds the Document Map for all users in the database.
It is safe to run repeatedly and can be run from the project root with
the virtual environment activated.

Usage:
    python scripts/rebuild_links.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.database.database import get_connection
from app.database.repositories import UserRepository
from app.services.link_service import rebuild_links


def main():
    conn = get_connection()
    try:
        user_repo = UserRepository()
        users = user_repo.list_all()

        if not users:
            print("No users found in database.")
            return 0

        total_edges = 0
        total_docs = 0

        for user in users:
            print(f"Rebuilding links for user {user.id} ({user.username})...")
            try:
                links = rebuild_links(user.id)
                # Count unique documents involved
                doc_ids = set()
                for link in links:
                    doc_ids.add(link["doc_a"])
                    doc_ids.add(link["doc_b"])
                print(f"  -> {len(doc_ids)} documents, {len(links)} edges")
                total_docs += len(doc_ids)
                total_edges += len(links)
            except Exception as e:
                print(f"  -> ERROR: {e}")

        print(f"\nTotal: {total_docs} documents, {total_edges} edges across {len(users)} users")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())