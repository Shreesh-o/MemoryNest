"use client"

import { useState, useEffect, useRef, useCallback, useMemo, Suspense } from "react"
import Link from "next/link"
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
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Skeleton } from "@/components/ui/skeleton"
import { Badge } from "@/components/ui/badge"
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "@/components/ui/popover"
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
  CheckIcon,
  SearchIcon,
  XIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  LayersIcon,
  PlusIcon,
  Trash2Icon,
  MessageSquareIcon,
  SendIcon,
  Loader2Icon,
  RefreshCwIcon,
  AlertTriangleIcon,
  AlertCircleIcon,
  FileTextIcon,
  BotIcon,
  UserIcon,
  SparklesIcon,
} from "lucide-react"
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
      <div className="p-3 border-b border-border/80 shrink-0">
        <Button onClick={onNewChat} className="w-full justify-start gap-2 h-9 text-xs font-semibold cursor-pointer" variant="outline">
          <PlusIcon className="size-4" />
          <span>New Chat</span>
        </Button>
      </div>
      <div className="flex-1 overflow-y-auto min-h-0 p-2 space-y-1">
        {conversations.length === 0 ? (
          <div className="text-center py-10 text-muted-foreground px-4">
            <MessageSquareIcon className="mx-auto size-8 mb-2 opacity-30" />
            <p className="text-xs font-medium text-foreground">No conversations yet</p>
            <p className="text-[11px] text-muted-foreground mt-0.5">Start a chat to ask questions</p>
          </div>
        ) : (
          conversations.map((convo) => {
            const isActive = activeId === convo.id
            return (
              <div
                key={convo.id}
                className={cn(
                  "group flex items-center gap-2.5 px-3 py-2.5 rounded-lg cursor-pointer text-left transition-all relative border border-transparent",
                  isActive
                    ? "bg-accent text-accent-foreground font-medium border-border/60 shadow-2xs"
                    : "hover:bg-muted/60 text-muted-foreground hover:text-foreground"
                )}
                onClick={() => onSelect(convo.id)}
              >
                <MessageSquareIcon className="size-3.5 shrink-0 opacity-70" />
                <div className="flex-1 min-w-0">
                  <p className="text-xs truncate font-medium leading-snug">
                    {convo.title || "Untitled Conversation"}
                  </p>
                  <p className="text-[10px] text-muted-foreground truncate opacity-70 mt-0.5">
                    {formatRelativeTime(convo.updated_at || convo.created_at)}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="icon-xs"
                  aria-label="Delete conversation"
                  className="size-6 shrink-0 text-muted-foreground hover:text-destructive opacity-100 md:opacity-0 md:group-hover:opacity-100 focus-visible:opacity-100 transition-opacity cursor-pointer"
                  onClick={(e) => {
                    e.stopPropagation()
                    onDelete(convo)
                  }}
                >
                  <Trash2Icon className="size-3" />
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

  const STORAGE_KEY = "memorynest_chat_selected_doc_ids"

  const docParam = searchParams.get("doc")
  const [prevDocParam, setPrevDocParam] = useState<string | null>(docParam)
  const [input, setInput] = useState("")
  const [isLoadingChat, setIsLoadingChat] = useState(false)
  const [sheetOpen, setSheetOpen] = useState(false)
  const [conversationToDelete, setConversationToDelete] = useState<ConversationPublic | null>(null)
  const [popoverOpen, setPopoverOpen] = useState(false)
  const [docSearchQuery, setDocSearchQuery] = useState("")

  const [selectedDocIds, setSelectedDocIds] = useState<number[]>(() => {
    if (typeof window === "undefined") return []
    if (docParam) {
      const p = parseInt(docParam, 10)
      if (!isNaN(p) && p > 0) return [p]
    }
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) {
        const parsed = JSON.parse(saved)
        if (Array.isArray(parsed)) {
          return parsed.filter((id): id is number => typeof id === "number" && id > 0)
        }
      }
    } catch {}
    return []
  })

  if (prevDocParam !== docParam) {
    setPrevDocParam(docParam)
    if (docParam) {
      const p = parseInt(docParam, 10)
      if (!isNaN(p) && p > 0) {
        setSelectedDocIds([p])
      }
    }
  }

  const updateSelectedDocIds = useCallback((nextIds: number[]) => {
    setSelectedDocIds(nextIds)
    try {
      if (nextIds.length > 0) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(nextIds))
      } else {
        localStorage.removeItem(STORAGE_KEY)
      }
    } catch {}
  }, [])

  const {
    data: readyDocuments = [],
    isLoading: isLoadingDocs,
  } = useQuery({
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

  const conversationMessages: Message[] = useMemo(() => {
    if (messages.length > 0) return messages
    if (activeConversation?.messages && activeConversation.id === conversationId) {
      return activeConversation.messages.map((m, idx) => ({
        id: idx + 1,
        role: m.role as "user" | "assistant",
        content: m.content,
        sources: m.sources || undefined,
        scope: m.scope || undefined,
      }))
    }
    return []
  }, [messages, activeConversation, conversationId])

  const validSelectedDocIds = useMemo(() => {
    if (readyDocuments.length === 0) return selectedDocIds
    const validSet = new Set(readyDocuments.map((d) => d.id))
    return selectedDocIds.filter((id) => validSet.has(id))
  }, [selectedDocIds, readyDocuments])

  const triggerLabel = useMemo(() => {
    if (validSelectedDocIds.length === 0) return "All documents"
    if (validSelectedDocIds.length === 1) {
      const doc = readyDocuments.find((d) => d.id === validSelectedDocIds[0])
      return doc ? doc.filename : "1 document"
    }
    return `${validSelectedDocIds.length} documents`
  }, [validSelectedDocIds, readyDocuments])

  const filteredDocs = useMemo(() => {
    const q = docSearchQuery.trim().toLowerCase()
    if (!q) return readyDocuments
    return readyDocuments.filter((d) => d.filename.toLowerCase().includes(q))
  }, [readyDocuments, docSearchQuery])

  const sortedConversations = [...conversations].sort((a, b) => {
    const timeA = new Date(a.updated_at || a.created_at || 0).getTime()
    const timeB = new Date(b.updated_at || b.created_at || 0).getTime()
    return timeB - timeA
  })

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

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [conversationMessages, isLoadingChat])

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
    const currentList = conversationMessages
    setMessages([...currentList, userMessage])

    try {
      const result = await chatAsk({
        question,
        conversation_id: conversationId,
        document_ids: validSelectedDocIds.length > 0 ? validSelectedDocIds : undefined,
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
        setMessages([...currentList, userMessage, assistantMessage])

        await queryClient.invalidateQueries({ queryKey: ["conversations"] })

        if (conversationId !== newConvoId) {
          setJustCreatedId(newConvoId)
          await queryClient.invalidateQueries({ queryKey: ["conversation", newConvoId] })
          router.replace(`/chat?c=${newConvoId}`)
        }
      } else {
        const statusCode = result.error?.status
        if (statusCode === 404 || statusCode === 400) {
          toast.error("Selected documents are no longer available. Resetting search to all documents.")
          updateSelectedDocIds([])
          await queryClient.invalidateQueries({ queryKey: ["chat-documents"] })
          setMessages(currentList)
        } else if (statusCode === 503) {
          setError(result.error?.detail || "The language model is not running. Start Ollama and retry.")
          setMessages(currentList)
        } else {
          throw new Error(result.error?.detail || "Failed to get answer")
        }
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to get answer"
      if (message.includes("404") || message.includes("400")) {
        toast.error("Selected documents are no longer available. Resetting search to all documents.")
        updateSelectedDocIds([])
        queryClient.invalidateQueries({ queryKey: ["chat-documents"] })
      } else if (message.includes("503") || message.includes("Ollama") || message.includes("LLM")) {
        setError("The language model is not running. Start Ollama and retry.")
      } else {
        setError(message)
      }
      setMessages(currentList)
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
      {/* Desktop Left Conversations Column */}
      <aside className="hidden md:flex flex-col w-72 shrink-0 border-r border-border/80 bg-sidebar text-sidebar-foreground min-h-0">
        <div className="p-3.5 border-b border-sidebar-border shrink-0 flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            History
          </span>
          <Badge variant="outline" className="font-mono text-[10px] px-1.5 py-0">
            {sortedConversations.length}
          </Badge>
        </div>
        <ConversationList
          conversations={sortedConversations}
          activeId={conversationId}
          onSelect={handleSelectConversation}
          onDelete={(convo) => setConversationToDelete(convo)}
          onNewChat={handleNewChat}
        />
      </aside>

      {/* Mobile Drawer Sheet */}
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent side="left" className="w-80 p-0 flex flex-col min-h-0">
          <SheetHeader className="p-4 border-b border-border/80">
            <SheetTitle className="font-heading text-base font-semibold">Conversations</SheetTitle>
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

      {/* Right Column: Chat Window */}
      <div className="flex-1 flex flex-col min-w-0 min-h-0 bg-background">
        {/* Top Header */}
        <div className="border-b border-border/80 bg-background/90 backdrop-blur-xs px-4 py-2.5 shrink-0 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5 min-w-0">
            <Button
              variant="outline"
              size="icon-sm"
              className="md:hidden shrink-0 cursor-pointer"
              onClick={() => setSheetOpen(true)}
              aria-label="Open conversation list"
            >
              <MessageSquareIcon className="size-4" />
            </Button>
            <div className="min-w-0">
              <h2 className="text-sm font-semibold truncate text-foreground">
                {notFound
                  ? "Conversation not found"
                  : activeConversation
                  ? activeConversation.title || "Chat"
                  : "New Conversation"}
              </h2>
              <p className="text-[11px] text-muted-foreground truncate">
                {notFound
                  ? "This thread could not be found"
                  : activeConversation
                  ? formatRelativeTime(activeConversation.updated_at || activeConversation.created_at)
                  : "Grounding answers with local RAG citations"}
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleNewChat}
            className="text-xs h-7.5 gap-1.5 shrink-0 cursor-pointer"
          >
            <PlusIcon className="size-3.5" />
            <span className="hidden sm:inline">New Chat</span>
          </Button>
        </div>

        {/* Message Scroll Area */}
        <div className="flex-1 overflow-y-auto min-h-0 p-4 md:p-6">
          <div className="max-w-3xl mx-auto w-full space-y-5">
            {notFound ? (
              <div className="flex items-center justify-center min-h-[300px]">
                <Card className="max-w-md w-full text-center border-border">
                  <CardHeader>
                    <div className="mx-auto size-12 rounded-xl bg-muted/60 flex items-center justify-center mb-2">
                      <AlertCircleIcon className="size-6 text-muted-foreground" />
                    </div>
                    <CardTitle className="text-base font-semibold">Conversation not found</CardTitle>
                    <CardDescription className="text-xs">
                      This thread does not exist or may have been deleted.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <Button onClick={handleNewChat} size="sm" className="w-full gap-2 cursor-pointer">
                      <PlusIcon className="size-4" />
                      Start New Chat
                    </Button>
                  </CardContent>
                </Card>
              </div>
            ) : conversationMessages.length === 0 && !isLoadingChat && !error ? (
              <div className="flex flex-col items-center justify-center min-h-[340px] text-center max-w-lg mx-auto py-10">
                <div className="size-13 rounded-2xl bg-primary/10 text-primary flex items-center justify-center mb-4 ring-1 ring-primary/20">
                  <SparklesIcon className="size-6.5" />
                </div>
                <h2 className="font-heading text-lg font-bold text-foreground mb-1.5">
                  Ask Your Knowledge Vault
                </h2>
                <p className="text-xs text-muted-foreground mb-6 leading-relaxed max-w-md">
                  Query your uploaded files with semantic precision. Answers include verifiable document citations and chunk similarities.
                </p>
                <div className="space-y-2 w-full">
                  {SUGGESTED_QUESTIONS.map((q, i) => (
                    <Button
                      key={i}
                      variant="outline"
                      className="w-full justify-between text-left h-auto py-2.5 px-3.5 text-xs font-normal border-border/80 hover:border-border hover:bg-muted/40 transition-all cursor-pointer group"
                      onClick={() => handleSend(q)}
                    >
                      <span className="truncate">{q}</span>
                      <ChevronRightIcon className="size-3.5 text-muted-foreground opacity-60 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all shrink-0 ml-2" />
                    </Button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {conversationMessages.map((msg) => (
                  <div
                    key={msg.id}
                    className={cn(
                      "flex gap-3",
                      msg.role === "user" ? "flex-row-reverse" : "flex-row"
                    )}
                  >
                    <div
                      className={cn(
                        "size-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5 shadow-2xs",
                        msg.role === "user"
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted text-muted-foreground ring-1 ring-border/50"
                      )}
                    >
                      {msg.role === "user" ? <UserIcon className="size-3.5" /> : <BotIcon className="size-3.5" />}
                    </div>

                    <div
                      className={cn(
                        "rounded-xl px-4 py-3 text-sm leading-relaxed transition-all",
                        msg.role === "user"
                          ? "bg-primary text-primary-foreground max-w-[85%] ml-auto shadow-xs"
                          : "bg-card border border-border/80 text-card-foreground max-w-[90%] shadow-xs"
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

                      {msg.role === "assistant" && msg.scope && (
                        <p className="mt-2.5 text-[11px] text-muted-foreground font-medium pt-2 border-t border-border/40">
                          {(() => {
                            if (
                              msg.scope.scope === "all" ||
                              !msg.scope.document_ids ||
                              msg.scope.document_ids.length === 0
                            ) {
                              return "Scope: All documents searched"
                            }
                            const names = msg.scope.document_ids.map((id) => {
                              const found = readyDocuments.find((d) => d.id === id)
                              if (found) return found.filename
                              const srcFound = msg.sources?.find((s) => s.document_id === id)
                              if (srcFound) return srcFound.document
                              return `Doc #${id}`
                            })
                            return `Scope: ${names.join(", ")}`
                          })()}
                        </p>
                      )}

                      {msg.sources && msg.sources.length > 0 && (
                        <details className="mt-2.5 group text-xs border-t border-border/50 pt-2">
                          <summary className="flex items-center gap-1.5 text-muted-foreground cursor-pointer font-medium hover:text-foreground select-none">
                            <FileTextIcon className="size-3.5 text-primary" />
                            <span>Citations ({msg.sources.length})</span>
                            <ChevronRightIcon className="ml-auto size-3.5 transition-transform group-open:rotate-90" />
                          </summary>
                          <div className="mt-2 space-y-1.5 pl-3 border-l-2 border-primary/40">
                            {msg.sources.map((source, idx) => (
                              <div key={idx} className="text-muted-foreground text-[11px] leading-snug">
                                <span className="font-semibold text-foreground">
                                  {source.document}
                                </span>
                                {source.chunk_index !== undefined && (
                                  <span className="font-mono text-muted-foreground"> · chunk #{source.chunk_index}</span>
                                )}
                                {source.similarity !== undefined && (
                                  <span className="font-mono text-muted-foreground"> · similarity {source.similarity.toFixed(3)}</span>
                                )}
                              </div>
                            ))}
                          </div>
                        </details>
                      )}
                    </div>
                  </div>
                ))}

                {/* Thinking / Streaming Indicator */}
                {isLoadingChat && (
                  <div className="flex gap-3">
                    <div className="size-7 rounded-lg bg-muted flex items-center justify-center shrink-0 mt-0.5 ring-1 ring-border/50 text-muted-foreground">
                      <BotIcon className="size-3.5" />
                    </div>
                    <div className="flex-1 bg-card border border-border/80 rounded-xl p-4 space-y-2.5 max-w-[85%] shadow-xs">
                      <div className="flex items-center gap-2 text-xs text-primary font-medium">
                        <Loader2Icon className="size-3.5 animate-spin" />
                        <span>Searching documents and generating response...</span>
                      </div>
                      <div className="h-2.5 bg-muted animate-pulse rounded-full w-3/4" />
                      <div className="h-2.5 bg-muted animate-pulse rounded-full w-1/2" />
                    </div>
                  </div>
                )}

                {/* Error Banner */}
                {error && (
                  <div className="border border-destructive/40 bg-destructive/10 text-destructive p-4 rounded-xl shadow-xs">
                    <div className="flex items-start gap-3">
                      <AlertTriangleIcon className="size-5 shrink-0 mt-0.5" />
                      <div className="flex-1">
                        <p className="font-semibold text-sm">Language model error</p>
                        <p className="text-xs opacity-90 mt-1 leading-relaxed">{error}</p>
                        <Button
                          variant="outline"
                          size="sm"
                          className="mt-3 text-xs h-7.5 gap-1.5 border-destructive/30 hover:bg-destructive/10 cursor-pointer"
                          onClick={handleRetry}
                        >
                          <RefreshCwIcon className="size-3.5" />
                          Retry Query
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

        {/* Pinned Bottom Input Bar */}
        <div className="border-t border-border/80 p-3 md:p-4 bg-background shrink-0">
          <div className="max-w-3xl mx-auto w-full">
            <form
              onSubmit={(e) => {
                e.preventDefault()
                if (input.trim() && !isLoadingChat && !notFound) {
                  handleSend(input)
                }
              }}
            >
              {/* Scope Selector */}
              {isLoadingDocs ? (
                <div className="flex items-center gap-2 mb-2">
                  <Skeleton className="h-6 w-32 rounded-md" />
                </div>
              ) : readyDocuments.length === 0 ? (
                <div className="flex items-center gap-2 mb-2 text-xs text-muted-foreground">
                  <Button
                    variant="outline"
                    size="xs"
                    type="button"
                    disabled
                    className="h-6.5 gap-1.5 text-xs font-normal opacity-60 cursor-not-allowed"
                  >
                    <LayersIcon className="size-3" />
                    <span>All documents</span>
                  </Button>
                  <span>
                    No documents uploaded.{" "}
                    <Link
                      href="/upload"
                      className="text-primary hover:underline font-medium"
                    >
                      Upload files
                    </Link>
                  </span>
                </div>
              ) : (
                <div className="flex items-center gap-2 mb-2 text-xs">
                  <Popover open={popoverOpen} onOpenChange={setPopoverOpen}>
                    <PopoverTrigger
                      render={
                        <Button
                          variant="outline"
                          size="xs"
                          type="button"
                          className={cn(
                            "h-6.5 gap-1.5 text-xs font-normal max-w-[260px] border-border/80 transition-colors cursor-pointer",
                            validSelectedDocIds.length > 0 &&
                              "border-primary/60 bg-primary/10 text-foreground font-medium"
                          )}
                          title={triggerLabel}
                        >
                          <LayersIcon className="size-3 text-muted-foreground shrink-0" />
                          <span className="truncate">{triggerLabel}</span>
                          <ChevronDownIcon className="size-3 opacity-60 shrink-0 ml-0.5" />
                        </Button>
                      }
                    />
                    <PopoverContent
                      align="start"
                      side="top"
                      sideOffset={6}
                      className="w-80 p-0 shadow-lg border border-border bg-popover text-popover-foreground rounded-xl overflow-hidden"
                    >
                      <div className="p-2 border-b border-border/60 flex items-center gap-1.5 bg-muted/20">
                        <SearchIcon className="size-3.5 text-muted-foreground shrink-0 ml-1" />
                        <Input
                          value={docSearchQuery}
                          onChange={(e) => setDocSearchQuery(e.target.value)}
                          placeholder="Search documents..."
                          className="h-7 text-xs border-none shadow-none focus-visible:ring-0 px-1 bg-transparent"
                        />
                        {docSearchQuery && (
                          <Button
                            variant="ghost"
                            size="icon-xs"
                            className="size-5 text-muted-foreground hover:text-foreground shrink-0 cursor-pointer"
                            onClick={() => setDocSearchQuery("")}
                            type="button"
                            aria-label="Clear search"
                          >
                            <XIcon className="size-3" />
                          </Button>
                        )}
                      </div>

                      {/* All documents option */}
                      <div
                        role="checkbox"
                        aria-checked={validSelectedDocIds.length === 0}
                        tabIndex={0}
                        onClick={() => updateSelectedDocIds([])}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault()
                            updateSelectedDocIds([])
                          }
                        }}
                        className="flex items-center gap-2.5 px-3 py-2 text-xs hover:bg-muted/70 cursor-pointer border-b border-border/40 select-none transition-colors"
                      >
                        <div
                          className={cn(
                            "size-4 rounded border flex items-center justify-center shrink-0 transition-colors",
                            validSelectedDocIds.length === 0
                              ? "bg-primary border-primary text-primary-foreground"
                              : "border-muted-foreground/40 bg-background"
                          )}
                        >
                          {validSelectedDocIds.length === 0 && <CheckIcon className="size-3 stroke-[3]" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <span className="font-medium text-foreground">All documents</span>
                        </div>
                        <span className="text-[10px] text-muted-foreground font-mono shrink-0">Entire library</span>
                      </div>

                      {/* Documents list */}
                      <div className="max-h-56 overflow-y-auto p-1 space-y-0.5">
                        {filteredDocs.length === 0 ? (
                          <div className="py-6 text-center text-xs text-muted-foreground">
                            No matching documents
                          </div>
                        ) : (
                          filteredDocs.map((doc) => {
                            const isSelected = validSelectedDocIds.includes(doc.id)
                            return (
                              <div
                                key={doc.id}
                                role="checkbox"
                                aria-checked={isSelected}
                                tabIndex={0}
                                onClick={() => {
                                  const next = isSelected
                                    ? validSelectedDocIds.filter((id) => id !== doc.id)
                                    : [...validSelectedDocIds, doc.id]
                                  updateSelectedDocIds(next)
                                }}
                                onKeyDown={(e) => {
                                  if (e.key === "Enter" || e.key === " ") {
                                    e.preventDefault()
                                    const next = isSelected
                                      ? validSelectedDocIds.filter((id) => id !== doc.id)
                                      : [...validSelectedDocIds, doc.id]
                                    updateSelectedDocIds(next)
                                  }
                                }}
                                className={cn(
                                  "flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-xs hover:bg-muted/70 cursor-pointer select-none transition-colors",
                                  isSelected && "bg-muted/50 font-medium"
                                )}
                              >
                                <div
                                  className={cn(
                                    "size-4 rounded border flex items-center justify-center shrink-0 transition-colors",
                                    isSelected
                                      ? "bg-primary border-primary text-primary-foreground"
                                      : "border-muted-foreground/40 bg-background"
                                  )}
                                >
                                  {isSelected && <CheckIcon className="size-3 stroke-[3]" />}
                                </div>
                                <span className="truncate flex-1 text-foreground" title={doc.filename}>
                                  {doc.filename}
                                </span>
                                <span className="px-1.5 py-0.5 rounded text-[10px] font-mono uppercase bg-muted text-muted-foreground border border-border/40 shrink-0">
                                  {doc.file_type}
                                </span>
                              </div>
                            )
                          })
                        )}
                      </div>

                      {/* Footer */}
                      <div className="p-2 border-t border-border/60 bg-muted/20 flex items-center justify-between text-[11px] text-muted-foreground">
                        <span>
                          {validSelectedDocIds.length > 0
                            ? `${validSelectedDocIds.length} of ${readyDocuments.length} selected`
                            : `All ${readyDocuments.length} documents`}
                        </span>
                        {validSelectedDocIds.length > 0 && (
                          <button
                            type="button"
                            onClick={() => updateSelectedDocIds([])}
                            className="text-primary hover:underline font-medium cursor-pointer"
                          >
                            Reset to all
                          </button>
                        )}
                      </div>
                    </PopoverContent>
                  </Popover>

                  {validSelectedDocIds.length > 0 && (
                    <Button
                      variant="ghost"
                      size="xs"
                      type="button"
                      className="h-6.5 px-2 text-xs text-muted-foreground hover:text-foreground cursor-pointer"
                      onClick={() => updateSelectedDocIds([])}
                    >
                      Clear
                    </Button>
                  )}
                </div>
              )}

              {/* Chat Input Field & Send Button */}
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
                    className="min-h-[42px] max-h-[150px] resize-none py-2.5 pr-4 text-sm leading-relaxed overflow-y-auto rounded-xl"
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
                  className="size-10 shrink-0 rounded-xl cursor-pointer shadow-xs"
                  aria-label="Send message"
                >
                  {isLoadingChat ? (
                    <Loader2Icon className="size-4 animate-spin" />
                  ) : (
                    <SendIcon className="size-4" />
                  )}
                </Button>
              </div>
              <p className="text-[11px] text-muted-foreground text-center mt-2">
                Press Enter to send, Shift+Enter for new line
              </p>
            </form>
          </div>
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
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
              size="sm"
              onClick={() => setConversationToDelete(null)}
              disabled={deleteMutation.isPending}
              className="cursor-pointer"
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => {
                if (conversationToDelete) {
                  deleteMutation.mutate(conversationToDelete.id)
                }
              }}
              disabled={deleteMutation.isPending}
              className="cursor-pointer"
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete Permanently"}
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
          <Loader2Icon className="size-8 animate-spin text-muted-foreground" />
        </div>
      }
    >
      <ChatContent />
    </Suspense>
  )
}
