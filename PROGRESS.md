# MemoryNest — Build Progress

Log of the autonomous build. Newest entries first.

## 2026-09-21

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

- **Tests**: 50 passing (DB, auth, extraction, OCR, chunking, embedding, vector, RAG, LLM, summary, TTS, events, email)
- **Lines of code**: ~3,150 (app + tests)
- **Services**: 11 (extraction, OCR, chunking, embedding, vector, RAG, LLM, summary, TTS, events, email)
- **Pages**: 7 (dashboard, upload, documents, chat, history, summaries, reminders)
- **Database tables**: 9 (users, documents, chunks, conversations, messages, summaries, events, reminders, notification_logs)

### Environment notes

- **Ollama**: installed, qwen2.5:3b-instruct pulled, works on CPU (~7s first load)
- **Tesseract**: system package (5.5.3)
- **espeak-ng**: NOT installed (sudo password required) — TTS logs install hint, gracefully returns None
- **Python**: 3.14.7 via mise — all deps have cp314 wheels
- **RAM**: ~4 GB free; models load lazily, no OOM in testing

### Security

- All user data isolated by user_id (SQL FK + Chroma metadata filter)
- Passwords bcrypt-hashed
- Secrets in .env (never committed)
- No hardcoded credentials

### What's NOT built (explicitly out of scope per prompt)

- Neo4j / knowledge graph
- WhatsApp / Google Calendar
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