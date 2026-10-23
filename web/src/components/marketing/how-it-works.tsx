import { UploadCloud, Cpu, CalendarCheck, Binary, ChevronRight } from "lucide-react"

export function HowItWorks() {
  const stages = [
    {
      step: "01",
      title: "Local Ingestion & Deduplication",
      desc: "Drop in PDFs, Word documents, plain text, or scanned receipts. PyMuPDF, python-docx, and Tesseract extract raw content with SHA-256 hashing to eliminate redundant processing.",
      icon: UploadCloud,
      meta: "PyMuPDF · Tesseract OCR · SHA-256",
    },
    {
      step: "02",
      title: "Sentence Chunker & Vectorization",
      desc: "Text is partitioned into sentence-aware chunks of approximately 450 characters. Embeddings are generated locally using the sentence-transformers all-MiniLM-L6-v2 model and stored in ChromaDB.",
      icon: Binary,
      meta: "450-char chunks · ChromaDB vector store",
    },
    {
      step: "03",
      title: "Grounded Retrieval & Local Inference",
      desc: "Queries trigger vector similarity retrieval. If chunks satisfy the strict similarity gate, Ollama executes local inference (qwen2.5:3b) with verifiable citations; otherwise, it reports insufficient context.",
      icon: Cpu,
      meta: "Ollama (qwen2.5:3b) · Sim Gate > 0.30",
    },
    {
      step: "04",
      title: "Temporal Parsing & Calendar Stream",
      desc: "Regex patterns and LLM date extractors detect deadlines and obligations, streaming them into an in-app monthly calendar with scheduled reminders and optional Google Calendar OAuth synchronization.",
      icon: CalendarCheck,
      meta: "In-app calendar · Google Calendar OAuth",
    },
  ]

  return (
    <section
      id="how-it-works"
      aria-labelledby="how-it-works-heading"
      className="py-16 sm:py-24 bg-background relative overflow-hidden border-t border-border/70"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-left max-w-3xl mb-12 sm:mb-16">
          <div className="inline-flex items-center gap-1.5 rounded-md border border-border/80 bg-muted/60 px-2.5 py-1 text-xs font-mono uppercase tracking-wider text-muted-foreground mb-3 shadow-2xs">
            <span>PIPELINE SPECIFICATION // 4-STAGE ENCLAVE</span>
          </div>
          <h2
            id="how-it-works-heading"
            className="font-heading text-3xl font-extrabold tracking-tight sm:text-4xl lg:text-5xl text-foreground text-balance"
          >
            How MemoryNest processes documents.
          </h2>
          <p className="mt-4 text-base sm:text-lg text-muted-foreground leading-relaxed text-balance">
            Four sequential stages from binary disk read to grounded answers and calendar milestones.
            Every computation occurs inside your local user boundary.
          </p>
        </div>

        {/* 4 Architectural Process Plates */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          {stages.map((stage) => {
            const Icon = stage.icon
            return (
              <div
                key={stage.step}
                className="rounded-2xl border border-border/80 bg-card p-6 shadow-sm paper-folio flex flex-col justify-between hover:border-primary/40 transition-colors"
              >
                <div>
                  <div className="flex items-center justify-between border-b border-border/50 pb-3 mb-4">
                    <span className="font-mono text-xs font-bold text-primary">
                      PHASE {stage.step}
                    </span>
                    <div className="size-8 rounded-lg bg-muted flex items-center justify-center text-foreground">
                      <Icon className="size-4" aria-hidden="true" />
                    </div>
                  </div>

                  <h3 className="font-heading text-base font-bold text-foreground mb-2">
                    {stage.title}
                  </h3>

                  <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
                    {stage.desc}
                  </p>
                </div>

                <div className="mt-6 pt-3 border-t border-border/50 font-mono text-[11px] text-muted-foreground flex items-center gap-1">
                  <ChevronRight className="size-3 text-primary shrink-0" aria-hidden="true" />
                  <span>{stage.meta}</span>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
