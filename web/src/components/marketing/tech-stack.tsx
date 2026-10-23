import { Code2, Zap, Terminal, Database, Server, Cpu, FileSearch } from "lucide-react"

export function TechStack() {
  const stack = [
    {
      name: "Next.js 16",
      role: "React 19 App Router",
      icon: Code2,
    },
    {
      name: "FastAPI",
      role: "Python REST Backend",
      icon: Zap,
    },
    {
      name: "Ollama",
      role: "Local LLM Runtime",
      icon: Terminal,
    },
    {
      name: "ChromaDB",
      role: "Local Vector Store",
      icon: Database,
    },
    {
      name: "SQLite",
      role: "Relational Metadata",
      icon: Server,
    },
    {
      name: "sentence-transformers",
      role: "all-MiniLM-L6-v2",
      icon: Cpu,
    },
    {
      name: "Tesseract",
      role: "Local OCR Extraction",
      icon: FileSearch,
    },
  ]

  return (
    <section
      aria-labelledby="tech-stack-heading"
      className="py-12 bg-background border-t border-border/70"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="text-left mb-6">
          <p
            id="tech-stack-heading"
            className="text-xs font-mono uppercase tracking-wider text-muted-foreground"
          >
            ARCHITECTURE INVENTORY // OPEN-SOURCE ENGINE
          </p>
        </div>

        {/* Badges Grid */}
        <div className="flex flex-wrap items-center gap-2.5 sm:gap-3">
          {stack.map((tech) => {
            const Icon = tech.icon
            return (
              <div
                key={tech.name}
                className="inline-flex items-center gap-2 rounded-lg border border-border/80 bg-card px-3 py-2 text-xs font-mono text-foreground shadow-2xs hover:border-primary/40 transition-colors"
              >
                <Icon className="size-3.5 text-primary shrink-0" aria-hidden="true" />
                <span className="font-semibold text-foreground">{tech.name}</span>
                <span className="text-muted-foreground text-[11px]">
                  ({tech.role})
                </span>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
