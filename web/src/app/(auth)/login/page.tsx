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
import { Layers, ArrowLeftIcon, AlertCircleIcon, Loader2Icon } from "lucide-react"

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
    <div className="relative min-h-screen w-full flex items-center justify-center bg-background px-4 py-12 selection:bg-primary/20">
      {/* Back to main showcase website */}
      <div className="absolute top-5 left-5 sm:top-8 sm:left-8 z-20">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-all duration-200 px-3.5 py-2 rounded-xl border border-border/70 bg-card/70 backdrop-blur-md hover:bg-muted/80 hover:border-border shadow-xs group"
        >
          <ArrowLeftIcon className="size-4 transition-transform group-hover:-translate-x-1" />
          <span>Back to website</span>
        </Link>
      </div>

      {/* Subtle decorative background blur */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-10 flex items-center justify-center overflow-hidden"
      >
        <div className="size-[34rem] rounded-full bg-primary/5 blur-3xl" />
      </div>

      <Card className="w-full max-w-lg border border-border/80 shadow-xl dark:shadow-2xl">
        <CardHeader className="text-center pb-6 pt-8 px-6 sm:px-10">
          <Link
            href="/"
            className="group mx-auto mb-4 flex flex-col items-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-2xl"
            title="Go to main website"
          >
            <div className="flex size-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-md transition-all duration-200 group-hover:scale-105 group-hover:shadow-lg">
              <Layers className="size-7" />
            </div>
            <CardTitle className="font-heading text-3xl font-bold tracking-tight text-foreground transition-colors group-hover:text-primary mt-3">
              MemoryNest
            </CardTitle>
          </Link>
          <CardDescription className="text-base text-muted-foreground mt-1">
            Sign in to your private knowledge vault
          </CardDescription>
        </CardHeader>

        <CardContent className="px-6 sm:px-10 pt-2 pb-6">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-2">
              <Label htmlFor="username" className="text-sm font-medium text-foreground">
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
                className="h-11 px-3.5 text-base sm:text-sm"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="text-sm font-medium text-foreground">
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
                className="h-11 px-3.5 text-base sm:text-sm"
              />
            </div>

            {error && (
              <div
                className="flex items-center gap-2 rounded-lg border border-destructive/20 bg-destructive/10 p-3 text-sm font-medium text-destructive animate-in fade-in"
                role="alert"
              >
                <AlertCircleIcon className="size-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <Button
              type="submit"
              className="w-full h-11 text-base font-semibold shadow-xs transition-all hover:shadow cursor-pointer mt-2"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2Icon className="size-4 mr-2 animate-spin" />
                  Signing in...
                </>
              ) : (
                "Sign in"
              )}
            </Button>
          </form>
        </CardContent>

        <CardFooter className="flex flex-col items-center gap-3.5 border-t border-border/60 bg-muted/20 py-6 px-6 sm:px-10">
          <p className="text-sm text-muted-foreground">
            Don&apos;t have an account?{" "}
            <Link
              href="/register"
              className="font-medium text-foreground underline-offset-4 hover:underline hover:text-primary transition-colors"
            >
              Sign up
            </Link>
          </p>
          <div className="w-full flex items-center justify-center pt-2 border-t border-border/40">
            <Link
              href="/"
              className="inline-flex items-center gap-1.5 text-xs sm:text-sm text-muted-foreground hover:text-foreground transition-colors group"
            >
              <ArrowLeftIcon className="size-3.5 transition-transform group-hover:-translate-x-0.5" />
              <span>Back to project showcase</span>
            </Link>
          </div>
        </CardFooter>
      </Card>
    </div>
  )
}
