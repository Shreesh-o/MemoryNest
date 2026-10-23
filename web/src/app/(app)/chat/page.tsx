"use client"

import { useState, useEffect, useRef, useCallback, Suspense } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  chatAsk,
  chatDocuments,
  conversationsList,
  conversationsGet,
  conversationsDelete,
  ConversationPublic,
} from "@/lib/api"
import { cn } from "@/lib/utils"
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu"
import { Check } from "lucide-react"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import {
  SvgPlus,
  SvgTrash2,
  SvgMessageSquare,
  SvgSend,
  SvgLoader2,
  SvgRefreshCw,
  SvgAlertTriangle,
  SvgAlertCircle,
  SvgFileText,
} from "@/components/ui/icons"
import { toast } from "sonner"
import Markdown from "react-markdown"

type Message = {
  id: number
  role: "user" | "assistant"
  content: string
  sources?: { document: string; chunk_index: number; similarity: number; document_id?: number }[]
  scope?: { scope: "all" | "selected"; document_ids?: number[] | null } | null
}

const SUGGESTED_QUESTIONS = [
  "What documents do I have about meetings?",
  "Summarize my latest uploaded document",
  "Find all events scheduled for next month",
]

let messageIdCounter = 0
function getNextMessageId(): number {
  messageIdCounter += 1
  return messageIdCounter
}

function formatRelativeTime(isoString: string | null | undefined): string {
  if (!isoString) return ""
  const normalized = isoString.includes("T") ? isoString : isoString.replace(" ", "T") + "Z"
  const date = new Date(normalized)
  if (isNaN(date.getTime())) return ""
  const now = new Date()
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000)
  if (diffInSeconds < 0 || diffInSeconds < 60) return "just now"
  const diffInMinutes = Math.floor(diffInSeconds / 60)
  if (diffInMinutes < 60) return `${diffInMinutes}m ago`
  const diffInHours = Math.floor(diffInMinutes / 60)
  if (diffInHours < 24) return `${diffInHours}h ago`
  const diffInDays = Math.floor(diffInHours / 24)
  if (diffInDays < 30) return `${diffInDays}d ago`
  const diffInMonths = Math.floor(diffInDays / 30)
  if (diffInMonths < 12) return `${diffInMonths}mo ago`
  const diffInYears = Math.floor(diffInDays / 365)
  return `${diffInYears}y ago`
}

function ConversationList({
  conversations,
  activeId,
  onSelect,
  onDelete,
  onNewChat,
}: {
  conversations: ConversationPublic[]
  activeId: number | null
  onSelect: (id: number) => void
  onDelete: (convo: ConversationPublic) => void
  onNewChat: () => void
}) {
  return (
    <div className="flex-1 flex flex-col min-h-0">
      <div className="p-3 border-b shrink-0">
        <Button onClick={onNewChat} className="w-full justify-start gap-2" variant="outline">
          <SvgPlus className="h-4 w-4" />
          <span>New chat</span>
        </Button>
      </div>
      <div className="flex-1 overflow-y-auto min-h-0 p-2 space-y-1">
        {conversations.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground px-4">
            <SvgMessageSquare className="mx-auto h-8 w-8 mb-2 opacity-40" />
            <p className="text-sm font-medium">No conversations yet</p>
            <p className="text-xs text-muted-foreground mt-1">Start a new chat to begin</p>
          </div>
        ) : (
          conversations.map((convo) => {
            const isActive = activeId === convo.id
            return (
              <div
                key={convo.id}
                className={cn(
                  "group flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer text-left transition-colors relative",
                  isActive
                    ? "bg-accent text-accent-foreground font-medium"
                    : "hover:bg-muted text-muted-foreground hover:text-foreground"
                )}
                onClick={() => onSelect(convo.id)}
              >
                <SvgMessageSquare className="h-4 w-4 shrink-0 opacity-70" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm truncate leading-snug">
                    {convo.title || "Untitled"}
                  </p>
                  <p className="text-xs text-muted-foreground truncate opacity-70 mt-0.5">
                    {formatRelativeTime(convo.updated_at || convo.created_at)}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="Delete conversation"
                  className="h-7 w-7 shrink-0 text-muted-foreground hover:text-destructive opacity-100 md:opacity-0 md:group-hover:opacity-100 focus-visible:opacity-100 transition-opacity"
                  onClick={(e) => {
                    e.stopPropagation()
                    onDelete(convo)
                  }}
                >
                  <SvgTrash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

function ChatContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const queryClient = useQueryClient()

  const cParam = searchParams.get("c")
  const conversationId = cParam ? parseInt(cParam, 10) : null
  const isValidId = conversationId !== null && !isNaN(conversationId) && conversationId > 0

  // Adjust state when cParam changes during render
  const [prevCParam, setPrevCParam] = useState<string | null>(cParam)
  const [messages, setMessages] = useState<Message[]>([])
  const [error, setError] = useState<string | null>(null)
  const [justCreatedId, setJustCreatedId] = useState<number | null>(null)

  if (prevCParam !== cParam) {
    setPrevCParam(cParam)
    if (justCreatedId !== conversationId) {
      setMessages([])
      setError(null)
    }
  }

  const [input, setInput] = useState("")
  const [isLoadingChat, setIsLoadingChat] = useState(false)
  const [sheetOpen, setSheetOpen] = useState(false)
  const [conversationToDelete, setConversationToDelete] = useState<ConversationPublic | null>(null)
  const [selectedDocIds, setSelectedDocIds] = useState<number[]>([])

  const { data: readyDocuments = [] } = useQuery({
    queryKey: ["chat-documents"],
    queryFn: async () => {
      const res = await chatDocuments()
      if (!res.ok) return []
      return res.data
    },
  })

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const lastUserQuestionRef = useRef<string>("")

  // Fetch conversations list with React Query
  const { data: conversations = [] } = useQuery({
    queryKey: ["conversations"],
    queryFn: async () => {
      const res = await conversationsList()
      if (!res.ok) {
        throw new Error(res.error?.detail || "Failed to load conversations")
      }
      return res.data
    },
  })

  // Fetch current conversation if ID is valid
  const {
    data: fetchedConversation,
    isError: isConversationError,
  } = useQuery({
    queryKey: ["conversation", conversationId],
    queryFn: async () => {
      if (!conversationId) return null
      const res = await conversationsGet(conversationId)
      if (!res.ok) {
        throw new Error("Conversation not found")
      }
      return res.data
    },
    enabled: isValidId,
    retry: false,
  })

  const activeConversation = isValidId && fetchedConversation ? fetchedConversation : null
  const notFound = Boolean(cParam && (!isValidId || isConversationError))

  // Sort newest first
  const sortedConversations = [...conversations].sort((a, b) => {
    const timeA = new Date(a.updated_at || a.created_at || 0).getTime()
    const timeB = new Date(b.updated_at || b.created_at || 0).getTime()
    return timeB - timeA
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      const res = await conversationsDelete(id)
      if (!res.ok) {
        throw new Error(res.error?.detail || "Failed to delete conversation")
      }
      return id
    },
    onSuccess: (deletedId) => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] })
      toast.success("Conversation deleted")
      setConversationToDelete(null)
      if (conversationId === deletedId) {
        router.push("/chat")
        setMessages([])
        setError(null)
      }
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Failed to delete conversation"
      toast.error(msg)
    },
  })

  // Auto-grow textarea up to 6 rows (~150px)
  const adjustTextareaHeight = useCallback(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
      const nextHeight = Math.min(textareaRef.current.scrollHeight, 150)
      textareaRef.current.style.height = `${Math.max(nextHeight, 42)}px`
    }
  }, [])

  useEffect(() => {
    adjustTextareaHeight()
  }, [input, adjustTextareaHeight])

  // Scroll to bottom when messages or loading state changes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, isLoadingChat])

  const handleNewChat = () => {
    setMessages([])
    setError(null)
    setInput("")
    router.push("/chat")
  }

  const handleSelectConversation = (id: number) => {
    if (conversationId === id) return
    router.push(`/chat?c=${id}`)
  }

  const handleSend = async (questionText: string) => {
    const question = questionText.trim()
    if (!question || isLoadingChat || notFound) return

    setInput("")
    setIsLoadingChat(true)
    setError(null)
    lastUserQuestionRef.current = question

    const userMessage: Message = {
      id: getNextMessageId(),
      role: "user",
      content: question,
    }
    setMessages((prev) => [...prev, userMessage])

    try {
      const result = await chatAsk({
        question,
        conversation_id: conversationId,
        document_ids: selectedDocIds.length > 0 ? selectedDocIds : null,
      })

      if (result.ok) {
        const { conversation_id: newConvoId, answer, sources, scope } = result.data
        const assistantMessage: Message = {
          id: getNextMessageId(),
          role: "assistant",
          content: answer,
          sources,
          scope,
        }
        setMessages((prev) => [...prev, assistantMessage])

        // Refresh conversation list immediately
        await queryClient.invalidateQueries({ queryKey: ["conversations"] })

        // Update active conversation & keep URL in sync if this was a new chat
        if (conversationId !== newConvoId) {
          setJustCreatedId(newConvoId)
          await queryClient.invalidateQueries({ queryKey: ["conversation", newConvoId] })
          router.replace(`/chat?c=${newConvoId}`)
        }
      } else if (result.error?.status === 503) {
        setError(result.error.detail || "The language model is not running. Start Ollama and retry.")
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
      setMessages((prev) => prev.slice(0, -1))
    } finally {
      setIsLoadingChat(false)
    }
  }

  const handleRetry = () => {
    if (lastUserQuestionRef.current) {
      handleSend(lastUserQuestionRef.current)
    }
  }

  return (
    <div className="-m-4 md:-m-6 h-[calc(100dvh-4rem)] flex overflow-hidden min-h-0 bg-background">
      {/* Desktop left column (w-72, border-r) */}
      <aside className="hidden md:flex flex-col w-72 shrink-0 border-r bg-card min-h-0">
        <div className="p-3 border-b shrink-0 flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Conversations
          </span>
          <span className="text-xs text-muted-foreground font-mono">
            {sortedConversations.length}
          </span>
        </div>
        <ConversationList
          conversations={sortedConversations}
          activeId={conversationId}
          onSelect={handleSelectConversation}
          onDelete={(convo) => setConversationToDelete(convo)}
          onNewChat={handleNewChat}
        />
      </aside>

      {/* Mobile drawer Sheet */}
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent side="left" className="w-80 p-0 flex flex-col min-h-0">
          <SheetHeader className="p-4 border-b">
            <SheetTitle>Conversations</SheetTitle>
          </SheetHeader>
          <ConversationList
            conversations={sortedConversations}
            activeId={conversationId}
            onSelect={(id) => {
              handleSelectConversation(id)
              setSheetOpen(false)
            }}
            onDelete={(convo) => setConversationToDelete(convo)}
            onNewChat={() => {
              handleNewChat()
              setSheetOpen(false)
            }}
          />
        </SheetContent>
      </Sheet>

      {/* Right column */}
      <div className="flex-1 flex flex-col min-w-0 min-h-0 bg-background">
        {/* Header */}
        <div className="border-b bg-background px-4 py-3 shrink-0 flex items-center justify-between">
          <div className="flex items-center gap-2 min-w-0">
            <Button
              variant="outline"
              size="icon"
              className="md:hidden shrink-0"
              onClick={() => setSheetOpen(true)}
              aria-label="Open conversation list"
            >
              <SvgMessageSquare className="h-4 w-4" />
            </Button>
            <div className="min-w-0">
              <h1 className="text-base font-semibold truncate">
                {notFound
                  ? "Conversation not found"
                  : activeConversation
                  ? activeConversation.title || "Chat"
                  : "New Chat"}
              </h1>
              <p className="text-xs text-muted-foreground truncate">
                {notFound
                  ? "This conversation could not be found"
                  : activeConversation
                  ? formatRelativeTime(activeConversation.updated_at || activeConversation.created_at)
                  : "Start a new conversation"}
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleNewChat}
            className="gap-1.5 shrink-0"
          >
            <SvgPlus className="h-4 w-4" />
            <span className="hidden sm:inline">New chat</span>
          </Button>
        </div>

        {/* Message area */}
        <div className="flex-1 overflow-y-auto min-h-0 p-4 md:p-6">
          <div className="max-w-3xl mx-auto w-full space-y-4">
            {notFound ? (
              <div className="flex items-center justify-center min-h-[300px]">
                <Card className="max-w-md w-full text-center">
                  <CardHeader>
                    <div className="mx-auto w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-2">
                      <SvgAlertCircle className="h-6 w-6 text-muted-foreground" />
                    </div>
                    <CardTitle className="text-lg">Conversation not found</CardTitle>
                    <CardDescription>
                      This conversation does not exist or you do not have permission to view it.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <Button onClick={handleNewChat} className="w-full gap-2">
                      <SvgPlus className="h-4 w-4" />
                      New chat
                    </Button>
                  </CardContent>
                </Card>
              </div>
            ) : messages.length === 0 && !isLoadingChat && !error ? (
              <div className="flex flex-col items-center justify-center min-h-[320px] text-center max-w-md mx-auto py-8">
                <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-4">
                  <SvgMessageSquare className="h-6 w-6 text-muted-foreground" />
                </div>
                <h2 className="text-lg font-semibold mb-2">Start a conversation</h2>
                <p className="text-sm text-muted-foreground mb-6">
                  Ask questions about your documents. I&apos;ll search through your uploaded files
                  and provide answers with citations.
                </p>
                <div className="space-y-2 w-full">
                  {SUGGESTED_QUESTIONS.map((q, i) => (
                    <Button
                      key={i}
                      variant="outline"
                      className="w-full justify-start text-left h-auto py-2.5 px-3.5 text-sm font-normal"
                      onClick={() => handleSend(q)}
                    >
                      {q}
                    </Button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={cn(
                      "flex gap-3",
                      msg.role === "user" ? "flex-row-reverse" : "flex-row"
                    )}
                  >
                    <div
                      className={cn(
                        "flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium",
                        msg.role === "user"
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted text-muted-foreground"
                      )}
                    >
                      {msg.role === "user" ? "You" : "AI"}
                    </div>
                    <div
                      className={cn(
                        "rounded-lg p-3.5",
                        msg.role === "user"
                          ? "bg-primary text-primary-foreground max-w-[85%] ml-auto"
                          : "bg-muted/50 border border-border/50 max-w-[90%]"
                      )}
                    >
                      <div
                        className={cn(
                          "prose prose-sm max-w-none break-words",
                          msg.role === "user"
                            ? "text-primary-foreground prose-invert"
                            : "text-foreground dark:prose-invert"
                        )}
                      >
                        <Markdown>{msg.content}</Markdown>
                      </div>
                      {msg.scope && (
                        <div className="mt-2 text-xs text-muted-foreground">
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-background border border-border/60 text-[11px] font-medium">
                            {msg.scope.scope === "selected"
                              ? `Scoped to ${msg.scope.document_ids?.length || 0} document${(msg.scope.document_ids?.length || 0) === 1 ? "" : "s"}`
                              : "All documents"}
                          </span>
                        </div>
                      )}
                      {msg.sources && msg.sources.length > 0 && (
                        <details className="mt-2.5 group text-xs border-t border-border/50 pt-2">
                          <summary className="flex items-center gap-1.5 text-muted-foreground cursor-pointer font-medium hover:text-foreground">
                            <SvgFileText className="h-3.5 w-3.5" />
                            <span>Sources ({msg.sources.length})</span>
                            <svg
                              className="ml-auto h-3.5 w-3.5 transition-transform group-open:rotate-90"
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M9 5l7 7-7 7"
                              />
                            </svg>
                          </summary>
                          <div className="mt-2 space-y-1.5 pl-4 border-l-2 border-muted">
                            {msg.sources.map((source, idx) => (
                              <div key={idx} className="text-muted-foreground">
                                <span className="font-medium text-foreground">
                                  {source.document}
                                </span>
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

                {/* Thinking... state */}
                {isLoadingChat && (
                  <div className="flex gap-3">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-muted flex items-center justify-center text-xs font-medium text-muted-foreground">
                      AI
                    </div>
                    <div className="flex-1 bg-muted/40 border border-border/50 rounded-lg p-3.5 space-y-2 max-w-[85%]">
                      <div className="flex items-center gap-2 text-xs text-muted-foreground font-medium">
                        <SvgLoader2 className="h-3.5 w-3.5 animate-spin" />
                        <span>Thinking...</span>
                      </div>
                      <div className="h-3 bg-muted animate-pulse rounded w-3/4" />
                      <div className="h-3 bg-muted animate-pulse rounded w-1/2" />
                    </div>
                  </div>
                )}

                {/* Error card */}
                {error && (
                  <div className="border border-destructive bg-destructive/10 text-destructive p-4 rounded-lg">
                    <div className="flex items-start gap-3">
                      <SvgAlertTriangle className="h-5 w-5 flex-shrink-0 mt-0.5" />
                      <div className="flex-1">
                        <p className="font-medium">The language model is not running</p>
                        <p className="text-sm opacity-90 mt-1">{error}</p>
                        <Button
                          variant="outline"
                          size="sm"
                          className="mt-3 gap-1.5"
                          onClick={handleRetry}
                        >
                          <SvgRefreshCw className="h-3.5 w-3.5" />
                          Retry
                        </Button>
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </>
            )}
          </div>
        </div>

        {/* Bottom pinned input bar */}
        <div className="border-t p-3 md:p-4 bg-background shrink-0">
          <div className="max-w-3xl mx-auto w-full">
            <form
              onSubmit={(e) => {
                e.preventDefault()
                if (input.trim() && !isLoadingChat && !notFound) {
                  handleSend(input)
                }
              }}
            >
              {readyDocuments.length > 0 && (
                <div className="flex items-center gap-2 mb-2 text-xs">
                  <span className="text-muted-foreground font-medium">Search scope:</span>
                  <DropdownMenu>
                    <DropdownMenuTrigger
                      render={
                        <Button
                          variant="outline"
                          size="xs"
                          type="button"
                          className="h-6 gap-1.5 text-xs font-normal"
                        >
                          <span>
                            {selectedDocIds.length === 0
                              ? "All documents (default)"
                              : `${selectedDocIds.length} document${selectedDocIds.length > 1 ? "s" : ""} selected`}
                          </span>
                        </Button>
                      }
                    />
                    <DropdownMenuContent align="start" className="w-64 max-h-60 overflow-y-auto p-1">
                      <DropdownMenuItem
                        onClick={() => setSelectedDocIds([])}
                        className="flex items-center justify-between text-xs cursor-pointer"
                      >
                        <span>All documents (default)</span>
                        {selectedDocIds.length === 0 && <Check className="h-3.5 w-3.5 text-primary" />}
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      {readyDocuments.map((doc) => {
                        const isSelected = selectedDocIds.includes(doc.id)
                        return (
                          <DropdownMenuItem
                            key={doc.id}
                            onClick={() => {
                              setSelectedDocIds((prev) =>
                                prev.includes(doc.id)
                                  ? prev.filter((id) => id !== doc.id)
                                  : [...prev, doc.id]
                              )
                            }}
                            className="flex items-center justify-between text-xs cursor-pointer"
                          >
                            <span className="truncate max-w-[190px]">{doc.filename}</span>
                            {isSelected && <Check className="h-3.5 w-3.5 text-primary shrink-0" />}
                          </DropdownMenuItem>
                        )
                      })}
                    </DropdownMenuContent>
                  </DropdownMenu>
                  {selectedDocIds.length > 0 && (
                    <Button
                      variant="ghost"
                      size="xs"
                      type="button"
                      className="h-6 px-1.5 text-xs text-muted-foreground hover:text-foreground"
                      onClick={() => setSelectedDocIds([])}
                    >
                      Reset
                    </Button>
                  )}
                </div>
              )}
              <div className="flex items-end gap-2">
                <div className="flex-1 relative">
                  <Textarea
                    ref={textareaRef}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder={
                      notFound
                        ? "Start a new chat to begin..."
                        : "Ask a question about your documents... (Shift+Enter for new line)"
                    }
                    rows={1}
                    disabled={isLoadingChat || notFound}
                    style={{ minHeight: "42px" }}
                    className="min-h-[42px] max-h-[150px] resize-none py-2.5 pr-4 text-sm leading-relaxed overflow-y-auto"
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault()
                        if (input.trim() && !isLoadingChat && !notFound) {
                          handleSend(input)
                        }
                      }
                    }}
                  />
                </div>
                <Button
                  type="submit"
                  size="icon"
                  disabled={!input.trim() || isLoadingChat || notFound}
                  className="h-10 w-10 shrink-0"
                  aria-label="Send message"
                >
                  {isLoadingChat ? (
                    <SvgLoader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <SvgSend className="h-4 w-4" />
                  )}
                </Button>
              </div>
              <p className="text-xs text-muted-foreground text-center mt-2">
                Press Enter to send, Shift+Enter for new line
              </p>
            </form>
          </div>
        </div>
      </div>

      {/* Confirmation Dialog for Delete */}
      <Dialog
        open={!!conversationToDelete}
        onOpenChange={(open) => {
          if (!open && !deleteMutation.isPending) {
            setConversationToDelete(null)
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete this conversation?</DialogTitle>
            <DialogDescription>
              Delete this conversation? This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2 mt-4">
            <Button
              variant="outline"
              onClick={() => setConversationToDelete(null)}
              disabled={deleteMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                if (conversationToDelete) {
                  deleteMutation.mutate(conversationToDelete.id)
                }
              }}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default function ChatPage() {
  useEffect(() => {
    document.title = "Chat — MemoryNest"
  }, [])

  return (
    <Suspense
      fallback={
        <div className="-m-4 md:-m-6 h-[calc(100dvh-4rem)] flex items-center justify-center">
          <SvgLoader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      }
    >
      <ChatContent />
    </Suspense>
  )
}
