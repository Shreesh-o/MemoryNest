"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { toast } from "sonner"
import { authRegister, authLogin } from "@/lib/api"
import { useQueryClient } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card"
import { Archive, AlertCircleIcon, Loader2Icon, ArrowLeft } from "lucide-react"

export const dynamic = "force-dynamic"

export default function RegisterPage() {
  const router = useRouter()
  const queryClient = useQueryClient()
  const [username, setUsername] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [error, setError] = useState("")
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    if (password !== confirmPassword) {
      setError("Passwords do not match")
      toast.error("Passwords do not match")
      return
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters")
      toast.error("Password must be at least 6 characters")
      return
    }

    setIsLoading(true)

    try {
      const result = await authRegister({ username, email: email || undefined, password })
      if (result.ok) {
        const loginResult = await authLogin({ username, password })
        if (loginResult.ok) {
          queryClient.setQueryData(["me"], loginResult.data)
          toast.success("Account created successfully")
          router.replace("/dashboard")
        } else if (loginResult.error) {
          setError(loginResult.error.detail)
          toast.error(loginResult.error.detail)
        }
      } else if (result.error) {
        setError(result.error.detail)
        toast.error(result.error.detail)
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Registration failed"
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
        <span>ENCLAVE // PROVISION</span>
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
            Provision your local personal knowledge enclave
          </CardDescription>
        </CardHeader>

        <CardContent className="pt-2">
          <form onSubmit={handleSubmit} className="space-y-3.5">
            <div className="space-y-1">
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
                placeholder="Enter username (3-32 chars)"
                required
                minLength={3}
                maxLength={32}
                disabled={isLoading}
                className="h-10 text-sm font-sans rounded-lg border-border"
              />
            </div>

            <div className="space-y-1">
              <Label htmlFor="email" className="text-xs font-mono font-medium uppercase tracking-wider text-muted-foreground">
                Email (optional)
              </Label>
              <Input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                disabled={isLoading}
                className="h-10 text-sm font-sans rounded-lg border-border"
              />
            </div>

            <div className="space-y-1">
              <Label htmlFor="password" className="text-xs font-mono font-medium uppercase tracking-wider text-muted-foreground">
                Password
              </Label>
              <Input
                id="password"
                name="password"
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Min 6 characters"
                required
                minLength={6}
                disabled={isLoading}
                className="h-10 text-sm font-sans rounded-lg border-border"
              />
            </div>

            <div className="space-y-1">
              <Label htmlFor="confirmPassword" className="text-xs font-mono font-medium uppercase tracking-wider text-muted-foreground">
                Confirm Password
              </Label>
              <Input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm password"
                required
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
              className="w-full h-10 font-semibold shadow-xs transition-all cursor-pointer mt-1 rounded-lg"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2Icon className="size-4 mr-2 animate-spin" aria-hidden="true" />
                  <span>Provisioning enclave...</span>
                </>
              ) : (
                "Initialize Vault"
              )}
            </Button>
          </form>
        </CardContent>

        <CardFooter className="flex justify-center border-t border-border/60 bg-muted/20 py-4 rounded-b-xl">
          <p className="text-xs text-muted-foreground font-sans">
            Already have an enclave?{" "}
            <Link
              href="/login"
              className="font-medium text-foreground underline-offset-4 hover:underline hover:text-primary transition-colors"
            >
              Sign in
            </Link>
          </p>
        </CardFooter>
      </Card>
    </main>
  )
}
