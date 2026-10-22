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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { SvgRefreshCw, SvgCalendar, SvgDownload, SvgSearch, SvgX, SvgCheck, SvgClock } from "@/components/ui/icons";
import { toast } from "sonner";

type Event = {
  id: number;
  user_id: number;
  event_text: string;
  document_id?: number | null;
  event_date?: string | null;
  raw_date?: string | null;
  status: string;
  created_at?: string | null;
};

type Reminder = {
  id: number;
  user_id: number;
  event_id: number;
  remind_at: string;
  channel: string;
  subject?: string | null;
  body?: string | null;
  status: string;
  sent_at?: string | null;
  created_at?: string | null;
};

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

async function fetchEvents(status?: string): Promise<Event[]> {
  const path = status ? `/api/events?status=${status}` : "/api/events";
  const res = await fetch(path, { credentials: "include" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to fetch events");
  }
  return res.json();
}

async function fetchReminders(): Promise<Reminder[]> {
  const res = await fetch("/api/reminders", { credentials: "include" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to fetch reminders");
  }
  return res.json();
}

async function fetchDocuments(): Promise<Document[]> {
  const res = await fetch("/api/documents", { credentials: "include" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to fetch documents");
  }
  return res.json();
}

function StatusBadge({ status }: { status: string }) {
  const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
    pending: "secondary",
    confirmed: "default",
    skipped: "outline",
    scheduled: "default",
    sent: "secondary",
    failed: "destructive",
    cancelled: "outline",
  };
  return (
    <Badge variant={variants[status] || "default"} className="capitalize">
      {status}
    </Badge>
  );
}

function EventCard({ event, onConfirm, onDiscard, onExtract, extractingDocId }: {
  event: Event;
  onConfirm: (id: number) => void;
  onDiscard: (id: number) => void;
  onExtract: (docId: number) => void;
  extractingDocId: number | null;
}) {
  return (
    <Card className="mb-3">
      <CardContent className="pt-4 pb-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <span className="font-medium truncate">{event.event_text}</span>
              <StatusBadge status={event.status} />
            </div>
            <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
              {event.raw_date && (
                <span><SvgClock className="h-4 w-4 inline mr-1" /> Raw: {event.raw_date}</span>
              )}
              {event.event_date && (
                <span><SvgCalendar className="h-4 w-4 inline mr-1" /> Date: {event.event_date}</span>
              )}
              {event.document_id && (
                <span><SvgCalendar className="h-4 w-4 inline mr-1" /> Doc ID: {event.document_id}</span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            {event.status === "pending" && (
              <>
                <Button variant="outline" size="sm" onClick={() => onConfirm(event.id)} disabled={extractingDocId !== null}>
                  <SvgCheck className="mr-2 h-4 w-4" /> Confirm
                </Button>
                <Button variant="ghost" size="sm" onClick={() => onDiscard(event.id)} className="text-red-600 hover:bg-red-50" disabled={extractingDocId !== null}>
                  <SvgX className="mr-1 h-4 w-4" /> Discard
                </Button>
              </>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ReminderCard({ reminder, onSendNow, onCancel, sendingReminderId, cancellingReminderId }: {
  reminder: Reminder;
  onSendNow: (id: number) => void;
  onCancel: (id: number) => void;
  sendingReminderId: number | null;
  cancellingReminderId: number | null;
}) {
  return (
    <Card className="mb-3">
      <CardContent className="pt-4 pb-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <span className="font-medium truncate">{reminder.subject}</span>
              <StatusBadge status={reminder.status} />
            </div>
            <p className="text-sm text-muted-foreground mb-2">{reminder.body}</p>
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <span><SvgClock className="h-4 w-4 inline mr-1" /> {formatDate(reminder.remind_at)}</span>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            {reminder.status === "scheduled" && (
              <>
                <Button variant="outline" size="sm" onClick={() => onSendNow(reminder.id)} disabled={sendingReminderId !== null || cancellingReminderId !== null}>
                  <SvgClock className="mr-2 h-4 w-4" /> Send now
                </Button>
                <Button variant="ghost" size="sm" onClick={() => onCancel(reminder.id)} className="text-red-600 hover:bg-red-50" disabled={sendingReminderId !== null || cancellingReminderId !== null}>
                  <SvgX className="mr-1 h-4 w-4" /> Cancel reminder
                </Button>
              </>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ExtractDialog({ open, onOpenChange, onExtract, extractingDocId, documents }: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onExtract: (docId: number) => void;
  extractingDocId: number | null;
  documents: Document[];
}) {
  const readyDocs = documents.filter(d => d.status === "ready");

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Extract Events from Document</DialogTitle>
          <DialogDescription>Select a document to extract events from.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 mt-4">
          <select
            className="w-full px-3 py-2 border rounded-md"
            disabled={extractingDocId !== null}
            onChange={(e) => onExtract(Number(e.target.value))}
            value={extractingDocId || ""}
          >
            <option value="">Select a document</option>
            {readyDocs.map((doc) => (
              <option key={doc.id} value={String(doc.id)}>
                {doc.filename} ({doc.file_type})
              </option>
            ))}
          </select>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)} disabled={extractingDocId !== null}>
              Cancel
            </Button>
            <Button onClick={() => onOpenChange(false)} disabled={extractingDocId === null}>
              {extractingDocId !== null ? (
                <>
                  <SvgRefreshCw className="mr-2 h-4 w-4 animate-spin" />
                  Extracting...
                </>
              ) : (
                <>
                  <SvgSearch className="mr-2 h-4 w-4" />
                  Extract
                </>
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function ConfirmDialog({ open, onOpenChange, onConfirm, remindingAt }: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (remindAt?: string) => void;
  remindingAt?: string;
}) {
  const [remindAt, setRemindAt] = useState(remindingAt || "");

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Confirm Event</DialogTitle>
          <DialogDescription>Set reminder time (optional). Defaults to event date at 09:00 or today at 09:00.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 mt-4">
          <input
            type="datetime-local"
            value={remindAt}
            onChange={(e) => setRemindAt(e.target.value)}
            className="w-full px-3 py-2 border rounded-md"
            placeholder="YYYY-MM-DDTHH:MM"
          />
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button onClick={() => { onConfirm(remindAt || undefined); onOpenChange(false); }}>
              Confirm
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function CancelReminderDialog({
  open,
  onOpenChange,
  onConfirm,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Cancel reminder</DialogTitle>
          <DialogDescription>
            Cancel this reminder? The event goes back to Pending.
          </DialogDescription>
        </DialogHeader>
        <div className="flex justify-end gap-2 mt-4">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Keep reminder
          </Button>
          <Button
            variant="destructive"
            onClick={() => {
              onConfirm();
              onOpenChange(false);
            }}
          >
            Cancel reminder
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function DiscardEventDialog({
  open,
  onOpenChange,
  onConfirm,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Discard event</DialogTitle>
          <DialogDescription>
            Are you sure you want to discard this event? This action cannot be undone.
          </DialogDescription>
        </DialogHeader>
        <div className="flex justify-end gap-2 mt-4">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Keep event
          </Button>
          <Button
            variant="destructive"
            onClick={() => {
              onConfirm();
              onOpenChange(false);
            }}
          >
            Discard
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function DownloadCalendarButton({ eventIds }: { eventIds?: number[] }) {
  const [downloading, setDownloading] = useState(false);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const blob = await (await import("@/lib/api")).calendarIcs(eventIds);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "memorynest.ics";
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success("Calendar downloaded");
    } catch (err) {
      toast.error("Failed to download calendar");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <Button variant="outline" size="sm" onClick={handleDownload} disabled={downloading}>
      {downloading ? (
        <>
          <SvgRefreshCw className="mr-2 h-4 w-4 animate-spin" />
          Downloading...
        </>
      ) : (
        <>
          <SvgDownload className="mr-2 h-4 w-4" />
          Download calendar (.ics)
        </>
      )}
    </Button>
  );
}

export default function RemindersPage() {
  useEffect(() => {
    document.title = "Reminders — MemoryNest"
  }, [])
  const queryClient = useQueryClient();
  const [extractDialogOpen, setExtractDialogOpen] = useState(false);
  const [extractingDocId, setExtractingDocId] = useState<number | null>(null);
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [confirmingEventId, setConfirmingEventId] = useState<number | null>(null);
  const [confirmRemindAt, setConfirmRemindAt] = useState<string>("");
  const [sendingReminderId, setSendingReminderId] = useState<number | null>(null);
  const [cancellingReminderId, setCancellingReminderId] = useState<number | null>(null);
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [discardingEventId, setDiscardingEventId] = useState<number | null>(null);
  const [discardDialogOpen, setDiscardDialogOpen] = useState(false);

  const { data: health } = useQuery<{ email_configured?: boolean }>({
    queryKey: ["health"],
    queryFn: async () => {
      const res = await fetch("/api/health");
      if (!res.ok) return { email_configured: false };
      return res.json();
    },
  });

  const { data: pendingEvents, isLoading: pendingLoading, refetch: refetchPending } = useQuery({
    queryKey: ["events", "pending"],
    queryFn: () => fetchEvents("pending"),
  });

  const { data: scheduledReminders, isLoading: scheduledLoading, refetch: refetchScheduled } = useQuery({
    queryKey: ["reminders", "scheduled"],
    queryFn: fetchReminders,
  });

  const { data: allEvents, isLoading: allEventsLoading } = useQuery({
    queryKey: ["events", "all"],
    queryFn: () => fetchEvents(),
  });

  const { data: documents, isLoading: docsLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: fetchDocuments,
  });

  const extractMutation = useMutation({
    mutationFn: ({ docId }: { docId: number }) => (import("@/lib/api")).then(m => m.eventsExtract(docId)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["events", "pending"] });
      toast.success("Events extracted");
      setExtractingDocId(null);
      setExtractDialogOpen(false);
    },
    onError: (err: Error) => {
      toast.error(err.message);
      setExtractingDocId(null);
    },
  });

  const confirmMutation = useMutation({
    mutationFn: ({ eventId, remindAt }: { eventId: number; remindAt?: string }) =>
      (import("@/lib/api")).then(m => m.eventsConfirm(eventId, remindAt)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["events", "pending"] });
      queryClient.invalidateQueries({ queryKey: ["reminders", "scheduled"] });
      toast.success("Event confirmed");
      setConfirmDialogOpen(false);
      setConfirmingEventId(null);
      setConfirmRemindAt("");
    },
    onError: (err: Error) => {
      toast.error(err.message);
    },
  });

  const discardMutation = useMutation({
    mutationFn: (eventId: number) => (import("@/lib/api")).then(m => m.eventsDiscard(eventId)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["events"] });
      toast.success("Event discarded");
      setDiscardingEventId(null);
    },
    onError: (err: Error) => {
      toast.error(err.message);
      setDiscardingEventId(null);
    },
  });

  const sendNowMutation = useMutation({
    mutationFn: (reminderId: number) => (import("@/lib/api")).then(m => m.remindersCheck()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reminders", "scheduled"] });
      toast.success("Reminder sent");
      setSendingReminderId(null);
    },
    onError: (err: Error) => {
      toast.error(err.message);
      setSendingReminderId(null);
    },
  });

  const cancelMutation = useMutation({
    mutationFn: (reminderId: number) => (import("@/lib/api")).then(m => m.remindersCancel(reminderId)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reminders"] });
      queryClient.invalidateQueries({ queryKey: ["events"] });
      toast.success("Reminder cancelled");
      setCancellingReminderId(null);
    },
    onError: (err: Error) => {
      toast.error(err.message);
      setCancellingReminderId(null);
    },
  });

  const checkDueMutation = useMutation({
    mutationFn: () => (import("@/lib/api")).then(m => m.remindersCheck()),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["reminders"] });
      const res = data.data;
      if (!res.configured) {
        toast.info(
          res.errors?.[0] ||
            "Email is not set up. Add EMAIL_USERNAME and EMAIL_APP_PASSWORD to the .env file."
        );
      } else {
        const firstErr = res.errors && res.errors.length > 0 ? `: ${res.errors[0]}` : "";
        const msg = `Sent ${res.sent}, failed ${res.failed}${firstErr}`;
        if (res.failed > 0) {
          toast.error(msg);
        } else {
          toast.success(msg);
        }
      }
    },
    onError: (err: Error) => {
      toast.error(err.message);
    },
  });

  const handleExtract = (docId: number) => {
    setExtractingDocId(docId);
    extractMutation.mutate({ docId });
  };

  const handleConfirm = (eventId: number) => {
    setConfirmingEventId(eventId);
    setConfirmDialogOpen(true);
  };

  const handleConfirmSubmit = (remindAt?: string) => {
    if (confirmingEventId !== null) {
      confirmMutation.mutate({ eventId: confirmingEventId, remindAt });
    }
  };

  const handleDiscard = (eventId: number) => {
    setDiscardingEventId(eventId);
    setDiscardDialogOpen(true);
  };

  const handleDiscardConfirm = () => {
    if (discardingEventId !== null) {
      discardMutation.mutate(discardingEventId);
    }
  };

  const handleSendNow = (reminderId: number) => {
    setSendingReminderId(reminderId);
    sendNowMutation.mutate(reminderId);
  };

  const handleCancel = (reminderId: number) => {
    setCancellingReminderId(reminderId);
    setCancelDialogOpen(true);
  };

  const handleCancelConfirm = () => {
    if (cancellingReminderId !== null) {
      cancelMutation.mutate(cancellingReminderId);
    }
  };

  const pendingEventsData = pendingEvents || [];
  const scheduledRemindersData = scheduledReminders || [];
  const allEventsData = allEvents || [];

  if (pendingLoading || scheduledLoading || allEventsLoading || docsLoading) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <Card>
          <CardHeader>
            <CardTitle>Reminders & Events</CardTitle>
            <CardDescription>Manage extracted events and reminders</CardDescription>
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
          <CardTitle>Reminders & Events</CardTitle>
          <CardDescription>Manage extracted events and reminders</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <Tabs defaultValue="pending" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="pending">Pending ({pendingEventsData.filter(e => e.status === "pending").length})</TabsTrigger>
              <TabsTrigger value="scheduled">Scheduled ({scheduledRemindersData.filter(r => r.status === "scheduled").length})</TabsTrigger>
              <TabsTrigger value="all">All Events ({allEventsData.length})</TabsTrigger>
            </TabsList>

            <TabsContent value="pending" className="mt-4 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-medium">Events awaiting confirmation</h3>
                <Button variant="outline" size="sm" onClick={() => setExtractDialogOpen(true)} disabled={extractingDocId !== null}>
                  <SvgSearch className="mr-2 h-4 w-4" /> Find dates in a document
                </Button>
              </div>

              {pendingEventsData.filter(e => e.status === "pending").length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <SvgCalendar className="mx-auto h-12 w-12 mb-4 opacity-50" />
                  <p>No pending events. Extract events from a document to get started.</p>
                </div>
              ) : (
                <>
                  {pendingEventsData.filter(e => e.status === "pending").map((event) => (
                    <EventCard
                      key={event.id}
                      event={event}
                      onConfirm={handleConfirm}
                      onDiscard={handleDiscard}
                      onExtract={handleExtract}
                      extractingDocId={extractingDocId}
                    />
                  ))}
                  <Separator />
                  <div className="flex justify-end">
                    <DownloadCalendarButton
                      eventIds={pendingEventsData.filter(e => e.status === "confirmed").map(e => e.id)}
                    />
                  </div>
                </>
              )}
            </TabsContent>

            <TabsContent value="scheduled" className="mt-4 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-medium">Scheduled reminders</h3>
                <div className="flex flex-col items-end gap-1">
                  <Button variant="outline" size="sm" onClick={() => checkDueMutation.mutate()} disabled={checkDueMutation.isPending}>
                    <SvgRefreshCw className={`mr-2 h-4 w-4 ${checkDueMutation.isPending ? "animate-spin" : ""}`} />
                    Send due reminders
                  </Button>
                  {health && health.email_configured === false && (
                    <p className="text-xs text-muted-foreground">
                      Email reminders are off. The calendar download still works.
                    </p>
                  )}
                </div>
              </div>

              {scheduledRemindersData.filter(r => r.status === "scheduled").length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <SvgClock className="mx-auto h-12 w-12 mb-4 opacity-50" />
                  <p>No scheduled reminders. Confirm events to schedule reminders.</p>
                </div>
              ) : (
                <>
                  {scheduledRemindersData.filter(r => r.status === "scheduled").map((reminder) => (
                    <ReminderCard
                      key={reminder.id}
                      reminder={reminder}
                      onSendNow={handleSendNow}
                      onCancel={handleCancel}
                      sendingReminderId={sendingReminderId}
                      cancellingReminderId={cancellingReminderId}
                    />
                  ))}
                  <Separator />
                  <div className="flex justify-end">
                    <DownloadCalendarButton
                      eventIds={scheduledRemindersData.filter(r => r.status === "scheduled").map(r => r.event_id)}
                    />
                  </div>
                </>
              )}
            </TabsContent>

            <TabsContent value="all" className="mt-4 space-y-4">
              <h3 className="font-medium">All events</h3>
              {allEventsData.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <SvgCalendar className="mx-auto h-12 w-12 mb-4 opacity-50" />
                  <p>No events yet.</p>
                </div>
              ) : (
                <>
                  {allEventsData.map((event) => (
                    <EventCard
                      key={event.id}
                      event={event}
                      onConfirm={handleConfirm}
                      onDiscard={handleDiscard}
                      onExtract={handleExtract}
                      extractingDocId={extractingDocId}
                    />
                  ))}
                  <Separator />
                  <div className="flex justify-end">
                    <DownloadCalendarButton
                      eventIds={allEventsData.filter(e => e.status === "confirmed").map(e => e.id)}
                    />
                  </div>
                </>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      <ExtractDialog
        open={extractDialogOpen}
        onOpenChange={setExtractDialogOpen}
        onExtract={handleExtract}
        extractingDocId={extractingDocId}
        documents={documents || []}
      />

      <ConfirmDialog
        open={confirmDialogOpen}
        onOpenChange={setConfirmDialogOpen}
        onConfirm={handleConfirmSubmit}
        remindingAt={confirmRemindAt}
      />

      <CancelReminderDialog
        open={cancelDialogOpen}
        onOpenChange={setCancelDialogOpen}
        onConfirm={handleCancelConfirm}
      />

      <DiscardEventDialog
        open={discardDialogOpen}
        onOpenChange={setDiscardDialogOpen}
        onConfirm={handleDiscardConfirm}
      />
    </div>
  );
}