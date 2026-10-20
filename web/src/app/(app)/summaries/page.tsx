"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
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
import { Separator } from "@/components/ui/separator";
import { SvgRefreshCw, SvgFileText, SvgVolume2, SvgDownload, SvgAlertCircle } from "@/components/ui/icons";
import { toast } from "sonner";
import { ScrollArea } from "@/components/ui/scroll-area";

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
  const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
    ready: "default",
    uploaded: "secondary",
    processing: "secondary",
    error: "destructive",
  };
  return (
    <Badge variant={variants[status] || "default"} className="capitalize">
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
  generatingAudioId
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
    <Card className="mb-4">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <span className="font-medium truncate">{doc.filename}</span>
              <StatusBadge status={doc.status} />
            </div>
            <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
              <span><SvgFileText className="h-4 w-4 inline mr-1" /> {doc.chunk_count} chunks</span>
              <span>{doc.file_type}</span>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-0 space-y-4">
        {existingSummary ? (
          <>
            <div className="prose prose-sm max-w-none">
              <ScrollArea className="max-h-64">
                <p className="whitespace-pre-wrap">{existingSummary.summary_text}</p>
              </ScrollArea>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onListen(existingSummary.id)}
                disabled={isGeneratingAudio || isSummarizing}
              >
                {isGeneratingAudio ? (
                  <>
                    <SvgRefreshCw className="mr-2 h-4 w-4 animate-spin" />
                    Generating audio...
                  </>
                ) : (
                  <>
                    <SvgVolume2 className="mr-2 h-4 w-4" />
                    Listen
                  </>
                )}
              </Button>
            </div>
          </>
        ) : (
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">No summary yet</p>
            <Button
              variant="default"
              size="sm"
              onClick={() => onSummarize(doc.id)}
              disabled={isSummarizing}
            >
              {isSummarizing ? (
                <>
                  <SvgRefreshCw className="mr-2 h-4 w-4 animate-spin" />
                  Summarizing...
                </>
              ) : (
                <>
                  <SvgFileText className="mr-2 h-4 w-4" />
                  Summarize
                </>
              )}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function AudioPlayer({
  summaryId,
  audioBlob,
  engine,
  onClose
}: {
  summaryId: number;
  audioBlob: Blob;
  engine: string;
  onClose: () => void;
}) {
  const audioUrl = URL.createObjectURL(audioBlob);

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Audio Player</DialogTitle>
          <DialogDescription>
            Generated with {engine}. Click download to save the file.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 mt-4">
          <audio controls src={audioUrl} className="w-full" />
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={onClose}>
              Close
            </Button>
            <Button
              onClick={() => {
                const a = document.createElement("a");
                a.href = audioUrl;
                a.download = `summary_${summaryId}.wav`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                toast.success("Audio downloaded");
              }}
            >
              <SvgDownload className="mr-2 h-4 w-4" />
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
  onRetry
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
      <DialogContent className="max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <SvgAlertCircle className="h-5 w-5 text-destructive" />
            <DialogTitle>{title}</DialogTitle>
          </div>
          <DialogDescription>{message}</DialogDescription>
        </DialogHeader>
        <div className="flex justify-end gap-2 mt-4">
          <Button variant="outline" onClick={onClose}>
            Dismiss
          </Button>
          {onRetry && (
            <Button onClick={() => { onRetry(); onClose(); }}>
              <SvgRefreshCw className="mr-2 h-4 w-4" />
              Retry
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default function SummariesPage() {
  const queryClient = useQueryClient();
  const [summarizingDocId, setSummarizingDocId] = useState<number | null>(null);
  const [generatingAudioId, setGeneratingAudioId] = useState<number | null>(null);
  const [audioPlayer, setAudioPlayer] = useState<{ summaryId: number; audioBlob: Blob; engine: string } | null>(null);
  const [errorState, setErrorState] = useState<{ title: string; message: string; onRetry?: () => void } | null>(null);

  const { data: documents, isLoading: docsLoading, refetch: refetchDocuments } = useQuery({
    queryKey: ["documents"],
    queryFn: fetchDocuments,
  });

  const { data: summaries, isLoading: summariesLoading, refetch: refetchSummaries } = useQuery({
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
        // Fetch the actual audio file
        try {
          const { summaryAudioGet } = await import("@/lib/api");
          const audioBlob = await summaryAudioGet(variables.summaryId);
          setAudioPlayer({
            summaryId: variables.summaryId,
            audioBlob,
            engine: data.data.engine,
          });
          toast.success("Audio generated");
        } catch (err) {
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

  const handleAudioClose = () => {
    if (audioPlayer) {
      URL.revokeObjectURL(audioPlayer.audioBlob as unknown as string);
    }
    setAudioPlayer(null);
  };

  const handleErrorClose = () => {
    setErrorState(null);
  };

  const readyDocs = documents?.filter(d => d.status === "ready") || [];

  if (docsLoading || summariesLoading) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <Card>
          <CardHeader>
            <CardTitle>Document Summaries</CardTitle>
            <CardDescription>Generate and listen to summaries of your documents</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="h-24 animate-pulse bg-muted rounded-lg" />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <Card>
        <CardHeader>
          <CardTitle>Document Summaries</CardTitle>
          <CardDescription>Generate and listen to summaries of your documents</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {readyDocs.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <SvgFileText className="mx-auto h-12 w-12 mb-4 opacity-50" />
              <p className="text-lg">No processed documents yet</p>
              <p className="mt-2">Upload some files first, then come back to generate summaries.</p>
            </div>
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
        </CardContent>
      </Card>

      {audioPlayer && (
        <AudioPlayer
          summaryId={audioPlayer.summaryId}
          audioBlob={audioPlayer.audioBlob}
          engine={audioPlayer.engine}
          onClose={handleAudioClose}
        />
      )}

      <ErrorDialog
        isOpen={!!errorState}
        onClose={handleErrorClose}
        title={errorState?.title || "Error"}
        message={errorState?.message || "An unexpected error occurred"}
        onRetry={errorState?.onRetry}
      />
    </div>
  );
}