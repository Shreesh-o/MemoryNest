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
import { Separator } from "@/components/ui/separator";
import { SvgUpload, SvgX, SvgFileText, SvgCheckCircle, SvgLoader2, SvgImage, SvgFile } from "@/components/ui/icons";

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
  const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
    ready: "default",
    duplicate: "secondary",
    rejected: "outline",
    error: "destructive",
  };
  return (
    <Badge variant={variants[status] || "default"} className="capitalize">
      {status}
    </Badge>
  );
}

function FileIcon({ type }: { type: string }) {
  const ext = type.toLowerCase();
  if (ext === "pdf") {
    return (
      <svg className="h-5 w-5 text-red-500" fill="currentColor" viewBox="0 0 24 24">
        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
        <path fill="#fff" d="M14 2v6h6" />
      </svg>
    );
  }
  if (ext === "docx") {
    return (
      <svg className="h-5 w-5 text-blue-600" fill="currentColor" viewBox="0 0 24 24">
        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
        <path fill="#fff" d="M14 2v6h6" />
        <text x="12" y="17" fontSize="8" textAnchor="middle" fill="#2563eb">DOCX</text>
      </svg>
    );
  }
  if (ext === "png" || ext === "jpg" || ext === "jpeg") {
    return <SvgImage className="h-5 w-5 text-green-600" />;
  }
  if (ext === "txt") {
    return <SvgFileText className="h-5 w-5 text-gray-400" />;
  }
  return <SvgFile className="h-5 w-5 text-gray-400" />;
}

function FileRow({ file, onRemove }: { file: UploadFile; onRemove: () => void }) {
  return (
    <div className="flex items-center gap-3 p-3 border rounded-lg bg-card">
      <div className="flex-shrink-0 w-10 h-10 flex items-center justify-center bg-muted rounded">
        <FileIcon type={file.file.name.split(".").pop() || ""} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium truncate">{file.file.name}</p>
        <p className="text-xs text-muted-foreground">
          {(file.file.size / 1024).toFixed(1)} KB
        </p>
        {file.status === "uploading" && (
          <Progress value={file.progress} className="mt-2 h-1.5" />
        )}
      </div>
      <div className="flex items-center gap-2">
        {file.status === "uploading" && (
          <SvgLoader2 className="h-5 w-5 animate-spin text-blue-600" />
        )}
        {file.status === "success" && file.result && (
          <>
            <StatusBadge status={file.result.status} />
            <span className="text-xs text-muted-foreground">{file.result.chunk_count} chunks</span>
          </>
        )}
        {file.status === "error" && (
          <Badge variant="destructive">Error</Badge>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={onRemove}
          disabled={file.status === "uploading"}
          className="text-red-600 hover:bg-red-50"
        >
          <SvgX className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

function ResultRow({ result }: { result: IngestResult }) {
  return (
    <div className="flex items-center gap-3 p-3 border rounded-lg bg-card">
      <div className="flex-shrink-0 w-10 h-10 flex items-center justify-center bg-muted rounded">
        <FileIcon type={result.filename.split(".").pop() || ""} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium truncate">{result.filename}</p>
        <p className="text-xs text-muted-foreground">{result.message}</p>
      </div>
      <div className="flex items-center gap-2">
        <StatusBadge status={result.status} />
        {result.chunk_count > 0 && (
          <span className="text-xs text-muted-foreground">{result.chunk_count} chunks</span>
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
    noClick: false,
    noKeyboard: false,
  });

  const handleUpload = () => {
    const pendingFiles = files.filter((f) => f.status === "pending");
    if (pendingFiles.length === 0) return;

    setFiles((prev) =>
      prev.map((f) => (f.status === "pending" ? { ...f, status: "uploading" } : f))
    );

    const interval = setInterval(() => {
      setFiles((prev) =>
        prev.map((f) => {
          if (f.status === "uploading" && f.progress < 90) {
            return { ...f, progress: f.progress + 10 };
          }
          return f;
        })
      );
    }, 100);

    uploadMutation.mutate(pendingFiles.map((f) => f.file), {
      onSettled: () => clearInterval(interval),
    });
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const retryFailed = () => {
    const failedFiles = files.filter((f) => f.status === "error");
    if (failedFiles.length === 0) return;

    setFiles((prev) =>
      prev.map((f) => (f.status === "error" ? { ...f, status: "pending", error: undefined } : f))
    );
  };

  const goToDocuments = () => {
    router.push("/documents");
    router.refresh();
  };

  const hasPending = files.some((f) => f.status === "pending");
  const hasUploading = files.some((f) => f.status === "uploading");
  const hasResults = results.length > 0;

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <Card>
        <CardHeader>
          <CardTitle>Upload Documents</CardTitle>
          <CardDescription>
            PDF, DOCX, TXT, PNG, JPG up to {MAX_FILE_MB} MB. Scanned files are read with OCR and can take a while.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Drop Zone */}
          <div
            {...getRootProps()}
            className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              isDragActive
                ? "border-primary bg-primary/5"
                : "border-muted-foreground/25 hover:border-primary/50"
            }`}
            role="button"
            tabIndex={0}
          >
            <input {...getInputProps()} />
            <SvgUpload className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-lg font-medium">{isDragActive ? "Drop files here..." : "Drag & drop files here, or click to select"}</p>
            <p className="text-sm text-muted-foreground mt-1">PDF, DOCX, TXT, PNG, JPG • Max {MAX_FILE_MB} MB each</p>
          </div>

          {/* File Queue */}
          {files.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="font-medium">Files to Upload ({files.filter(f => f.status === "pending").length} pending)</h3>
                {files.some(f => f.status === "error") && (
                  <Button variant="ghost" size="sm" onClick={retryFailed}>
                    Retry Failed
                  </Button>
                )}
              </div>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {files.map((file, index) => (
                  <FileRow key={index} file={file} onRemove={() => removeFile(index)} />
                ))}
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setFiles([])} disabled={hasUploading}>
                  Clear All
                </Button>
                <Button onClick={handleUpload} disabled={!hasPending || hasUploading}>
                  {hasUploading ? (
                    <>
                      <SvgLoader2 className="mr-2 h-4 w-4 animate-spin" />
                      Uploading...
                    </>
                  ) : (
                    <>
                      <SvgUpload className="mr-2 h-4 w-4" />
                      Upload {files.filter(f => f.status === "pending").length} File(s)
                    </>
                  )}
                </Button>
              </div>
            </div>
          )}

          {/* Results */}
          {hasResults && (
            <div className="space-y-3 pt-4 border-t">
              <Separator />
              <h3 className="font-medium">Upload Results</h3>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {results.map((result, index) => (
                  <ResultRow key={index} result={result} />
                ))}
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Button variant="outline" onClick={() => { setResults([]); setFiles([]); }}>
                  Upload More
                </Button>
                <Button onClick={goToDocuments}>
                  <SvgCheckCircle className="mr-2 h-4 w-4" />
                  View Documents
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}