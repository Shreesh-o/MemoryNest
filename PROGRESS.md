# MemoryNest — Build Progress

Log of the autonomous build. Newest entries first.

## 2026-09-21

- **Step 4 (Streamlit shell + auth gate)**: built `app/main.py` with login/register forms,
  session-state auth, logout, and `st.navigation` over 7 pages.
  - Tested: `AppTest` headless run — register flow succeeds, sidebar shows user. PASS.
- **Step 3 (Auth)**: `app/utils/auth.py` (register/login), `app/utils/security.py` (bcrypt).
  - Tested: 7 pytest cases (hash roundtrip, register validation, duplicate, wrong password,
    unknown user). PASS.
- **Step 2 (SQLite schema + repositories)**: `app/database/{database,models,repositories}.py`
  implementing all 9 tables from the spec with `user_id` on every user-owned row and
  FK cascades.
  - Tested: 8 pytest CRUD/isolation/cascade tests. PASS.
  - Fix log: added missing `ON DELETE CASCADE` on several `user_id` columns; stripped an
    extra `message_count` column that broke dataclass mapping.
- **Step 1 (Scaffold)**: git repo, `requirements.txt`, `.env.example`, `.gitignore`,
  folder structure, `.venv` (Python 3.14.7 — all pinned deps have cp314 wheels, verified).

### Environment decisions & notes

- **Ollama**: installed (v0.34.2); pulled `qwen2.5:3b-instruct` (~2 GB). Works on CPU.
- **Tesseract**: installed system-wide (5.5.3).
- **espeak-ng**: NOT installed; `sudo` requires a password (stop-condition in the prompt).
  TTS step (14) will need a workaround — see that entry when reached.
- **Python**: used the system mise Python 3.14.7 instead of installing 3.11/3.12,
  because every dependency (torch, chromadb, onnxruntime) resolved and installed on 3.14.
- **RAM**: only ~4 GB free of 15 GB at start. Ollama model loads lazily on demand and
  is not pinned permanently; embedding model (~90 MB) is small. Should be fine, but
  keep an eye on OOM during the final smoke test.
- Streamlit dev server runs headless on port 8599 (PID in /tmp/opencode/streamlit.pid).
