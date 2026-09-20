# MASTER PROMPT — MEMORYNEST (LEAN BUILD, AUTONOMOUS OVERNIGHT RUN)

You are acting as a senior Python/AI engineer building a complete working application in this repo, unattended, overnight. I will not be present to answer questions or confirm phases. Your job is to build, test, fix, and commit continuously until the MVP works end-to-end or you hit a genuine blocker (see "STOP CONDITIONS" at the end).

======================================================
0. MACHINE CONTEXT (read first, decides your choices)
======================================================

- OS: Arch-based Linux (Omarchy), Hyprland/Wayland
- CPU: Intel Core Ultra 5 125H (14 cores)
- GPU: Intel Arc iGPU only — NO CUDA, do not assume GPU acceleration
- RAM: ~15GB total
- Package manager: pacman (use `pacman -S` / `yay -S` for system packages, `pip` for Python packages)

All model/library choices below are already picked BECAUSE of this hardware. Do not upgrade to heavier alternatives (bigger LLMs, Neo4j, Docker, Postgres) without a documented reason in PROGRESS.md.

======================================================
1. PROJECT
======================================================

MemoryNest — a personal knowledge management app. User uploads documents (PDF/DOCX/TXT/images), the system extracts text (OCR for images), chunks + embeds it, stores it in a local vector DB, and lets the user ask natural-language questions answered via local RAG (Ollama), with source citations. It also generates summaries, keeps history, extracts dates/events from documents, and emails reminders after user confirmation.

This is the FULL scope for this build. Nothing else. If you're tempted to add WhatsApp, Neo4j, Google Calendar, PostgreSQL, or Docker — don't. They're explicitly future scope (write them into README's "Future Scope" section, don't build them).

======================================================
2. FINALIZED TECH STACK — DO NOT SUBSTITUTE
======================================================

- Language: Python 3.11+
- Frontend: Streamlit
- LLM: Ollama, running locally. Check if Ollama is installed (`ollama --version`); if not, tell me in PROGRESS.md exactly how to install it (do not attempt sudo installs yourself if it requires interactive prompts) and use a stub/mock LLM response so the rest of the pipeline can still be built and tested.
  - Model: pull `qwen2.5:3b-instruct` (or `llama3.2:3b` if that's unavailable) — small enough to run fast on CPU with 15GB RAM. Do NOT pull anything 7B+.
- Embeddings: `sentence-transformers`, model `all-MiniLM-L6-v2` (CPU-only, ~80MB, fast)
- Vector DB: ChromaDB, local persistent mode (`chromadb.PersistentClient`), no server process
- OCR: Tesseract (`pacman -S tesseract tesseract-data-eng`) + `pytesseract`
- PDF: PyMuPDF (`pymupdf`)
- DOCX: `python-docx`
- Database: SQLite (stdlib `sqlite3` or SQLAlchemy — your choice, keep it simple)
- TTS: `pyttsx3` (offline; needs `espeak-ng` — `pacman -S espeak-ng`)
- Email: `smtplib` with Gmail app password, read from `.env` (never hardcode)
- Date/event extraction: `dateparser` + regex first; only fall back to an LLM call if regex finds nothing
- Auth: simple username/password with `bcrypt` hashing + Streamlit session state (no OAuth, no JWT needed for v1)
- Testing: `pytest` for core logic (chunking, extraction, retrieval), manual smoke test for UI

======================================================
3. WHAT TO SKIP (explicitly out of scope for this build)
======================================================

- Neo4j / knowledge graph — future scope only, write one paragraph in README about how it would work
- WhatsApp — future scope only
- Google Calendar — future scope only
- PostgreSQL, Docker, docker-compose — not needed, don't create these files
- A background scheduler process (APScheduler/cron) — instead, add a "Check for reminders" button on the dashboard that runs the check on click
- Audio/video input — never, not even future scope discussion needed beyond one line

======================================================
4. FOLDER STRUCTURE
======================================================

```
memorynest/
├── app/
│   ├── main.py
│   ├── pages/
│   │   ├── dashboard.py
│   │   ├── upload.py
│   │   ├── documents.py
│   │   ├── chat.py
│   │   ├── history.py
│   │   ├── summaries.py
│   │   └── reminders.py
│   ├── services/
│   │   ├── extraction_service.py      # PDF/DOCX/TXT + routes to OCR
│   │   ├── ocr_service.py
│   │   ├── chunking_service.py
│   │   ├── embedding_service.py
│   │   ├── vector_service.py          # Chroma wrapper
│   │   ├── rag_service.py
│   │   ├── llm_service.py             # Ollama wrapper
│   │   ├── summary_service.py
│   │   ├── tts_service.py
│   │   ├── event_service.py           # date/event extraction
│   │   └── email_service.py
│   ├── database/
│   │   ├── database.py
│   │   ├── models.py
│   │   └── repositories.py
│   └── utils/
│       ├── config.py
│       ├── security.py
│       └── validators.py
├── data/
│   ├── uploads/
│   ├── audio/
│   └── chroma/
├── tests/
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
└── PROGRESS.md
```

======================================================
5. DATABASE SCHEMA (SQLite)
======================================================

Tables: `users`, `documents`, `document_chunks`, `conversations`, `messages`, `summaries`, `events`, `reminders`, `notification_logs`. Every document/event/conversation row carries `user_id`; every vector-DB chunk's metadata carries `user_id` too, and every query filters on it — this is a security requirement, not optional.

======================================================
6. RAG BEHAVIOR RULES
======================================================

- Chunk size ~400-500 tokens, ~50 token overlap
- On query: embed question → similarity search top-5 → if best match score is below a reasonable threshold, respond "I couldn't find this information in your stored documents" WITHOUT calling the LLM
- Always show which document/chunk an answer came from
- System prompt to Ollama must explicitly say: answer only from the provided context, say so if the answer isn't in it, do not make anything up

======================================================
7. BUILD ORDER (work through these in sequence, don't skip ahead if one is broken)
======================================================

1. Project scaffold, git init, requirements.txt, .env.example, .gitignore
2. SQLite schema + repositories, unit tests for CRUD
3. Auth (register/login) + Streamlit session handling
4. Streamlit shell: main.py + empty page stubs + nav
5. File upload + validation (type, size) → save to data/uploads, DB row created
6. Text extraction: PDF, DOCX, TXT — unit test each on a sample file you generate
7. OCR pipeline for images — test on a generated sample image with text
8. Chunking service — unit test on sample text
9. Embedding service + Chroma vector service — test insert + retrieve
10. Ollama integration (llm_service.py) — test a basic prompt/response; if Ollama isn't available, build a mock that returns a fixed string so downstream code is testable
11. Full RAG pipeline connecting 9+10, wired into chat.py UI
12. Conversation history — save/load/search
13. Summarization (map-reduce for long docs) + summaries page
14. TTS for summaries
15. Date/event extraction (regex+dateparser first) + confirmation UI on reminders.py
16. Email reminder sending, on-demand "check reminders" button
17. Dashboard: counts, upcoming deadlines, recent activity
18. README with setup instructions, architecture diagram (ASCII is fine), Future Scope section
19. Final smoke test: full flow from register → upload → chat → summary → reminder

After each numbered step: run whatever tests apply, fix failures before moving on, `git add -A && git commit -m "..."` with a clear message, and append one line to PROGRESS.md: what you built, what you tested, what passed/failed, what's still rough.

======================================================
8. HOW TO WORK AUTONOMOUSLY (since no one is watching)
======================================================

- Don't ask questions in chat — if you have to make a judgment call, make the simplest reasonable one, note it in PROGRESS.md, and keep going.
- Write real tests, run them yourself, and don't mark a step done in PROGRESS.md until its tests pass.
- If a step fails and you can't fix it after a few real attempts, don't get stuck in a loop — comment out/stub the broken part, note it clearly as `# TODO: broken, see PROGRESS.md`, and move to the next step so the rest of the app still runs.
- Prefer finishing all 19 steps at reduced quality over perfecting steps 1-5 and never reaching chat/RAG (steps 9-11 are the actual core of the project — protect time for those).
- Use `.env` for all secrets, never commit it, keep `.env.example` updated with every key you add.

======================================================
9. STOP CONDITIONS — genuinely pause and leave a clear note instead of guessing
======================================================

- Anything requiring interactive OAuth consent (not applicable here since Calendar is out of scope — but flag if you find yourself needing any external login flow)
- A Gmail app password or other secret you don't have — stub the function, log clearly what env var is needed
- `pacman`/`yay` install requiring sudo with an interactive password prompt you can't supply
- Anything that would require internet access you don't have (Ollama model pulls, pip installs) — note exactly what failed and why

======================================================
START
======================================================

Begin at step 1. Work straight through. Commit after every step. Keep PROGRESS.md current — that's the first thing I'll read in the morning.
