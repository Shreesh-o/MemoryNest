# MemoryNest Spec

Objectives (college project):
1. Centralized platform for storing personal documents and images (per-user isolation).
2. Extract information from PDF, DOCX, and scanned files using OCR and document processing.
3. Semantic search and RAG question answering with source citations via natural-language queries.
4. Generate text and audio summaries of stored information (offline piper, online edge-tts, espeak-ng).
5. Identify important dates and deadlines and provide calendar reminders (.ics export, email notifications, and Google Calendar sync).

Requirements:
- Uploads are validated (real file type, size limit, safe filenames) and duplicates are skipped per user.
- A failed upload leaves no partial data (SQLite rows, vectors, files) and is marked "error".
- Answers come only from the user's own documents; low-similarity questions are refused.
- The LLM must never silently fake answers: if Ollama is down, show a clear error.
- Reminders default to the `Asia/Kolkata` timezone; past dates are ignored.
- Reminders can be exported to `.ics`, sent via email, or synchronized to user's Google Calendar account via OAuth 2.0.
- Interactive month calendar provides visual overview of pending events, scheduled reminders, and sync status.
- Tests never touch the real `data/` folder.

Out of scope:
- Neo4j knowledge graph
- WhatsApp notifications
- Background daemon scheduler (on-demand checks and event-driven updates used)
- Multi-modal CLIP embeddings / video processing
