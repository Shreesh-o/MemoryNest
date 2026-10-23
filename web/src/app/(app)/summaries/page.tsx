"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import {
  Card,
  CardHeader,
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
  FileTextIcon,
  Volume2Icon,
  DownloadIcon,
  AlertCircleIcon,
  RefreshCwIcon,
  SparklesIcon,
  AudioLinesIcon,
  LayersIcon,
} from "lucide-react";
import { toast } from "sonner";
import { ScrollArea } from "@/components/ui/scroll-area";
import { EmptyState } from "@/components/ui/empty-state";
import Link from "next/link";

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

type Summary = {
  id: number;
  document_id: number;
  user_id: number;
  summary_text: string;
  created_at?: string | null;
};

async function fetchDocuments(): Promise<Document[]> {
  const res = await fetch("/api/documents", { credentials: "include" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to fetch documents");
  }
  return res.json();
}

async function fetchSummaries(): Promise<Summary[]> {
  const res = await fetch("/api/summaries", { credentials: "include" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to fetch summaries");
  }
  return res.json();
}

function StatusBadge({ status }: { status: string }) {
  const variants: Record<string, "success" | "secondary" | "destructive" | "warning" | "outline"> = {
    ready: "success",
    uploaded: "secondary",
    processing: "warning",
    error: "destructive",
  };
  return (
    <Badge variant={variants[status] || "outline"} className="capitalize font-mono text-2xs">
      {status}
    </Badge>
  );
}

function DocumentCard({
  doc,
  existingSummary,
  onSummarize,
  onListen,
  summarizingDocId,
  generatingAudioId,
}: {
  doc: Document;
  existingSummary: Summary | null;
  onSummarize: (docId: number) => void;
  onListen: (summaryId: number) => void;
  summarizingDocId: number | null;
  generatingAudioId: number | null;
}) {
  const isSummarizing = summarizingDocId === doc.id;
  const isGeneratingAudio = generatingAudioId === existingSummary?.id;

  return (
    <Card className="border border-border/80 shadow-xs hover:border-border transition-colors">
      <CardHeader className="p-4 sm:p-5 pb-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span className="font-semibold text-sm sm:text-base text-foreground truncate">{doc.filename}</span>
              <StatusBadge status={doc.status} />
            </div>
            <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1 font-mono">
                <LayersIcon className="size-3.5 text-muted-foreground" />
                {doc.chunk_count} chunk{doc.chunk_count !== 1 ? "s" : ""}
              </span>
              <span className="font-mono uppercase text-2xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                {doc.file_type}
              </span>
            </div>
          </div>
          <div className="shrink-0 flex items-center gap-2">
            {existingSummary ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onListen(existingSummary.id)}
                disabled={isGeneratingAudio || isSummarizing}
                className="h-8 text-xs gap-1.5 cursor-pointer shadow-2xs"
              >
                {isGeneratingAudio ? (
                  <>
                    <RefreshCwIcon className="size-3.5 animate-spin text-primary" />
                    Generating audio...
                  </>
                ) : (
                  <>
                    <Volume2Icon className="size-3.5 text-primary" />
                    Listen
                  </>
                )}
              </Button>
            ) : (
              <Button
                variant="default"
                size="sm"
                onClick={() => onSummarize(doc.id)}
                disabled={isSummarizing}
                className="h-8 text-xs gap-1.5 cursor-pointer shadow-2xs"
              >
                {isSummarizing ? (
                  <>
                    <RefreshCwIcon className="size-3.5 animate-spin" />
                    Summarizing...
                  </>
                ) : (
                  <>
                    <SparklesIcon className="size-3.5" />
                    Summarize
                  </>
                )}
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-4 sm:p-5 pt-0">
        {existingSummary ? (
          <div className="rounded-xl border border-border/60 bg-muted/20 p-3.5 sm:p-4 mt-2">
            <ScrollArea className="max-h-60">
              <p className="text-xs sm:text-sm text-foreground/90 whitespace-pre-wrap leading-relaxed font-sans">
                {existingSummary.summary_text}
              </p>
            </ScrollArea>
          </div>
        ) : (
          <div className="flex items-center justify-between py-2 text-xs text-muted-foreground">
            <span>No summary generated yet.</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function formatVoiceLabel(engine: string): string {
  const norm = (engine || "").toLowerCase();
  if (norm.includes("edge")) {
    return "Voice: Edge (online)";
  }
  if (norm.includes("piper")) {
    return "Voice: Piper (offline)";
  }
  if (norm.includes("espeak")) {
    return "Voice: espeak-ng (offline)";
  }
  if (norm.includes("pyttsx")) {
    return "Voice: pyttsx3 (offline)";
  }
  return `Voice: ${engine}`;
}

function AudioPlayer({
  summaryId,
  audioBlob,
  engine,
  onClose,
}: {
  summaryId: number;
  audioBlob: Blob;
  engine: string;
  onClose: () => void;
}) {
  const audioUrl = URL.createObjectURL(audioBlob);
  const ext = audioBlob.type === "audio/mpeg" ? "mp3" : "wav";

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-md p-6">
        <DialogHeader>
          <div className="flex items-center gap-2 mb-1">
            <div className="size-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
              <AudioLinesIcon className="size-4" />
            </div>
            <DialogTitle className="text-base font-semibold">Audio Player</DialogTitle>
          </div>
          <DialogDescription className="text-xs text-muted-foreground">
            Listen to your document summary audio. Download to keep the audio offline.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 mt-3">
          <div className="rounded-xl border border-border/80 bg-muted/40 p-3 flex flex-col gap-2">
            <audio controls src={audioUrl} className="w-full h-10">
              Your browser does not support the audio element.
            </audio>
            <div className="flex items-center justify-between text-2xs text-muted-foreground pt-1">
              <span className="font-mono font-medium">{formatVoiceLabel(engine)}</span>
              <span className="uppercase font-mono">{ext}</span>
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <Button variant="outline" size="sm" onClick={onClose} className="h-8 text-xs cursor-pointer">
              Close
            </Button>
            <Button
              size="sm"
              className="h-8 text-xs gap-1.5 cursor-pointer"
              onClick={() => {
                const a = document.createElement("a");
                a.href = audioUrl;
                a.download = `summary_${summaryId}.${ext}`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                toast.success("Audio downloaded");
              }}
            >
              <DownloadIcon className="size-3.5" />
              Download
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function ErrorDialog({
  isOpen,
  onClose,
  title,
  message,
  onRetry,
}: {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  message: string;
  onRetry?: () => void;
}) {
  if (!isOpen) return null;

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-md p-6">
        <DialogHeader>
          <div className="flex items-center gap-2 mb-1">
            <AlertCircleIcon className="size-5 text-destructive shrink-0" />
            <DialogTitle className="text-base font-semibold text-destructive">{title}</DialogTitle>
          </div>
          <DialogDescription className="text-xs text-muted-foreground leading-relaxed">
            {message}
          </DialogDescription>
        </DialogHeader>
        <div className="flex justify-end gap-2 mt-4 pt-2 border-t border-border/60">
          <Button variant="outline" size="sm" onClick={onClose} className="h-8 text-xs cursor-pointer">
            Dismiss
          </Button>
          {onRetry && (
            <Button
              size="sm"
              onClick={() => {
                onRetry();
                onClose();
              }}
              className="h-8 text-xs gap-1.5 cursor-pointer"
            >
              <RefreshCwIcon className="size-3.5" />
              Retry
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default function SummariesPage() {
  useEffect(() => {
    document.title = "Summaries — MemoryNest";
  }, []);

  const queryClient = useQueryClient();
  const [summarizingDocId, setSummarizingDocId] = useState<number | null>(null);
  const [generatingAudioId, setGeneratingAudioId] = useState<number | null>(null);
  const [audioPlayer, setAudioPlayer] = useState<{ summaryId: number; audioBlob: Blob; engine: string } | null>(null);
  const [errorState, setErrorState] = useState<{ title: string; message: string; onRetry?: () => void } | null>(null);

  const { data: documents, isLoading: docsLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: fetchDocuments,
  });

  const { data: summaries, isLoading: summariesLoading } = useQuery({
    queryKey: ["summaries"],
    queryFn: fetchSummaries,
  });

  const summarizeMutation = useMutation({
    mutationFn: ({ docId }: { docId: number }) => (import("@/lib/api")).then(m => m.summaryCreate(docId)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["summaries"] });
      toast.success("Summary generated");
      setSummarizingDocId(null);
    },
    onError: (err: Error) => {
      if (err.message.includes("503")) {
        setErrorState({
          title: "LLM Service Unavailable",
          message: err.message || "The language model service is currently unavailable. Please try again later.",
          onRetry: () => {
            if (summarizingDocId) {
              summarizeMutation.mutate({ docId: summarizingDocId });
            }
          },
        });
      } else {
        toast.error(err.message);
      }
      setSummarizingDocId(null);
    },
  });

  const audioCreateMutation = useMutation({
    mutationFn: ({ summaryId }: { summaryId: number }) => (import("@/lib/api")).then(m => m.summaryAudioCreate(summaryId)),
    onSuccess: async (data, variables) => {
      if (data.ok && data.data) {
        try {
          const { summaryAudioGet } = await import("@/lib/api");
          const audioBlob = await summaryAudioGet(variables.summaryId);
          setAudioPlayer({
            summaryId: variables.summaryId,
            audioBlob,
            engine: data.data.engine,
          });
          toast.success("Audio generated");
        } catch {
          toast.error("Failed to load audio");
        }
      }
      setGeneratingAudioId(null);
    },
    onError: (err: Error, variables) => {
      if (err.message.includes("502")) {
        setErrorState({
          title: "TTS Generation Failed",
          message: err.message || "Text-to-speech generation failed. Please try again.",
          onRetry: () => audioCreateMutation.mutate({ summaryId: variables.summaryId }),
        });
      } else {
        toast.error(err.message);
      }
      setGeneratingAudioId(null);
    },
  });

  const handleSummarize = (docId: number) => {
    setSummarizingDocId(docId);
    summarizeMutation.mutate({ docId });
  };

  const handleListen = (summaryId: number) => {
    setGeneratingAudioId(summaryId);
    audioCreateMutation.mutate({ summaryId });
  };

  const readyDocs = documents?.filter(d => d.status === "ready") || [];

  if (docsLoading || summariesLoading) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">Document Summaries</h1>
          <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">
            Generate and listen to executive summaries of your knowledge base.
          </p>
        </div>
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Card key={i} className="border border-border/80 p-5">
              <div className="h-6 w-1/3 bg-muted animate-pulse rounded-md mb-3" />
              <div className="h-4 w-1/2 bg-muted/60 animate-pulse rounded-md mb-4" />
              <div className="h-20 w-full bg-muted/40 animate-pulse rounded-xl" />
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">Document Summaries</h1>
        <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">
          Generate and listen to executive summaries of your knowledge base.
        </p>
      </div>

      {readyDocs.length === 0 ? (
        <EmptyState
          icon={<FileTextIcon className="size-6" />}
          title="No processed documents yet"
          description="Upload some files first, then return here to generate AI summaries and audio readings."
          action={
            <Link href="/upload">
              <Button size="sm" className="cursor-pointer gap-1.5">
                Upload documents
              </Button>
            </Link>
          }
        />
      ) : (
        <div className="space-y-4">
          {readyDocs.map((doc) => {
            const existingSummary = summaries?.find(s => s.document_id === doc.id) || null;
            return (
              <DocumentCard
                key={doc.id}
                doc={doc}
                existingSummary={existingSummary}
                onSummarize={handleSummarize}
                onListen={handleListen}
                summarizingDocId={summarizingDocId}
                generatingAudioId={generatingAudioId}
              />
            );
          })}
        </div>
      )}

      {audioPlayer && (
        <AudioPlayer
          summaryId={audioPlayer.summaryId}
          audioBlob={audioPlayer.audioBlob}
          engine={audioPlayer.engine}
          onClose={() => setAudioPlayer(null)}
        />
      )}

      <ErrorDialog
        isOpen={!!errorState}
        onClose={() => setErrorState(null)}
        title={errorState?.title || "Error"}
        message={errorState?.message || "An unexpected error occurred"}
        onRetry={errorState?.onRetry}
      />
    </div>
  );
}
