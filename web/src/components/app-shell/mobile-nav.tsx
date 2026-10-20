"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"

import {
  Sheet,
  SheetTrigger,
  SheetContent,
} from "@/components/ui/sheet"
import { XIcon } from "lucide-react"

const mainNav = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/documents", label: "Documents" },
  { href: "/upload", label: "Upload" },
  { href: "/summaries", label: "Summaries" },
  { href: "/reminders", label: "Reminders" },
  { href: "/chat", label: "Chat" },
] as const

export function MobileNav() {
  const pathname = usePathname()

  return (
    <Sheet>
      <SheetTrigger>
        <button className="md:hidden inline-flex items-center justify-center rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-accent-foreground" aria-label="Open menu">
          <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
      </SheetTrigger>
      <SheetContent side="left" className="w-72">
        <div className="flex items-center justify-between p-4 border-b">
          <span className="font-heading text-xl font-bold">MemoryNest</span>
          <SheetTrigger>
            <button className="inline-flex items-center justify-center rounded-md p-1 text-muted-foreground hover:bg-accent hover:text-accent-foreground" aria-label="Close menu">
              <XIcon className="h-5 w-5" />
              <span className="sr-only">Close</span>
            </button>
          </SheetTrigger>
        </div>
        <nav className="flex flex-col gap-1 p-4">
          {mainNav.map((item) => {
            const isActive = pathname === item.href
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-base font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )}
              >
                {item.label}
              </Link>
            )
          })}
        </nav>
      </SheetContent>
    </Sheet>
  )
}