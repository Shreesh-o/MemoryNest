"use client"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import {
  LogOutIcon,
  LayoutDashboardIcon,
  FileTextIcon,
  NetworkIcon,
  UploadCloudIcon,
  SparklesIcon,
  BellIcon,
  MessageSquareIcon,
  SearchIcon,
  ShieldCheckIcon,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { authLogout } from "@/lib/api"

interface NavItem {
  href: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  disabled?: boolean
}

const mainNav: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboardIcon },
  { href: "/documents", label: "Documents", icon: FileTextIcon },
  { href: "/map", label: "Document Map", icon: NetworkIcon },
  { href: "/upload", label: "Upload", icon: UploadCloudIcon },
  { href: "/summaries", label: "Summaries", icon: SparklesIcon },
  { href: "/reminders", label: "Reminders", icon: BellIcon },
  { href: "/chat", label: "Chat", icon: MessageSquareIcon },
  { href: "/search", label: "Search", icon: SearchIcon },
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
    <aside className="hidden md:flex fixed inset-y-0 left-0 z-40 w-64 border-r border-sidebar-border bg-sidebar text-sidebar-foreground flex-col">
      <div className="flex flex-col h-full">
        {/* Brand header */}
        <div className="flex items-center gap-2.5 px-5 py-4.5 border-b border-sidebar-border">
          <div className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-xs">
            <ShieldCheckIcon className="size-4.5" />
          </div>
          <div className="flex flex-col">
            <span className="font-heading text-base font-semibold tracking-tight text-sidebar-foreground">
              MemoryNest
            </span>
            <span className="text-[11px] text-muted-foreground font-medium flex items-center gap-1.5">
              <span className="inline-block size-1.5 rounded-full bg-emerald-500" />
              Local-first Vault
            </span>
          </div>
        </div>

        {/* Navigation items */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
          {mainNav.map((item) => {
            const isActive = pathname === item.href
            const Icon = item.icon
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all group",
                  isActive
                    ? "bg-sidebar-accent text-sidebar-accent-foreground font-semibold shadow-xs ring-1 ring-border/50"
                    : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
                  item.disabled && "opacity-50 pointer-events-none"
                )}
              >
                <Icon
                  className={cn(
                    "size-4 shrink-0 transition-colors",
                    isActive
                      ? "text-primary"
                      : "text-muted-foreground group-hover:text-sidebar-accent-foreground"
                  )}
                />
                <span className="truncate">{item.label}</span>
              </Link>
            )
          })}
        </nav>

        {/* Footer info & logout */}
        <div className="p-3.5 border-t border-sidebar-border space-y-2.5">
          <div className="flex items-center justify-between px-2 text-[11px] text-muted-foreground">
            <span>Offline-Ready</span>
            <span className="font-mono">v0.1.0</span>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 text-xs"
          >
            <LogOutIcon className="size-3.5" />
            Log out
          </Button>
        </div>
      </div>
    </aside>
  )
}
