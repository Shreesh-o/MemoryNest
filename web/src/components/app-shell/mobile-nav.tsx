"use client"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import {
  MenuIcon,
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
  UserIcon,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { authLogout } from "@/lib/api"
import {
  Sheet,
  SheetTrigger,
  SheetContent,
} from "@/components/ui/sheet"

const mainNav = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboardIcon },
  { href: "/documents", label: "Documents", icon: FileTextIcon },
  { href: "/map", label: "Document Map", icon: NetworkIcon },
  { href: "/upload", label: "Upload", icon: UploadCloudIcon },
  { href: "/summaries", label: "Summaries", icon: SparklesIcon },
  { href: "/reminders", label: "Reminders", icon: BellIcon },
  { href: "/chat", label: "Chat", icon: MessageSquareIcon },
  { href: "/search", label: "Search", icon: SearchIcon },
  { href: "/profile", label: "Profile", icon: UserIcon },
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
            className="md:hidden sr-only inline-flex items-center justify-center rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            aria-label="Open menu"
          />
        }
      >
        <MenuIcon className="h-6 w-6 lucide-menu" />
      </SheetTrigger>
      <SheetContent side="left" className="w-72 flex flex-col p-0">
        <div className="flex items-center gap-2.5 px-5 py-4 border-b border-border">
          <div className="flex size-7.5 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <ShieldCheckIcon className="size-4" />
          </div>
          <div className="flex flex-col">
            <span className="font-heading text-base font-semibold tracking-tight">MemoryNest</span>
            <span className="text-[11px] text-muted-foreground font-medium">Local-first Vault</span>
          </div>
        </div>
        <nav className="flex flex-col gap-1 p-3 flex-1 overflow-y-auto">
          {mainNav.map((item) => {
            const isActive = pathname === item.href
            const Icon = item.icon
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                  isActive
                    ? "bg-accent text-accent-foreground font-semibold"
                    : "text-muted-foreground hover:bg-accent/60 hover:text-accent-foreground"
                )}
              >
                <Icon className="size-4 shrink-0 text-muted-foreground" />
                <span>{item.label}</span>
              </Link>
            )
          })}
        </nav>
        <div className="p-3.5 border-t border-border mt-auto">
          <Button
            variant="outline"
            size="sm"
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2"
          >
            <LogOutIcon className="size-3.5" />
            Log out
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  )
}
