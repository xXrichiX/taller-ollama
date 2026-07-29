async function parseError(res: Response): Promise<never> {
  let message = res.statusText;
  if (res.status === 429) {
    message = "Demasiadas peticiones. Espera un momento e inténtalo de nuevo.";
  } else {
    try {
      const data = await res.json();
      message = data.detail || data.message || res.statusText;
    } catch {
      /* keep statusText */
    }
  }
  const retryHeader = res.headers.get("Retry-After");
  const retryAfterSec = retryHeader ? Number.parseInt(retryHeader, 10) : undefined;
  throw new ApiError(message, res.status, Number.isFinite(retryAfterSec) ? retryAfterSec : undefined);
}

export class ApiError extends Error {
  status: number;
  retryAfterSec?: number;

  constructor(message: string, status: number, retryAfterSec?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.retryAfterSec = retryAfterSec;
  }
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null,
): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> | undefined),
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(path, {
    ...options,
    headers,
    credentials: "include",
  });
  if (!res.ok) throw await parseError(res);
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export type PublicAuthConfig = {
  registration_enabled: boolean;
  turnstile_site_key: string;
  captcha_configured?: boolean;
  invite_required: boolean;
  captcha_mode: "turnstile" | "none";
  email_verification_enabled: boolean;
};

export async function fetchPublicAuthConfig(): Promise<PublicAuthConfig> {
  return api<PublicAuthConfig>("/api/auth/public-config");
}

export type StreamHandlers = {
  onStatus?: (label: string) => void;
  onToken?: (text: string) => void;
  onDone?: (data: { answer?: string; route?: string }) => void;
  onError?: (message: string) => void;
};

export async function streamChat(
  message: string,
  idSucursal: number | null | undefined,
  handlers: StreamHandlers,
  token?: string | null,
  idIsla?: number | null,
): Promise<void> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch("/api/chat/stream", {
    method: "POST",
    headers,
    credentials: "include",
    body: JSON.stringify({
      message,
      id_sucursal: idSucursal,
      id_isla: idIsla ?? undefined,
    }),
  });
  if (!res.ok) throw await parseError(res);
  if (!res.body) throw new Error("Sin respuesta del servidor");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    for (const line of lines) {
      if (!line.trim()) continue;
      const evt = JSON.parse(line) as { type: string; label?: string; text?: string; message?: string; answer?: string; route?: string };
      if (evt.type === "status" && evt.label) handlers.onStatus?.(evt.label);
      if (evt.type === "token" && evt.text) handlers.onToken?.(evt.text);
      if (evt.type === "done") handlers.onDone?.({ answer: evt.answer, route: evt.route });
      if (evt.type === "error") handlers.onError?.(evt.message || "Error");
    }
  }
}

export const ROUTE_LABELS: Record<string, string> = {
  sql: "Consulta SQL",
  rag: "Búsqueda en manuales",
  function_calling: "Acción en taller",
  transactional: "Transaccional",
  router: "Orquestador",
  guardrail: "Seguridad",
};

export async function transcribeSpeech(
  audio: Blob,
  token?: string | null,
): Promise<string> {
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;

  const form = new FormData();
  const ext = audio.type.includes("mp4") ? "m4a" : "webm";
  form.append("audio", audio, `recording.${ext}`);

  const res = await fetch("/api/speech/transcribe", {
    method: "POST",
    headers,
    credentials: "include",
    body: form,
  });
  if (!res.ok) throw await parseError(res);
  const data = (await res.json()) as { text?: string };
  return (data.text || "").trim();
}
