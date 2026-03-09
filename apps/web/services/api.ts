import type {
  AmazonConnectionStatus,
  AuthSessionResponse,
  LiveSessionCreateResponse,
  OrderCancellationResult,
  RuntimeObservation,
  RuntimeScreenshot,
  SessionContextSnapshot,
  SessionSummary,
  SensitiveCheckpoint
} from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8100";
const AUTH_STORAGE_KEY = "blindnav_auth_token";

export function getStoredAuthToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(AUTH_STORAGE_KEY);
}

export function persistAuthToken(token: string | null) {
  if (typeof window === "undefined") {
    return;
  }
  if (token) {
    window.localStorage.setItem(AUTH_STORAGE_KEY, token);
    return;
  }
  window.localStorage.removeItem(AUTH_STORAGE_KEY);
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const authToken = getStoredAuthToken();
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      ...(init?.headers ?? {})
    },
    cache: "no-store"
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${text || "request failed"}`);
  }
  return (await response.json()) as T;
}

export async function signup(params: {
  email: string;
  displayName: string;
  password: string;
  preferredLocale?: string | null;
}): Promise<AuthSessionResponse> {
  return requestJson<AuthSessionResponse>("/api/auth/signup", {
    method: "POST",
    body: JSON.stringify({
      email: params.email,
      display_name: params.displayName,
      password: params.password,
      preferred_locale: params.preferredLocale ?? null
    })
  });
}

export async function login(params: {
  email: string;
  password: string;
}): Promise<AuthSessionResponse> {
  return requestJson<AuthSessionResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({
      email: params.email,
      password: params.password
    })
  });
}

export async function getCurrentUser(): Promise<AuthSessionResponse> {
  return requestJson<AuthSessionResponse>("/api/auth/me");
}

export function buildAmazonLoginUrl(sessionId?: string | null): string {
  const url = new URL(`${API_BASE}/api/auth/amazon/login`);
  if (sessionId) {
    url.searchParams.set("session_id", sessionId);
  }
  return url.toString();
}

export async function getAmazonConnectionStatus(sessionId: string): Promise<AmazonConnectionStatus> {
  return requestJson<AmazonConnectionStatus>(`/api/auth/amazon/status/${sessionId}`);
}

export async function createLiveSession(params: {
  merchant: string;
  locale?: string | null;
}): Promise<LiveSessionCreateResponse> {
  return requestJson<LiveSessionCreateResponse>("/api/live/sessions", {
    method: "POST",
    body: JSON.stringify({
      merchant: params.merchant,
      locale: params.locale ?? null
    })
  });
}

export async function getSessionContext(sessionId: string): Promise<SessionContextSnapshot> {
  return requestJson<SessionContextSnapshot>(`/api/sessions/${sessionId}/context`);
}

export async function listSessions(limit = 20): Promise<SessionSummary[]> {
  return requestJson<SessionSummary[]>(`/api/sessions?limit=${limit}&offset=0`);
}

export async function getCheckpoint(sessionId: string): Promise<SensitiveCheckpoint | null> {
  try {
    return await requestJson<SensitiveCheckpoint>(`/api/sessions/${sessionId}/checkpoint`);
  } catch {
    return null;
  }
}

export async function resolveCheckpoint(params: {
  sessionId: string;
  approved: boolean;
  resolutionNotes?: string | null;
}): Promise<SensitiveCheckpoint> {
  return requestJson<SensitiveCheckpoint>(`/api/sessions/${params.sessionId}/checkpoint/resolve`, {
    method: "POST",
    body: JSON.stringify({
      approved: params.approved,
      resolution_notes: params.resolutionNotes ?? null
    })
  });
}

export async function getFinalConfirmation(sessionId: string): Promise<{
  required: boolean;
  confirmed: boolean;
  prompt_to_user?: string | null;
  confirmation_phrase_expected?: string | null;
  notes?: string | null;
} | null> {
  try {
    return await requestJson(`/api/sessions/${sessionId}/final-confirmation`);
  } catch {
    return null;
  }
}

export async function resolveFinalConfirmation(params: {
  sessionId: string;
  approved: boolean;
  resolutionNotes?: string | null;
}) {
  return requestJson(`/api/sessions/${params.sessionId}/final-confirmation/resolve`, {
    method: "POST",
    body: JSON.stringify({
      approved: params.approved,
      resolution_notes: params.resolutionNotes ?? null
    })
  });
}

export async function getRuntimeObservation(sessionId: string): Promise<RuntimeObservation | null> {
  try {
    return await requestJson<RuntimeObservation>(`/api/sessions/${sessionId}/runtime/observation`);
  } catch {
    return null;
  }
}

export async function getRuntimeScreenshot(sessionId: string): Promise<RuntimeScreenshot | null> {
  try {
    return await requestJson<RuntimeScreenshot>(`/api/sessions/${sessionId}/runtime/screenshot`);
  } catch {
    return null;
  }
}

export async function removeCartItem(params: {
  sessionId: string;
  itemId?: string | null;
  title?: string | null;
}) {
  return requestJson(`/api/sessions/${params.sessionId}/cart/remove`, {
    method: "POST",
    body: JSON.stringify({
      item_id: params.itemId ?? null,
      title: params.title ?? null
    })
  });
}

export async function updateCartQuantity(params: {
  sessionId: string;
  itemId?: string | null;
  title?: string | null;
  quantity: number;
}) {
  return requestJson(`/api/sessions/${params.sessionId}/cart/quantity`, {
    method: "POST",
    body: JSON.stringify({
      item_id: params.itemId ?? null,
      title: params.title ?? null,
      quantity: params.quantity
    })
  });
}

export async function loadLatestOrderSnapshot(sessionId: string) {
  return requestJson(`/api/sessions/${sessionId}/orders/latest`, {
    method: "POST",
    body: JSON.stringify({})
  });
}

export async function cancelLatestOrder(sessionId: string): Promise<OrderCancellationResult> {
  return requestJson<OrderCancellationResult>(`/api/sessions/${sessionId}/orders/cancel`, {
    method: "POST",
    body: JSON.stringify({})
  });
}

export function buildLiveWebSocketUrl(path: string): string {
  const base = new URL(API_BASE);
  const protocol = base.protocol === "https:" ? "wss:" : "ws:";
  const url = new URL(`${protocol}//${base.host}${path}`);
  const authToken = getStoredAuthToken();
  if (authToken) {
    url.searchParams.set("token", authToken);
  }
  return url.toString();
}
