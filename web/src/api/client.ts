const TOKEN_KEY = "iespro_token";

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

async function parseError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    return data.detail || data.message || res.statusText;
  } catch {
    return res.statusText;
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
  const t = token ?? getStoredToken();
  if (t) headers.Authorization = `Bearer ${t}`;
  if (options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(path, { ...options, headers });
  if (!res.ok) throw new Error(await parseError(res));
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
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
  const t = token ?? getStoredToken();
  const res = await fetch("/api/chat/stream", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${t}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message,
      id_sucursal: idSucursal,
      id_isla: idIsla ?? undefined,
    }),
  });
  if (!res.ok) throw new Error(await parseError(res));
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
  const t = token ?? getStoredToken();
  const form = new FormData();
  const ext = audio.type.includes("mp4") ? "m4a" : "webm";
  form.append("audio", audio, `recording.${ext}`);

  const res = await fetch("/api/speech/transcribe", {
    method: "POST",
    headers: t ? { Authorization: `Bearer ${t}` } : {},
    body: form,
  });
  if (!res.ok) throw new Error(await parseError(res));
  const data = (await res.json()) as { text?: string };
  return (data.text || "").trim();
}
