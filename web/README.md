# MemoryNest Web Frontend

Next.js 16 web application for MemoryNest, featuring a modern UI built with Tailwind CSS, shadcn/ui (Base UI style), TanStack React Query, and Sonner toasts.

## Getting Started

From the project root:

```bash
# Recommended: start the complete stack (FastAPI backend + Next.js frontend)
cd .. && bash scripts/dev.sh

# Or start the web frontend standalone:
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Backend Connection

All `/api/*` routes are proxied to the FastAPI backend via rewrites in `next.config.ts`.
By default, the web client proxies to `http://127.0.0.1:8000` (or the URL configured in `API_URL`).

```bash
API_URL=http://127.0.0.1:8000
```

## UI Component Guidelines

- Components in `src/components/ui/` use **Base UI** (`@base-ui/react`).
- Do not use Radix-specific props such as `asChild`; use the Base UI `render` prop pattern.

## Scripts

- `npm run dev`: Start Next.js development server on port 3000 with Turbopack.
- `npm run build`: Compile production build.
- `npm run start`: Start production server.
- `npm run lint`: Run ESLint checks.

