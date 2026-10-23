"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import {
  formatDate,
  authMe,
  authUpdateEmail,
  googleStatus,
  googleConnect,
  googleDisconnect,
  reminderSync,
  type UserPublic,
  type GoogleStatusResponse,
} from "@/lib/api";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import {
  CalendarIcon,
  ClockIcon,
  CheckIcon,
  XIcon,
  RefreshCwIcon,
  DownloadIcon,
  SearchIcon,
  MailIcon,
} from "lucide-react";
import { toast } from "sonner";
import { MonthCalendar } from "@/components/reminders/month-calendar";

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
  google_event_id?: string | null;
  sync_status?: "not_synced" | "synced" | "failed" | "not_connected";
  sync_error?: string | null;
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
  const variants: Record<string, "success" | "secondary" | "destructive" | "warning" | "outline"> = {
    pending: "warning",
    confirmed: "success",
    skipped: "outline",
    scheduled: "success",
    sent: "secondary",
    failed: "destructive",
    cancelled: "outline",
  };
  return (
    <Badge variant={variants[status] || "outline"} className="capitalize font-medium text-xs">
      {status}
    </Badge>
  );
}

function EventCard({ event, onConfirm, onDiscard, extractingDocId }: {
  event: Event;
  onConfirm: (id: number) => void;
  onDiscard: (id: number) => void;
  extractingDocId: number | null;
}) {
  return (
    <Card className="mb-3 border border-border/80 shadow-xs hover:border-border transition-colors">
      <CardContent className="p-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
              <span className="font-semibold text-sm text-foreground truncate">{event.event_text}</span>
              <StatusBadge status={event.status} />
            </div>
            <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
              {event.raw_date && (
                <span className="flex items-center gap-1 font-mono">
                  <ClockIcon className="size-3.5" /> Raw: {event.raw_date}
                </span>
              )}
              {event.event_date && (
                <span className="flex items-center gap-1 font-mono">
                  <CalendarIcon className="size-3.5" /> Date: {event.event_date}
                </span>
              )}
              {event.document_id && (
                <span className="flex items-center gap-1">
                  <span className="font-medium">Doc #{event.document_id}</span>
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0 pt-1 sm:pt-0">
            {event.status === "pending" && (
              <>
                <Button variant="outline" size="sm" onClick={() => onConfirm(event.id)} disabled={extractingDocId !== null} className="h-8 text-xs gap-1.5 cursor-pointer">
                  <CheckIcon className="size-3.5" /> Confirm
                </Button>
                <Button variant="ghost" size="sm" onClick={() => onDiscard(event.id)} className="h-8 text-xs text-destructive hover:bg-destructive/10 cursor-pointer" disabled={extractingDocId !== null}>
                  <XIcon className="size-3.5 mr-1" /> Discard
                </Button>
              </>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ReminderCard({
  reminder,
  onSendNow,
  onCancel,
  onRetrySync,
  sendingReminderId,
  cancellingReminderId,
  isSyncing,
}: {
  reminder: Reminder;
  onSendNow: (id: number) => void;
  onCancel: (id: number) => void;
  onRetrySync?: (id: number) => void;
  sendingReminderId: number | null;
  cancellingReminderId: number | null;
  isSyncing?: boolean;
}) {
  return (
    <Card className="mb-3 border border-border/80 shadow-xs hover:border-border transition-colors">
      <CardContent className="p-4">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
              <span className="font-semibold text-sm text-foreground truncate">{reminder.subject}</span>
              <StatusBadge status={reminder.status} />
              {/* Sync Badge */}
              {reminder.sync_status === "synced" && (
                <Badge variant="success" className="text-xs font-normal">
                  Synced to Google
                </Badge>
              )}
              {reminder.sync_status === "failed" && (
                <span className="inline-flex items-center gap-1.5">
                  <Badge
                    variant="destructive"
                    className="text-xs font-normal"
                    title={reminder.sync_error || undefined}
                  >
                    Sync failed
                  </Badge>
                  {onRetrySync && (
                    <Button
                      variant="outline"
                      size="xs"
                      className="h-5 px-1.5 text-[11px] text-destructive hover:bg-destructive/10 cursor-pointer"
                      onClick={() => onRetrySync(reminder.id)}
                      disabled={isSyncing}
                    >
                      {isSyncing ? (
                        <RefreshCwIcon className="mr-1 size-3 animate-spin" />
                      ) : null}
                      Retry Sync
                    </Button>
                  )}
                </span>
              )}
              {reminder.sync_status === "not_connected" && (
                <Badge variant="outline" className="text-muted-foreground text-xs font-normal">
                  Not connected
                </Badge>
              )}
            </div>
            {reminder.body && (
              <p className="text-xs text-muted-foreground mb-2 leading-relaxed">{reminder.body}</p>
            )}
            <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono">
              <ClockIcon className="size-3.5" />
              <span>Remind at: {formatDate(reminder.remind_at)}</span>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0 pt-1 sm:pt-0">
            {reminder.status === "scheduled" && (
              <>
                <Button variant="outline" size="sm" onClick={() => onSendNow(reminder.id)} disabled={sendingReminderId !== null || cancellingReminderId !== null} className="h-8 text-xs gap-1.5 cursor-pointer">
                  <ClockIcon className="size-3.5" /> Send Now
                </Button>
                <Button variant="ghost" size="sm" onClick={() => onCancel(reminder.id)} className="h-8 text-xs text-destructive hover:bg-destructive/10 cursor-pointer" disabled={sendingReminderId !== null || cancellingReminderId !== null}>
                  <XIcon className="size-3.5 mr-1" /> Cancel
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
          <DialogDescription>Select a processed document to scan for dates, milestones, and deadlines.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 mt-3">
          <select
            className="w-full h-10 px-3 py-2 border border-input rounded-lg bg-background text-foreground text-sm outline-none focus:border-ring focus:ring-2 focus:ring-ring/40 cursor-pointer"
            disabled={extractingDocId !== null}
            onChange={(e) => onExtract(Number(e.target.value))}
            value={extractingDocId || ""}
          >
            <option value="">Select a document...</option>
            {readyDocs.map((doc) => (
              <option key={doc.id} value={String(doc.id)}>
                {doc.filename} ({doc.file_type.toUpperCase()})
              </option>
            ))}
          </select>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" size="sm" onClick={() => onOpenChange(false)} disabled={extractingDocId !== null} className="cursor-pointer">
              Cancel
            </Button>
            <Button size="sm" onClick={() => onOpenChange(false)} disabled={extractingDocId === null} className="cursor-pointer">
              {extractingDocId !== null ? (
                <>
                  <RefreshCwIcon className="mr-2 size-3.5 animate-spin" />
                  Extracting...
                </>
              ) : (
                <>
                  <SearchIcon className="mr-2 size-3.5" />
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
  const [prevRemindingAt, setPrevRemindingAt] = useState(remindingAt || "");
  const [remindAt, setRemindAt] = useState(remindingAt || "");
  const [leadTimeOption, setLeadTimeOption] = useState<string>("default");

  if (prevRemindingAt !== (remindingAt || "")) {
    setPrevRemindingAt(remindingAt || "");
    setRemindAt(remindingAt || "");
  }

  const handleLeadTimeChange = (option: string) => {
    setLeadTimeOption(option);
    const now = new Date();
    let target = new Date();

    if (option === "default") {
      setRemindAt("");
      return;
    }
    if (option === "15m") {
      target = new Date(now.getTime() + 15 * 60 * 1000);
    } else if (option === "1h") {
      target = new Date(now.getTime() + 60 * 60 * 1000);
    } else if (option === "1d") {
      target = new Date(now.getTime() + 24 * 60 * 60 * 1000);
    } else if (option === "2d") {
      target = new Date(now.getTime() + 48 * 60 * 60 * 1000);
    } else if (option === "1w") {
      target = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
    }

    if (option !== "custom") {
      const pad = (n: number) => String(n).padStart(2, "0");
      const formatted = `${target.getFullYear()}-${pad(target.getMonth() + 1)}-${pad(target.getDate())}T${pad(target.getHours())}:${pad(target.getMinutes())}`;
      setRemindAt(formatted);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Confirm Event & Schedule Reminder</DialogTitle>
          <DialogDescription>
            Choose a lead time or set a custom reminder time. Defaults to event date at 09:00.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 mt-3">
          {/* Lead-Time Dropdown */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Reminder Lead Time
            </label>
            <select
              value={leadTimeOption}
              onChange={(e) => handleLeadTimeChange(e.target.value)}
              className="w-full h-10 px-3 py-2 border border-input rounded-lg bg-background text-foreground text-sm outline-none focus:border-ring focus:ring-2 focus:ring-ring/40 cursor-pointer"
            >
              <option value="default">At event date/time (default)</option>
              <option value="15m">15 minutes before / from now</option>
              <option value="1h">1 hour before / from now</option>
              <option value="1d">1 day before</option>
              <option value="2d">2 days before</option>
              <option value="1w">1 week before</option>
              <option value="custom">Custom date & time...</option>
            </select>
          </div>

          {/* Date Time Input */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Notification Date & Time
            </label>
            <input
              type="datetime-local"
              value={remindAt}
              onChange={(e) => {
                setRemindAt(e.target.value);
                setLeadTimeOption("custom");
              }}
              className="w-full h-10 px-3 py-2 border border-input rounded-lg bg-background text-foreground text-sm font-mono outline-none focus:border-ring focus:ring-2 focus:ring-ring/40 cursor-pointer"
              placeholder="YYYY-MM-DDTHH:MM"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" size="sm" onClick={() => onOpenChange(false)} className="cursor-pointer">
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={() => {
                onConfirm(remindAt || undefined);
                onOpenChange(false);
              }}
              className="cursor-pointer font-medium"
            >
              Schedule Reminder
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
          <DialogTitle>Cancel Reminder</DialogTitle>
          <DialogDescription>
            Cancel this scheduled reminder? The event will return to Pending status.
          </DialogDescription>
        </DialogHeader>
        <div className="flex justify-end gap-2 mt-4">
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)} className="cursor-pointer">
            Keep Reminder
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => {
              onConfirm();
              onOpenChange(false);
            }}
            className="cursor-pointer"
          >
            Cancel Reminder
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
          <DialogTitle>Discard Event</DialogTitle>
          <DialogDescription>
            Are you sure you want to discard this event? It will no longer appear on your calendar.
          </DialogDescription>
        </DialogHeader>
        <div className="flex justify-end gap-2 mt-4">
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)} className="cursor-pointer">
            Keep Event
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => {
              onConfirm();
              onOpenChange(false);
            }}
            className="cursor-pointer"
          >
            Discard
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function DownloadCalendarButton({
  eventIds,
  label = "Download .ics",
}: {
  eventIds?: number[];
  label?: string;
}) {
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
    } catch {
      toast.error("Failed to download calendar");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={handleDownload}
      disabled={downloading}
      className="text-xs text-muted-foreground hover:text-foreground h-7 px-2 cursor-pointer"
    >
      {downloading ? (
        <>
          <RefreshCwIcon className="mr-1.5 size-3.5 animate-spin" />
          Downloading .ics...
        </>
      ) : (
        <>
          <DownloadIcon className="mr-1.5 size-3.5" />
          {label}
        </>
      )}
    </Button>
  );
}

function DisconnectGoogleDialog({
  open,
  onOpenChange,
  onConfirm,
  isDisconnecting,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  isDisconnecting: boolean;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Disconnect Google Calendar</DialogTitle>
          <DialogDescription>
            Are you sure you want to disconnect? Events confirmed in the future will no longer sync automatically to your Google Calendar.
          </DialogDescription>
        </DialogHeader>
        <div className="flex justify-end gap-2 mt-4">
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)} disabled={isDisconnecting} className="cursor-pointer">
            Cancel
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={onConfirm}
            disabled={isDisconnecting}
            className="cursor-pointer"
          >
            {isDisconnecting ? "Disconnecting..." : "Disconnect"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function GoogleCalendarCard({
  status,
  onConnect,
  onDisconnectClick,
  isConnecting,
}: {
  status?: GoogleStatusResponse;
  onConnect: () => void;
  onDisconnectClick: () => void;
  isConnecting: boolean;
}) {
  if (!status) return null;

  return (
    <Card className="border border-border/80 shadow-xs">
      <CardContent className="p-4 sm:p-5">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <span className="font-heading font-semibold text-sm sm:text-base text-foreground">Google Calendar Sync</span>
              {status.connected ? (
                <Badge variant="success" className="text-xs">
                  Connected
                </Badge>
              ) : status.configured ? (
                <Badge variant="warning" className="text-xs">
                  Not connected
                </Badge>
              ) : (
                <Badge variant="outline" className="text-muted-foreground text-xs">
                  Not configured
                </Badge>
              )}
            </div>

            {!status.configured ? (
              <p className="text-xs text-muted-foreground leading-relaxed">
                Google Calendar sync is not configured on this server. Set <code className="px-1 py-0.5 rounded bg-muted font-mono text-[11px]">GOOGLE_CLIENT_ID</code> and <code className="px-1 py-0.5 rounded bg-muted font-mono text-[11px]">GOOGLE_CLIENT_SECRET</code> in <code className="px-1 py-0.5 rounded bg-muted font-mono text-[11px]">.env</code>.
              </p>
            ) : status.connected ? (
              <p className="text-xs text-muted-foreground leading-relaxed">
                Connected as <span className="font-semibold text-foreground">{status.google_email || "Google Account"}</span>. Confirmed reminders automatically sync to your calendar.
              </p>
            ) : (
              <p className="text-xs text-muted-foreground leading-relaxed">
                Connect your Google account so scheduled reminders automatically sync as events to your Google Calendar.
              </p>
            )}
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {status.configured && !status.connected && (
              <Button size="sm" onClick={onConnect} disabled={isConnecting} className="h-8 text-xs gap-1.5 cursor-pointer font-medium">
                {isConnecting ? (
                  <>
                    <RefreshCwIcon className="size-3.5 animate-spin" />
                    Connecting...
                  </>
                ) : (
                  <>
                    <CalendarIcon className="size-3.5" />
                    Connect Google Calendar
                  </>
                )}
              </Button>
            )}

            {status.connected && (
              <Button
                variant="outline"
                size="sm"
                onClick={onDisconnectClick}
                className="h-8 text-xs text-destructive hover:bg-destructive/10 hover:text-destructive cursor-pointer"
              >
                Disconnect
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function RemindersPage() {
  useEffect(() => {
    document.title = "Reminders — MemoryNest";
  }, []);

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
  const [disconnectDialogOpen, setDisconnectDialogOpen] = useState(false);
  const [syncingReminderId, setSyncingReminderId] = useState<number | null>(null);
  const [emailInput, setEmailInput] = useState("");
  const [isEditingEmail, setIsEditingEmail] = useState(false);

  // Handle ?google=connected / ?google=error URL parameters
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const googleParam = params.get("google");
    if (googleParam === "connected") {
      toast.success("Google Calendar connected successfully!");
      queryClient.invalidateQueries({ queryKey: ["google-status"] });
      queryClient.invalidateQueries({ queryKey: ["reminders"] });
      queryClient.invalidateQueries({ queryKey: ["calendar-items"] });
      const url = new URL(window.location.href);
      url.searchParams.delete("google");
      window.history.replaceState({}, "", url.pathname + (url.search ? url.search : ""));
    } else if (googleParam === "error") {
      toast.error("Failed to connect Google Calendar");
      const url = new URL(window.location.href);
      url.searchParams.delete("google");
      window.history.replaceState({}, "", url.pathname + (url.search ? url.search : ""));
    }
  }, [queryClient]);

  const { data: user } = useQuery<UserPublic>({
    queryKey: ["me"],
    queryFn: authMe,
  });

  const { data: google } = useQuery<GoogleStatusResponse>({
    queryKey: ["google-status"],
    queryFn: async () => {
      const res = await googleStatus();
      if (!res.ok) return { configured: false, connected: false };
      return res.data;
    },
  });

  const connectGoogleMutation = useMutation({
    mutationFn: async () => {
      const res = await googleConnect();
      if (!res.ok) {
        throw new Error(res.error?.detail || "Failed to initiate Google connection");
      }
      return res.data;
    },
    onSuccess: (data) => {
      if (data?.auth_url) {
        window.location.href = data.auth_url;
      }
    },
    onError: (err: Error) => {
      toast.error(err.message || "Failed to connect Google Calendar");
    },
  });

  const disconnectGoogleMutation = useMutation({
    mutationFn: async () => {
      const res = await googleDisconnect();
      if (!res.ok) {
        throw new Error(res.error?.detail || "Failed to disconnect Google Calendar");
      }
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["google-status"] });
      queryClient.invalidateQueries({ queryKey: ["reminders"] });
      queryClient.invalidateQueries({ queryKey: ["calendar-items"] });
      toast.success("Disconnected from Google Calendar");
      setDisconnectDialogOpen(false);
    },
    onError: (err: Error) => {
      toast.error(err.message || "Failed to disconnect Google Calendar");
    },
  });

  const syncReminderMutation = useMutation({
    mutationFn: (id: number) => {
      setSyncingReminderId(id);
      return reminderSync(id);
    },
    onSuccess: (res) => {
      setSyncingReminderId(null);
      queryClient.invalidateQueries({ queryKey: ["reminders"] });
      queryClient.invalidateQueries({ queryKey: ["calendar-items"] });
      if (res.ok && res.data.sync_status === "synced") {
        toast.success("Synced to Google Calendar");
      } else if (res.ok && res.data.sync_status === "failed") {
        toast.error(res.data.sync_error ? `Sync failed: ${res.data.sync_error}` : "Sync failed");
      } else if (res.ok && res.data.sync_status === "not_connected") {
        toast.info("Google Calendar is not connected. Connect above to sync.");
      } else {
        toast.error(res.error?.detail || "Sync failed");
      }
    },
    onError: (err: Error) => {
      setSyncingReminderId(null);
      toast.error(err.message || "Failed to sync reminder");
    },
  });

  const updateEmailMutation = useMutation({
    mutationFn: (email: string | null) => authUpdateEmail({ email }),
    onSuccess: async (res) => {
      if (!res.ok) {
        toast.error(res.error?.detail || "Failed to update email");
        return;
      }
      await queryClient.invalidateQueries({ queryKey: ["me"] });
      toast.success("Email saved");
      setIsEditingEmail(false);
    },
    onError: (err: Error) => {
      toast.error(err.message || "Failed to update email");
    },
  });

  const handleSaveEmail = () => {
    const trimmed = emailInput.trim();
    if (!trimmed && !user?.email) {
      toast.error("Please enter a valid email address");
      return;
    }
    updateEmailMutation.mutate(trimmed || null);
  };

  const { data: health } = useQuery<{ email_configured?: boolean }>({
    queryKey: ["health"],
    queryFn: async () => {
      const res = await fetch("/api/health");
      if (!res.ok) return { email_configured: false };
      return res.json();
    },
  });

  const { data: pendingEvents, isLoading: pendingLoading } = useQuery({
    queryKey: ["events", "pending"],
    queryFn: () => fetchEvents("pending"),
  });

  const { data: scheduledReminders, isLoading: scheduledLoading } = useQuery({
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
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["events", "pending"] });
      queryClient.invalidateQueries({ queryKey: ["reminders", "scheduled"] });
      queryClient.invalidateQueries({ queryKey: ["calendar-items"] });
      setConfirmDialogOpen(false);
      setConfirmingEventId(null);
      setConfirmRemindAt("");

      const emailStatus = res?.data?.email_status;
      const googleStatusRes = res?.data?.google_status;

      const parts = ["Reminder set."];
      if (emailStatus === "sent") {
        parts.push("Email sent.");
      } else if (emailStatus === "failed") {
        parts.push("Email delivery failed.");
      }

      if (googleStatusRes === "synced") {
        parts.push("Added to Google Calendar.");
      } else if (googleStatusRes === "failed") {
        parts.push("Google Calendar sync failed.");
      }

      const message = parts.join(" ");

      if (googleStatusRes === "failed" || emailStatus === "failed") {
        toast.warning(message);
      } else if (emailStatus === "no_email" && !googleStatusRes) {
        toast.info(message, {
          action: {
            label: "Add email",
            onClick: () => {
              const el = document.getElementById("reminder-email-input");
              if (el) {
                el.focus();
              } else {
                setIsEditingEmail(true);
              }
            },
          },
        });
      } else {
        toast.success(message);
      }
    },
    onError: (err: Error) => {
      toast.error(err.message);
    },
  });

  const discardMutation = useMutation({
    mutationFn: (eventId: number) => (import("@/lib/api")).then(m => m.eventsDiscard(eventId)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["events"] });
      queryClient.invalidateQueries({ queryKey: ["calendar-items"] });
      toast.success("Event discarded");
      setDiscardingEventId(null);
    },
    onError: (err: Error) => {
      toast.error(err.message);
      setDiscardingEventId(null);
    },
  });

  const sendNowMutation = useMutation({
    mutationFn: (id: number) => (import("@/lib/api")).then(m => { void id; return m.remindersCheck(); }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reminders", "scheduled"] });
      queryClient.invalidateQueries({ queryKey: ["calendar-items"] });
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
      queryClient.invalidateQueries({ queryKey: ["calendar-items"] });
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
      <div className="max-w-6xl mx-auto py-8">
        <Card className="border border-border/80">
          <CardHeader>
            <CardTitle>Reminders & Calendar</CardTitle>
            <CardDescription>Loading calendar schedule and notifications...</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="h-24 animate-pulse bg-muted rounded-xl" />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const isGoogleConnected = Boolean(google?.connected);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-border/60">
        <div>
          <h1 className="font-heading text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
            Reminders & Calendar
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Track extracted dates, confirm milestones, and sync notifications to Google Calendar or .ics
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setExtractDialogOpen(true)}
            className="text-xs h-8 gap-1.5 cursor-pointer"
          >
            <SearchIcon className="size-3.5" />
            <span>Scan Document</span>
          </Button>
        </div>
      </div>

      {/* Interactive Month Calendar View */}
      <MonthCalendar
        onConfirmEvent={handleConfirm}
        onDiscardEvent={handleDiscard}
        onCancelReminder={handleCancel}
        onSendReminderNow={handleSendNow}
        onSyncReminder={(id) => syncReminderMutation.mutate(id)}
        isSyncingReminderId={syncingReminderId}
      />

      {/* Google Calendar Integration Card */}
      <GoogleCalendarCard
        status={google}
        onConnect={() => connectGoogleMutation.mutate()}
        onDisconnectClick={() => setDisconnectDialogOpen(true)}
        isConnecting={connectGoogleMutation.isPending}
      />

      {/* Email Notification Card / Manager */}
      {user && !user.email ? (
        <Card className="border-primary/30 bg-primary/5">
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-semibold flex items-center gap-2">
              <MailIcon className="size-4.5 text-primary" />
              Add your email to receive reminder notifications
            </CardTitle>
            <CardDescription className="text-xs">
              MemoryNest sends automated email notifications and calendar invites when reminders are due.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSaveEmail();
              }}
              className="flex flex-col sm:flex-row items-center gap-2 max-w-md"
            >
              <Input
                id="reminder-email-input"
                type="email"
                placeholder="you@example.com"
                value={emailInput}
                onChange={(e) => setEmailInput(e.target.value)}
                disabled={updateEmailMutation.isPending}
                className="h-9 text-sm"
                required
              />
              <Button
                type="submit"
                disabled={updateEmailMutation.isPending || !emailInput.trim()}
                className="h-9 w-full sm:w-auto font-medium cursor-pointer"
              >
                {updateEmailMutation.isPending ? (
                  <>
                    <RefreshCwIcon className="mr-2 size-3.5 animate-spin" />
                    Saving...
                  </>
                ) : (
                  "Save Email"
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      ) : user?.email ? (
        isEditingEmail ? (
          <div className="p-4 rounded-xl border border-border bg-card text-card-foreground shadow-xs">
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider whitespace-nowrap">
                Notification Email:
              </span>
              <Input
                type="email"
                placeholder="you@example.com"
                value={emailInput}
                onChange={(e) => setEmailInput(e.target.value)}
                disabled={updateEmailMutation.isPending}
                className="h-8.5 max-w-xs text-sm"
                autoFocus
              />
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  className="h-8.5 text-xs font-medium cursor-pointer"
                  onClick={handleSaveEmail}
                  disabled={updateEmailMutation.isPending}
                >
                  {updateEmailMutation.isPending ? "Saving..." : "Save"}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-8.5 text-xs cursor-pointer"
                  onClick={() => {
                    setIsEditingEmail(false);
                    setEmailInput(user.email || "");
                  }}
                  disabled={updateEmailMutation.isPending}
                >
                  Cancel
                </Button>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-between text-xs text-muted-foreground bg-muted/40 px-4 py-2.5 rounded-xl border border-border/80">
            <div className="flex items-center gap-2 truncate">
              <MailIcon className="size-4 text-primary shrink-0" />
              <span>Notification address:</span>
              <span className="font-semibold text-foreground truncate">{user.email}</span>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2.5 text-xs text-primary hover:text-primary font-medium cursor-pointer"
              onClick={() => {
                setEmailInput(user.email || "");
                setIsEditingEmail(true);
              }}
            >
              Edit
            </Button>
          </div>
        )
      ) : null}

      {/* Tabs for Events and Reminders */}
      <Card className="border border-border/80 shadow-xs">
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-semibold">Events & Scheduled Reminders</CardTitle>
          <CardDescription className="text-xs">Review pending dates extracted from documents and manage active notification alerts</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6 pt-0">
          <Tabs defaultValue="pending" className="w-full">
            <TabsList className="grid w-full grid-cols-3 max-w-md">
              <TabsTrigger value="pending" className="cursor-pointer text-xs">
                Pending ({pendingEventsData.filter(e => e.status === "pending").length})
              </TabsTrigger>
              <TabsTrigger value="scheduled" className="cursor-pointer text-xs">
                Scheduled ({scheduledRemindersData.filter(r => r.status === "scheduled").length})
              </TabsTrigger>
              <TabsTrigger value="all" className="cursor-pointer text-xs">
                All ({allEventsData.length})
              </TabsTrigger>
            </TabsList>

            {/* Pending Tab */}
            <TabsContent value="pending" className="mt-4 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-foreground">Events awaiting confirmation</h3>
                <Button variant="outline" size="sm" onClick={() => setExtractDialogOpen(true)} disabled={extractingDocId !== null} className="text-xs h-7.5 gap-1.5 cursor-pointer">
                  <SearchIcon className="size-3.5" /> Find dates in document
                </Button>
              </div>

              {pendingEventsData.filter(e => e.status === "pending").length === 0 ? (
                <div className="text-center py-12 text-muted-foreground border border-dashed border-border/80 rounded-xl bg-muted/20">
                  <CalendarIcon className="mx-auto size-10 mb-2 opacity-40" />
                  <p className="text-sm font-medium text-foreground">No pending events</p>
                  <p className="text-xs text-muted-foreground mt-0.5">Extract dates from a document to get started</p>
                </div>
              ) : (
                <>
                  {pendingEventsData.filter(e => e.status === "pending").map((event) => (
                    <EventCard
                      key={event.id}
                      event={event}
                      onConfirm={handleConfirm}
                      onDiscard={handleDiscard}
                      extractingDocId={extractingDocId}
                    />
                  ))}
                  <Separator />
                  <div className="flex items-center justify-between text-xs text-muted-foreground pt-1">
                    {!isGoogleConnected ? (
                      <span className="text-muted-foreground/80">
                        Google Calendar not connected. Download .ics instead:
                      </span>
                    ) : <span />}
                    <DownloadCalendarButton
                      eventIds={pendingEventsData.filter(e => e.status === "confirmed").map(e => e.id)}
                    />
                  </div>
                </>
              )}
            </TabsContent>

            {/* Scheduled Tab */}
            <TabsContent value="scheduled" className="mt-4 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                <h3 className="text-sm font-semibold text-foreground">Scheduled notification reminders</h3>
                <div className="flex flex-col sm:flex-row sm:items-center gap-2">
                  <Button variant="outline" size="sm" onClick={() => checkDueMutation.mutate()} disabled={checkDueMutation.isPending} className="text-xs h-7.5 gap-1.5 cursor-pointer">
                    <RefreshCwIcon className={`size-3.5 ${checkDueMutation.isPending ? "animate-spin" : ""}`} />
                    Send due reminders
                  </Button>
                  {health && health.email_configured === false && (
                    <p className="text-[11px] text-muted-foreground">
                      Email service not configured. ICS downloads work.
                    </p>
                  )}
                </div>
              </div>

              {scheduledRemindersData.filter(r => r.status === "scheduled").length === 0 ? (
                <div className="text-center py-12 text-muted-foreground border border-dashed border-border/80 rounded-xl bg-muted/20">
                  <ClockIcon className="mx-auto size-10 mb-2 opacity-40" />
                  <p className="text-sm font-medium text-foreground">No scheduled reminders</p>
                  <p className="text-xs text-muted-foreground mt-0.5">Confirm pending events to schedule notifications</p>
                </div>
              ) : (
                <>
                  {scheduledRemindersData.filter(r => r.status === "scheduled").map((reminder) => (
                    <ReminderCard
                      key={reminder.id}
                      reminder={reminder}
                      onSendNow={handleSendNow}
                      onCancel={handleCancel}
                      onRetrySync={(id) => syncReminderMutation.mutate(id)}
                      sendingReminderId={sendingReminderId}
                      cancellingReminderId={cancellingReminderId}
                      isSyncing={syncingReminderId === reminder.id}
                    />
                  ))}
                  <Separator />
                  <div className="flex items-center justify-between text-xs text-muted-foreground pt-1">
                    {!isGoogleConnected ? (
                      <span className="text-muted-foreground/80">
                        Google Calendar not connected. Download .ics instead:
                      </span>
                    ) : <span />}
                    <DownloadCalendarButton
                      eventIds={scheduledRemindersData.filter(r => r.status === "scheduled").map(r => r.event_id)}
                    />
                  </div>
                </>
              )}
            </TabsContent>

            {/* All Tab */}
            <TabsContent value="all" className="mt-4 space-y-4">
              <h3 className="text-sm font-semibold text-foreground">All document events</h3>
              {allEventsData.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground border border-dashed border-border/80 rounded-xl bg-muted/20">
                  <CalendarIcon className="mx-auto size-10 mb-2 opacity-40" />
                  <p className="text-sm font-medium text-foreground">No events recorded yet</p>
                </div>
              ) : (
                <>
                  {allEventsData.map((event) => (
                    <EventCard
                      key={event.id}
                      event={event}
                      onConfirm={handleConfirm}
                      onDiscard={handleDiscard}
                      extractingDocId={extractingDocId}
                    />
                  ))}
                  <Separator />
                  <div className="flex items-center justify-between text-xs text-muted-foreground pt-1">
                    {!isGoogleConnected ? (
                      <span className="text-muted-foreground/80">
                        Google Calendar not connected. Download .ics instead:
                      </span>
                    ) : <span />}
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

      {/* Dialogs */}
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

      <DisconnectGoogleDialog
        open={disconnectDialogOpen}
        onOpenChange={setDisconnectDialogOpen}
        onConfirm={() => disconnectGoogleMutation.mutate()}
        isDisconnecting={disconnectGoogleMutation.isPending}
      />
    </div>
  );
}
