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
- Local LLM: Ollama with qwen2.5:3b-instruct (3B, CPU-compatible)
- Conversation history: per-user, searchable, per-session
- Summaries: map-reduce for long documents; TTS renders audio; download button
- Event extraction: regex + dateparser, LLM fallback; .ics export for confirmed events; month calendar view on the Reminders page
- Email reminders: Gmail SMTP with app password, confirmation emails sent to user's address upon event confirmation (with email_status), due reminders delivered to user address, on-demand "check" button, user email management with format validation and Reminders page editor
- Google Calendar Integration: Per-user Google account connect and disconnect via OAuth 2.0 with offline access, CSRF state protection, encrypted refresh token storage (Fernet), automatic event creation upon confirmation, event deletion upon cancellation, manual retry sync, and status indicators in web calendar and reminders
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

- **auto** (default): tries edge-tts → espeak-ng → pyttsx3, stopping at the first that works
- **edge**: online via edge-tts; needs internet (10 s timeout); MP3→WAV conversion with ffmpeg; voice `en-IN-NeerjaNeural`
- **espeak-ng**: offline, lower quality (raspy/robotic); CLI flags `-s 150 -g 3 -p 50`
- **pyttsx3**: fallback only (not installed in venv)

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

- Knowledge Graph (Neo4j): entities/relations extracted from documents, graph-RAX traversals
- WhatsApp notifications: replace/supplement email with WhatsApp Business API
- Two-way Calendar Webhooks: sync modifications made directly in Google Calendar back to MemoryNest
- PostgreSQL: replace SQLite for multi-user concurrency
- Docker/Compose: containerize Ollama, Chroma, and the app
- Background scheduler: APScheduler/cron for automatic reminder checks
- Audio/video input: not planned — text/image only
- Multi-modal RCLIP: image embeddings alongside text for visual search

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
| `E2E_BASE_URL` | `http://127.0.0.1:3000` | E2E test frontend URL |
| `E2E_API_URL` | `http://127.0.0.1:8000` | E2E test API URL |

### Key API Endpoints

- **Google Calendar**:
  - `GET /api/google/status` — Returns Google configuration and user connection status with email.
  - `POST /api/google/connect` — Initiates OAuth flow, sets CSRF state cookie, returns Google authorization URL.
  - `GET /api/google/callback` — Handles OAuth redirect, stores encrypted refresh token, redirects to `/reminders?google=connected`.
  - `POST /api/google/disconnect` — Revokes Google tokens and marks connection disconnected.
  - `POST /api/reminders/{id}/sync` — Manually retry syncing a reminder to Google Calendar.
- **Reminders & Events**:
  - `POST /api/events/{id}/confirm` — Confirms an event, sets reminder, creates Google Calendar event (returns `google_status` and `email_status`).
  - `DELETE /api/reminders/{id}` — Cancels reminder, removes from Google Calendar, reverts event to pending.
  - `GET /api/reminders/calendar-items` — Calendar view items including `sync_status`.

### Frontend Tech Stack

- **Frontend**: Next.js 16 (App Router, Turbopack)
- **UI**: shadcn/ui (Base UI), Tailwind CSS, lucide-react
- **State**: TanStack React Query, Sonner (toasts)
- **Testing**: Playwright (E2E)

## Screenshots

![Screenshots](docs/screenshots/)

## License

MIT
