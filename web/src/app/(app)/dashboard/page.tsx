"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { formatDate } from "@/lib/api"
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { EmptyState } from "@/components/ui/empty-state"
import {
  CalendarIcon,
  ClockIcon,
  UploadCloudIcon,
  MessageSquareIcon,
  AlertCircleIcon,
  RefreshCwIcon,
  LayersIcon,
  FileTextIcon,
  ArrowRightIcon,
  CheckCircle2Icon,
  CpuIcon,
} from "lucide-react"

type DashboardData = {
  total_documents: number
  ready_documents: number
  failed_documents: number
  pending_documents: number
  total_chunks: number
  pending_events: Array<{
    id: number
    event_text: string
    event_date?: string | null
    raw_date?: string | null
    document_id?: number | null
  }>
  confirmed_events: Array<{
    id: number
    event_text: string
    event_date?: string | null
    raw_date?: string | null
    document_id?: number | null
  }>
  upcoming_deadlines: Array<{
    id: number
    event_text: string
    event_date?: string | null
    raw_date?: string | null
    document_id?: number | null
  }>
  recent_conversations: Array<{
    id: number
    title?: string | null
    created_at?: string | null
    updated_at?: string | null
  }>
}

type HealthStatus = {
  status: string
  ollama: string
  mock_llm: boolean
}

export default function DashboardPage() {
  useEffect(() => {
    document.title = "Dashboard — MemoryNest"
  }, [])

  const router = useRouter()
  const [data, setData] = useState<DashboardData | null>(null)
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function load() {
      try {
        const [dRes, hRes] = await Promise.all([
          fetch("/api/dashboard", { credentials: "include" }),
          fetch("/api/health"),
        ])
        if (dRes.ok) {
          setData(await dRes.json())
        } else {
          setError("Failed to load dashboard data")
        }
        if (hRes.ok) {
          setHealth(await hRes.json())
        }
      } catch {
        setError("Failed to connect to server")
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const goToUpload = () => router.push("/upload")
  const goToChat = () => router.push("/chat")
  const goToReminders = () => router.push("/reminders")
  const goToDocuments = () => router.push("/documents")

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto py-8">
        <Card className="border border-border/80">
          <CardHeader>
            <CardTitle>Dashboard</CardTitle>
            <CardDescription>Loading your knowledge vault stats...</CardDescription>
          </CardHeader>
          <CardContent className="flex items-center justify-center h-64">
            <RefreshCwIcon className="size-8 animate-spin text-primary" />
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-6xl mx-auto py-8">
        <Card className="border border-destructive/30">
          <CardHeader>
            <CardTitle>Dashboard</CardTitle>
            <CardDescription>Something went wrong</CardDescription>
          </CardHeader>
          <CardContent className="text-center py-12">
            <AlertCircleIcon className="mx-auto size-12 text-destructive mb-4" />
            <h3 className="text-lg font-medium mb-2">Failed to load dashboard</h3>
            <p className="text-muted-foreground mb-4 text-sm">{error}</p>
            <Button variant="outline" onClick={() => window.location.reload()}>
              <RefreshCwIcon className="mr-2 size-4" />
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!data) {
    return null
  }

  const badgeVariant = () => {
    if (!health) return "secondary" as const
    if (health.ollama === "down") return "destructive" as const
    if (health.mock_llm) return "warning" as const
    return "success" as const
  }

  const badgeText = () => {
    if (!health) return "Status: Unknown"
    if (health.ollama === "down") return "LLM Down"
    if (health.mock_llm) return "Mock LLM Mode"
    return "Ollama Active"
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-border/60">
        <div>
          <h1 className="font-heading text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
            Dashboard
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Overview of your local documents, indexed knowledge, and upcoming dates
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          {health && (
            <Badge variant={badgeVariant()} className="gap-1.5 py-1 px-2.5 text-xs font-medium">
              <CpuIcon className="size-3.5" />
              <span>{badgeText()}</span>
            </Badge>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => window.location.reload()}
            className="text-xs h-8 gap-1.5 cursor-pointer"
          >
            <RefreshCwIcon className="size-3.5" />
            <span>Refresh</span>
          </Button>
        </div>
      </div>

      {/* 4 Stat Cards in Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Documents */}
        <Card className="hover:border-border transition-all">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Documents
            </CardTitle>
            <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <FileTextIcon className="size-4" />
            </div>
          </CardHeader>
          <CardContent className="space-y-1.5">
            <div className="font-heading text-3xl font-bold tracking-tight text-foreground">
              {data.ready_documents}
              <span className="text-sm font-normal text-muted-foreground ml-1.5">
                / {data.total_documents} total
              </span>
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground pt-1">
              <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium">
                <CheckCircle2Icon className="size-3" />
                {data.ready_documents} ready
              </span>
              {data.failed_documents > 0 && (
                <span className="text-destructive font-medium">
                  • {data.failed_documents} failed
                </span>
              )}
              {data.pending_documents > 0 && (
                <span className="text-amber-600 font-medium">
                  • {data.pending_documents} pending
                </span>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Total Chunks */}
        <Card className="hover:border-border transition-all">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Vector Chunks
            </CardTitle>
            <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <LayersIcon className="size-4" />
            </div>
          </CardHeader>
          <CardContent className="space-y-1.5">
            <div className="font-heading text-3xl font-bold tracking-tight text-foreground">
              {data.total_chunks.toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground pt-1">
              Embedded in local ChromaDB
            </p>
          </CardContent>
        </Card>

        {/* Pending Events */}
        <Card className="hover:border-border transition-all">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Extracted Events
            </CardTitle>
            <div className="flex size-8 items-center justify-center rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400">
              <ClockIcon className="size-4" />
            </div>
          </CardHeader>
          <CardContent className="space-y-1.5">
            <div className="font-heading text-3xl font-bold tracking-tight text-foreground">
              {data.pending_events.length}
            </div>
            <button
              onClick={goToReminders}
              className="inline-flex items-center gap-1 text-xs text-primary hover:underline font-medium pt-1 cursor-pointer"
            >
              <span>Review in Reminders</span>
              <ArrowRightIcon className="size-3" />
            </button>
          </CardContent>
        </Card>

        {/* Recent Chats */}
        <Card className="hover:border-border transition-all">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Conversations
            </CardTitle>
            <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <MessageSquareIcon className="size-4" />
            </div>
          </CardHeader>
          <CardContent className="space-y-1.5">
            <div className="font-heading text-3xl font-bold tracking-tight text-foreground">
              {data.recent_conversations.length}
            </div>
            <button
              onClick={goToChat}
              className="inline-flex items-center gap-1 text-xs text-primary hover:underline font-medium pt-1 cursor-pointer"
            >
              <span>Open Chat Assistant</span>
              <ArrowRightIcon className="size-3" />
            </button>
          </CardContent>
        </Card>
      </div>

      {/* Two Column Section: Upcoming Deadlines & Recent Chats */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Upcoming Deadlines */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CalendarIcon className="size-4.5 text-primary" />
              <h2 className="font-heading text-base font-semibold tracking-tight text-foreground">
                Upcoming Deadlines
              </h2>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={goToReminders}
              className="text-xs h-7 text-muted-foreground hover:text-foreground"
            >
              View Calendar
            </Button>
          </div>

          <Card className="border border-border/80 min-h-[260px] flex flex-col justify-center">
            <CardContent className="p-4">
              {data.upcoming_deadlines.length === 0 ? (
                <EmptyState
                  icon={<CalendarIcon />}
                  title="No upcoming deadlines"
                  description="Documents with detected dates and milestones will appear here."
                  className="border-none bg-transparent min-h-[200px]"
                />
              ) : (
                <div className="space-y-2.5">
                  {data.upcoming_deadlines.map((event) => (
                    <div
                      key={event.id}
                      className="group flex items-start gap-3 p-3 rounded-lg border border-border/60 hover:border-border hover:bg-muted/40 transition-all cursor-pointer"
                      onClick={() => goToReminders()}
                    >
                      <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-amber-500/10 text-amber-600 dark:text-amber-400 mt-0.5">
                        <ClockIcon className="size-4" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-foreground truncate group-hover:text-primary transition-colors">
                          {event.event_text}
                        </p>
                        <p className="text-xs text-muted-foreground font-mono mt-0.5">
                          {event.event_date || event.raw_date || "Date Pending"}
                        </p>
                      </div>
                      <ArrowRightIcon className="size-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity mt-1 shrink-0" />
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Recent Chats */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MessageSquareIcon className="size-4.5 text-primary" />
              <h2 className="font-heading text-base font-semibold tracking-tight text-foreground">
                Recent Conversations
              </h2>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={goToChat}
              className="text-xs h-7 text-muted-foreground hover:text-foreground"
            >
              Open Chat
            </Button>
          </div>

          <Card className="border border-border/80 min-h-[260px] flex flex-col justify-center">
            <CardContent className="p-4">
              {data.recent_conversations.length === 0 ? (
                <EmptyState
                  icon={<MessageSquareIcon />}
                  title="No conversations yet"
                  description="Ask questions across your documents with citations in real time."
                  action={
                    <Button size="sm" onClick={goToChat} className="text-xs h-8">
                      Start First Chat
                    </Button>
                  }
                  className="border-none bg-transparent min-h-[200px]"
                />
              ) : (
                <div className="space-y-2.5">
                  {data.recent_conversations.map((convo) => (
                    <div
                      key={convo.id}
                      className="group flex items-start gap-3 p-3 rounded-lg border border-border/60 hover:border-border hover:bg-muted/40 transition-all cursor-pointer"
                      onClick={() => router.push(`/chat?c=${convo.id}`)}
                    >
                      <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary mt-0.5">
                        <MessageSquareIcon className="size-4" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-foreground truncate group-hover:text-primary transition-colors">
                          {convo.title || "Untitled Conversation"}
                        </p>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {formatDate(convo.updated_at || convo.created_at)}
                        </p>
                      </div>
                      <ArrowRightIcon className="size-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity mt-1 shrink-0" />
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Quick Action Tiles */}
      <div className="space-y-3 pt-2">
        <h2 className="font-heading text-base font-semibold tracking-tight text-foreground">
          Quick Actions
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Button
            onClick={goToUpload}
            variant="outline"
            className="h-auto flex flex-col items-center justify-center gap-2.5 p-5 border-border/80 hover:border-primary/50 hover:bg-muted/30 transition-all group cursor-pointer"
          >
            <div className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary group-hover:scale-105 transition-transform">
              <UploadCloudIcon className="size-5" />
            </div>
            <div className="text-center">
              <span className="block text-sm font-semibold text-foreground">Upload Files</span>
              <span className="text-[11px] text-muted-foreground">PDF, DOCX, TXT, OCR</span>
            </div>
          </Button>

          <Button
            onClick={goToChat}
            variant="outline"
            className="h-auto flex flex-col items-center justify-center gap-2.5 p-5 border-border/80 hover:border-primary/50 hover:bg-muted/30 transition-all group cursor-pointer"
          >
            <div className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary group-hover:scale-105 transition-transform">
              <MessageSquareIcon className="size-5" />
            </div>
            <div className="text-center">
              <span className="block text-sm font-semibold text-foreground">Ask Assistant</span>
              <span className="text-[11px] text-muted-foreground">RAG with citations</span>
            </div>
          </Button>

          <Button
            onClick={goToDocuments}
            variant="outline"
            className="h-auto flex flex-col items-center justify-center gap-2.5 p-5 border-border/80 hover:border-primary/50 hover:bg-muted/30 transition-all group cursor-pointer"
          >
            <div className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary group-hover:scale-105 transition-transform">
              <FileTextIcon className="size-5" />
            </div>
            <div className="text-center">
              <span className="block text-sm font-semibold text-foreground">View Documents</span>
              <span className="text-[11px] text-muted-foreground">Vault inventory</span>
            </div>
          </Button>

          <Button
            onClick={goToReminders}
            variant="outline"
            className="h-auto flex flex-col items-center justify-center gap-2.5 p-5 border-border/80 hover:border-primary/50 hover:bg-muted/30 transition-all group cursor-pointer"
          >
            <div className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary group-hover:scale-105 transition-transform">
              <CalendarIcon className="size-5" />
            </div>
            <div className="text-center">
              <span className="block text-sm font-semibold text-foreground">Reminders</span>
              <span className="text-[11px] text-muted-foreground">Calendar & Sync</span>
            </div>
          </Button>
        </div>
      </div>
    </div>
  )
}
