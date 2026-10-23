import Link from "next/link"
import { ArrowRight, ShieldCheck, Cpu, HardDrive } from "lucide-react"
import { buttonVariants } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { HeroChatMock } from "./hero-chat-mock"

export function HeroSection() {
  return (
    <section
      aria-labelledby="hero-heading"
      className="relative overflow-hidden pt-12 pb-20 sm:pt-20 sm:pb-28 lg:pt-24 lg:pb-32"
    >
      {/* Background Grid Pattern (decorative) */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-20 bg-[linear-gradient(to_right,var(--color-border)_1px,transparent_1px),linear-gradient(to_bottom,var(--color-border)_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] opacity-30 dark:opacity-20"
      />

      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-12 lg:gap-8">
          {/* Left Column: Headline and CTAs */}
          <div className="flex flex-col items-center text-center lg:items-start lg:text-left lg:col-span-6 xl:col-span-5">
            {/* Pill Badge */}
            <div className="inline-flex items-center gap-2 rounded-full border border-border/80 bg-muted/60 px-3.5 py-1 text-xs font-medium text-foreground mb-6 shadow-2xs backdrop-blur-xs">
              <span className="size-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>Local RAG · Ollama Powered · Offline-First</span>
            </div>

            {/* H1 Heading */}
            <h1
              id="hero-heading"
              className="font-heading text-4xl font-extrabold tracking-tight sm:text-5xl md:text-6xl text-foreground text-balance"
            >
              Your documents,{" "}
              <span className="bg-gradient-to-r from-foreground via-foreground/90 to-muted-foreground bg-clip-text text-transparent underline decoration-primary/40 decoration-wavy decoration-2 underline-offset-8">
                finally answering back.
              </span>
            </h1>

            {/* Subtitle */}
            <p className="mt-6 text-lg sm:text-xl text-muted-foreground max-w-xl leading-relaxed text-balance">
              Local-first personal knowledge manager: upload, ask, summarize, and
              never lose a deadline.
            </p>

            {/* CTA Buttons */}
            <div className="mt-8 flex flex-col sm:flex-row items-center gap-3 w-full sm:w-auto">
              <Link
                href="/register"
                className={cn(
                  buttonVariants({ size: "lg" }),
                  "w-full sm:w-auto font-medium shadow-md hover:shadow-lg transition-all group px-6 h-12 text-base rounded-xl"
                )}
              >
                <span>Get started free</span>
                <ArrowRight
                  className="size-4 ml-1 transition-transform group-hover:translate-x-1"
                  aria-hidden="true"
                />
              </Link>

              <Link
                href="/login"
                className={cn(
                  buttonVariants({ variant: "outline", size: "lg" }),
                  "w-full sm:w-auto font-medium px-6 h-12 text-base rounded-xl border-border hover:bg-muted/60"
                )}
              >
                Log in
              </Link>
            </div>

            {/* Trust Badges */}
            <div className="mt-10 pt-6 border-t border-border/50 grid grid-cols-3 gap-3 w-full text-xs text-muted-foreground">
              <div className="flex items-center gap-1.5 justify-center lg:justify-start">
                <HardDrive className="size-3.5 text-primary shrink-0" aria-hidden="true" />
                <span>Local Storage</span>
              </div>
              <div className="flex items-center gap-1.5 justify-center lg:justify-start">
                <Cpu className="size-3.5 text-primary shrink-0" aria-hidden="true" />
                <span>Local LLM</span>
              </div>
              <div className="flex items-center gap-1.5 justify-center lg:justify-start">
                <ShieldCheck className="size-3.5 text-emerald-500 shrink-0" aria-hidden="true" />
                <span>Zero Lock-in</span>
              </div>
            </div>
          </div>

          {/* Right Column: Hero Visual Chat Mock */}
          <div className="w-full lg:col-span-6 xl:col-span-7">
            <HeroChatMock />
          </div>
        </div>
      </div>
    </section>
  )
}
