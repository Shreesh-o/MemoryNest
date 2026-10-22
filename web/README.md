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
│   ├── (auth)/              # Unauthenticated route group
│   │   ├── login/           # User sign-in with username and password
│   │   └── register/        # Account registration with optional email
│   ├── (app)/               # Authenticated route group (App Shell & Navigation)
│   │   ├── dashboard/       # Metric cards, pending actions, upcoming deadlines
│   │   ├── upload/          # Multi-file drag & drop, client validation, upload progress
│   │   ├── documents/       # Document inventory, text previews, cascading deletion
│   │   ├── chat/            # RAG question answering, streaming citations, thread switcher
│   │   ├── history/         # Searchable conversation history and thread deletion
│   │   ├── summaries/       # Map-reduce summaries, audio player, voice engine badge
│   │   └── reminders/       # Month calendar, Google sync card, email manager, tabs
│   ├── layout.tsx           # Root layout with QueryClient and Toaster providers
│   └── page.tsx             # Root redirect (authenticated → /dashboard, unauth → /login)
├── components/
│   ├── layout/              # Sidebar navigation and header controls
│   ├── reminders/           # MonthCalendar interactive component & sheets
│   └── ui/                  # Base UI (@base-ui/react) styled components
└── lib/
    ├── api.ts               # Typed client functions for FastAPI backend
    └── utils.ts             # Styling helpers (clsx, twMerge)
```

## Key Frontend Features

- **Month Calendar & Reminders**: Interactive month calendar view displaying pending deadlines (amber) and scheduled reminders (emerald) with Google sync status badges and manual retry actions.
- **Google Calendar Card**: One-click OAuth 2.0 connection, status badge showing connected Google email, disconnect confirmation dialog, and clean URL params handling.
- **Email Profile Manager**: Inline editor on Reminders page for setting, updating, or clearing email notification addresses.
- **Natural TTS Player**: Plays synthesized summaries with an engine badge (e.g. `edge`, `piper`, `espeak`) and download link.
- **RAG Chat with Citations**: Real-time conversation with expandable document source citations and similarity verification.

## UI Component Guidelines

- Components in `src/components/ui/` use **Base UI** (`@base-ui/react`).
- Do not use Radix-specific props such as `asChild`; use the Base UI `render` prop pattern.

## Scripts

- `npm run dev`: Start Next.js development server on port 3000 with Turbopack.
- `npm run build`: Compile production build.
- `npm run start`: Start production server.
- `npm run lint`: Run ESLint checks.
- `npm run test:e2e`: Run Playwright end-to-end tests.

