# Login for findtorontoevents.ca — Google OAuth Setup

## Goal

- **Default:** Everyone can see all events (no paywall).
- **Optional:** Google / email login so signed-in users can get extra features (e.g. saved events, preferences) later.

This doc walks you through **Authorized JavaScript origins** and **Authorized redirect URIs** in Google Cloud Console, and what to use for findtorontoevents.ca.

---

## 1. Where these settings live

1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Select (or create) the project that has your OAuth client (e.g. the one used for FavCreators at `/fc/`).
3. Go to **APIs & Services** → **Credentials**.
4. Open your **OAuth 2.0 Client ID** (Web application).
5. In that client you’ll see:
   - **Authorized JavaScript origins**
   - **Authorized redirect URIs**

---

## 2. Authorized JavaScript origins — what to put

**What it is:** The **exact origins** (scheme + host + port, no path) from which your **frontend** is allowed to run. Google uses this to allow the OAuth popup/redirect to start from your page. If the page’s origin isn’t listed, the OAuth flow can be blocked.

**Rules:**

- Use full origin: `https://` or `http://`, then host, then port **only if not 443/80**.
- No trailing slash.
- No path (e.g. no `/fc/` or `/login`).

**What to add for findtorontoevents.ca:**

| Environment | Authorized JavaScript origin |
|-------------|------------------------------|
| **Production** | `https://findtorontoevents.ca` |
| **Local dev**  | `http://localhost` (or `http://localhost:8000` if you use port 8000, etc.) |
| **FavCreators (if same client)** | `https://findtorontoevents.ca` (same as prod; `/fc/` is same origin) |

So in the “Authorized JavaScript origins” list you should see at least:

- `https://findtorontoevents.ca`
- `http://localhost` (and `http://localhost:8000` if you use that port)

---

## 3. Authorized redirect URIs — what to put

**What it is:** The **exact URL** to which Google redirects the user **after** they sign in and consent. Your server (e.g. PHP) receives the `?code=...` at this URL and exchanges it for tokens. This URI must match **character-for-character** what you send in the OAuth request as `redirect_uri`.

**Rules:**

- Full URL: scheme, host, port (if non-default), and **path**.
- No query string or fragment in the value you configure (Google adds `?code=...`).
- Must be HTTPS in production (HTTP only for localhost).

**Main site login (implemented):**

| Purpose | Authorized redirect URI |
|--------|--------------------------|
| **Main site login (production)** | `https://findtorontoevents.ca/api/google_callback.php` |
| **FavCreators (existing)** | `https://findtorontoevents.ca/fc/api/google_callback.php` |
| **Local dev** | `http://localhost/api/google_callback.php` (or with port if needed) |

You can keep the existing FavCreators redirect URI if you’re reusing the same OAuth client.

---

## 4. Quick reference

| Setting | Meaning | Example for findtorontoevents.ca |
|--------|--------|----------------------------------|
| **Authorized JavaScript origins** | “Where my app’s pages run” (origin only) | `https://findtorontoevents.ca`, `http://localhost` |
| **Authorized redirect URIs** | “Where Google sends the user after login” (full URL of your callback) | `https://findtorontoevents.ca/api/auth/google_callback.php` |

---

## 5. Checklist

- [ ] In Google Cloud Console → Credentials → your OAuth 2.0 Client ID:
  - [ ] **Authorized JavaScript origins:** add `https://findtorontoevents.ca` and `http://localhost` (and port if needed).
  - [ ] **Authorized redirect URIs:** add `https://findtorontoevents.ca/api/google_callback.php` (and `http://localhost/api/google_callback.php` for local dev).
- [ ] In your app, the `redirect_uri` you send in the OAuth request must match one of these URIs exactly (including path and trailing nothing).
- [ ] Keep **Client secret** only on the server (e.g. in PHP); never in frontend or public repo.

---

## 6. Implementation (main site)

- **Backend (in place):** `api/google_auth.php` and `api/google_callback.php` use callback `https://findtorontoevents.ca/api/google_callback.php`. They share the FavCreators `users` DB so one login works site-wide. Optional `?return_to=/path` on `google_auth.php` controls where the user is sent after login.
- **Frontend:** Add a “Sign in” link on the main events page to `https://findtorontoevents.ca/api/google_auth.php` (or `?return_to=/` to land back on home). Events remain visible to everyone.
