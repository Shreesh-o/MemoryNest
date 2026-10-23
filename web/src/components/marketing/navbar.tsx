"use client"

import * as React from "react"
import Link from "next/link"
import { useTheme } from "next-themes"
import { Archive, Menu, X, Sun, Moon, ArrowRight } from "lucide-react"
import { Button, buttonVariants } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export function MarketingNavbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false)
  const { theme, setTheme, resolvedTheme } = useTheme()
  const mounted = React.useSyncExternalStore(
    () => () => {},
    () => true,
    () => false
  )

  const navLinks = [
    { name: "Features", href: "#features" },
    { name: "How it works", href: "#how-it-works" },
    { name: "Privacy", href: "#privacy" },
  ]

  const handleScrollTo = (e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
    e.preventDefault()
    setMobileMenuOpen(false)
    const target = document.querySelector(href)
    if (target) {
      target.scrollIntoView({ behavior: "smooth", block: "start" })
    }
  }

  const toggleTheme = () => {
    if (!mounted) return
    const current = resolvedTheme || theme
    setTheme(current === "dark" ? "light" : "dark")
  }

  return (
    <>
      {/* Skip Link for Keyboard Accessibility */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded-lg focus:shadow-lg focus:outline-none focus:ring-2 focus:ring-ring font-medium text-sm"
      >
        Skip to main content
      </a>

      <header className="sticky top-0 z-40 w-full border-b border-border/70 bg-background/90 backdrop-blur-md transition-colors supports-[backdrop-filter]:bg-background/75">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          {/* Brand Mark */}
          <Link
            href="/"
            className="flex items-center gap-2.5 font-heading text-lg font-bold tracking-tight text-foreground transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-lg py-1 px-1.5"
            aria-label="MemoryNest Home"
          >
            <div className="flex size-8 items-center justify-center rounded-lg bg-foreground text-background shadow-xs">
              <Archive className="size-4" aria-hidden="true" />
            </div>
            <span className="text-lg font-bold tracking-tight">MemoryNest</span>
          </Link>

          {/* Desktop Navigation */}
          <nav
            className="hidden md:flex items-center gap-7 text-xs font-mono uppercase tracking-wider text-muted-foreground"
            aria-label="Main Navigation"
          >
            {navLinks.map((link) => (
              <a
                key={link.name}
                href={link.href}
                onClick={(e) => handleScrollTo(e, link.href)}
                className="hover:text-foreground transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-md px-2 py-1"
              >
                {link.name}
              </a>
            ))}
          </nav>

          {/* Desktop Actions */}
          <div className="hidden md:flex items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleTheme}
              aria-label={
                mounted && resolvedTheme === "dark"
                  ? "Switch to light theme"
                  : "Switch to dark theme"
              }
              className="text-muted-foreground hover:text-foreground rounded-lg size-8"
            >
              {mounted && resolvedTheme === "dark" ? (
                <Sun className="size-4" aria-hidden="true" />
              ) : (
                <Moon className="size-4" aria-hidden="true" />
              )}
            </Button>

            <Link
              href="/login"
              className={cn(
                buttonVariants({ variant: "ghost", size: "sm" }),
                "text-xs font-medium text-foreground hover:text-foreground px-3.5 h-8 rounded-lg"
              )}
            >
              Log in
            </Link>

            <Link
              href="/register"
              className={cn(
                buttonVariants({ size: "sm" }),
                "text-xs font-semibold px-4 h-8 rounded-lg shadow-xs flex items-center gap-1.5"
              )}
            >
              <span>Get started</span>
              <ArrowRight className="size-3" aria-hidden="true" />
            </Link>
          </div>

          {/* Mobile Menu Toggle Button */}
          <div className="flex items-center gap-2 md:hidden">
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleTheme}
              aria-label={
                mounted && resolvedTheme === "dark"
                  ? "Switch to light theme"
                  : "Switch to dark theme"
              }
              className="text-muted-foreground hover:text-foreground rounded-lg size-8"
            >
              {mounted && resolvedTheme === "dark" ? (
                <Sun className="size-4" aria-hidden="true" />
              ) : (
                <Moon className="size-4" aria-hidden="true" />
              )}
            </Button>

            <Button
              variant="ghost"
              size="icon"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-expanded={mobileMenuOpen}
              aria-controls="mobile-navigation"
              aria-label={mobileMenuOpen ? "Close navigation menu" : "Open navigation menu"}
              className="text-muted-foreground hover:text-foreground rounded-lg size-9"
            >
              {mobileMenuOpen ? (
                <X className="size-5" aria-hidden="true" />
              ) : (
                <Menu className="size-5" aria-hidden="true" />
              )}
            </Button>
          </div>
        </div>

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <div
            id="mobile-navigation"
            className="md:hidden border-b border-border bg-background px-4 pt-3 pb-6 shadow-xl"
          >
            <nav className="flex flex-col gap-2" aria-label="Mobile Navigation">
              {navLinks.map((link) => (
                <a
                  key={link.name}
                  href={link.href}
                  onClick={(e) => handleScrollTo(e, link.href)}
                  className="rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                >
                  {link.name}
                </a>
              ))}
              <div className="mt-4 pt-4 border-t border-border flex flex-col gap-2">
                <Link
                  href="/login"
                  onClick={() => setMobileMenuOpen(false)}
                  className={cn(
                    buttonVariants({ variant: "outline" }),
                    "w-full justify-center text-sm font-medium h-10 rounded-lg"
                  )}
                >
                  Log in
                </Link>
                <Link
                  href="/register"
                  onClick={() => setMobileMenuOpen(false)}
                  className={cn(
                    buttonVariants(),
                    "w-full justify-center text-sm font-semibold h-10 rounded-lg"
                  )}
                >
                  Get started free
                </Link>
              </div>
            </nav>
          </div>
        )}
      </header>
    </>
  )
}
