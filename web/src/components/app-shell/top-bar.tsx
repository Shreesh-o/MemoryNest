"use client"

import Link from "next/link"
import { useTheme } from "next-themes"
import { useRouter } from "next/navigation"
import { useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { authLogout } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { XIcon, SunIcon, MoonIcon, MonitorIcon, LogOutIcon, LayoutDashboardIcon, FileTextIcon, UploadIcon, MessageSquareIcon, ClockIcon } from "lucide-react"
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

  const handleLogout = async () => {
    const result = await authLogout()
    if (result.ok) {
      queryClient.clear()
      toast.success("Logged out")
      router.push("/login")
      router.refresh()
    } else if (result.error) {
      toast.error(result.error.detail)
    }
  }

  // In a real app, this would come from the auth context
  const currentUser = "User"

  return (
    <header className="sticky top-0 z-30 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 md:ml-64">
      <div className="flex h-16 items-center gap-4 px-4">
        {/* Mobile menu button */}
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
              <Separator className="my-4" />
              <div className="flex items-center gap-3 px-3 py-2.5 text-muted-foreground opacity-50">
                <MessageSquareIcon className="h-5 w-5" />
                <span>Chat</span>
                <Badge variant="secondary" className="ml-auto text-xs">Soon</Badge>
              </div>
              <div className="flex items-center gap-3 px-3 py-2.5 text-muted-foreground opacity-50">
                <FileTextIcon className="h-5 w-5" />
                <span>Summaries</span>
                <Badge variant="secondary" className="ml-auto text-xs">Soon</Badge>
              </div>
              <div className="flex items-center gap-3 px-3 py-2.5 text-muted-foreground opacity-50">
                <ClockIcon className="h-5 w-5" />
                <span>Reminders</span>
                <Badge variant="secondary" className="ml-auto text-xs">Soon</Badge>
              </div>
            </nav>
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
          <DropdownMenuTrigger>
            <Button variant="ghost" className="relative h-9 w-9 rounded-full">
              <Avatar className="h-9 w-9">
                <AvatarFallback className="font-medium">
                  {currentUser.charAt(0).toUpperCase()}
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel className="font-medium">
              {currentUser}
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleLogout}>
              <LogOutIcon className="h-4 w-4 mr-2" />
              Logout
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
