import Link from "next/link"
import { ArrowRight, Sparkles } from "lucide-react"
import { buttonVariants } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export function CTASection() {
  return (
    <section aria-labelledby="cta-heading" className="py-20 sm:py-28 2xl:py-36 bg-muted/20 border-t border-border/40">
      <div className="mx-auto max-w-7xl 2xl:max-w-[1536px] 3xl:max-w-[1720px] px-4 sm:px-6 lg:px-8 2xl:px-12">
        <div className="relative overflow-hidden rounded-3xl 2xl:rounded-4xl border border-border/70 bg-gradient-to-b from-card via-card/90 to-background p-8 sm:p-14 lg:p-16 2xl:p-24 text-center shadow-lg">
          {/* Subtle Ambient Glow */}
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 -z-10 flex items-center justify-center"
          >
            <div className="size-96 2xl:size-[32rem] rounded-full bg-primary/10 blur-3xl" />
          </div>

          {/* Badge */}
          <div className="inline-flex items-center gap-1.5 rounded-full border border-border/80 bg-background px-3.5 py-1 2xl:px-4 2xl:py-1.5 text-xs 2xl:text-sm font-semibold uppercase tracking-wider text-primary mb-6 2xl:mb-8 shadow-2xs">
            <Sparkles className="size-3.5 2xl:size-4 text-primary" aria-hidden="true" />
            <span>Begin Your Local Vault</span>
          </div>

          {/* Heading */}
          <h2
            id="cta-heading"
            className="font-heading text-3xl font-extrabold tracking-tight sm:text-4xl lg:text-5xl 2xl:text-6xl text-foreground max-w-3xl 2xl:max-w-5xl mx-auto text-balance"
          >
            Ready to turn your static documents into an active memory vault?
          </h2>

          <p className="mt-4 2xl:mt-6 text-base sm:text-lg 2xl:text-xl text-muted-foreground max-w-2xl 2xl:max-w-3xl mx-auto leading-relaxed text-balance">
            Install on your machine, drop in your files, and enjoy private, grounded AI search
            without monthly subscriptions or cloud leaks.
          </p>

          {/* CTA Buttons */}
          <div className="mt-8 2xl:mt-10 flex flex-col sm:flex-row items-center justify-center gap-4 2xl:gap-5 max-w-md 2xl:max-w-lg mx-auto">
            <Link
              href="/register"
              className={cn(
                buttonVariants({ size: "lg" }),
                "w-full sm:w-auto font-medium shadow-md hover:shadow-lg transition-all group px-7 2xl:px-8 h-12 2xl:h-14 text-base 2xl:text-lg rounded-xl 2xl:rounded-2xl"
              )}
            >
              <span>Get started free</span>
              <ArrowRight
                className="size-4 2xl:size-5 ml-1.5 transition-transform group-hover:translate-x-1"
                aria-hidden="true"
              />
            </Link>

            <Link
              href="/login"
              className={cn(
                buttonVariants({ variant: "outline", size: "lg" }),
                "w-full sm:w-auto font-medium px-7 2xl:px-8 h-12 2xl:h-14 text-base 2xl:text-lg rounded-xl 2xl:rounded-2xl border-border hover:bg-muted/60"
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
