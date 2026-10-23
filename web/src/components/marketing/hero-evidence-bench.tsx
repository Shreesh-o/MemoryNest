"use client"

import * as React from "react"
import { ShieldCheck, FileText, CornerDownRight, Sparkles, Binary, Cpu } from "lucide-react"

interface Scenario {
  id: string
  title: string
  filename: string
  page: number
  chunkId: string
  similarity: number
  query: string
  answer: string
  sourceSnippet: string
  sourcePrefix: string
  highlightedText: string
  sourceSuffix: string
  latency: string
  tokenCount: number
}

const SCENARIOS: Scenario[] = [
  {
    id: "lease",
    title: "Lease Notice Terms",
    filename: "Residential_Lease_Agreement_2026.pdf",
    page: 14,
    chunkId: "chk_088b",
    similarity: 0.892,
    query: "When is the deadline to issue notice of non-renewal, and what is the exact required period?",
    answer:
      "Notice of non-renewal must be delivered in writing at least 60 calendar days prior to the expiration date. Based on the lease term ending December 31, 2026, the final date to deliver notice is November 1, 2026.",
    sourcePrefix:
      "Section 14.1 Renewal. Either party may elect not to renew upon written notification. ",
    highlightedText:
      "Section 14.2 Notice Period. Such written notice of non-renewal must be delivered at least sixty (60) calendar days prior to the final calendar day of the Initial Term.",
    sourceSuffix:
      " Failure to provide timely notice shall result in a month-to-month extension under standard rates.",
    sourceSnippet:
      "Section 14.2 Notice Period. Such written notice of non-renewal must be delivered at least sixty (60) calendar days prior to the final calendar day of the Initial Term.",
    latency: "142ms",
    tokenCount: 48,
  },
  {
    id: "ip",
    title: "IP Assignment Clause",
    filename: "Master_Services_Contract_v3.docx",
    page: 8,
    chunkId: "chk_041e",
    similarity: 0.915,
    query: "Does the contractor retain ownership of pre-existing intellectual property and open-source tooling?",
    answer:
      "Yes. The contractor retains full ownership of all Background Technology and pre-existing open-source libraries incorporated into deliverables, granting the client a non-exclusive perpetual license.",
    sourcePrefix:
      "Article 7.3 Work Product. Subject to Section 7.4, Work Product belongs to Client. ",
    highlightedText:
      "Article 7.4 Background Technology. Contractor retains sole ownership of all pre-existing software, frameworks, and open-source libraries authored prior to the Effective Date.",
    sourceSuffix:
      " Client is granted an irrevocable, royalty-free, perpetual license to use such Background Technology.",
    sourceSnippet:
      "Article 7.4 Background Technology. Contractor retains sole ownership of all pre-existing software, frameworks, and open-source libraries authored prior to the Effective Date.",
    latency: "118ms",
    tokenCount: 42,
  },
  {
    id: "medical",
    title: "Clinical Lab Results",
    filename: "Diagnostic_Panel_Report_Oct.pdf",
    page: 2,
    chunkId: "chk_019a",
    similarity: 0.874,
    query: "What was the reported fasting glucose level and does it exceed reference standard ranges?",
    answer:
      "The fasting plasma glucose was measured at 94 mg/dL. This is strictly within the normal reference standard of 70 to 99 mg/dL; no elevated flag was triggered.",
    sourcePrefix:
      "Metabolic Profile (Fasting 12h). Specimen collected 08:30 EST. ",
    highlightedText:
      "GLUCOSE, FASTING: 94 mg/dL. Reference Interval: 70 - 99 mg/dL. Status: Within normal limits. Prior historical comparison: 92 mg/dL.",
    sourceSuffix:
      " Hemoglobin A1c measured at 5.4% of total hemoglobin (reference < 5.7%).",
    sourceSnippet:
      "GLUCOSE, FASTING: 94 mg/dL. Reference Interval: 70 - 99 mg/dL. Status: Within normal limits.",
    latency: "96ms",
    tokenCount: 36,
  },
]

export function HeroEvidenceBench() {
  const [activeScenarioId, setActiveScenarioId] = React.useState<string>("lease")
  const [isRayIlluminated, setIsRayIlluminated] = React.useState<boolean>(true)

  const active = React.useMemo(() => {
    return SCENARIOS.find((s) => s.id === activeScenarioId) ?? SCENARIOS[0]
  }, [activeScenarioId])

  return (
    <div className="w-full flex flex-col gap-3">
      {/* Scenario Selector Tabs */}
      <div
        role="tablist"
        aria-label="Evidence bench scenarios"
        className="flex items-center gap-1.5 p-1 rounded-xl bg-muted/60 border border-border/80 overflow-x-auto text-xs"
      >
        <span className="px-2.5 py-1 text-[11px] font-mono uppercase tracking-wider text-muted-foreground shrink-0 flex items-center gap-1">
          <Binary className="size-3 text-primary" aria-hidden="true" />
          <span>Evidence:</span>
        </span>
        {SCENARIOS.map((scenario) => {
          const isSelected = scenario.id === activeScenarioId
          return (
            <button
              key={scenario.id}
              role="tab"
              aria-selected={isSelected}
              onClick={() => setActiveScenarioId(scenario.id)}
              className={`px-3 py-1.5 rounded-lg font-medium transition-all shrink-0 flex items-center gap-1.5 ${
                isSelected
                  ? "bg-background text-foreground shadow-xs border border-border/80 font-semibold"
                  : "text-muted-foreground hover:text-foreground hover:bg-background/40"
              }`}
            >
              <span>{scenario.title}</span>
            </button>
          )
        })}
      </div>

      {/* The Evidence Bench Container */}
      <div className="rounded-2xl border border-border/90 bg-card p-4 sm:p-6 shadow-sm paper-folio text-card-foreground flex flex-col gap-5 relative overflow-hidden">
        {/* Bench Header & Coordinates */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 pb-3 text-xs">
          <div className="flex items-center gap-2">
            <span className="size-2 rounded-full bg-emerald-500 animate-pulse" aria-hidden="true" />
            <span className="font-mono text-[11px] font-semibold tracking-wider uppercase text-foreground">
              {active.filename}
            </span>
          </div>
          <div className="flex items-center gap-3 font-mono text-[11px] text-muted-foreground">
            <span>PAGE {active.page}</span>
            <span className="text-border">|</span>
            <span>{active.chunkId}</span>
            <span className="text-border">|</span>
            <span className="text-emerald-700 dark:text-emerald-400 font-semibold">
              SIM {(active.similarity * 100).toFixed(1)}%
            </span>
          </div>
        </div>

        {/* Dual-Pane Grid: Query & Response (Left) + Document Leaf (Right) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch relative">
          {/* Left Column: Query and Answer (5 cols) */}
          <div className="lg:col-span-6 flex flex-col justify-between gap-4">
            {/* User Query Block */}
            <div className="rounded-xl border border-border/70 bg-muted/40 p-3.5 flex flex-col gap-1.5">
              <div className="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
                <span>Natural Language Query</span>
                <span>User Input</span>
              </div>
              <p className="text-xs sm:text-sm font-medium text-foreground leading-snug">
                &ldquo;{active.query}&rdquo;
              </p>
            </div>

            {/* Grounded LLM Response Block */}
            <div
              onMouseEnter={() => setIsRayIlluminated(true)}
              className="rounded-xl border border-primary/30 bg-primary/[0.03] dark:bg-primary/[0.06] p-4 flex flex-col gap-2 relative transition-all"
            >
              <div className="flex items-center justify-between text-[11px] font-mono text-muted-foreground border-b border-border/40 pb-1.5">
                <span className="flex items-center gap-1.5 font-semibold text-foreground">
                  <Sparkles className="size-3.5 text-primary" aria-hidden="true" />
                  <span>Grounded Inference</span>
                </span>
                <span>Refusal Gate: Active</span>
              </div>

              <p className="text-xs sm:text-sm leading-relaxed text-foreground">
                {active.answer}
              </p>

              {/* Exact Citation Tether Chip */}
              <div className="mt-1 pt-2 border-t border-border/40 flex items-center justify-between">
                <div className="inline-flex items-center gap-1.5 rounded-md bg-primary/10 px-2 py-1 text-[11px] font-mono font-medium text-primary border border-primary/20">
                  <CornerDownRight className="size-3" aria-hidden="true" />
                  <span>
                    Citation: [{active.filename} · p.{active.page}]
                  </span>
                </div>
                <span className="text-[10px] font-mono text-muted-foreground">
                  Verified 100%
                </span>
              </div>
            </div>
          </div>

          {/* Right Column: Physical Document Folio Sheet (6 cols) */}
          <div className="lg:col-span-6 flex flex-col">
            <div className="h-full rounded-xl border border-border/80 bg-background/90 p-4 sm:p-5 flex flex-col justify-between shadow-2xs relative">
              {/* Document Header & Margin Rules */}
              <div className="flex items-center justify-between border-b border-border/60 pb-2 mb-3 text-[11px] font-mono text-muted-foreground">
                <div className="flex items-center gap-1.5">
                  <FileText className="size-3.5 text-foreground" aria-hidden="true" />
                  <span className="font-semibold text-foreground">DOCUMENT FOLIO</span>
                </div>
                <span>OPTICAL MARGIN CALIPER</span>
              </div>

              {/* Rendered Text with Highlighting */}
              <div className="relative text-xs sm:text-[13px] leading-relaxed text-foreground/80 font-serif">
                <span className="text-muted-foreground">{active.sourcePrefix}</span>
                <mark
                  className={`px-1 py-0.5 rounded transition-all font-sans font-medium ${
                    isRayIlluminated
                      ? "bg-amber-300/40 text-foreground dark:bg-amber-400/25 border-l-2 border-primary pl-1.5"
                      : "bg-amber-200/20 text-foreground"
                  }`}
                >
                  {active.highlightedText}
                </mark>
                <span className="text-muted-foreground">{active.sourceSuffix}</span>
              </div>

              {/* Document Metadata Strip */}
              <div className="mt-4 pt-2.5 border-t border-border/50 flex items-center justify-between font-mono text-[10px] text-muted-foreground">
                <span>EXTRACTED CHUNK: ~450 CHARACTERS</span>
                <span>SHA-256 VERIFIED</span>
              </div>
            </div>
          </div>
        </div>

        {/* Telemetry Footer */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-border/60 text-[11px] font-mono text-muted-foreground">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1 text-foreground">
              <Cpu className="size-3 text-primary" aria-hidden="true" />
              <span>Ollama (qwen2.5:3b)</span>
            </span>
            <span>·</span>
            <span>Latency: {active.latency}</span>
            <span>·</span>
            <span>{active.tokenCount} tokens</span>
          </div>
          <div className="flex items-center gap-1.5 text-emerald-700 dark:text-emerald-400 font-medium">
            <ShieldCheck className="size-3.5" aria-hidden="true" />
            <span>Executed entirely on localhost (no network egress)</span>
          </div>
        </div>
      </div>
    </div>
  )
}
