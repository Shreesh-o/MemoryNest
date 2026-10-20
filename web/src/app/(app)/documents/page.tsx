"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect } from "react";
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
import { SvgRefreshCw, SvgEye, SvgTrash2, SvgRotateCcw } from "@/components/ui/icons";
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

function DocumentSkeleton() {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Document</TableHead>
          <TableHead>Type</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Chunks</TableHead>
          <TableHead>Created</TableHead>
          <TableHead className="w-32">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {Array.from({ length: 5 }).map((_, i) => (
          <TableRow key={i}>
            <TableCell>
              <Skeleton className="h-4 w-48" />
            </TableCell>
            <TableCell>
              <Skeleton className="h-4 w-20" />
            </TableCell>
            <TableCell>
              <Skeleton className="h-6 w-24" />
            </TableCell>
            <TableCell>
              <Skeleton className="h-4 w-16" />
            </TableCell>
            <TableCell>
              <Skeleton className="h-4 w-32" />
            </TableCell>
            <TableCell>
              <Skeleton className="h-8 w-24" />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function DocumentsTable({ documents, onPreview, onDelete, onRetry }: {
  documents: Document[];
  onPreview: (doc: Document) => void;
  onDelete: (id: number) => void;
  onRetry: (id: number) => void;
}) {
  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Document</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Chunks</TableHead>
            <TableHead>Created</TableHead>
            <TableHead className="w-32">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {documents.map((doc) => (
            <TableRow key={doc.id}>
              <TableCell className="font-medium truncate max-w-xs">{doc.filename}</TableCell>
              <TableCell>{doc.file_type.toUpperCase()}</TableCell>
              <TableCell><StatusBadge status={doc.status} /></TableCell>
              <TableCell>{doc.chunk_count}</TableCell>
              <TableCell>{formatDate(doc.created_at)}</TableCell>
              <TableCell>
                <DropdownMenu>
                  <DropdownMenuTrigger>
                    <Button variant="ghost" size="icon" className="h-8 w-8">
                      <span className="sr-only">Actions</span>
                      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
                      </svg>
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={() => onPreview(doc)}>
                      <SvgEye className="mr-2 h-4 w-4" /> Preview
                    </DropdownMenuItem>
                    {doc.status === "failed" && (
                      <>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem onClick={() => onRetry(doc.id)} className="text-blue-600">
                          <SvgRotateCcw className="mr-2 h-4 w-4" /> Retry Extraction
                        </DropdownMenuItem>
                      </>
                    )}
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={() => onDelete(doc.id)} className="text-red-600">
                      <SvgTrash2 className="mr-2 h-4 w-4" /> Delete
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

function DocumentCard({ doc, onPreview, onDelete, onRetry }: {
  doc: Document;
  onPreview: (doc: Document) => void;
  onDelete: (id: number) => void;
  onRetry: (id: number) => void;
}) {
  return (
    <Card className="flex flex-col">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="min-w-0 flex-1">
            <CardTitle className="truncate text-lg">{doc.filename}</CardTitle>
            <CardDescription className="text-xs">
              {doc.file_type.toUpperCase()} &bull; {doc.chunk_count} chunks &bull; {formatDate(doc.created_at)}
            </CardDescription>
          </div>
          <StatusBadge status={doc.status} />
        </div>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col justify-end pt-0">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => onPreview(doc)} className="flex-1">
            <SvgEye className="mr-2 h-4 w-4" /> Preview
          </Button>
          {doc.status === "failed" && (
            <Button variant="outline" size="sm" onClick={() => onRetry(doc.id)} className="text-blue-600 border-blue-600 hover:bg-blue-50">
              <SvgRotateCcw className="mr-2 h-4 w-4" /> Retry
            </Button>
          )}
          <Button variant="ghost" size="sm" onClick={() => onDelete(doc.id)} className="text-red-600 hover:bg-red-50">
            <SvgTrash2 className="h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function PreviewDialog({ document, open, onOpenChange }: {
  document: Document | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle>{document?.filename}</DialogTitle>
          <DialogDescription>
            {document?.file_type.toUpperCase()} &bull; {document?.chunk_count} chunks &bull; {formatDate(document?.created_at)}
          </DialogDescription>
        </DialogHeader>
        <div className="mt-4 max-h-[60vh] overflow-y-auto p-4 bg-muted/50 rounded-md border whitespace-pre-wrap font-mono text-sm">
          {document?.text_preview || "No preview available"}
        </div>
      </DialogContent>
    </Dialog>
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
          <DialogDescription>{/* eslint-disable-next-line react/no-unescaped-entities */}
            Are you sure you want to delete "{document?.filename}"? This action cannot be undone.
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

export default function DocumentsPage() {
  useEffect(() => {
    document.title = "Documents — MemoryNest"
  }, [])
  const queryClient = useQueryClient();
  const [viewMode, setViewMode] = useState<ViewMode>("table");
  const [previewDoc, setPreviewDoc] = useState<Document | null>(null);
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

  const handlePreview = (doc: Document) => {
    setPreviewDoc(doc);
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
      <div className="p-6 max-w-4xl mx-auto">
        <Card>
          <CardHeader>
            <CardTitle>Documents</CardTitle>
            <CardDescription>Manage your documents</CardDescription>
          </CardHeader>
          <CardContent>
            <DocumentSkeleton />
          </CardContent>
        </Card>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Documents</CardTitle>
                <CardDescription>Manage your documents</CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                <SvgRefreshCw className="mr-2 h-4 w-4" /> Retry
              </Button>
            </div>
          </CardHeader>
          <CardContent className="text-center py-8">
            <p className="text-red-600 mb-4">Failed to load documents: {error instanceof Error ? error.message : "Unknown error"}</p>
            <Button onClick={() => refetch()}>
              <SvgRefreshCw className="mr-2 h-4 w-4" /> Try Again
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const docs = documents || [];

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <CardTitle>Documents</CardTitle>
              <CardDescription>Manage your documents</CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex border rounded-md overflow-hidden">
                <Button
                  variant={viewMode === "table" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setViewMode("table")}
                  className="rounded-r-none"
                >
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  </svg>
                  <span className="hidden sm:inline">Table</span>
                </Button>
                <Button
                  variant={viewMode === "cards" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setViewMode("cards")}
                  className="rounded-l-none"
                >
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                  <span className="hidden sm:inline">Cards</span>
                </Button>
              </div>
              <Button variant="outline" size="sm" onClick={() => refetch()} disabled={deleteMutation.isPending || retryMutation.isPending}>
                <SvgRefreshCw className={`mr-2 h-4 w-4 ${deleteMutation.isPending || retryMutation.isPending ? "animate-spin" : ""}`} />
                Refresh
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {docs.length === 0 ? (
            <div className="text-center py-12">
              <svg className="mx-auto h-12 w-12 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <h3 className="mt-4 text-lg font-medium">No documents yet</h3>
              <p className="mt-2 text-muted-foreground">Upload your first document to get started.</p>
            </div>
          ) : viewMode === "table" ? (
            <DocumentsTable
              documents={docs}
              onPreview={handlePreview}
              onDelete={handleDelete}
              onRetry={handleRetry}
            />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {docs.map((doc) => (
                <DocumentCard
                  key={doc.id}
                  doc={doc}
                  onPreview={handlePreview}
                  onDelete={handleDelete}
                  onRetry={handleRetry}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <PreviewDialog document={previewDoc} open={!!previewDoc} onOpenChange={(open) => !open && setPreviewDoc(null)} />
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
