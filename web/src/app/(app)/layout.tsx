"use client"

import { Suspense, useEffect } from "react"
import { useRouter, usePathname } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import { Skeleton } from "@/components/ui/skeleton"
import { Sidebar } from "@/components/app-shell/sidebar"
import { TopBar } from "@/components/app-shell/top-bar"
import { MobileNav } from "@/components/app-shell/mobile-nav"

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

function GuardedContent({ children }: { children: React.ReactNode }) {
  const { data: user, isLoading, isFetching, isError, refetch } = useQuery({
    queryKey: ["me"],
    queryFn: fetchMe,
    retry: false,
    staleTime: 0,
    refetchOnMount: "always",
  })
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    if (isError && !isFetching) {
      router.replace("/login")
    }
  }, [isError, isFetching, router])

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
          <div className="rounded-lg border bg-card text-card-foreground shadow-sm p-6">
            <div className="text-center space-y-4">
              <svg className="h-12 w-12 text-destructive mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <h2 className="text-xl font-semibold">Can&apos;t reach the server</h2>
              <p className="text-muted-foreground">
                An unexpected error occurred. This might be a temporary network issue.
              </p>
              <div className="flex gap-2 justify-center">
                <button
                  onClick={() => refetch()}
                  disabled={isFetching}
                  className="inline-flex items-center justify-center gap-2 rounded-md border bg-transparent px-4 py-2 text-sm font-medium ring-offset-background transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Retry
                </button>
                <a
                  href="/login"
                  className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-sm hover:bg-primary/90"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
                  </svg>
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
