import { Metadata } from "next"
import { Suspense } from "react"
import { AuthLayoutClient } from "./auth-layout-client"
import "../globals.css"

export const metadata: Metadata = {
  title: "MemoryNest - Sign In",
  description: "Personal knowledge vault — local RAG over your documents.",
}

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <Suspense
      fallback={
        <main tabIndex={-1} className="min-h-screen flex items-center justify-center bg-background p-4">
          <h1 className="sr-only">MemoryNest Authentication</h1>
          <div className="text-sm font-mono text-muted-foreground">Loading authentication enclave...</div>
        </main>
      }
    >
      <AuthLayoutClient>{children}</AuthLayoutClient>
    </Suspense>
  )
}
