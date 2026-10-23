import { ShieldCheck, Lock, HardDrive, Cpu, Radio, Check, Info } from "lucide-react"

export function PrivacySection() {
  const localGuarantees = [
    {
      title: "Local LLM via Ollama",
      desc: "Answers are inferred locally on your CPU/GPU using open-weight models (qwen2.5:3b-instruct). Documents and chat history never train external AI.",
      icon: Cpu,
    },
    {
      title: "Local Vector Store & SQLite",
      desc: "ChromaDB and SQLite run directly on your filesystem. Embeddings (all-MiniLM-L6-v2) are generated locally without third-party vector cloud services.",
      icon: HardDrive,
    },
    {
      title: "Strict Per-User Isolation",
      desc: "Every database record, chunk, and vector embedding is strictly scoped by user_id with cascading foreign keys and bcrypt-hashed authentication.",
      icon: Lock,
    },
    {
      title: "Encrypted Credentials & Cookies",
      desc: "Session tokens are managed via secure HTTP-only cookies, and third-party tokens (like Google OAuth refresh keys) are encrypted using Fernet.",
      icon: ShieldCheck,
    },
  ]

  return (
    <section
      id="privacy"
      aria-labelledby="privacy-heading"
      className="py-20 sm:py-28 bg-muted/20 border-t border-border/40"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-1.5 rounded-full border border-border/80 bg-background px-3 py-1 text-xs font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 mb-4 shadow-2xs">
            Data Sovereignty
          </div>
          <h2
            id="privacy-heading"
            className="font-heading text-3xl font-extrabold tracking-tight sm:text-4xl lg:text-5xl text-foreground text-balance"
          >
            Local-first by design
          </h2>
          <p className="mt-4 text-base sm:text-lg text-muted-foreground leading-relaxed text-balance">
            Your personal notes, financial files, contracts, and medical records stay under your
            control. MemoryNest is built to run self-hosted on your own hardware.
          </p>
        </div>

        {/* 4 Feature Pillars */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-5xl mx-auto">
          {localGuarantees.map((item) => {
            const Icon = item.icon
            return (
              <div
                key={item.title}
                className="rounded-2xl border border-border/70 bg-card p-6 shadow-xs flex items-start gap-4"
              >
                <div className="size-11 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0 mt-0.5">
                  <Icon className="size-5" aria-hidden="true" />
                </div>
                <div>
                  <h3 className="font-heading text-base font-bold text-foreground mb-1">
                    {item.title}
                  </h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {item.desc}
                  </p>
                </div>
              </div>
            )
          })}
        </div>

        {/* Transparent Opt-in Notice Box */}
        <div className="mt-10 max-w-5xl mx-auto rounded-2xl border border-border/70 bg-background p-6 sm:p-7 shadow-xs">
          <div className="flex items-start gap-4">
            <div className="size-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center shrink-0 mt-0.5">
              <Radio className="size-5" aria-hidden="true" />
            </div>
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <h3 className="font-heading text-base font-bold text-foreground">
                  Accurate Disclosure on External Services (Strictly Opt-In)
                </h3>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">
                We believe in complete transparency: MemoryNest is local-first, but we do not claim
                it is 100% offline because certain optional features integrate with third-party
                services when explicitly configured:
              </p>
              <ul className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs text-muted-foreground pt-1">
                <li className="flex items-start gap-2 bg-muted/50 p-2.5 rounded-lg border border-border/40">
                  <Check className="size-4 text-emerald-500 shrink-0 mt-0.5" aria-hidden="true" />
                  <span>
                    <strong className="text-foreground">Google Calendar:</strong> Only connects if
                    you link your Google account to push event dates.
                  </span>
                </li>
                <li className="flex items-start gap-2 bg-muted/50 p-2.5 rounded-lg border border-border/40">
                  <Check className="size-4 text-emerald-500 shrink-0 mt-0.5" aria-hidden="true" />
                  <span>
                    <strong className="text-foreground">Online TTS Voice:</strong> edge-tts requests
                    neural voice audio from Microsoft online; offline engines (piper, espeak) run locally.
                  </span>
                </li>
                <li className="flex items-start gap-2 bg-muted/50 p-2.5 rounded-lg border border-border/40">
                  <Check className="size-4 text-emerald-500 shrink-0 mt-0.5" aria-hidden="true" />
                  <span>
                    <strong className="text-foreground">Email Reminders:</strong> Connects to your
                    configured Gmail SMTP account only when sending due alerts.
                  </span>
                </li>
              </ul>
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground pt-1">
                <Info className="size-3.5 text-primary shrink-0" aria-hidden="true" />
                <span>
                  No telemetry, analytics, or background tracking are ever compiled or sent home.
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
