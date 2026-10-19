import { Metadata } from "next"
import { Suspense } from "react"
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
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center bg-background">Loading...</div>}>
      <div className="min-h-screen flex items-center justify-center bg-background p-4">{children}</div>
    </Suspense>
  )
}
