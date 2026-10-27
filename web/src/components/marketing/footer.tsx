import Link from "next/link"
import { Layers } from "lucide-react"

export function MarketingFooter() {
  const currentYear = 2026

  return (
    <footer className="border-t border-border/50 bg-background py-12 2xl:py-16 text-sm 2xl:text-base text-muted-foreground">
      <div className="mx-auto max-w-7xl 2xl:max-w-[1536px] 3xl:max-w-[1720px] px-4 sm:px-6 lg:px-8 2xl:px-12">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6 pb-8 2xl:pb-10 border-b border-border/40">
          {/* Brand */}
          <div className="flex flex-col items-center md:items-start gap-2">
            <Link
              href="/"
              className="flex items-center gap-2.5 font-heading text-lg 2xl:text-xl font-bold text-foreground"
            >
              <div className="flex size-8 2xl:size-10 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <Layers className="size-4 2xl:size-5" aria-hidden="true" />
              </div>
              <span>MemoryNest</span>
            </Link>
            <p className="text-xs 2xl:text-sm text-muted-foreground text-center md:text-left max-w-sm 2xl:max-w-md">
              Local-first personal knowledge vault: upload, ask, summarize, and never lose a deadline.
            </p>
          </div>

          {/* Quick Links */}
          <nav className="flex flex-wrap items-center justify-center gap-6 2xl:gap-8 text-xs sm:text-sm 2xl:text-base font-medium">
            <a href="#features" className="hover:text-foreground transition-colors">
              Features
            </a>
            <a href="#how-it-works" className="hover:text-foreground transition-colors">
              How it works
            </a>
            <a href="#privacy" className="hover:text-foreground transition-colors">
              Privacy
            </a>
            <Link href="/login" className="hover:text-foreground transition-colors">
              Log in
            </Link>
            <Link href="/register" className="hover:text-foreground transition-colors">
              Register
            </Link>
          </nav>
        </div>

        {/* Bottom Bar */}
        <div className="pt-8 2xl:pt-10 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs 2xl:text-sm text-muted-foreground">
          <p>© {currentYear} MemoryNest. All rights reserved.</p>
          <div className="flex items-center gap-4">
            <span>Released under the MIT License</span>
          </div>
        </div>
      </div>
    </footer>
  )
}
