"use client"

import { Suspense } from "react"
import { useQuery } from "@tanstack/react-query"
import { useRouter } from "next/navigation"
import { useEffect } from "react"

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

export function AuthLayoutClient({
  children,
}: {
  children: React.ReactNode
}) {
  const { data: user, isLoading, isFetching } = useQuery({
    queryKey: ["me"],
    queryFn: fetchMe,
    retry: false,
    staleTime: 0,
    refetchOnMount: "always",
  })
  const router = useRouter()

  useEffect(() => {
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
