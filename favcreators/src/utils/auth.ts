import { fcApiFetch } from "./apiLog";

export type AuthUser = {
  id: number;
  email?: string;
  display_name?: string;
  avatar_url?: string;
  provider?: string;
  discord_id?: string;
  discord_username?: string;
};

export type LoginResult = {
  user?: AuthUser | null;
};

const AUTH_BASE = import.meta.env.VITE_AUTH_BASE_URL as string | undefined;

/** Cached resolved base when /fc/api returns non-JSON and /findevents/fc/api works (host path quirk). */
let _resolvedAuthBase: string | null = null;

/** Same-origin API path when VITE_AUTH_BASE_URL is unset. Prefer /fc/api (deploy path). */
function getDefaultAuthBase(): string {
  if (typeof window !== "undefined" && window.location?.origin) {
    const path = (window.location.pathname || "").toLowerCase();
    const apiPath = path.includes("/fc") ? "/fc/api" : "/favcreators/api";
    return `${window.location.origin}${apiPath}`;
  }
  return "";
}

/** True when app is on localhost so we must use same-origin API (avoid CORS). */
function isLocalhost(): boolean {
  if (typeof window === "undefined" || !window.location?.hostname) return false;
  const h = window.location.hostname.toLowerCase();
  return h === "localhost" || h === "127.0.0.1" || h === "";
}

const assertBase = () => {
  const base = (AUTH_BASE ?? getDefaultAuthBase()).replace(/\/$/, "");
  if (!base) {
    throw new Error("Missing VITE_AUTH_BASE_URL and not in browser");
  }
  return base;
};

/** Auth API base URL. On localhost use same-origin /fc/api (serve_local mocks). Uses resolved base when set. */
export const getAuthBase = (): string => {
  const base = _resolvedAuthBase ?? (isLocalhost() ? getDefaultAuthBase() : (AUTH_BASE ?? getDefaultAuthBase()));
  return base.replace(/\/$/, "") || "";
};

/**
 * Resolve API base: try /fc/api, if response is not JSON (e.g. PHP parse error) try /findevents/fc/api.
 * Call once before API calls so guest/notes work when host serves API only under findevents.
 */
export const resolveAuthBase = async (): Promise<string> => {
  if (_resolvedAuthBase) return _resolvedAuthBase.replace(/\/$/, "");
  if (typeof window === "undefined" || isLocalhost() || AUTH_BASE) {
    const b = getDefaultAuthBase().replace(/\/$/, "");
    if (b) _resolvedAuthBase = b;
    return b;
  }
  const origin = window.location.origin;
  const primary = `${origin}/fc/api`;
  try {
    const r = await fcApiFetch(`${primary}/status.php`);
    const text = await r.text();
    const looksJson = text.trim().startsWith("{");
    if (r.ok && looksJson) {
      _resolvedAuthBase = primary;
      return primary;
    }
  } catch {
    /* ignore */
  }
  const fallback = `${origin}/findevents/fc/api`;
  try {
    const r = await fcApiFetch(`${fallback}/status.php`);
    const text = await r.text();
    const looksJson = text.trim().startsWith("{");
    if (r.ok && looksJson) {
      _resolvedAuthBase = fallback;
      return fallback;
    }
  } catch {
    /* ignore */
  }
  _resolvedAuthBase = primary;
  return primary;
}

/** PHP session check: get_me.php returns { user } from session (Google login sets it). */
export const fetchMe = async (): Promise<AuthUser | null> => {
  const base = getAuthBase();
  if (!base) return null;
  try {
    const res = await fcApiFetch(`${base}/get_me.php`, { credentials: "include" });
    if (!res.ok) return null;
    const text = await res.text();
    try {
      const data = JSON.parse(text) as { user?: AuthUser | null };
      return data.user ?? null;
    } catch {
      // Server returned non-JSON (e.g. raw PHP when PHP is not executed)
      return null;
    }
  } catch {
    return null;
  }
};

export const loginWithPassword = async (email: string, password: string) => {
  const base = getAuthBase() || assertBase();
  if (!base) {
    throw new Error("Missing VITE_AUTH_BASE_URL and not in browser");
  }

  const baseNorm = base.replace(/\/$/, "");
  const loginUrl = `${baseNorm}/login.php`;
  let res: Response;
  try {
    res = await fcApiFetch(loginUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email, password }),
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    if (/failed to fetch|networkerror|load failed/i.test(msg)) {
      throw new Error(
        "Cannot reach login server. Check that the site API is at /fc/api/ and try again."
      );
    }
    throw err;
  }
  if (!res.ok) {
    const text = await res.text();
    let data: { error?: string } = {};
    try {
      data = JSON.parse(text);
    } catch {
      data = { error: text || "Login failed" };
    }
    throw new Error(data.error || "Login failed");
  }
  const text = await res.text();
  const data = (() => {
    try {
      return JSON.parse(text) as LoginResult;
    } catch {
      return {} as LoginResult;
    }
  })();
  return data.user || null;
};

export const registerWithPassword = async (
  email: string,
  password: string,
  displayName: string,
) => {
  const base = assertBase();
  const res = await fcApiFetch(`${base}/register.php`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ email, password, displayName }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.error || "Registration failed");
  }
};

export const logout = async () => {
  // Client side logout mostly
};
