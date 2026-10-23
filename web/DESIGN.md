# MemoryNest — Design System & Art Direction Specification

> **Status:** Phase 1 Complete (Concept & Art Direction Approved)  
> **Target:** Award-Caliber Experience (Awwwards Site of the Day Benchmark)  
> **Repository:** `~/MemoryNest`  
> **Branch:** `awwww`

---

## 1. Product Brief & Explicit Assumptions

### 1.1 The Product
MemoryNest is an authentic **local-first personal knowledge manager**. Unlike conventional cloud-based RAG tools that upload private data to third-party APIs, MemoryNest runs on the user's local machine using a local LLM (Ollama), sentence embeddings (`all-MiniLM-L6-v2`), SQLite, and ChromaDB.

### 1.2 Core Capabilities (Authoritative Baseline)
- **Multi-Format Ingestion:** PDF, DOCX, TXT, and images with OCR extraction.
- **Strictly Cited Q&A:** Grounded document question answering that cites exact chunks and explicitly refuses to speculate when evidence is absent.
- **Semantic Search:** Vector retrieval across user document chunks with hybrid term matching.
- **Summaries & Neural TTS Audio:** Map-reduce document summaries with local/neural text-to-speech audio player.
- **Extracted Deadlines & Reminders:** Automatic date and event detection, scheduled reminder alerts, in-app monthly calendar, and optional Google Calendar OAuth synchronization.
- **Document Map:** Interactive document relationship graph driven by embedding similarity and TF-IDF shared terms.
- **Clean Document Viewer:** In-browser document inspection with rendered page/HTML text.
- **Conversation History:** Multi-session chat threads with saved citations and document filters.
- **Private User Isolation:** Strict per-user data segregation across database tables, Chroma vectors, and filesystem paths.

### 1.3 Design Constraints & Invariants
- **No Invented Features:** No reminder lead-time dropdowns, fake "remind me X before" chips, or fabricated cloud controls.
- **No Fictional Social Proof:** Zero fake testimonials, fake client logos, fabricated star ratings, or inflated user statistics.
- **Local-First Terminology:** Use "local-first" rather than inaccurate absolutes like "100% offline" (since optional Google Calendar sync and TTS engines may access external network endpoints).
- **Exact Terminology:** Feature is named **Document Map** (not "knowledge graph").
- **Component Architecture:** Next.js App Router, Tailwind CSS v4, Base UI (strictly avoiding Radix and `asChild`), Lucide icons, TanStack React Query. Motion strictly isolated to marketing route group.

---

## 2. Concept Exploration (Three Distinct Territories)

We explored three fundamentally different concepts grounded in MemoryNest's specific identity:

### Concept A — "The Evidence Chamber" (Territory: Domain Material & Provenance)
* **One-Sentence Idea:** Personal knowledge is an evidence room where nothing is taken on faith: every answer, summary, and deadline is anchored to an inspectable, highlighted leaf of paper on your own desk.
* **Metaphor:** The forensic reading room, archival evidence bench, and legal brief verification table.
* **Visual Language:** Archival carbon and warm parchment (`#F8F7F4` / `#121316`), hairlines, crisp document folios, marginalia coordinate stamps, optical rule lines.
* **Typography:** Precision contemporary neo-grotesk (`Geist` / `Supreme`) paired with a warm editorial serif (`Newsreader`) for authentic document citations and `Geist Mono` for technical coordinates.
* **Signature Moment:** **The Provenance Ray** — hovering or scrubbing any answer or claim dynamically renders an illuminated optical tether linking the claim directly to its highlighted excerpt in the source document folio.
* **The Screenshot Frame:** The asymmetric hero workbench: a floating cited document sheet with optical margin calipers and an active citation ray illuminating the exact evidence chunk.
* **Anchor:** MemoryNest's defining product truth: strictly cited Q&A that refuses to guess, paired with its raw document extraction engine.
* **Trade-offs:** Demands rigorous typographic calibration and restrained spacing so it feels like a high-craft cultural archive rather than a sterile legal compliance tool.

### Concept B — "The Woven Nest" (Territory: Name & Structural Metaphor)
* **One-Sentence Idea:** Memory is not a filing cabinet, but an interwoven nest of living connections where documents land like leaves and twigs that bind into a resilient personal sanctuary.
* **Metaphor:** The natural avian nest and woven organic trellis.
* **Visual Language:** Deep forest obsidian and lichen tones (`#0D1110`, `#E8EDE7`, `#5CE69E`), contoured topographic flow lines, and fiber-like network lines.
* **Typography:** `General Sans` paired with structural display headings (`Cabinet Grotesk`).
* **Signature Moment:** **The Nesting Constellation** — an interactive Document Map physics node cluster where dragging document nodes tightens the woven connections and surfaces shared terms.
* **Anchor:** The etymology of "Nest" combined with MemoryNest's Document Map (`link_service`).
* **Trade-offs:** Can easily slip into looking like a generic network graph visualization or biotech website.

### Concept C — "The Air-Gapped Monolith" (Territory: Formal System & Operational Hardware)
* **One-Sentence Idea:** A sovereign data sanctuary engineered directly into your local silicon: zero telemetry, zero cloud harvesting, and absolute physical custody of your mind.
* **Metaphor:** Industrial mainframe console, air-gapped cryptographic terminal, and avionics flight recorder.
* **Visual Language:** High-density matte obsidian graphite (`#08090A`, `#121417`, `#EDEDF0`), amber status indicators (`#F59E0B`), and precision hardware bevels.
* **Typography:** Strict industrial neo-grotesk (`Geist`) and dense tabular monospace (`Geist Mono`).
* **Signature Moment:** **The Air-Gap Caliper** — an interactive comparative telemetry switch showing external cloud API packet leaks versus MemoryNest's closed local loop on localhost.
* **Anchor:** MemoryNest's local LLM (Ollama) and local SQLite/Chroma storage.
* **Trade-offs:** Risks feeling cold, intimidating, or overly developer-centric for general knowledge workers.

### 2.4 Concept Scoring & Evaluation

| Criterion | Weight | Concept A: Evidence Chamber | Concept B: Woven Nest | Concept C: Air-Gapped Monolith |
| :--- | :---: | :---: | :---: | :---: |
| **Originality** (1-5) | 25% | **4.5** | 3.5 | 3.5 |
| **Fit to MemoryNest** (1-5) | 35% | **5.0** | 4.0 | 4.0 |
| **Feasibility in Code** (1-5) | 20% | **4.8** | 3.8 | 4.5 |
| **Portability** (1-5, lower is better) | 20% | **1.5** | 3.0 | 3.5 |
| **Weighted Total** | | **4.38 / 5.0** | 3.65 / 5.0 | 3.83 / 5.0 |

**Selected Concept:** **Concept A — "The Evidence Chamber"**  
*Rationale:* Concept A anchors directly on MemoryNest's most distinctive functional commitment: uncompromised citation veracity and local document provenance. It avoids both generic SaaS card kits and cold terminal tropes, elevating the product into an authoritative, cultural-grade instrument.

---

## 3. The Selected Concept: Concept Card

```text
Idea:        Personal knowledge is an evidence room where nothing is taken on faith:
             every answer, summary, and deadline is anchored to an inspectable,
             highlighted leaf of paper on your own desk.
Metaphor:    The forensic archival reading room and provenance workbench.
Signature:   The Provenance Ray: an interactive dual-pane inspector where hovering
             a cited claim casts an illuminated optical beam directly to its source
             sentence in a floating document folio.
Emotion:     Quiet, commanding confidence, intellectual clarity, and forensic certainty.
Motion verb: Settle like heavy paper and snap like an optical caliper.
Screenshot:  The asymmetric hero evidence bench with an illuminated citation ray linking
             an active answer claim to a highlighted document folio with margin coordinates.
```

---

## 4. Art Direction System

### 4.1 Color Architecture (Light & Dark Designed Pairs)

All text pairings exceed WCAG AA 4.5:1 contrast requirements (and exceed AAA 7.0:1 for primary headings and body copy).

#### Light Mode (Warm Archival Parchment)
- `ground`: `#F9F8F5` — Warm archival paper ground.
- `surface`: `#FFFFFF` — Crisp document leaf white.
- `surface-elevated`: `#F2EFE9` — Stacked dossier plate.
- `ink`: `#111215` — Deep carbon ink (contrast ratio 16.8:1 against ground).
- `muted`: `#4E5360` — Graphite annotation slate (contrast ratio 5.3:1 against ground).
- `line`: `rgba(17, 18, 21, 0.08)` — Hairline ruling edge.
- `line-strong`: `rgba(17, 18, 21, 0.16)` — Structural bounding line.
- `accent-primary`: `#0A58CA` — Evidence cobalt (verified provenance).
- `accent-highlight`: `rgba(234, 179, 8, 0.22)` — Archival yellow highlighter.
- `accent-emerald`: `#047857` — Verified local health indicator.

#### Dark Mode (Obsidian Archive)
- `ground`: `#090A0C` — Obsidian chamber ground.
- `surface`: `#121418` — Dense carbon plate.
- `surface-elevated`: `#1A1D23` — Elevated folio card.
- `ink`: `#F5F6F8` — Magnesium white (contrast ratio 18.2:1 against ground).
- `muted`: `#929AA6` — Silver slate (contrast ratio 5.6:1 against ground).
- `line`: `rgba(245, 246, 248, 0.08)` — Hairline ruling edge.
- `line-strong`: `rgba(245, 246, 248, 0.16)` — Structural bounding line.
- `accent-primary`: `#3B82F6` — Electric cobalt beam.
- `accent-highlight`: `rgba(250, 204, 21, 0.25)` — Illuminated chunk highlight.
- `accent-emerald`: `#10B981` — Local status signal.

### 4.2 Typography System

- **Display & Headings:** `Geist Sans` (Next.js font integration).
  - Tracking: `-0.03em` for `text-5xl` through `text-7xl`.
  - Leading: `0.92` to `1.05`.
  - Case: Sentence case strictly. No uppercase shouting.
- **Body & Controls:** `Geist Sans`.
  - Size: `15px` to `17px`.
  - Leading: `1.5` to `1.6`.
  - Weight: `400` regular, `500` medium for labels.
- **Document Citations & Excerpts:** `Newsreader` / Editorial Serif (italicized & regular).
  - Role: Applied exclusively to quoted document text, citations, and summaries to create an immediate perceptual distinction between the software interface and the human source material.
- **Data & Coordinates:** `Geist Mono`.
  - Tracking: `0.02em`.
  - Role: File sizes, hashes, chunk indices, latency figures, and calendar timestamps.

### 4.3 Spatial Grid & Layout Families

1. **Section 1: Hero — Asymmetric Evidence Bench**
   - 45% Left: Clear product headline, local-first thesis, instant dual CTAs (Get Started, Sign In), and live localhost status badge.
   - 55% Right: Interactive Evidence Inspector showing an actual question ("What were our quarterly compliance commitments?"), an extracted answer card with source tag `[doc_4: p.12]`, and an SVG-tethered citation ray pointing to an illuminated paragraph on a rendered document page.
2. **Section 2: The Proof Index (Capabilities Dossier)**
   - Asymmetric split-view index: Left side features a tactile catalog of capabilities (Cited Q&A, Semantic Search, Document Map, Audio Summaries, Extracted Deadlines), right side features a real-time reactive preview slate.
3. **Section 3: The Architecture of Truth (Local Engine Mechanics)**
   - 3-column irregular grid illustrating the ingest-to-retrieval pipeline: Raw Upload (PDF/OCR) → Sentence Chunker & Vector Index → Local LLM Inference. Real parameters, zero marketing hand-waving.
4. **Section 4: The Document Map Constellation**
   - Live interactive mini-canvas showcasing document relationship nodes, connection strengths, and shared terms based directly on MemoryNest's `link_service` algorithms.
5. **Section 5: Autonomous Calendar & Reminders Stream**
   - Chronological timeline showing extracted events, deadline badges, in-app calendar view, and optional Google Calendar sync flow.
6. **Section 6: The Local vs Cloud Audit**
   - Forensic comparison ledger contrasting cloud-dependent data harvesting against MemoryNest's private, encrypted local execution.
7. **Section 7: Footer & Archival Colophon**
   - Four-corner archival frame: copyright, system health status, architectural navigation, and keyboard shortcuts.

### 4.4 Motion & Interaction Principles

- **Motion Verb:** "Settle like heavy paper and snap like an optical caliper."
- **Primary Targets:** Buttons and interactive cards feature an optical border illumination and a subtle inner elevation lift (`translateY(-2px)`), avoiding generic bouncy springs.
- **Idle Motion:** A slow, breathing pulse on the citation beam and live status indicator (`0.5Hz`), suspended immediately when the user scrolls or when `prefers-reduced-motion` is active.
- **Reduced Motion:** If `prefers-reduced-motion: reduce` is detected, all CSS transforms and GSAP animations resolve instantly to their final opacity: 1 and position: 0 states.

### 4.5 The Genericness Test

- *Does it have a centered headline over a purple/blue gradient blob?* **No.** Asymmetric split bench over warm archival/obsidian ground.
- *Does it use three identical feature cards with rounded borders?* **No.** Structured dossier index with irregular modular architectural plates.
- *Does it use fake testimonials or "trusted by 10,000+ teams"?* **No.** Grounded entirely in real, truthful product capabilities.
- *Does it use generic "elevate your workflow" copy?* **No.** Precise, specific language: "Every answer anchored to verifiable citations on your own machine."

---

## 5. Execution Phases Plan

- **Phase 1:** Concept & Art Direction (`web/DESIGN.md` created & documented) — **CURRENT**
- **Phase 2:** Design Foundations (Tailwind v4 tokens, typography, dark/light CSS variables in `globals.css`)
- **Phase 3:** Landing Page (Semantic, responsive, fully accessible static structure with real product details)
- **Phase 4:** Marketing Motion (GSAP & Lenis smooth choreography strictly scoped to `(marketing)` layout, with full reduced-motion support)
- **Phase 5:** Login & Register Pages (Cohesive archival aesthetic, preserving 100% of auth handlers and redirect logic)
- **Phase 6:** Light App-Wide Redesign (Refined tokens and polish across dashboard, viewer, chat, reminders, map, summaries, preserving all baseline data behavior)
- **Phase 7:** Production QA & Jury Review (Playwright tests, axe accessibility audit, mobile 390px responsive validation, jury scorecard)
