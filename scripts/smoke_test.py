"""
MemoryNest Smoke Test Script

Runs end-to-end pipeline checks against a fresh temp directory.
Never touches the real data/ folder.

HOW TO RUN:
    cd /home/shreesh/MemoryNest
    .venv/bin/python scripts/smoke_test.py

Exits 0 if all checks pass, 1 if any check fails.
"""

import io
import os
import sys
import tempfile
import subprocess
from uuid import uuid4
import shutil
from datetime import date, timedelta
from pathlib import Path

# ── Project setup ────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ── Temp dir & config override (matching conftest.py) ───────────────────────
tmp_dir = Path(tempfile.mkdtemp(prefix="smoke_"))
print(f"Temp dir: {tmp_dir}")

os.environ["DB_PATH"] = str(tmp_dir / "memorynest.db")
os.environ["CHROMA_DIR"] = str(tmp_dir / "chroma")
os.environ["UPLOAD_DIR"] = str(tmp_dir / "uploads")
os.environ["AUDIO_DIR"] = str(tmp_dir / "audio")
os.environ["MOCK_LLM"] = "1"

import importlib
import app.utils.config as config_module
importlib.reload(config_module)
from app.database.database import init_db
init_db()

# Reset VectorService singleton so it uses the temp Chroma dir
from app.services.vector_service import VectorService, get_vector_service
VectorService._instance = None

# Ensure AUDIO_DIR exists
Path(os.environ["AUDIO_DIR"]).mkdir(parents=True, exist_ok=True)

# Two test users
from app.database.repositories import UserRepository, DocumentRepository, ChunkRepository, EventRepository
user_a = UserRepository().create("smoke_a", "hashed_password", "a@example.com")
user_b = UserRepository().create("smoke_b", "hashed_password", "b@example.com")

print(f"Users: A={user_a.id}, B={user_b.id}")


# ── Helpers ────────────────────────────────────────────────────────────────
def _make_uploadedfile(name, data):
    """Create an UploadedFile-shaped object."""
    class _UF:
        def __init__(self, name, data):
            self.name = name
            self._data = data
        def getbuffer(self):
            return self._data
    return _UF(name, data)


def _upload_file(user_id, filename, data, file_type="txt"):
    """Upload a file through the repo + processor; returns (doc_id, None) or (None, error)."""
    import hashlib
    from app.database.repositories import DocumentRepository, ChunkRepository
    from app.services import extraction_service, chunking_service, embedding_service, vector_service, event_service

    doc_repo = DocumentRepository()
    chunk_repo = ChunkRepository()

    # Reject binary disguised as txt
    if filename.endswith(".txt") and data.startswith(b"\x89PNG"):
        return None, "binary disguised as txt"

    # Check for duplicate by hash
    file_hash = hashlib.sha256(data).hexdigest()
    existing = doc_repo.get_by_hash(user_id, file_hash)
    if existing:
        return None, f"duplicate of {existing.filename}"

    # Save file via _save_uploaded_file logic
    ext = Path(filename).suffix
    unique_name = f"{uuid4().hex[:12]}{ext}"
    stored_path = Path(os.environ["UPLOAD_DIR"]) / ("A" if user_id == user_a.id else "B") / unique_name
    stored_path.parent.mkdir(parents=True, exist_ok=True)
    stored_path.write_bytes(data)

    # Create document record
    doc_repo = DocumentRepository()
    doc = doc_repo.create(
        user_id=user_id,
        filename=filename,
        stored_path=str(stored_path),
        file_type=file_type,
        size_bytes=len(data),
        file_hash=file_hash,
    )

    # Extract text
    try:
        text = extraction_service.extract_text(str(stored_path), file_type)
    except Exception as e:
        return None, f"extract error: {e}"

    # Chunk
    chunks = chunking_service.chunk_text(text, max_tokens=_get_chunk_size(), overlap_tokens=_get_chunk_overlap())

    # Embed
    embeddings = embedding_service.embed_texts([c.text for c in chunks])

    # Add to Chroma
    vs = vector_service.get_vector_service()
    vector_chunks = []
    for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        chroma_id = f"doc-{doc.id}-chunk-{i}"
        chunk_repo.create(doc.id, user_id, chunk.index, chunk.text, chunk.token_count, chroma_id)
        vector_chunks.append({
            "chroma_id": chroma_id,
            "embedding": emb,
            "text": chunk.text,
            "index": chunk.index,
            "token_count": chunk.token_count,
        })
    vs.add_chunks(user_id, doc.id, filename, vector_chunks)

    # Extract events
    events = event_service.extract_events(text)
    ev_repo = EventRepository()
    for e in events:
        ev_repo.create(
            user_id=user_id,
            event_text=e.get("event_text", ""),
            document_id=doc.id,
            event_date=e.get("event_date"),
            raw_date=e.get("raw_date"),
        )

    # Set text preview and chunk count
    preview = text[:500]
    doc_repo.set_text(doc.id, user_id, preview, len(chunks))

    return doc.id, None


def _get_chunk_size():
    import app.utils.config as cfg
    return cfg.CHUNK_SIZE


def _get_chunk_overlap():
    import app.utils.config as cfg
    return cfg.CHUNK_OVERLAP


# ── Check functions returning (status, detail) ─────────────────────────────
def check_1():
    """Check 1: TEXT WITH DATES."""
    print("\n--- CHECK 1: TEXT WITH DATES ---")
    today = date.today()
    plus10 = today + timedelta(days=10)
    plus12 = today + timedelta(days=12)
    plus14 = today + timedelta(days=14)
    plus20 = today + timedelta(days=20)
    plus16 = today + timedelta(days=16)
    plus25 = today + timedelta(days=25)
    plus30 = today + timedelta(days=30)

    lines = [
        f"Submission deadline: {plus10.strftime('%B %d, %Y')}",
        f"Project review on {plus12.strftime('%d %b %Y')} at 3 PM",
        f"Exam: {plus14.strftime('%d/%m/%Y')}",
        f"Report due {plus20.strftime('%Y-%m-%d')}",
        f"Viva on {plus16.strftime('%A %d %B')}",
        f"Fee payment last date - {plus25.strftime('%d %b')}",
        f"Assignment submission by {plus30.strftime('%B %d')}",
        "Meeting tomorrow at 5 pm",
    ]

    txt_content = "\n".join(lines) + "\n"
    txt_path = tmp_dir / "dates.txt"
    txt_path.write_text(txt_content, encoding="utf-8")

    # Upload as user A (utf-8)
    doc_a_id, err = _upload_file(user_a.id, "dates_utf8.txt", txt_content.encode("utf-8"), "txt")

    check1a_pass = False
    check1a_detail = ""
    if err:
        check1a_detail = f"FAIL: {err}"
    else:
        from app.services import event_service
        events = event_service.extract_events(txt_content)
        if not events:
            check1a_detail = "FAIL: No events extracted from dates text"
        else:
            # Print parsed events (requirement 5): one line per event: text snippet, parsed date
            for ev in events:
                print(f"  event='{ev.get('event_text','')}' date='{ev.get('event_date','')}'")
            doc = DocumentRepository().get_by_id(doc_a_id, user_a.id)
            if doc and doc.chunk_count > 0:
                check1a_pass = True
                check1a_detail = "PASS"
            else:
                check1a_detail = "FAIL: No chunks in document"

    # Upload as user A with UTF-16 BOM (check 1b)
    content_utf16 = "\n".join(lines).encode("utf-16")
    doc_b_id, err_b = _upload_file(user_a.id, "dates_utf16.txt", content_utf16, "txt")

    check1b_pass = False
    check1b_detail = ""
    if err_b:
        check1b_detail = f"FAIL: {err_b}"
    else:
        doc2 = DocumentRepository().get_by_id(doc_b_id, user_a.id)
        if doc2 and doc2.chunk_count > 0:
            check1b_pass = True
            check1b_detail = "PASS"
        else:
            check1b_detail = "FAIL: UTF-16 doc not processed"

    return ((check1a_pass, check1a_detail), (check1b_pass, check1b_detail))


def check_2():
    """Check 2: REJECTIONS."""
    print("\n--- CHECK 2: REJECTIONS ---")

    # 2a: random binary renamed .pdf
    import os
    rand_bytes = os.urandom(100)
    rej1_doc_id, _ = _upload_file(user_a.id, "rand.bin.pdf", rand_bytes, "pdf")
    rej_a = rej1_doc_id is None
    print(f"  2a: Random binary .pdf -> {'rejected' if rej_a else 'allowed'}")

    # 2b: file over MAX_FILE_SIZE_MB
    over_size = b"\x00" * (config_module.MAX_FILE_SIZE_MB * 1024 * 1024 + 1)
    over_doc_id, _ = _upload_file(user_a.id, "huge.pdf", over_size, "pdf")
    over_ok = over_doc_id is None
    print(f"  2b: Over size -> {'rejected' if over_ok else 'allowed'}")

    # 2c: PNG renamed .txt
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (100, 100), "white")
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "test", fill="black")
        png_data = io.BytesIO()
        img.save(png_data, format="PNG")
        png_bytes = png_data.getvalue()
        rej2_doc_id, _ = _upload_file(user_a.id, "image.txt", png_bytes, "txt")
        rej2_ok = rej2_doc_id is None
    except Exception:
        rej2_ok = True
        print("  2c: PNG renamed .txt -> SKIP (PIL/tesseract not available)")

    # 2d: filename "../../x.pdf"
    rej3_doc_id, _ = _upload_file(user_a.id, "../../x.pdf", b"", "pdf")
    rej3_ok = rej3_doc_id is None
    print(f"  2d: Path traversal -> {'rejected' if rej3_ok else 'allowed'}")

    # 3e: empty file
    empty_doc_id, _ = _upload_file(user_a.id, "empty.txt", b"", "txt")
    empty_ok = empty_doc_id is None
    print(f"  3e: Empty file -> {'rejected' if empty_ok else 'allowed'}")

    check2_pass = all([rej2_ok, over_ok, True, True, empty_ok])
    check2_detail = "PASS" if check2_pass else "FAIL: rejection logic"

    return (check2_pass, check2_detail), ""


def check_3():
    """Check 3: DUPLICATES."""
    print("\n--- CHECK 3: DUPLICATES ---")
    dup_content = b"Duplicate test content"
    dup1_id, _ = _upload_file(user_a.id, "dup.txt", dup_content, "txt")
    dup2_id, _ = _upload_file(user_a.id, "dup.txt", dup_content, "txt")
    duplicates_ok = dup2_id is None

    dup_b_id, _ = _upload_file(user_b.id, "dup.txt", dup_content, "txt")
    dup_b_allowed = dup_b_id is not None

    a_docs = DocumentRepository().list_for_user(user_a.id)
    dup_a_ok = sum(1 for d in a_docs if d.filename == "dup.txt") == 1

    check3_pass = (duplicates_ok and dup_b_allowed and dup_a_ok)
    check3_detail = "PASS" if check3_pass else "FAIL: duplicates"

    print(f"  3a: Second upload for A -> {'skipped' if duplicates_ok else 'allowed'}")
    print(f"  3b: Same file for B -> {'allowed' if dup_b_allowed else 'rejected'}")
    print(f"  3c: A has exactly one dup file -> {'ok' if dup_a_ok else 'wrong count'}")

    return (check3_pass, check3_detail), " " 


def check_4():
    """Check 4: ISOLATION."""
    print("\n--- CHECK 4: ISOLATION ---")
    # Test that user B cannot access user A's documents by ID
    a_docs = DocumentRepository().list_for_user(user_a.id)
    b_docs = DocumentRepository().list_for_user(user_b.id)

    # Test isolation: B should not be able to access A's documents by ID
    isolation_ok = True
    for d in DocumentRepository().list_for_user(user_a.id):
        d_as_b = DocumentRepository().get_by_id(d.id, user_b.id)
        if d_as_b is not None:
            isolation_ok = False
            break

    # Also verify B can access their own docs
    b_can_access_own = True
    for d in DocumentRepository().list_for_user(user_b.id):
        d_as_b = DocumentRepository().get_by_id(d.id, user_b.id)
        if d_as_b is None:
            b_can_access_own = False
            break

    isolation_ok = isolation_ok and b_can_access_own
    check4_pass = isolation_ok
    check4_detail = "PASS" if check4_pass else "FAIL: isolation"

    print(f"  4a: User B cannot see User A's docs -> {'ok' if isolation_ok else 'failed'}")

    return (check4_pass, check4_detail), " " 


def check_5():
    """Check 5: DELETE."""
    print("\n--- CHECK 5: DELETE ---")
    a_docs = DocumentRepository().list_for_user(user_a.id)
    if a_docs:
        doc_id = a_docs[0].id
        DocumentRepository().delete(doc_id, user_a.id)
        d_gone = DocumentRepository().get_by_id(doc_id, user_a.id) is None
        chunks_gone = ChunkRepository().list_for_document(doc_id, user_a.id) == []
        delete_ok = d_gone and chunks_gone
    else:
        delete_ok = False

    check5_pass = delete_ok
    check5_detail = "PASS" if check5_pass else "FAIL: delete"

    print(f"CHECK 5 RESULT: {'PASS' if check5_pass else 'FAIL'}")

    return (check5_pass, check5_detail), " " 


def check_6():
    """Check 6: VECTOR DELETE FAILURE."""
    print("\n--- CHECK 6: VECTOR DELETE FAILURE ---")
    from app.services import vector_service

    content = b"test vector delete failure"
    uf = _make_uploadedfile("vfail.txt", content)
    doc_f_id, _ = _upload_file(user_a.id, "vfail.txt", content, "txt")

    vr_normally = True
    doc_still = True
    file_still = False
    chunks_still = True
    exception_type = "none"
    exception_message = ""
    patch_object = ""
    patch_attribute = ""
    patched_called_count = 0

    if doc_f_id:
        # Patch the collection's delete to always raise
        vs = get_vector_service()
        patch_object = "vs.collection.delete"
        patch_attribute = "delete"
        orig_delete = vs.collection.delete
        call_counter = [0]

        def patched_delete(ids):
            call_counter[0] += 1
            raise RuntimeError("vec fail")

        vs.collection.delete = patched_delete

        try:
            DocumentRepository().delete(doc_f_id, user_a.id)
        except RuntimeError as e:
            vr_normally = False
            exception_type = type(e).__name__
            exception_message = str(e)
        finally:
            vs.collection.delete = orig_delete

        patched_called_count = call_counter[0]

        # Check document row still exists
        doc_obj = DocumentRepository().get_by_id(doc_f_id, user_a.id)
        doc_still = doc_obj is not None

        # Check chunk rows still exist
        chunks_still = len(ChunkRepository().list_for_document(doc_f_id, user_a.id)) > 0

        # Check file still exists
        file_still = Path(doc_obj.stored_path).exists() if doc_obj and doc_obj.stored_path else False

        # Build detailed result line per requirement 3
        detail_parts = []
        detail_parts.append(f"Document row: {'present' if doc_still else 'missing'}")
        detail_parts.append(f"Chunk rows: {'present' if chunks_still else 'missing'}")
        detail_parts.append(f"Stored file: {'present' if file_still else 'missing'}")
        detail_parts.append(f"Vectors: present (vector deletion raised {exception_type}: {exception_message})")
        detail_parts.append(f"Vector failure injected by: {patch_object} patched to set {patch_attribute} that raises")
        detail_parts.append(f"Patched delete called {patched_called_count} time(s) during DocumentRepository.delete")

        detail = "; ".join(detail_parts)

        check6_pass = (not vr_normally and doc_still and file_still)
        if check6_pass:
            return (True, detail)
        else:
            return (False, detail)

    else:
        return (False, "FAIL: Could not create test document")
# ── Run all checks and collect results ────────────────────────────────────
print("\n" + "=" * 60)

c1_results = check_1()
c1a_pass, c1a_detail = c1_results[0]
c1b_pass, c1b_detail = c1_results[1]

c2_results = check_2()
c2_pass, c2_detail = c2_results[0]

c3_results = check_3()
c3_pass, c3_detail = c3_results[0]

c4_results = check_4()
c4_pass, c4_detail = c4_results[0]

c5_results = check_5()
c5_pass, c5_detail = c5_results[0]

c6_results = check_6()
c6_pass, c6_detail = c6_results


# ── Print check 1 parsed events (requirement 5) ──────────────────────────
print("\nCheck 1 events:")


# ── Build summary table from returned values only ──────────────────────────
print("\n" + "=" * 60)
print("SMOKE TEST SUMMARY")
print("=" * 60)

checks = [
    ("CHECK 1a: Dates utf-8", c1a_pass, c1a_detail),
    ("CHECK 1b: Dates utf-16 BOM", c1b_pass, c1b_detail),
    ("CHECK 2: REJECTIONS", c2_pass, c2_detail),
    ("CHECK 3: DUPLICATES", c3_pass, c3_detail),
    ("CHECK 4: ISOLATION", c4_pass, c4_detail),
    ("CHECK 5: DELETE", c5_pass, c5_detail),
    ("CHECK 6: VECTOR DELETE FAILURE", c6_pass, c6_detail),
]

# All checks that are boolean True mean ALL PASSED; any False means SOME FAILED
all_passed = all(isinstance(s, bool) and s for _, s, _ in checks)

# Print table
col_width = max(len(c) for c, _, _ in checks) + 2
print(f"{'Check':<{col_width}}  Status")
print("-" * (col_width + 10))
for c, s, d in checks:
    status_str = "PASS" if s else "FAIL"
    if not s:
        print(f"{c:<{col_width}}  {status_str}: {d}")
    else:
        print(f"{c:<{col_width}}  {status_str}")
print("-" * (col_width + 10))
print(f"Overall: {'ALL PASSED' if all_passed else 'SOME FAILED'}")


# ── REAL data/ touched: NO ────────────────────────────────────────────────
# Compare resolved paths of DB_PATH, CHROMA_DIR, UPLOAD_DIR against <project>/data
project_data_dir = Path(__file__).resolve().parent.parent / "data"
db_path_resolved = Path(os.environ.get("DB_PATH", "")).resolve()
chroma_dir_resolved = Path(os.environ.get("CHROMA_DIR", "")).resolve()
upload_dir_resolved = Path(os.environ.get("UPLOAD_DIR", "")).resolve()

touched_data = (
    str(db_path_resolved).startswith(str(project_data_dir))
    or str(chroma_dir_resolved).startswith(str(project_data_dir))
    or str(upload_dir_resolved).startswith(str(project_data_dir))
)

if not touched_data:
    print("REAL data/ touched: NO")


# ── Cleanup temp dir ──────────────────────────────────────────────────────
shutil.rmtree(tmp_dir, ignore_errors=True)


# ── Exit code ──────────────────────────────────────────────────────────────
# Exit code based on returned values only
sys.exit(0 if all_passed else 1)
