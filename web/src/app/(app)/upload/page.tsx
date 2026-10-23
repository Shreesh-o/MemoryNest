"use client";

import { useState, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useDropzone } from "react-dropzone";
import { toast } from "sonner";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  UploadCloudIcon,
  XIcon,
  FileTextIcon,
  CheckCircle2Icon,
  Loader2Icon,
  ImageIcon,
  FileIcon,
  FileTypeIcon,
  ArrowRightIcon,
  AlertCircleIcon,
} from "lucide-react";

const MAX_FILE_MB = Number(process.env.NEXT_PUBLIC_MAX_FILE_MB || "20");
const MAX_FILE_BYTES = MAX_FILE_MB * 1024 * 1024;

type IngestResult = {
  filename: string;
  status: "ready" | "duplicate" | "rejected" | "error";
  message: string;
  doc_id?: number | null;
  chunk_count: number;
};

type UploadFile = {
  file: File;
  preview: string;
  progress: number;
  status: "pending" | "uploading" | "success" | "error";
  result?: IngestResult;
  error?: string;
};

async function uploadFiles(files: File[]): Promise<IngestResult[]> {
  const formData = new FormData();
  files.forEach((f) => formData.append("files", f));

  const res = await fetch("/api/documents/upload", {
    method: "POST",
    credentials: "include",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Upload failed");
  }
  return res.json();
}

function StatusBadge({ status }: { status: string }) {
  const variants: Record<string, "success" | "secondary" | "destructive" | "outline"> = {
    ready: "success",
    duplicate: "secondary",
    rejected: "outline",
    error: "destructive",
  };
  return (
    <Badge variant={variants[status] || "outline"} className="capitalize font-medium text-xs">
      {status}
    </Badge>
  );
}

function FileTypeIconComponent({ filename }: { filename: string }) {
  const ext = (filename.split(".").pop() || "").toLowerCase();
  if (ext === "pdf") {
    return <FileTypeIcon className="size-5 text-primary" />;
  }
  if (["png", "jpg", "jpeg"].includes(ext)) {
    return <ImageIcon className="size-5 text-primary" />;
  }
  if (["docx", "txt"].includes(ext)) {
    return <FileTextIcon className="size-5 text-primary" />;
  }
  return <FileIcon className="size-5 text-primary" />;
}

function FileRow({ file, onRemove }: { file: UploadFile; onRemove: () => void }) {
  return (
    <div className="flex items-center gap-3 p-3.5 border border-border/80 rounded-xl bg-card hover:border-border transition-colors">
      <div className="flex-shrink-0 size-10 flex items-center justify-center bg-muted/60 rounded-lg">
        <FileTypeIconComponent filename={file.file.name} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-sm text-foreground truncate">{file.file.name}</p>
        <p className="text-xs text-muted-foreground font-mono mt-0.5">
          {(file.file.size / 1024).toFixed(1)} KB
        </p>
        {file.status === "uploading" && (
          <Progress value={file.progress} className="mt-2 h-1.5" />
        )}
      </div>
      <div className="flex items-center gap-2">
        {file.status === "uploading" && (
          <Loader2Icon className="size-4 animate-spin text-primary" />
        )}
        {file.status === "success" && file.result && (
          <>
            <StatusBadge status={file.result.status} />
            <span className="text-xs text-muted-foreground font-mono">{file.result.chunk_count} chunks</span>
          </>
        )}
        {file.status === "error" && (
          <Badge variant="destructive" className="gap-1">
            <AlertCircleIcon className="size-3" />
            Error
          </Badge>
        )}
        <Button
          variant="ghost"
          size="icon-xs"
          onClick={onRemove}
          disabled={file.status === "uploading"}
          className="size-7 text-muted-foreground hover:text-destructive hover:bg-destructive/10 cursor-pointer"
          title="Remove file"
        >
          <XIcon className="size-3.5" />
        </Button>
      </div>
    </div>
  );
}

function ResultRow({ result }: { result: IngestResult }) {
  return (
    <div className="flex items-center gap-3 p-3.5 border border-border/80 rounded-xl bg-card">
      <div className="flex-shrink-0 size-10 flex items-center justify-center bg-muted/60 rounded-lg">
        <FileTypeIconComponent filename={result.filename} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-sm text-foreground truncate">{result.filename}</p>
        <p className="text-xs text-muted-foreground mt-0.5">{result.message}</p>
      </div>
      <div className="flex items-center gap-2">
        <StatusBadge status={result.status} />
        {result.chunk_count > 0 && (
          <span className="text-xs text-muted-foreground font-mono">{result.chunk_count} chunks</span>
        )}
      </div>
    </div>
  );
}

export default function UploadPage() {
  useEffect(() => {
    document.title = "Upload — MemoryNest"
  }, [])
  const router = useRouter();
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [results, setResults] = useState<IngestResult[]>([]);

  const uploadMutation = useMutation({
    mutationFn: uploadFiles,
    onSuccess: (data) => {
      setResults(data);
      toast.success(`${data.length} file(s) processed`);
      setFiles([]);
    },
    onError: (err: Error) => {
      toast.error(err.message);
      setFiles((prev) =>
        prev.map((f) => (f.status === "uploading" ? { ...f, status: "error", error: err.message } : f))
      );
    },
  });

  const onDrop = (acceptedFiles: File[]) => {
    const newFiles: UploadFile[] = acceptedFiles.map((file) => ({
      file,
      preview: URL.createObjectURL(file),
      progress: 0,
      status: "pending",
    }));
    setFiles((prev) => [...prev, ...newFiles]);
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "text/plain": [".txt"],
      "image/png": [".png"],
      "image/jpeg": [".jpg", ".jpeg"],
    },
    maxSize: MAX_FILE_BYTES,
    onDropRejected: (rejectedFiles) => {
      rejectedFiles.forEach(({ file, errors }) => {
        const errorMsg = errors.map((e) => e.message).join(", ");
        toast.error(`${file.name}: ${errorMsg}`);
      });
    },
  });

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const clearAll = () => {
    setFiles([]);
  };

  const handleUpload = () => {
    if (files.length === 0) return;
    setFiles((prev) => prev.map((f) => ({ ...f, status: "uploading", progress: 50 })));
    uploadMutation.mutate(files.map((f) => f.file));
  };

  const isUploading = uploadMutation.isPending;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-border/60">
        <div>
          <h1 className="font-heading text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
            Upload Documents
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Drag and drop files to extract text, generate embeddings, and schedule reminders
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => router.push("/documents")}
          className="text-xs h-8 gap-1.5 cursor-pointer self-start sm:self-auto"
        >
          <span>View All Documents</span>
          <ArrowRightIcon className="size-3.5" />
        </Button>
      </div>

      {/* Dropzone Card */}
      <Card className="border border-border/80">
        <CardContent className="p-6">
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-xl p-8 sm:p-12 text-center transition-all cursor-pointer ${
              isDragActive
                ? "border-primary bg-primary/5"
                : "border-border/80 hover:border-border hover:bg-muted/20"
            }`}
          >
            <input {...getInputProps()} />
            <div className="flex flex-col items-center justify-center space-y-3">
              <div className="size-14 rounded-2xl bg-primary/10 text-primary flex items-center justify-center">
                <UploadCloudIcon className="size-7" />
              </div>
              <div className="space-y-1">
                <p className="font-heading text-base font-semibold text-foreground">
                  {isDragActive ? "Drop the files here" : "Drag & drop documents here, or click to browse"}
                </p>
                <p className="text-xs text-muted-foreground">
                  Supported formats: PDF, DOCX, TXT, PNG, JPG (OCR enabled)
                </p>
                <p className="text-xs text-muted-foreground font-mono">
                  Maximum file size: {MAX_FILE_MB} MB
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Selected Files Queue */}
      {files.length > 0 && (
        <Card className="border border-border/80">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle className="text-base font-semibold">Queue ({files.length} file{files.length === 1 ? "" : "s"})</CardTitle>
              <CardDescription className="text-xs">Ready for processing into the knowledge vault</CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={clearAll}
                disabled={isUploading}
                className="text-xs h-8 cursor-pointer text-muted-foreground hover:text-destructive"
              >
                Clear Queue
              </Button>
              <Button
                size="sm"
                onClick={handleUpload}
                disabled={isUploading}
                className="text-xs h-8 gap-1.5 cursor-pointer font-medium"
              >
                {isUploading ? (
                  <>
                    <Loader2Icon className="size-3.5 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <UploadCloudIcon className="size-3.5" />
                    Upload & Process
                  </>
                )}
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-2 pt-0">
            {files.map((file, i) => (
              <FileRow key={i} file={file} onRemove={() => removeFile(i)} />
            ))}
          </CardContent>
        </Card>
      )}

      {/* Ingestion Results */}
      {results.length > 0 && (
        <Card className="border border-border/80">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <CheckCircle2Icon className="size-4.5 text-emerald-600 dark:text-emerald-400" />
                Processing Results
              </CardTitle>
              <CardDescription className="text-xs">Status of indexed documents</CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => router.push("/documents")}
              className="text-xs h-8 gap-1.5 cursor-pointer"
            >
              <span>Go to Documents</span>
              <ArrowRightIcon className="size-3.5" />
            </Button>
          </CardHeader>
          <CardContent className="space-y-2 pt-0">
            {results.map((result, i) => (
              <ResultRow key={i} result={result} />
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
