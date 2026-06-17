type Json = Record<string, unknown> | Array<unknown>;

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function resolveApiBase() {
  const raw = String(import.meta.env.VITE_API_BASE_URL || "").trim();
  if (!raw) return "";
  const cleaned = raw.replace(/\/+$/, "");

  if (typeof window === "undefined") return cleaned;
  try {
    const parsed = new URL(cleaned);
    const pageHost = window.location.hostname;
    const apiHost = parsed.hostname;
    const isLoopbackPair =
      (apiHost === "localhost" || apiHost === "127.0.0.1") &&
      (pageHost === "localhost" || pageHost === "127.0.0.1");
    if (!isLoopbackPair || apiHost === pageHost) return cleaned;
    parsed.hostname = pageHost;
    return parsed.toString().replace(/\/+$/, "");
  } catch {
    return cleaned;
  }
}

function resolveAppBasePrefix() {
  const raw = String(import.meta.env.BASE_URL || "/").trim();
  if (!raw || raw === "/") return "";
  const normalized = raw.replace(/\/+$/, "");
  if (!normalized || normalized === "/") return "";
  return normalized.startsWith("/") ? normalized : `/${normalized}`;
}

const API_BASE = resolveApiBase();
const APP_BASE_PREFIX = resolveAppBasePrefix();
const TOKEN_KEY = "auth_token";

export function getToken() {
  const legacy = localStorage.getItem(TOKEN_KEY) || "";
  if (legacy) localStorage.removeItem(TOKEN_KEY);
  return "";
}

export function toUrl(path: string) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  if (API_BASE) return `${API_BASE}${normalizedPath}`;
  if (APP_BASE_PREFIX && (normalizedPath === APP_BASE_PREFIX || normalizedPath.startsWith(`${APP_BASE_PREFIX}/`))) {
    return normalizedPath;
  }
  return `${APP_BASE_PREFIX}${normalizedPath}`;
}

function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function isTransientNetworkError(err: unknown): boolean {
  if (!(err instanceof Error)) return false;
  const msg = String(err.message || "").toLowerCase();
  return (
    err.name === "TypeError" ||
    msg.includes("failed to fetch") ||
    msg.includes("networkerror") ||
    msg.includes("network error")
  );
}

export function safeParsePayload(text: string): any {
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text };
  }
}

export async function request<T = Json>(path: string, init: RequestInit = {}): Promise<T> {
  getToken();
  const headers = new Headers(init.headers || {});
  const res = await fetch(toUrl(path), { ...init, headers, credentials: "include" });

  const text = await res.text();
  const payload = safeParsePayload(text);
  if (!res.ok) {
    throw new ApiError(res.status, String((payload as any).detail || "request failed"));
  }
  return payload as T;
}

export async function authFetch(
  path: string,
  init: RequestInit = {},
  opts: { networkRetry?: number; retryDelayMs?: number } = {},
) {
  const retries = Math.max(0, Number(opts.networkRetry || 0));
  const delayMs = Math.max(50, Number(opts.retryDelayMs || 300));
  let attempt = 0;
  while (true) {
    try {
      getToken();
      const headers = new Headers(init.headers || {});
      const res = await fetch(toUrl(path), { ...init, headers, credentials: "include" });
      if (res.status === 401) {
        throw new ApiError(401, "unauthorized");
      }
      return res;
    } catch (e) {
      if (attempt >= retries || !isTransientNetworkError(e)) {
        throw e;
      }
      attempt += 1;
      await sleep(delayMs * attempt);
    }
  }
}

export async function parseOrThrow<T>(res: Response): Promise<T> {
  const text = await res.text();
  const payload = safeParsePayload(text);
  if (!res.ok) {
    throw new ApiError(res.status, String((payload as any).detail || "request failed"));
  }
  return payload as T;
}

export async function authRequest<T>(
  path: string,
  init: RequestInit = {},
  opts: { networkRetry?: number; retryDelayMs?: number } = {},
): Promise<T> {
  const res = await authFetch(path, init, opts);
  return parseOrThrow<T>(res);
}

export function buildQueryString(params: Record<string, string | number | boolean | undefined>): string {
  const qs = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) {
      qs.set(key, String(value));
    }
  }
  return qs.toString();
}

export const TOKEN_KEY_EXPORT = TOKEN_KEY;
