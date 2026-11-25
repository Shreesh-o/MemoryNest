# 🪺 MemoryNest — Personal Knowledge Manager

<p align="center">
  <strong>A local-first, privacy-focused knowledge hub for intelligent document indexing, scoped RAG search, audio briefings, and calendar automation.</strong>
</p>

<p align="center">
  <a href="#-tech-stack"><img src="https://img.shields.io/badge/Next.js-16%20App%20Router-black?style=for-the-badge&logo=next.js" alt="Next.js" /></a>
  <a href="#-tech-stack"><img src="https://img.shields.io/badge/FastAPI-Modern%20REST-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" /></a>
  <a href="#-tech-stack"><img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python" /></a>
  <a href="#-tech-stack"><img src="https://img.shields.io/badge/Node.js-v20%2B-green?style=for-the-badge&logo=node.js" alt="Node.js" /></a>
  <a href="#-tech-stack"><img src="https://img.shields.io/badge/Vector%20DB-ChromaDB-orange?style=for-the-badge" alt="ChromaDB" /></a>
  <a href="#-tech-stack"><img src="https://img.shields.io/badge/LLM-Ollama%20(Local)-green?style=for-the-badge&logo=ollama" alt="Ollama" /></a>
  <a href="#-testing--quality-assurance"><img src="https://img.shields.io/badge/Tests-349%20Passing-brightgreen?style=for-the-badge" alt="Tests" /></a>
  <a href="#-license"><img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License" /></a>
</p>

---

<p align="center">
  <img src="docs/screenshots/hero-landing.png" alt="MemoryNest Hero Landing" width="100%" style="border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.15);" />
</p>

## 📖 Overview

**MemoryNest** is a local, privacy-first personal knowledge manager designed to ingest, index, and synthesize documents and images without sending sensitive data to cloud providers.

Upload **PDFs, DOCX files, raw TXT documents, and scanned images (via OCR)** — all processing, vector embedding, similarity ranking, and generative AI inference execute strictly on your own hardware. Ask precise questions with document-scoped **RAG**, listen to generated **TTS audio briefings**, explore topic relationships with an interactive **2D Force-Directed Document Map**, and automatically extract **deadlines and calendar events** that sync directly to **Google Calendar** or export as standard `.ics` files.

---

## 📑 Table of Contents

- [Overview](#-overview)
- [System Architecture & Diagrams](#-system-architecture--diagrams)
  - [Full Architecture Blueprint](#full-architecture-blueprint)
  - [Data Flow Diagrams (DFD)](#data-flow-diagrams-dfd)
  - [System Use Cases](#system-use-cases)
- [Key Features](#-key-features)
- [Visual Interface Showcase](#-visual-interface-showcase)
- [Tech Stack](#-tech-stack)
- [Quick Start Guide (Any Device)](#-quick-start-guide-any-device)
  - [Step 1: Prerequisites & System Dependencies](#step-1-prerequisites--system-dependencies)
  - [Step 2: Local LLM Setup (Ollama)](#step-2-local-llm-setup-ollama)
  - [Step 3: Clone & Backend Environment Setup](#step-3-clone--backend-environment-setup)
  - [Step 4: Web Frontend Setup](#step-4-web-frontend-setup)
  - [Step 5: Launch the Application](#step-5-launch-the-application)
- [Configuration & Environment Variables](#-configuration--environment-variables)
- [Google Calendar OAuth Setup](#-google-calendar-oauth-setup)
- [Voice & TTS Options](#-voice--tts-options)
- [REST API Reference](#-rest-api-reference)
- [Document Map Maintenance](#-document-map-maintenance)
- [Testing & Quality Assurance](#-testing--quality-assurance)
- [License](#-license)

---

## 🏛️ System Architecture & Diagrams

MemoryNest separates concerns into a reactive **Next.js 16 Web Frontend**, a high-performance **FastAPI API Gateway**, and a modular **Service Layer** backed by local-only storage engines.

### Full Architecture Blueprint

<p align="center">
  <img src="docs/architecture-a4.svg" alt="MemoryNest Architecture Blueprint" width="85%" style="border-radius: 8px; border: 1px solid #e2e8f0;" />
</p>

```mermaid
flowchart TD
    subgraph Clients["Presentation Layer"]
        Web["Next.js 16 Web App<br/>(Tailwind v4, Base UI, TanStack Query)<br/>Port: 3000"]
        Streamlit["Streamlit UI (Legacy / Alternative)<br/>Port: 8501"]
    end

    subgraph Gateway["API Gateway & Security"]
        FastAPI["FastAPI REST Server (:8000)"]
        AuthMiddleware["JWT Cookie Auth & Bcrypt Gate"]
        Router["Route Handlers (Auth, Docs, Chat, Summaries, Reminders, Graph)"]
    end

    subgraph Services["Core Service Layer"]
        IngestSvc["Ingest & OCR Service<br/>(PyMuPDF, Docx, Tesseract)"]
        ChunkSvc["Sentence Chunking Service<br/>(~450 chars, 50 overlap)"]
        EmbedSvc["Embedding Service<br/>(all-MiniLM-L6-v2)"]
        RAGSvc["RAG & Chat Service<br/>(Scope Filter + Similarity Gate)"]
        SummSvc["Map-Reduce Summary & TTS<br/>(Piper, Edge-TTS, eSpeak)"]
        EventSvc["Event & Date Extractor<br/>(Regex + NLP + LLM Fallback)"]
        GCalSvc["Google Calendar & Email Flow<br/>(OAuth 2.0, Fernet, SMTP)"]
        GraphSvc["Document Map & Similarity<br/>(Cosine Sim + TF-IDF Terms)"]
    end

    subgraph Engines["Local Engines & Storage"]
        Ollama["Local Ollama LLM<br/>(qwen2.5:3b-instruct)"]
        Chroma["ChromaDB Vector Store<br/>(User-isolated collections)"]
        SQLite["SQLite Database<br/>(Users, Docs, Chunks, Events, Sessions)"]
        Disk["Filesystem Storage<br/>(data/uploads, data/audio, data/text_cache)"]
    end

    subgraph External["Optional External Integrations"]
        GoogleAPI["Google Calendar API (OAuth 2.0)"]
        Gmail["Gmail SMTP Service"]
    end

    Web -->|"/api/* Proxy"| FastAPI
    Streamlit -.->|Direct Service Calls| Services
    FastAPI --> AuthMiddleware
    AuthMiddleware --> Router
    Router --> Services

    IngestSvc --> ChunkSvc --> EmbedSvc --> Chroma
    IngestSvc --> SQLite
    IngestSvc --> Disk

    RAGSvc --> EmbedSvc
    RAGSvc --> Chroma
    RAGSvc --> Ollama

    SummSvc --> Ollama
    SummSvc --> Disk

    EventSvc --> Ollama
    EventSvc --> SQLite
    EventSvc --> GCalSvc

    GCalSvc -.-> GoogleAPI
    GCalSvc -.-> Gmail

    GraphSvc --> Chroma
    GraphSvc --> SQLite
```

---

### Data Flow Diagrams (DFD)

<details>
<summary><strong>🔍 Level 0: Context Level Diagram</strong></summary>

<br/>
<p align="center">
  <img src="docs/dfd-level-0.svg" alt="DFD Level 0 Context Diagram" width="85%" style="border-radius: 8px; border: 1px solid #e2e8f0;" />
</p>

*Shows the external entities (User, Local Storage, Google Cloud Services, LLM Daemon) and how information enters and exits MemoryNest.*
</details>

<details open>
<summary><strong>🔍 Level 1: Major System Processes</strong></summary>

<br/>
<p align="center">
  <img src="docs/dfd-level-1.svg" alt="DFD Level 1 Major Processes Diagram" width="90%" style="border-radius: 8px; border: 1px solid #e2e8f0;" />
</p>

*Illustrates data exchange between the 6 primary processes: Authentication, Document Ingestion, Semantic Indexing, Scoped Chat/RAG, Summarization/TTS, and Calendar Automation.*
</details>

<details>
<summary><strong>🔍 Level 2: Ingestion & RAG Deep Dive</strong></summary>

<br/>
<p align="center">
  <img src="docs/dfd-level-2.svg" alt="DFD Level 2 Pipeline Decomposition" width="90%" style="border-radius: 8px; border: 1px solid #e2e8f0;" />
</p>

*Detailed data breakdown of the extraction, chunking, embedding, vector storage, and similarity-gated prompt synthesis pipelines.*
</details>

---

### System Use Cases

<p align="center">
  <img src="docs/use-case-diagram.svg" alt="MemoryNest Use Case Diagram" width="85%" style="border-radius: 8px; border: 1px solid #e2e8f0;" />
</p>

---

## ✨ Key Features

| Feature | Description |
| :--- | :--- |
| 🛡️ **100% Local & Privacy-First** | All documents, vector embeddings, chunk databases, and LLM inference run strictly on your local device. No third-party data tracking or telemetry. |
| 🎯 **Scoped Document Chat** | Ask questions against your entire library or scope retrieval to specific files. Supports multi-turn conversation history with citation tracking. |
| 🗺️ **Document Map (Knowledge Graph)** | Interactive 2D force-directed graph powered by mean chunk cosine similarities with shared TF-IDF terms labeling the connections. |
| 📑 **Universal Ingestion & Dual Viewer** | Ingest PDFs, DOCX, TXT, and scanned image files. In-browser viewer supports original rendering (PDF iframe, sanitized DOCX HTML) and cached extracted text. |
| 🎙️ **Map-Reduce Summaries & TTS Audio** | Condenses massive documents into executive briefs. Automatically converts summaries into audio via **Piper**, **Edge-TTS**, or **eSpeak-ng**. |
| 📅 **Event Extraction & Google Calendar Sync** | Discovers dates and deadlines using pattern matching and LLM extraction. Syncs confirmed events directly to Google Calendar via OAuth 2.0 or exports `.ics`. |
| 🔍 **Semantic Vector Search** | Standalone vector similarity search with real-time relevance scoring and highlighted snippet previews. |
| 🌗 **Dark Mode & Archival Design** | Elegant "Evidence Chamber" aesthetic featuring Geist Sans, Geist Mono, Newsreader typography, Lenis smooth scrolling, and complete dark mode persistence. |

---

## 🖼️ Visual Interface Showcase

<div align="center">

### Modern Knowledge Dashboard
*Instant overview of your indexed document library, deadlines, and recent chats.*
<img src="docs/screenshots/dashboard.png" alt="MemoryNest Dashboard" width="90%" style="border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 24px;" />

---

### Ingestion & Documents Inventory
*Real-time processing status, file type badges, and dual-mode document viewer.*
<img src="docs/screenshots/documents-view.png" alt="MemoryNest Documents" width="90%" style="border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 24px;" />

---

### Drag-and-Drop File Upload Flow
*Client-side file validation, multi-file uploads, and automatic OCR ingestion.*
<img src="docs/screenshots/upload-flow.png" alt="MemoryNest Upload Flow" width="90%" style="border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 24px;" />

---

### Dark Mode & Archival Styling
*Thoughtfully crafted theme variables with reduced-motion compliance and high-contrast readability.*
<img src="docs/screenshots/dark-mode.png" alt="MemoryNest Dark Mode" width="90%" style="border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 24px;" />

---

### Mobile & Responsive Layout
*Full-featured responsive experience optimized for mobile screens, tablets, and desktops.*
<img src="docs/screenshots/mobile-view.png" alt="MemoryNest Mobile View" width="50%" style="border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 24px;" />

</div>

---

## 🛠️ Tech Stack

### Web Frontend
- **Framework**: [Next.js 16](https://nextjs.org/) (App Router, Turbopack, React 19)
- **Styling**: [Tailwind CSS v4](https://tailwindcss.com/)
- **UI Components**: [Base UI](https://base-ui.com/), [shadcn/ui](https://ui.shadcn.com/) patterns, [Lucide React](https://lucide.dev/) icons, [Sonner](https://sonner.emilkowal.ski/)
- **Graph Visualization**: `react-force-graph-2d`
- **State & Data Fetching**: TanStack React Query v5
- **Alternative / Legacy UI**: [Streamlit](https://streamlit.io/) (Python)

### Backend API & Storage
- **API Framework**: [FastAPI](https://fastapi.tiangolo.com/) (RESTful, Pydantic v2, HTTP-only JWT cookies)
- **Relational DB**: SQLite 3 with schema migrations and cascade deletes
- **Vector Database**: [ChromaDB](https://www.trychroma.com/) (PersistentClient mode, isolated by user_id)

### AI, Machine Learning & Media
- **Local LLM**: [Ollama](https://ollama.ai/) with `qwen2.5:3b-instruct` (3B parameters, CPU & GPU compatible)
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (fast 384-dimensional dense vectors)
- **OCR Engine**: [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) via `pytesseract`
- **Document Extractors**: [PyMuPDF](https://pymupdf.readthedocs.io/) (PDF), [python-docx](https://python-docx.readthedocs.io/) & [mammoth](https://github.com/mwilliamson/python-mammoth) (DOCX)
- **Text-to-Speech (TTS)**: Piper TTS (neural offline), Edge-TTS (natural cloud voice), eSpeak-ng (lightweight offline fallback)

---

## 🚀 Quick Start Guide (Any Device)

Follow the simple setup steps below for your operating system. MemoryNest runs seamlessly on **Linux**, **macOS**, and **Windows**.

### Step 1: Prerequisites & System Dependencies

Make sure you have:
- **Python**: 3.10 – 3.12 installed
- **Node.js**: v18.18+ or v20+ LTS (with `npm`)

Choose your operating system to install the required system tools (**Tesseract OCR**, **FFmpeg**, and optional **eSpeak-ng**):

<details open>
<summary><strong>🐧 Linux (Ubuntu / Debian / Mint)</strong></summary>

```bash
sudo apt-get update
sudo apt-get install -y python3-venv nodejs npm tesseract-ocr espeak-ng ffmpeg
```
*(On Fedora: `sudo dnf install python3-virtualenv nodejs tesseract espeak-ng ffmpeg`)*  
*(On Arch Linux: `sudo pacman -S python nodejs npm tesseract espeak-ng ffmpeg`)*
</details>

<details>
<summary><strong>🍎 macOS (Apple Silicon & Intel)</strong></summary>

Using [Homebrew](https://brew.sh/):
```bash
brew install python@3.11 node tesseract espeak-ng ffmpeg
```
</details>

<details>
<summary><strong>🪟 Windows (WSL2 Recommended or Native)</strong></summary>

> **💡 Recommended: WSL2 (Windows Subsystem for Linux)**  
> Run `wsl --install` in PowerShell, then follow the Linux instructions inside your Ubuntu terminal.

**If installing on Native Windows via [winget](https://learn.microsoft.com/en-us/windows/package-manager/winget/):**
```powershell
winget install Python.Python.3.11 OpenJS.NodeJS.LTS UB-Mannheim.TesseractOCR Gyan.FFmpeg
```
*(After installing Tesseract on Windows, ensure `C:\Program Files\Tesseract-OCR` is in your system `PATH`.)*
</details>

---

### Step 2: Local LLM Setup (Ollama)

MemoryNest uses Ollama to run the high-speed `qwen2.5:3b-instruct` model completely offline on your CPU or GPU.

1. **Install Ollama**:
   - **Linux & macOS**:
     ```bash
     curl -fsSL https://ollama.ai/install.sh | sh
     ```
   - **macOS via Homebrew**:
     ```bash
     brew install --cask ollama
     ```
   - **Windows**: Download the installer from [ollama.com/download/windows](https://ollama.com/download/windows) or run:
     ```powershell
     winget install Ollama.Ollama
     ```

2. **Pull the recommended lightweight model**:
   ```bash
   ollama pull qwen2.5:3b-instruct
   ```
   *(Takes ~2.0 GB of disk space. Smoothly runs on 4GB+ RAM on both CPU and GPU.)*

---

### Step 3: Clone & Backend Environment Setup

```bash
# 1. Clone the repository
git clone https://github.com/Shreesh-o/MemoryNest.git
cd MemoryNest

# 2. Create Python virtual environment
python3 -m venv .venv

# 3. Activate the virtual environment
# On Linux / macOS:
source .venv/bin/activate
# On Windows (PowerShell):
# .venv\Scripts\Activate.ps1
# On Windows (CMD):
# .venv\Scripts\activate.bat

# 4. Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 5. Create environment configuration
cp .env.example .env
```

---

### Step 4: Web Frontend Setup

```bash
# Navigate to web directory and install frontend dependencies
cd web
npm install
cd ..
```

---

### Step 5: Launch the Application

#### Option A: Unified Dev Runner (Linux & macOS / WSL2)

We provide an automated runner that checks preflight conditions, starts Ollama, spins up the FastAPI backend, and boots the Next.js frontend with hot reload:

```bash
bash scripts/dev.sh
```

#### Option B: Manual Two-Terminal Launch (Universal / Native Windows)

If you prefer running services individually or are on native Windows without Bash:

- **Terminal 1 (Backend API)**:
  ```bash
  # Activate venv first
  source .venv/bin/activate   # or .venv\Scripts\Activate.ps1 on Windows
  uvicorn app.api.main:app --host 127.0.0.1 --port 8000 --reload
  ```

- **Terminal 2 (Frontend App)**:
  ```bash
  cd web
  npm run dev
  ```

---

### 🌐 Access Your Services

| Service | Address | Description |
| :--- | :--- | :--- |
| **Next.js Web Application** | [http://localhost:3000](http://localhost:3000) | Primary web application |
| **Interactive API Documentation** | [http://localhost:8000/docs](http://localhost:8000/docs) | Interactive Swagger UI |
| **Streamlit UI (Alternative)** | [http://localhost:8501](http://localhost:8501) | Run via `streamlit run app/main.py` |

#### Useful Runner Commands:
```bash
bash scripts/dev.sh --stop      # Cleanly terminate all running background processes
bash scripts/dev.sh --prod      # Production build and optimized launch
bash scripts/dev.sh --fresh     # Launch with a clean, temporary isolated database
bash scripts/dev.sh --force     # Bypass optional preflight warnings
```

---

## ⚙️ Configuration & Environment Variables

Key configuration options in `.env`:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama daemon endpoint address |
| `OLLAMA_MODEL` | `qwen2.5:3b-instruct` | LLM model identifier in Ollama |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformers model name |
| `DB_PATH` | `data/memorynest.db` | SQLite database file location |
| `CHROMA_DIR` | `data/chroma` | ChromaDB vector store directory |
| `UPLOAD_DIR` | `data/uploads` | Uploaded document storage path |
| `AUDIO_DIR` | `data/audio` | Generated TTS audio directory |
| `RAG_TOP_K` | `5` | Number of context chunks retrieved per query |
| `RAG_MIN_SIMILARITY` | `0.30` | Minimum cosine similarity threshold for RAG answers |
| `CHUNK_SIZE` | `450` | Target chunk size in characters |
| `CHUNK_OVERLAP` | `50` | Overlap between sequential chunks |
| `LINK_MIN_SIMILARITY`| `0.45` | Cosine similarity threshold for Document Map visualization |
| `LINK_STORE_MIN_SIMILARITY`| `0.30` | Minimum similarity floor for persisted document relations |
| `LINK_MAX_PER_DOC` | `3` | Maximum number of outgoing edges per document node |
| `TTS_ENGINE` | `auto` | Engine strategy: `auto`, `piper`, `edge`, or `espeak` |
| `TTS_VOICE` | `en_US-lessac-medium` | Default voice identifier for TTS |
| `JWT_SECRET` | *(auto-generated)* | Key for signing HTTP-only session cookies |
| `JWT_EXPIRE_MINUTES` | `720` | Session lifetime (12 hours) |
| `GOOGLE_CLIENT_ID` | `""` | Google Cloud OAuth 2.0 Web Client ID |
| `GOOGLE_CLIENT_SECRET` | `""` | Google Cloud OAuth 2.0 Client Secret |
| `GOOGLE_REDIRECT_URI` | `http://localhost:8000/api/google/callback` | OAuth redirect callback URI |
| `TOKEN_ENCRYPTION_KEY` | `""` | Fernet key for encrypting stored Google refresh tokens |

---

## 📅 Google Calendar OAuth Setup

MemoryNest can automatically push confirmed reminders to your Google Calendar and remove them if cancelled.

### 1. Google Cloud Console
1. Navigate to the [Google Cloud Console](https://console.cloud.google.com/) and create a project (`MemoryNest`).
2. Go to **APIs & Services > Library** and enable the **Google Calendar API**.
3. Under **OAuth consent screen**:
   - Choose **External** for personal testing.
   - Add scopes: `https://www.googleapis.com/auth/calendar.events` and `https://www.googleapis.com/auth/userinfo.email`.
   - Add your Google account email under **Test Users**.
4. Under **Credentials**:
   - Create **OAuth client ID** > **Web application**.
   - Set **Authorized redirect URIs** to `http://localhost:8000/api/google/callback`.
   - Copy your **Client ID** and **Client Secret**.

### 2. Generate Fernet Token Encryption Key
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 3. Add to `.env`
```env
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/google/callback
FRONTEND_URL=http://localhost:3000
TOKEN_ENCRYPTION_KEY=your-generated-fernet-key
```

### 4. Lifecycle & Behavior
- Click **Connect Google Calendar** on the **Reminders** page to authorize via Google OAuth 2.0.
- When you confirm an event, it is immediately synchronized to your primary Google Calendar.
- If an event is cancelled, it is automatically removed from Google Calendar.
- Fallback **Download .ics** remains available at all times.

---

## 🔊 Voice & TTS Options

MemoryNest features a multi-tier speech synthesis pipeline:

- **`auto` (Default)**: Dynamically checks available engines in order: `piper` (local neural) ➔ `edge-tts` (online neural) ➔ `espeak-ng` (local synthesized) ➔ `pyttsx3`.
- **`piper`**: Ultra-fast offline neural TTS using lightweight ONNX voice models.
- **`edge`**: High-fidelity natural neural speech (requires internet connectivity; converted from MP3 to WAV via `ffmpeg`).
- **`espeak-ng`**: Compact offline synthesizer requiring minimal system overhead.

---

## 📡 REST API Reference

All protected endpoints require an authenticated JWT session cookie. Interactive Swagger UI is available at `/docs`.

<details>
<summary><strong>🔐 Authentication & User Profile</strong></summary>

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/auth/register` | Register new user account (`username`, `password`, optional `email`) |
| `POST` | `/api/auth/login` | Authenticate and issue HTTP-only JWT cookie |
| `GET` | `/api/auth/me` | Fetch authenticated user profile (`id`, `username`, `email`) |
| `POST` | `/api/auth/logout` | Revoke session and clear authentication cookie |
| `PATCH` | `/api/auth/me/email` | Update or remove recipient email address |

</details>

<details>
<summary><strong>📄 Documents & Ingestion</strong></summary>

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/documents/upload` | Multipart file upload (PDF, DOCX, TXT, images) with OCR & deduplication |
| `GET` | `/api/documents` | List user documents with processing status and chunk statistics |
| `GET` | `/api/documents/{id}` | Retrieve document details, extracted chunks, and detected events |
| `GET` | `/api/documents/{id}/file` | Stream original file (`?download=1` for attachment download) |
| `GET` | `/api/documents/{id}/content` | Get disk-cached, normalized extracted text (~500k character limit) |
| `GET` | `/api/documents/{id}/html` | Get sanitized HTML rendering for DOCX files (via mammoth + nh3) |
| `DELETE` | `/api/documents/{id}` | Permanently delete document with cascading SQLite and vector cleanup |
| `POST` | `/api/documents/{id}/retry` | Re-trigger parsing and embedding for failed documents |
| `POST` | `/api/documents/{id}/extract-events` | Re-run event and deadline extraction on document text |

</details>

<details>
<summary><strong>💬 Scoped Chat & Search</strong></summary>

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/chat/documents` | List ready documents available for scoped question answering |
| `POST` | `/api/chat` | Send question with optional `document_ids` scoping; returns answer + citations |
| `GET` | `/api/conversations` | List conversation threads |
| `GET` | `/api/conversations/{id}/messages` | Retrieve conversation message history with citations and scope metadata |
| `DELETE` | `/api/conversations/{id}` | Delete a conversation thread |
| `POST` | `/api/search` | Query vector index across all user chunks with similarity scores |

</details>

<details>
<summary><strong>🗺️ Document Map (Knowledge Graph)</strong></summary>

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/graph?min_score=0.45` | Get force-directed graph structure (`{nodes, edges, unlinked}`) |
| `GET` | `/api/documents/{id}/related` | Get top related neighbors with shared TF-IDF terms |
| `POST` | `/api/graph/refresh` | Recompute embedding similarity links across all user documents |

</details>

<details>
<summary><strong>🎙️ Summaries & Audio</strong></summary>

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/summaries` | List user document summaries |
| `POST` | `/api/documents/{id}/summary` | Trigger map-reduce summarization |
| `POST` | `/api/summaries/{id}/audio` | Synthesize TTS audio briefing |
| `GET` | `/api/summaries/{id}/audio` | Check audio generation status and TTS engine badge |
| `GET` | `/api/summaries/{id}/audio/file` | Stream or download generated WAV audio |

</details>

<details>
<summary><strong>📅 Events & Reminders</strong></summary>

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/events` | List detected pending calendar events |
| `POST` | `/api/events/{id}/confirm` | Schedule reminder, trigger confirmation email, push to Google Calendar |
| `POST` | `/api/events/{id}/discard` | Discard pending event |
| `GET` | `/api/reminders` | List scheduled or delivered reminders |
| `DELETE` | `/api/reminders/{id}` | Cancel reminder, delete from Google Calendar, revert to pending |
| `POST` | `/api/reminders/check` | Trigger on-demand due reminder email dispatch |
| `GET` | `/api/calendar/items` | Get month calendar items with Google sync status |
| `GET` | `/api/calendar.ics` | Export user's confirmed events as standard iCalendar `.ics` file |
| `POST` | `/api/reminders/{id}/sync` | Manually retry syncing reminder to Google Calendar |

</details>

<details>
<summary><strong>🔗 Google Calendar OAuth</strong></summary>

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/google/status` | Check Google Calendar connection status and linked account |
| `POST` | `/api/google/connect` | Initialize OAuth 2.0 flow with CSRF state cookie |
| `GET` | `/api/google/callback` | Exchange OAuth code for encrypted refresh token |
| `POST` | `/api/google/disconnect` | Revoke tokens and disconnect Google account |

</details>

---

## 🗺️ Document Map Maintenance

To rebuild semantic relationships between documents across all users or after adjusting similarity parameters:

```bash
# Activate environment and rebuild document map links
source .venv/bin/activate
python scripts/rebuild_links.py
```

---

## 🧪 Testing & Quality Assurance

MemoryNest is covered by a test suite ensuring reliability across all core services and endpoints:

```bash
# Run backend pytest suite (349 unit & API integration tests)
source .venv/bin/activate
pytest -v

# Run Playwright end-to-end tests
cd web
npx playwright test
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
