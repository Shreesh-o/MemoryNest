"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { formatDate } from "@/lib/api";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import {
  RefreshCwIcon,
  EyeIcon,
  Trash2Icon,
  RotateCcwIcon,
  FileTextIcon,
  TableIcon,
  LayoutGridIcon,
  MoreVerticalIcon,
  UploadCloudIcon,
  FileIcon,
  FileTypeIcon,
  ImageIcon,
} from "lucide-react";
import { toast } from "sonner";

type Document = {
  id: number;
  filename: string;
  file_type: string;
  status: string;
  chunk_count: number;
  error_message?: string | null;
  created_at?: string | null;
  text_preview?: string | null;
};

type ViewMode = "table" | "cards";

async function fetchDocuments(): Promise<Document[]> {
  const res = await fetch("/api/documents", { credentials: "include" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to fetch documents");
  }
  return res.json();
}

async function deleteDocument(id: number): Promise<void> {
  const res = await fetch(`/api/documents/${id}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to delete document");
  }
}

async function retryDocument(id: number): Promise<Document> {
  const res = await fetch(`/api/documents/${id}/retry`, {
    method: "POST",
    credentials: "include",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to retry extraction");
  }
  return res.json();
}

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

function getFileIcon(fileType: string) {
  const type = fileType.toLowerCase();
  if (["png", "jpg", "jpeg"].includes(type)) {
    return <ImageIcon className="size-4 text-primary" />;
  }
  if (type === "pdf") {
    return <FileTypeIcon className="size-4 text-primary" />;
  }
  return <FileTextIcon className="size-4 text-primary" />;
}

function DocumentSkeleton() {
  return (
    <div className="rounded-lg border border-border overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Document</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Chunks</TableHead>
            <TableHead>Created</TableHead>
            <TableHead className="w-24 text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {Array.from({ length: 5 }).map((_, i) => (
            <TableRow key={i}>
              <TableCell>
                <Skeleton className="h-4 w-48" />
              </TableCell>
              <TableCell>
                <Skeleton className="h-4 w-16" />
              </TableCell>
              <TableCell>
                <Skeleton className="h-5 w-20 rounded-full" />
              </TableCell>
              <TableCell>
                <Skeleton className="h-4 w-12" />
              </TableCell>
              <TableCell>
                <Skeleton className="h-4 w-28" />
              </TableCell>
              <TableCell className="text-right">
                <Skeleton className="h-7 w-7 rounded-md ml-auto" />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function DocumentsTable({ documents, onView, onDelete, onRetry }: {
  documents: Document[];
  onView: (id: number) => void;
  onDelete: (id: number) => void;
  onRetry: (id: number) => void;
}) {
  return (
    <div className="rounded-lg border border-border/80 overflow-hidden bg-card">
      <Table>
        <TableHeader className="bg-muted/30">
          <TableRow>
            <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider">Document</TableHead>
            <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider">Type</TableHead>
            <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider">Status</TableHead>
            <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider">Chunks</TableHead>
            <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider">Created</TableHead>
            <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider text-right w-24">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {documents.map((doc) => (
            <TableRow key={doc.id} className="hover:bg-muted/40 transition-colors">
              <TableCell className="font-medium">
                <button
                  onClick={() => onView(doc.id)}
                  className="flex items-center gap-2.5 max-w-sm sm:max-w-md truncate text-left text-foreground hover:text-primary transition-colors cursor-pointer"
                >
                  <div className="flex size-7 shrink-0 items-center justify-center rounded bg-muted/60">
                    {getFileIcon(doc.file_type)}
                  </div>
                  <span className="truncate">{doc.filename}</span>
                </button>
              </TableCell>
              <TableCell>
                <Badge variant="outline" className="text-[11px] font-mono uppercase">
                  {doc.file_type}
                </Badge>
              </TableCell>
              <TableCell><StatusBadge status={doc.status} /></TableCell>
              <TableCell className="font-mono text-xs text-muted-foreground">{doc.chunk_count}</TableCell>
              <TableCell className="text-xs text-muted-foreground">{formatDate(doc.created_at)}</TableCell>
              <TableCell className="text-right">
                <DropdownMenu>
                  <DropdownMenuTrigger
                    render={
                      <Button variant="ghost" size="icon-sm" className="size-8 cursor-pointer rounded-md" />
                    }
                  >
                    <span className="sr-only">Actions</span>
                    <MoreVerticalIcon className="size-4" />
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-44">
                    <DropdownMenuItem onClick={() => onView(doc.id)} className="cursor-pointer">
                      <EyeIcon className="mr-2 size-4" /> View Details
                    </DropdownMenuItem>
                    {(doc.status === "failed" || doc.status === "error") && (
                      <>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem onClick={() => onRetry(doc.id)} className="cursor-pointer text-primary focus:text-primary">
                          <RotateCcwIcon className="mr-2 size-4" /> Retry Extraction
                        </DropdownMenuItem>
                      </>
                    )}
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={() => onDelete(doc.id)} className="cursor-pointer text-destructive focus:text-destructive">
                      <Trash2Icon className="mr-2 size-4" /> Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function DocumentCard({ doc, onView, onDelete, onRetry }: {
  doc: Document;
  onView: (id: number) => void;
  onDelete: (id: number) => void;
  onRetry: (id: number) => void;
}) {
  return (
    <Card className="flex flex-col justify-between hover:border-border transition-all group">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-start gap-2.5 min-w-0 flex-1">
            <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-muted/60 mt-0.5">
              {getFileIcon(doc.file_type)}
            </div>
            <div className="min-w-0 flex-1">
              <CardTitle className="truncate text-base font-medium group-hover:text-primary transition-colors">
                {doc.filename}
              </CardTitle>
              <CardDescription className="text-xs text-muted-foreground mt-0.5">
                {doc.chunk_count} chunks &bull; {formatDate(doc.created_at)}
              </CardDescription>
            </div>
          </div>
          <StatusBadge status={doc.status} />
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="flex items-center gap-2 border-t border-border/50 pt-3 mt-1">
          <Button variant="outline" size="sm" onClick={() => onView(doc.id)} className="flex-1 text-xs h-8 cursor-pointer">
            <EyeIcon className="mr-1.5 size-3.5" /> View
          </Button>
          {(doc.status === "failed" || doc.status === "error") && (
            <Button variant="outline" size="sm" onClick={() => onRetry(doc.id)} className="text-xs h-8 text-primary border-primary/30 hover:bg-primary/10 cursor-pointer">
              <RotateCcwIcon className="mr-1.5 size-3.5" /> Retry
            </Button>
          )}
          <Button variant="ghost" size="icon-sm" onClick={() => onDelete(doc.id)} className="size-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10 cursor-pointer">
            <Trash2Icon className="size-3.5" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function DeleteConfirmDialog({ document, open, onOpenChange, onConfirm, isPending }: {
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
            Are you sure you want to delete &quot;{document?.filename}&quot;? This action will remove all vector embeddings, summaries, and extracted text permanently.
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

export default function DocumentsPage() {
  useEffect(() => {
    document.title = "Documents — MemoryNest"
  }, [])

  const router = useRouter();
  const queryClient = useQueryClient();
  const [viewMode, setViewMode] = useState<ViewMode>("table");
  const [deleteDoc, setDeleteDoc] = useState<Document | null>(null);

  const { data: documents, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["documents"],
    queryFn: fetchDocuments,
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      toast.success("Document deleted");
      setDeleteDoc(null);
    },
    onError: (err: Error) => {
      toast.error(err.message);
    },
  });

  const retryMutation = useMutation({
    mutationFn: retryDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      toast.success("Extraction retried");
    },
    onError: (err: Error) => {
      toast.error(err.message);
    },
  });

  const handleDelete = (id: number) => {
    const doc = documents?.find((d) => d.id === id);
    if (doc) setDeleteDoc(doc);
  };

  const handleView = (id: number) => {
    router.push(`/documents/${id}`);
  };

  const handleRetry = (id: number) => {
    retryMutation.mutate(id);
  };

  const confirmDelete = () => {
    if (deleteDoc) {
      deleteMutation.mutate(deleteDoc.id);
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="flex items-center justify-between pb-2 border-b border-border/60">
          <div>
            <h1 className="font-heading text-2xl sm:text-3xl font-bold tracking-tight text-foreground">Documents</h1>
            <p className="text-sm text-muted-foreground mt-1">Loading vault inventory...</p>
          </div>
        </div>
        <DocumentSkeleton />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="max-w-6xl mx-auto py-8">
        <Card className="border border-destructive/30">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Documents</CardTitle>
                <CardDescription>Failed to load documents</CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={() => refetch()} className="cursor-pointer">
                <RefreshCwIcon className="mr-2 size-4" /> Retry
              </Button>
            </div>
          </CardHeader>
          <CardContent className="text-center py-8">
            <p className="text-destructive mb-4 text-sm">{error instanceof Error ? error.message : "Unknown error"}</p>
            <Button onClick={() => refetch()} className="cursor-pointer">
              <RefreshCwIcon className="mr-2 size-4" /> Try Again
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const docs = documents || [];

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Page Header with View Controls & Upload Action */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-border/60">
        <div>
          <h1 className="font-heading text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
            Documents
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage your knowledge vault files, view extractions, and inspect index status
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <Button
            size="sm"
            onClick={() => router.push("/upload")}
            className="text-xs h-8 gap-1.5 cursor-pointer"
          >
            <UploadCloudIcon className="size-3.5" />
            <span>Upload New</span>
          </Button>

          {/* Table / Cards View Mode Toggle */}
          <div className="flex items-center rounded-lg border border-border/70 bg-muted/40 p-0.5">
            <Button
              variant={viewMode === "table" ? "secondary" : "ghost"}
              size="icon-xs"
              onClick={() => setViewMode("table")}
              aria-label="Table view"
              className="rounded-md"
            >
              <TableIcon className="size-3.5" />
            </Button>
            <Button
              variant={viewMode === "cards" ? "secondary" : "ghost"}
              size="icon-xs"
              onClick={() => setViewMode("cards")}
              aria-label="Cards view"
              className="rounded-md"
            >
              <LayoutGridIcon className="size-3.5" />
            </Button>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={deleteMutation.isPending || retryMutation.isPending}
            className="text-xs h-8 gap-1.5 cursor-pointer"
          >
            <RefreshCwIcon className={`size-3.5 ${deleteMutation.isPending || retryMutation.isPending ? "animate-spin" : ""}`} />
            <span className="hidden sm:inline">Refresh</span>
          </Button>
        </div>
      </div>

      {/* Content Area */}
      {docs.length === 0 ? (
        <EmptyState
          icon={<FileIcon />}
          title="No documents yet"
          description="Upload your PDFs, Word documents, text notes, or scanned images to begin searching and querying."
          action={
            <Button onClick={() => router.push("/upload")} size="sm" className="gap-1.5">
              <UploadCloudIcon className="size-4" />
              Upload First Document
            </Button>
          }
        />
      ) : viewMode === "table" ? (
        <DocumentsTable
          documents={docs}
          onView={handleView}
          onDelete={handleDelete}
          onRetry={handleRetry}
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {docs.map((doc) => (
            <DocumentCard
              key={doc.id}
              doc={doc}
              onView={handleView}
              onDelete={handleDelete}
              onRetry={handleRetry}
            />
          ))}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <DeleteConfirmDialog
        document={deleteDoc}
        open={!!deleteDoc}
        onOpenChange={(open) => !open && setDeleteDoc(null)}
        onConfirm={confirmDelete}
        isPending={deleteMutation.isPending}
      />
    </div>
  );
}
