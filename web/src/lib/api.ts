// Types mirroring app/api/schemas.py
export interface UserPublic {
  id: number;
  username: string;
  email?: string | null;
}

export interface RegisterRequest {
  username: string;
  password: string;
  email?: string | null;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface UpdateEmailRequest {
  email?: string | null;
}

export interface DocumentPublic {
  id: number;
  filename: string;
  file_type: string;
  size_bytes: number;
  status: string;
  chunk_count: number;
  error_message?: string | null;
  created_at?: string | null;
  text_preview?: string | null;
}

export interface IngestResultResponse {
  filename: string;
  status: "ready" | "duplicate" | "rejected" | "error";
  message: string;
  doc_id?: number | null;
  chunk_count: number;
}

export interface EventPublic {
  id: number;
  user_id: number;
  event_text: string;
  document_id?: number | null;
  event_date?: string | null;
  raw_date?: string | null;
  status: string;
  created_at?: string | null;
  email_status?: "sent" | "no_email" | "not_configured" | "failed" | null;
  google_status?: "synced" | "failed" | "not_connected" | null;
}

export interface ConfirmEventResponse extends EventPublic {
  email_status: "sent" | "no_email" | "not_configured" | "failed";
  google_status?: "synced" | "failed" | "not_connected" | null;
}

export interface EventExtractResponse {
  events: EventPublic[];
}

export interface ConfirmEventRequest {
  remind_at?: string | null;
  lead_minutes?: number | null;
}

export interface ReminderPublic {
  id: number;
  user_id: number;
  event_id: number;
  remind_at: string;
  lead_minutes?: number | null;
  channel: string;
  subject?: string | null;
  body?: string | null;
  status: string;
  sent_at?: string | null;
  google_event_id?: string | null;
  sync_status?: "not_synced" | "synced" | "failed" | "not_connected";
  sync_error?: string | null;
  created_at?: string | null;
}

export interface CheckRemindersResponse {
  configured: boolean;
  sent: number;
  failed: number;
  skipped: number;
  errors: string[];
  details?: { reminder_id: number; success: boolean; detail: string }[];
}

export interface CalendarItem {
  id: number;
  kind: "event" | "reminder";
  title: string;
  date: string;
  all_day: boolean;
  status: string;
  document_id?: number | null;
  event_id?: number | null;
  sync_status?: "not_synced" | "synced" | "failed" | "not_connected" | null;
}

export interface ChatMessage {
  role: string;
  content: string;
  sources?: { document: string; chunk_index: number; similarity: number; document_id?: number }[];
  scope?: { scope: "all" | "selected"; document_ids?: number[] | null } | null;
  created_at?: string | null;
}

export interface ChatDocumentItem {
  id: number;
  filename: string;
  file_type: string;
}

export interface ChatRequest {
  question: string;
  conversation_id?: number | null;
  document_ids?: number[] | null;
}

export interface ChatResponse {
  conversation_id: number;
  answer: string;
  sources: { document: string; chunk_index: number; similarity: number; document_id?: number }[];
  scope?: { scope: "all" | "selected"; document_ids?: number[] | null } | null;
}

export interface ConversationPublic {
  id: number;
  user_id: number;
  title?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  messages?: ChatMessage[] | null;
}

export interface SummaryPublic {
  id: number;
  document_id: number;
  user_id: number;
  summary_text: string;
  created_at?: string | null;
}

export interface SummaryCreateRequest {
  force?: boolean;
}

export interface SummaryAudioResponse {
  engine: string;
  url: string;
}

export interface HealthResponse {
  status: string;
  ollama: string;
  mock_llm: boolean;
  tts_engine?: string;
  email_configured: boolean;
}

// API Error class
export class ApiError extends Error {
  status: number;
  detail: string;
  constructor(detail: string, status: number) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

// Helper to check if response is an ApiError
function isApiError(data: unknown): data is { status: number; detail: string } {
  return (
    typeof data === "object" &&
    data !== null &&
    "status" in data &&
    typeof (data as Record<string, unknown>).status === "number" &&
    "detail" in data &&
    typeof (data as Record<string, unknown>).detail === "string"
  );
}

// Client with credentials "same-origin"
async function fetchApi<T>(path: string, options: RequestInit = {}): Promise<{
  ok: boolean;
  data: T;
  error?: { status: number; detail: string };
}> {
  const response = await fetch(`/api/${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  let data: unknown = {};
  if (response.status !== 204) {
    const text = await response.text();
    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        data = { detail: text };
      }
    }
  }

  if (!response.ok) {
    const errorData = isApiError(data) ? data : { status: response.status, detail: ((data as Record<string, unknown>).detail as string) || "Request failed" };
    return {
      ok: false,
      data: {} as T,
      error: errorData,
    };
  }

  return { ok: true, data: data as T };
}

// Auth
export async function authRegister(data: RegisterRequest) {
  return fetchApi<UserPublic>("auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function authLogin(data: LoginRequest) {
  return fetchApi<UserPublic>("auth/login", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function authLogout() {
  return fetchApi<{ detail: string }>("auth/logout", {
    method: "POST",
  });
}

export async function authMe(): Promise<UserPublic> {
  const result = await fetchApi<UserPublic>("auth/me");
  if (!result.ok) {
    if (result.error?.status === 401) {
      throw new Error("Unauthorized");
    }
    throw new Error(result.error?.detail || "Failed to fetch user");
  }
  return result.data;
}

export async function authUpdateEmail(data: UpdateEmailRequest) {
  return fetchApi<UserPublic>("auth/me/email", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export const updateEmail = authUpdateEmail;

// Documents
export async function documentsList() {
  return fetchApi<UserPublic[]>("documents");
}

export async function documentsGet(id: number) {
  return fetchApi<DocumentPublic>(`documents/${id}`);
}

export async function documentsDelete(id: number) {
  return fetchApi<{ detail: string }>(`documents/${id}`, {
    method: "DELETE",
  });
}

export async function documentsUpload(formData: FormData) {
  return fetchApi<IngestResultResponse[]>("documents/upload", {
    method: "POST",
    body: formData,
  });
}

export async function documentsRetry(id: number) {
  return fetchApi<IngestResultResponse>(`documents/${id}/retry`, {
    method: "POST",
  });
}

export async function documentsFile(id: number, download = false) {
  const url = download ? `/api/documents/${id}/file?download=1` : `/api/documents/${id}/file`;
  const response = await fetch(url, { credentials: "include" });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to fetch file");
  }
  return response.blob();
}

export async function documentsContent(id: number) {
  return fetchApi<{ text: string; char_count: number; truncated: boolean; file_type: string }>(
    `documents/${id}/content`
  );
}

export async function documentsHtml(id: number) {
  return fetchApi<{ html: string }>(`documents/${id}/html`);
}

// Format date helper - treats API timestamps as UTC
export function formatDate(isoString: string | null | undefined): string {
  if (!isoString) return "";
  // API returns timestamps like "2026-10-18 21:42:01" (UTC, no TZ marker)
  // Treat as UTC by replacing space with T and appending Z
  const date = new Date(isoString.replace(" ", "T") + "Z");
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "numeric",
    hour12: true,
  });
}

// Events & Reminders
export async function eventsList(status?: string) {
  const path = status ? `events?status=${status}` : "events";
  return fetchApi<EventPublic[]>(path);
}

export async function eventsExtract(docId: number) {
  return fetchApi<EventExtractResponse>(`documents/${docId}/extract-events`, {
    method: "POST",
  });
}

export async function eventsConfirm(eventId: number, remindAt?: string, leadMinutes?: number) {
  return fetchApi<ConfirmEventResponse>(`events/${eventId}/confirm`, {
    method: "POST",
    body: JSON.stringify({
      remind_at: remindAt,
      ...(leadMinutes !== undefined ? { lead_minutes: leadMinutes } : {}),
    }),
  });
}

export async function eventsDiscard(eventId: number) {
  return fetchApi<{ detail: string }>(`events/${eventId}/discard`, {
    method: "POST",
  });
}

export interface LeadTimeOption {
  minutes: number;
  label: string;
}

export async function remindersLeadTimes(): Promise<LeadTimeOption[]> {
  try {
    const res = await fetch("/api/reminders/lead-times", { credentials: "include" });
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data) && data.length > 0) {
        return data;
      }
    }
  } catch {
    // fallback if endpoint is not implemented
  }
  return [
    { minutes: 10, label: "10 minutes before" },
    { minutes: 30, label: "30 minutes before" },
    { minutes: 60, label: "1 hour before" },
    { minutes: 120, label: "2 hours before" },
    { minutes: 1440, label: "1 day before" },
    { minutes: 2880, label: "2 days before" },
    { minutes: 10080, label: "1 week before" },
  ];
}

export async function reminderUpdate(id: number, data: { lead_minutes?: number; remind_at?: string }) {
  return fetchApi<ReminderPublic>(`reminders/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function remindersList() {
  return fetchApi<ReminderPublic[]>("reminders");
}

export async function remindersCancel(id: number) {
  return fetchApi<{ detail?: string }>(`reminders/${id}`, {
    method: "DELETE",
  });
}

export async function remindersCheck() {
  return fetchApi<CheckRemindersResponse>("reminders/check", {
    method: "POST",
  });
}

export async function calendarIcs(eventIds?: number[]): Promise<Blob> {
  const path = eventIds && eventIds.length > 0
    ? `calendar.ics?event_ids=${eventIds.join(",")}`
    : "calendar.ics";
  const response = await fetch(`/api/${path}`, {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error("Failed to download calendar");
  }
  return response.blob();
}

export async function calendarItems(start: string, end: string) {
  return fetchApi<CalendarItem[]>(`calendar/items?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`);
}

// Chat
export async function chatAsk(req: ChatRequest) {
  return fetchApi<ChatResponse>("chat", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export async function chatDocuments() {
  return fetchApi<ChatDocumentItem[]>("chat/documents");
}

export async function conversationsList() {
  return fetchApi<ConversationPublic[]>("conversations");
}

export async function conversationsGet(id: number) {
  return fetchApi<ConversationPublic>(`conversations/${id}`);
}

export async function conversationsDelete(id: number) {
  return fetchApi<{ detail: string }>(`conversations/${id}`, {
    method: "DELETE",
  });
}

// Summaries
export async function summariesList() {
  return fetchApi<SummaryPublic[]>("summaries");
}

export async function summaryCreate(docId: number, force = false) {
  return fetchApi<SummaryPublic>(`documents/${docId}/summary`, {
    method: "POST",
    body: JSON.stringify({ force }),
  });
}

export async function summaryAudioCreate(summaryId: number) {
  return fetchApi<SummaryAudioResponse>(`summaries/${summaryId}/audio`, {
    method: "POST",
  });
}

export async function summaryAudioGet(summaryId: number): Promise<Blob> {
  const response = await fetch(`/api/summaries/${summaryId}/audio`, {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error("Failed to fetch audio");
  }
  return response.blob();
}

// Graph / Document Map
export interface GraphNode {
  id: number;
  label: string;
  file_type: string;
  link_count: number;
  // ForceGraph2D adds these during simulation
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
}

export interface GraphEdge {
  source: number;
  target: number;
  score: number;
  shared_terms: string[];
  // ForceGraph2D uses source/target as IDs initially, then replaces with node objects
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  unlinked: GraphNode[];
}

export interface GraphRefreshResponse {
  documents: number;
  edges: number;
}

export async function getGraph(minScore?: number) {
  const params = minScore !== undefined ? `?min_score=${minScore}` : "";
  return fetchApi<GraphResponse>(`graph${params}`);
}

export async function refreshGraph() {
  return fetchApi<GraphRefreshResponse>("graph/refresh", {
    method: "POST",
  });
}

// Google Calendar & Reminders Sync
export interface GoogleStatusResponse {
  configured: boolean;
  connected: boolean;
  google_email?: string | null;
}

export interface GoogleConnectResponse {
  auth_url: string;
}

export interface GoogleDisconnectResponse {
  status: string;
  disconnected: boolean;
}

export async function googleStatus() {
  return fetchApi<GoogleStatusResponse>("google/status");
}

export async function googleConnect() {
  return fetchApi<GoogleConnectResponse>("google/connect", {
    method: "POST",
  });
}

export async function googleDisconnect() {
  return fetchApi<GoogleDisconnectResponse>("google/disconnect", {
    method: "POST",
  });
}

export async function reminderSync(reminderId: number) {
  return fetchApi<ReminderPublic>(`reminders/${reminderId}/sync`, {
    method: "POST",
  });
}

