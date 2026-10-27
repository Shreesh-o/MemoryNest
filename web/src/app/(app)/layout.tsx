"use client"

import { Suspense, useEffect } from "react"
import { useRouter, usePathname } from "next/navigation"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { Skeleton } from "@/components/ui/skeleton"
import { Sidebar } from "@/components/app-shell/sidebar"
import { TopBar } from "@/components/app-shell/top-bar"
import { MobileNav } from "@/components/app-shell/mobile-nav"
import { AlertTriangleIcon, RefreshCwIcon, LogInIcon } from "lucide-react"
import { cn } from "@/lib/utils"

function fetchMe() {
  return fetch("/api/auth/me", { credentials: "include" }).then(async (response) => {
    if (!response.ok) {
      if (response.status === 401) {
        throw new Error("Unauthorized")
      }
      const data = await response.json()
      throw new Error(data.detail || "Failed to fetch user")
    }
    return response.json()
  })
}

async function logoutApi() {
  try {
    await fetch("/api/auth/logout", { method: "POST", credentials: "include" })
  } catch {
    // Ignore errors - best effort
  }
}

function GuardedContent({ children }: { children: React.ReactNode }) {
  const { data: user, error, isLoading, isFetching, isError, refetch } = useQuery({
    queryKey: ["me"],
    queryFn: fetchMe,
    retry: false,
    staleTime: 0,
    refetchOnMount: "always",
  })
  const router = useRouter()
  const pathname = usePathname()
  const queryClient = useQueryClient()

  useEffect(() => {
    if (isError && !isFetching && error?.message === "Unauthorized") {
      logoutApi()
      queryClient.clear()
      router.replace("/login")
    }
  }, [isError, isFetching, error, router, queryClient])

  const isPending = (isLoading || isFetching) && !user
  if (isPending) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="space-y-4 max-w-md w-full mx-auto">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </div>
      </div>
    )
  }

  if (isError && !user) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className="rounded-xl border border-border bg-card text-card-foreground shadow-sm p-6">
            <div className="text-center space-y-4">
              <div className="mx-auto flex size-12 items-center justify-center rounded-xl bg-destructive/10 text-destructive">
                <AlertTriangleIcon className="size-6" />
              </div>
              <h2 className="text-xl font-semibold">Can&apos;t reach the server</h2>
              <p className="text-muted-foreground text-sm">
                An unexpected error occurred. This might be a temporary network issue.
              </p>
              <div className="flex gap-2 justify-center">
                <button
                  onClick={() => refetch()}
                  disabled={isFetching}
                  className="inline-flex items-center justify-center gap-2 rounded-lg border border-border bg-transparent px-4 py-2 text-sm font-medium ring-offset-background transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 cursor-pointer"
                >
                  <RefreshCwIcon className={cn("size-4", isFetching && "animate-spin")} />
                  Retry
                </button>
                <a
                  href="/login"
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-xs hover:bg-primary/90 cursor-pointer"
                >
                  <LogInIcon className="size-4" />
                  Login
                </a>
              </div>
              <hr className="my-4 border-border" />
              <p className="text-xs text-muted-foreground">
                The authentication check failed. This might be a temporary network issue.
              </p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (!user) {
    return null
  }

  const titles: Record<string, string> = {
    "/dashboard": "Dashboard",
    "/documents": "Documents",
    "/upload": "Upload",
    "/map": "Document Map",
    "/summaries": "Summaries",
    "/reminders": "Reminders",
    "/chat": "Chat",
    "/search": "Search",
    "/profile": "Profile & Settings",
  }
  const pageTitle = titles[pathname] || "MemoryNest"

  return (
    <div className="min-h-screen bg-background flex">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 md:ml-64">
        <TopBar pageTitle={pageTitle} />
        <main className="flex-1 p-4 md:p-6">
          {children}
        </main>
      </div>
      <MobileNav />
    </div>
  )
}

export default function AppLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen bg-background">
      <Suspense fallback={null}>
        <GuardedContent>{children}</GuardedContent>
      </Suspense>
    </div>
  )
}
