"use client"

import { useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import Link from "next/link"
import { toast } from "sonner"
import { authLogin } from "@/lib/api"
import { useQueryClient } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card"
import { Archive, AlertCircleIcon, Loader2Icon, ArrowLeft } from "lucide-react"

export const dynamic = "force-dynamic"

export default function LoginPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const queryClient = useQueryClient()
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [isLoading, setIsLoading] = useState(false)

  // Validate callbackUrl is a same-origin relative path starting with "/"
  const getSafeCallbackUrl = () => {
    const url = searchParams?.get("callbackUrl") || ""
    if (url.startsWith("/") && !url.startsWith("//")) {
      return url
    }
    return "/dashboard"
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setIsLoading(true)

    try {
      const result = await authLogin({ username, password })
      if (result.ok) {
        queryClient.setQueryData(["me"], result.data)
        toast.success("Logged in successfully")
        router.replace(getSafeCallbackUrl())
      } else if (result.error) {
        setError(result.error.detail)
        toast.error(result.error.detail)
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Login failed"
      setError(msg)
      toast.error(msg)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main tabIndex={-1} className="relative min-h-screen w-full flex flex-col items-center justify-center bg-background px-4 py-12 selection:bg-primary/15 selection:text-foreground focus:outline-none">
      {/* Back to Home Link */}
      <div className="w-full max-w-md mb-4 flex justify-between items-center text-xs font-mono text-muted-foreground">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 hover:text-foreground transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded px-1.5 py-1"
        >
          <ArrowLeft className="size-3.5" aria-hidden="true" />
          <span>Return to Overview</span>
        </Link>
        <span>ENCLAVE // AUTH_GATE</span>
      </div>

      <Card className="w-full max-w-md border border-border/80 bg-card p-2 shadow-sm paper-folio text-card-foreground">
        <CardHeader className="text-center pb-4 pt-6">
          <div className="mx-auto mb-3 flex size-11 items-center justify-center rounded-xl bg-foreground text-background shadow-xs">
            <Archive className="size-5" aria-hidden="true" />
          </div>
          <h1 className="font-heading text-2xl font-bold tracking-tight text-foreground">
            MemoryNest
          </h1>
          <CardDescription className="text-xs sm:text-sm text-muted-foreground mt-1 font-sans">
            Sign in to access your local personal knowledge vault
          </CardDescription>
        </CardHeader>

        <CardContent className="pt-2">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="username" className="text-xs font-mono font-medium uppercase tracking-wider text-muted-foreground">
                Username
              </Label>
              <Input
                id="username"
                name="username"
                type="text"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter your username"
                required
                disabled={isLoading}
                className="h-10 text-sm font-sans rounded-lg border-border"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password" className="text-xs font-mono font-medium uppercase tracking-wider text-muted-foreground">
                Password
              </Label>
              <Input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                required
                minLength={6}
                disabled={isLoading}
                className="h-10 text-sm font-sans rounded-lg border-border"
              />
            </div>

            {error && (
              <div
                className="flex items-center gap-2 rounded-lg border border-destructive/20 bg-destructive/10 p-2.5 text-xs font-medium text-destructive animate-in fade-in"
                role="alert"
              >
                <AlertCircleIcon className="size-4 shrink-0" aria-hidden="true" />
                <span>{error}</span>
              </div>
            )}

            <Button
              type="submit"
              className="w-full h-10 font-semibold shadow-xs transition-all cursor-pointer rounded-lg"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2Icon className="size-4 mr-2 animate-spin" aria-hidden="true" />
                  <span>Authenticating...</span>
                </>
              ) : (
                "Sign in"
              )}
            </Button>
          </form>
        </CardContent>

        <CardFooter className="flex justify-center border-t border-border/60 bg-muted/20 py-4 rounded-b-xl">
          <p className="text-xs text-muted-foreground font-sans">
            Don&apos;t have an account?{" "}
            <Link
              href="/register"
              className="font-medium text-foreground underline-offset-4 hover:underline hover:text-primary transition-colors"
            >
              Initialize Vault
            </Link>
          </p>
        </CardFooter>
      </Card>
    </main>
  )
}
