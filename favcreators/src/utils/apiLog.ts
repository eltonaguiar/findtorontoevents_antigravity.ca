/**
 * Log all /fc API requests to the console and to an on-page log.
 * Use fcApiFetch() for any request to getAuthBase() (get_notes, get_my_creators, save_creators, etc.).
 */

const PREFIX = "[FC API]";
const MAX_LOG_ENTRIES = 80;

export type ApiLogEntry = {
  id: number;
  time: string;
  method: string;
  url: string;
  status?: number;
  ok?: boolean;
  error?: string;
};

let logEntries: ApiLogEntry[] = [];
let nextId = 1;
const listeners = new Set<() => void>();

function shortUrl(url: string): string {
  return url.replace(/^https?:\/\/[^/]+/, "");
}

function addEntry(entry: Omit<ApiLogEntry, "id">): void {
  const full: ApiLogEntry = { ...entry, id: nextId++ };
  logEntries.push(full);
  if (logEntries.length > MAX_LOG_ENTRIES) {
    logEntries = logEntries.slice(-MAX_LOG_ENTRIES);
  }
  listeners.forEach((cb) => cb());
}

export function getApiLog(): ApiLogEntry[] {
  return [...logEntries];
}

export function subscribeToApiLog(cb: () => void): () => void {
  listeners.add(cb);
  return () => listeners.delete(cb);
}

export function clearApiLog(): void {
  logEntries = [];
  listeners.forEach((cb) => cb());
}

function logRequest(method: string, url: string, body?: string | null): void {
  if (typeof window === "undefined") return;
  const short = shortUrl(url);
  addEntry({
    time: new Date().toLocaleTimeString(),
    method,
    url: short,
  });
  if (body != null && body.length > 0) {
    const len = typeof body === "string" ? body.length : JSON.stringify(body).length;
    console.log(`${PREFIX} ${method} ${short} (body ${len} chars)`);
  } else {
    console.log(`${PREFIX} ${method} ${short}`);
  }
}

function logResponse(method: string, url: string, status: number, ok: boolean): void {
  if (typeof window === "undefined") return;
  const short = shortUrl(url);
  const last = logEntries[logEntries.length - 1];
  if (last && last.url === short && last.method === method && last.status == null) {
    last.status = status;
    last.ok = ok;
    listeners.forEach((cb) => cb());
  } else {
    addEntry({ time: new Date().toLocaleTimeString(), method, url: short, status, ok });
  }
  console.log(`${PREFIX} ${method} ${short} → ${status} ${ok ? "OK" : "FAIL"}`);
}

function logError(method: string, url: string, error: unknown): void {
  if (typeof window !== "undefined") {
    const short = shortUrl(url);
    const last = logEntries[logEntries.length - 1];
    const errMsg = error instanceof Error ? error.message : String(error);
    if (last && last.url === short && last.method === method && last.status == null) {
      last.error = errMsg;
      listeners.forEach((cb) => cb());
    } else {
      addEntry({ time: new Date().toLocaleTimeString(), method, url: short, error: errMsg });
    }
    console.log(`${PREFIX} ${method} ${short} → ERROR`, error);
  }
}

/**
 * Same as fetch() but logs every /fc API request and response to the console and on-page log.
 */
export async function fcApiFetch(
  url: string,
  init?: RequestInit
): Promise<Response> {
  const method = (init?.method || "GET").toUpperCase();
  const body = init?.body;
  logRequest(method, url, typeof body === "string" ? body : (body != null ? "[body]" : null));
  try {
    const res = await fetch(url, init);
    logResponse(method, url, res.status, res.ok);
    return res;
  } catch (e) {
    logError(method, url, e);
    throw e;
  }
}
