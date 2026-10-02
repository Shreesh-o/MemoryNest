# MemoryNest — READ-ONLY AUDIT REPORT

**Date:** 2026-10-02 · **Repo:** /home/shreesh/MemoryNest (branch `master`, HEAD `24c2a38`) · **Mode:** read-only

**Rule applied:** every claim below carries evidence (command output, `file:line`, or test name).
Anything not provable is marked **UNVERIFIED**. The word "works" is never used without evidence.

## data/ protection — mtime before/after (READ-ONLY GUARANTEE)

Recorded with `stat -c '%n | mtime=%y | size=%s'` at audit start and audit end:

```
BEFORE (saved /tmp/opencode/audit_data_mtime_before.txt)      AFTER (/tmp/opencode/audit_data_mtime_after.txt)
data              mtime=2026-10-01 15:27:37.916150959 +0530  data              mtime=2026-10-01 15:27:37.916150959 +0530  size=132
data/memorynest.db mtime=2026-10-01 15:27:37.909151452 +0530 data/memorynest.db mtime=2026-10-01 15:27:37.909151452 +0530  size=4034560
data/uploads      mtime=2026-10-01 14:24:55.765673542 +0530  data/uploads      mtime=2026-10-01 14:24:55.765673542 +0530  size=8568
data/chroma       mtime=2026-10-01 20:13:17.490000037 +0530  data/chroma       mtime=2026-10-01 20:13:17.490000037 +0530  size=100

diff before after → IDENTICAL: data/ untouched by audit
```

DB reads used `sqlite3 -readonly` / `sqlite3 "file:...?mode=ro"`. All probes ran in `/tmp/audit_p*` temp dirs.

---

# PART 1: History

## 1.1 Full commit log (`git log --oneline`, 23 commits)

```
24c2a38 fix: migration crash on old databases - move file_hash index creation after migration, add migration tests
90b9c8f Task 4: SQLite/ChromaDB consistency - failure cleanup, document delete cleanup, repair script with orphan detection/fix, tests
4a34a65 Task 3: OCR fallback for PDFs - per-page OCR fallback for scanned PDFs, graceful Tesseract missing handling, test with image-only PDF
fd33a62 Task 2: Duplicate detection - file_hash column with migration, SHA-256 hash computation, duplicate detection per user, different users can upload same file
335ebaa Task 1: Upload validation - max file size from .env, magic bytes checking, filename sanitization, user_id subfolder, clear error messages
7bb5e92 cleanup: silence noisy loggers, offline HF model loading, pymupdf import, HF_HUB_OFFLINE env option
7f2a687 fix: ruff F841, logging in exception handlers, event extraction test; fix: bug introduced in 5583f73
ebcae1d fix: upload NameError (user.id -> user_id), add .streamlit/config.toml, add upload regression tests (4 tests)
7ec6aa7 test: add tests for ics_service.py (9 tests passing)
c5063b4 feat: add .ics export buttons to reminders page
0927040 feat: add ics_service.py with icalendar for .ics calendar export
fad961e docs: update README.md and ARCHITECTURE.md for .ics export feature
a69f7e9 docs: update PROGRESS.md with verification results
6b187c9 fix: streamlit sys.path for imports, correct TTS test to mock unavailable case
2f78ba4 Final smoke test passed; PROGRESS.md complete; all 50 tests passing
bc986b6 Dashboard page + README with architecture diagram and Future Scope
5583f73 Pages: upload (with pipeline), documents, history, summaries, reminders - all imports verified
24e34d9 Summary (map-reduce), TTS, event extraction, email services + tests (50 total)
2ab5628 Ollama LLM service with mock fallback (39 tests total)
2e68633 Embedding + Chroma vector service (36 tests total passing)
fc63bc1 Services: extraction (PDF/DOCX/TXT), OCR (Tesseract), chunking (sentence-aware with overlap) - 17 tests passing
2548244 Auth (bcrypt + session state) and Streamlit shell with login/register + nav (AppTest verified)
9c9019d Scaffold project + SQLite schema, repositories, and CRUD tests (8 passing)
```

## 1.2 `git status` (working tree is DIRTY)

```
On branch master
Changes not staged for commit:
	modified:   app/database/database.py          (+188/-..)
	modified:   app/database/repositories.py      (+3)
	modified:   app/pages/upload.py               (+110/-..)
	modified:   app/services/extraction_service.py (+4/-..)
	modified:   app/utils/validators.py           (+26/-..)
	modified:   tests/conftest.py                 (+115)
	modified:   tests/test_auth.py                (+11)
	modified:   tests/test_repair.py              (+2)
	modified:   tests/test_upload_processing.py   (+11)
Untracked files:
	data_backup_2026-10-01/
	tests/test_validators.py

git diff --stat: 9 files changed, 398 insertions(+), 72 deletions(-)
```

**FACT:** every hardening feature from Tasks 1–4 lives in *uncommitted* working-tree changes plus one untracked test file. Only `24c2a38` (migration fix) is committed.

## 1.3 Every commit since `fad961e` (`git show --stat`) — and what it *really* changed

| commit | stat (files changed) | what it really changed |
|---|---|---|
| `fad961e` docs | ARCHITECTURE.md +174, README.md +3/-1 | Docs only: documented the .ics feature. |
| `0927040` feat ics_service | app/services/ics_service.py +124, requirements.txt +1 | New service `build_ics`/`build_ics_from_events_and_reminders` + `icalendar` dep. |
| `c5063b4` ics buttons | app/pages/reminders.py +69/-5 | Added export buttons + `_get_confirmed_events_with_reminders` helpers to Reminders page (reminders.py:13,26,124-128). |
| `7ec6aa7` ics tests | tests/test_ics_service.py +276 | 9 tests for ics building (timezone, all-day, special chars). |
| `ebcae1d` upload NameError fix | upload.py +2/-2, main.py ±, .streamlit/config.toml +2, tests/test_upload_processing.py +189 | Fixed `user.id → user_id` NameError in upload flow; added 4 regression tests. |
| `7f2a687` ruff/logging/event test | main.py +8, chat.py +11, reminders.py +106/-.., summaries.py +8, upload.py +2, tests +45 | Silenced exception tracebacks into `logging.exception`, refactored reminders page, added event-extraction test; self-described "fix bug introduced in 5583f73". |
| `7bb5e92` cleanup | .env.example +3, embedding_service.py +27/-.., extraction_service.py +2/-2 | HF cache detection + `HF_HUB_OFFLINE` setdefault + pymupdf import fix. **Commit message says "silence noisy loggers" but `git show 7bb5e92` contains no logger-level change** — only an `INFO` log line in embedding_service.py:32. Message overstates. |
| `335ebaa` Task 1 validation | upload.py +82/-.., validators.py +45/-.., config.py +4, .env.example +4, requirements.txt +1 | Magic-byte validation, size limit from config, filename sanitization, per-user upload folder (upload.py:52-66,211-229). |
| `fd33a62` Task 2 duplicates | database.py +32, models.py +1, repositories.py +19, upload.py +34, tests +84 | `file_hash` column + SHA-256 + `get_by_hash` per-user duplicate gate (upload.py:234-241). |
| `4a34a65` Task 3 OCR fallback | extraction_service.py +54/-.., tests/test_extraction.py +37 | Per-page OCR fallback when a PDF page has <50 chars of text (extraction_service.py:53-79). |
| `90b9c8f` Task 4 consistency | database.py +48, repositories.py +34, upload.py +32, scripts/repair.py +232, tests +303 | Failure cleanup in `_process_document` except block, `DocumentRepository.delete` full cleanup, new `scripts/repair.py` orphan detection. |
| `24c2a38` migration fix (HEAD) | database.py +56/-.., tests/test_migration.py +298 | Moved `CREATE INDEX idx_documents_user_hash` to *after* `_migrate_add_file_hash`; added 4 migration tests. |

---

# PART 2: Test health

## 2.1 Full pytest suite

Command: `cd /home/shreesh/MemoryNest && .venv/bin/python -m pytest tests/ -v`
(full log: `/tmp/opencode/audit_pytest.txt`)

```
============= 4 failed, 71 passed, 1 warning, 20 errors in 14.66s ==============
```

95 tests collected (`pytest --collect-only -q`). Per test file:

| test file | collected | passed | failed | errors |
|---|---|---|---|---|
| tests/test_auth.py | 7 | 3 | **4** | 0 |
| tests/test_chunking.py | 8 | 8 | 0 | 0 |
| tests/test_database.py | 8 | 0 | 0 | **8** |
| tests/test_embedding.py | 4 | 4 | 0 | 0 |
| tests/test_extraction.py | 10 | 10 | 0 | 0 |
| tests/test_ics_service.py | 9 | 9 | 0 | 0 |
| tests/test_llm.py | 3 | 3 | 0 | 0 |
| tests/test_migration.py | 4 | 4 | 0 | 0 |
| tests/test_more_services.py | 8 | 8 | 0 | 0 |
| tests/test_rag.py | 4 | 4 | 0 | 0 |
| tests/test_repair.py | 3 | 0 | 0 | **3** |
| tests/test_upload_processing.py | 9 | 0 | 0 | **9** |
| tests/test_validators.py | 18 | 18 | 0 | 0 |
| **TOTAL** | **95** | **71** | **4** | **20** |

All 24 non-passing tests fail with the same error, e.g.:

```
E   sqlite3.OperationalError: no such table: users
app/database/repositories.py:36: OperationalError        (setup of test_database.py::test_user_crud)
app/database/repositories.py:56: OperationalError        (test_auth.py::test_register_and_login)
```

**FAILED (4):** `test_auth.py::test_register_and_login`, `::test_register_rejects_duplicate`, `::test_login_wrong_password`, `::test_login_unknown_user`
**ERROR at setup (20):** all 8 of `test_database.py`; all 3 of `test_repair.py`; all 9 of `test_upload_processing.py` (full list in `/tmp/opencode/audit_pytest.txt`).

### Root cause (PROVEN, probe in /tmp)

`get_connection()` resolves the DB path from **config/env**, not from the module attribute tests patch:

- `app/database/database.py:38-45` — `get_connection()` calls `_get_db_path()`
- `app/database/database.py:12-17` — `_get_db_path()` does `importlib.reload(app.utils.config)` and returns `config.DB_PATH` (env-derived)
- `app/database/database.py:24-35` — module-level `DB_PATH` is a **`@property` object**, not a path: probe printed `type(app.database.database.DB_PATH) = <class 'property'>`

Test patterns vs reality:

1. `tests/test_database.py:30`, `tests/test_repair.py:22`, `tests/test_upload_processing.py:20` all do `monkeypatch.setattr("app.database.database.DB_PATH", db)`. **Ineffective** — `get_connection` never reads that attribute.
   Reproduction (`/tmp/opencode/out_probe1b.txt`):
   ```
   REPRODUCED: OperationalError: no such table: users
   monkeypatched DB_PATH (fixture) tables: ['users', 'sqlite_sequence', 'documents', ...]
   file the repo actually opened exists: True        <- repo opened the OTHER (never-initialized) file
   ```
2. `tests/test_auth.py:11-23` — fixture calls `init_db(tmp_path/"auth.db")` (line 16) but **never sets `DB_PATH` env** (lines 17-22 reload config without `setenv`; comment says "Set environment variable" but no `os.environ[...] = ...` exists). Probe (`/tmp/opencode/out_probe1.txt`):
   ```
   [5] UserRepository._connect() opened file: .../env_declared.db       <- NOT the fixture db
   [8] after reload, config.DB_PATH = .../env_declared.db
   [10] auth fixture's init_db wrote tables to: .../auth.db -> ['users', ...]
   ```
   init_db writes to one file, repositories read another → `no such table`.
3. **Working pattern** (`tests/test_validators.py:244-249`): `monkeypatch.setenv("DB_PATH", ...)` + `importlib.reload(config)` + `init_db()` (no arg) → everything points at the same temp file → all 18 validator tests pass.

## 2.2 Ruff

Command: `.venv/bin/python -m ruff check app/ tests/ --select F821,F811,F841` (log: `/tmp/opencode/audit_ruff.txt`)

```
Found 20 errors.
[*] 18 fixable with the --fix option (1 hidden fix can be enabled with the --unsafe-fixes option).
```

| file | count | issues |
|---|---|---|
| app/pages/upload.py | 5 | F811 re-imports `ChunkRepository`/`vector_service` (:71,:72,:104,:105), F841 unused `doc_repo` (:75) |
| tests/test_upload_processing.py | 6 | F811 `_process_document` re-import (:79,:129), `hashlib` re-import (:243,:278,:325,:375) |
| tests/test_validators.py | 5 | F811 `Image/ImageDraw/ImageFont` (:285), `_save_uploaded_file`/`_process_document` (:351) |
| tests/conftest.py | 1 | F811 `shutil` re-import (:89) |
| tests/test_auth.py | 1 | F811 `importlib` re-import (:21) |
| tests/test_migration.py | 1 | F811 duplicate `create_old_schema_db` (:16 def, :251 re-def) |
| tests/test_repair.py | 1 | F811 `ChunkRepository` re-import (:147) |

No F821 (undefined names) in `app/` or `tests/`. **Not fixed — audit is read-only.**

Additional issues ruff did NOT flag (found by reading):
- `SCHEMA` is defined **twice** in `app/database/database.py` (line 60 and line 214; second wins).
- `tests/conftest.py` contains the guard block twice (lines 39–64 and 93–118; second `@pytest.fixture` shadows the first) and the temp-env setup twice (`pytest_configure` :17-29 and session fixture :68-90).
- DEBUG `print()` statements in production code: `app/pages/upload.py:100,102,115,119,159,163` and `app/database/repositories.py:151` (visible in probe output as `DEBUG set_text: ...`).

## 2.3 TEST POLLUTION — does any test touch real data/?

Grep for real-path usage: `grep -rn "/home/shreesh\|MemoryNest/data\|Path(\"data\"\|'data/'" tests/`

```
tests/conftest.py:40:REAL_DATA_DIR = Path("/home/shreesh/MemoryNest/data").resolve()
tests/conftest.py:94:REAL_DATA_DIR = Path("/home/shreesh/MemoryNest/data").resolve()
tests/test_repair.py:101,108,131,138,180,187: cwd="/home/shreesh/MemoryNest"   (project root, subprocess cwd only)
tests/test_migration.py:13:sys.path.insert(0, "/home/shreesh/MemoryNest")      (sys.path only)
```

**VERDICT: no test reads or writes `data/memorynest.db`, `data/uploads/`, or `data/chroma/`.** The only `data/` references are the guard constants.

### How config/DB paths are resolved in tests (`tests/conftest.py`)

1. `pytest_configure` (conftest.py:17-29): creates one `tempfile.mkdtemp(prefix="memorynest_test_")`, sets `DB_PATH`, `CHROMA_DIR`, `UPLOAD_DIR`, `AUDIO_DIR`, `MOCK_LLM=1`, then `importlib.reload(config_module)` (lines 22-29). Duplicated again in session fixture `setup_test_environment` (lines 68-90).
2. Runtime resolution: `database._get_db_path()` (database.py:12-17) **reloads config on every connection** → reads env → temp path. `vector_service` reads module attr `CHROMA_DIR`.
3. Guard: `@pytest.fixture(autouse=True) _check_real_data_access_during_test` (conftest.py:57-64, duplicated 111-118) fails a test if `config.DB_PATH/CHROMA_DIR/UPLOAD_DIR/AUDIO_DIR` resolve under real `data/` — `_check_real_data_access` (conftest.py:47-53, duplicated 101-107).

### Path-patching inventory (file:line)

| location | mechanism | effective? |
|---|---|---|
| tests/conftest.py:22-25, 75-78 | env + reload | YES (this is why non-DB tests pass) |
| tests/test_validators.py:248-249 | `setenv` + reload (config.py) | YES — 18/18 pass |
| tests/test_embedding.py:34,72 / test_rag.py:24 | monkeypatch `vector_service.CHROMA_DIR` | YES — module attr read at singleton init |
| tests/test_database.py:30 | monkeypatch `database.DB_PATH` | **NO** (property ignored by `_get_db_path`) |
| tests/test_repair.py:22 | same | **NO** |
| tests/test_upload_processing.py:20 | same | **NO** |
| tests/test_auth.py:11-23 | `init_db(tmp)` but no `setenv` | **NO** — writes/reads different files |

**Side effect:** because the monkeypatch is ignored, these tests connect to conftest's *temp* file (never initialized) — they fail, but they do **not** pollute real `data/`.

## 2.4 Real DB contents (read-only: `sqlite3 -readonly data/memorynest.db`)

```
PRAGMA integrity_check → ok ; PRAGMA user_version → 0
users = 10 ; documents = 301 ; document_chunks = 1960

status: error=137, ready=164      (uploaded/extracting = 0)

top filenames (filename, count):
  og.pdf                          107
  og.docx                         100
  318_Shreesh_Kajve.docx           80
  valid.pdf                          5
  deadline.txt                       4
  valid.png                          3
  RepoSense_Synopsis (1) (1).pdf     1
  AI_Personal_MemoryOS_Knowledge_Management_Case_Study.docx 1

by user_id: 2→1, 3→209, 4→83, 6→1, 7→1, 8→2, 9→2, 10→2   (users 1 and 5: 0 docs)

users: 1 Shreesh, 2 shreesh, 3 shreesh1234, 4 shreesh1, 5 batchuser,
       6..10 batchuser_23c0f4f7 / batchuser_f51fddf5 / batchuser_747e2737 /
             batchuser_47a55a98 / batchuser_668fe66b
```

**How many look like test fixtures:** by filename, **299 of 301 (99.3%)** are repetitive test uploads (`og.pdf` 107×, `og.docx` 100×, `318_Shreesh_Kajve.docx` 80×, `valid.pdf/valid.png/deadline.txt` 12×). Only 2 rows (`RepoSense_Synopsis (1) (1).pdf`, `AI_Personal_MemoryOS_...docx`) plausibly resemble real documents. Accounts `shreesh1234` (id 3) and `shreesh1` (id 4) hold 292/301 rows and read like test accounts; `batchuser_*` (ids 6-10) are provably generated (uuid-hex usernames).

Additional read-only consistency probe (`/tmp/opencode/audit_db_filecheck*.txt`):

```
documents: 301, stored_path exists: 293, missing: 8
missing-file docs (id,user_id,status): [(293,6,'error'), (294,7,'error'), (295,8,'error'),
  (296,8,'error'), (297,9,'error'), (298,9,'error'), (299,10,'error'), (300,10,'error')]
files on disk: 294 | orphan files (not referenced): 1 ['data/uploads/1_7f7c85d3.pdf']
document_chunks: 1960 | ready docs: 164 | ready docs with 0 chunk rows: 0
```

- All 8 missing files belong to `batchuser_*` rows already marked `error`; their per-user folders were removed (consistent with `_process_document`'s cleanup `path.parent.rmdir()`, upload.py:190).
- 1 orphan file exists in real data (`data/uploads/1_7f7c85d3.pdf`) — exactly the kind of issue `scripts/repair.py` targets.
- Ready docs ↔ chunk rows are consistent (0 ready docs without chunks).

---

# PART 3: Feature checklist

Legend: **Real** = runs actual code with real deps (Tesseract/Chroma/embeddings); **Mocked** = LLM/SMTP stubbed.

### 1. Auth + user isolation — PARTIAL

- **Implemented:** `app/utils/auth.py:18 register`, `:37 login`; every repo query carries `AND user_id` (e.g. `repositories.py:106,117,128,141,155,200,243,255`); Chroma filter `where={"user_id": user_id}` (`vector_service.py:75`), delete `where={"$and":[document_id,user_id]}` (`vector_service.py:99`), `delete_user` (`:105-107`).
- **Tests:** `test_auth.py` 3/7 pass, 4 fail (DB wiring, §2.1); `test_database.py::test_document_crud_and_user_isolation` ERROR (never runs); `test_rag.py::test_rag_user_isolation` **PASSED** (real Chroma + real embeddings, mock LLM).
- **Live probe** (`/tmp/opencode/out_probe6_auth.txt`, temp DB):
  ```
  register: alice err: None
  login ok: True
  duplicate register blocked: True err: Username is already taken.
  wrong password blocked: True err: Invalid username or password.
  unknown user blocked: True err: Invalid username or password.
  ```
  Isolation probe (`out_probe4.txt`): `alice.list_for_user: ['alice_secret.txt']`, `bob: ['bob_secret.txt']`, `alice reads bob's doc id=2 -> None`, `chroma query filters on user_id: True`.
- **Status: PARTIAL** — isolation and auth logic VERIFIED live; the auth/isolation *test suite* is BROKEN (§2.1). App-level E2E through Streamlit UI: UNVERIFIED (no `streamlit run` in audit).

### 2. Upload validation — VERIFIED

- **Implemented:** `validators.py:58 validate_file_content` (magic bytes via `filetype.guess`), `:69 validate_size`, `:33 validate_filename`, `:42 sanitize_filename`, `:77 file_type_for`; config `MAX_FILE_SIZE_MB=20` (`config.py:44`); UI gate `upload.py:211-229`; per-user folder `upload.py:52-66` (`_save_uploaded_file`, `user_dir = _get_upload_dir()/str(user_id)`).
- **Tests:** `tests/test_validators.py` — **18/18 PASSED**, real bytes (no mocks; includes `test_validate_file_content_random_binary_rejected`, `test_sanitize_filename_removes_path_traversal`, `test_validate_size_too_large`, batch e2e `test_upload_batch_rejected_file_does_not_stop_valid_files`).
- **Live probes:** see §4a/4b/4c — binary `.pdf` rejected; `max+1` rejected; `../../x.pdf → "x.pdf"` saved to `uploads/1/a8c357f265b1.pdf` (no traversal).
- **Cosmetic bug:** `validators.py:74` formats size with decimal `1e6` while config is MiB — error text says `limit 21 MB` for a 20 MiB limit (probe4 output). Display-only.

### 3. Duplicate detection (SHA-256) — PARTIAL

- **Implemented:** hash computed at `upload.py:234`, gate at `upload.py:236-241` (`doc_repo.get_by_hash(user.id, file_hash)`); `repositories.py:112-121 get_by_hash`; index `idx_documents_user_hash` (`database.py:191-194`).
- **Tests:** `test_upload_processing.py::test_duplicate_detection_same_user` and `::test_duplicate_detection_different_users` — **ERROR at fixture setup, never executed** (§2.1). Their assertions are repository-level (would pass once DB wiring is fixed — logic verified live below).
- **Live probe** (§4d): user1 second attempt → `get_by_hash found -> True` (blocked); user2 same content → `found -> False`, new row id=3 created (allowed).
- **Status: PARTIAL** — logic VERIFIED by probe; the two designated tests do not run.

### 4. OCR fallback for scanned PDFs — VERIFIED (REAL Tesseract)

- **Implemented:** `extraction_service.py:53-79` — per-page fallback when `len(page_text) < 50` and `shutil.which("tesseract")`; image files route to `ocr_service.ocr_image` (`extraction_service.py:28-29`).
- **Tests:** `test_extraction.py::test_ocr_image`, `::test_extract_routes_image_to_ocr`, `::test_extract_pdf_ocr_fallback` — **all PASSED**. Real/mocked: **REAL** — `grep -rn "unittest.mock\|MagicMock\|patch" tests/` → no matches; tests feed actual PIL images/PDFs.
- **Live probe** (§4e): `tesseract 5.5.3` at `/usr/bin/tesseract`; image-only PDF with **0-char native text layer** extracted `[Page 1 OCR]\nAUDIT SCANNED INVOICE...` including `AUD-2026-777`.

### 5. Failure cleanup — PARTIAL (data cleanup verified; failure MARKING broken)

- **Implemented:** `upload.py:166-193` (except block inside `_process_document`): deletes chunk rows (:178), Chroma vectors (:181-182), stored file (:185-192).
- **BROKEN parts (proven):**
  - **No `raise` anywhere in `upload.py`** (`grep -n "raise" app/pages/upload.py` → no matches) → exception is swallowed → `render()`'s `except` (upload.py:254-257) never fires and `st.success(...)` (:253) shows ✅ for failed uploads.
  - **Document status is never set to `error`:** only `update_status(..., "extracting")` exists (`upload.py:113`); `grep -rn '"error"' app/` shows only *display* code (`documents.py:25,44`). The function that claims to mark errors — `_cleanup_failed_document` (upload.py:68-94) — **has zero callers** (`grep -rn "_cleanup_failed_document" app/` → only the definition) and its body contains **no status update either**, despite the docstring "marks it as error" (upload.py:70).
  - Consequence: on failure the row is stuck at `status='extracting'` forever.
- **Tests:** `test_upload_processing.py::test_process_document_failure_marks_failed` and `::test_failure_cleanup_removes_partial_data` both assert `pytest.raises(FileNotFoundError)` + `status == "error"` — **ERROR at fixture setup today; when the DB wiring is fixed they will FAIL** (function does not raise, status never `error`).
- **Live probe** (§4f, sabotage `VectorService.add_chunks` after chunk rows written): `_process_document raised: None`; `doc status after failure: extracting | error_message: None`; `chunks left in SQLite: 0`; `vectors left in Chroma for doc: 0`; `file left on disk: False`; `doc row left in SQLite: True`.
- **Status: PARTIAL** — SQLite/Chroma/file cleanup VERIFIED; failure propagation + status marking BROKEN.

### 6. Document delete — VERIFIED (by probe; test does not run)

- **Implemented:** UI `documents.py:33-41`; full cleanup in `repositories.py:175-210` (`DocumentRepository.delete`: read stored_path → delete chunks+collect chroma_ids → Chroma delete → row delete → unlink file → rmdir user folder).
- **Test:** `test_upload_processing.py::test_document_delete_cleans_everything` — ERROR (fixture), never executed.
- **Live probe** (§4-6): after `drepo.delete()` → `row after delete: None`, `chunks after delete: 0`, `vectors after delete: 0`, `file exists after delete: False`.

### 7. scripts/repair.py — PARTIAL

- **Implemented:** `scripts/repair.py` — 4 checks (`check_orphan_vectors` :42, `check_chunks_without_document` :71, `check_files_without_document` :113, `check_documents_without_chunks` :159), `--fix` flag (:31), `--db-path` (:32), `main()` :190-228.
- **Tests:** `test_repair.py` 3 tests (dry-run + fix via subprocess, `cwd=project`, temp env) — all **ERROR at fixture** (§2.1).
- **Live probe** (§4-7, temp copy only): report mode found `Total issues found: 3` (orphan chunk 1, orphan file 1, ready-doc-without-chunks 1), exit 1; `--fix` → `Deleted 1 orphan chunks`, `Deleted 1 orphan files`, `Marked 1 documents as error`, `orphan chunk rows left after --fix: 0`.
- **BROKEN default path:** running without `--db-path` crashes: `stderr tail: NameError: name 'DEFAULT_DB_PATH' is not defined` (`repair.py:39` references an undefined name). Always-passed in tests → hidden.
- Minor: `main()` returns `1` even after a successful `--fix` (repair.py:227 `0 if total_issues == 0 else 1` counts issues *found*, not issues *remaining*).
- **Status: PARTIAL** — both modes VERIFIED with explicit `--db-path`; default invocation BROKEN.

### 8. DB migration for file_hash — VERIFIED

- **Implemented:** `database.py:180-188 _migrate_add_file_hash` (PRAGMA table_info → ALTER TABLE → backfill), `:197-211 _backfill_file_hashes` (SHA-256 of stored file), `:191-194 _create_file_hash_index` (runs after migration — the `24c2a38` fix), called from `init_db` :174-175.
- **Tests:** `test_migration.py` — **4/4 PASSED** (`test_migration_adds_file_hash_column`, `::test_init_db_idempotent_on_migrated_db`, `::test_init_db_on_fresh_database`, `::test_migration_preserves_existing_data`); real SQLite in tmp, no mocks. (File has a duplicate `create_old_schema_db` definition — ruff F811, :16/:251 — harmless because identical.)
- **Live probe in /tmp only** (§4-8): old-schema DB (11 columns, no `file_hash`) → after `init_db`: `file_hash added: True`, `backfill matches file content: True`, `indexes: ['idx_documents_user_hash','idx_documents_user']`, second `init_db` → `rows: 1, duplicate rows: 0` (idempotent).
- **Real DB corroborates:** `data/memorynest.db` documents table already has `file_hash TEXT NOT NULL DEFAULT ''` + both indexes (`.schema documents` output, §2.4).

### 9. Event extraction user_id bug fix + reminders flow — PARTIAL

- **Implemented:** `upload.py:144-155` — `ev_repo.create(user_id=user_id, ...)` explicitly (the fixed bug: no bare/global `user`); reminders flow `reminders.py:46-128` (confirm :97, skip :117, send :169-212, .ics export :124-128); `event_service.extract_events`.
- **Tests:** `test_upload_processing.py::test_process_document_extracts_events` — **ERROR (does not run)**; `test_more_services.py::test_event_extraction_regex` + `::test_event_extraction_no_dates` — PASSED (regex layer, no DB); `test_database.py::test_events_and_reminders` — ERROR; email tests `::test_email_config_missing`, `::test_send_reminder_missing_config` — PASSED but **deliberately mocked by deleting env config** (`monkeypatch.delenv("EMAIL_*")`, test_more_services.py:77-79,86-88) — they only verify the *missing-config* path.
- **Live probe** (§4-9): processing a TXT with 2 dates produced 3 events, `any event with wrong user_id: False`, non-uploader sees `0` events.
- **Email send: UNVERIFIED** — no SMTP credentials available; no live send attempted (correct for a read-only audit).
- **Status: PARTIAL** — extraction+isolation VERIFIED live; designated test broken; live email UNVERIFIED.

### 10. .ics export — VERIFIED

- **Implemented:** `ics_service.py:32 build_ics`, `:109 build_ics_from_events_and_reminders`; buttons `reminders.py:124-128`.
- **Tests:** `test_ics_service.py` — **9/9 PASSED** (real `icalendar` parsing round-trip inside tests; no mocks).
- **Live probe** (§4-10): temp event+reminder → `wrote .../export.ics size 570` → `parsed VEVENT count: 1`, `SUMMARY: Audit probe meeting | DTSTART: 2026-10-15 09:00:00+05:30 TZID=Asia/Kolkata`; `build_ics` single-event API also `VEVENT count: 1`.

### 11. RAG chat with citations + similarity threshold — VERIFIED (mock LLM)

- **Implemented:** `rag_service.py:49-87` — threshold gate at `:64` (`results[0]["similarity"] < min_similarity → below_threshold=True, sources=[]`), sources formatted `:77-83`; config `RAG_MIN_SIMILARITY=0.30`, `RAG_TOP_K=5` (`config.py:38-39`); citations in prompt `:23,45`; chat UI renders `result.sources` (`chat.py:49-57`) and stores them (`:59`).
- **Tests:** `test_rag.py` — **4/4 PASSED** (`test_rag_answer_above_threshold`, `::test_rag_answer_below_threshold`, `::test_rag_user_isolation`, `::test_rag_empty_db`); real embeddings + real Chroma, **LLM mocked** (`MOCK_LLM=1`, conftest.py:26).
- **Live probe** (§4-11): `RAG_MIN_SIMILARITY = 0.3`; far query → `below_threshold = True | sources = 0 | answer: "I couldn't find this information in your stored documents."`; near query → `below_threshold = False | sources = [('audit_doc.txt', 0.809)]`.
- **Real Ollama answer path: UNVERIFIED** in this audit (mock used; Ollama service itself available but not exercised to keep the audit deterministic).

### 12. Summaries, TTS, History, Dashboard — PARTIAL (import + service functions verified; page `render()` not executed)

- **Live probe** (§4-12): all 7 pages import OK (`dashboard, upload, documents, chat, history, summaries, reminders` → `import ... : OK`).
  - `summary_service.summarize_document(...)` → `len: 113`, mock-LLM text (`summary_service.py:30`).
  - `tts_service.tts_available() -> True`; `tts_service.synthesize_to_file('hello audit') -> /tmp/.../audit_probe.wav` — **real synthesis** (espeak-ng present).
  - `ConversationRepository().list_for_user(1) -> []` (`history` data path).
  - Dashboard stat path: `DocumentRepository.count_for_user(u) = 1 / u2 = 0` (§4-5 probe).
- **Tests:** `test_more_services.py` 8/8 PASSED (summary mocked, TTS availability both branches mocked, event regex real).
- **UNVERIFIED:** Streamlit `render()` bodies of these 4 pages were not executed (would require driving Streamlit UI; only `import` + service/repo functions proven).

### 13. Logging config + HF offline behavior — PARTIAL

- **Logging:** `main.py:16-20` — `logging.basicConfig(level=logging.INFO, format=..., datefmt=...)`. **That is the only logging configuration in the app** (`grep -rn "basicConfig|setLevel|getLogger" app/` → main.py:16 + one `getLogger(__name__).info` at embedding_service.py:32). No per-logger levels, no silencing — despite commit `7bb5e92` claiming "silence noisy loggers" (diff contains no such change, §1.3).
- **HF offline:** `embedding_service.py:20-35` — `_is_model_cached()` checks `HF_HOME/hub/models--<name>` and `os.environ.setdefault("HF_HUB_OFFLINE", "1")` if cached else `"0"`; `.env.example` documents `HF_HUB_OFFLINE` (added by 7bb5e92).
- **Live probe** (`/tmp/opencode/out_probe_hf.txt`):
  ```
  _is_model_cached(all-MiniLM-L6-v2): False
  HF_HUB_OFFLINE before load: None
  Loading weights: 100%|...| 103/103   (loaded instantly from local storage)
  HF_HUB_OFFLINE after load: 0
  (plus: "Warning: You are sending unauthenticated requests to the HF Hub...")
  ```
  → On this machine the cache check **misses** (model loads fine anyway), so offline mode is never enabled and a Hub round-trip is still attempted. Offline behavior is **intent-coded but not effective here** → PARTIAL.

### 14. Docs vs code — PARTIAL (3 mismatches + 1 gap)

| claim | evidence | verdict |
|---|---|---|
| README.md:147 `# 50 tests covering: ...` | actual collected: **95** (`pytest --collect-only`: per-file sums to 95) | **MISMATCH** (stale — was true at `2f78ba4`) |
| README.md:133 services list `... summary, TTS, events, email` (11 names, no ics) | `ls app/services/` = 12 modules incl. `ics_service.py`; ARCHITECTURE.md:39 says 12 and :51 lists ics | **MISMATCH** (README stale; ARCHITECTURE correct) |
| README + ARCHITECTURE mention of duplicate detection / repair script / migration / file_hash | `grep -c -i -E "repair\|duplicate\|migration\|file_hash" README.md ARCHITECTURE.md` → `README.md:0`, `ARCHITECTURE.md:0` | **GAP** — entire Tasks 1–4 surface undocumented (commits `335ebaa..24c2a38` came after last docs commit `fad961e`) |
| ARCHITECTURE.md:69 "Database Tables (9)" | SCHEMA (database.py:60-165) = users, documents, document_chunks, conversations, messages, summaries, events, reminders, notification_logs = 9 | MATCH (but ARCHITECTURE omits new `file_hash` column — minor) |
| ARCHITECTURE.md:157 threshold 0.30 | config.py:39 `RAG_MIN_SIMILARITY = 0.30` | MATCH |
| README.md:69 CHUNK_SIZE 450 / overlap 50 | config.py:40-41 `450` / `50` | MATCH |
| 7 pages (README.md:132, ARCHITECTURE.md:10,31) | main.py:86-96 `st.navigation` has exactly 7 `st.Page`s | MATCH |
| README.md:11 "top-5 retrieval" | config.py:38 `RAG_TOP_K = 5` | MATCH |
| README.md:124 "all SQL tables and Chroma metadata carry user_id" | repositories.py `AND user_id` everywhere; vector_service.py:50,75 | MATCH (verified §1) |

---

# PART 4: Probes (all in temp dirs, real output pasted)

### (a) Random binary renamed `.pdf` through upload processing

```
=== PROBE (a): random binary renamed .pdf ===
filename: fake.pdf, first bytes: b'\x0c\xec\xedY\x01<\xe1Y'
validate_file_content -> (False, 'Could not determine file type from content', '')
validate_filename('fake.pdf') -> (True, '')
DEBUG _process_document ENTRY: doc_id=1, user_id=1, file_type=pdf
_process_document raised: None
doc status after: extracting | error_message: None
file still on disk: False
```

- **UI gate rejects it** (`validate_file_content` False) → never reaches processing in the real flow.
- Forced through `_process_document` anyway: file/chunks cleaned (`file still on disk: False`), **but no exception surfaced and doc stuck at `extracting`** → confirms §5 failure-marking bug.

### (b) Oversized file

```
=== PROBE (b): oversized file ===
config MAX_FILE_SIZE_BYTES = 20971520 (20 MB)
size=max+1 -> (False, 'File too large (21.0 MB, limit 21 MB)')
size=max   -> (True, '')
size=0     -> (False, 'File is empty')
```

Rejected at 1 byte over the 20 MiB limit (`validators.py:69-75`). Message displays decimal MB → says "21 MB" (cosmetic only).

### (c) Filename `../../x.pdf`

```
=== PROBE (c): filename '../../x.pdf' ===
sanitize_filename('../../x.pdf') -> 'x.pdf'
validate_filename(safe) -> (True, '')
file_type_for(safe) -> pdf
_save_uploaded_file stored_path -> /tmp/audit_p2_k1bmaopz/uploads/1/a8c357f265b1.pdf
escaped upload root: False
under user folder: True
```

Traversal stripped; file lands inside `<uploads>/<user_id>/`.

### (d) Same file twice — one user, then two users

```
=== PROBE (d): same file twice — one user, then two users ===
user1 second attempt: get_by_hash found -> True (blocked by upload.py:238-241)
user2 same content: get_by_hash found -> False => allowed (no cross-user blocking)
user2 document row created: id = 3 (different users can upload same file)
different content hash != same: True
```

(Repository-level execution of the exact gate used by `upload.py:238`; the Streamlit button loop itself is not driven in the audit.)

### (e) Image-only PDF through extraction with REAL Tesseract

```
=== PROBE (e): image-only PDF through extraction with REAL Tesseract ===
tesseract binary: /usr/bin/tesseract
tesseract --version: tesseract 5.5.3
native text layer length: 0 (expect 0)
extracted length: 81
OCR hit 'AUDIT': True
OCR hit 'AUD-2026-777': True
OCR marker '[Page 1 OCR]': True
excerpt: '[Page 1 OCR]\nAUDIT SCANNED INVOICE\nInvoice #: AUD-2026-777\n\nAmount: 4,321 dollars'
```

### (f) Simulated embedding/vector-store failure → what is left behind

Failure injected at `VectorService.add_chunks` (fires **after** chunk rows are written, upload.py:139→142):

```
_process_document raised: None
doc status after failure: extracting | error_message: None
chunks left in SQLite: 0
vectors left in Chroma for doc: 0
file left on disk: False
doc row left in SQLite: True
```

- **Nothing left in Chroma or on disk; chunk rows cleaned** ✅
- **Document row remains, stuck at `extracting`, and the failure was swallowed** ❌ (§5)

### (g) Document delete + event user_id (bonus probes, /tmp)

```
status after process: ready | chunks: 1
chunks before delete: 1 | vectors before delete: 1 | file exists before delete: True
row after delete: None
chunks after delete: 0
vectors after delete: 0
file exists after delete: False

events for uploader (user 1): 3   (all user_id=1)
events visible to NON-uploader (user 2): 0
any event with wrong user_id: False
```

### (h) repair.py (temp copy) + migration (/tmp) + .ics round-trip + auth + RAG (key lines)

```
--- repair.py REPORT (temp copy) ---
MODE: DRY RUN (no changes)
  Orphan vectors: 0
  Chunks without document: 1
  Orphan files: 1
  Documents without chunks: 1
Total issues found: 3 | exit code: 1

--- repair.py --fix ---
  Deleted 1 orphan chunks
  Deleted 1 orphan files
  Marked 1 documents as error
  orphan chunk rows left after --fix: 0 (expect 0)
run WITHOUT --db-path: exit 1
stderr tail: NameError: name 'DEFAULT_DB_PATH' is not defined

--- migration (old schema, /tmp) ---
columns BEFORE: [... 11 cols, no file_hash]
columns AFTER:  [... 11 cols, 'file_hash']
file_hash added: True
backfill matches file content: True
indexes: ['idx_documents_user_hash', 'idx_documents_user']
rows after 2nd init_db: 1 | duplicate rows: 0

--- .ics ---
wrote /tmp/.../export.ics size 570
parsed VEVENT count: 1
  SUMMARY: Audit probe meeting | DTSTART: 2026-10-15 09:00:00+05:30 TZID=Asia/Kolkata

--- RAG threshold ---
RAG_MIN_SIMILARITY = 0.3 | RAG_TOP_K = 5
far query:  below_threshold = True  | sources = 0  | answer: "I couldn't find this information in your stored documents."
near query: below_threshold = False | sources = [('audit_doc.txt', 0.809)]

--- pages/services ---
import app.pages.dashboard/upload/documents/chat/history/summaries/reminders: all OK
summary_service.summarize_document -> len: 113 (mock LLM)
tts_service.tts_available() -> True ; synthesize_to_file -> /tmp/.../audit_probe.wav (real file)
```

Probe logs: `/tmp/opencode/out_probe1.txt`, `out_probe1b.txt`, `out_probe2.txt`, `out_probe3.txt`, `out_probe4.txt`, `out_probe4b_ics.txt`, `out_probe5.txt`, `out_probe6_auth.txt`, `out_probe_hf.txt`.

---

# PART 5: Summary

| # | item | status | evidence | what is missing |
|---|---|---|---|---|
| 1 | History / commits | VERIFIED | §1 full `git log`, `--stat` for 12 commits, `git status` | — |
| 2 | Test suite health | **BROKEN** | `4 failed, 71 passed, 20 errors / 95` (§2.1) | 24 tests cannot run; DB path wiring bug (`database.py:12-17,38-45` + `test_auth.py:11-23`) |
| 3 | Ruff F821/F811/F841 | **BROKEN** (20 errors) | §2.2 ruff output | 18 auto-fixable; not fixed (read-only) |
| 4 | Test pollution of real data/ | VERIFIED (none) | grep §2.3 + autouse guard conftest.py:57 + mtimes identical | — |
| 5 | Real DB contents | VERIFIED | §2.4 readonly queries + file-existence probe | 1 orphan file + 8 missing files already present in real data |
| 1 | Auth + user isolation | PARTIAL | probe6 auth live; probe4 isolation; `test_rag_user_isolation` PASSED | auth tests broken; Streamlit UI E2E UNVERIFIED |
| 2 | Upload validation | VERIFIED | probes 4a/4b/4c; `test_validators.py` 18/18 | cosmetic MB-message bug |
| 3 | Duplicate detection | PARTIAL | probe 4d (`get_by_hash` True/False) | its 2 tests ERROR (fixture); not exercised through the Streamlit button loop |
| 4 | OCR fallback | VERIFIED | probe 4e (real tesseract 5.5.3, 0-text-layer PDF); 3 extraction tests PASSED unmocked | — |
| 5 | Failure cleanup | PARTIAL / BROKEN | probe 4f: chunks/vectors/file gone BUT `raised: None`, status stuck `extracting`; `_cleanup_failed_document` (upload.py:68) has no callers | status `error` never set anywhere in app; swallowed exceptions make UI show ✅ on failure |
| 6 | Document delete | VERIFIED | probe 4g: row/chunks/vectors/file all gone | designated test ERROR (fixture) |
| 7 | scripts/repair.py | PARTIAL | probe 4h report+fix outputs, orphan chunk = 0 after fix | `NameError: DEFAULT_DB_PATH` without `--db-path` (repair.py:39); exit=1 even after successful fix |
| 8 | file_hash migration | VERIFIED | probe 4h (old-schema → column+backfill+index, idempotent); `test_migration.py` 4/4 | — |
| 9 | Event extraction user_id | PARTIAL | probe 4g: 3 events all `user_id=1`, other user sees 0 | `test_process_document_extracts_events` ERROR; live email send UNVERIFIED (no creds) |
| 10 | .ics export | VERIFIED | probe 4h: VEVENT parsed back, TZID correct; `test_ics_service.py` 9/9 | — |
| 11 | RAG + threshold | VERIFIED (mock LLM) | probe 4h: below/above threshold both correct; `test_rag.py` 4/4 | real Ollama answer UNVERIFIED in audit |
| 12 | Summaries/TTS/History/Dashboard | PARTIAL | probe 4h: all import; summary ran; real WAV synthesized; repo stat fns ran | page `render()` bodies not executed |
| 13 | Logging + HF offline | PARTIAL | main.py:16 INFO only; `out_probe_hf.txt`: cache check False → `HF_HUB_OFFLINE=0` + Hub warning | offline mode not effective on this machine; "silence noisy loggers" commit claim unsupported |
| 14 | Docs vs code | PARTIAL | 3 mismatches + 1 gap (§3.14) | README test count, README services list, zero docs for Tasks 1–4 |
| — | data/ untouched | VERIFIED | identical before/after mtimes (top of file) | — |

## Top 5 risks, most severe first — blunt

1. **The test suite is lying to you.** 24/95 tests never execute their assertions because `get_connection()` (database.py:38-45) ignores every `monkeypatch.setattr("app.database.database.DB_PATH", ...)` and `test_auth.py`'s fixture inits a DB it never points at. Right now "tests pass" means nothing for DB-dependent behavior — and the moment you fix the wiring, `test_process_document_failure_marks_failed` and `test_failure_cleanup_removes_partial_data` will fail (see #2). **Fix first:** make `_get_db_path()` honor an explicit override (or stop reloading config per connection), and make every DB fixture use the `setenv + reload + init_db()` pattern that already works in `test_validators.py:244-249`.

2. **Failed uploads report success and poison the DB with stuck rows.** `_process_document` swallows every exception (no `raise` in upload.py; except block upload.py:166-193), never sets `status='error'` (only setter in the app is `upload.py:113` → `"extracting"`), and its error-marking helper `_cleanup_failed_document` (upload.py:68) is dead code whose docstring lies. The real DB already shows the archaeology: 8 rows stuck from batch runs and 137 `error` rows from older code paths. Data cleanup (chunks/vectors/file) does work — the failure *semantics* don't. The two tests that assert the correct behavior exist but can't run.

3. **Everything valuable is uncommitted.** 9 modified files (+398/−72) + untracked `tests/test_validators.py` (18 tests) — all of Tasks 1–4 hardening. One `git checkout .` or disk slip away from losing it. Commit the work as soon as the suite is green (not part of this audit).

4. **The repo's hygiene signal is broken:** 20 ruff errors (F811/F841), `SCHEMA` defined twice (database.py:60 + :214), conftest guard/env blocks duplicated twice, DEBUG `print()` calls shipped in production paths (upload.py:100-164, repositories.py:151 — visible in every probe), `scripts/repair.py` crashes on its own default path (`DEFAULT_DB_PATH` undefined, repair.py:39), and README claims "50 tests" when 95 exist and never mentions duplicate detection, validation, repair, or migration. Fix in this order: repair.py NameError (one line), ruff `--fix`, remove prints/duplicate blocks, then docs.

5. **Offline story is aspirational.** `_is_model_cached()` returns `False` on a machine where the model loads instantly, so `HF_HUB_OFFLINE` is forced to `0` and every process start still pings the HF Hub (warning captured in `out_probe_hf.txt`). Combined with `MOCK_LLM` masking the real Ollama path and no live SMTP test, two of the three "local-first" legs (offline embeddings, real LLM answers, email delivery) are **UNVERIFIED** end-to-end.

**Recommended fix order:** (1) DB path wiring → green suite, (2) failure marking + re-raise in `_process_document` + wire up `_cleanup_failed_document`, (3) commit the tree, (4) ruff/prints/duplicate-block cleanup + `DEFAULT_DB_PATH`, (5) docs sync + HF cache-detection fix.
