# MemoryNest — Architecture Overview

Simple reference for making change/remove decisions.

---

## 1. High-Level Flow

```
User → Next.js Web UI (:3000)   [or Streamlit UI :8501]
             ↓ /api/* rewrites
        FastAPI API (:8000)
             ↓
        Auth (bcrypt + JWT cookie)
             ↓
        Services (24 modules)
             ↓
    ┌─────────────────────────────────────┐
    │  SQLite (metadata, users, chunks)   │
    │  ChromaDB (vectors, user_id filter) │
    │  Filesystem (uploads/, audio/)      │
    └─────────────────────────────────────┘
```

---

## 2. Directory Structure

```
memorynest/
├── app/
│   ├── main.py              # Streamlit entry point, auth gate, navigation
│   ├── api/                 # FastAPI REST API layer
│   │   ├── main.py          # App factory, CORS, exception handlers
│   │   ├── deps.py          # Dependency injection (get_current_user)
│   │   ├── schemas.py       # Pydantic request & response schemas
│   │   └── routers/         # API endpoints
│   │       ├── auth.py      # /api/auth/register, /login, /me, /logout, PATCH /me/email
│   │       ├── chat.py      # /api/chat, /api/conversations
│   │       ├── dashboard.py # /api/dashboard
│   │       ├── documents.py # /api/documents/upload, /retry, /file, /content, /html
│   │       ├── google.py    # /api/google/status, /connect, /callback, /disconnect
│   │       ├── health.py    # /api/health (ollama, mock_llm, email_configured)
│   │       ├── reminders.py # /api/events, /api/reminders, /api/reminders/{id}/sync, /calendar.ics, /calendar/items
│   │       ├── search.py    # /api/search
│   │       ├── summaries.py # /api/documents/{id}/summary, /audio
│   │       └── links.py     # /api/graph, /api/documents/{id}/related, /api/graph/refresh
│   ├── pages/               # 7 Streamlit UI pages
│   ├── services/            # Business logic (24 modules)
│   │   ├── auth_service.py         # User registration, login, email updates
│   │   ├── calendar_service.py     # Calendar items aggregation & range validation
│   │   ├── chat_service.py         # Conversation sessions & query routing
│   │   ├── chunking_service.py     # Sentence-aware chunks
│   │   ├── dashboard_service.py    # Aggregate stats, deadlines, recent activity
│   │   ├── document_service.py     # Doc listing, preview, cascading deletion
│   │   ├── email_service.py        # SMTP (Gmail app password / user recipient)
│   │   ├── embedding_service.py    # sentence-transformers (all-MiniLM-L6-v2)
│   │   ├── event_service.py        # Regex + dateparser + LLM fallback
│   │   ├── extraction_service.py   # PDF/DOCX/TXT + OCR router
│   │   ├── google_auth_service.py  # Google OAuth flow, token encryption, Calendar client
│   │   ├── google_calendar_service.py # Google Calendar event create, update, delete
│   │   ├── ics_service.py          # .ics calendar export
│   │   ├── ingest_service.py       # Upload pipeline (extract, chunk, embed, events)
│   │   ├── llm_service.py          # Ollama client (+ mock)
│   │   ├── link_service.py         # Document Map: embedding similarity + TF-IDF shared terms
│   │   ├── ocr_service.py          # Tesseract wrapper
│   │   ├── rag_service.py          # Query → embed → retrieve → LLM
│   │   ├── reminder_flow_service.py# Reminders flow, cancellation, due check, sync
│   │   ├── search_service.py       # Vector & text search
│   │   ├── summary_flow_service.py # Summarization & audio synthesis flow
│   │   ├── summary_service.py      # Map-reduce summarization
│   │   ├── text_cache_service.py   # Extracted text/HTML cache (disk, invalidated on retry/delete)
│   │   └── tts_service.py          # piper/edge/espeak/pyttsx3 TTS
│   ├── database/            # SQLite layer
│   │   ├── database.py      # Schema + init + migrations
│   │   ├── models.py        # Dataclasses
│   │   └── repositories.py  # CRUD per table
│   └── utils/               # Config, security, validators, auth helpers
├── web/                     # Next.js 16 frontend (Base UI, Tailwind CSS)
│   ├── src/app/             # App Router pages ((auth), (app) routes)
│   ├── src/components/ui/   # shadcn / Base UI components
│   └── src/lib/api.ts       # Typed client API requests
├── scripts/
│   ├── dev.sh               # Single-command runner (preflight, Ollama, API, web)
│   ├── api_check.sh         # Endpoint verification script
│   └── repair.py            # SQLite/Chroma consistency checker
├── data/                    # Runtime (gitignored)
│   ├── uploads/
│   ├── audio/
│   ├── chroma/
│   └── text_cache/          # Cached extracted text & DOCX HTML
├── tests/                   # 271 passing unit and API tests
├── requirements.txt
├── .env.example
└── README.md
```

---

## 3. Database Tables (10)

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `users` | Auth | id, username, password_hash, email |
| `documents` | Uploaded files | id, user_id, filename, stored_path, file_type, status, chunk_count, file_hash |
| `document_chunks` | Text pieces | id, document_id, user_id, chunk_index, content, chroma_id |
| `conversations` | Chat sessions | id, user_id, title |
| `messages` | Chat history | id, conversation_id, user_id, role, content, sources |
| `summaries` | Doc summaries | id, document_id, user_id, summary_text |
| `events` | Extracted dates | id, user_id, document_id, event_text, event_date, raw_date, status |
| `reminders` | Scheduled reminders & sync | id, user_id, event_id, remind_at, channel, subject, body, status, sent_at, google_event_id, sync_status, sync_error |
| `notification_logs` | Audit trail | id, user_id, reminder_id, kind, success, detail |
| `google_connections` | Google OAuth | id, user_id (UNIQUE), google_email, refresh_token_encrypted, scope, connected_at |
| `document_links` | Document Map (related docs) | id, user_id, doc_a, doc_b, score, shared_terms, created_at |

**Security**: Every user-owned row has `user_id` with FK `ON DELETE CASCADE`. Chroma metadata also stores `user_id`; all queries filter on it.

---

## 4. Services (What Each Does)

| Service | Input → Output | Dependencies |
|---------|---------------|--------------|
| `auth_service` | username, password, email → User, token | bcrypt, JWT, repositories |
| `calendar_service` | user_id, start, end → List[CalendarItem] | sqlite queries (events & reminders) |
| `chat_service` | question, conversation_id → answer, sources | rag_service, repositories |
| `chunking_service` | text → List[Chunk] | regex, char-based token estimate |
| `dashboard_service` | user_id → stats, deadlines, activity | repositories |
| `document_service` | user_id, doc_id → docs, cascade delete | repositories, vector_service, filesystem |
| `email_service` | subject, body, to_address → (success, detail) | smtplib (Gmail / user recipient with legacy fallback) |
| `embedding_service` | List[str] → List[vector] | sentence-transformers (all-MiniLM-L6-v2) |
| `event_service` | text → List[event] | regex + dateparser + LLM fallback |
| `extraction_service` | file_path, type → text | PyMuPDF, python-docx, pytesseract |
| `google_auth_service` | user_id, OAuth flow, tokens → status, auth_url, calendar_client | google-auth, google-auth-oauthlib, google-api-python-client, cryptography (Fernet) |
| `google_calendar_service` | user_id, event, reminder → google_event_id (create/update/delete) | google-api-python-client, pytz |
| `ics_service` | events list → .ics bytes | icalendar, pytz |
| `ingest_service` | file, user_id → Document, chunks, events | extraction, chunking, embedding, vector, event |
| `llm_service` | prompt → response | Ollama HTTP API (qwen2.5:3b-instruct) |
| `ocr_service` | image_path → text | Tesseract (system) |
| `rag_service` | question → RAGResult(answer, sources) | embedding + vector + llm |
| `reminder_flow_service` | confirm/cancel/due check/sync → status, reminders | email_service, google_calendar_service, repositories |
| `search_service` | query, user_id → search results | vector_service, repositories |
| `summary_flow_service` | doc_id, user_id, engine → summary, audio_url | summary_service, tts_service, repositories |
| `summary_service` | full_text → summary | llm + chunking (map-reduce) |
| `tts_service` | text, engine → .wav path, engine_name | piper (neural offline) / edge-tts (online neural, ffmpeg) / espeak-ng / pyttsx3 |
| `link_service` | user_id → document links | embedding_service, vector_service, repositories |

---

## 5. Pages (User-Facing)

| Page | Key Features |
|------|--------------|
| Dashboard | Counts, upcoming deadlines, pending events, due reminders, recent chats |
| Upload | Multi-file, validation, duplicate check (SHA-256), sync processing, status updates |
| Documents | List with preview, chunk & event counts, delete (cascades to Chroma + chunks) |
| Chat (Ask) | Streaming chat UI, RAG answers with citations, source snippets, conversation history |
| History | Conversation list, keyword search, load conversation, delete thread |
| Summaries | Pick doc → generate (map-reduce/direct) → view + TTS audio synthesis with engine badge (edge/piper/espeak) + audio download |
| Reminders | Month calendar view + Google Calendar card (connect/disconnect/status) + sync status badges with retry + 3 tabs (Pending/Scheduled/All) + email management card + combined toast confirmation + secondary .ics export |
| Document Viewer | Full document view: Original tab (PDF iframe, image zoom, DOCX rendered HTML, TXT) + Extracted text tab (search, highlight, copy, OCR notice). Header with actions: Download, Delete, Summarize, Extract events, Ask about document. |

---

## 6. New Document Viewer Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/documents/{doc_id}/file` | Stream original file with correct Content-Type. `Content-Disposition: inline` (or `attachment` with `?download=1`). Security: path traversal protection, `X-Content-Type-Options: nosniff`, `Content-Security-Policy: sandbox`. |
| `GET /api/documents/{doc_id}/content` | Returns `{text, char_count, truncated, file_type}`. Re-runs extraction on stored file, caches result on disk (`data/text_cache/<doc_id>.txt`), invalidated on retry/delete. Caps at ~500k chars. Normalizes whitespace, fixes hyphenated line breaks. |
| `GET /api/documents/{doc_id}/html` | DOCX only (400 for other types). Converts with mammoth, sanitizes with nh3 (allows headings, p, lists, tables, strong/em, links with rel="noopener noreferrer", images as data URIs with size cap). Cached like text. |

---

## 7. Document Map Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/graph?min_score=0.45` | Get the full Document Map graph. Returns `{nodes: [...], edges: [...], unlinked: [...]}`. Nodes are documents with ≥1 edge above min_score; unlinked are documents with no edges above threshold. Edges are stored links with score ≥ min_score. min_score defaults to LINK_MIN_SIMILARITY (0.45), validated between 0.20–0.95. |
| `GET /api/documents/{doc_id}/related?min_score=...` | Get up to 5 related documents for a specific document. Returns `[{id, filename, file_type, score, shared_terms}]` sorted by score descending. 404 if document not found or not owned by user. |
| `POST /api/graph/refresh` | Rebuild the Document Map for the current user. Computes embedding similarity between all ready documents using LINK_STORE_MIN_SIMILARITY (0.30) as storage floor, keeping top LINK_MAX_PER_DOC neighbors per doc. Returns `{documents, edges}` counts. |

**Storage vs. Read Thresholds**: Links are stored with a low floor (LINK_STORE_MIN_SIMILARITY=0.30) to capture more relationships, but filtered at read time using LINK_MIN_SIMILARITY=0.45 (configurable via min_score query param). This allows users to explore weaker connections without re-computing.

---

## 8. Config (via `.env`)
```
OLLAMA_HOST, OLLAMA_MODEL, EMBEDDING_MODEL, DB_PATH, CHROMA_DIR, UPLOAD_DIR, AUDIO_DIR
RAG_TOP_K, RAG_MIN_SIMILARITY, CHUNK_SIZE, CHUNK_OVERLAP
EMAIL_HOST, EMAIL_PORT, EMAIL_USERNAME, EMAIL_APP_PASSWORD, RECIPIENT_EMAIL
TTS_ENGINE, TTS_VOICE
GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI, FRONTEND_URL, TOKEN_ENCRYPTION_KEY
LINK_MIN_SIMILARITY=0.45, LINK_STORE_MIN_SIMILARITY=0.30, LINK_MAX_PER_DOC=3
```

---

## 9. Document Map Auto-Rebuild Behavior

The Document Map is kept fresh automatically:

- **After successful document upload**: Rebuilds once at the end of the multi-file upload request (if any document was successfully processed).
- **After document deletion**: Rebuilds immediately after the document is deleted.
- **After retry extraction**: Rebuilds after a failed document is successfully reprocessed.

All rebuilds run in try/except blocks — if the rebuild fails, the error is logged but the main operation (upload, delete, retry) continues unaffected. This ensures the Document Map is eventually consistent without blocking user actions.

For manual rebuilds, use `POST /api/graph/refresh` or run `scripts/rebuild_links.py` (rebuilds for all users).

## 9. What's Explicitly OUT of Scope

- Knowledge Graph (Neo4j)
- WhatsApp notifications
- PostgreSQL / Docker / docker-compose
- Background daemon scheduler (APScheduler/cron) — uses on-demand button and API triggers
- Audio/video input
- Multi-modal RAG (CLIP for images)

---

## 10. Decision Points for You

| Component | Can Remove? | Impact |
|-----------|-------------|--------|
| TTS (piper/edge/espeak/pyttsx3) | Yes | Remove `tts_service.py`, Summaries page "Play" button, audio output |
| Email reminders | Yes | Remove `email_service.py`, Reminders tab 3, SMTP config |
| Google Calendar sync | Yes | Remove `google_auth_service.py`, `google_calendar_service.py`, `routers/google.py`, Google card |
| Event extraction | Yes | Remove `event_service.py`, Reminders tab 1+2, LLM fallback call |
| Summaries (map-reduce) | Yes | Remove `summary_service.py`, Summaries page |
| History page | Yes | Remove `history.py`, message search |
| Documents page | Yes | Remove `documents.py` (keep upload + delete via API) |
| OCR (images) | Yes | Remove `ocr_service.py`, pytesseract dep, image upload support |
| DOCX support | Yes | Remove python-docx dep, handle only PDF/TXT/images |
| Multi-user | **No** | Core security model — user_id everywhere |
| RAG threshold (0.30) | Tunable | Lower = more answers, more hallucinations |
| Chunk size (450/50) | Tunable | Larger = fewer chunks, less precision |

---

## 11. Minimal Viable Subset (If Cutting Hard)

Keep only:
- `main.py` (auth + nav)
- `upload.py` + `extraction_service.py` (PDF/TXT only)
- `chunking_service.py`
- `embedding_service.py` + `vector_service.py`
- `rag_service.py` + `llm_service.py`
- `chat.py`
- `database/` (users, documents, chunks, conversations, messages)
- `utils/` (config, bcrypt, validators, auth helpers)

Removes: summaries, TTS, events, reminders, email, google calendar, history, documents page, OCR, DOCX.

---

## 12. Future Scope

- Knowledge Graph (Neo4j): entities/relations extracted from documents, graph-RAG traversals
- WhatsApp notifications: replace/supplement email with WhatsApp Business API
- Google Calendar two-way webhooks: listen for remote Google Calendar deletes/moves
- PostgreSQL: replace SQLite for multi-user concurrency and horizontal scaling
- Docker/Compose: containerize Ollama, Chroma, and the app for reproducible deployment
- Background scheduler: APScheduler/cron for automatic reminder checks
- Audio/video input: not planned — text/image only
- Multi-modal RAG: CLIP embeddings alongside text for visual search
