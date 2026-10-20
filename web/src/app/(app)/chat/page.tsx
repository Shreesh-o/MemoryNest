"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { useRouter } from "next/navigation"
import { chatAsk, conversationsList, conversationsDelete, ConversationPublic } from "@/lib/api"
import { formatDate } from "@/lib/api"
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import {
  Sheet,
  SheetTrigger,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import {
  SvgPlus,
  SvgTrash2,
  SvgMessageSquare,
  SvgSend,
  SvgLoader2,
  SvgX,
  SvgAlertCircle,
  SvgCheckCircle,
  SvgRefreshCw,
} from "@/components/ui/icons"
import { toast } from "sonner"
import Markdown from "react-markdown"
import { SvgAlertTriangle } from "@/components/ui/icons"

type Conversation = ConversationPublic & { message_count?: number }

type Message = {
  id: number
  role: "user" | "assistant"
  content: string
  sources?: { document: string; chunk_index: number; similarity: number; document_id?: number }[]
  created_at?: string
}

const SUGGESTED_QUESTIONS = [
  "What documents do I have about meetings?",
  "Summarize my latest uploaded document",
  "Find all events scheduled for next month",
]

export default function ChatPage() {
  const router = useRouter()
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [messages, setMessages] = useState<Message[]>([])
  const [currentConversationId, setCurrentConversationId] = useState<number | null>(null)
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [])

  useEffect(() => {
    conversationsList().then(result => {
      if (result.ok) {
        setConversations(result.data)
      }
    }).catch(() => {
      toast.error("Failed to load conversations")
    })
  }, [])

  const handleNewChat = () => {
    setMessages([])
    setCurrentConversationId(null)
    setError(null)
    setSheetOpen(false)
  }

  const handleLoadConversation = async (conversationId: number) => {
    setCurrentConversationId(conversationId)
    try {
      const result = await fetch(`/api/conversations/${conversationId}`, { credentials: "include" })
      if (result.ok) {
        const convo = await result.json()
        // Load messages for this conversation
        const msgResult = await fetch(`/api/conversations/${conversationId}/messages`, { credentials: "include" })
        // We don't have a messages endpoint yet, so we'll just set the conversation ID
        // and let the user start fresh. The backend will continue the conversation.
        setMessages([])
      }
    } catch {
      toast.error("Failed to load conversation")
    }
    setSheetOpen(false)
  }

  const handleDeleteConversation = async (conversationId: number) => {
    try {
      const result = await conversationsDelete(conversationId)
      if (result.ok) {
        setConversations((prev) => prev.filter((c) => c.id !== conversationId))
        if (currentConversationId === conversationId) {
          handleNewChat()
        }
        toast.success("Conversation deleted")
      }
    } catch {
      toast.error("Failed to delete conversation")
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const question = input.trim()
    setInput("")
    setIsLoading(true)
    setError(null)

    // Add user message immediately
    const userMessage: Message = {
      id: Date.now(),
      role: "user",
      content: question,
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMessage])

    try {
      const result = await chatAsk({
        question,
        conversation_id: currentConversationId,
      })
      if (result.ok) {
        const { conversation_id, answer, sources } = result.data
        setCurrentConversationId(conversation_id)
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now() + 1,
            role: "assistant",
            content: answer,
            sources,
            created_at: new Date().toISOString(),
          },
        ])
      } else if (result.error?.status === 503) {
        setError(result.error.detail || "The language model is not running. Start Ollama and retry.")
        // Remove the user message on error
        setMessages((prev) => prev.slice(0, -1))
      } else {
        throw new Error(result.error?.detail || "Failed to get answer")
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to get answer"
      if (message.includes("503") || message.includes("Ollama") || message.includes("LLM")) {
        setError("The language model is not running. Start Ollama and retry.")
      } else {
        setError(message)
      }
      // Remove the user message on error
      setMessages((prev) => prev.slice(0, -1))
    } finally {
      setIsLoading(false)
    }
  }

  const handleRetry = () => {
    if (messages.length === 0) return
    const lastUserMessage = messages.findLast((m) => m.role === "user")
    if (!lastUserMessage) return

    // Remove messages after the last user message
    const lastUserIndex = messages.findLastIndex((m) => m.role === "user")
    setMessages(messages.slice(0, lastUserIndex + 1))
    setError(null)

    // Resubmit
    handleSubmit({ preventDefault: () => {} } as React.FormEvent)
  }

  const isMobile = typeof window !== "undefined" && window.innerWidth < 768

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar / Conversation List */}
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetTrigger>
          <Button variant="outline" size="icon" className="md:hidden lg:hidden xl:hidden">
            <SvgMessageSquare className="h-5 w-5" />
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="w-80 p-0">
          <SheetHeader className="flex flex-row items-center justify-between p-4">
            <SheetTitle>Conversations</SheetTitle>
            <Button
              variant="ghost"
              size="icon"
              onClick={handleNewChat}
              className="h-8 w-8"
            >
              <SvgPlus className="h-4 w-4" />
            </Button>
          </SheetHeader>
          <Separator />
          <ScrollArea className="flex-1 p-2">
            {conversations.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <SvgMessageSquare className="mx-auto h-10 w-10 mb-2 opacity-50" />
                <p className="text-sm">No conversations yet</p>
                <p className="text-xs">Start a new chat</p>
              </div>
            ) : (
              <div className="space-y-1">
                {conversations.map((convo) => (
                  <div
                    key={convo.id}
                    className={`flex items-center gap-2 p-2 rounded-lg transition-colors ${
                      currentConversationId === convo.id
                        ? "bg-primary text-primary-foreground"
                        : "hover:bg-accent text-accent-foreground"
                    }`}
                    onClick={() => {
                      setCurrentConversationId(convo.id)
                      setMessages([])
                      setSheetOpen(false)
                    }}
                  >
                    <SvgMessageSquare className="h-4 w-4 flex-shrink-0" />
                    <div className="flex-1 min-w-0 text-left">
                      <p className="text-sm font-medium truncate">
                        {convo.title || "Untitled"}
                      </p>
                      <p className="text-xs truncate opacity-70">
                        {formatDate(convo.updated_at || convo.created_at)}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDeleteConversation(convo.id)
                      }}
                    >
                      <SvgTrash2 className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </ScrollArea>
        </SheetContent>
      </Sheet>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-4 py-3">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-lg font-semibold">
                {currentConversationId
                  ? conversations.find((c) => c.id === currentConversationId)?.title || "Chat"
                  : "New Chat"}
              </h1>
              <p className="text-xs text-muted-foreground">
                {currentConversationId
                  ? `${conversations.find((c) => c.id === currentConversationId)?.message_count || 0} messages`
                  : "Start a new conversation"}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setSheetOpen(true)}
                className="lg:hidden xl:hidden"
              >
                <SvgMessageSquare className="h-5 w-5" />
              </Button>
              <Button variant="ghost" size="icon" onClick={handleNewChat}>
                <SvgPlus className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>

        {/* Messages */}
        <ScrollArea className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && !isLoading && !error ? (
            <div className="flex flex-col items-center justify-center h-full min-h-[300px] text-center">
              <SvgMessageSquare className="h-16 w-16 text-muted-foreground/50 mb-4" />
              <h2 className="text-xl font-medium mb-2">Start a conversation</h2>
              <p className="text-muted-foreground mb-6 max-w-md">
              Ask questions about your documents. I&apos;ll search through your uploaded files
              and provide answers with citations.
                and provide answers with citations.
              </p>
              <div className="space-y-2 w-full max-w-md">
                {SUGGESTED_QUESTIONS.map((q, i) => (
                  <Button
                    key={i}
                    variant="outline"
                    className="w-full justify-start text-left h-auto py-3 px-4 text-sm"
                    onClick={() => {
                      setInput(q)
                      handleSubmit({ preventDefault: () => {} } as React.FormEvent)
                    }}
                  >
                    {q}
                  </Button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {messages.map((msg, index) => (
                <div
                  key={msg.id}
                  className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
                >
                  <div
                    className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                      msg.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-muted-foreground"
                    }`}
                  >
                    {msg.role === "user" ? (
                      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                      </svg>
                    ) : (
                      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                      </svg>
                    )}
                  </div>
                  <div className={`flex-1 min-w-0 ${msg.role === "user" ? "text-right" : ""}`}>
                    <div
                      className={`prose prose-sm max-w-none ${
                        msg.role === "user" ? "prose-invert" : ""
                      }`}
                    >
                      <Markdown>{msg.content}</Markdown>
                    </div>
                    {msg.sources && msg.sources.length > 0 && (
                      <details className="mt-2 group">
                        <summary className="flex items-center gap-2 text-sm text-muted-foreground cursor-pointer">
                          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                          Sources ({msg.sources.length})
                          <svg className="ml-auto h-4 w-4 transition-transform group-open:rotate-90" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </summary>
                        <div className="mt-2 space-y-1 pl-6 border-l-2 border-muted">
                          {msg.sources.map((source, i) => (
                            <div key={i} className="text-xs text-muted-foreground">
                              <span className="font-medium">{source.document}</span>
                              {source.chunk_index !== undefined && (
                                <span> · chunk {source.chunk_index}</span>
                              )}
                              {source.similarity !== undefined && (
                                <span> · similarity {source.similarity.toFixed(3)}</span>
                              )}
                            </div>
                          ))}
                        </div>
                      </details>
                    )}
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex gap-3">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-muted flex items-center justify-center">
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                  </div>
                  <div className="flex-1">
                    <div className="h-4 bg-muted animate-pulse rounded w-3/4 mb-1" />
                    <div className="h-4 bg-muted animate-pulse rounded w-1/2" />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </>
          )}
        </ScrollArea>

        {/* Error Display */}
        {error && (
          <div className="border border-destructive bg-destructive/10 text-destructive p-4 mx-4 mb-4 rounded-lg">
            <div className="flex items-start gap-3">
              <SvgAlertTriangle className="h-5 w-5 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="font-medium">The language model is not running</p>
                <p className="text-sm opacity-80 mt-1">{error}</p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-2"
                  onClick={handleRetry}
                >
                  <SvgRefreshCw className="mr-2 h-4 w-4" />
                  Retry
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Input Form */}
        <form onSubmit={handleSubmit} className="border-t p-4 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <div className="flex items-end gap-2">
            <div className="flex-1 relative">
              <Textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask a question about your documents... (Shift+Enter for new line)"
                rows={1}
                disabled={isLoading}
                className="pr-12"
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault()
                    handleSubmit(e as unknown as React.FormEvent)
                  }
                }}
              />
            </div>
            <Button
              type="submit"
              size="icon"
              disabled={!input.trim() || isLoading}
              className="h-10 w-10"
            >
              {isLoading ? (
                <SvgLoader2 className="h-5 w-5 animate-spin" />
              ) : (
                <SvgSend className="h-5 w-5" />
              )}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground text-center mt-2">
            Press Enter to send, Shift+Enter for new line
          </p>
        </form>
      </div>
    </div>
  )
}