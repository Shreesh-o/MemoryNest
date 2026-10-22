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
import {
  SvgCalendar,
  SvgClock,
  SvgUpload,
  SvgMessageSquare,
  SvgAlertCircle,
  SvgPlus,
  SvgRefreshCw,
  SvgCheck,
  SvgDownload,
  SvgFile,
} from "@/components/ui/icons"
import { Badge } from "@/components/ui/badge"
import { toast } from "sonner"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"

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
      <div className="p-6 max-w-4xl mx-auto">
        <Card>
          <CardHeader>
            <CardTitle>Dashboard</CardTitle>
            <CardDescription>Loading your data...</CardDescription>
          </CardHeader>
          <CardContent className="flex items-center justify-center h-64">
            <SvgRefreshCw className="h-8 w-8 animate-spin text-primary" />
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <Card>
          <CardHeader>
            <CardTitle>Dashboard</CardTitle>
            <CardDescription>Something went wrong</CardDescription>
          </CardHeader>
          <CardContent className="text-center py-12">
            <SvgAlertCircle className="mx-auto h-12 w-12 text-destructive mb-4" />
            <h3 className="text-lg font-medium mb-2">Failed to load dashboard</h3>
            <p className="text-muted-foreground mb-4">{error}</p>
            <Button variant="outline" onClick={() => window.location.reload()}>
              <SvgRefreshCw className="mr-2 h-4 w-4" />
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
    if (!health) return "secondary"
    if (health.ollama === "down") return "destructive"
    if (health.mock_llm) return "secondary"
    return "secondary"
  }

  const badgeText = () => {
    if (!health) return "Unknown"
    if (health.ollama === "down") return "LLM Down"
    if (health.mock_llm) return "Mock LLM"
    return "LLM Up"
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">Your knowledge base at a glance</p>
        </div>
        <div className="flex items-center gap-2">
          {health && (
            <Badge variant={badgeVariant()} className="text-xs">
              {badgeText()}
            </Badge>
          )}
          <Button variant="outline" size="sm" onClick={() => window.location.reload()}>
            <SvgRefreshCw className="mr-2 h-4 w-4" /> Refresh
          </Button>
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid gap-4 mb-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between py-4">
            <div>
              <CardTitle className="text-sm font-medium">Documents</CardTitle>
              <CardDescription className="text-xs">
                {data.ready_documents} ready of {data.total_documents} total
              </CardDescription>
            </div>
            <SvgFile className="h-5 w-5 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.ready_documents}</div>
            <p className="text-xs text-muted-foreground mt-2">
              {data.failed_documents} failed • {data.pending_documents} processing
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between py-4">
            <div>
              <CardTitle className="text-sm font-medium">Total Chunks</CardTitle>
              <CardDescription className="text-xs">Indexed text chunks</CardDescription>
            </div>
            <SvgCheck className="h-5 w-5 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.total_chunks}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between py-4">
            <div>
              <CardTitle className="text-sm font-medium">Pending Events</CardTitle>
              <CardDescription className="text-xs">Awaiting confirmation</CardDescription>
            </div>
            <SvgClock className="h-5 w-5 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.pending_events.length}</div>
            <Button
              variant="link"
              size="sm"
              className="mt-2 p-0 text-primary-foreground hover:bg-accent"
              onClick={goToReminders}
            >
              View Reminders
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between py-4">
            <div>
              <CardTitle className="text-sm font-medium">Recent Chats</CardTitle>
              <CardDescription className="text-xs">{data.recent_conversations.length} conversations</CardDescription>
            </div>
            <SvgMessageSquare className="h-5 w-5 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.recent_conversations.length}</div>
            <Button
              variant="link"
              size="sm"
              className="mt-2 p-0 text-primary-foreground hover:bg-accent"
              onClick={goToChat}
            >
              View Chats
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Upcoming deadlines */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Upcoming Deadlines</h2>
          <Button
            variant="outline"
            size="sm"
            onClick={goToReminders}
          >
            View All Reminders
          </Button>
        </div>
        <Card>
          <CardContent className="p-4">
            {data.upcoming_deadlines.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                <SvgCalendar className="h-8 w-8 mb-2 opacity-50" />
                <p>No upcoming deadlines</p>
              </div>
            ) : (
              <div className="space-y-3">
                {data.upcoming_deadlines.map((event) => (
                  <div
                    key={event.id}
                    className="flex items-center gap-3 p-3 rounded-lg border border-muted/50 hover:bg-muted/50 transition-colors cursor-pointer"
                    onClick={() => goToReminders()}
                  >
                    <SvgClock className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{event.event_text}</p>
                      <p className="text-xs text-muted-foreground">
                        {event.event_date || "TBD"}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent chats */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Recent Chats</h2>
          <Button variant="outline" size="sm" onClick={goToChat}>
            View All Chats
          </Button>
        </div>
        <Card>
          <CardContent className="p-4">
            {data.recent_conversations.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                <SvgMessageSquare className="h-8 w-8 mb-2 opacity-50" />
                <p>No chats yet</p>
                <p className="text-xs">Start asking questions about your documents</p>
              </div>
            ) : (
              <div className="space-y-3">
                {data.recent_conversations.map((convo) => (
                  <div
                    key={convo.id}
                    className="flex items-center gap-3 p-3 rounded-lg border border-muted/50 hover:bg-muted/50 transition-colors cursor-pointer"
                    onClick={() => router.push(`/chat?c=${convo.id}`)}
                  >
                    <SvgMessageSquare className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">
                        {convo.title || "Untitled"}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {formatDate(convo.updated_at || convo.created_at)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick actions */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-4">Quick Actions</h2>
        <div className="grid gap-3 grid-cols-2 md:grid-cols-4">
          <Button
            onClick={goToUpload}
            className="w-full flex flex-col items-center gap-2 py-6"
            variant="outline"
          >
            <SvgUpload className="h-6 w-6 text-primary" />
            <span className="text-sm font-medium">Upload File</span>
          </Button>
          <Button
            onClick={goToChat}
            className="w-full flex flex-col items-center gap-2 py-6"
            variant="outline"
          >
            <SvgMessageSquare className="h-6 w-6 text-primary" />
            <span className="text-sm font-medium">Ask a Question</span>
          </Button>
          <Button
            onClick={goToDocuments}
            className="w-full flex flex-col items-center gap-2 py-6"
            variant="outline"
          >
            <SvgFile className="h-6 w-6 text-primary" />
            <span className="text-sm font-medium">View Documents</span>
          </Button>
          <Button
            onClick={goToReminders}
            className="w-full flex flex-col items-center gap-2 py-6"
            variant="outline"
          >
            <SvgCalendar className="h-6 w-6 text-primary" />
            <span className="text-sm font-medium">View Reminders</span>
          </Button>
        </div>
      </div>
    </div>
  )
}