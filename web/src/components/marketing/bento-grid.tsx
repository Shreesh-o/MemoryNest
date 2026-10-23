"use client"

import * as React from "react"
import {
  MessageSquare,
  Network,
  UploadCloud,
  Volume2,
  CalendarDays,
  Search,
  CheckCircle2,
  Play,
  Sliders,
} from "lucide-react"

export function BentoGrid() {
  return (
    <section
      id="features"
      aria-labelledby="features-heading"
      className="py-16 sm:py-24 bg-muted/20 border-t border-border/70"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-left max-w-3xl mb-12 sm:mb-16">
          <div className="inline-flex items-center gap-1.5 rounded-md border border-border/80 bg-background px-2.5 py-1 text-xs font-mono uppercase tracking-wider text-muted-foreground mb-3 shadow-2xs">
            <span>SPECIFICATION // CAPABILITIES DOSSIER</span>
          </div>
          <h2
            id="features-heading"
            className="font-heading text-3xl font-extrabold tracking-tight sm:text-4xl lg:text-5xl text-foreground text-balance"
          >
            Seven verified capabilities. Executed without cloud dependencies.
          </h2>
          <p className="mt-4 text-base sm:text-lg text-muted-foreground leading-relaxed text-balance">
            Every layer runs inside your local user enclave. From OCR parsing of image scans to
            vector retrieval, neural audio synthesis, and interactive relationship mapping.
          </p>
        </div>

        {/* Feature Grid: Irregular Architectural Plate System */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-5">
          {/* Card 1: Cited Document Q&A & Refusal Gate (7 cols) */}
          <div className="md:col-span-12 lg:col-span-7 rounded-2xl border border-border/80 bg-card p-6 shadow-sm paper-folio flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between border-b border-border/60 pb-3 mb-4">
                <div className="flex items-center gap-2.5">
                  <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <MessageSquare className="size-4" aria-hidden="true" />
                  </div>
                  <div>
                    <h3 className="font-heading text-base font-bold text-foreground">
                      Cited Document Q&amp;A
                    </h3>
                    <p className="text-xs text-muted-foreground font-mono">
                      Strict Grounding Gate (Threshold &gt; 0.30)
                    </p>
                  </div>
                </div>
                <span className="rounded px-2 py-0.5 text-[10px] font-mono font-medium bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20">
                  Hallucination Proof
                </span>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Queries are embedded via <code className="text-xs font-mono bg-muted px-1.5 py-0.5 rounded">all-MiniLM-L6-v2</code> and matched against local ChromaDB chunks. If retrieved chunks fail the similarity threshold, MemoryNest outputs an explicit refusal rather than confabulating.
              </p>
            </div>

            {/* Interactive Simulation Block */}
            <div className="mt-5 rounded-xl border border-border/70 bg-muted/30 p-4 space-y-3 font-mono text-xs">
              <div className="flex items-center justify-between text-muted-foreground text-[11px] pb-2 border-b border-border/40">
                <span>QUERY: &ldquo;What penalty applies for delayed filing?&rdquo;</span>
                <span className="text-emerald-700 dark:text-emerald-400 font-semibold">SIM: 0.88</span>
              </div>
              <div className="rounded-lg bg-background p-3 border border-border/70 shadow-2xs">
                <p className="font-serif text-xs sm:text-[13px] leading-relaxed text-foreground">
                  &ldquo;A late administrative fee of $150 applies for the first 30 days, followed by a monthly compounding rate of 1.5%.&rdquo;
                </p>
                <div className="mt-2.5 pt-2 border-t border-border/40 flex items-center justify-between text-[11px]">
                  <span className="text-primary font-medium">
                    [Master_Services_2026.docx · Section 4.2]
                  </span>
                  <span className="text-muted-foreground">Ollama Inference: 112ms</span>
                </div>
              </div>
            </div>
          </div>

          {/* Card 2: Document Map (5 cols) */}
          <div className="md:col-span-12 lg:col-span-5 rounded-2xl border border-border/80 bg-card p-6 shadow-sm paper-folio flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between border-b border-border/60 pb-3 mb-4">
                <div className="flex items-center gap-2.5">
                  <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Network className="size-4" aria-hidden="true" />
                  </div>
                  <div>
                    <h3 className="font-heading text-base font-bold text-foreground">
                      Document Map
                    </h3>
                    <p className="text-xs text-muted-foreground font-mono">
                      TF-IDF &amp; Cosine Similarity
                    </p>
                  </div>
                </div>
                <span className="rounded px-2 py-0.5 text-[10px] font-mono font-medium bg-muted text-muted-foreground border border-border">
                  Interactive Graph
                </span>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Visualizes inter-document affinities dynamically. Calculates vector distance and shared vocabulary keywords, rendering connected clusters with adjustable threshold sliders and side panels.
              </p>
            </div>

            {/* Visual Schematic of Nodes */}
            <div className="mt-5 rounded-xl border border-border/70 bg-background p-4 relative overflow-hidden flex flex-col gap-2.5">
              <div className="flex items-center justify-between text-[11px] font-mono text-muted-foreground">
                <span className="flex items-center gap-1">
                  <Sliders className="size-3 text-primary" aria-hidden="true" />
                  <span>SIMILARITY THRESHOLD: 0.65</span>
                </span>
                <span>4 CLUSTERS</span>
              </div>
              {/* Node Pairs */}
              <div className="space-y-1.5 text-xs font-mono">
                <div className="flex items-center justify-between p-2 rounded bg-muted/40 border border-border/50">
                  <span className="font-medium text-foreground">Lease_2026.pdf ↔ Addendum.docx</span>
                  <span className="text-primary font-semibold">0.91 (5 shared terms)</span>
                </div>
                <div className="flex items-center justify-between p-2 rounded bg-muted/40 border border-border/50">
                  <span className="font-medium text-foreground">Patent_Filings.pdf ↔ Claims.txt</span>
                  <span className="text-primary font-semibold">0.84 (8 shared terms)</span>
                </div>
              </div>
            </div>
          </div>

          {/* Card 3: Extracted Deadlines & In-App Calendar (5 cols) */}
          <div className="md:col-span-12 lg:col-span-5 rounded-2xl border border-border/80 bg-card p-6 shadow-sm paper-folio flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between border-b border-border/60 pb-3 mb-4">
                <div className="flex items-center gap-2.5">
                  <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <CalendarDays className="size-4" aria-hidden="true" />
                  </div>
                  <div>
                    <h3 className="font-heading text-base font-bold text-foreground">
                      Deadlines &amp; In-App Calendar
                    </h3>
                    <p className="text-xs text-muted-foreground font-mono">
                      Automated Temporal Parsing
                    </p>
                  </div>
                </div>
                <span className="rounded px-2 py-0.5 text-[10px] font-mono font-medium bg-muted text-muted-foreground border border-border">
                  Monthly Grid
                </span>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Dates, expiration deadlines, and milestone commitments are parsed from uploaded text via regex and LLM extractors, populated automatically into an in-app calendar with optional Google Calendar sync.
              </p>
            </div>

            <div className="mt-5 rounded-xl border border-border/70 bg-background p-4 flex flex-col gap-2">
              <div className="flex items-center justify-between text-[11px] font-mono text-muted-foreground border-b border-border/50 pb-1.5">
                <span>EXTRACTED EVENT</span>
                <span>STATUS: ACTIVE</span>
              </div>
              <div className="flex items-start justify-between gap-3 text-xs">
                <div>
                  <div className="font-semibold text-foreground">Notice of Non-Renewal</div>
                  <div className="text-muted-foreground text-[11px]">Due: November 1, 2026 · 60-day buffer</div>
                </div>
                <span className="rounded bg-amber-500/10 text-amber-900 dark:text-amber-200 border border-amber-500/30 px-2 py-0.5 text-[10px] font-mono font-bold">
                  PENDING
                </span>
              </div>
            </div>
          </div>

          {/* Card 4: Summaries & Audio Synthesizer (7 cols) */}
          <div className="md:col-span-12 lg:col-span-7 rounded-2xl border border-border/80 bg-card p-6 shadow-sm paper-folio flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between border-b border-border/60 pb-3 mb-4">
                <div className="flex items-center gap-2.5">
                  <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Volume2 className="size-4" aria-hidden="true" />
                  </div>
                  <div>
                    <h3 className="font-heading text-base font-bold text-foreground">
                      Document Summaries &amp; Neural Audio
                    </h3>
                    <p className="text-xs text-muted-foreground font-mono">
                      Map-Reduce &amp; Offline TTS
                    </p>
                  </div>
                </div>
                <span className="rounded px-2 py-0.5 text-[10px] font-mono font-medium bg-muted text-muted-foreground border border-border">
                  Piper &amp; Edge-TTS
                </span>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Large folios are distilled into executive summaries using map-reduce chunk passes. Synthesize high-fidelity voice audio on demand with Piper neural synthesis or Microsoft Edge-TTS with an in-app player.
              </p>
            </div>

            {/* Audio Wave Player Mock */}
            <div className="mt-5 rounded-xl border border-border/70 bg-muted/30 p-4 flex items-center justify-between gap-4 font-mono text-xs">
              <div className="flex items-center gap-3">
                <div className="flex size-9 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-xs shrink-0">
                  <Play className="size-4 ml-0.5" aria-hidden="true" />
                </div>
                <div>
                  <div className="font-semibold text-foreground">Summary_Audio_Folio.wav</div>
                  <div className="text-[11px] text-muted-foreground">Neural Voice · Piper en_US_ryan</div>
                </div>
              </div>
              <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                <span className="px-2 py-0.5 rounded bg-background border border-border">02:45 / 05:12</span>
              </div>
            </div>
          </div>

          {/* Card 5: Ingestion Pipeline & Tesseract OCR (6 cols) */}
          <div className="md:col-span-12 lg:col-span-6 rounded-2xl border border-border/80 bg-card p-6 shadow-sm paper-folio flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between border-b border-border/60 pb-3 mb-4">
                <div className="flex items-center gap-2.5">
                  <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <UploadCloud className="size-4" aria-hidden="true" />
                  </div>
                  <div>
                    <h3 className="font-heading text-base font-bold text-foreground">
                      Multi-Format Ingestion &amp; OCR
                    </h3>
                    <p className="text-xs text-muted-foreground font-mono">
                      PDF, DOCX, TXT, Scanned Images
                    </p>
                  </div>
                </div>
                <span className="rounded px-2 py-0.5 text-[10px] font-mono font-medium bg-muted text-muted-foreground border border-border">
                  SHA-256 Dedup
                </span>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Native document extraction pipelines handle digital PDFs via PyMuPDF, DOCX via python-docx, and physical paperwork via Tesseract OCR. Cryptographic hashes ensure identical documents are never processed twice.
              </p>
            </div>

            <div className="mt-5 pt-3 border-t border-border/50 grid grid-cols-4 gap-2 text-center font-mono text-[11px]">
              <div className="p-2 rounded bg-muted/40 border border-border/50">
                <div className="font-bold text-foreground">PDF</div>
                <div className="text-[10px] text-muted-foreground">PyMuPDF</div>
              </div>
              <div className="p-2 rounded bg-muted/40 border border-border/50">
                <div className="font-bold text-foreground">DOCX</div>
                <div className="text-[10px] text-muted-foreground">python-docx</div>
              </div>
              <div className="p-2 rounded bg-muted/40 border border-border/50">
                <div className="font-bold text-foreground">TXT</div>
                <div className="text-[10px] text-muted-foreground">UTF-8</div>
              </div>
              <div className="p-2 rounded bg-muted/40 border border-border/50">
                <div className="font-bold text-foreground">IMAGES</div>
                <div className="text-[10px] text-muted-foreground">Tesseract</div>
              </div>
            </div>
          </div>

          {/* Card 6: Semantic Hybrid Search (6 cols) */}
          <div className="md:col-span-12 lg:col-span-6 rounded-2xl border border-border/80 bg-card p-6 shadow-sm paper-folio flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between border-b border-border/60 pb-3 mb-4">
                <div className="flex items-center gap-2.5">
                  <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Search className="size-4" aria-hidden="true" />
                  </div>
                  <div>
                    <h3 className="font-heading text-base font-bold text-foreground">
                      Semantic &amp; Hybrid Search
                    </h3>
                    <p className="text-xs text-muted-foreground font-mono">
                      Sub-50ms Vector Retrieval
                    </p>
                  </div>
                </div>
                <span className="rounded px-2 py-0.5 text-[10px] font-mono font-medium bg-muted text-muted-foreground border border-border">
                  Ranked Distance
                </span>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Query terms retrieve the most relevant passages by conceptual meaning, matching synonyms and paraphrased clauses across thousands of stored chunks with explicit score cards and direct snippet jumping.
              </p>
            </div>

            <div className="mt-5 pt-3 border-t border-border/50 flex items-center justify-between font-mono text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5 text-foreground">
                <CheckCircle2 className="size-3.5 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
                <span>Zero Cloud Ingress / Egress</span>
              </span>
              <span>ChromaDB Local Engine</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
