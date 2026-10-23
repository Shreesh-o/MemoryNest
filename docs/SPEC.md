# MemoryNest Spec

Objectives (college project):
1. Centralized platform for storing personal documents and images (per-user isolation).
2. Extract information from PDF, DOCX, and scanned files using OCR and document processing.
3. Semantic search and RAG question answering with source citations via natural-language queries.
4. Scoped document chat allowing questions to be targeted to specific subsets of documents.
5. In-browser document inspection via dual-mode viewer (rendered PDF/DOCX-HTML/image and clean extracted text).
6. Document relationship discovery via Document Map (embedding cosine similarity and TF-IDF shared terms).
7. Generate text and audio summaries of stored information (offline piper, online edge-tts, espeak-ng).
8. Identify important dates and deadlines and provide calendar reminders (.ics export, email notifications, and Google Calendar OAuth sync).

Requirements:
- Uploads are validated (real file type, size limit, safe filenames) and duplicates are skipped per user.
- A failed upload leaves no partial data (SQLite rows, vectors, files) and is marked "error".
- Answers come only from the user's own documents; low-similarity questions are refused.
- Scoped chat requests validate document ownership and state, returning generic 404 for unknown/foreign documents.
- The LLM must never silently fake answers: if Ollama is down, show a clear error.
- Document Map maintains eventual consistency with automatic rebuilds on upload, delete, and retry.
- Document file streaming enforces strict security headers (`X-Content-Type-Options: nosniff`, `Content-Security-Policy: sandbox`).
- Reminders default to the `Asia/Kolkata` timezone; past dates are ignored.
- Reminders can be exported to `.ics`, sent via email, or synchronized to user's Google Calendar account via OAuth 2.0.
- Interactive month calendar provides visual overview of pending events, scheduled reminders, and sync status.
- Frontend: Responsive Next.js 16 App Router interface featuring an archival "Evidence Chamber" marketing landing page, full keyboard accessibility, and light/dark theme support.
- Tests never touch the real `data/` folder; comprehensive test suite (304 passing tests) guarantees isolation and correctness.

Out of scope:
- Neo4j knowledge graph
- WhatsApp notifications
- Background daemon scheduler (on-demand checks and event-driven updates used)
- Multi-modal CLIP embeddings / video processing
