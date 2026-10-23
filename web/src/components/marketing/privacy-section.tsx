import { ShieldCheck, Lock, HardDrive, Cpu, Radio, Check, Info } from "lucide-react"

export function PrivacySection() {
  const localGuarantees = [
    {
      title: "Local LLM via Ollama",
      desc: "Answers are computed locally on your CPU/GPU using open-weight models (qwen2.5:3b-instruct). Documents and chat history never leave your machine to train external models.",
      icon: Cpu,
    },
    {
      title: "Local Vector Store & SQLite",
      desc: "ChromaDB vector indices and SQLite relational metadata exist exclusively on your local disk. Embeddings are generated with sentence-transformers without external API calls.",
      icon: HardDrive,
    },
    {
      title: "Strict Per-User Data Isolation",
      desc: "Every record, chunk, and vector is partitioned by user_id with cascading foreign keys and bcrypt password hashing. Multi-tenant privacy is enforced at the database layer.",
      icon: Lock,
    },
    {
      title: "Fernet Encrypted Credentials",
      desc: "Session tokens are managed with secure HTTP-only cookies, and third-party tokens (such as Google OAuth refresh tokens) are encrypted on disk via Fernet encryption.",
      icon: ShieldCheck,
    },
  ]

  return (
    <section
      id="privacy"
      aria-labelledby="privacy-heading"
      className="py-16 sm:py-24 bg-muted/20 border-t border-border/70"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-left max-w-3xl mb-12 sm:mb-16">
          <div className="inline-flex items-center gap-1.5 rounded-md border border-border/80 bg-background px-2.5 py-1 text-xs font-mono uppercase tracking-wider text-muted-foreground mb-3 shadow-2xs">
            <span>SOVEREIGNTY PROTOCOL // LOCAL ENCLAVE</span>
          </div>
          <h2
            id="privacy-heading"
            className="font-heading text-3xl font-extrabold tracking-tight sm:text-4xl lg:text-5xl text-foreground text-balance"
          >
            Physical custody of your knowledge.
          </h2>
          <p className="mt-4 text-base sm:text-lg text-muted-foreground leading-relaxed text-balance">
            Your personal contracts, notes, and records remain on your own silicon.
            MemoryNest is designed from the database up for complete user autonomy.
          </p>
        </div>

        {/* 4 Feature Pillars */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-8">
          {localGuarantees.map((item) => {
            const Icon = item.icon
            return (
              <div
                key={item.title}
                className="rounded-2xl border border-border/80 bg-card p-6 shadow-sm paper-folio flex items-start gap-4"
              >
                <div className="size-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center shrink-0 mt-0.5">
                  <Icon className="size-5" aria-hidden="true" />
                </div>
                <div>
                  <h3 className="font-heading text-base font-bold text-foreground mb-1">
                    {item.title}
                  </h3>
                  <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
                    {item.desc}
                  </p>
                </div>
              </div>
            )
          })}
        </div>

        {/* Transparent Opt-in Notice Box */}
        <div className="rounded-2xl border border-border/80 bg-card p-6 sm:p-7 shadow-sm paper-folio">
          <div className="flex items-start gap-4">
            <div className="size-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center shrink-0 mt-0.5">
              <Radio className="size-5" aria-hidden="true" />
            </div>
            <div className="space-y-3 w-full">
              <div className="flex items-center justify-between border-b border-border/50 pb-2">
                <h3 className="font-heading text-base font-bold text-foreground">
                  Precise Disclosure on External Services (Strictly Opt-In)
                </h3>
                <span className="font-mono text-[11px] text-muted-foreground">AUDIT TRANSPARENCY</span>
              </div>
              <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
                MemoryNest is local-first. We do not claim it is 100% offline because three optional
                capabilities connect to external services only when explicitly configured by the user:
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs pt-1">
                <div className="flex flex-col gap-1 bg-muted/40 p-3 rounded-xl border border-border/60">
                  <span className="font-semibold text-foreground flex items-center gap-1.5">
                    <Check className="size-3.5 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
                    <span>Google Calendar Sync</span>
                  </span>
                  <span className="text-muted-foreground text-[11px] leading-relaxed">
                    Transmits extracted event dates to Google Calendar only when OAuth is authorized.
                  </span>
                </div>
                <div className="flex flex-col gap-1 bg-muted/40 p-3 rounded-xl border border-border/60">
                  <span className="font-semibold text-foreground flex items-center gap-1.5">
                    <Check className="size-3.5 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
                    <span>Edge-TTS Audio Voice</span>
                  </span>
                  <span className="text-muted-foreground text-[11px] leading-relaxed">
                    Optional online voice uses Microsoft Edge-TTS; Piper and espeak run 100% locally.
                  </span>
                </div>
                <div className="flex flex-col gap-1 bg-muted/40 p-3 rounded-xl border border-border/60">
                  <span className="font-semibold text-foreground flex items-center gap-1.5">
                    <Check className="size-3.5 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
                    <span>SMTP Email Alerts</span>
                  </span>
                  <span className="text-muted-foreground text-[11px] leading-relaxed">
                    Sends reminder notifications through your configured Gmail SMTP credentials.
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2 text-[11px] font-mono text-muted-foreground pt-2">
                <Info className="size-3.5 text-primary shrink-0" aria-hidden="true" />
                <span>Zero telemetry, trackers, or marketing analytics are ever embedded.</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
