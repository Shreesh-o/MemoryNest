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
  XIcon,
  SunIcon,
  MoonIcon,
  MonitorIcon,
  LogOutIcon,
  LayoutDashboardIcon,
  FileTextIcon,
  UploadIcon,
  MessageSquareIcon,
  ClockIcon,
  SearchIcon,
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
  const { setTheme } = useTheme()
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

  return (
    <header className="sticky top-0 z-30 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-16 items-center gap-4 px-4">
        {/* Mobile menu button */}
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
              <Link href="/dashboard" className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-base font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground">
                <LayoutDashboardIcon className="h-5 w-5" />
                Dashboard
              </Link>
              <Link href="/documents" className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-base font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground">
                <FileTextIcon className="h-5 w-5" />
                Documents
              </Link>
              <Link href="/upload" className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-base font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground">
                <UploadIcon className="h-5 w-5" />
                Upload
              </Link>
              <Separator className="my-2" />
              <Link href="/chat" className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-base font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground">
                <MessageSquareIcon className="h-5 w-5" />
                <span>Chat</span>
              </Link>
              <Link href="/summaries" className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-base font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground">
                <FileTextIcon className="h-5 w-5" />
                <span>Summaries</span>
              </Link>
              <Link href="/reminders" className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-base font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground">
                <ClockIcon className="h-5 w-5" />
                <span>Reminders</span>
              </Link>
              <Link href="/search" className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-base font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground">
                <SearchIcon className="h-5 w-5" />
                <span>Search</span>
              </Link>
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

        {/* Page title */}
        <div className="flex-1 truncate">
          <h1 className="font-heading text-lg font-semibold truncate">{pageTitle}</h1>
        </div>

        {/* Theme toggle */}
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme("light")}
            aria-label="Light mode"
          >
            <SunIcon className="h-5 w-5" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme("dark")}
            aria-label="Dark mode"
          >
            <MoonIcon className="h-5 w-5" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme("system")}
            aria-label="System theme"
          >
            <MonitorIcon className="h-5 w-5" />
          </Button>
        </div>

        {/* User dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger
            render={
              <Button variant="ghost" className="relative h-9 w-9 rounded-full" />
            }
          >
            <Avatar className="h-9 w-9">
              <AvatarFallback className="font-medium">
                {userInitial}
              </AvatarFallback>
            </Avatar>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel className="font-medium">
              {username}
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleLogout}>
              <LogOutIcon className="h-4 w-4 mr-2" />
              Log out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
