"use client"

import { Suspense } from "react"
import { useQuery } from "@tanstack/react-query"
import { authMe } from "@/lib/api"
import { useRouter } from "next/navigation"
import { useEffect } from "react"

function MeQuery() {
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

export function AuthLayoutClient({
  children,
}: {
  children: React.ReactNode
}) {
  const { data: user, isLoading, isFetching } = MeQuery()
  const router = useRouter()

  useEffect(() => {
    // Only redirect when we have a user (not on error or loading)
    if (!isLoading && !isFetching && user) {
      router.replace("/dashboard")
    }
  }, [user, isLoading, isFetching, router])

  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center bg-background">Loading...</div>}>
      <div className="min-h-screen flex items-center justify-center bg-background p-4">{children}</div>
    </Suspense>
  )
}
