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
}

export interface ConfirmEventResponse extends EventPublic {
  email_status: "sent" | "no_email" | "not_configured" | "failed";
}

export interface EventExtractResponse {
  events: EventPublic[];
}

export interface ConfirmEventRequest {
  remind_at?: string | null;
}

export interface ReminderPublic {
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
}

export interface ChatMessage {
  role: string;
  content: string;
  sources?: { document: string; chunk_index: number; similarity: number; document_id?: number }[];
}

export interface ChatRequest {
  question: string;
  conversation_id?: number | null;
}

export interface ChatResponse {
  conversation_id: number;
  answer: string;
  sources: { document: string; chunk_index: number; similarity: number; document_id?: number }[];
}

export interface ConversationPublic {
  id: number;
  user_id: number;
  title?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
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
  return fetchApi<UserPublic>(`documents/${id}`);
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

export async function eventsConfirm(eventId: number, remindAt?: string) {
  return fetchApi<ConfirmEventResponse>(`events/${eventId}/confirm`, {
    method: "POST",
    body: JSON.stringify({ remind_at: remindAt }),
  });
}

export async function eventsDiscard(eventId: number) {
  return fetchApi<{ detail: string }>(`events/${eventId}/discard`, {
    method: "POST",
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
