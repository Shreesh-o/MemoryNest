"use client"

import { Suspense, useEffect } from "react"
import { useRouter, usePathname } from "next/navigation"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { authMe } from "@/lib/api"
import { Skeleton } from "@/components/ui/skeleton"
import { Sidebar } from "@/components/app-shell/sidebar"
import { TopBar } from "@/components/app-shell/top-bar"
import { MobileNav } from "@/components/app-shell/mobile-nav"

function MeQuery() {
  const queryClient = useQueryClient()
  return useQuery({
    queryKey: ["me"],
    queryFn: async () => {
      const result = await authMe()
      if (!result.ok) {
        if (result.error?.status === 401) {
          return null
        }
        throw new Error(result.error?.detail || "Failed to fetch user")
      }
      return result.data
    },
    retry: false,
    staleTime: 0,
    refetchOnMount: "always",
  })
}

function PageTitle({ pathname }: { pathname: string }) {
  const titles: Record<string, string> = {
    "/dashboard": "Dashboard",
    "/documents": "Documents",
    "/upload": "Upload",
  }
  return titles[pathname] || "MemoryNest"
}

function GuardedContent({ children }: { children: React.ReactNode }) {
  const { data: user, isLoading, isFetching, isError, error } = MeQuery()
  const router = useRouter()
  const pathname = usePathname()
  const queryClient = useQueryClient()

  useEffect(() => {
    // Only redirect when settled on a 401 error and not currently fetching
    if (isError && !isFetching) {
      const apiError = error as { status?: number; detail?: string } | null
      if (apiError?.status === 401) {
        router.replace("/login")
      }
    }
  }, [isError, isFetching, error, router, pathname])

  // Show skeleton while loading or refetching without data
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

  if (!user) {
    return null
  }

  return (
    <div className="min-h-screen bg-background flex">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 md:ml-64">
        <TopBar pageTitle={PageTitle({ pathname })} />
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
