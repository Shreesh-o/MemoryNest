import Link from "next/link"
import { Archive, Cpu, Server, Terminal } from "lucide-react"

export function MarketingFooter() {
  const currentYear = 2026

  return (
    <footer className="border-t border-border/80 bg-background py-14 text-xs font-mono text-muted-foreground">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Main Colophon Grid */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-8 pb-10 border-b border-border/60">
          {/* Brand & Mission (5 cols) */}
          <div className="md:col-span-5 flex flex-col gap-3">
            <Link
              href="/"
              className="flex items-center gap-2.5 font-heading text-base font-bold text-foreground"
            >
              <div className="flex size-7 items-center justify-center rounded-lg bg-foreground text-background">
                <Archive className="size-3.5" aria-hidden="true" />
              </div>
              <span className="font-sans text-base font-bold tracking-tight">MemoryNest</span>
            </Link>
            <p className="text-muted-foreground max-w-sm leading-relaxed font-sans text-xs">
              Local-first personal knowledge manager. Grounded cited Q&amp;A, Document Map
              relationships, and automated calendar extraction running on your own hardware.
            </p>
            <div className="flex items-center gap-2 text-[11px] text-muted-foreground pt-1">
              <span className="size-2 rounded-full bg-emerald-500 inline-block" aria-hidden="true" />
              <span>Sovereignty Protocol: Active</span>
            </div>
          </div>

          {/* Engine Status Specs (4 cols) */}
          <div className="md:col-span-4 flex flex-col gap-2">
            <span className="font-semibold text-foreground tracking-wider uppercase text-[11px]">
              Local Enclave Interfaces
            </span>
            <div className="flex flex-col gap-1 text-[11px] text-muted-foreground pt-1">
              <span className="flex items-center gap-2">
                <Server className="size-3 text-primary" aria-hidden="true" />
                <span>REST API: 127.0.0.1:8000</span>
              </span>
              <span className="flex items-center gap-2">
                <Terminal className="size-3 text-primary" aria-hidden="true" />
                <span>Ollama Inference: 127.0.0.1:11434</span>
              </span>
              <span className="flex items-center gap-2">
                <Cpu className="size-3 text-primary" aria-hidden="true" />
                <span>Vector ChromaDB: SQLite Enclave</span>
              </span>
            </div>
          </div>

          {/* Navigation Links (3 cols) */}
          <div className="md:col-span-3 flex flex-col gap-2">
            <span className="font-semibold text-foreground tracking-wider uppercase text-[11px]">
              Navigation
            </span>
            <nav className="flex flex-col gap-1.5 pt-1" aria-label="Footer Navigation">
              <a href="#features" className="hover:text-foreground transition-colors">
                {"// Capabilities"}
              </a>
              <a href="#how-it-works" className="hover:text-foreground transition-colors">
                {"// Pipeline Architecture"}
              </a>
              <a href="#privacy" className="hover:text-foreground transition-colors">
                {"// Data Sovereignty"}
              </a>
              <Link href="/login" className="hover:text-foreground transition-colors">
                {"// Log in to Session"}
              </Link>
              <Link href="/register" className="hover:text-foreground transition-colors">
                {"// Initialize Vault"}
              </Link>
            </nav>
          </div>
        </div>

        {/* Archival Footnote */}
        <div className="pt-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-[11px] text-muted-foreground">
          <p>© {currentYear} MemoryNest. Open Source under the MIT License.</p>
          <div className="flex items-center gap-4">
            <span>Local-first architecture</span>
            <span>·</span>
            <span>Zero cloud telemetry</span>
          </div>
        </div>
      </div>
    </footer>
  )
}
