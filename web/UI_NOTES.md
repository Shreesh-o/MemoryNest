# MemoryNest UI/UX Design System Notes

## 1. Design Direction: Swiss Minimalism
- **Aesthetic**: Swiss Minimalism / Local-first Executive Vault. Clean lines, generous whitespace, high data density without clutter, clear typographic hierarchy.
- **Palette**: Neutral slate & obsidian foundation (`oklch` based tokens in `globals.css`):
  - Background (Light): `#F8FAFC` (subtle off-white)
  - Background (Dark): `#0B0F19` (rich obsidian)
  - Foreground (Light): `#0F172A` / Foreground (Dark): `#F8FAFC`
  - Accent / Primary: Emerald / Mint (`#10B981` / `oklch(0.696 0.17 162.48)`)
  - Semantic Status Tokens:
    - Success: Emerald (`oklch(0.696 0.17 162.48)`)
    - Warning: Amber (`oklch(0.769 0.188 70.08)`)
    - Destructive: Rose/Red (`oklch(0.577 0.245 27.325)`)
    - Info: Sky/Blue (`oklch(0.6 0.18 240)`)
- **Typography**: System font stack (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif`) with tabular figures on numbers and metadata. Zero external remote font dependencies (`fonts.googleapis.com` free) for offline resilience and fast loading.
- **Micro-Interactions & Motion**:
  - `cursor: pointer` explicitly on all interactive buttons, cards, links, tabs, and toggles.
  - Subtle transitions (`150ms-200ms ease-out`).
  - Strict `@media (prefers-reduced-motion: reduce)` override disabling non-essential transitions and animations.

## 2. Dependencies
- **New Dependencies**: 0 (zero new dependencies added).
- **Component Stack**:
  - Base UI (`@base-ui/react`) for accessible primitives (Slider, Tabs, Dialog, Popover).
  - Lucide React for consistent vector iconography (no raw emojis as icons).
  - Tailwind CSS v4 with semantic CSS variable tokens.
  - Sonner for notifications.
  - TanStack React Query for data state management.

## 3. Key Pages & Layout Improvements
1. **App Shell**: Responsive sidebar with brand vault identity, 8 navigation items with dedicated Lucide icons, mobile slide-out drawer, theme segmented control (Light / Dark).
2. **Dashboard**: 4-column responsive metrics overview, recent documents, upcoming deadlines, system health indicators.
3. **Documents & Viewer**: Grid/list view toggles, ingestion pipeline status badges, full-screen document viewer with document metadata sidebar, chunk inspection, and raw/processed tabs.
4. **Chat & History**: Pinned viewport layout without window scrolling, conversation history drawer, source citation details, searchable document selector.
5. **Reminders & Calendar**: Full monthly interactive grid with status badges, custom lead-time reminder scheduling (15m, 1h, 1d, 2d, 1w), Google Calendar sync indicator, and inline email manager.
6. **Document Map**: Hardware-accelerated force-directed graph (`react-force-graph-2d`, `ssr: false`), Base UI similarity threshold slider, responsive side panel, crisp canvas rendering in both light and dark modes.
7. **Summaries & Search**: Map-reduce executive summaries, natural text-to-speech audio player modal with download, semantic vector search with relevance meter and matched snippet highlighting.
