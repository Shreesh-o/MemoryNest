"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
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
  SvgTrash2,
  SvgRotateCcw,
  SvgDownload,
  SvgFileText,
  SvgFile,
  SvgImage,
  SvgAlertCircle,
  SvgRefreshCw,
  SvgArrowLeft,
  SvgExternalLink,
  SvgChevronUp,
  SvgChevronDown,
  SvgCopy,
  SvgFileType,
  SvgCalendar,
  SvgMessageSquare,
} from "@/components/ui/icons";
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
  const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
    ready: "default",
    processing: "secondary",
    pending: "secondary",
    failed: "destructive",
    rejected: "outline",
    duplicate: "outline",
  };
  return (
    <Badge variant={variants[status] || "default"} className="capitalize">
      {status}
    </Badge>
  );
}

function FileTypeBadge({ fileType }: { fileType: string }) {
  const icons: Record<string, React.ReactNode> = {
    pdf: <SvgFileType className="h-3 w-3" />,
    docx: <SvgFileText className="h-3 w-3" />,
    txt: <SvgFileText className="h-3 w-3" />,
    png: <SvgImage className="h-3 w-3" />,
    jpg: <SvgImage className="h-3 w-3" />,
    jpeg: <SvgImage className="h-3 w-3" />,
  };
  const Icon = icons[fileType.toLowerCase()] || <SvgFile className="h-3 w-3" />;
  return (
    <Badge variant="outline" className="gap-1">
      {Icon}
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
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={onConfirm} disabled={isPending}>
            {isPending ? "Deleting..." : "Delete"}
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
      <SvgAlertCircle className="h-12 w-12 text-red-600 mb-4" />
      <h3 className="text-lg font-medium mb-2">Unable to load document</h3>
      <p className="text-muted-foreground mb-4 max-w-md">{message}</p>
      <Button onClick={onRetry} disabled={retrying}>
        {retrying ? (
          <>
            <SvgRefreshCw className="mr-2 h-4 w-4 animate-spin" />
            Retrying...
          </>
        ) : (
          <>
            <SvgRefreshCw className="mr-2 h-4 w-4" />
            Retry
          </>
        )}
      </Button>
    </div>
  );
}

function ProcessingState({ message = "Processing document..." }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <SvgLoader2 className="h-12 w-12 text-muted-foreground animate-spin mb-4" />
      <h3 className="text-lg font-medium mb-2">Document is processing</h3>
      <p className="text-muted-foreground">{message}</p>
    </div>
  );
}

// Add SvgLoader2 to icons if needed
function SvgLoader2(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg {...props} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
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
      <div className="h-full flex flex-col">
        <div className="flex items-center justify-between p-4 border-b">
          <p className="text-sm text-muted-foreground">PDF Document</p>
          <Button variant="outline" size="sm" onClick={() => window.open(`/api/documents/${document.id}/file`, "_blank")}>
            <SvgExternalLink className="mr-2 h-4 w-4" />
            Open in new tab
          </Button>
        </div>
        <iframe
          src={`/api/documents/${document.id}/file`}
          className="flex-1 border-none"
          style={{ minHeight: "calc(100vh - 280px)" }}
          title={document.filename}
        />
      </div>
    );
  }

  // Images
  if (["png", "jpg", "jpeg"].includes(fileType)) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-4">
        <div
          className={`transition-transform duration-200 cursor-zoom-in ${zoomed ? "zoom-150" : "max-w-full"}`}
          onClick={() => setZoomed(!zoomed)}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && setZoomed(!zoomed)}
        >
          <img
            src={`/api/documents/${document.id}/file`}
            alt={document.filename}
            className="max-w-full max-h-[calc(100vh-300px)] object-contain"
            style={{ boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)" }}
          />
        </div>
        <div className="mt-4 flex items-center gap-4 text-sm text-muted-foreground">
          <span>Click to toggle zoom</span>
          <Button variant="outline" size="sm" onClick={() => window.open(`/api/documents/${document.id}/file`, "_blank")}>
            <SvgExternalLink className="mr-2 h-4 w-4" />
            Open full size
          </Button>
        </div>
      </div>
    );
  }

  // DOCX - rendered HTML
  if (fileType === "docx") {
    return (
      <div className="h-full flex flex-col">
        <div className="p-4 border-b">
          <div className="prose prose-sm dark:prose-invert max-w-3xl mx-auto bg-white dark:bg-gray-100 p-8 rounded-lg shadow-sm"
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

  // Compute matches during render (avoids setState in effect)
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
  // currentMatch is initialized above, updated via effect when matches change

  // Update currentMatch when matches change (reset to first match)
  useEffect(() => {
    const timer = setTimeout(() => {
      setCurrentMatch(matches.length > 0 ? 0 : -1);
    }, 0);
    return () => clearTimeout(timer);
  }, [matches.length]);

  // Highlight matches when they change
  useEffect(() => {
    setTimeout(() => {
      const highlights = textRef.current?.querySelectorAll(".search-highlight");
      if (highlights && highlights.length > 0) {
        highlightsRef.current = Array.from(highlights) as HTMLSpanElement[];
        if (currentMatch >= 0) {
          highlightsRef.current[currentMatch].classList.add("current-match");
          highlightsRef.current[currentMatch].scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }
    }, 0);
  }, [searchQuery, text, currentMatch]);

  const goToMatch = (direction: "next" | "prev") => {
    if (matches.length === 0) return;
    highlightsRef.current[currentMatch]?.classList.remove("current-match");
    let newIndex = currentMatch;
    if (direction === "next") {
      newIndex = (currentMatch + 1) % matches.length;
    } else {
      newIndex = (currentMatch - 1 + matches.length) % matches.length;
    }
    setCurrentMatch(newIndex);
    highlightsRef.current[newIndex]?.classList.add("current-match");
    highlightsRef.current[newIndex]?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  const copyAll = async () => {
    await navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard");
  };

  const highlightText = (text: string, query: string): React.ReactNode => {
    if (!query.trim()) return text;
    const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi");
    const parts = text.split(regex);
    return parts.map((part, index) => {
      if (!part) return null;
      if (regex.test(part)) {
        return <mark key={index} className="search-highlight rounded bg-yellow-200/80 px-0.5 text-foreground dark:bg-yellow-500/30">{part}</mark>;
      }
      return <span key={index}>{part}</span>;
    });
  };

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2 p-3 border-b bg-muted/30 sticky top-0 z-10">
        <div className="flex-1 min-w-[200px]">
          <Input
            placeholder="Search in text..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="max-w-xs"
          />
        </div>
        {matches.length > 0 && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span>{currentMatch + 1} of {matches.length}</span>
            <Button variant="ghost" size="icon" onClick={() => goToMatch("prev")} disabled={matches.length === 0} title="Previous match">
              <SvgChevronUp className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" onClick={() => goToMatch("next")} disabled={matches.length === 0} title="Next match">
              <SvgChevronDown className="h-4 w-4" />
            </Button>
          </div>
        )}
        <Button variant="outline" size="sm" onClick={copyAll} disabled={!text}>
          <SvgCopy className="mr-2 h-4 w-4" />
          Copy all
        </Button>
        {contentData?.truncated && (
          <Badge variant="secondary" className="ml-2">
            <SvgAlertCircle className="mr-1 h-3 w-3" />
            Text truncated ({contentData.char_count.toLocaleString()} chars)
          </Badge>
        )}
        {isTxt && contentData?.file_type === "image" && (
          <Badge variant="outline" className="ml-2 text-xs">
            Text from OCR — may contain errors
          </Badge>
        )}
      </div>

      {/* Text content */}
      <div className="flex-1 overflow-y-auto p-4">
        <div
          ref={textRef}
          className={`max-w-3xl mx-auto whitespace-pre-wrap break-words leading-relaxed ${isCodeLike ? "font-mono text-sm" : "text-base"}`}
        >
          {highlightText(text, searchQuery)}
        </div>
        {!text && (
          <div className="text-center text-muted-foreground py-12">
            <SvgFileText className="mx-auto h-12 w-12 mb-4 opacity-50" />
            <p>No extracted text available</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function DocumentViewerPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
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
          // Determine default tab
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
    } catch (err) {
      toast.error("Failed to download file");
    }
  };

  // Keyboard navigation: Esc or Backspace to go back
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" || e.key === "Backspace") {
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
      <div className="p-6 max-w-4xl mx-auto">
        <Card>
          <CardHeader>
            <CardTitle>Loading...</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <Skeleton className="h-8 w-64" />
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-96 w-full" />
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <Card>
          <CardHeader>
            <CardTitle>Document</CardTitle>
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
      <div className="p-6 max-w-4xl mx-auto">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>{doc.filename}</CardTitle>
                <CardDescription>
                  {FileTypeBadge({ fileType: doc.file_type })}
                  <span className="ml-2">•</span>
                  <span className="ml-2">{formatSize(doc.size_bytes)}</span>
                  <span className="ml-2">•</span>
                  <span className="ml-2">{formatDate(doc.created_at)}</span>
                </CardDescription>
              </div>
              <StatusBadge status={doc.status} />
            </div>
          </CardHeader>
          <CardContent>
            {doc.status === "failed" ? (
              <div className="text-center py-8">
                <SvgAlertCircle className="mx-auto h-12 w-12 text-red-600 mb-4" />
                <h3 className="text-lg font-medium mb-2">Extraction failed</h3>
                <p className="text-muted-foreground mb-4">{doc.error_message || "Unknown error"}</p>
                <Button onClick={handleRetry} disabled={retrying}>
                  {retrying ? (
                    <>
                      <SvgRefreshCw className="mr-2 h-4 w-4 animate-spin" />
                      Retrying...
                    </>
                  ) : (
                    <>
                      <SvgRotateCcw className="mr-2 h-4 w-4" />
                      Retry Extraction
                    </>
                  )}
                </Button>
              </div>
            ) : (
              <ProcessingState message={`Document is ${doc.status}...`} />
            )}
            {doc.status === "failed" && (
              <div className="mt-6 pt-6 border-t">
                <Button variant="outline" onClick={handleDownload}>
                  <SvgDownload className="mr-2 h-4 w-4" />
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
    <div className="min-h-screen bg-background">
      {/* Sticky Header */}
      <header className="sticky top-0 z-40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-b">
        <div className="p-4 max-w-4xl mx-auto">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            {/* Back + Filename */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 min-w-0">
              <Button variant="ghost" size="icon" onClick={() => router.back()} className="sm:hidden">
                <SvgArrowLeft className="h-5 w-5" />
              </Button>
              <Button variant="ghost" size="sm" onClick={() => router.push("/documents")} className="hidden sm:flex items-center gap-2">
                <SvgArrowLeft className="h-4 w-4" />
                Back to Documents
              </Button>
              <div className="min-w-0 flex-1">
                <h1 className="text-lg font-semibold truncate">{doc.filename}</h1>
                <div className="flex flex-wrap items-center gap-2 mt-1 text-sm text-muted-foreground">
                  <FileTypeBadge fileType={doc.file_type} />
                  <span>•</span>
                  <span>{formatSize(doc.size_bytes)}</span>
                  <span>•</span>
                  <span>{formatDate(doc.created_at)}</span>
                  <span>•</span>
                  <StatusBadge status={doc.status} />
                  <span>•</span>
                  <span>{doc.chunk_count} chunks</span>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex flex-wrap items-center gap-2">
              <Button variant="outline" size="sm" onClick={handleDownload}>
                <SvgDownload className="mr-2 h-4 w-4" />
                Download
              </Button>
              <Button variant="outline" size="sm" onClick={() => router.push(`/summaries?doc=${docId}`)}>
                <SvgFileText className="mr-2 h-4 w-4" />
                Summarize
              </Button>
              <Button variant="outline" size="sm" onClick={() => router.push(`/reminders?doc=${docId}`)}>
                <SvgCalendar className="mr-2 h-4 w-4" />
                Extract events
              </Button>
              <Button variant="outline" size="sm" onClick={() => router.push(`/chat?doc=${docId}`)}>
                <SvgMessageSquare className="mr-2 h-4 w-4" />
                Ask about this document
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setDeleteDialogOpen(true)} className="text-red-600 hover:bg-red-50">
                <SvgTrash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Tabs - single Tabs root wrapping both header and content */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        {/* Sticky Tab Bar */}
        <div className="sticky top-16 z-30 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-b px-4">
          <TabsList className="w-full">
            <TabsTrigger value="original" className="flex-1">
              Original
            </TabsTrigger>
            <TabsTrigger value="extracted" className="flex-1">
              Extracted text
            </TabsTrigger>
          </TabsList>
        </div>

        {/* Tab Content */}
        <main className="p-4 max-w-4xl mx-auto pb-16">
          <TabsContent value="original" className="h-[calc(100vh-280px)] min-h-[500px]">
            {htmlLoading && activeTab === "original" && doc.file_type.toLowerCase() === "docx" ? (
              <div className="h-full flex items-center justify-center">
                <SvgLoader2 className="h-8 w-8 animate-spin" />
              </div>
            ) : (
              <OriginalTab document={doc} contentData={doc.file_type.toLowerCase() === "docx" ? { text: htmlContent || "", char_count: 0, truncated: false, file_type: "docx" } : contentData} />
            )}
          </TabsContent>

          <TabsContent value="extracted" className="h-[calc(100vh-280px)] min-h-[500px]">
            {contentLoading ? (
              <div className="h-full flex items-center justify-center">
                <SvgLoader2 className="h-8 w-8 animate-spin" />
              </div>
            ) : (
              <ExtractedTextTab contentData={contentData} isTxt={doc.file_type.toLowerCase() === "txt"} />
            )}
          </TabsContent>
        </main>
      </Tabs>

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