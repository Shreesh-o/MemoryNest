"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { formatDate, documentsGet, documentsFile, documentsContent, documentsHtml, documentsDelete, documentsRetry } from "@/lib/api";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Trash2Icon,
  RotateCcwIcon,
  DownloadIcon,
  FileTextIcon,
  FileIcon,
  ImageIcon,
  AlertCircleIcon,
  RefreshCwIcon,
  ArrowLeftIcon,
  ExternalLinkIcon,
  ChevronUpIcon,
  ChevronDownIcon,
  CopyIcon,
  FileTypeIcon,
  CalendarIcon,
  MessageSquareIcon,
  Loader2Icon,
} from "lucide-react";
import { toast } from "sonner";

type Document = {
  id: number;
  filename: string;
  file_type: string;
  size_bytes: number;
  status: string;
  chunk_count: number;
  error_message?: string | null;
  created_at?: string | null;
  text_preview?: string | null;
};

type Tab = "original" | "extracted";

type ContentData = {
  text: string;
  char_count: number;
  truncated: boolean;
  file_type: string;
};

function StatusBadge({ status }: { status: string }) {
  const variants: Record<string, "success" | "secondary" | "destructive" | "outline"> = {
    ready: "success",
    processing: "secondary",
    pending: "secondary",
    failed: "destructive",
    error: "destructive",
    rejected: "outline",
    duplicate: "outline",
  };
  return (
    <Badge variant={variants[status] || "outline"} className="capitalize font-medium text-xs">
      {status}
    </Badge>
  );
}

function FileTypeBadge({ fileType }: { fileType: string }) {
  const type = fileType.toLowerCase();
  let icon = <FileIcon className="size-3" />;
  if (type === "pdf") icon = <FileTypeIcon className="size-3" />;
  else if (["png", "jpg", "jpeg"].includes(type)) icon = <ImageIcon className="size-3" />;
  else if (["docx", "txt"].includes(type)) icon = <FileTextIcon className="size-3" />;

  return (
    <Badge variant="outline" className="gap-1 font-mono text-[11px] uppercase">
      {icon}
      {fileType.toUpperCase()}
    </Badge>
  );
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function DeleteConfirmDialog({
  document,
  open,
  onOpenChange,
  onConfirm,
  isPending,
}: {
  document: Document | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  isPending: boolean;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete Document</DialogTitle>
          <DialogDescription>
            Are you sure you want to delete &quot;{document?.filename}&quot;? This action cannot be undone.
          </DialogDescription>
        </DialogHeader>
        <div className="flex justify-end gap-2 mt-4">
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)} disabled={isPending} className="cursor-pointer">
            Cancel
          </Button>
          <Button variant="destructive" size="sm" onClick={onConfirm} disabled={isPending} className="cursor-pointer">
            {isPending ? "Deleting..." : "Delete Permanently"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function ErrorState({
  message,
  onRetry,
  retrying,
}: {
  message: string;
  onRetry: () => void;
  retrying: boolean;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="size-12 rounded-xl bg-destructive/10 text-destructive flex items-center justify-center mb-4">
        <AlertCircleIcon className="size-6" />
      </div>
      <h3 className="text-lg font-semibold mb-1">Unable to load document</h3>
      <p className="text-muted-foreground mb-4 max-w-md text-sm">{message}</p>
      <Button onClick={onRetry} disabled={retrying} size="sm" className="cursor-pointer">
        <RefreshCwIcon className={`mr-2 size-4 ${retrying ? "animate-spin" : ""}`} />
        {retrying ? "Retrying..." : "Retry"}
      </Button>
    </div>
  );
}

function ProcessingState({ message = "Processing document..." }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <Loader2Icon className="size-10 text-primary animate-spin mb-4" />
      <h3 className="text-lg font-semibold mb-1">Document is processing</h3>
      <p className="text-muted-foreground text-sm">{message}</p>
    </div>
  );
}

function OriginalTab({
  document,
  contentData,
}: {
  document: Document;
  contentData: ContentData | null;
}) {
  const fileType = document.file_type.toLowerCase();
  const [zoomed, setZoomed] = useState(false);

  // PDF
  if (fileType === "pdf") {
    return (
      <div className="h-full flex flex-col rounded-xl border border-border/80 overflow-hidden bg-card">
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-border/80 bg-muted/30">
          <span className="text-xs font-medium text-muted-foreground">PDF Preview</span>
          <Button variant="outline" size="xs" onClick={() => window.open(`/api/documents/${document.id}/file`, "_blank")} className="gap-1.5 cursor-pointer">
            <ExternalLinkIcon className="size-3" />
            Open in new tab
          </Button>
        </div>
        <iframe
          src={`/api/documents/${document.id}/file`}
          className="flex-1 w-full border-none bg-muted/20"
          style={{ minHeight: "calc(100vh - 280px)" }}
          title={document.filename}
        />
      </div>
    );
  }

  // Images
  if (["png", "jpg", "jpeg"].includes(fileType)) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-6 rounded-xl border border-border/80 bg-card">
        <div
          className={`transition-transform duration-200 cursor-zoom-in ${zoomed ? "scale-125" : "max-w-full"}`}
          onClick={() => setZoomed(!zoomed)}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && setZoomed(!zoomed)}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={`/api/documents/${document.id}/file`}
            alt={document.filename}
            className="max-w-full max-h-[calc(100vh-320px)] object-contain rounded-lg shadow-md border border-border"
          />
        </div>
        <div className="mt-4 flex items-center gap-4 text-xs text-muted-foreground">
          <span>Click image to toggle zoom</span>
          <Button variant="outline" size="xs" onClick={() => window.open(`/api/documents/${document.id}/file`, "_blank")} className="gap-1 cursor-pointer">
            <ExternalLinkIcon className="size-3" />
            Open full size
          </Button>
        </div>
      </div>
    );
  }

  // DOCX - rendered HTML
  if (fileType === "docx") {
    return (
      <div className="h-full flex flex-col rounded-xl border border-border/80 overflow-hidden bg-card">
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-border/80 bg-muted/30">
          <span className="text-xs font-medium text-muted-foreground">HTML Converted Document</span>
        </div>
        <div className="flex-1 overflow-y-auto p-6 bg-muted/10">
          <div
            className="prose prose-sm dark:prose-invert max-w-3xl mx-auto bg-card text-card-foreground p-8 rounded-xl border border-border/70 shadow-xs"
            dangerouslySetInnerHTML={{ __html: contentData?.text || "" }}
          />
        </div>
      </div>
    );
  }

  // TXT - same as extracted text
  return (
    <div className="h-full flex flex-col">
      <ExtractedTextTab contentData={contentData} isTxt={true} />
    </div>
  );
}

function ExtractedTextTab({
  contentData,
  isTxt = false,
}: {
  contentData: ContentData | null;
  isTxt?: boolean;
}) {
  const [searchQuery, setSearchQuery] = useState("");
  const [currentMatch, setCurrentMatch] = useState(-1);
  const textRef = useRef<HTMLDivElement>(null);
  const highlightsRef = useRef<HTMLSpanElement[]>([]);

  const text = contentData?.text || "";
  const isCodeLike = isTxt && /^\s*(\/\/|#|\* |```|import |const |function |def |class |<\?php)/m.test(text);

  // Compute matches
  const computeMatches = useCallback((query: string, content: string) => {
    if (!query.trim()) return [];
    const regex = new RegExp(query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi");
    const foundIndices: number[] = [];
    let match;
    while ((match = regex.exec(content)) !== null) {
      foundIndices.push(match.index);
    }
    return foundIndices;
  }, []);

  const matches = computeMatches(searchQuery, text);

  useEffect(() => {
    const timer = setTimeout(() => {
      setCurrentMatch(matches.length > 0 ? 0 : -1);
    }, 0);
    return () => clearTimeout(timer);
  }, [matches.length]);

  useEffect(() => {
    const timer = setTimeout(() => {
      const highlights = textRef.current?.querySelectorAll(".search-highlight");
      if (highlights && highlights.length > 0) {
        highlightsRef.current = Array.from(highlights) as HTMLSpanElement[];
        if (currentMatch >= 0 && highlightsRef.current[currentMatch]) {
          highlightsRef.current[currentMatch].classList.add("ring-2", "ring-primary");
          highlightsRef.current[currentMatch].scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }
    }, 0);
    return () => clearTimeout(timer);
  }, [searchQuery, text, currentMatch]);

  const goToMatch = (direction: "next" | "prev") => {
    if (matches.length === 0) return;
    highlightsRef.current[currentMatch]?.classList.remove("ring-2", "ring-primary");
    let newIndex = currentMatch;
    if (direction === "next") {
      newIndex = (currentMatch + 1) % matches.length;
    } else {
      newIndex = (currentMatch - 1 + matches.length) % matches.length;
    }
    setCurrentMatch(newIndex);
    highlightsRef.current[newIndex]?.classList.add("ring-2", "ring-primary");
    highlightsRef.current[newIndex]?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  const copyAll = async () => {
    await navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard");
  };

  const highlightText = (content: string, query: string): React.ReactNode => {
    if (!query.trim()) return content;
    const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi");
    const parts = content.split(regex);
    return parts.map((part, index) => {
      if (!part) return null;
      if (regex.test(part)) {
        return (
          <mark
            key={index}
            className="search-highlight rounded bg-amber-400/35 text-foreground dark:bg-amber-400/25 px-0.5 border-b border-amber-500/50"
          >
            {part}
          </mark>
        );
      }
      return <span key={index}>{part}</span>;
    });
  };

  return (
    <div className="h-full flex flex-col rounded-xl border border-border/80 overflow-hidden bg-card">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2 p-3 border-b border-border/80 bg-muted/30 sticky top-0 z-10">
        <div className="flex items-center gap-2 flex-1 min-w-[200px]">
          <Input
            placeholder="Search within extracted text..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="max-w-xs h-8 text-xs"
          />
          {matches.length > 0 && (
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-medium">
              <span>{currentMatch + 1} of {matches.length}</span>
              <Button variant="ghost" size="icon-xs" onClick={() => goToMatch("prev")} title="Previous match">
                <ChevronUpIcon className="size-3.5" />
              </Button>
              <Button variant="ghost" size="icon-xs" onClick={() => goToMatch("next")} title="Next match">
                <ChevronDownIcon className="size-3.5" />
              </Button>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          {contentData?.truncated && (
            <Badge variant="warning" className="text-[11px] gap-1">
              <AlertCircleIcon className="size-3" />
              Truncated ({contentData.char_count.toLocaleString()} chars)
            </Badge>
          )}
          {isTxt && contentData?.file_type === "image" && (
            <Badge variant="outline" className="text-[11px]">
              OCR Text
            </Badge>
          )}
          <Button variant="outline" size="sm" onClick={copyAll} disabled={!text} className="text-xs h-8 gap-1.5 cursor-pointer">
            <CopyIcon className="size-3.5" />
            Copy All
          </Button>
        </div>
      </div>

      {/* Text content */}
      <div className="flex-1 overflow-y-auto p-6 bg-muted/5">
        <div
          ref={textRef}
          className={`max-w-3xl mx-auto whitespace-pre-wrap break-words leading-relaxed text-foreground ${isCodeLike ? "font-mono text-xs" : "text-sm"}`}
        >
          {highlightText(text, searchQuery)}
        </div>
        {!text && (
          <div className="text-center text-muted-foreground py-16">
            <FileTextIcon className="mx-auto size-12 mb-3 opacity-40" />
            <p className="text-sm">No extracted text available for this file</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function DocumentViewerPage() {
  const params = useParams();
  const router = useRouter();
  const docId = parseInt(params.id as string, 10);

  const [doc, setDoc] = useState<Document | null>(null);
  const [contentData, setContentData] = useState<ContentData | null>(null);
  const [htmlContent, setHtmlContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [contentLoading, setContentLoading] = useState(false);
  const [htmlLoading, setHtmlLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>("original");

  // Load document metadata
  useEffect(() => {
    const mounted = { current: true };
    async function loadDocument() {
      try {
        setLoading(true);
        const result = await documentsGet(docId);
        if (!result.ok) {
          if (result.error?.status === 404) {
            setError("Document not found");
          } else {
            setError(result.error?.detail || "Failed to load document");
          }
          return;
        }
        if (mounted.current) {
          setDoc(result.data);
          const ft = result.data.file_type.toLowerCase();
          if (ft === "txt") {
            setActiveTab("extracted");
          }
        }
      } catch (err) {
        if (mounted.current) setError(err instanceof Error ? err.message : "Failed to load document");
      } finally {
        if (mounted.current) setLoading(false);
      }
    }
    loadDocument();
    return () => { mounted.current = false; };
  }, [docId]);

  // Load content when extracted tab is active
  useEffect(() => {
    if (!doc || activeTab !== "extracted" || contentData) return;
    const mounted = { current: true };
    async function loadContent() {
      try {
        setContentLoading(true);
        const result = await documentsContent(docId);
        if (!result.ok) {
          throw new Error(result.error?.detail || "Failed to load content");
        }
        if (mounted.current) setContentData(result.data);
      } catch (err) {
        if (mounted.current) toast.error(err instanceof Error ? err.message : "Failed to load content");
      } finally {
        if (mounted.current) setContentLoading(false);
      }
    }
    loadContent();
  }, [docId, activeTab, doc, contentData]);

  // Load HTML when original tab is active and file is DOCX
  useEffect(() => {
    if (!doc || activeTab !== "original" || doc.file_type.toLowerCase() !== "docx" || htmlContent) return;
    const mounted = { current: true };
    async function loadHtml() {
      try {
        setHtmlLoading(true);
        const result = await documentsHtml(docId);
        if (!result.ok) {
          throw new Error(result.error?.detail || "Failed to load HTML");
        }
        if (mounted.current) setHtmlContent(result.data.html);
      } catch (err) {
        if (mounted.current) toast.error(err instanceof Error ? err.message : "Failed to load HTML");
      } finally {
        if (mounted.current) setHtmlLoading(false);
      }
    }
    loadHtml();
  }, [docId, activeTab, doc, htmlContent]);

  const handleDelete = async () => {
    try {
      const result = await documentsDelete(docId);
      if (!result.ok) throw new Error(result.error?.detail || "Failed to delete");
      toast.success("Document deleted");
      router.push("/documents");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete document");
    }
  };

  const handleRetry = async () => {
    if (!doc) return;
    try {
      setRetrying(true);
      const result = await documentsRetry(docId);
      if (!result.ok) throw new Error(result.error?.detail || "Failed to retry");
      toast.success("Extraction retried");
      router.refresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to retry extraction");
    } finally {
      setRetrying(false);
    }
  };

  const handleDownload = async () => {
    if (!doc) return;
    try {
      const blob = await documentsFile(docId, true);
      const url = URL.createObjectURL(blob);
      const a = window.document.createElement("a");
      a.href = url;
      a.download = doc.filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Failed to download file");
    }
  };

  // Keyboard navigation: Esc or Backspace to go back
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        router.back();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [router]);

  // Page title
  useEffect(() => {
    if (doc) {
      window.document.title = `${doc.filename} — MemoryNest`;
    }
  }, [doc]);

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto space-y-4 py-8">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-6 w-96" />
        <Skeleton className="h-[600px] w-full rounded-xl" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-6xl mx-auto py-8">
        <Card className="border border-destructive/30">
          <CardHeader>
            <CardTitle>Document Viewer</CardTitle>
          </CardHeader>
          <CardContent>
            <ErrorState message={error} onRetry={() => router.refresh()} retrying={retrying} />
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!doc) {
    return null;
  }

  // Show processing/failed state
  if (doc.status !== "ready") {
    return (
      <div className="max-w-6xl mx-auto py-8">
        <Card className="border border-border/80">
          <CardHeader>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <CardTitle className="text-xl font-bold">{doc.filename}</CardTitle>
                <CardDescription className="flex items-center gap-2 mt-1">
                  <FileTypeBadge fileType={doc.file_type} />
                  <span>•</span>
                  <span>{formatSize(doc.size_bytes)}</span>
                  <span>•</span>
                  <span>{formatDate(doc.created_at)}</span>
                </CardDescription>
              </div>
              <StatusBadge status={doc.status} />
            </div>
          </CardHeader>
          <CardContent>
            {(doc.status === "failed" || doc.status === "error") ? (
              <div className="text-center py-8">
                <AlertCircleIcon className="mx-auto size-12 text-destructive mb-4" />
                <h3 className="text-lg font-semibold mb-1">Extraction failed</h3>
                <p className="text-muted-foreground mb-4 text-sm max-w-md mx-auto">{doc.error_message || "Unknown error during text processing"}</p>
                <Button onClick={handleRetry} disabled={retrying} className="gap-2 cursor-pointer">
                  <RotateCcwIcon className={`size-4 ${retrying ? "animate-spin" : ""}`} />
                  {retrying ? "Retrying..." : "Retry Extraction"}
                </Button>
              </div>
            ) : (
              <ProcessingState message={`Document is currently ${doc.status}...`} />
            )}
            {(doc.status === "failed" || doc.status === "error") && (
              <div className="mt-6 pt-6 border-t border-border flex justify-center">
                <Button variant="outline" size="sm" onClick={handleDownload} className="gap-1.5 cursor-pointer">
                  <DownloadIcon className="size-4" />
                  Download Original File
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Top Header Card */}
      <div className="flex flex-col gap-4 pb-4 border-b border-border/60">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          {/* Back button + Title */}
          <div className="flex items-start gap-3 min-w-0">
            <Button
              variant="outline"
              size="icon-sm"
              onClick={() => router.push("/documents")}
              className="mt-0.5 shrink-0 cursor-pointer"
              title="Back to Documents"
            >
              <ArrowLeftIcon className="size-4" />
            </Button>
            <div className="min-w-0 flex-1">
              <h1 className="font-heading text-xl sm:text-2xl font-bold tracking-tight text-foreground truncate">
                {doc.filename}
              </h1>
              <div className="flex flex-wrap items-center gap-2 mt-1.5 text-xs text-muted-foreground">
                <FileTypeBadge fileType={doc.file_type} />
                <span>•</span>
                <span className="font-mono">{formatSize(doc.size_bytes)}</span>
                <span>•</span>
                <span>{formatDate(doc.created_at)}</span>
                <span>•</span>
                <StatusBadge status={doc.status} />
                <span>•</span>
                <span className="font-medium">{doc.chunk_count} chunks indexed</span>
              </div>
            </div>
          </div>

          {/* Quick Action Buttons */}
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleDownload} className="text-xs h-8 gap-1.5 cursor-pointer">
              <DownloadIcon className="size-3.5" />
              Download
            </Button>
            <Button variant="outline" size="sm" onClick={() => router.push(`/summaries?doc=${docId}`)} className="text-xs h-8 gap-1.5 cursor-pointer">
              <FileTextIcon className="size-3.5" />
              Summarize
            </Button>
            <Button variant="outline" size="sm" onClick={() => router.push(`/reminders?doc=${docId}`)} className="text-xs h-8 gap-1.5 cursor-pointer">
              <CalendarIcon className="size-3.5" />
              Events
            </Button>
            <Button variant="outline" size="sm" onClick={() => router.push(`/chat?doc=${docId}`)} className="text-xs h-8 gap-1.5 cursor-pointer">
              <MessageSquareIcon className="size-3.5" />
              Ask
            </Button>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => setDeleteDialogOpen(true)}
              className="size-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10 cursor-pointer"
              title="Delete Document"
            >
              <Trash2Icon className="size-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Tabs View */}
      <Tabs value={activeTab} onValueChange={(val) => setActiveTab(val as Tab)} className="w-full space-y-4">
        <TabsList className="grid w-full grid-cols-2 max-w-xs">
          <TabsTrigger value="original" className="cursor-pointer">
            Original File
          </TabsTrigger>
          <TabsTrigger value="extracted" className="cursor-pointer">
            Extracted Text
          </TabsTrigger>
        </TabsList>

        <TabsContent value="original" className="min-h-[550px] outline-none">
          {htmlLoading && activeTab === "original" && doc.file_type.toLowerCase() === "docx" ? (
            <div className="min-h-[400px] flex items-center justify-center">
              <Loader2Icon className="size-8 animate-spin text-primary" />
            </div>
          ) : (
            <OriginalTab
              document={doc}
              contentData={doc.file_type.toLowerCase() === "docx" ? { text: htmlContent || "", char_count: 0, truncated: false, file_type: "docx" } : contentData}
            />
          )}
        </TabsContent>

        <TabsContent value="extracted" className="min-h-[550px] outline-none">
          {contentLoading ? (
            <div className="min-h-[400px] flex items-center justify-center">
              <Loader2Icon className="size-8 animate-spin text-primary" />
            </div>
          ) : (
            <ExtractedTextTab contentData={contentData} isTxt={doc.file_type.toLowerCase() === "txt"} />
          )}
        </TabsContent>
      </Tabs>

      {/* Delete Confirmation Modal */}
      <DeleteConfirmDialog
        document={doc}
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        onConfirm={handleDelete}
        isPending={retrying}
      />
    </div>
  );
}
