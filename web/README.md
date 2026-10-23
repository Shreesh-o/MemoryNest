# MemoryNest Web Frontend

Next.js 16 web application for MemoryNest, featuring a modern UI built with Tailwind CSS, shadcn/ui (Base UI style), TanStack React Query, and Sonner toasts.

## Getting Started

From the project root:

```bash
# Recommended: start the complete stack (FastAPI backend + Next.js frontend)
cd .. && bash scripts/dev.sh

# Or start the web frontend standalone:
cd web && npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Backend Connection & API Proxy

All `/api/*` routes are proxied to the FastAPI backend via rewrites in `next.config.ts`.
By default, the web client proxies to `http://127.0.0.1:8000` (or the URL configured in `API_URL`).

```bash
API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_MAX_FILE_MB=20
```

## Application Structure

The web application uses the Next.js 16 App Router architecture:

```
web/src/
├── app/
│   ├── (marketing)/         # Marketing landing page route group
│   │   ├── layout.tsx       # Marketing shell with Lenis smooth scroll & GSAP ticker
│   │   └── page.tsx         # "Evidence Chamber" landing page (bench, dossier, mechanics)
│   ├── (auth)/              # Unauthenticated route group
│   │   ├── login/           # User sign-in with username and password
│   │   ├── register/        # Account registration with optional email
│   │   ├── auth-layout-client.tsx
│   │   └── layout.tsx       # Archival-styled auth layout with keyboard navigation
│   ├── (app)/               # Authenticated route group (App Shell & Navigation)
│   │   ├── dashboard/       # Metric cards, pending actions, upcoming deadlines
│   │   ├── upload/          # Multi-file drag & drop, client validation, upload progress
│   │   ├── documents/       # Document inventory, text previews, cascading deletion
│   │   ├── documents/[id]/  # Full document viewer (PDF iframe, DOCX HTML, raw text, actions)
│   │   ├── chat/            # Scoped RAG Q&A, citations, thread switcher
│   │   ├── search/          # Semantic vector search with relevance meter & snippets
│   │   ├── map/             # Interactive 2D canvas Document Map force graph
│   │   ├── history/         # Searchable conversation history and thread deletion
│   │   ├── summaries/       # Map-reduce summaries, audio player, voice engine badge
│   │   └── reminders/       # Month calendar, Google sync card, email manager, tabs
│   ├── fonts.ts             # Local font definitions (Geist Sans, Geist Mono, Newsreader)
│   ├── globals.css          # Tailwind CSS v4 tokens, dark/light theme variables
│   ├── layout.tsx           # Root layout with QueryClient and Toaster providers
│   └── providers.tsx        # React Query and Theme providers
├── components/
│   ├── app-shell/           # Sidebar navigation, top bar, and mobile navigation
│   ├── marketing/           # Landing page sections (hero, bento-grid, how-it-works, etc.)
│   ├── reminders/           # MonthCalendar interactive component & sheets
│   └── ui/                  # Base UI (@base-ui/react) styled components
└── lib/
    ├── api.ts               # Typed client functions for FastAPI backend
    └── utils.ts             # Styling helpers (clsx, twMerge)
```

## Key Frontend Features

- **Marketing Landing Page ("The Evidence Chamber")**: Awwwards-inspired local-first presentation featuring the interactive Evidence Bench, capabilities dossier, architecture mechanics, and reduced-motion compliant Lenis & GSAP choreography.
- **Document Map**: Hardware-accelerated 2D force-directed canvas graph (`react-force-graph-2d`) illustrating document conceptual relationships via cosine similarity and TF-IDF shared terms with interactive threshold slider.
- **Document Viewer**: Dual-mode in-browser document viewer supporting native PDF embedding, sanitized DOCX HTML rendering via mammoth + nh3, responsive image viewer with OCR notice, and disk-cached whitespace-normalized extracted text.
- **Scoped Document Chat**: Grounded Q&A that can query across all documents or focus retrieval to a selected subset of ready documents.
- **Semantic Search**: Fast vector similarity search across all document chunks with relevance meters and matched snippet highlights.
- **Month Calendar & Reminders**: Interactive month calendar view displaying pending deadlines (amber) and scheduled reminders (emerald) with Google sync status badges and manual retry actions.
- **Google Calendar Card**: One-click OAuth 2.0 connection, status badge showing connected Google email, disconnect confirmation dialog, and clean URL params handling.
- **Email Profile Manager**: Inline editor on Reminders page for setting, updating, or clearing email notification addresses.
- **Natural TTS Player**: Plays synthesized summaries with an engine badge (e.g. `edge`, `piper`, `espeak`) and download link.

## UI Component Guidelines

- Components in `src/components/ui/` use **Base UI** (`@base-ui/react`).
- Do not use Radix-specific props such as `asChild`; use the Base UI `render` prop pattern.

## Scripts

- `npm run dev`: Start Next.js development server on port 3000 with Turbopack.
- `npm run build`: Compile production build.
- `npm run start`: Start production server.
- `npm run lint`: Run ESLint checks.
- `npm run test:e2e`: Run Playwright end-to-end tests.

