"use client"

import { useState, useCallback, useMemo, useEffect, useRef } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import dynamic from "next/dynamic"
import Link from "next/link"
import {
  Share2,
  RotateCcw,
  X,
  Maximize2,
  ExternalLink,
  ChevronDown,
  ChevronUp,
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
import { Slider as BaseUISlider } from "@base-ui/react/slider"
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

// FGEdge doesn't extend GraphEdge because the library uses number for source/target initially
// but replaces them with node objects after layout
interface FGEdge {
  source: number | FGNode
  target: number | FGNode
  score: number
  shared_terms: string[]
  // Allow any additional properties for library compatibility
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  [key: string]: any
}

// File type colors
const FILE_TYPE_COLORS: Record<string, string> = {
  pdf: "hsl(var(--destructive))",
  docx: "hsl(221 83% 53%)", // blue
  txt: "hsl(var(--primary))",
  png: "hsl(30 100% 50%)", // orange
  jpg: "hsl(30 100% 50%)",
  jpeg: "hsl(30 100% 50%)",
  default: "hsl(var(--muted-foreground))",
}

function GraphSkeleton() {
  return (
    <Card className="h-[calc(100vh-280px)] min-h-[400px]">
      <CardContent className="h-full flex items-center justify-center">
        <Skeleton className="h-full w-full" />
      </CardContent>
    </Card>
  )
}

function EmptyState() {
  return (
    <Card className="h-[calc(100vh-280px)] min-h-[400px] flex flex-col items-center justify-center p-8">
      <CardContent className="flex flex-col items-center justify-center text-center">
        <Share2 className="h-12 w-12 text-muted-foreground mb-4" />
        <h3 className="text-lg font-medium mb-2">Upload at least 2 documents to see how they relate</h3>
        <p className="text-muted-foreground mb-6 max-w-xs">
          The Document Map connects documents with similar topics using embedding similarity.
        </p>
        <Link href="/upload">
          <Button>Go to Upload</Button>
        </Link>
      </CardContent>
    </Card>
  )
}

function NoEdgesHint() {
  return (
    <div className="text-center py-4 text-sm text-muted-foreground">
      No connections at this threshold. <span className="font-medium">Lower the similarity slider</span> to see weaker connections.
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
    <div
      className={cn(
        "fixed z-50 bg-card border shadow-lg transition-all duration-300",
        isMobile
          ? "bottom-0 left-0 right-0 max-h-[60vh] rounded-t-xl"
          : "right-0 top-0 h-full w-96 rounded-l-xl"
      )}
      style={isMobile ? { transform: "translateY(0)" } : { transform: "translateX(0)" }}
    >
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-3">
            <span
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: fileTypeColor }}
            />
            <div>
              <p className="font-medium truncate max-w-[200px]">{selectedNode.label}</p>
              <Badge variant="outline" className="text-xs capitalize">
                {selectedNode.file_type.toUpperCase()}
              </Badge>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Connected documents */}
        <ScrollArea className="flex-1 p-4">
          <h4 className="text-sm font-medium mb-3">Connected Documents ({edges.length})</h4>
          {edges.length === 0 ? (
            <p className="text-sm text-muted-foreground">No connections at current threshold</p>
          ) : (
            <div className="space-y-3">
              {edges.map((edge) => {
                const neighbor = neighbors.find(
                  (n) => n.id === (edge.source === selectedNode.id ? edge.target : edge.source)
                )
                if (!neighbor) return null
                const similarity = Math.round(edge.score * 100)
                return (
                  <div
                    key={`${selectedNode.id}-${neighbor.id}`}
                    className="flex items-start gap-3 p-3 rounded-lg hover:bg-accent transition-colors cursor-pointer group"
                    onClick={() => onNavigate(`/documents/${neighbor.id}`)}
                  >
                    <span
                      className="w-2.5 h-2.5 rounded-full mt-1.5 flex-shrink-0"
                      style={{ backgroundColor: FILE_TYPE_COLORS[neighbor.file_type.toLowerCase()] || FILE_TYPE_COLORS.default }}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate group-hover:underline">{neighbor.label}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="outline" className="text-xs">
                          {similarity}% similarity
                        </Badge>
                        {edge.shared_terms.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            {edge.shared_terms.slice(0, 3).map((term) => (
                              <Badge key={term} variant="secondary" className="text-xs">
                                {term}
                              </Badge>
                            ))}
                            {edge.shared_terms.length > 3 && (
                              <Badge variant="secondary" className="text-xs">
                                +{edge.shared_terms.length - 3}
                              </Badge>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                    <ExternalLink className="h-4 w-4 text-muted-foreground group-hover:text-foreground" />
                  </div>
                )
              })}
            </div>
          )}
        </ScrollArea>

        {/* Open document button */}
        <div className="p-4 border-t">
          <Button className="w-full" onClick={() => onNavigate(`/documents/${selectedNode.id}`)}>
            <ExternalLink className="h-4 w-4 mr-2" />
            Open Document
          </Button>
        </div>
      </div>
    </div>
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
  const containerRef = useRef<HTMLDivElement>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const graphRef = useRef<any>(null)
  const isMobile = typeof window !== "undefined" && window.innerWidth < 768

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

  // Re-render graph on theme change (simple approach: listen for media query)
  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)")
    const handleChange = () => {
      // Force a re-render by updating container size slightly
      setContainerSize((prev) => ({ ...prev, width: prev.width + 0 }))
    }
    mediaQuery.addEventListener("change", handleChange)
    return () => mediaQuery.removeEventListener("change", handleChange)
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

  // Node canvas object for custom rendering
  const nodeCanvasObject = useCallback(
    (node: FGNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const { x = 0, y = 0, __fileTypeColor } = node
      const radius = Math.max(8, Math.min(18, 8 + node.link_count * 2))

      // Draw node circle
      ctx.beginPath()
      ctx.arc(x, y, radius, 0, 2 * Math.PI)
      ctx.fillStyle = __fileTypeColor || FILE_TYPE_COLORS.default
      ctx.fill()
      ctx.strokeStyle = "hsl(var(--background))"
      ctx.lineWidth = 2
      ctx.stroke()

      // Draw label on hover/zoom
      if (globalScale > 1.5 || node.__hover || node.__selected) {
        ctx.font = "12px system-ui, sans-serif"
        ctx.fillStyle = "hsl(var(--foreground))"
        ctx.textAlign = "center"
        const label = node.label.length > 24 ? node.label.slice(0, 24) + "..." : node.label
        const metrics = ctx.measureText(label)
        const textWidth = metrics.width
        const padding = 6

        // Background for label
        ctx.fillStyle = "hsl(var(--popover))"
        ctx.beginPath()
        ctx.roundRect(
          x - textWidth / 2 - padding,
          y - radius - 24,
          textWidth + padding * 2,
          18,
          4
        )
        ctx.fill()

        ctx.fillStyle = "hsl(var(--foreground))"
        ctx.fillText(label, x, y - radius - 8)
      }
    },
    []
  )

  // Calculate dimensions
  const graphHeight = containerSize.height || window.innerHeight - 280

  // Total documents count
  const totalDocs = (graphData?.nodes.length || 0) + (graphData?.unlinked.length || 0)

  if (isLoading) return <GraphSkeleton />

  if (isError) {
    return (
      <Card className="h-[calc(100vh-280px)] min-h-[400px]">
        <CardContent className="h-full flex flex-col items-center justify-center">
          <div className="text-center">
            <p className="text-destructive mb-4">Failed to load Document Map</p>
            <Button onClick={() => refetch()}>Retry</Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (totalDocs < 2) return <EmptyState />

  const hasEdges = graphDataMemo.links.length > 0

  return (
    <div className="flex flex-col h-[calc(100vh-120px)] min-h-[600px] p-4 md:p-6 gap-4">
      {/* Title & Description */}
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold">Document Map</h1>
        <p className="text-muted-foreground">
          Documents are connected when they cover similar topics.
        </p>
      </div>

      {/* Controls */}
      <Card className="flex-shrink-0">
        <CardContent className="p-4">
          <div className="flex flex-col md:flex-row md:items-end gap-4 w-full">
            <div className="flex-1">
              <div className="flex items-center justify-between mb-2">
                <Label htmlFor="minScore">Minimum similarity</Label>
                <span className="text-sm font-mono text-primary">
                  {Math.round(minScore * 100)}%
                </span>
              </div>
              <BaseUISlider.Root
                id="minScore"
                min={0.3}
                max={0.9}
                step={0.05}
                value={minScore}
                onValueChange={(v: number) => setMinScore(v)}
                className="w-full"
              >
                <BaseUISlider.Track className="relative h-2 w-full grow overflow-hidden rounded-full bg-secondary">
                  <BaseUISlider.Indicator className="h-full bg-primary" />
                </BaseUISlider.Track>
                <BaseUISlider.Thumb className="block h-5 w-5 rounded-full border-2 border-primary bg-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50" />
              </BaseUISlider.Root>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => refreshMutation.mutate()}
                disabled={refreshMutation.isPending}
                className="gap-2"
              >
                {refreshMutation.isPending ? (
                  <>
                    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24">
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                        fill="none"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    Refreshing...
                  </>
                ) : (
                  <>
                    <RotateCcw className="h-4 w-4" />
                    Refresh
                  </>
                )}
              </Button>
              <Button variant="outline" onClick={() => graphRef.current?.zoomToFit()}>
                <Maximize2 className="h-4 w-4 mr-2" />
                Reset view
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Graph */}
      <Card className="flex-1 min-h-0 overflow-hidden relative">
        <CardContent className="h-full p-0 relative">
          <div
            ref={containerRef}
            className="w-full h-full"
            style={{ height: graphHeight }}
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
                nodeVal={(node) => Math.max(8, Math.min(18, 8 + node.link_count * 2))}
                linkSource="source"
                linkTarget="target"
                linkColor={() => "hsl(var(--border))"}
                linkWidth={(link) => Math.max(0.5, link.score * 3)}
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

      {/* Legend */}
      <Card className="flex-shrink-0">
        <CardContent className="p-4">
          <div className="flex flex-wrap items-center gap-4 text-sm">
            <span className="font-medium">File types:</span>
            {Object.entries(FILE_TYPE_COLORS).map(([type, color]) => (
              type !== "default" && (
                <span key={type} className="flex items-center gap-1.5">
                  <span
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: color }}
                  />
                  {type.toUpperCase()}
                </span>
              )
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Unlinked documents */}
      {graphData && graphData.unlinked.length > 0 && (
        <Card className="flex-shrink-0">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Not connected</CardTitle>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setShowUnlinked(!showUnlinked)}
                className="text-muted-foreground"
              >
                {showUnlinked ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </Button>
            </div>
            <CardDescription className="text-xs">
              {graphData.unlinked.length} document{graphData.unlinked.length !== 1 ? "s" : ""} with no connections at this threshold
            </CardDescription>
          </CardHeader>
          {showUnlinked && (
              <CardContent className="pt-0">
                <ScrollArea className="max-h-40">
                  <div className="flex flex-wrap gap-2">
                    {graphData.unlinked.map((doc) => (
                      <Link
                        key={doc.id}
                        href={`/documents/${doc.id}`}
                        className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm hover:bg-accent transition-colors"
                      >
                        <span
                          className="w-2 h-2 rounded-full"
                          style={{ backgroundColor: FILE_TYPE_COLORS[doc.file_type.toLowerCase()] || FILE_TYPE_COLORS.default }}
                        />
                        <span className="truncate max-w-[150px]">{doc.label}</span>
                        <Badge variant="outline" className="text-xs capitalize ml-auto">
                          {doc.file_type.toUpperCase()}
                        </Badge>
                      </Link>
                    ))}
                  </div>
                </ScrollArea>
              </CardContent>
            )}
          </Card>
        )}

      {/* Side Panel */}
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