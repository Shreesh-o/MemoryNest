"use client"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { XIcon, LogOutIcon } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { authLogout } from "@/lib/api"
import {
  Sheet,
  SheetTrigger,
  SheetContent,
} from "@/components/ui/sheet"

const mainNav = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/documents", label: "Documents" },
  { href: "/upload", label: "Upload" },
  { href: "/summaries", label: "Summaries" },
  { href: "/reminders", label: "Reminders" },
  { href: "/chat", label: "Chat" },
  { href: "/search", label: "Search" },
] as const

export function MobileNav() {
  const pathname = usePathname()
  const router = useRouter()
  const queryClient = useQueryClient()

  const handleLogout = async () => {
    try {
      const result = await authLogout()
      if (result.ok) {
        queryClient.clear()
        router.replace("/login")
      } else {
        toast.error(result.error?.detail || "Failed to log out")
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to log out"
      toast.error(msg)
    }
  }

  return (
    <Sheet>
      <SheetTrigger
        render={
          <button
            className="md:hidden inline-flex items-center justify-center rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            aria-label="Open menu"
          />
        }
      >
        <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </SheetTrigger>
      <SheetContent side="left" className="w-72 flex flex-col">
        <div className="flex items-center justify-between p-4 border-b">
          <span className="font-heading text-xl font-bold">MemoryNest</span>
          <SheetTrigger
            render={
              <button
                className="inline-flex items-center justify-center rounded-md p-1 text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                aria-label="Close menu"
              />
            }
          >
            <XIcon className="h-5 w-5" />
            <span className="sr-only">Close</span>
          </SheetTrigger>
        </div>
        <nav className="flex flex-col gap-1 p-4 flex-1 overflow-y-auto">
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
        <div className="p-4 border-t mt-auto">
          <Button
            variant="outline"
            size="sm"
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2"
          >
            <LogOutIcon className="h-4 w-4" />
            Log out
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  )
}
