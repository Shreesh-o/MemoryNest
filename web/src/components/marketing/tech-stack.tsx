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
      className="py-16 2xl:py-24 bg-background border-t border-border/40"
    >
      <div className="mx-auto max-w-7xl 2xl:max-w-[1536px] 3xl:max-w-[1720px] px-4 sm:px-6 lg:px-8 2xl:px-12">
        <div className="text-center mb-8 2xl:mb-12">
          <p
            id="tech-stack-heading"
            className="text-xs 2xl:text-sm font-semibold uppercase tracking-wider text-muted-foreground"
          >
            Built on proven open-source technologies
          </p>
        </div>

        {/* Badges Grid */}
        <div className="flex flex-wrap items-center justify-center gap-3 sm:gap-4 2xl:gap-5 max-w-5xl 2xl:max-w-none mx-auto">
          {stack.map((tech) => {
            const Icon = tech.icon
            return (
              <div
                key={tech.name}
                className="inline-flex items-center gap-2 2xl:gap-2.5 rounded-xl 2xl:rounded-2xl border border-border/70 bg-card px-3.5 py-2 2xl:px-5 2xl:py-3 text-xs 2xl:text-sm font-medium text-foreground shadow-2xs hover:border-primary/40 transition-colors"
              >
                <Icon className="size-4 2xl:size-5 text-primary shrink-0" aria-hidden="true" />
                <span className="font-semibold text-foreground">{tech.name}</span>
                <span className="text-muted-foreground font-normal text-[11px] 2xl:text-xs">
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
