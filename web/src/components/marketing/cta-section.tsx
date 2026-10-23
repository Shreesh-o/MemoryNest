import Link from "next/link"
import { ArrowRight, Sparkles } from "lucide-react"
import { buttonVariants } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export function CTASection() {
  return (
    <section aria-labelledby="cta-heading" className="py-20 sm:py-28 bg-muted/20 border-t border-border/40">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="relative overflow-hidden rounded-3xl border border-border/70 bg-gradient-to-b from-card via-card/90 to-background p-8 sm:p-14 lg:p-16 text-center shadow-lg">
          {/* Subtle Ambient Glow */}
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 -z-10 flex items-center justify-center"
          >
            <div className="size-96 rounded-full bg-primary/10 blur-3xl" />
          </div>

          {/* Badge */}
          <div className="inline-flex items-center gap-1.5 rounded-full border border-border/80 bg-background px-3.5 py-1 text-xs font-semibold uppercase tracking-wider text-primary mb-6 shadow-2xs">
            <Sparkles className="size-3.5 text-primary" aria-hidden="true" />
            <span>Begin Your Local Vault</span>
          </div>

          {/* Heading */}
          <h2
            id="cta-heading"
            className="font-heading text-3xl font-extrabold tracking-tight sm:text-4xl lg:text-5xl text-foreground max-w-3xl mx-auto text-balance"
          >
            Ready to turn your static documents into an active memory vault?
          </h2>

          <p className="mt-4 text-base sm:text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed text-balance">
            Install on your machine, drop in your files, and enjoy private, grounded AI search
            without monthly subscriptions or cloud leaks.
          </p>

          {/* CTA Buttons */}
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4 max-w-md mx-auto">
            <Link
              href="/register"
              className={cn(
                buttonVariants({ size: "lg" }),
                "w-full sm:w-auto font-medium shadow-md hover:shadow-lg transition-all group px-7 h-12 text-base rounded-xl"
              )}
            >
              <span>Get started free</span>
              <ArrowRight
                className="size-4 ml-1.5 transition-transform group-hover:translate-x-1"
                aria-hidden="true"
              />
            </Link>

            <Link
              href="/login"
              className={cn(
                buttonVariants({ variant: "outline", size: "lg" }),
                "w-full sm:w-auto font-medium px-7 h-12 text-base rounded-xl border-border hover:bg-muted/60"
              )}
            >
              Log in to vault
            </Link>
          </div>
        </div>
      </div>
    </section>
  )
}
