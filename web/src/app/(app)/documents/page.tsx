"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useRouter } from "next/navigation"
import { useToast } from "sonner"
import {
  documentsList,
  documentsDelete,
  documentsRetry,
  documentsUpload,
  type DocumentPublic,
} from "@/lib/api"
import { formatDate } from "@/lib/api"
import {
  FileText,
  FileAudio,
  FileImage,
  FileVideo,
  FileSpreadsheet,
  FileCode,
  File,
  MoreVertical,
  Eye,
  RotateCcw,
  Trash2,
  Upload,
  RefreshCw,
  AlertCircleIcon,
} from "lucide-react"
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  TableCaption,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from "@/components/ui/dropdown-menu"
import { AlertCircleIcon, UploadIcon, RefreshCwIcon } from "lucide-react"

function getFileIcon(fileType: string) {
  switch (fileType) {
    case "pdf": return FileText
    case "docx": return FileText
    case "txt": return FileText
    case "png": case "jpg": case "jpeg": case "tiff": case "bmp": return FileImage
    case "mp3": case "wav": case "ogg": return FileAudio
    case "mp4": case "mov": case "avi": return FileVideo
    case "xlsx": case "csv": return FileSpreadsheet
    case "py": case "js": case "ts": case "json": return FileCode
    default: return File
  }
}

function getStatusBadge(status: string) {
  switch (status) {
    case "ready": return <Badge variant="default" className="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">Ready</Badge>
    case "processing": return <Badge variant="secondary" className="bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200">Processing</Badge>
    case "error": return <Badge variant="destructive" className="bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">Error</Badge>
    case "uploaded": return <Badge variant="secondary" className="bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">Uploaded</Badge>
    case "extracting": return <Badge variant="secondary" className="bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200">Extracting</Badge>
    default: return <Badge variant="outline">{status}</Badge>
  }
}

function DocumentRowActions({ doc, onPreview, onRetry, onDelete }: { doc: DocumentPublic; onPreview: () => void; onRetry: () => void; onDelete: () => void }) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="h-8 w-8">
          <MoreVertical className="h-4 w-4" />
          <span className="sr-only">Actions</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel>Actions</DropdownMenuLabel>
        <DropdownMenuItem onClick={onPreview}><Eye className="h-4 w-4 mr-2" /> Preview</DropdownMenuItem>
        {doc.status === "error" && (<><DropdownMenuSeparator /><DropdownMenuItem onClick={onRetry}><RotateCcw className="h-4 w-4 mr-2" /> Retry extraction</DropdownMenuItem></>)}
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={onDelete} variant="destructive"><Trash2 className="h-4 w-4 mr-2" /> Delete</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

function PreviewDialog({ open, onOpenChange, doc }: { open: boolean; onOpenChange: (open: boolean) => void; doc: DocumentPublic | null }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle className="truncate">{doc?.filename}</DialogTitle>
          <DialogDescription>Status: {doc?.status} \u2022 {doc?.file_type} \u2022 {doc?.chunk_count} chunks</DialogDescription>
        </DialogHeader>
        <div className="max-h-[60vh] overflow-y-auto p-4 space-y-4">
          {doc?.text_preview && (<div><h4 className="font-medium mb-2">Text Preview</h4><pre className="whitespace-pre-wrap text-sm bg-muted p-4 rounded-md max-h-[40vh] overflow-y-auto">{doc.text_preview}</pre></div>)}
          {doc?.error_message && (<div className="border border-destructive/50 bg-destructive/10 p-4 rounded-md"><h4 className="font-medium text-destructive mb-2">Error</h4><p className="text-sm">{doc.error_message}</p></div>)}
          {!doc?.text_preview && !doc?.error_message && <p className="text-muted-foreground text-center py-8">No preview available</p>}
        </div>
      </DialogContent>
    </Dialog>
  )
}

function DeleteConfirmDialog({ open, onOpenChange, onConfirm, isLoading, docName }: { open: boolean; onOpenChange: (open: boolean) => void; onConfirm: () => void; isLoading: boolean; docName: string }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader><DialogTitle>Delete document</DialogTitle><DialogDescription>Are you sure you want to delete \u201c{docName}\u201d? This action cannot be undone.</DialogDescription></DialogHeader>
        <DialogFooter><Button variant="outline" onClick={() => onOpenChange(false)} disabled={isLoading}>Cancel</Button><Button variant="destructive" onClick={onConfirm} disabled={isLoading}>Delete</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function MobileDocumentCard({ doc, onPreview, onRetry, onDelete }: { doc: DocumentPublic; onPreview: () => void; onRetry: () => void; onDelete: () => void }) {
  const FileIcon = getFileIcon(doc.file_type)
  return (
    <div className="border border-border rounded-lg p-4 space-y-3 bg-card">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <FileIcon className="h-10 w-10 text-muted-foreground flex-shrink-0" />
          <div className="min-w-0"><h3 className="font-medium truncate">{doc.filename}</h3><p className="text-sm text-muted-foreground">{doc.file_type.toUpperCase()} \u2022 {doc.chunk_count} chunks</p></div>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild><Button variant="ghost" size="icon" className="h-8 w-8"><MoreVertical className="h-4 w-4" /><span className="sr-only">Actions</span></Button></DropdownMenuTrigger>
          <DropdownMenuContent align="end"><DropdownMenuLabel>Actions</DropdownMenuLabel>
            <DropdownMenuItem onClick={onPreview}><Eye className="h-4 w-4 mr-2" />Preview</DropdownMenuItem>
            {doc.status === "error" && (<><DropdownMenuSeparator /><DropdownMenuItem onClick={onRetry}><RotateCcw className="h-4 w-4 mr-2" />Retry extraction</DropdownMenuItem></>)}
            <DropdownMenuSeparator /><DropdownMenuItem onClick={onDelete} variant="destructive"><Trash2 className="h-4 w-4 mr-2" />Delete</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      <div className="flex items-center gap-2 flex-wrap">{getStatusBadge(doc.status)}<span className="text-xs text-muted-foreground">{formatDate(doc.created_at)}</span><span className="text-xs text-muted-foreground">{doc.chunk_count} chunks</span></div>
      {doc.status === "error" && doc.error_message && <p className="text-sm text-destructive bg-destructive/10 p-2 rounded">{doc.error_message}</p>}
    </div>
  )
}

export default function DocumentsPage() {
  const router = useRouter()
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const [previewDoc, setPreviewDoc] = useState<DocumentPublic | null>(null)
  const [deleteDoc, setDeleteDoc] = useState<DocumentPublic | null>(null)

  const { data: documents, isLoading, isError, error, refetch, isFetching } = useQuery({ queryKey: ["documents"], queryFn: documentsList, staleTime: 30000 })

  const deleteMutation = useMutation({ mutationFn: (id: number) => documentsDelete(id), onSuccess: () => { toast.success("Document deleted"); queryClient.invalidateQueries({ queryKey: ["documents"] }) }, onError: (error: Error) => { toast.error(error.message) } })
  const retryMutation = useMutation({ mutationFn: (id: number) => documentsRetry(id), onSuccess: () => { toast.success("Extraction retry started"); queryClient.invalidateQueries({ queryKey: ["documents"] }) }, onError: (error: Error) => { toast.error(error.message) } })

  const handleDelete = (doc: DocumentPublic) => { setDeleteDoc(doc) }
  const confirmDelete = () => { if (deleteDoc) { deleteMutation.mutate(deleteDoc.id); setDeleteDoc(null) } }
  const handlePreview = (doc: DocumentPublic) => { setPreviewDoc(doc) }
  const handleRetry = (id: number) => { retryMutation.mutate(id) }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files; if (!files || files.length === 0) return
    const formData = new FormData(); for (let i = 0; i < files.length; i++) formData.append("files", files[i])
    try { const results = await documentsUpload(formData); for (const result of results) { if (result.status === "ready") toast.success(`${result.filename}: ${result.message}`); else if (result.status === "duplicate") toast.info(`${result.filename}: ${result.message}`); else toast.error(`${result.filename}: ${result.message}`) } queryClient.invalidateQueries({ queryKey: ["documents"] }) } catch { toast.error("Upload failed") }
  }

  if (isLoading) { return (<div className="p-6"><div className="flex items-center justify-between mb-6"><h1 className="text-2xl font-bold">Documents</h1><Button variant="outline" size="icon" onClick={() => refetch()} disabled={isFetching}><RefreshCwIcon className="h-4 w-4" /><span className="sr-only">Refresh</span></Button></div><div className="space-y-3">{[1,2,3,4,5].map(i => (<div key={i} className="border border-border rounded-lg p-4 space-y-3 bg-card animate-pulse"><div className="flex items-center gap-3"><Skeleton className="h-10 w-10 rounded" /><div className="flex-1 space-y-2"><Skeleton className="h-4 w-3/4" /><Skeleton className="h-3 w-1/2" /></div></div><div className="flex items-center gap-2"><Skeleton className="h-5 w-20" /><Skeleton className="h-5 w-24" /><Skeleton className="h-5 w-16" /></div></div>))}</div></div>) }

  if (isError) { return (<div className="p-6"><div className="flex items-center justify-between mb-6"><h1 className="text-2xl font-bold">Documents</h1><Button onClick={() => refetch()} disabled={isFetching}><RefreshCwIcon className="h-4 w-4 mr-2" />Retry</Button></div><div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6 max-w-2xl"><AlertCircleIcon className="h-12 w-12 text-destructive mx-auto mb-4" /><h2 className="text-xl font-semibold text-center">Failed to load documents</h2><p className="text-muted-foreground text-center mt-2">{error instanceof Error ? error.message : "An unexpected error occurred"}</p><Button onClick={() => refetch()} className="mt-4 w-full"><RefreshCwIcon className="h-4 w-4 mr-2" />Retry</Button></div></div>) }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6"><h1 className="text-2xl font-bold">Documents</h1><div className="flex items-center gap-2"><Button variant="outline" size="icon" onClick={() => refetch()} disabled={isFetching}><RefreshCwIcon className="h-4 w-4" /><span className="sr-only">Refresh</span></Button><label className="cursor-pointer"><input type="file" multiple className="sr-only" onChange={handleUpload} /><Button><UploadIcon className="h-4 w-4 mr-2" />Upload</Button></label></div></div>
      {documents.length === 0 && (<div className="text-center py-12 border-2 border-dashed border-border rounded-xl"><UploadIcon className="h-12 w-12 text-muted-foreground mx-auto mb-4" /><h2 className="text-xl font-semibold mb-2">No documents yet</h2><p className="text-muted-foreground mb-6">Upload your first document to get started</p><label className="cursor-pointer"><input type="file" multiple className="sr-only" onChange={handleUpload} /><Button size="lg"><UploadIcon className="h-5 w-5 mr-2" />Upload your first document</Button></label></div>)}
      {documents.length > 0 && (<React.Fragment>
        <div className="hidden md:block overflow-x-auto rounded-lg border"><Table><TableCaption className="sr-only">Documents</TableCaption><TableHeader><TableRow><TableHead>File</TableHead><TableHead className="hidden sm:table-cell">Type</TableHead><TableHead className="hidden md:table-cell">Status</TableHead><TableHead className="hidden lg:table-cell">Chunks</TableHead><TableHead className="hidden md:table-cell">Created</TableHead><TableHead className="w-32">Actions</TableHead></TableRow></TableHeader><TableBody>{documents.map(doc => {const FileIcon = getFileIcon(doc.file_type); return (<TableRow key={doc.id}><TableCell className="flex items-center gap-3 min-w-[200px]"><div className="flex items-center gap-3"><FileIcon className="h-8 w-8 text-muted-foreground" /><div><p className="font-medium truncate max-w-[200px]">{doc.filename}</p><p className="text-xs text-muted-foreground">{doc.file_type.toUpperCase()}</p></div></div></TableCell><TableCell className="hidden sm:table-cell"><span className="text-sm text-muted-foreground capitalize">{doc.file_type}</span></TableCell><TableCell className="hidden md:table-cell">{getStatusBadge(doc.status)}</TableCell><TableCell className="hidden lg:table-cell"><span className="text-sm text-muted-foreground">{doc.chunk_count}</span></TableCell><TableCell className="hidden md:table-cell"><span className="text-sm text-muted-foreground">{formatDate(doc.created_at)}</span></TableCell><TableCell className="w-32"><DocumentRowActions doc={doc} onPreview={() => setPreviewDoc(doc)} onRetry={() => retryMutation.mutate(doc.id)} onDelete={() => setDeleteDoc(doc)} /></TableCell></TableRow>)})}</TableBody></Table></div><div className="md:hidden space-y-3">{documents.map(doc => <MobileDocumentCard key={doc.id} doc={doc} onPreview={() => setPreviewDoc(doc)} onRetry={() => retryMutation.mutate(doc.id)} onDelete={() => setDeleteDoc(doc)} />)}</div></React.Fragment>)}
      <PreviewDialog open={!!previewDoc} onOpenChange={open => { if (!open) setPreviewDoc(null) }} doc={previewDoc} /><DeleteConfirmDialog open={!!deleteDoc} onOpenChange={open => { if (!open) setDeleteDoc(null) }} onConfirm={confirmDelete} isLoading={deleteMutation.isPending} docName={deleteDoc?.filename || ""} /></div>)}

function MobileDocumentCard({ doc, onPreview, onRetry, onDelete }: { doc: DocumentPublic; onPreview: () => void; onRetry: () => void; onDelete: () => void }) {
  const FileIcon = getFileIcon(doc.file_type)
  return (<div className="border border-border rounded-lg p-4 space-y-3 bg-card"><div className="flex items-start justify-between gap-2"><div className="flex items-center gap-3 flex-1 min-w-0"><FileIcon className="h-10 w-10 text-muted-foreground flex-shrink-0" /><div className="min-w-0"><h3 className="font-medium truncate">{doc.filename}</h3><p className="text-sm text-muted-foreground">{doc.file_type.toUpperCase()} \u2022 {doc.chunk_count} chunks</p></div></div><DropdownMenu><DropdownMenuTrigger asChild><Button variant="ghost" size="icon" className="h-8 w-8"><MoreVertical className="h-4 w-4" /><span className="sr-only">Actions</span></Button></DropdownMenuTrigger><DropdownMenuContent align="end"><DropdownMenuLabel>Actions</DropdownMenuLabel><DropdownMenuItem onClick={onPreview}><Eye className="h-4 w-4 mr-2" />Preview</DropdownMenuItem>{doc.status === "error" && (<><DropdownMenuSeparator /><DropdownMenuItem onClick={onRetry}><RotateCcw className="h-4 w-4 mr-2" />Retry extraction</DropdownMenuItem></>)}<DropdownMenuSeparator /><DropdownMenuItem onClick={onDelete} variant="destructive"><Trash2 className="h-4 w-4 mr-2" />Delete</DropdownMenuItem></DropdownMenuContent></DropdownMenu></div><div className="flex items-center gap-2 flex-wrap">{getStatusBadge(doc.status)}<span className="text-xs text-muted-foreground">{formatDate(doc.created_at)}</span><span className="text-xs text-muted-foreground">{doc.chunk_count} chunks</span></div>{doc.status === "error" && doc.error_message && <p className="text-sm text-destructive bg-destructive/10 p-2 rounded">{doc.error_message}</p>}</div>)}

export default DocumentsPage
