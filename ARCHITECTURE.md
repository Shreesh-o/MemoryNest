# MemoryNest — Architecture Overview

Simple reference for making change/remove decisions.

---

## 1. High-Level Flow

```
User → Streamlit UI (7 pages)
         ↓
    Auth (bcrypt + session)
         ↓
    Services (11 modules)
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
│   ├── main.py              # Entry point, auth gate, navigation
│   ├── pages/               # 7 UI pages
│   │   ├── dashboard.py     # Stats, deadlines, reminders
│   │   ├── upload.py        # File picker → processing pipeline
│   │   ├── documents.py     # List, preview, delete docs
│   │   ├── chat.py          # RAG Q&A with citations
│   │   ├── history.py       # Conversation list, search, load
│   │   ├── summaries.py     # Generate/play summaries
│   │   └── reminders.py     # Extract events, confirm, email
│   ├── services/            # Business logic (12 modules)
│   │   ├── extraction_service.py   # PDF/DOCX/TXT + OCR router
│   │   ├── ocr_service.py          # Tesseract wrapper
│   │   ├── chunking_service.py     # Sentence-aware chunks
│   │   ├── embedding_service.py    # sentence-transformers
│   │   ├── vector_service.py       # ChromaDB wrapper
│   │   ├── rag_service.py          # Query → embed → retrieve → LLM
│   │   ├── llm_service.py          # Ollama client (+ mock)
│   │   ├── summary_service.py      # Map-reduce summarization
│   │   ├── tts_service.py          # pyttsx3 (offline)
│   │   ├── event_service.py        # Regex + dateparser + LLM fallback
│   │   ├── email_service.py        # SMTP (Gmail app password)
│   │   └── ics_service.py          # .ics calendar export
│   ├── database/            # SQLite layer
│   │   ├── database.py      # Schema + init
│   │   ├── models.py        # Dataclasses
│   │   └── repositories.py  # CRUD per table
│   └── utils/               # Config, security, validators, auth helpers
├── data/                    # Runtime (gitignored)
│   ├── uploads/
│   ├── audio/
│   └── chroma/
├── tests/                   # 51 unit tests
├── requirements.txt
├── .env.example
└── README.md
```

---

## 3. Database Tables (9)

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `users` | Auth | id, username, password_hash, email |
| `documents` | Uploaded files | id, user_id, filename, path, type, status, chunk_count |
| `document_chunks` | Text pieces | id, document_id, user_id, chunk_index, content, chroma_id |
| `conversations` | Chat sessions | id, user_id, title |
| `messages` | Chat history | id, conversation_id, user_id, role, content, sources |
| `summaries` | Doc summaries | id, document_id, user_id, summary_text |
| `events` | Extracted dates | id, user_id, document_id, event_text, event_date, status |
| `reminders` | Scheduled emails | id, user_id, event_id, remind_at, status |
| `notification_logs` | Audit trail | id, user_id, reminder_id, kind, success, detail |

**Security**: Every user-owned row has `user_id` with FK `ON DELETE CASCADE`. Chroma metadata also stores `user_id`; all queries filter on it.

---

## 4. Services (What Each Does)

| Service | Input → Output | Dependencies |
|---------|---------------|--------------|
| `extraction_service` | file_path, type → text | PyMuPDF, python-docx, pytesseract |
| `ocr_service` | image_path → text | Tesseract (system) |
| `chunking_service` | text → List[Chunk] | regex, char-based token estimate |
| `embedding_service` | List[str] → List[vector] | sentence-transformers (all-MiniLM-L6-v2) |
| `vector_service` | add/query/delete chunks | ChromaDB PersistentClient |
| `rag_service` | question → RAGResult(answer, sources) | embedding + vector + llm |
| `llm_service` | prompt → response | Ollama HTTP API (qwen2.5:3b-instruct) |
| `summary_service` | full_text → summary | llm + chunking (map-reduce) |
| `tts_service` | text → .wav path | pyttsx3 (needs espeak-ng) |
| `event_service` | text → List[event] | regex + dateparser + LLM fallback |
| `email_service` | subject, body → (success, detail) | smtplib (Gmail) |
| `ics_service` | events list → .ics bytes | icalendar |

---

## 5. Pages (User-Facing)

| Page | Key Features |
|------|--------------|
| Dashboard | Counts, upcoming deadlines, pending events, due reminders, recent chats |
| Upload | Multi-file, validation, sync processing, status updates |
| Documents | List with preview, delete (cascades to Chroma + chunks) |
| Chat (Ask) | Streaming chat UI, RAG answers with expandable source citations |
| History | Conversation list, keyword search, load/delete |
| Summaries | Pick doc → generate (map-reduce) → view + TTS play |
| Reminders | 3 tabs: Extract from doc / Pending confirm / Scheduled + "Check now" + .ics export |

---

## 6. Config (via `.env`)

```
OLLAMA_HOST, OLLAMA_MODEL
EMBEDDING_MODEL
DB_PATH, CHROMA_DIR, UPLOAD_DIR, AUDIO_DIR
RAG_TOP_K, RAG_MIN_SIMILARITY (0.30), CHUNK_SIZE (450), CHUNK_OVERLAP (50)
EMAIL_HOST, EMAIL_PORT, EMAIL_USERNAME, EMAIL_APP_PASSWORD, RECIPIENT_EMAIL
```

---

## 7. What's Explicitly OUT of Scope (Future Scope)

- Neo4j / Knowledge Graph
- WhatsApp notifications
- **Direct Google Calendar API sync** — .ics file export is implemented for manual import
- PostgreSQL / Docker / docker-compose
- Background scheduler (APScheduler/cron) — uses on-demand button instead
- Audio/video input
- Multi-modal RAG (CLIP for images)

---

## 8. Decision Points for You

| Component | Can Remove? | Impact |
|-----------|-------------|--------|
| TTS (pyttsx3) | Yes | Remove `tts_service.py`, Summaries page "Play" button, `espeak-ng` dep |
| Email reminders | Yes | Remove `email_service.py`, Reminders tab 3, SMTP config |
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

## 9. Minimal Viable Subset (If Cutting Hard)

Keep only:
- `main.py` (auth + nav)
- `upload.py` + `extraction_service.py` (PDF/TXT only)
- `chunking_service.py`
- `embedding_service.py` + `vector_service.py`
- `rag_service.py` + `llm_service.py`
- `chat.py`
- `database/` (users, documents, chunks, conversations, messages)
- SQLite + ChromaDB

Removes: summaries, TTS, events, reminders, email, history, documents page, OCR, DOCX.