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

// API Error interface (plain object, serializable)
export interface ApiError {
  status: number;
  detail: string;
}

// Helper to check if response is an ApiError
function isApiError(data: unknown): data is ApiError {
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
  error?: ApiError;
}> {
  const response = await fetch(`/api/${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  const data = (await response.json()) as unknown;

  if (!response.ok) {
    return {
      ok: false,
      data: {} as T,
      error: isApiError(data) ? data : { status: response.status, detail: ((data as Record<string, unknown>).detail as string) || "Request failed" },
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

export async function authMe() {
  return fetchApi<UserPublic>("auth/me");
}

// Documents
export async function documentsList() {
  return fetchApi<DocumentPublic[]>("documents");
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
  return fetchApi<DocumentPublic>(`documents/${id}/retry`, {
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
