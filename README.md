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
- Event extraction: regex + dateparser, LLM fallback; .ics export for confirmed events
- Email reminders: Gmail SMTP with app password, confirmation emails sent to user's address upon event confirmation (with email_status), due reminders delivered to user address, on-demand "check" button, user email management with format validation and Reminders page editor
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

## Future Scope

- Knowledge Graph (Neo4j): entities/relations extracted from documents, graph-RAX traversals
- WhatsApp notifications: replace/supplement email with WhatsApp Business API
- Google Calendar sync: two-way sync via Calendar API (currently .ics export only)
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
| `E2E_BASE_URL` | `http://127.0.0.1:3000` | E2E test frontend URL |
| `E2E_API_URL` | `http://127.0.0.1:8000` | E2E test API URL |

### Frontend Tech Stack

- **Frontend**: Next.js 16 (App Router, Turbopack)
- **UI**: shadcn/ui (Base UI), Tailwind CSS, lucide-react
- **State**: TanStack React Query, Sonner (toasts)
- **Testing**: Playwright (E2E)

## Screenshots

![Screenshots](docs/screenshots/)

## License

MIT
