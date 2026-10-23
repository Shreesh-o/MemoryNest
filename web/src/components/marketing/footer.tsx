import Link from "next/link"
import { Layers } from "lucide-react"

export function MarketingFooter() {
  const currentYear = 2026

  return (
    <footer className="border-t border-border/50 bg-background py-12 text-sm text-muted-foreground">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6 pb-8 border-b border-border/40">
          {/* Brand */}
          <div className="flex flex-col items-center md:items-start gap-2">
            <Link
              href="/"
              className="flex items-center gap-2.5 font-heading text-lg font-bold text-foreground"
            >
              <div className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <Layers className="size-4" aria-hidden="true" />
              </div>
              <span>MemoryNest</span>
            </Link>
            <p className="text-xs text-muted-foreground text-center md:text-left max-w-sm">
              Local-first personal knowledge vault: upload, ask, summarize, and never lose a deadline.
            </p>
          </div>

          {/* Quick Links */}
          <nav className="flex flex-wrap items-center justify-center gap-6 text-xs sm:text-sm font-medium">
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
        <div className="pt-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-muted-foreground">
          <p>© {currentYear} MemoryNest. All rights reserved.</p>
          <div className="flex items-center gap-4">
            <span>Released under the MIT License</span>
          </div>
        </div>
      </div>
    </footer>
  )
}
