# MemoryNest

Personal knowledge management with local RAG. Upload documents (PDF, DOCX, TXT, images), extract text (OCR for images), embed with sentence-transformers, store in ChromaDB, and ask natural-language questions answered by a local Ollama LLM with source citations.

## Features

- **Document ingestion**: PDF (PyMuPDF), DOCX (python-docx), TXT, images (Tesseract OCR)
- **Chunking**: sentence-aware, ~450 tokens with ~50 token overlap
- **Embeddings**: all-MiniLM-L6-v2 via sentence-transformers (CPU)
- **Vector DB**: ChromaDB local persistent mode
- **RAG**: top-5 retrieval, similarity threshold gate, LLM answers with citations
- **Local LLM**: Ollama with qwen2.5:3b-instruct (or llama3.2:3b)
- **Conversation history**: per-user, searchable
- **Summaries**: map-reduce for long documents
- **TTS**: offline pyttsx3 (needs espeak-ng)
- **Event extraction**: regex + dateparser, LLM fallback
- **Email reminders**: Gmail SMTP with app password, on-demand "check" button
- **Auth**: username/password with bcrypt, Streamlit session state

## Quick Start

### Prerequisites (Arch/Omarchy)

```bash
# System packages
sudo pacman -S tesseract tesseract-data-eng espeak-ng

# Ollama (if not installed)
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull qwen2.5:3b-instruct  # or llama3.2:3b
```

### Install

```bash
git clone <this-repo>
cd MemoryNest
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your email credentials (optional, for reminders)
```

### Run

```bash
streamlit run app/main.py
```

Open http://localhost:8501. Register an account, upload documents, then ask questions on the **Ask (RAG)** page.

## Configuration

All settings via `.env` (copy from `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `qwen2.5:3b-instruct` | Model to use |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformers model |
| `DB_PATH` | `data/memorynest.db` | SQLite database |
| `CHROMA_DIR` | `data/chroma` | ChromaDB persistence |
| `UPLOAD_DIR` | `data/uploads` | Stored uploads |
| `AUDIO_DIR` | `data/audio` | TTS output |
| `RAG_TOP_K` | `5` | Retrieval count |
| `RAG_MIN_SIMILARITY` | `0.30` | Min cosine similarity to answer |
| `CHUNK_SIZE` | `450` | Target tokens per chunk |
| `CHUNK_OVERLAP` | `50` | Overlap tokens |
| `EMAIL_HOST` | `smtp.gmail.com` | SMTP host |
| `EMAIL_PORT` | `587` | SMTP port |
| `EMAIL_USERNAME` | | Gmail address |
| `EMAIL_APP_PASSWORD` | | Gmail app password |
| `RECIPIENT_EMAIL` | | Where reminders are sent |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Frontend                        │
│  ┌─────────┬─────────┬─────────┬─────────┬────────────────┐ │
│  │Dashboard│ Upload  │Documents│  Ask    │ History/       │ │
│  │         │         │         │ (RAG)   │ Summaries/     │ │
│  │         │         │         │         │ Reminders      │ │
│  └────┬────┴────┬────┴────┬────┴────┬────┴────────┬──────┘ │
└───────┼─────────┼─────────┼─────────┼─────────────┼────────┘
        │         │         │         │             │
        ▼         ▼         ▼         ▼             ▼
┌─────────────────────────────────────────────────────────────┐
│                      Service Layer                           │
│  ┌──────────┐ ┌─────────┐ ┌──────────┐ ┌────────────────┐  │
│  │Extract   │ │Chunking │ │Embedding │ │Vector (Chroma) │  │
│  │(PDF/DOCX│ │(sentence│ │(MiniLM)  │ │(cosine, user_id)│  │
│  │ TXT/OCR)│ │ aware)  │ │          │ │                │  │
│  └────┬─────┘ └────┬────┘ └────┬─────┘ └───────┬────────┘  │
│       │            │           │               │           │
│       ▼            ▼           ▼               ▼           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                    RAG Pipeline                        │  │
│  │  query → embed → retrieve → threshold → LLM → answer  │  │
│  └──────────────────────────────────────────────────────┘  │
│       │                    │                    │           │
│       ▼                    ▼                    ▼           │
│  ┌──────────┐        ┌──────────┐         ┌──────────┐     │
│  │Summary   │        │  Event   │         │  Email   │     │
│  │(map-red) │        │ extraction│        │ reminders│     │
│  └──────────┘        └──────────┘         └──────────┘     │
└─────────────────────────────────────────────────────────────┘
        │                    │                    │
        ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                      Storage Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  SQLite      │  │  ChromaDB    │  │  Filesystem      │   │
│  │  (metadata,  │  │  (vectors,   │  │  (uploads/,      │   │
│  │   chunks,    │  │   user_id    │  │   audio/)        │   │
│  │   events,    │  │   filter)    │  │                  │   │
│  │   reminders) │  │              │  │                  │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

Security: Every user's data is isolated by `user_id` — all SQL tables and Chroma metadata carry `user_id`, and every query filters on it.

## Project Structure

```
memorynest/
├── app/
│   ├── main.py              # Streamlit entry, auth gate, navigation
│   ├── pages/               # 7 pages: dashboard, upload, documents, chat, history, summaries, reminders
│   ├── services/            # Core logic: extraction, OCR, chunking, embedding, vector, RAG, LLM, summary, TTS, events, email
│   ├── database/            # SQLite schema, models, repositories
│   └── utils/               # Config, security (bcrypt), validators, auth helpers
├── data/                    # Runtime data (gitignored)
├── tests/                   # pytest unit tests (50+)
├── requirements.txt
├── .env.example
└── README.md
```

## Testing

```bash
pytest tests/ -q
# 50 tests covering: DB CRUD, auth, extraction, OCR, chunking, embeddings, vector, RAG, summary, TTS, events, email
```

## Future Scope

These features are explicitly **not implemented** in this build but are designed for:

- **Knowledge Graph (Neo4j)**: Entities/relationships extracted from documents, stored in Neo4j alongside vectors. Would enable graph-RAG traversals (e.g., "what projects is person X involved in?"). The current `Event` table is a lightweight precursor — could be expanded to a full entity/relation store.
- **WhatsApp notifications**: Replace/supplement email with WhatsApp Business API or a self-hosted bridge (e.g., whatsapp-web.js). Requires external service integration.
- **Google Calendar sync**: Two-way sync of confirmed events/reminders. Needs OAuth flow and Calendar API.
- **PostgreSQL**: Replace SQLite for multi-user concurrency and horizontal scaling. Current schema is portable.
- **Docker/Compose**: Containerize Ollama, Chroma, and the app for reproducible deployment. Current design is single-process + local services.
- **Background scheduler**: APScheduler/cron for automatic reminder checks. Current MVP uses an on-demand button.
- **Audio/video input**: Not planned — text/image only.
- **Multi-modal RAG**: Image embeddings (CLIP) alongside text for visual search.

## License

MIT