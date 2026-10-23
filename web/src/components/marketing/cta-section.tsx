import Link from "next/link"
import { ArrowRight, ShieldCheck, HardDrive, Lock } from "lucide-react"
import { buttonVariants } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export function CTASection() {
  return (
    <section aria-labelledby="cta-heading" className="py-16 sm:py-24 bg-muted/20 border-t border-border/70">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="rounded-2xl border border-border/80 bg-card p-8 sm:p-14 lg:p-16 text-left shadow-sm paper-folio flex flex-col lg:flex-row lg:items-center lg:justify-between gap-8">
          <div className="max-w-2xl">
            {/* Archival Badge */}
            <div className="inline-flex items-center gap-1.5 rounded-md border border-border/80 bg-muted/50 px-2.5 py-1 text-xs font-mono uppercase tracking-wider text-muted-foreground mb-4 shadow-2xs">
              <span className="size-2 rounded-full bg-emerald-500" aria-hidden="true" />
              <span>SOVEREIGN ARCHIVAL ENCLAVE</span>
            </div>

            {/* Heading */}
            <h2
              id="cta-heading"
              className="font-heading text-3xl font-extrabold tracking-tight sm:text-4xl text-foreground text-balance"
            >
              Establish your private knowledge vault.
            </h2>

            <p className="mt-4 text-base text-muted-foreground leading-relaxed text-balance">
              Deploy locally on your workstation, drop in your documents, and experience
              grounded, cited AI queries without cloud exposure or monthly subscriptions.
            </p>

            {/* Reassurance points */}
            <div className="mt-6 flex flex-wrap items-center gap-4 text-xs font-mono text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <HardDrive className="size-3.5 text-primary" aria-hidden="true" />
                <span>100% Local Disk Storage</span>
              </span>
              <span className="flex items-center gap-1.5">
                <Lock className="size-3.5 text-primary" aria-hidden="true" />
                <span>Per-User Database Isolation</span>
              </span>
              <span className="flex items-center gap-1.5">
                <ShieldCheck className="size-3.5 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
                <span>Zero Telemetry</span>
              </span>
            </div>
          </div>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row lg:flex-col items-stretch gap-3 shrink-0 sm:w-64">
            <Link
              href="/register"
              className={cn(
                buttonVariants({ size: "lg" }),
                "font-semibold shadow-xs transition-all group px-6 h-12 text-sm rounded-xl flex items-center justify-center gap-2"
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
                "font-medium px-6 h-12 text-sm rounded-xl border-border hover:bg-muted/60 flex items-center justify-center"
              )}
            >
              Log in to Session
            </Link>
          </div>
        </div>
      </div>
    </section>
  )
}
