"use client"

import Link from "next/link"
import { useTheme } from "next-themes"
import { useRouter } from "next/navigation"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { authLogout, authMe, type UserPublic } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import {
  MenuIcon,
  SunIcon,
  MoonIcon,
  MonitorIcon,
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
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from "@/components/ui/dropdown-menu"
import {
  Avatar,
  AvatarFallback,
} from "@/components/ui/avatar"
import {
  Sheet,
  SheetTrigger,
  SheetContent,
} from "@/components/ui/sheet"

interface TopBarProps {
  pageTitle: string
}

export function TopBar({ pageTitle }: TopBarProps) {
  const { setTheme, theme } = useTheme()
  const router = useRouter()
  const queryClient = useQueryClient()

  const { data: user } = useQuery<UserPublic>({
    queryKey: ["me"],
    queryFn: authMe,
  })

  const username = user?.username || "User"
  const userInitial = (user?.username?.[0] || "U").toUpperCase()

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

  const mobileNav = [
    { href: "/dashboard", label: "Dashboard", icon: LayoutDashboardIcon },
    { href: "/documents", label: "Documents", icon: FileTextIcon },
    { href: "/map", label: "Document Map", icon: NetworkIcon },
    { href: "/upload", label: "Upload", icon: UploadCloudIcon },
    { href: "/summaries", label: "Summaries", icon: SparklesIcon },
    { href: "/reminders", label: "Reminders", icon: BellIcon },
    { href: "/chat", label: "Chat", icon: MessageSquareIcon },
    { href: "/search", label: "Search", icon: SearchIcon },
    { href: "/profile", label: "Profile", icon: UserIcon },
  ]

  return (
    <header className="sticky top-0 z-30 w-full border-b border-border bg-background/85 backdrop-blur-md transition-colors">
      <div className="flex h-15 items-center justify-between gap-4 px-4 sm:px-6">
        <div className="flex items-center gap-3 min-w-0">
          {/* Mobile menu sheet */}
          <Sheet>
            <SheetTrigger
              render={
                <button
                  className="md:hidden inline-flex items-center justify-center rounded-lg p-2 text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors cursor-pointer"
                  aria-label="Open menu"
                />
              }
            >
              <MenuIcon className="size-5 lucide-menu" />
            </SheetTrigger>
            <SheetContent side="left" className="w-72 flex flex-col p-0">
              <div className="flex items-center gap-2.5 px-5 py-4 border-b border-border">
                <div className="flex size-7.5 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                  <ShieldCheckIcon className="size-4" />
                </div>
                <div className="flex flex-col">
                  <span className="font-heading text-base font-semibold tracking-tight">
                    MemoryNest
                  </span>
                  <span className="text-[11px] text-muted-foreground font-medium">
                    Local-first Knowledge Vault
                  </span>
                </div>
              </div>
              <nav className="flex flex-col gap-1 p-3 flex-1 overflow-y-auto">
                {mobileNav.map((item) => {
                  const Icon = item.icon
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
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

          {/* Page title */}
          <div className="truncate">
            <h1 className="font-heading text-base sm:text-lg font-semibold tracking-tight text-foreground truncate">
              {pageTitle}
            </h1>
          </div>
        </div>

        {/* Right side controls: Theme toggles + User avatar */}
        <div className="flex items-center gap-2">
          {/* Segmented Theme Toggle */}
          <div className="flex items-center rounded-lg border border-border/70 bg-muted/40 p-0.5">
            <Button
              variant={theme === "light" ? "secondary" : "ghost"}
              size="icon-xs"
              onClick={() => setTheme("light")}
              aria-label="Light mode"
              className="rounded-md"
            >
              <SunIcon className="size-3.5" />
            </Button>
            <Button
              variant={theme === "dark" ? "secondary" : "ghost"}
              size="icon-xs"
              onClick={() => setTheme("dark")}
              aria-label="Dark mode"
              className="rounded-md"
            >
              <MoonIcon className="size-3.5" />
            </Button>
            <Button
              variant={theme === "system" ? "secondary" : "ghost"}
              size="icon-xs"
              onClick={() => setTheme("system")}
              aria-label="System theme"
              className="rounded-md"
            >
              <MonitorIcon className="size-3.5" />
            </Button>
          </div>

          <Separator orientation="vertical" className="h-5 mx-0.5" />

          {/* User dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger
              render={
                <Button
                  variant="ghost"
                  className="relative size-8.5 rounded-full p-0 ring-1 ring-border/60 hover:ring-border transition-all"
                />
              }
            >
              <Avatar className="size-8">
                <AvatarFallback className="font-semibold text-xs bg-primary/10 text-primary">
                  {userInitial}
                </AvatarFallback>
              </Avatar>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel className="font-medium text-xs text-muted-foreground">
                Signed in as <span className="font-semibold text-foreground block text-sm mt-0.5">{username}</span>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => router.push("/profile")} className="cursor-pointer">
                <UserIcon className="size-4 mr-2" />
                Profile & Settings
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleLogout} className="cursor-pointer text-destructive focus:text-destructive">
                <LogOutIcon className="size-4 mr-2" />
                Log out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  )
}
