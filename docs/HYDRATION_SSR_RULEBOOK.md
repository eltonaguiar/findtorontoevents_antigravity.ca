# Hydration / SSR Rulebook — Find Toronto Events

This doc captures **why the login button disappeared** (hydration mismatch) and a short **rulebook** so we avoid this class of disappearing-UI issues in the future. See also [LOGIN_GOOGLE_OAUTH_SETUP.md](./LOGIN_GOOGLE_OAUTH_SETUP.md) for auth setup.

---

## Root cause (login button disappearing)

- **Primary issue:** The client-side script (React) replaces the server-rendered header/control UI with its own React-rendered tree. The login element existed in the **static HTML** but was **not** in the **React component tree**. During hydration, React treats the server HTML as the source to “attach” to; when the client tree differs, React updates the DOM to match the client tree, so the login node was removed.
- **Evidence:**
  - Static HTML had a complex header (GLOBAL FEED, MY EVENTS, quick-nav, etc.) but no stable dedicated login node in the **same tree** React hydrates.
  - Markup is highly dynamic (serialized/virtual tree with `node="..."` etc.), re-instantiated by client React; header is recomputed on mount and can drop elements not present in the client tree.
  - Login/collection controls appear in initial HTML but are part of a shell that is **recomputed on the client** with different state → classic “element in SSR, gone after hydration.”

**Conclusion:** Anything we want to stay visible in the header/nav must either (1) be part of the **same React tree** that renders that region (so server and client output match), or (2) be added **after** hydration (client-only) so React never “replaces” it.

---

## How we fixed it (current approach)

We use a **client-only island** style fix:

- The **Sign in** link is **not** in the initial server-rendered HTML for the header.
- A small **plain-JS script** in `index.html` runs **after** load (DOMContentLoaded + short delay, and again on `load`). It finds the top-right control container (via the Config button) and **injects** the Sign in `<a>` before the Config button.
- Because the link is added **after** React has hydrated, there is **no hydration mismatch**: React’s tree and the server HTML never contained the link, so React doesn’t remove it.

This matches the feedback’s **Fix #3** (client-only island) and **Fix #2** (mount guard): we don’t render the login in the SSR/hydrated tree; we “mount” it only on the client, after the shell is stable.

**Trade-off:** Sign in is not in the initial HTML (no SSR for that node). For a single link, that’s acceptable and avoids touching the minified React nav chunk.

---

## Rulebook: avoid disappearing UI / hydration issues

### 1) Never read browser-only state during initial render

- Do **not** use `window`, `document`, `localStorage`, `sessionStorage`, or `Date.now()` / `Math.random()` **in React render** (or in sync hooks that run before first paint) for any component that is server-rendered and then hydrated.
- If you must use them, gate behind `useEffect` and a `hasMounted` (or similar) flag so the **first** client render matches the server HTML.

```tsx
function Component() {
  const [hasMounted, setHasMounted] = useState(false);
  useEffect(() => setHasMounted(true), []);

  if (!hasMounted) return <SSRSafeShell />;

  const value = window.localStorage.getItem('x');
  return <RealUI value={value} />;
}
```

### 2) Make auth and header state SSR-aware

- For login / “Global feed” / “My events” / user menu: derive **initial** state on the server (e.g. cookies/session) and pass as **props**. Do not recompute differently on the client in the first render.
- Treat **SSR output as the source of truth** for the first paint; client can refine later in `useEffect` or background fetches.

### 3) Keep initial markup stable and deterministic

- Avoid **random IDs**, **timestamps**, or **live counts** in the header/shell on the **first** render unless they are identical on server and client.
- If you need dynamic values (e.g. “Last updated: …”), either (a) compute them on the server and pass as props, or (b) render a placeholder on SSR and set the real value in `useEffect` after mount.

### 4) Use explicit “client-only islands” for risky bits

- For small, dynamic widgets (login button, user menu, settings flyout), consider:
  - **Client-only mount:** render nothing (or a neutral shell) on the server, then render the real UI in `useEffect` after mount; or
  - **Non-hydrated island:** e.g. Next.js `dynamic(..., { ssr: false })`, or a wrapper that returns `null` until `hasMounted`.
- Our **Sign in** link is implemented as a **non-React client-only island** (plain script that injects DOM after load), which avoids hydration entirely for that node.

### 5) Build a quick hydration-check into dev process

- When touching SSR + React (e.g. header, nav, auth UI):
  - Open DevTools → Console and hard-refresh; fix any **“Hydration failed because the initial UI does not match”** (or similar) before shipping.
  - If something **disappears** after load (e.g. login), first ask: **“Does the SSR HTML match the first client render?”** — diff the DOM/markup if needed.
- See [Next.js hydration error docs](https://nextjs.org/docs/messages/react-hydration-error) and [Josh Comeau – Perils of rehydration](https://www.joshwcomeau.com/react/the-perils-of-rehydration/) for patterns.

---

## Verification steps (after any header/nav/auth change)

1. **Console:** Hard-refresh with DevTools open; confirm no React hydration warnings.
2. **View Page Source:** Check that the server-rendered header/nav region matches what you expect (and that you’re not relying on a node that only exists in client React tree).
3. **After full load:** Confirm the login (or user controls) **remains visible** and does not disappear during or right after hydration.
4. **Auth states:** Toggle logged-in / logged-out (clear cookies or localStorage, log in again); ensure no hydration errors and that SSR output is consistent with the chosen approach (e.g. neutral shell vs. server-derived auth prop).

---

## References (from analysis)

- [findtorontoevents.ca](https://findtorontoevents.ca/) — live site
- [Next.js – React Hydration Error](https://nextjs.org/docs/messages/react-hydration-error)
- [Josh Comeau – The perils of rehydration](https://www.joshwcomeau.com/react/the-perils-of-rehydration/)
- [Stack Overflow – React hydration error (Next.js)](https://stackoverflow.com/questions/73162551/how-to-solve-react-hydration-error-in-nextjs)
- [JAM – Hydration failed: initial UI does not match](https://jam.dev/blog/articles/react-hydration-failed-initial-ui-does-not-match/)
- [TanStack Start – Hydration errors](https://tanstack.com/start/latest/docs/framework/react/guide/hydration-errors)
