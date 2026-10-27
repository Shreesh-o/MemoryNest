"use client"

import * as React from "react"
import { motion, useReducedMotion } from "motion/react"
import { UploadCloud, Brain, MessageSquareText, CalendarCheck } from "lucide-react"

export function HowItWorks() {
  const shouldReduceMotion = useReducedMotion()

  const steps = [
    {
      step: "01",
      title: "Upload",
      desc: "Drop in PDFs, Word docs, TXT files, or scanned receipts. Instant SHA-256 deduplication ensures no duplicate processing.",
      icon: UploadCloud,
    },
    {
      step: "02",
      title: "Understand",
      desc: "PyMuPDF, docx, and Tesseract extract text, followed by sentence-aware chunking (~450 char) and local embedding generation.",
      icon: Brain,
    },
    {
      step: "03",
      title: "Ask & Explore",
      desc: "Converse with your local Ollama LLM, inspect grounded citations, run semantic queries, or explore the interactive Document Map.",
      icon: MessageSquareText,
    },
    {
      step: "04",
      title: "Stay on Top of Deadlines",
      desc: "Regex and LLM scanners automatically surface upcoming dates into your month view, with optional Google Calendar sync.",
      icon: CalendarCheck,
    },
  ]

  return (
    <section
      id="how-it-works"
      aria-labelledby="how-it-works-heading"
      className="py-20 sm:py-28 2xl:py-36 bg-background relative overflow-hidden"
    >
      <div className="mx-auto max-w-7xl 2xl:max-w-[1536px] 3xl:max-w-[1720px] px-4 sm:px-6 lg:px-8 2xl:px-12">
        {/* Header */}
        <div className="text-center max-w-3xl 2xl:max-w-4xl mx-auto mb-16 sm:mb-20 2xl:mb-24">
          <div className="inline-flex items-center gap-1.5 rounded-full border border-border/80 bg-muted/60 px-3 py-1 2xl:px-4 2xl:py-1.5 text-xs 2xl:text-sm font-semibold uppercase tracking-wider text-primary mb-4 2xl:mb-6 shadow-2xs">
            Simple, Transparent Pipeline
          </div>
          <h2
            id="how-it-works-heading"
            className="font-heading text-3xl font-extrabold tracking-tight sm:text-4xl lg:text-5xl 2xl:text-6xl text-foreground text-balance"
          >
            How MemoryNest works
          </h2>
          <p className="mt-4 2xl:mt-6 text-base sm:text-lg 2xl:text-xl text-muted-foreground leading-relaxed text-balance">
            Four streamlined stages from raw file ingestion to actionable recall. All executing on
            your machine.
          </p>
        </div>

        {/* Steps Container */}
        <div className="relative">
          {/* Desktop Connecting Line */}
          <div
            aria-hidden="true"
            className="hidden lg:block absolute top-1/2 left-12 right-12 -translate-y-12 h-0.5 bg-gradient-to-r from-border via-primary/30 to-border -z-10"
          />

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 2xl:gap-10 relative">
            {steps.map((item, index) => {
              const Icon = item.icon
              return (
                <motion.div
                  key={item.step}
                  initial={shouldReduceMotion ? false : { opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: "-40px" }}
                  transition={{ duration: 0.4, delay: shouldReduceMotion ? 0 : index * 0.1 }}
                  className="rounded-2xl 2xl:rounded-3xl border border-border/70 bg-card p-6 2xl:p-8 shadow-xs flex flex-col items-center text-center relative group hover:border-primary/40 hover:shadow-md transition-all"
                >
                  {/* Number Badge with Icon */}
                  <div className="relative mb-5 2xl:mb-6">
                    <div className="size-14 2xl:size-16 rounded-2xl bg-muted border border-border flex items-center justify-center text-foreground group-hover:bg-primary group-hover:text-primary-foreground group-hover:border-primary transition-colors shadow-2xs">
                      <Icon className="size-6 2xl:size-7" aria-hidden="true" />
                    </div>
                    <span className="absolute -top-2 -right-2 rounded-full bg-primary px-2 py-0.5 2xl:px-2.5 2xl:py-1 text-[10px] 2xl:text-xs font-mono font-bold text-primary-foreground shadow-2xs">
                      {item.step}
                    </span>
                  </div>

                  <h3 className="font-heading text-lg 2xl:text-xl font-bold text-foreground mb-2 2xl:mb-3">
                    {item.title}
                  </h3>

                  <p className="text-sm 2xl:text-base text-muted-foreground leading-relaxed text-balance">
                    {item.desc}
                  </p>
                </motion.div>
              )
            })}
          </div>
        </div>
      </div>
    </section>
  )
}
