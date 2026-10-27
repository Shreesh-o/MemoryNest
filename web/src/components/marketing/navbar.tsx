"use client"

import * as React from "react"
import Link from "next/link"
import { useTheme } from "next-themes"
import { Layers, Menu, X, Sun, Moon } from "lucide-react"
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
    <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/80 backdrop-blur-md transition-colors supports-[backdrop-filter]:bg-background/60">
      <div className="mx-auto flex h-16 2xl:h-20 max-w-7xl 2xl:max-w-[1536px] 3xl:max-w-[1720px] items-center justify-between px-4 sm:px-6 lg:px-8 2xl:px-12">
        {/* Brand / Logo */}
        <Link
          href="/"
          className="flex items-center gap-2.5 font-heading text-lg 2xl:text-xl font-bold tracking-tight text-foreground transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-md"
          aria-label="MemoryNest Home"
        >
          <div className="flex size-9 2xl:size-11 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm">
            <Layers className="size-5 2xl:size-6" aria-hidden="true" />
          </div>
          <span className="text-xl 2xl:text-2xl font-bold tracking-tight">MemoryNest</span>
        </Link>

        {/* Desktop Navigation */}
        <nav
          className="hidden md:flex items-center gap-8 2xl:gap-10 text-sm 2xl:text-base font-medium"
          aria-label="Main Navigation"
        >
          {navLinks.map((link) => (
            <a
              key={link.name}
              href={link.href}
              onClick={(e) => handleScrollTo(e, link.href)}
              className="text-muted-foreground hover:text-foreground transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-md px-1.5 py-1"
            >
              {link.name}
            </a>
          ))}
        </nav>

        {/* Desktop Actions */}
        <div className="hidden md:flex items-center gap-3 2xl:gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            aria-label={
              mounted && resolvedTheme === "dark"
                ? "Switch to light theme"
                : "Switch to dark theme"
            }
            className="text-muted-foreground hover:text-foreground rounded-lg 2xl:size-10 [&_svg]:2xl:size-5"
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
              "text-sm 2xl:text-base font-medium text-muted-foreground hover:text-foreground 2xl:h-11 2xl:px-4"
            )}
          >
            Log in
          </Link>

          <Link
            href="/register"
            className={cn(
              buttonVariants({ variant: "default", size: "sm" }),
              "text-sm 2xl:text-base font-medium shadow-sm transition-transform active:scale-[0.98] 2xl:h-11 2xl:px-5"
            )}
          >
            Get started
          </Link>
        </div>

        {/* Mobile Menu Button */}
        <div className="flex md:hidden items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            aria-label="Toggle theme"
            className="text-muted-foreground hover:text-foreground"
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
            aria-label={mobileMenuOpen ? "Close navigation menu" : "Open navigation menu"}
            aria-expanded={mobileMenuOpen}
            className="text-muted-foreground hover:text-foreground"
          >
            {mobileMenuOpen ? (
              <X className="size-5" aria-hidden="true" />
            ) : (
              <Menu className="size-5" aria-hidden="true" />
            )}
          </Button>
        </div>
      </div>

      {/* Mobile Dropdown Menu */}
      {mobileMenuOpen && (
        <div className="border-b border-border/40 bg-background/95 backdrop-blur-md px-4 pt-3 pb-6 md:hidden animate-in fade-in slide-in-from-top-2 duration-200">
          <nav className="flex flex-col space-y-3" aria-label="Mobile Navigation">
            {navLinks.map((link) => (
              <a
                key={link.name}
                href={link.href}
                onClick={(e) => handleScrollTo(e, link.href)}
                className="rounded-lg px-3 py-2 text-base font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
              >
                {link.name}
              </a>
            ))}
            <div className="pt-2 flex flex-col gap-2">
              <Link
                href="/login"
                onClick={() => setMobileMenuOpen(false)}
                className={cn(
                  buttonVariants({ variant: "outline", size: "default" }),
                  "w-full justify-center"
                )}
              >
                Log in
              </Link>
              <Link
                href="/register"
                onClick={() => setMobileMenuOpen(false)}
                className={cn(
                  buttonVariants({ variant: "default", size: "default" }),
                  "w-full justify-center"
                )}
              >
                Get started
              </Link>
            </div>
          </nav>
        </div>
      )}
    </header>
  )
}
