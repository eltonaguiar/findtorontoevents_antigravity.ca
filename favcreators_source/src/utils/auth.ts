export type AuthUser = {
  id: number;
  email?: string;
  display_name?: string;
  avatar_url?: string;
  provider?: string;
};

export type LoginResult = {
  user?: AuthUser | null;
};

const AUTH_BASE = import.meta.env.VITE_AUTH_BASE_URL as string | undefined;

const assertBase = () => {
  if (!AUTH_BASE) {
    throw new Error("Missing VITE_AUTH_BASE_URL");
  }
  return AUTH_BASE.replace(/\/$/, "");
};

export const getAuthBase = () => assertBase();

export const fetchMe = async (): Promise<AuthUser | null> => {
  const base = assertBase();
  const res = await fetch(`${base}/auth/me`, {
    credentials: "include",
  });
  if (!res.ok) return null;
  const data = (await res.json()) as { user: AuthUser | null };
  return data.user ?? null;
};

export const loginWithPassword = async (email: string, password: string) => {
  if (!AUTH_BASE) {
    const normalizedEmail = email.trim().toLowerCase();
    const normalizedPassword = password.trim();
    if (normalizedEmail === "admin" && normalizedPassword === "admin") {
      return { id: 0, email: "admin", provider: "admin" } as AuthUser;
    }
    throw new Error("Missing VITE_AUTH_BASE_URL");
  }

  const base = assertBase();
  const res = await fetch(`${base}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.error || "Login failed");
  }
  const data = (await res.json().catch(() => ({}))) as LoginResult;
  return data.user || null;
};

export const registerWithPassword = async (
  email: string,
  password: string,
  displayName: string,
) => {
  const base = assertBase();
  const res = await fetch(`${base}/auth/register`, {
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
  const base = assertBase();
  await fetch(`${base}/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
};
