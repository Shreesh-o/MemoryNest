"use client"

import * as React from "react"
import { motion, useReducedMotion } from "motion/react"
import { Bot, User, FileText, CheckCircle2, Calendar, Sparkles } from "lucide-react"

export function HeroChatMock() {
  const shouldReduceMotion = useReducedMotion()

  const fullAnswer =
    "According to Section 14.2 of your Residential Lease Agreement, the term expires on December 31, 2026. Notice of non-renewal must be provided in writing at least 60 days prior (by November 1, 2026)."

  const [displayedLength, setDisplayedLength] = React.useState(0)

  React.useEffect(() => {
    if (shouldReduceMotion) {
      return
    }

    let current = 0
    let timer: NodeJS.Timeout

    const startTyping = () => {
      timer = setInterval(() => {
        current += 2
        if (current >= fullAnswer.length) {
          setDisplayedLength(fullAnswer.length)
          clearInterval(timer)
        } else {
          setDisplayedLength(current)
        }
      }, 30)
    }

    // Small delay before typing begins
    const timeout = setTimeout(startTyping, 600)

    return () => {
      clearTimeout(timeout)
      clearInterval(timer)
    }
  }, [shouldReduceMotion, fullAnswer.length])

  const isTypingComplete = Boolean(shouldReduceMotion) || displayedLength >= fullAnswer.length
  const textToShow = shouldReduceMotion ? fullAnswer : fullAnswer.slice(0, displayedLength)

  return (
    <div className="relative w-full max-w-xl mx-auto lg:max-w-none">
      {/* Ambient gradient blobs (decorative, aria-hidden) */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -inset-4 sm:-inset-8 -z-10 overflow-hidden"
      >
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 size-72 sm:size-96 rounded-full bg-primary/10 blur-3xl dark:bg-primary/15" />
        <div className="absolute -top-12 -right-8 size-56 sm:size-72 rounded-full bg-emerald-500/10 blur-3xl dark:bg-emerald-500/15" />
        <div className="absolute -bottom-8 -left-8 size-56 sm:size-72 rounded-full bg-indigo-500/10 blur-3xl dark:bg-indigo-500/15" />
      </div>

      {/* Floating Mock Window */}
      <motion.div
        initial={shouldReduceMotion ? false : { opacity: 0, y: 20 }}
        animate={
          shouldReduceMotion
            ? { opacity: 1, y: 0 }
            : {
                opacity: 1,
                y: [0, -6, 0],
                transition: {
                  y: {
                    duration: 5,
                    repeat: Infinity,
                    repeatType: "reverse",
                    ease: "easeInOut",
                  },
                  opacity: { duration: 0.6 },
                },
              }
        }
        className="relative rounded-2xl 2xl:rounded-3xl border border-border/70 bg-card/90 p-4 sm:p-6 2xl:p-8 shadow-2xl backdrop-blur-xl ring-1 ring-border/50 text-card-foreground"
      >
        {/* Window Chrome */}
        <div className="flex items-center justify-between border-b border-border/40 pb-3 2xl:pb-4 mb-4 2xl:mb-6">
          <div className="flex items-center gap-2">
            <span className="size-3 2xl:size-3.5 rounded-full bg-red-500/80 inline-block" />
            <span className="size-3 2xl:size-3.5 rounded-full bg-amber-500/80 inline-block" />
            <span className="size-3 2xl:size-3.5 rounded-full bg-emerald-500/80 inline-block" />
            <span className="ml-2 text-xs 2xl:text-sm font-medium text-muted-foreground">
              Lease_Agreement_2024.pdf
            </span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 2xl:px-3 2xl:py-1.5 rounded-full bg-muted text-[11px] 2xl:text-xs font-medium text-muted-foreground">
            <Sparkles className="size-3 2xl:size-3.5 text-primary" aria-hidden="true" />
            <span>RAG Active · Ollama Local</span>
          </div>
        </div>

        {/* Chat Thread */}
        <div className="space-y-4 2xl:space-y-6 text-xs sm:text-sm 2xl:text-base">
          {/* User Message */}
          <div className="flex items-start gap-3 justify-end">
            <div className="rounded-2xl 2xl:rounded-3xl rounded-tr-sm bg-primary px-4 py-2.5 2xl:px-5 2xl:py-3.5 text-primary-foreground max-w-[85%] shadow-sm">
              <p className="font-normal leading-relaxed">
                When does our lease contract expire, and what are the notice terms?
              </p>
            </div>
            <div className="size-7 2xl:size-8 rounded-full bg-muted flex items-center justify-center shrink-0 text-muted-foreground mt-0.5">
              <User className="size-4 2xl:size-4.5" aria-hidden="true" />
            </div>
          </div>

          {/* Assistant Message */}
          <div className="flex items-start gap-3">
            <div className="size-7 2xl:size-8 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0 text-primary mt-0.5">
              <Bot className="size-4 2xl:size-4.5" aria-hidden="true" />
            </div>
            <div className="flex-1 space-y-3 2xl:space-y-4">
              <div className="rounded-2xl 2xl:rounded-3xl rounded-tl-sm border border-border/60 bg-muted/50 p-4 2xl:p-5 shadow-sm text-foreground">
                <p className="leading-relaxed">
                  {textToShow}
                  {!isTypingComplete && (
                    <span className="inline-block w-1.5 h-3.5 ml-1 bg-primary animate-pulse align-middle" />
                  )}
                </p>

                {/* Grounding & Citations */}
                <div className="mt-3 2xl:mt-4 pt-3 2xl:pt-4 border-t border-border/40 flex flex-wrap items-center gap-2 2xl:gap-3">
                  <div className="inline-flex items-center gap-1.5 rounded-md bg-background px-2.5 py-1 2xl:px-3 2xl:py-1.5 text-xs 2xl:text-sm font-medium text-foreground border border-border shadow-2xs hover:border-primary/50 transition-colors cursor-default">
                    <FileText className="size-3.5 2xl:size-4 text-primary" aria-hidden="true" />
                    <span>Lease_Agreement_2024.pdf · Sec 14.2 (p. 14)</span>
                    <span className="text-[10px] 2xl:text-xs text-emerald-600 dark:text-emerald-400 font-mono font-semibold ml-1">
                      98% match
                    </span>
                  </div>

                  <span className="inline-flex items-center gap-1 text-[11px] 2xl:text-xs text-muted-foreground">
                    <CheckCircle2 className="size-3 2xl:size-3.5 text-emerald-500" aria-hidden="true" />
                    Grounded strictly in vault
                  </span>
                </div>
              </div>

              {/* Extracted Event Banner */}
              <div className="rounded-xl 2xl:rounded-2xl border border-border/60 bg-background/80 px-3.5 py-2.5 2xl:px-4 2xl:py-3.5 flex items-center justify-between gap-3 shadow-2xs">
                <div className="flex items-center gap-2 min-w-0">
                  <div className="size-6 2xl:size-8 rounded-lg 2xl:rounded-xl bg-primary/10 flex items-center justify-center text-primary shrink-0">
                    <Calendar className="size-3.5 2xl:size-4" aria-hidden="true" />
                  </div>
                  <div className="min-w-0">
                    <div className="font-medium text-xs 2xl:text-sm truncate">
                      Extracted Deadline: Lease Notice Deadline
                    </div>
                    <div className="text-[11px] 2xl:text-xs text-muted-foreground truncate">
                      November 1, 2026 · Auto-detected from Sec 14.2
                    </div>
                  </div>
                </div>
                <span className="shrink-0 rounded-full bg-primary/10 px-2 py-0.5 2xl:px-3 2xl:py-1 text-[10px] 2xl:text-xs font-medium text-primary">
                  Ready to confirm
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Input Bar Mock */}
        <div className="mt-4 2xl:mt-6 pt-3 2xl:pt-4 border-t border-border/40 flex items-center justify-between gap-2 text-xs 2xl:text-sm text-muted-foreground">
          <div className="flex items-center gap-2 truncate">
            <span className="size-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="truncate">Ask a question across 42 indexed documents...</span>
          </div>
          <kbd className="px-2 py-0.5 2xl:px-2.5 2xl:py-1 rounded bg-muted border border-border text-[10px] 2xl:text-xs font-mono shrink-0">
            ↵ Enter
          </kbd>
        </div>
      </motion.div>
    </div>
  )
}
