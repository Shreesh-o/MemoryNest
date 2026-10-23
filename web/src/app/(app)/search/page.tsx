"use client"

import { useState, useEffect, type ReactNode } from "react"
import Link from "next/link"
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { EmptyState } from "@/components/ui/empty-state"
import {
  SearchIcon,
  FileTextIcon,
  AlertCircleIcon,
  RefreshCwIcon,
  Loader2Icon,
  ExternalLinkIcon,
  SparklesIcon,
  XIcon,
} from "lucide-react"

type SearchHit = {
  document_id: number
  filename: string
  chunk_index: number
  snippet: string
  similarity: number
}

async function searchDocuments(query: string, top_k?: number) {
  const res = await fetch("/api/search", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, top_k }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || "Search failed")
  }
  return res.json()
}

function SearchHitCard({ hit, query }: { hit: SearchHit; query: string }) {
  const pct = Math.round(hit.similarity * 100)
  const highlighted = highlightText(hit.snippet, query)

  const badgeVariant: "success" | "warning" | "destructive" =
    hit.similarity >= 0.7 ? "success" : hit.similarity >= 0.5 ? "warning" : "destructive"

  return (
    <Card className="border border-border/80 shadow-xs hover:border-border transition-colors">
      <CardHeader className="p-4 sm:p-5 pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <CardTitle className="truncate text-base font-semibold text-foreground">
              {hit.filename}
            </CardTitle>
            <CardDescription className="text-xs text-muted-foreground mt-0.5">
              Chunk {hit.chunk_index + 1} &bull; Document #{hit.document_id}
            </CardDescription>
          </div>
          <div className="shrink-0 flex items-center gap-2">
            <Badge variant={badgeVariant} className="font-mono text-xs">
              {pct}% match
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-4 sm:p-5 pt-0 space-y-3">
        {/* Similarity meter */}
        <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-300 ${
              hit.similarity >= 0.7
                ? "bg-success"
                : hit.similarity >= 0.5
                ? "bg-warning"
                : "bg-destructive"
            }`}
            style={{ width: `${Math.max(5, pct)}%` }}
          />
        </div>

        {/* Snippet */}
        <div className="p-3.5 rounded-xl bg-muted/40 border border-border/60 text-xs sm:text-sm font-mono text-muted-foreground whitespace-pre-wrap break-words leading-relaxed">
          {highlighted}
        </div>

        {/* Action Link */}
        <div className="flex justify-end pt-1">
          <Link
            href={`/documents/${hit.document_id}`}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground border border-border/70 hover:border-border rounded-lg px-3 py-1.5 transition-colors cursor-pointer"
          >
            <ExternalLinkIcon className="size-3.5" />
            Open in Documents
          </Link>
        </div>
      </CardContent>
    </Card>
  )
}

function SearchSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 3 }).map((_, i) => (
        <Card key={i} className="border border-border/80 p-5">
          <div className="flex items-center justify-between mb-3">
            <Skeleton className="h-5 w-1/3 rounded-md" />
            <Skeleton className="h-5 w-16 rounded-full" />
          </div>
          <Skeleton className="h-1.5 w-full rounded-full mb-3" />
          <Skeleton className="h-16 w-full rounded-xl" />
        </Card>
      ))}
    </div>
  )
}

function highlightText(text: string, query: string): ReactNode {
  if (!query || !query.trim()) return text

  const stopWords = new Set(["the", "a", "of", "and", "to", "in", "is", "it", "for", "on", "with", "as", "at", "by", "from", "an", "or"])
  const terms = query
    .trim()
    .split(/\s+/)
    .filter(
      (term) => term.length >= 2 && !stopWords.has(term.toLowerCase())
    )

  if (terms.length === 0) return text

  const uniqueTerms = Array.from(new Set(terms.map((term) => term.toLowerCase())))
  uniqueTerms.sort((a, b) => b.length - a.length)

  // Build a case-insensitive regex pattern that matches any of the terms
  const escapedTerms = uniqueTerms.map((term) =>
    term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
  )
  const regex = new RegExp(`(${escapedTerms.join("|")})`, "gi")
  const termSet = new Set(uniqueTerms)

  // Split the text by the regex, keeping the matches
  const parts = text.split(regex)

  return parts.map((part, index) => {
    if (!part) return null
    if (termSet.has(part.toLowerCase())) {
      return (
        <mark
          key={index}
          className="rounded-xs bg-primary/20 text-foreground font-semibold px-0.5"
        >
          {part}
        </mark>
      )
    }
    return <span key={index}>{part}</span>
  })
}

export default function SearchPage() {
  useEffect(() => {
    document.title = "Search — MemoryNest"
  }, [])

  const [query, setQuery] = useState("")
  const [hits, setHits] = useState<SearchHit[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hasSearched, setHasSearched] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim() || loading) return
    setLoading(true)
    setError(null)
    setHasSearched(true)
    try {
      const data = await searchDocuments(query.trim())
      setHits(data.hits || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">Semantic Search</h1>
        <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">
          Find exact phrases or concept matches across your documents using embedding similarity.
        </p>
      </div>

      {/* Search Input Card */}
      <Card className="border border-border/80 shadow-xs">
        <CardContent className="p-3.5 sm:p-5">
          <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-2.5">
            <div className="relative flex-1">
              <SearchIcon className="absolute left-3.5 top-1/2 -translate-y-1/2 size-4 text-muted-foreground pointer-events-none" />
              <Input
                placeholder="Ask or search by concept, keywords, or topics..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="pl-10 pr-9 h-10 text-sm"
              />
              {query && (
                <button
                  type="button"
                  onClick={() => setQuery("")}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground cursor-pointer"
                  aria-label="Clear search"
                >
                  <XIcon className="size-3.5" />
                </button>
              )}
            </div>
            <Button
              type="submit"
              disabled={!query.trim() || loading}
              className="h-10 text-xs sm:text-sm gap-1.5 cursor-pointer px-5"
            >
              {loading ? (
                <>
                  <Loader2Icon className="size-4 animate-spin" />
                  Searching...
                </>
              ) : (
                <>
                  <SearchIcon className="size-4" />
                  Search
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Results or States */}
      {loading ? (
        <SearchSkeleton />
      ) : error ? (
        <Card className="border border-destructive/40 bg-destructive/5 text-center p-8">
          <AlertCircleIcon className="mx-auto size-10 text-destructive mb-3" />
          <h3 className="text-base font-semibold text-foreground mb-1">Search failed</h3>
          <p className="text-xs text-muted-foreground mb-4 max-w-sm mx-auto">{error}</p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleSubmit({ preventDefault: () => {} } as React.FormEvent)}
            className="cursor-pointer gap-1.5"
          >
            <RefreshCwIcon className="size-3.5" />
            Retry
          </Button>
        </Card>
      ) : hasSearched && hits.length === 0 ? (
        <EmptyState
          icon={<FileTextIcon className="size-6" />}
          title="No results found"
          description={`No document passages matched "${query}". Try adjusting keywords, asking broader concepts, or uploading more documents.`}
          action={
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setQuery("")
                setHasSearched(false)
              }}
              className="cursor-pointer"
            >
              Clear search
            </Button>
          }
        />
      ) : hits.length > 0 ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between px-1">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              {hits.length} result{hits.length !== 1 ? "s" : ""} for &quot;{query}&quot;
            </h3>
            <span className="text-2xs text-muted-foreground font-mono">Sorted by relevance</span>
          </div>
          <div className="space-y-3">
            {hits.map((hit) => (
              <SearchHitCard key={`${hit.document_id}-${hit.chunk_index}`} hit={hit} query={query} />
            ))}
          </div>
        </div>
      ) : (
        <EmptyState
          icon={<SparklesIcon className="size-6" />}
          title="Explore your knowledge base"
          description="Type any question or phrase above to retrieve the most semantically relevant passages across all your uploaded documents."
        />
      )}
    </div>
  )
}
