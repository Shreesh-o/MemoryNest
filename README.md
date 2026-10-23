# MemoryNest — Personal Knowledge Manager

MemoryNest is a local, privacy-first web app for storing, searching, and summarizing personal documents and images. Upload PDFs, DOCX files, TXT files, and images (via OCR) — all processing happens offline on your machine. Ask natural-language questions via RAG, generate audio summaries, and extract calendar events with email reminders.

## Objectives

1. **Centralized storage** — Upload and index PDFs, DOCX, TXT, and images (OCR) in a SQLite + ChromaDB-backed portal, each user isolated by `user_id`.
2. **Extraction from PDF/DOCX/scanned files** — PyMuPDF, python-docx, and Tesseract OCR extract text from all supported types; chunking splits text into ~450-character segments with 50-character overlap.
3. **Semantic search and RAG question answering** — Sentence-transformers embed queries/retrieved chunks; a local Ollama LLM answers with citations; a similarity gate refuses low-confidence answers.
4. **Text and audio summaries** — Map-reduce summarization of long documents; TTS (edge-tts or espeak-ng) renders summaries as WAV; the Summaries page adds a download button.
5. **Important dates/deadlines with calendar reminders** — Regex + dateparser extract events from any document text; confirmed events export to .ics; on-demand "Check now" button triggers email via Gmail SMTP (app password) or local calendar .ics download.

## Features

- Document ingestion: PDF (PyMuPDF), DOCX (python-docx), TXT, images (Tesseract OCR)
- Chunking: sentence-aware, ~450 characters with 50-character overlap
- Embeddings: all-MiniLM-L6-v2 via sentence-transformers (CPU-only)
- Vector DB: ChromaDB local persistent mode, user-id filtered
- RAG: top-5 retrieval, similarity threshold gate, LLM answers with citations
- **Scoped Document Chat**: Ask questions across all documents or scope retrieval to a selected subset of ready documents (`POST /api/chat` with `document_ids`); selection status persisted in message history and visible in the chat UI
- Local LLM: Ollama with qwen2.5:3b-instruct (3B, CPU-compatible)
- Conversation history: per-user, searchable, per-session
- Summaries: map-reduce for long documents; TTS renders audio; download button
- Event extraction: regex + dateparser, LLM fallback; .ics export for confirmed events; month calendar view on the Reminders page
- Email reminders: Gmail SMTP with app password, confirmation emails sent to user's address upon event confirmation (with email_status), due reminders delivered to user address, on-demand "check" button, user email management with format validation and Reminders page editor
- Google Calendar Integration: Per-user Google account connect and disconnect via OAuth 2.0 with offline access, CSRF state protection, encrypted refresh token storage (Fernet), automatic event creation upon confirmation, event deletion upon cancellation, manual retry sync, and status indicators in web calendar and reminders
- **Document Map**: Shows related documents by topic similarity (cosine similarity of mean chunk embeddings). Links are stored with a low floor (LINK_STORE_MIN_SIMILARITY=0.30) and filtered at read time (LINK_MIN_SIMILARITY=0.45 default), keeping top 3 neighbors per doc. Computes shared terms via TF-IDF for readable link labels. Rebuild on demand via API or auto-rebuild after upload/delete/retry.
- Auth: username/password with bcrypt, JWT cookies (FastAPI) & Streamlit session state, user profile with email management (`PATCH /api/auth/me/email`)

## Tech Stack

- **Web Frontend**: Next.js 16 (App Router, Turbopack, Tailwind CSS, Base UI / shadcn, TanStack React Query)
- **Legacy UI**: Streamlit (Python)
- **Backend API**: FastAPI (REST endpoints, JWT auth, Pydantic schemas)
- **Storage & Vector DB**: SQLite (metadata), ChromaDB (embeddings, user-isolated)
- **LLM**: Ollama (`qwen2.5:3b-instruct`, 3B local model)
- **Embeddings**: sentence-transformers (`all-MiniLM-L6-v2`)
- **OCR**: Tesseract (via pytesseract)
- **TTS**: edge-tts (online, MP3→WAV w/ ffmpeg) / espeak-ng (offline) / piper
- **Email**: smtplib (Gmail SMTP, app password)

## Quick Start (Linux)

### 1. Prerequisites & Dependencies

```bash
# System packages
sudo apt-get install tesseract-ocr espeak-ng ffmpeg

# Ollama
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull qwen2.5:3b-instruct

# Python venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Web dependencies (one time)
cd web && npm install && cd ..
```

### 2. Running MemoryNest

Use the unified development runner `scripts/dev.sh` to run preflight checks and launch Ollama, FastAPI (port 8000), and Next.js (port 3000) with hot reload:

```bash
# Start in development mode (hot reload)
bash scripts/dev.sh

# Stop all background services
bash scripts/dev.sh --stop
```

#### Additional Runner Options:
```bash
bash scripts/dev.sh --prod      # Production build + start
bash scripts/dev.sh --fresh     # Run with an isolated temporary empty database
bash scripts/dev.sh --force     # Start even if optional preflight checks warn
```

- **Web App**: http://localhost:3000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **Streamlit (Alternative)**: `streamlit run app/main.py` (http://localhost:8501)

## Voice Options

- **auto** (default): tries `piper` (if local model installed) → `edge-tts` (online neural) → `espeak-ng` (offline) → `pyttsx3`, stopping at the first that works
- **piper**: offline neural TTS using piper-tts (fast, natural voice; looks in `models/piper/` or `TTS_VOICE`)
- **edge**: online natural voice via `edge-tts`; requires internet connection (8s timeout); MP3→WAV conversion with `ffmpeg`; voice `en-IN-NeerjaNeural`
- **espeak-ng**: offline synthesized speech; CLI flags `-s 150 -p 45 -g 4`
- **pyttsx3**: local library fallback

The generated TTS audio displays an engine badge (e.g., `edge`, `piper`, `espeak`) in the web UI.

## Known Limitations

- Processing is synchronous — the UI freezes during extraction/summarization/TTS
- No background scheduler — reminders are on-demand via a "Check now" button
- Requires local Ollama; 3B model (`qwen2.5:3b-instruct`) is the smallest recommended
- Scanned-document OCR quality depends on scan resolution and contrast
- Email reminders need Gmail app password; no other providers configured

## Google Calendar Setup

MemoryNest can automatically push confirmed reminders to your Google Calendar and remove them if cancelled.

### 1. Google Cloud Console Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a new project (e.g. `MemoryNest`).
2. Navigate to **APIs & Services > Library** and enable the **Google Calendar API**.
3. Navigate to **APIs & Services > OAuth consent screen**:
   - Choose User Type (**External** for personal testing).
   - Fill in the required app information.
   - Add the scopes:
     - `https://www.googleapis.com/auth/calendar.events`
     - `https://www.googleapis.com/auth/userinfo.email`
   - In Test Users, add your Google account email address.
4. Navigate to **APIs & Services > Credentials**:
   - Click **Create Credentials > OAuth client ID**.
   - Application type: **Web application**.
   - Name: `MemoryNest Web`.
   - **Authorized redirect URIs**: `http://localhost:8000/api/google/callback` (or your production redirect URI).
   - Save your **Client ID** and **Client Secret**.

### 2. Configure Environment Variables

Generate a Fernet token encryption key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Add the following to your `.env` file:
```env
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/google/callback
FRONTEND_URL=http://localhost:3000
TOKEN_ENCRYPTION_KEY=your-generated-fernet-key
```

### 3. Usage & Lifecycle
- On the **Reminders** page, the **Google Calendar** card displays connection status.
- Click **Connect Google Calendar** to authorize with Google via OAuth 2.0.
- When an event is confirmed, a Google Calendar event is automatically created (`Asia/Kolkata` timezone, title = event text, description = doc name + "Created by MemoryNest", and popup alert matching `remind_at`).
- Cancelling a reminder automatically deletes the event from Google Calendar.
- If sync fails (e.g. temporary network issue), a **Retry** button allows syncing with `POST /api/reminders/{id}/sync`.
- If Google access is revoked (401), the connection is marked disconnected and the user is prompted to reconnect.
- Users without Google Calendar connected can still use the fallback **Download .ics** button.

## Future Scope

- Knowledge Graph (Neo4j): entities/relations extracted from documents, graph-RAG traversals
- WhatsApp notifications: replace/supplement email with WhatsApp Business API
- Two-way Calendar Webhooks: sync modifications made directly in Google Calendar back to MemoryNest
- PostgreSQL: replace SQLite for multi-user concurrency
- Docker/Compose: containerize Ollama, Chroma, and the app
- Background scheduler: APScheduler/cron for automatic reminder checks
- Audio/video input: not planned — text/image only
- Multi-modal RAG (CLIP): image embeddings alongside text for visual search

## Document Map Maintenance

The `scripts/rebuild_links.py` script rebuilds the Document Map for all users. It is safe to run repeatedly and can be run from the project root with the virtual environment activated:

```bash
python scripts/rebuild_links.py
```

This is useful for:
- Initial population after upgrading from a version without Document Map
- Full rebuild after changing similarity thresholds
- Periodic maintenance (can be cron'd)

## Frontend (Next.js)

The web frontend is a separate Next.js app in the `web/` directory.

### Setup

```bash
# Backend API (port 8000)
cd /home/shreesh/MemoryNest
source .venv/bin/activate
export JWT_SECRET=your-secret-key
python -m uvicorn app.api.main:app --port 8000

# Frontend (port 3000)
cd web
npm install
npm run build
npm run start
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET` | (random) | Secret for signing session tokens |
| `DB_PATH` | `data/memorynest.db` | SQLite database path |
| `CHROMA_DIR` | `data/chroma` | ChromaDB storage directory |
| `UPLOAD_DIR` | `data/uploads` | Uploaded files directory |
| `AUDIO_DIR` | `data/audio` | TTS audio output directory |
| `NEXT_PUBLIC_MAX_FILE_MB` | `20` | Max upload file size in MB |
| `GOOGLE_CLIENT_ID` | `""` | Google OAuth 2.0 Web Client ID |
| `GOOGLE_CLIENT_SECRET` | `""` | Google OAuth 2.0 Web Client Secret |
| `GOOGLE_REDIRECT_URI` | `http://localhost:8000/api/google/callback` | OAuth redirect URI handled by backend |
| `FRONTEND_URL` | `http://localhost:3000` | Frontend web URL for OAuth redirects |
| `TOKEN_ENCRYPTION_KEY` | `""` | 32-byte URL-safe base64 Fernet key for encrypted OAuth refresh tokens |
| `LINK_MIN_SIMILARITY` | `0.45` | Minimum cosine similarity for Document Map links (read-time filter) |
| `LINK_STORE_MIN_SIMILARITY` | `0.30` | Minimum cosine similarity for storing links (low floor) |
| `LINK_MAX_PER_DOC` | `3` | Maximum related documents per document in Document Map |
| `E2E_BASE_URL` | `http://127.0.0.1:3000` | E2E test frontend URL |
| `E2E_API_URL` | `http://127.0.0.1:8000` | E2E test API URL |

### Key API Endpoints

- **Authentication**:
  - `POST /api/auth/register` — Create account (`username`, `password`, optional `email`).
  - `POST /api/auth/login` — Authenticate and receive HTTP-only JWT session cookie.
  - `GET /api/auth/me` — Return current authenticated user profile (`id`, `username`, `email`).
  - `POST /api/auth/logout` — Clear session cookie.
  - `PATCH /api/auth/me/email` — Update or clear user email address with validation.
- **Documents**:
  - `POST /api/documents/upload` — Multipart upload (PDF, DOCX, TXT, images) with deduplication and OCR.
  - `GET /api/documents` — List user documents with processing status and chunk counts.
  - `GET /api/documents/{id}` — Get document metadata, chunks, and events.
  - `GET /api/documents/{id}/file` — Stream original file (PDF, DOCX, TXT, images). `?download=1` for attachment.
  - `GET /api/documents/{id}/content` — Get clean extracted text (re-extracted, cached, ~500k char cap, normalized whitespace).
  - `GET /api/documents/{id}/html` — DOCX only: sanitized HTML from mammoth + nh3.
  - `DELETE /api/documents/{id}` — Delete document and cascade delete SQLite rows and Chroma vectors.
  - `POST /api/documents/{id}/retry` — Retry failed document extraction/embedding.
- **Document Map**:
  - `GET /api/graph?min_score=0.45` — Get the full Document Map graph. Returns `{nodes: [...], edges: [...], unlinked: [...]}`. Nodes are documents with ≥1 edge above min_score; unlinked are documents with no edges above threshold. Edges are stored links with score ≥ min_score. min_score defaults to LINK_MIN_SIMILARITY (0.45), validated between 0.20–0.95.
  - `GET /api/documents/{doc_id}/related?min_score=...` — Get up to 5 related documents for a specific document. Returns `[{id, filename, file_type, score, shared_terms}]` sorted by score descending. 404 if document not found or not owned by user.
  - `POST /api/graph/refresh` — Rebuild the Document Map for the current user. Computes embedding similarity between all ready documents using LINK_STORE_MIN_SIMILARITY (0.30) as storage floor, keeping top LINK_MAX_PER_DOC neighbors per doc. Returns `{documents, edges}` counts.
- **Chat & RAG**:
  - `POST /api/chat` — Ask natural-language questions with semantic retrieval and citations.
  - `GET /api/conversations` — List conversation threads.
  - `GET /api/conversations/{id}` — Get conversation message history.
  - `DELETE /api/conversations/{id}` — Delete conversation thread.
- **Summaries**:
  - `POST /api/documents/{id}/summary` — Generate map-reduce or direct summary.
  - `GET /api/documents/{id}/summary` — Retrieve existing summary.
  - `POST /api/documents/{id}/audio` — Synthesize TTS summary audio (`auto`, `edge`, `piper`, `espeak`).
  - `GET /api/documents/{id}/audio` — Download generated summary WAV.
- **Events & Reminders**:
  - `GET /api/events` — List extracted dates and events.
  - `POST /api/events/{id}/confirm` — Schedule reminder, trigger confirmation email, and push to Google Calendar.
  - `DELETE /api/events/{id}` — Discard pending event.
  - `GET /api/reminders` — List reminders (`all`, `scheduled`, or `sent`).
  - `DELETE /api/reminders/{id}` — Cancel reminder, delete Google Calendar event, revert event to pending.
  - `POST /api/reminders/check` — On-demand due reminder email dispatch.
  - `GET /api/reminders/calendar-items` — Month calendar view items with Google sync status.
  - `GET /api/reminders/calendar.ics` — Export confirmed events as standard iCalendar `.ics`.
  - `POST /api/reminders/{id}/sync` — Manually retry syncing reminder to Google Calendar.
- **Google Calendar**:
  - `GET /api/google/status` — Return Google configuration status and connected user email.
  - `POST /api/google/connect` — Initiate OAuth 2.0 flow with CSRF state cookie.
  - `GET /api/google/callback` — Exchange auth code, encrypt refresh token, redirect to UI.
  - `POST /api/google/disconnect` — Revoke Google tokens and remove connection record.
- **System & Dashboard**:
  - `GET /api/dashboard` — Aggregated counts, upcoming deadlines, pending events, recent chats.
  - `GET /api/health` — Service health (Ollama status, mock mode, email configuration).

### Frontend Tech Stack

- **Frontend**: Next.js 16 (App Router, Turbopack)
- **UI**: shadcn/ui (Base UI), Tailwind CSS, lucide-react
- **State**: TanStack React Query, Sonner (toasts)
- **Testing**: Playwright (E2E)

## Screenshots

![Screenshots](docs/screenshots/)

## License

MIT
