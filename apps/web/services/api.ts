import type {
  LiveSessionCreateResponse,
  RuntimeObservation,
  RuntimeScreenshot,
  SessionContextSnapshot,
  SessionSummary,
  SensitiveCheckpoint
} from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8100";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
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

export function buildLiveWebSocketUrl(path: string): string {
  const base = new URL(API_BASE);
  const protocol = base.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${base.host}${path}`;
}
