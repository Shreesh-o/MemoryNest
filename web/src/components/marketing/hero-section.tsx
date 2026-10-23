import Link from "next/link"
import { ArrowRight, Cpu, HardDrive, Lock } from "lucide-react"
import { buttonVariants } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { HeroEvidenceBench } from "./hero-evidence-bench"

export function HeroSection() {
  return (
    <section
      aria-labelledby="hero-heading"
      className="relative overflow-hidden pt-10 pb-16 sm:pt-16 sm:pb-24 lg:pt-20 lg:pb-28"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 items-center gap-10 lg:grid-cols-12 lg:gap-10">
          {/* Left Column: Headline and CTAs (5 cols on desktop) */}
          <div className="flex flex-col items-start text-left lg:col-span-5">
            {/* Archival Coordinate Badge */}
            <div className="inline-flex items-center gap-2 rounded-lg border border-border/80 bg-muted/50 px-3 py-1 text-xs font-mono font-medium text-foreground mb-6 shadow-2xs">
              <span className="size-2 rounded-full bg-emerald-500 animate-pulse" aria-hidden="true" />
              <span>LOCAL-FIRST KNOWLEDGE ENCLAVE</span>
            </div>

            {/* H1 Heading */}
            <h1
              id="hero-heading"
              className="font-heading text-4xl font-extrabold tracking-tight sm:text-5xl lg:text-6xl text-foreground text-balance leading-[1.04]"
            >
              Every claim anchored to verifiable citations on your own machine.
            </h1>

            {/* Subtitle */}
            <p className="mt-5 text-base sm:text-lg text-muted-foreground leading-relaxed text-balance">
              MemoryNest is a local-first personal knowledge manager. Ingest PDFs, Word
              documents, and scanned records into a private SQLite &amp; ChromaDB vault. Ask
              questions with cited excerpts that never hallucinate, explore your Document Map,
              and track extracted deadlines.
            </p>

            {/* CTA Buttons */}
            <div className="mt-8 flex flex-col sm:flex-row items-stretch sm:items-center gap-3 w-full sm:w-auto">
              <Link
                href="/register"
                className={cn(
                  buttonVariants({ size: "lg" }),
                  "font-medium shadow-sm transition-all group px-6 h-12 text-sm sm:text-base rounded-xl flex items-center justify-center gap-2"
                )}
              >
                <span>Initialize Vault</span>
                <ArrowRight
                  className="size-4 transition-transform group-hover:translate-x-1"
                  aria-hidden="true"
                />
              </Link>

              <Link
                href="/login"
                className={cn(
                  buttonVariants({ variant: "outline", size: "lg" }),
                  "font-medium px-6 h-12 text-sm sm:text-base rounded-xl border-border hover:bg-muted/60 flex items-center justify-center"
                )}
              >
                Open Session
              </Link>
            </div>

            {/* Technical Hardware Guarantees */}
            <div className="mt-10 pt-6 border-t border-border/60 grid grid-cols-3 gap-2 w-full text-xs font-mono text-muted-foreground">
              <div className="flex flex-col gap-1">
                <span className="flex items-center gap-1.5 text-foreground font-semibold">
                  <Cpu className="size-3.5 text-primary shrink-0" aria-hidden="true" />
                  <span>Ollama LLM</span>
                </span>
                <span className="text-[11px] text-muted-foreground">Local weights</span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="flex items-center gap-1.5 text-foreground font-semibold">
                  <HardDrive className="size-3.5 text-primary shrink-0" aria-hidden="true" />
                  <span>ChromaDB</span>
                </span>
                <span className="text-[11px] text-muted-foreground">Vector storage</span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="flex items-center gap-1.5 text-foreground font-semibold">
                  <Lock className="size-3.5 text-emerald-700 dark:text-emerald-400 shrink-0" aria-hidden="true" />
                  <span>User Isolation</span>
                </span>
                <span className="text-[11px] text-muted-foreground">Strict per-user data</span>
              </div>
            </div>
          </div>

          {/* Right Column: Hero Visual Evidence Bench (7 cols on desktop) */}
          <div className="w-full lg:col-span-7">
            <HeroEvidenceBench />
          </div>
        </div>
      </div>
    </section>
  )
}
