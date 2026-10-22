"use client"

import { useState, useEffect, useCallback, type ReactNode } from "react"
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import {
  SvgSearch,
  SvgFileText,
  SvgAlertCircle,
  SvgRefreshCw,
  SvgFile,
  SvgLoader2,
} from "@/components/ui/icons"
import { toast } from "sonner"

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

  return (
    <Card className="mb-3">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <CardTitle className="truncate text-lg">{hit.filename}</CardTitle>
            <CardDescription className="text-xs">
              Chunk {hit.chunk_index + 1} &bull; Document #{hit.document_id}
            </CardDescription>
          </div>
          <div className="text-right text-sm">
            <div className="font-mono text-sm">{pct}%</div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="flex h-1 w-full">
          <div className={`flex-1 bg-${hit.similarity >= 0.7 ? "green" : hit.similarity >= 0.5 ? "amber" : "red"}-500/30`} style={{ width: `${pct}%` }} />
        </div>
        <div className="p-3 whitespace-pre-wrap break-words text-sm font-mono text-muted-foreground">
          {highlighted}
        </div>
        <div className="flex justify-end pt-2">
          <a
            href={`/documents/${hit.document_id}`}
            className="text-sm inline-flex items-center gap-1 border border-input rounded-md px-2.5 py-1 text-sm font-medium hover:bg-muted transition-colors"
          >
            <span className="mr-1 h-4 w-4" />
            Open in Documents
          </a>
        </div>
      </CardContent>
    </Card>
  )
}

function SearchSkeleton() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Search Results</CardTitle>
        <CardDescription>Search your documents</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex items-start gap-3">
            <div className="flex-shrink-0 w-10 h-10 flex items-center justify-center bg-muted rounded">
              <Skeleton className="h-6 w-6" />
            </div>
            <div className="flex-1 min-w-0 space-y-2">
              <div className="h-4 bg-muted rounded w-3/4" />
              <div className="h-4 bg-muted rounded w-1/2" />
              <div className="h-12 bg-muted rounded w-full" />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
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
          className="rounded bg-yellow-200/80 px-0.5 text-foreground dark:bg-yellow-500/30"
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim() || loading) return
    setLoading(true)
    setError(null)
    try {
      const data = await searchDocuments(query.trim())
      setHits(data.hits || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed")
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <Card>
          <CardHeader>
            <CardTitle>Search</CardTitle>
            <CardDescription>Search your documents</CardDescription>
          </CardHeader>
          <CardContent>
            <SearchSkeleton />
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
            <CardTitle>Search</CardTitle>
            <CardDescription>Search your documents</CardDescription>
          </CardHeader>
          <CardContent className="text-center py-8">
            <SvgAlertCircle className="mx-auto h-12 w-12 text-red-600 mb-4" />
            <h3 className="text-lg font-medium mb-2">Search failed</h3>
            <p className="text-muted-foreground mb-4">{error}</p>
            <Button onClick={() => window.location.reload()}>
              <SvgRefreshCw className="mr-2 h-4 w-4" />
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <Card>
        <CardHeader>
          <CardTitle>Search</CardTitle>
          <CardDescription>Search your documents semantically</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="relative">
              <Input
                placeholder="Search your documents..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="pl-10"
              />
              <div className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                <SvgSearch className="h-4 w-4" />
              </div>
            </div>
            <Button type="submit" disabled={!query.trim() || loading} className="w-full">
              {loading ? (
                <SvgLoader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <SvgSearch className="mr-2 h-4 w-4" />
              )}
              Search
            </Button>
          </form>
          <Separator />
          {query.trim() && hits.length === 0 && !error && (
            <div className="text-center py-8 text-muted-foreground">
              <SvgFileText className="mx-auto h-12 w-12 mb-4 opacity-50" />
              <h3 className="text-lg font-medium">No results found</h3>
              <p className="mt-2">No documents match &quot;{query}&quot;. Try uploading more documents or adjusting your search terms.</p>
            </div>
          )}
          {hits.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-medium mb-3">
                {hits.length} result{hits.length !== 1 ? "s" : ""} for &quot;{query}&quot;
              </h3>
              {hits.map((hit) => (
                <SearchHitCard key={`${hit.document_id}-${hit.chunk_index}`} hit={hit} query={query} />
              ))}
            </div>
          )}
          {!query.trim() && hits.length === 0 && !error && (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
              <SvgSearch className="mx-auto h-12 w-12 mb-4 opacity-50" />
              <h3 className="text-lg font-medium">Search your documents</h3>
              <p className="mt-2">Enter a search query to find relevant documents.</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}