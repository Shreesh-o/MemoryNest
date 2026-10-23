# MemoryNest — Build Progress

Log of the autonomous build. Newest entries first.

## 2026-10-23

### Awwwards Redesign ("The Evidence Chamber") & Design System Integration

- **Concept & Art Direction (Phase 1)**:
  - Specified "The Evidence Chamber" concept in `web/DESIGN.md`, emphasizing forensic reading rooms, uncompromised citation veracity, and local custody.
  - Selected editorial serif `Newsreader` for document citations and human quotes paired with contemporary neo-grotesk `Geist Sans` and `Geist Mono` for coordinates and data.
- **Design Foundations & Tokens (Phase 2)**:
  - Local font integration: Self-hosted `.woff2` files for `Geist Sans`, `Geist Mono`, and `Newsreader` in `web/public/fonts/` loaded via `web/src/app/fonts.ts` (zero remote requests).
  - Tailwind CSS v4 variables in `globals.css` with semantic tokens for warm archival parchment (`#F9F8F5` light ground) and obsidian archive (`#090A0C` dark ground), with evidence cobalt accents.
- **Marketing Landing Page & Evidence Bench (Phase 3)**:
  - Semantic, accessible landing page at `web/src/app/(marketing)/page.tsx` featuring the Evidence Bench, capabilities dossier, local execution mechanics, and local vs. cloud ledger.
- **Marketing-Scoped Motion Choreography (Phase 4)**:
  - Scoped Lenis smooth scroll and GSAP ticker integration in `web/src/app/(marketing)/layout.tsx` and `marketing-motion.tsx`.
  - Full `@media (prefers-reduced-motion: reduce)` compliance, instantly neutralizing animations when reduced motion is requested.
- **Archival Auth Flows (Phase 5)**:
  - Restyled `/login` and `/register` pages with archival folio borders, coordinate stamps, and semantic typography while strictly preserving all authentication handlers and redirect logic.
- **App Shell & Reminders Styling Polish (Phase 6)**:
  - Unified navigation tokens and card styling across the authenticated app shell (`/dashboard`, `/documents`, `/chat`, `/search`, `/map`, `/summaries`, `/reminders`).
  - Restored baseline reminder confirmation behavior without unbacked lead-time dropdowns, maintaining strict functional veracity.
- **Accessibility & Contrast Verification**:
  - Resolved badge contrast ratios to exceed WCAG AA requirements.
  - Added semantic `<main>` landmarks and `<h1>` headings to auth and marketing flows.

### Document Map (Relationship Graph)

- **Backend Embedding Similarity Engine (`app/services/link_service.py`)**:
  - Computes pairwise cosine similarity of mean document chunk embeddings across user documents.
  - Storage floor threshold (`LINK_STORE_MIN_SIMILARITY = 0.30`) stores candidate edges while read-time filter (`LINK_MIN_SIMILARITY = 0.45` default) returns prominent relationships.
  - Caps edges to top 3 neighbors per document to prevent visual clutter.
  - Computes shared terms using TF-IDF for readable relationship labels.
- **Database Schema & Migrations**:
  - Added `document_links` table (`id`, `user_id`, `doc_a`, `doc_b`, `score`, `shared_terms`, `created_at`) with foreign keys and compound indexes.
  - Implemented idempotent migration `_migrate_add_document_links(conn)` in `app/database/database.py`.
- **API Endpoints**:
  - `GET /api/graph?min_score=0.45`: Returns `{nodes, edges, unlinked}` for full user graph.
  - `GET /api/documents/{doc_id}/related?min_score=...`: Returns top related documents for a specific document.
  - `POST /api/graph/refresh`: On-demand graph recalculation.
  - `scripts/rebuild_links.py`: CLI maintenance script for rebuilding links across all users.
  - Event-driven auto-rebuild: Triggers background rebuild on document upload, deletion, and retry extraction.
- **Interactive Force Graph UI (`web/src/app/(app)/map/page.tsx`)**:
  - Hardware-accelerated 2D canvas force graph using `react-force-graph-2d` with dynamic sizing.
  - Base UI slider for real-time similarity threshold filtering (0.20–0.95).
  - Responsive document inspector side sheet showing connected neighbors, shared terms, and quick actions.

### Scoped Document Chat

- **Focused RAG Ingestion & Query Routing**:
  - Extended `POST /api/chat` with optional `document_ids: list[int] | null` parameter.
  - Validates document ownership, returns generic 404 for unknown/foreign document IDs, and rejects non-ready documents.
  - ChromaDB retrieval filters on `{"$and": [{"user_id": uid}, {"document_id": {"$in": doc_ids}}]}`.
  - Scope state (`all` vs. `selected` with document IDs) persisted in `messages` table and returned in conversation history.
  - Custom refusal response when scoped retrieval finds no evidence: `"I couldn't find this information in the selected documents."`
- **Frontend Scope Selector (`web/src/app/(app)/chat/page.tsx`)**:
  - Scope picker popover loaded from `GET /api/chat/documents`.
  - Visual badges indicating whether an answer was derived from all documents or specific selected files.

### Document Viewer & Enhanced Content Pipeline

- **Content & File Endpoints (`app/api/routers/documents.py`)**:
  - `GET /api/documents/{doc_id}/file`: Streams original file with security headers (`nosniff`, `CSP: sandbox`).
  - `GET /api/documents/{doc_id}/content`: Clean extracted text with disk cache (`data/text_cache/<doc_id>.txt`), whitespace normalization, hyphenation fixes, 500k character cap.
  - `GET /api/documents/{doc_id}/html`: DOCX HTML rendering via `mammoth` sanitized via `nh3`.
  - `POST /api/documents/{doc_id}/extract-events`: On-demand date/event extraction trigger.
- **Full In-Browser Viewer (`web/src/app/(app)/documents/[id]/page.tsx`)**:
  - Dual tabs: Rendered view (inline PDF iframe, DOCX HTML, responsive image with OCR notice) and Extracted Text (search, highlight, copy).
  - Document metadata sidebar with chunk and event inspection.
  - Fast action toolbar: Download, Delete, Summarize, Extract Events, Ask About Document.

### Semantic Search

- **Vector Search Endpoint (`app/api/routers/search.py`)**:
  - `POST /api/search`: Vector similarity search across document chunks with relevance scores and snippet highlights.
- **Search UI (`web/src/app/(app)/search/page.tsx`)**:
  - Fast query input, relevance score meters, document badges, and matched chunk snippets.

### Verification & Health Status

- **Pytest Suite**: **304 unit and API tests passing** across 35 test files with 0 failures (`tests/`).
- **Web Frontend**: Next.js 16 (App Router + Turbopack) production build compiles in ~1.4s with 0 errors across 13 routes (`web/`).
- **Backend API**: All registered FastAPI endpoints operational with JWT cookie authentication and strict multi-user isolation.
- **Service Stack**: Local Ollama LLM (`qwen2.5:3b-instruct`), sentence-transformers embeddings (`all-MiniLM-L6-v2`), ChromaDB persistent storage, and SQLite migrations verified.

### Google Calendar Integration & Reminders UI Polish (Phase 6)

- **Database Migration & Schema**:
  - Added `google_event_id`, `sync_status` (`not_synced` | `synced` | `failed` | `not_connected`), and `sync_error` columns to `reminders` table.
  - Implemented idempotent SQLite migration `_migrate_add_reminder_google_sync(conn)` in `app/database/database.py` with migration test in `tests/test_migration.py`.
- **Google Calendar Services & OAuth**:
  - `app/services/google_auth_service.py`: Multi-user OAuth flow with state cookie validation, token encryption via Fernet, and disconnection token revocation.
  - `app/services/google_calendar_service.py`: Automated event creation (`Asia/Kolkata` timezone, all-day vs timed, popup reminders clamped to Google limits, doc title context), idempotent update-if-exists, event deletion on reminder cancellation, and 401 token-revocation handling.
  - `app/services/reminder_flow_service.py`: Non-blocking Google Calendar event creation upon `confirm_event` and deletion upon `cancel_reminder`; manual retry sync via `sync_reminder`.
- **REST Endpoints & Schemas**:
  - `GET /api/google/status`, `POST /api/google/connect`, `GET /api/google/callback`, `POST /api/google/disconnect`.
  - `POST /api/reminders/{id}/sync` for manual sync retries.
  - Enhanced `ConfirmEventResponse` with `google_status` and `ReminderPublic`/`CalendarItem` with `sync_status`.
- **Frontend (Next.js 16)**:
  - **Google Calendar Card**: Displays connection status (not configured / connect button / connected as `<email>` with disconnect confirmation dialog).
  - **Query Param Handling**: Catches `?google=connected` or `?google=error` via Sonner toasts and cleans the URL without page reload (`window.history.replaceState`).
  - **Sync Badges & Retry**: Added visual badges on reminders and calendar items (`synced`, `failed` with interactive Retry button, `not_connected`).
  - **Combined Confirmation Toast**: Unified feedback toast (e.g. "Reminder set. Email sent. Added to Google Calendar.") reflecting real-time email and Google sync outcomes.
  - **Demoted .ics Download**: Kept `.ics` download as a secondary link, prioritizing direct Google sync.
- **Verification**:
  - 246 unit & integration tests passing in pytest (including 10 dedicated Google sync tests and 10 Google auth tests).
  - Next.js production build succeeds with 0 errors.

### Month Calendar View on Reminders Page (Phase 3)

- **Backend Aggregation API**:
  - `app/services/calendar_service.py`: Aggregates pending events and scheduled reminders into unified `CalendarItem` objects filtered by ISO date ranges.
  - `GET /api/reminders/calendar-items`: Validates start/end ranges (up to 90 days), enforces user isolation, and omits discarded/cancelled items.
- **Interactive Calendar Component**:
  - `web/src/components/reminders/month-calendar.tsx`: Full interactive month view with day cells, dot indicators (amber for pending, emerald for scheduled, red for sync failure), day details sheet, and quick action dialogs.

### Instant Reminder Confirmation Email

- **Email Notification**:
  - Automated confirmation email sent immediately upon confirming an event (`app/services/email_service.py:send_reminder_confirmation_email`).
  - Returns `email_status` (`sent` | `failed` | `not_configured` | `no_email`) in `ConfirmEventResponse`.
  - Displays instant delivery toast to the user indicating whether the email was sent or skipped.

---

## 2026-10-22

### User Email Management & Validation

- **Profile & Email Endpoints**:
  - `PATCH /api/auth/me/email` for setting, updating, or clearing user email addresses.
  - Normalized email validation in `app/utils/validators.py` and collision detection across users.
  - Interactive Email Management Card on the Reminders page with edit/save/clear workflow.

### Natural TTS Voices (edge-tts & piper) with Dynamic Fallback

- **TTS Engine Architecture (`app/services/tts_service.py`)**:
  - `edge-tts`: Online high-quality natural voice (`en-IN-NeerjaNeural`) with MP3→WAV transcoding via `ffmpeg`.
  - `piper`: Fast offline neural TTS models (`models/piper/`).
  - `espeak-ng`: Offline synthesized fallback.
  - `pyttsx3`: Local fallback.
- **UI Engine Indicator**:
  - Summaries page displays engine badge (e.g., `edge`, `piper`, `espeak`) alongside generated audio player.

### V2 Web UI, FastAPI Backend & Workflow Enhancements

- **FastAPI REST API Layer (`app/api/`)**: Full async/REST backend architecture supporting auth (JWT HTTP-only cookies), documents upload/management, RAG chat, semantic search, summaries, and reminders.
- **Next.js 16 Web Frontend (`web/`)**: Modern App Router UI using Base UI (shadcn), Tailwind CSS, TanStack React Query, and Sonner toasts.
- **Unified Dev Runner (`scripts/dev.sh`)**: Preflight validation, Ollama orchestration, FastAPI on `:8000`, and Next.js on `:3000` with hot reload and process cleanup (`--stop`).
- **Reminders Workflow**:
  - Reminder cancellation (`DELETE /api/reminders/{id}`) deletes reminder and reverts event back to "pending".
  - Confirmation dialogs for cancelling scheduled reminders and discarding pending events.
  - Due reminders check returning structured `{configured, sent, failed, skipped, errors, details}` without false failure counts when SMTP is unconfigured.
  - `GET /api/health` reports `email_configured: bool`.
- **Test Suite**: 200 unit and API tests passing in pytest (0 failures).

---

## 2026-09-21

### Verification — 2026-09-21 (Follow-up fixes)

**Bug fixes applied:**
1. **Streamlit import path** — Added `sys.path.insert(0, project_root)` at top of `app/main.py` so `from app.*` imports work when Streamlit runs from `app/` directory.
2. **TTS test** — Updated `test_tts_unavailable` to properly mock pyttsx3 engine failure (since espeak-ng is actually installed). Added `test_tts_available` for the happy path.

**Test results after fixes:**
```
51 passed, 1 warning in 24.60s
```

**Streamlit app verification:**
```
$ streamlit run app/main.py --server.headless true --server.port 8599
Uvicorn server started on :::8599
Local URL: http://localhost:8599
```
HTTP 200 confirmed — app loads without import errors.

**Manual smoke test results (via services + AppTest):**

| Check | Result | Notes |
|-------|--------|-------|
| 1. Register user | PASS | Auth module works; AppTest sidebar capture limitation only |
| 2. Upload document with factual content | PASS | Full pipeline: extract → chunk → embed → ChromaDB |
| 3. Question IN document → correct answer + citation | PASS | RAG returns mock answer with 1 source |
| 4. Question NOT in document → "couldn't find" | PASS | Below threshold (0.30), refuses to hallucinate |
| 5. User isolation (user2 cannot see user1's docs) | PASS | ChromaDB `where={"user_id": ...}` filter works |

All 5 checks: **PASS**

**Core functionality verified:** Register, upload, RAG with citations, threshold gating, multi-user isolation.

---

### Original build log (steps 1-19)

- **Step 19 (Final smoke test)**: Full pipeline verified end-to-end:
  register → upload PDF → extract text → chunk → embed → ChromaDB → RAG query → summary → event extraction → reminders → email check.
  All stages passed. Mock LLM used (MOCK_LLM=1); real Ollama works on CPU.

- **Step 18 (README)**: Complete with setup instructions, ASCII architecture diagram, and Future Scope section.

- **Step 17 (Dashboard)**: Counts (docs, chunks, summaries, conversations), upcoming deadlines, pending confirmations, due reminders, recent activity.

- **Step 16 (Email service)**: SMTP with Gmail app password, config validation, graceful missing-config handling.

- **Step 15 (Event service)**: Regex + dateparser first, LLM fallback; date formats: ISO, US, written months; deduplication.

- **Step 14 (TTS)**: pyttsx3 wrapper; graceful degradation when espeak-ng missing (logs install hint).

- **Step 13 (Summary service)**: Map-reduce for long docs (1200-token chunks, 100 overlap); short docs direct summarize.

- **Step 12 (History page)**: Conversation list, search messages, load/delete conversations.

- **Step 11 (RAG + Chat page)**: Full pipeline with similarity threshold (0.30), citations, mock LLM for testing.

- **Step 10 (LLM service)**: Ollama /api/generate client, availability check with caching, MOCK_LLM=1 fallback.

- **Step 9 (Embedding + Vector)**: sentence-transformers (all-MiniLM-L6-v2), ChromaDB PersistentClient with cosine space, user_id filtering.

- **Step 8 (Chunking)**: Sentence-aware, ~450 tokens target, ~50 overlap, hard-split for oversized sentences, char-based token estimate.

- **Step 7 (OCR)**: pytesseract + PIL, routes from extraction_service for image files.

- **Step 6 (Extraction)**: PDF (PyMuPDF), DOCX (python-docx), TXT (multi-encoding), images → OCR.

- **Step 5 (Upload page)**: Multi-file, validation (type/size), synchronous processing pipeline, status updates.

- **Step 4 (Streamlit shell)**: main.py with auth gate, session state, st.navigation over 7 pages, logout.

- **Step 3 (Auth)**: bcrypt hashing, register/login helpers, username/password validation, Streamlit session.

- **Step 2 (SQLite + repositories)**: 9 tables with user_id on all user-owned rows, FK cascades, 8 CRUD/isolation tests.

- **Step 1 (Scaffold)**: git, requirements.txt, .env.example, .gitignore, folder structure, venv (Python 3.14.7).

### Final stats

- **Tests**: 51 passing (DB, auth, extraction, OCR, chunking, embedding, vector, RAG, LLM, summary, TTS, events, email)
- **Lines of code**: ~3,150 (app + tests)
- **Services**: 11 (extraction, OCR, chunking, embedding, vector, RAG, LLM, summary, TTS, events, email)
- **Pages**: 7 (dashboard, upload, documents, chat, history, summaries, reminders)
- **Database tables**: 9 (users, documents, chunks, conversations, messages, summaries, events, reminders, notification_logs)

### Environment notes

- **Ollama**: installed, qwen2.5:3b-instruct pulled, works on CPU (~7s first load)
- **Tesseract**: system package (5.5.3)
- **espeak-ng**: installed (1.52.0) — TTS works
- **Python**: 3.14.7 via mise — all deps have cp314 wheels
- **RAM**: ~4 GB free; models load lazily, no OOM in testing

### Security

- All user data isolated by user_id (SQL FK + Chroma metadata filter)
- Passwords bcrypt-hashed
- Secrets in .env (never committed)
- No hardcoded credentials

### What's NOT built (explicitly out of scope per prompt)

- Neo4j / knowledge graph
- WhatsApp (Google Calendar OAuth sync was added in Phase 6)
- PostgreSQL / Docker
- Background scheduler (uses on-demand button)
- Audio/video input

### To run

```bash
cd MemoryNest
source .venv/bin/activate
streamlit run app/main.py
# Open http://localhost:8501
```