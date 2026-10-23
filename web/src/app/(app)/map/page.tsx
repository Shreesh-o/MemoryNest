"use client"

import { useState, useCallback, useMemo, useEffect, useRef } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import dynamic from "next/dynamic"
import Link from "next/link"
import {
  Share2Icon,
  RotateCcwIcon,
  XIcon,
  Maximize2Icon,
  ExternalLinkIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  Loader2Icon,
  InfoIcon,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { Slider } from "@/components/ui/slider"
import { getGraph, refreshGraph, type GraphNode, type GraphEdge } from "@/lib/api"

// Import react-force-graph-2d dynamically with SSR disabled
const ForceGraph2D = dynamic(
  () => import("react-force-graph-2d").then((mod) => mod.default),
  { ssr: false, loading: () => <GraphSkeleton /> }
)

// Extended types for ForceGraph2D (library adds simulation properties)
interface FGNode extends GraphNode {
  x?: number
  y?: number
  vx?: number
  vy?: number
  fx?: number | null
  fy?: number | null
  __fileTypeColor?: string
  __hover?: boolean
  __selected?: boolean
  // Allow any additional properties for library compatibility
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  [key: string]: any
}

interface FGEdge {
  source: number | FGNode
  target: number | FGNode
  score: number
  shared_terms: string[]
  // Allow any additional properties for library compatibility
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  [key: string]: any
}

// Consistent file type colors for canvas rendering
const FILE_TYPE_COLORS: Record<string, string> = {
  pdf: "#ef4444",   // red
  docx: "#3b82f6",  // blue
  txt: "#10b981",   // emerald
  png: "#f59e0b",   // amber
  jpg: "#f59e0b",
  jpeg: "#f59e0b",
  default: "#64748b", // slate
}

function GraphSkeleton() {
  return (
    <Card className="h-[calc(100vh-280px)] min-h-[400px] border border-border/80 shadow-xs">
      <CardContent className="h-full flex items-center justify-center p-6">
        <Skeleton className="h-full w-full rounded-xl" />
      </CardContent>
    </Card>
  )
}

function EmptyState() {
  return (
    <div className="flex-1 min-h-[440px] flex items-center justify-center p-6">
      <Card className="max-w-md w-full border border-border/80 shadow-xs text-center p-8">
        <div className="mx-auto size-12 rounded-xl bg-primary/10 flex items-center justify-center text-primary mb-4">
          <Share2Icon className="size-6" />
        </div>
        <h3 className="text-base font-semibold text-foreground mb-1.5">
          Upload at least 2 documents to see how they relate
        </h3>
        <p className="text-sm text-muted-foreground mb-6 leading-relaxed">
          The Document Map connects documents with similar topics using embedding similarity.
        </p>
        <Link href="/upload">
          <Button className="cursor-pointer">Go to Upload</Button>
        </Link>
      </Card>
    </div>
  )
}

function NoEdgesHint() {
  return (
    <div className="text-center py-6 px-4 text-sm text-muted-foreground bg-background/80 backdrop-blur-xs rounded-xl border border-border/70 max-w-sm shadow-xs">
      <InfoIcon className="size-5 mx-auto mb-2 text-primary" />
      <p className="font-medium text-foreground">No connections at this threshold</p>
      <p className="text-xs text-muted-foreground mt-1">
        Lower the similarity slider to reveal weaker connections.
      </p>
    </div>
  )
}

interface SidePanelProps {
  node: { node: GraphNode; edges: GraphEdge[]; neighbors: GraphNode[] } | null
  onClose: () => void
  onNavigate: (path: string) => void
  isMobile: boolean
}

function SidePanel({ node, onClose, onNavigate, isMobile }: SidePanelProps) {
  if (!node) return null

  const { node: selectedNode, edges, neighbors } = node
  const fileTypeColor = FILE_TYPE_COLORS[selectedNode.file_type.toLowerCase()] || FILE_TYPE_COLORS.default

  return (
    <>
      {isMobile && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-xs z-40 transition-opacity"
          onClick={onClose}
        />
      )}
      <div
        className={cn(
          "fixed z-50 bg-card border border-border shadow-2xl transition-all duration-200 flex flex-col",
          isMobile
            ? "bottom-0 left-0 right-0 max-h-[70vh] rounded-t-2xl border-b-0"
            : "right-0 top-0 h-full w-96 rounded-l-2xl border-r-0"
        )}
      >
        <div className="flex flex-col h-full min-h-0">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-border/70">
            <div className="flex items-center gap-3 min-w-0">
              <span
                className="size-3 rounded-full shrink-0 shadow-xs"
                style={{ backgroundColor: fileTypeColor }}
              />
              <div className="min-w-0">
                <p className="font-semibold text-sm text-foreground truncate">{selectedNode.label}</p>
                <Badge variant="outline" className="text-2xs font-mono uppercase mt-0.5">
                  {selectedNode.file_type}
                </Badge>
              </div>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              className="text-muted-foreground hover:text-foreground shrink-0 size-8 cursor-pointer rounded-lg"
              aria-label="Close details"
            >
              <XIcon className="size-4" />
            </Button>
          </div>

          {/* Connected documents */}
          <ScrollArea className="flex-1 p-4 min-h-0">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
              Connected Documents ({edges.length})
            </h4>
            {edges.length === 0 ? (
              <p className="text-xs text-muted-foreground py-4 text-center">
                No connections at current similarity threshold.
              </p>
            ) : (
              <div className="space-y-2">
                {edges.map((edge) => {
                  const neighbor = neighbors.find(
                    (n) => n.id === (edge.source === selectedNode.id ? edge.target : edge.source)
                  )
                  if (!neighbor) return null
                  const similarity = Math.round(edge.score * 100)
                  return (
                    <div
                      key={`${selectedNode.id}-${neighbor.id}`}
                      className="flex items-start gap-3 p-3 rounded-xl border border-border/60 hover:border-border hover:bg-accent/40 transition-colors cursor-pointer group"
                      onClick={() => onNavigate(`/documents/${neighbor.id}`)}
                    >
                      <span
                        className="size-2.5 rounded-full mt-1.5 shrink-0"
                        style={{ backgroundColor: FILE_TYPE_COLORS[neighbor.file_type.toLowerCase()] || FILE_TYPE_COLORS.default }}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-foreground truncate group-hover:text-primary transition-colors">
                          {neighbor.label}
                        </p>
                        <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                          <Badge variant="outline" className="text-2xs font-mono">
                            {similarity}% match
                          </Badge>
                          {edge.shared_terms.length > 0 && (
                            <div className="flex flex-wrap gap-1">
                              {edge.shared_terms.slice(0, 3).map((term) => (
                                <Badge key={term} variant="secondary" className="text-2xs">
                                  {term}
                                </Badge>
                              ))}
                              {edge.shared_terms.length > 3 && (
                                <Badge variant="secondary" className="text-2xs">
                                  +{edge.shared_terms.length - 3}
                                </Badge>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                      <ExternalLinkIcon className="size-4 text-muted-foreground group-hover:text-foreground shrink-0 mt-0.5" />
                    </div>
                  )
                })}
              </div>
            )}
          </ScrollArea>

          {/* Open document button */}
          <div className="p-4 border-t border-border/70 bg-card">
            <Button
              className="w-full gap-2 cursor-pointer font-medium"
              onClick={() => onNavigate(`/documents/${selectedNode.id}`)}
            >
              <ExternalLinkIcon className="size-4" />
              Open Document
            </Button>
          </div>
        </div>
      </div>
    </>
  )
}

export default function MapPage() {
  const queryClient = useQueryClient()
  const router = useRouter()
  const [minScore, setMinScore] = useState(0.45)
  const [debouncedMinScore, setDebouncedMinScore] = useState(0.45)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [selectedNodeData, setSelectedNodeData] = useState<{
    node: GraphNode
    edges: GraphEdge[]
    neighbors: GraphNode[]
  } | null>(null)
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 })
  const [showUnlinked, setShowUnlinked] = useState(true)
  const [isMobile, setIsMobile] = useState(false)
  const [isDark, setIsDark] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const graphRef = useRef<any>(null)

  // Track viewport width
  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768)
    }
    handleResize()
    window.addEventListener("resize", handleResize)
    return () => window.removeEventListener("resize", handleResize)
  }, [])

  // Track dark theme changes for canvas rendering
  useEffect(() => {
    const checkDark = () => {
      setIsDark(document.documentElement.classList.contains("dark"))
    }
    checkDark()
    const observer = new MutationObserver(checkDark)
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] })
    return () => observer.disconnect()
  }, [])

  // Debounce minScore changes
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedMinScore(minScore)
    }, 300)
    return () => clearTimeout(timer)
  }, [minScore])

  // Fetch graph data with debounced minScore
  const { data: graphResponse, isLoading, isError, refetch } = useQuery({
    queryKey: ["graph", debouncedMinScore],
    queryFn: () => getGraph(debouncedMinScore),
    enabled: true,
  })

  const graphData = graphResponse?.data

  // Refresh mutation
  const refreshMutation = useMutation({
    mutationFn: refreshGraph,
    onSuccess: () => {
      toast.success("Document Map refreshed")
      queryClient.invalidateQueries({ queryKey: ["graph"] })
    },
    onError: (err: Error) => {
      toast.error(err.message || "Failed to refresh graph")
    },
  })

  // Handle container resize
  useEffect(() => {
    if (!containerRef.current) return
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerSize({ width: entry.contentRect.width, height: entry.contentRect.height })
      }
    })
    observer.observe(containerRef.current)
    return () => observer.disconnect()
  }, [])

  // Prepare graph data (memoized to prevent re-layout)
  const graphDataMemo = useMemo(() => {
    if (!graphData) return { nodes: [], links: [] }

    // Copy data to prevent mutation by the library
    const nodes = graphData.nodes.map((n) => ({ ...n })) as FGNode[]
    const links = graphData.edges.map((e) => ({ ...e })) as FGEdge[]

    return { nodes, links }
  }, [graphData])

  // Handle graph events
  const onNodeHover = useCallback((node: FGNode | null) => {
    if (!node) {
      setSelectedNode(null)
      setSelectedNodeData(null)
      return
    }
    // Find neighbors
    const edges = graphData?.edges.filter(
      (e) => e.source === node.id || e.target === node.id
    ) || []
    const neighborIds = new Set(
      edges.flatMap((e) => (e.source === node.id ? e.target : e.source))
    )
    const neighbors = graphData?.nodes.filter((n) => neighborIds.has(n.id)) || []

    setSelectedNode(node)
    setSelectedNodeData({ node, edges, neighbors })
  }, [graphData])

  const onNodeClick = useCallback((node: FGNode | null) => {
    if (node) {
      onNodeHover(node)
    }
  }, [onNodeHover])

  const onBackgroundClick = useCallback(() => {
    setSelectedNode(null)
    setSelectedNodeData(null)
  }, [])

  // Node canvas object for custom crisp rendering in light/dark
  const nodeCanvasObject = useCallback(
    (node: FGNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const { x = 0, y = 0, __fileTypeColor } = node
      const radius = Math.max(8, Math.min(18, 8 + (node.link_count || 0) * 2))

      // Draw node circle
      ctx.beginPath()
      ctx.arc(x, y, radius, 0, 2 * Math.PI)
      ctx.fillStyle = __fileTypeColor || FILE_TYPE_COLORS[node.file_type?.toLowerCase()] || FILE_TYPE_COLORS.default
      ctx.fill()
      ctx.strokeStyle = isDark ? "#0b0f19" : "#ffffff"
      ctx.lineWidth = 2.5
      ctx.stroke()

      // Draw label on hover/zoom or selection
      const isSelected = selectedNode?.id === node.id
      if (globalScale > 1.4 || node.__hover || isSelected) {
        ctx.font = "600 12px system-ui, sans-serif"
        const label = node.label.length > 24 ? node.label.slice(0, 24) + "..." : node.label
        const metrics = ctx.measureText(label)
        const textWidth = metrics.width
        const padding = 7

        // Background pill for label
        ctx.fillStyle = isDark ? "#111827" : "#ffffff"
        ctx.strokeStyle = isDark ? "#374151" : "#e2e8f0"
        ctx.lineWidth = 1
        ctx.beginPath()
        ctx.roundRect(
          x - textWidth / 2 - padding,
          y - radius - 24,
          textWidth + padding * 2,
          20,
          6
        )
        ctx.fill()
        ctx.stroke()

        ctx.fillStyle = isDark ? "#f9fafb" : "#0f172a"
        ctx.textAlign = "center"
        ctx.textBaseline = "middle"
        ctx.fillText(label, x, y - radius - 14)
      }
    },
    [isDark, selectedNode]
  )

  // Total documents count
  const totalDocs = (graphData?.nodes.length || 0) + (graphData?.unlinked.length || 0)

  if (isLoading) return <GraphSkeleton />

  if (isError) {
    return (
      <Card className="h-[calc(100vh-280px)] min-h-[400px] border border-border/80 shadow-xs">
        <CardContent className="h-full flex flex-col items-center justify-center p-6 text-center">
          <p className="text-sm font-medium text-destructive mb-3">Failed to load Document Map</p>
          <Button onClick={() => refetch()} variant="outline" size="sm" className="cursor-pointer">
            Retry
          </Button>
        </CardContent>
      </Card>
    )
  }

  if (totalDocs < 2) return <EmptyState />

  const hasEdges = graphDataMemo.links.length > 0

  return (
    <div className="flex flex-col h-[calc(100vh-100px)] min-h-[640px] gap-4">
      {/* Title & Description */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">Document Map</h1>
          <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">
            Documents are connected when they cover similar topics.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refreshMutation.mutate()}
            disabled={refreshMutation.isPending}
            className="gap-2 cursor-pointer h-9 text-xs"
          >
            {refreshMutation.isPending ? (
              <>
                <Loader2Icon className="size-3.5 animate-spin text-primary" />
                Refreshing...
              </>
            ) : (
              <>
                <RotateCcwIcon className="size-3.5" />
                Refresh
              </>
            )}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => graphRef.current?.zoomToFit(400)}
            className="gap-1.5 cursor-pointer h-9 text-xs"
          >
            <Maximize2Icon className="size-3.5" />
            Reset view
          </Button>
        </div>
      </div>

      {/* Controls Bar */}
      <Card className="shrink-0 border border-border/80 shadow-xs">
        <CardContent className="p-3.5 sm:p-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex-1 max-w-md">
              <div className="flex items-center justify-between mb-2">
                <Label htmlFor="minScore" className="text-xs font-medium text-foreground cursor-pointer">
                  Minimum similarity threshold
                </Label>
                <span className="text-xs font-mono font-semibold text-primary">
                  {Math.round(minScore * 100)}%
                </span>
              </div>
              <Slider
                id="minScore"
                min={0.3}
                max={0.9}
                step={0.05}
                value={minScore}
                onValueChange={(v) => {
                  if (typeof v === "number") setMinScore(v)
                  else if (Array.isArray(v) && typeof v[0] === "number") setMinScore(v[0])
                }}
                className="w-full"
              />
            </div>

            {/* Legend inline on wide screens */}
            <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground border-t sm:border-t-0 sm:border-l border-border/70 pt-3 sm:pt-0 sm:pl-4">
              <span className="font-semibold text-foreground text-2xs uppercase tracking-wider">File types:</span>
              {Object.entries(FILE_TYPE_COLORS).map(([type, color]) => (
                type !== "default" && (
                  <span key={type} className="inline-flex items-center gap-1.5 font-mono text-2xs">
                    <span
                      className="size-2.5 rounded-full shrink-0"
                      style={{ backgroundColor: color }}
                    />
                    {type.toUpperCase()}
                  </span>
                )
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Graph Canvas Container */}
      <Card className="flex-1 min-h-[360px] overflow-hidden relative border border-border/80 shadow-xs bg-card/60 backdrop-blur-2xs">
        <CardContent className="h-full p-0 relative">
          <div
            ref={containerRef}
            className="w-full h-full min-h-[360px]"
            onClick={onBackgroundClick}
          >
            {hasEdges && containerSize.width > 0 && containerSize.height > 0 && (
              <ForceGraph2D
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                ref={graphRef as any}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                graphData={graphDataMemo as any}
                width={containerSize.width}
                height={containerSize.height}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                nodeCanvasObject={nodeCanvasObject as any}
                nodeAutoColorBy="file_type"
                nodeLabel={(node) => node.label}
                nodeVal={(node) => Math.max(8, Math.min(18, 8 + (node.link_count || 0) * 2))}
                linkSource="source"
                linkTarget="target"
                linkColor={() => (isDark ? "rgba(148, 163, 184, 0.3)" : "rgba(100, 116, 139, 0.25)")}
                linkWidth={(link) => Math.max(0.75, (link.score || 0) * 3)}
                linkDirectionalParticles={0}
                onEngineTick={() => {}}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                onNodeHover={onNodeHover as any}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                onNodeClick={onNodeClick as any}
                onBackgroundClick={onBackgroundClick}
                cooldownTicks={100}
                cooldownTime={15000}
                d3AlphaDecay={0.02}
                d3VelocityDecay={0.4}
                backgroundColor="transparent"
              />
            )}
            {!hasEdges && containerSize.width > 0 && (
              <div className="absolute inset-0 flex items-center justify-center p-8">
                <NoEdgesHint />
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Unlinked documents */}
      {graphData && graphData.unlinked.length > 0 && (
        <Card className="shrink-0 border border-border/80 shadow-xs">
          <CardHeader className="p-3.5 pb-2">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-sm font-semibold text-foreground">Not connected</CardTitle>
                <CardDescription className="text-xs mt-0.5">
                  {graphData.unlinked.length} document{graphData.unlinked.length !== 1 ? "s" : ""} with no connections at {Math.round(minScore * 100)}% similarity
                </CardDescription>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setShowUnlinked(!showUnlinked)}
                className="text-muted-foreground hover:text-foreground size-7 cursor-pointer"
                aria-label={showUnlinked ? "Collapse unlinked documents" : "Expand unlinked documents"}
              >
                {showUnlinked ? <ChevronUpIcon className="size-4" /> : <ChevronDownIcon className="size-4" />}
              </Button>
            </div>
          </CardHeader>
          {showUnlinked && (
            <CardContent className="p-3.5 pt-0">
              <ScrollArea className="max-h-36">
                <div className="flex flex-wrap gap-2 pt-1">
                  {graphData.unlinked.map((doc) => (
                    <Link
                      key={doc.id}
                      href={`/documents/${doc.id}`}
                      className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs border border-border/70 bg-card hover:bg-accent hover:border-border transition-colors group cursor-pointer"
                    >
                      <span
                        className="size-2 rounded-full shrink-0"
                        style={{ backgroundColor: FILE_TYPE_COLORS[doc.file_type.toLowerCase()] || FILE_TYPE_COLORS.default }}
                      />
                      <span className="truncate max-w-[140px] text-foreground font-medium group-hover:text-primary transition-colors">
                        {doc.label}
                      </span>
                      <Badge variant="outline" className="text-2xs font-mono uppercase">
                        {doc.file_type}
                      </Badge>
                    </Link>
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          )}
        </Card>
      )}

      {/* Side Panel for Selected Node */}
      {selectedNode && (
        <SidePanel
          node={selectedNodeData}
          onClose={() => {
            setSelectedNode(null)
            setSelectedNodeData(null)
          }}
          onNavigate={(path: string) => router.push(path)}
          isMobile={isMobile}
        />
      )}
    </div>
  )
}
