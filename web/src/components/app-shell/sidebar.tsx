"use client"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { LogOutIcon } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { authLogout } from "@/lib/api"

interface NavItem {
  href: string
  label: string
  disabled?: boolean
}

const mainNav: NavItem[] = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/documents", label: "Documents" },
  { href: "/upload", label: "Upload" },
  { href: "/summaries", label: "Summaries" },
  { href: "/reminders", label: "Reminders" },
  { href: "/chat", label: "Chat" },
  { href: "/search", label: "Search" },
]

export function Sidebar() {
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
    <aside className="hidden md:block fixed inset-y-0 left-0 z-40 w-64 border-r bg-card flex flex-col">
      <div className="flex flex-col h-full">
        <div className="flex items-center gap-2 px-4 py-4 border-b">
          <span className="font-heading text-xl font-bold">MemoryNest</span>
        </div>

        <nav className="flex-1 overflow-y-auto p-4 space-y-1">
          {mainNav.map((item) => {
            const isActive = pathname === item.href
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                  item.disabled && "opacity-50 pointer-events-none"
                )}
              >
                {item.label}
              </Link>
            )
          })}
        </nav>

        <div className="p-4 border-t">
          <p className="text-xs text-muted-foreground text-center">
            v0.1.0
          </p>
          <div className="mt-4">
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
        </div>
      </div>
    </aside>
  )
}
