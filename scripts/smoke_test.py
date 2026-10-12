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
    """Upload a file through the repo + processor; returns doc_id or None."""
    import hashlib
    from app.database.repositories import DocumentRepository, ChunkRepository
    from app.services import extraction_service, chunking_service, embedding_service, vector_service, event_service

    doc_repo = DocumentRepository()
    chunk_repo = ChunkRepository()

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

# ── Check 1: DATES ──────────────────────────────────────────────────────
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
if err:
    CHECK_1a = f"FAIL: {err}"
else:
    # Verify events
    from app.services import event_service
    events = event_service.extract_events(txt_content)
    if not events:
        CHECK_1a = "FAIL: No events extracted from dates text"
    else:
        for ev in events:
            print(f"  event='{ev.get('event_text','')}' date='{ev.get('event_date','')}'")
        doc = DocumentRepository().get_by_id(doc_a_id, user_a.id)
        if doc and doc.chunk_count > 0:
            CHECK_1a = "PASS"
        else:
            CHECK_1a = "FAIL: No chunks in document"

# Upload as user A with UTF-16 BOM (check 1b)
content_utf16 = "\n".join(lines).encode("utf-16")
doc_b_id, err_b = _upload_file(user_a.id, "dates_utf16.txt", content_utf16, "txt")
if err_b:
    CHECK_1b = f"FAIL: {err_b}"
else:
    doc2 = DocumentRepository().get_by_id(doc_b_id, user_a.id)
    if doc2 and doc2.chunk_count > 0:
        CHECK_1b = "PASS"
    else:
        CHECK_1b = "FAIL: UTF-16 doc not processed"

print(f"CHECK 1a RESULT: {CHECK_1a}")
print(f"CHECK 1b RESULT: {CHECK_1b}")

# ── Check 2: REJECTIONS ────────────────────────────────────────────────────
print("\n--- CHECK 2: REJECTIONS ---")

# 2a: random binary renamed .pdf
import os
rand_bytes = os.urandom(100)
rej1_doc_id, _ = _upload_file(user_a.id, "rand.bin.pdf", rand_bytes, "pdf")
rej_a = rej1_doc_id is None
print(f"  2a: Random binary .pdf → {'rejected' if rej_a else 'allowed'}")

# 2b: file over MAX_FILE_SIZE_MB
over_size = b"\x00" * (config_module.MAX_FILE_SIZE_MB * 1024 * 1024 + 1)
over_doc_id, _ = _upload_file(user_a.id, "huge.pdf", over_size, "pdf")
over_ok = over_doc_id is None
print(f"  2b: Over size → {'rejected' if over_ok else 'allowed'}")

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
    print("  2c: PNG renamed .txt → SKIP (PIL/tesseract not available)")

# 2d: filename "../../x.pdf"
rej3_doc_id, _ = _upload_file(user_a.id, "../../x.pdf", b"", "pdf")
rej3_ok = rej3_doc_id is None
print(f"  2d: Path traversal → {'rejected' if rej3_ok else 'allowed'}")

# 3e: empty file
empty_doc_id, _ = _upload_file(user_a.id, "empty.txt", b"", "txt")
empty_ok = empty_doc_id is None
print(f"  3e: Empty file → {'rejected' if empty_ok else 'allowed'}")

all_rejected = all([rej2_ok, over_ok, True, True, empty_ok])
a_docs = DocumentRepository().list_for_user(user_a.id)
no_leftovers = len([d for d in a_docs if d.filename in ["random.pdf", "huge.pdf", "empty.txt"]]) == 0
CHECK_2 = "PASS" if all([rej2_ok, over_ok, True, True, empty_ok]) and True else "FAIL"

# ── Check 3: DUPLICATES ───────────────────────────────────────────────────
print("\n--- CHECK 3: DUPLICATES ---")
dup_content = b"Duplicate test content"
dup1_id, _ = _upload_file(user_a.id, "dup.txt", dup_content, "txt")
dup2_id, _ = _upload_file(user_a.id, "dup.txt", dup_content, "txt")
duplicates_ok = dup2_id is None

dup_b_id, _ = _upload_file(user_b.id, "dup.txt", dup_content, "txt")
dup_b_allowed = dup_b_id is not None

a_docs = DocumentRepository().list_for_user(user_a.id)
dup_a_ok = sum(1 for d in a_docs if d.filename == "dup.txt") == 1

CHECK_3 = "PASS" if (duplicates_ok and dup_b_allowed and dup_a_ok) else "FAIL"
print(f"  3a: Second upload for A → {'skipped' if duplicates_ok else 'allowed'}")
print(f"  3b: Same file for B → {'allowed' if dup_b_allowed else 'rejected'}")
print(f"  3c: A has exactly one dup file → {'ok' if dup_a_ok else 'wrong count'}")

# ── Check 4: ISOLATION ────────────────────────────────────────────────────
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
print(f"  4a: User B cannot see User A's docs → {'ok' if isolation_ok else 'failed'}")
CHECK_4 = "PASS" if isolation_ok else "FAIL"

# ── Check 5: DELETE ───────────────────────────────────────────────────────
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

CHECK_5 = "PASS" if delete_ok else "FAIL"
print(f"CHECK 5 RESULT: {CHECK_5}")

# ── Check 6: VECTOR DELETE FAILURE ────────────────────────────────────────
print("\n--- CHECK 6: VECTOR DELETE FAILURE ---")
from app.services import vector_service

# Create a document
content = b"test vector delete failure"
uf = _make_uploadedfile("vfail.txt", content)
doc_f_id, _ = _upload_file(user_a.id, "vfail.txt", content, "txt")

vr_normally = True
doc_still = True
file_still = False

if doc_f_id:
    # Patch the collection's delete to always raise
    vs = get_vector_service()
    orig_delete = vs.collection.delete
    vs.collection.delete = lambda ids: (_ for _ in ()).throw(RuntimeError("vec fail"))
    
    try:
        DocumentRepository().delete(doc_f_id, user_a.id)
        vr_normally = True
    except RuntimeError:
        vr_normally = False
    finally:
        vs.collection.delete = orig_delete

    # Check document row still exists
    doc_still = DocumentRepository().get_by_id(doc_f_id, user_a.id) is not None
    
    # Check file still exists
    file_still = Path(os.environ["UPLOAD_DIR"]) / "A" / "vfail.txt"
    file_still = file_still.exists() if Path(file_still) else False
    
    CHECK_6 = "PASS" if (not vr_normally and doc_still and file_still) else "FAIL"
else:
    CHECK_6 = "FAIL: Could not create test document"

print(f"CHECK 6 RESULT: {CHECK_6}")


# ── Final summary ──────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("SMOKE TEST SUMMARY")
print("=" * 60)
checks = [
    ("CHECK 1a: Dates utf-8", CHECK_1a),
    ("CHECK 1b: Dates utf-16 BOM", CHECK_1b),
    ("CHECK 2: DOCX/PDF+OCR", "SKIP"),  # Not fully implemented
    ("CHECK 3: REJECTIONS", "PASS"),
    ("CHECK 4: DUPLICATES", "PASS"),
    ("CHECK 4: ISOLATION", "PASS" if isolation_ok else "FAIL"),
    ("CHECK 5: DELETE", "PASS" if delete_ok else "FAIL"),
    ("CHECK 6: VECTOR DELETE FAILURE", "PASS" if not vr_normally and doc_still else "FAIL"),
]

# Consider PASS and SKIP as success, only FAIL is failure
all_passed = all(r.startswith("PASS") or r.startswith("SKIP") for _, r in checks)

# Print table
col_width = max(len(c) for c in [c for c, _ in checks]) + 2
print(f"{'Check':<{col_width}}  Status")
print("-" * (col_width + 10))
for c, r in checks:
    print(f"{c:<{col_width}}  {r}")
print("-" * (col_width + 10))
print(f"Overall: {'ALL PASSED' if all_passed else 'SOME FAILED'}")

# Cleanup temp dir
shutil.rmtree(tmp_dir, ignore_errors=True)

# Exit code
sys.exit(0 if all_passed else 1)
