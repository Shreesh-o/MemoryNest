"use client"

import * as React from "react"
import { motion, useReducedMotion } from "motion/react"
import {
  MessageSquare,
  Upload,
  Search,
  Volume2,
  CalendarClock,
  Calendar,
  Network,
  FileText,
  History,
  ShieldCheck,
  CheckCircle2,
  Play,
  AlertCircle,
} from "lucide-react"

export function BentoGrid() {
  const shouldReduceMotion = useReducedMotion()

  return (
    <section
      id="features"
      aria-labelledby="features-heading"
      className="py-20 sm:py-28 bg-muted/20 border-y border-border/40"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16 sm:mb-20">
          <div className="inline-flex items-center gap-1.5 rounded-full border border-border/80 bg-background px-3 py-1 text-xs font-semibold uppercase tracking-wider text-primary mb-4 shadow-2xs">
            Comprehensive Capabilities
          </div>
          <h2
            id="features-heading"
            className="font-heading text-3xl font-extrabold tracking-tight sm:text-4xl lg:text-5xl text-foreground text-balance"
          >
            Everything you need to turn documents into actionable memory.
          </h2>
          <p className="mt-4 text-base sm:text-lg text-muted-foreground leading-relaxed text-balance">
            Every feature runs locally on your machine with zero cloud lock-in.
            From OCR ingestion to RAG chat, audio playback, and calendar scheduling.
          </p>
        </div>

        {/* Bento Grid */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
          {/* Card 1: Ask Your Documents (RAG Chat) - 8 cols on desktop */}
          <motion.div
            initial={shouldReduceMotion ? false : { opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-40px" }}
            transition={{ duration: 0.4, delay: 0 }}
            whileHover={shouldReduceMotion ? undefined : { y: -3 }}
            className="md:col-span-12 lg:col-span-8 rounded-2xl border border-border/70 bg-card p-6 sm:p-7 shadow-xs hover:border-primary/40 hover:shadow-lg transition-all flex flex-col justify-between overflow-hidden relative group"
          >
            <div>
              <div className="flex items-center gap-3 mb-3">
                <div className="size-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary shrink-0">
                  <MessageSquare className="size-5" aria-hidden="true" />
                </div>
                <div>
                  <h3 className="font-heading text-lg font-bold text-foreground">
                    Ask Your Documents (RAG Chat)
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    Grounded citations • Hallucination refusal gate
                  </p>
                </div>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Pose natural-language questions and receive answers cited down to the exact
                chunk. If the answer isn&apos;t in your files, MemoryNest says &ldquo;I couldn&apos;t find
                that&rdquo; instead of guessing.
              </p>
            </div>

            {/* Mini Preview */}
            <div className="mt-6 rounded-xl border border-border/60 bg-muted/40 p-4 space-y-3 font-sans text-xs">
              <div className="flex items-center justify-between text-muted-foreground border-b border-border/30 pb-2">
                <span className="font-medium">Ollama RAG Session</span>
                <span className="inline-flex items-center gap-1 text-[11px] text-emerald-600 dark:text-emerald-400">
                  <CheckCircle2 className="size-3" aria-hidden="true" />
                  Similarity Gate: &gt;0.30
                </span>
              </div>
              <div className="rounded-lg bg-background p-3 border border-border/60 shadow-2xs">
                <div className="font-medium text-foreground mb-1">
                  &ldquo;What is the late return policy for rental equipment?&rdquo;
                </div>
                <div className="text-muted-foreground leading-relaxed">
                  &ldquo;Late returns incur a $25 daily fee up to 5 days, after which the replacement
                  charge applies.&rdquo;
                </div>
                <div className="mt-2.5 flex flex-wrap items-center gap-2 pt-2 border-t border-border/40">
                  <span className="rounded bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary">
                    [Equipment_Agreement.pdf · Sec 8.1]
                  </span>
                  <span className="text-[11px] text-muted-foreground">
                    Cosine Score: 0.88
                  </span>
                </div>
              </div>
              <div className="rounded-lg bg-background/60 p-2.5 border border-dashed border-border/80 flex items-center gap-2 text-muted-foreground">
                <AlertCircle className="size-3.5 text-amber-500 shrink-0" aria-hidden="true" />
                <span>
                  Query outside vault? &rarr; &ldquo;I couldn&apos;t find any relevant information in your
                  documents.&rdquo;
                </span>
              </div>
            </div>
          </motion.div>

          {/* Card 2: Upload & OCR - 4 cols on desktop */}
          <motion.div
            initial={shouldReduceMotion ? false : { opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-40px" }}
            transition={{ duration: 0.4, delay: 0.05 }}
            whileHover={shouldReduceMotion ? undefined : { y: -3 }}
            className="md:col-span-6 lg:col-span-4 rounded-2xl border border-border/70 bg-card p-6 sm:p-7 shadow-xs hover:border-primary/40 hover:shadow-lg transition-all flex flex-col justify-between overflow-hidden relative group"
          >
            <div>
              <div className="flex items-center gap-3 mb-3">
                <div className="size-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary shrink-0">
                  <Upload className="size-5" aria-hidden="true" />
                </div>
                <div>
                  <h3 className="font-heading text-lg font-bold text-foreground">
                    Multi-Format Upload & OCR
                  </h3>
                  <p className="text-xs text-muted-foreground">PDF, DOCX, TXT, and scanned images</p>
                </div>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Drag-and-drop any document format. Images and scanned receipts are processed via
                built-in Tesseract OCR without sending data over the network.
              </p>
            </div>

            {/* Mini Preview */}
            <div className="mt-6 rounded-xl border border-border/60 bg-muted/40 p-4 space-y-3 font-sans text-xs">
              <div className="grid grid-cols-4 gap-1.5 text-center font-mono text-[10px] font-semibold">
                <span className="rounded bg-background border border-border p-1.5 text-foreground">.PDF</span>
                <span className="rounded bg-background border border-border p-1.5 text-foreground">.DOCX</span>
                <span className="rounded bg-background border border-border p-1.5 text-foreground">.TXT</span>
                <span className="rounded bg-primary/10 border border-primary/30 p-1.5 text-primary">OCR</span>
              </div>
              <div className="rounded-lg bg-background p-3 border border-border/60">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="font-medium text-foreground truncate">Invoice_Scan_04.jpg</span>
                  <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-medium">Tesseract OCR</span>
                </div>
                <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
                  <div className="bg-primary h-full w-full rounded-full" />
                </div>
                <div className="mt-2 text-[11px] text-muted-foreground flex justify-between">
                  <span>Sentence chunking (~450 char)</span>
                  <span>Ready</span>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Card 3: Semantic Search - 4 cols */}
          <motion.div
            initial={shouldReduceMotion ? false : { opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-40px" }}
            transition={{ duration: 0.4, delay: 0.1 }}
            whileHover={shouldReduceMotion ? undefined : { y: -3 }}
            className="md:col-span-6 lg:col-span-4 rounded-2xl border border-border/70 bg-card p-6 sm:p-7 shadow-xs hover:border-primary/40 hover:shadow-lg transition-all flex flex-col justify-between overflow-hidden relative group"
          >
            <div>
              <div className="flex items-center gap-3 mb-3">
                <div className="size-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary shrink-0">
                  <Search className="size-5" aria-hidden="true" />
                </div>
                <div>
                  <h3 className="font-heading text-lg font-bold text-foreground">
                    Semantic Search
                  </h3>
                  <p className="text-xs text-muted-foreground">Find by meaning, not just exact keywords</p>
                </div>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Powered by sentence-transformers embeddings in ChromaDB. Match conceptual queries
                even when phrasing differs completely from the original text.
              </p>
            </div>

            {/* Mini Preview */}
            <div className="mt-6 rounded-xl border border-border/60 bg-muted/40 p-4 space-y-2.5 text-xs">
              <div className="flex items-center gap-2 rounded-lg bg-background px-2.5 py-1.5 border border-border">
                <Search className="size-3.5 text-muted-foreground" aria-hidden="true" />
                <span className="font-mono text-[11px] text-foreground">&ldquo;laptop warranty battery&rdquo;</span>
              </div>
              <div className="rounded-lg bg-background p-2.5 border border-border/60 space-y-1">
                <div className="flex items-center justify-between text-[11px]">
                  <span className="font-medium text-foreground truncate">Hardware_Care_Plan.pdf</span>
                  <span className="text-primary font-mono text-[10px] font-semibold">94% match</span>
                </div>
                <p className="text-muted-foreground text-[11px] leading-snug">
                  &ldquo;...coverage extends to all <mark className="bg-primary/20 text-foreground px-1 rounded">internal rechargeable cells</mark> failing under normal use...&rdquo;
                </p>
              </div>
            </div>
          </motion.div>

          {/* Card 4: Summaries & Audio - 4 cols */}
          <motion.div
            initial={shouldReduceMotion ? false : { opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-40px" }}
            transition={{ duration: 0.4, delay: 0.15 }}
            whileHover={shouldReduceMotion ? undefined : { y: -3 }}
            className="md:col-span-6 lg:col-span-4 rounded-2xl border border-border/70 bg-card p-6 sm:p-7 shadow-xs hover:border-primary/40 hover:shadow-lg transition-all flex flex-col justify-between overflow-hidden relative group"
          >
            <div>
              <div className="flex items-center gap-3 mb-3">
                <div className="size-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary shrink-0">
                  <Volume2 className="size-5" aria-hidden="true" />
                </div>
                <div>
                  <h3 className="font-heading text-lg font-bold text-foreground">
                    Summaries & Audio TTS
                  </h3>
                  <p className="text-xs text-muted-foreground">Map-reduce summaries with voice readout</p>
                </div>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Map-reduce summarization digests massive multi-page documents. Listen on demand
                with edge-tts, piper, or espeak audio synthesis.
              </p>
            </div>

            {/* Mini Preview */}
            <div className="mt-6 rounded-xl border border-border/60 bg-muted/40 p-4 space-y-3 text-xs">
              <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                <span className="font-medium">Map-Reduce Digest (50pg &rarr; 1pg)</span>
                <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-mono border border-border">
                  piper / edge-tts
                </span>
              </div>
              <div className="rounded-lg bg-background p-2.5 border border-border flex items-center gap-3">
                <div className="size-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground shrink-0 shadow-2xs">
                  <Play className="size-3.5 fill-current ml-0.5" aria-hidden="true" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1 h-3 mb-1">
                    {[40, 70, 30, 90, 60, 100, 45, 80, 50, 65, 85, 30, 75, 45].map((h, i) => (
                      <span
                        key={i}
                        className="w-1 bg-primary/70 rounded-full"
                        style={{ height: `${h}%` }}
                      />
                    ))}
                  </div>
                  <div className="flex justify-between text-[10px] text-muted-foreground">
                    <span>Summary.wav</span>
                    <span>01:42 / 03:10</span>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Card 5: Deadlines & Reminders - 4 cols */}
          <motion.div
            initial={shouldReduceMotion ? false : { opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-40px" }}
            transition={{ duration: 0.4, delay: 0.2 }}
            whileHover={shouldReduceMotion ? undefined : { y: -3 }}
            className="md:col-span-6 lg:col-span-4 rounded-2xl border border-border/70 bg-card p-6 sm:p-7 shadow-xs hover:border-primary/40 hover:shadow-lg transition-all flex flex-col justify-between overflow-hidden relative group"
          >
            <div>
              <div className="flex items-center gap-3 mb-3">
                <div className="size-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary shrink-0">
                  <CalendarClock className="size-5" aria-hidden="true" />
                </div>
                <div>
                  <h3 className="font-heading text-lg font-bold text-foreground">
                    Deadlines & Reminders
                  </h3>
                  <p className="text-xs text-muted-foreground">Auto-extracted dates & email alerts</p>
                </div>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Regex, dateparser, and LLM fallbacks scan every document for dates and commitments.
                Confirm reminders and get timely email notifications.
              </p>
            </div>

            {/* Mini Preview */}
            <div className="mt-6 rounded-xl border border-border/60 bg-muted/40 p-4 space-y-2 text-xs">
              <div className="rounded-lg bg-background p-2.5 border border-border space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-foreground truncate">Quarterly Tax Filing</span>
                  <span className="rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 px-2 py-0.5 text-[10px] font-medium">
                    Confirmed
                  </span>
                </div>
                <div className="text-[11px] text-muted-foreground">Due: November 15, 2026</div>
                <div className="flex items-center gap-1 text-[10px] text-muted-foreground pt-1 border-t border-border/40">
                  <CheckCircle2 className="size-3 text-emerald-500" aria-hidden="true" />
                  <span>Confirmation email sent via Gmail SMTP</span>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Card 6: Calendar & Google Sync - 6 cols */}
          <motion.div
            initial={shouldReduceMotion ? false : { opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-40px" }}
            transition={{ duration: 0.4, delay: 0.25 }}
            whileHover={shouldReduceMotion ? undefined : { y: -3 }}
            className="md:col-span-12 lg:col-span-6 rounded-2xl border border-border/70 bg-card p-6 sm:p-7 shadow-xs hover:border-primary/40 hover:shadow-lg transition-all flex flex-col justify-between overflow-hidden relative group"
          >
            <div>
              <div className="flex items-center gap-3 mb-3">
                <div className="size-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary shrink-0">
                  <Calendar className="size-5" aria-hidden="true" />
                </div>
                <div>
                  <h3 className="font-heading text-lg font-bold text-foreground">
                    Calendar View & Google Calendar Sync
                  </h3>
                  <p className="text-xs text-muted-foreground">Interactive month view + optional OAuth 2.0 sync</p>
                </div>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Visualize deadlines in an in-app interactive month calendar. Connect your personal
                Google Calendar via OAuth 2.0 for automatic event creation, or export offline .ics files.
              </p>
            </div>

            {/* Mini Preview */}
            <div className="mt-6 rounded-xl border border-border/60 bg-muted/40 p-4 space-y-3 text-xs">
              <div className="flex items-center justify-between border-b border-border/40 pb-2">
                <span className="font-medium text-foreground">Month View: November 2026</span>
                <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
                  Google Calendar: Connected
                </span>
              </div>
              {/* Mini Calendar Grid */}
              <div className="grid grid-cols-7 gap-1 text-center font-mono text-[10px]">
                {["S", "M", "T", "W", "T", "F", "S"].map((d, i) => (
                  <span key={i} className="text-muted-foreground font-semibold">{d}</span>
                ))}
                {[...Array(14)].map((_, i) => (
                  <div
                    key={i}
                    className={`h-6 flex flex-col items-center justify-center rounded ${
                      i === 7
                        ? "bg-primary text-primary-foreground font-bold shadow-2xs"
                        : i === 11
                        ? "bg-muted border border-primary/40 text-foreground font-medium"
                        : "text-muted-foreground"
                    }`}
                  >
                    <span>{i + 1}</span>
                  </div>
                ))}
              </div>
              <div className="flex items-center justify-between text-[11px] text-muted-foreground pt-1">
                <span>Nov 8: Annual Policy Review</span>
                <span className="text-emerald-600 dark:text-emerald-400 font-medium">Synced</span>
              </div>
            </div>
          </motion.div>

          {/* Card 7: Document Map - 6 cols */}
          <motion.div
            initial={shouldReduceMotion ? false : { opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-40px" }}
            transition={{ duration: 0.4, delay: 0.3 }}
            whileHover={shouldReduceMotion ? undefined : { y: -3 }}
            className="md:col-span-12 lg:col-span-6 rounded-2xl border border-border/70 bg-card p-6 sm:p-7 shadow-xs hover:border-primary/40 hover:shadow-lg transition-all flex flex-col justify-between overflow-hidden relative group"
          >
            <div>
              <div className="flex items-center gap-3 mb-3">
                <div className="size-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary shrink-0">
                  <Network className="size-5" aria-hidden="true" />
                </div>
                <div>
                  <h3 className="font-heading text-lg font-bold text-foreground">
                    Topic-Similarity Document Map
                  </h3>
                  <p className="text-xs text-muted-foreground">Thematic graph with TF-IDF shared keywords</p>
                </div>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Explore latent relationships between files. Cosine similarity of chunk embeddings
                identifies clusters, while TF-IDF labels links with meaningful shared terminology.
              </p>
            </div>

            {/* Mini Preview */}
            <div className="mt-6 rounded-xl border border-border/60 bg-muted/40 p-4 space-y-2.5 text-xs">
              <div className="flex items-center justify-between text-[11px] text-muted-foreground border-b border-border/40 pb-2">
                <span>Similarity threshold: 0.45</span>
                <span className="text-primary font-medium">Rebuilds automatically</span>
              </div>
              <div className="h-24 rounded-lg bg-background border border-border relative flex items-center justify-around px-4">
                {/* Node 1 */}
                <div className="size-10 rounded-full bg-primary/10 border border-primary/30 flex items-center justify-center text-[10px] font-semibold text-primary">
                  Lease
                </div>
                {/* Connecting Line with shared keyword */}
                <div className="flex-1 flex flex-col items-center mx-2">
                  <span className="rounded bg-muted px-1.5 py-0.5 text-[9px] font-mono text-muted-foreground border border-border truncate max-w-[120px]">
                    deposit, terms (0.76)
                  </span>
                  <div className="w-full h-0.5 bg-primary/30 my-1" />
                </div>
                {/* Node 2 */}
                <div className="size-10 rounded-full bg-primary/10 border border-primary/30 flex items-center justify-center text-[10px] font-semibold text-primary">
                  Tenant
                </div>
                {/* Node 3 */}
                <div className="flex-1 flex flex-col items-center mx-2">
                  <span className="rounded bg-muted px-1.5 py-0.5 text-[9px] font-mono text-muted-foreground border border-border truncate max-w-[120px]">
                    notice (0.64)
                  </span>
                  <div className="w-full h-0.5 bg-primary/30 my-1" />
                </div>
                <div className="size-10 rounded-full bg-muted border border-border flex items-center justify-center text-[10px] font-semibold text-muted-foreground">
                  Receipt
                </div>
              </div>
            </div>
          </motion.div>

          {/* Card 8: Clean Document Viewer - 4 cols */}
          <motion.div
            initial={shouldReduceMotion ? false : { opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-40px" }}
            transition={{ duration: 0.4, delay: 0.35 }}
            whileHover={shouldReduceMotion ? undefined : { y: -3 }}
            className="md:col-span-6 lg:col-span-4 rounded-2xl border border-border/70 bg-card p-6 sm:p-7 shadow-xs hover:border-primary/40 hover:shadow-lg transition-all flex flex-col justify-between overflow-hidden relative group"
          >
            <div>
              <div className="flex items-center gap-3 mb-3">
                <div className="size-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary shrink-0">
                  <FileText className="size-5" aria-hidden="true" />
                </div>
                <div>
                  <h3 className="font-heading text-lg font-bold text-foreground">
                    Dual-Pane Document Viewer
                  </h3>
                  <p className="text-xs text-muted-foreground">Original rendering & extracted text</p>
                </div>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Inspect original PDF/DOCX layouts or switch to cleaned extracted text with in-viewer
                search, syntax highlighting, and instant copying.
              </p>
            </div>

            {/* Mini Preview */}
            <div className="mt-6 rounded-xl border border-border/60 bg-muted/40 p-4 space-y-2 text-xs">
              <div className="flex rounded-md bg-muted p-1 border border-border text-[11px]">
                <span className="flex-1 text-center py-1 rounded text-muted-foreground font-medium">Original File</span>
                <span className="flex-1 text-center py-1 rounded bg-background shadow-2xs font-semibold text-foreground">Extracted Text</span>
              </div>
              <div className="rounded-lg bg-background p-2.5 border border-border/60 font-mono text-[11px] text-muted-foreground space-y-1">
                <div className="flex items-center justify-between text-[10px] text-primary pb-1 border-b border-border/30">
                  <span>Search: &ldquo;termination&rdquo;</span>
                  <span>3 matches</span>
                </div>
                <div className="truncate">L14: Early termination conditions...</div>
                <div className="truncate text-foreground font-medium bg-primary/10 px-1 rounded">L15: Notice of 60 days required</div>
              </div>
            </div>
          </motion.div>

          {/* Card 9: Conversation History - 4 cols */}
          <motion.div
            initial={shouldReduceMotion ? false : { opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-40px" }}
            transition={{ duration: 0.4, delay: 0.4 }}
            whileHover={shouldReduceMotion ? undefined : { y: -3 }}
            className="md:col-span-6 lg:col-span-4 rounded-2xl border border-border/70 bg-card p-6 sm:p-7 shadow-xs hover:border-primary/40 hover:shadow-lg transition-all flex flex-col justify-between overflow-hidden relative group"
          >
            <div>
              <div className="flex items-center gap-3 mb-3">
                <div className="size-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary shrink-0">
                  <History className="size-5" aria-hidden="true" />
                </div>
                <div>
                  <h3 className="font-heading text-lg font-bold text-foreground">
                    Conversation History
                  </h3>
                  <p className="text-xs text-muted-foreground">Per-user searchable chat threads</p>
                </div>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Every conversation is saved, indexed, and isolated per user. Resume complex inquiries
                anytime or search historical answers effortlessly.
              </p>
            </div>

            {/* Mini Preview */}
            <div className="mt-6 rounded-xl border border-border/60 bg-muted/40 p-4 space-y-2 text-xs">
              <div className="rounded-lg bg-background p-2 border border-border flex items-center justify-between text-muted-foreground text-[11px]">
                <span>Filter threads...</span>
                <kbd className="text-[10px] px-1 bg-muted rounded">⌘K</kbd>
              </div>
              <div className="space-y-1.5">
                <div className="rounded bg-background p-2 border border-primary/30 text-foreground font-medium flex justify-between items-center text-[11px]">
                  <span className="truncate">Lease terms & deposit inquiry</span>
                  <span className="text-[10px] text-primary">Active</span>
                </div>
                <div className="rounded bg-background/60 p-2 border border-border/40 text-muted-foreground flex justify-between items-center text-[11px]">
                  <span className="truncate">Medical policy deductible</span>
                  <span className="text-[10px]">Yesterday</span>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Card 10: Private by Design - 4 cols */}
          <motion.div
            initial={shouldReduceMotion ? false : { opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-40px" }}
            transition={{ duration: 0.4, delay: 0.45 }}
            whileHover={shouldReduceMotion ? undefined : { y: -3 }}
            className="md:col-span-12 lg:col-span-4 rounded-2xl border border-border/70 bg-card p-6 sm:p-7 shadow-xs hover:border-primary/40 hover:shadow-lg transition-all flex flex-col justify-between overflow-hidden relative group"
          >
            <div>
              <div className="flex items-center gap-3 mb-3">
                <div className="size-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary shrink-0">
                  <ShieldCheck className="size-5 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
                </div>
                <div>
                  <h3 className="font-heading text-lg font-bold text-foreground">
                    Private by Design
                  </h3>
                  <p className="text-xs text-muted-foreground">Rigorous data isolation & HTTP-only sessions</p>
                </div>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Bcrypt passwords, HTTP-only JWT cookies, and strict per-user database scoping on
                every query. Your vault is completely isolated.
              </p>
            </div>

            {/* Mini Preview */}
            <div className="mt-6 rounded-xl border border-border/60 bg-muted/40 p-4 space-y-2 text-xs">
              <div className="space-y-1.5 font-mono text-[11px]">
                <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400">
                  <CheckCircle2 className="size-3.5 shrink-0" aria-hidden="true" />
                  <span>WHERE user_id = :current_user</span>
                </div>
                <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400">
                  <CheckCircle2 className="size-3.5 shrink-0" aria-hidden="true" />
                  <span>Passwords hashed with bcrypt</span>
                </div>
                <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400">
                  <CheckCircle2 className="size-3.5 shrink-0" aria-hidden="true" />
                  <span>Session cookie: HttpOnly; SameSite=Lax</span>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
