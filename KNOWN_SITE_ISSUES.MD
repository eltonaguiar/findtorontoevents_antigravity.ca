# Known Site Issues

This document tracks known issues for **findtorontoevents.ca** and related pages. Use it for triage, planning fixes, and avoiding duplicate work.

---

## Navigation / Menu

### 1. Menu items don’t work on pages other than the main page

**Status:** Known  
**Scope:** Any page that is not the site root (e.g. `/index.html`, `/`).

- The **Quick Nav** menu (hamburger, top-left) and its links are implemented on the **main page** (`index.html`).
- On other site pages (e.g. `/2xko/`, `/findstocks/`, `/MENTALHEALTHRESOURCES/`, subpages), the menu either:
  - Does not appear, or  
  - Appears but links/behavior are broken (e.g. wrong base path, relative URLs, or missing script context).

**Impact:** Users on subpages cannot use the same navigation as on the homepage.

**Possible causes:** Nav is only injected on the root `index.html`; subpages may use different HTML/scripts or relative URLs that break when not at `/`.

---

### 2. Certain pages (e.g. FavCreators) don’t have the menu

**Status:** Known  
**Scope:** FavCreators and any other separately built apps/sections.

- **FavCreators** is a separate app (Vite/React) with its own `index.html` and build. It does **not** include the main site’s Quick Nav menu.
- Other standalone sections (e.g. Next.js or static subsites) may also lack the menu if they don’t include the same nav markup/scripts.

**Impact:** No consistent way to jump back to the main events page or to other network links from FavCreators (and similar pages) without using the browser back button or typing the URL.

---

## FavCreators / Starfireara note

### 3. Guest page note empty until DB configured and seeded

**Status:** Fixed in code; host config required for note to show.

- The app and API are deployed and **PHP 5.2 compatible**; the API under **`/findevents/fc/api/`** returns JSON. The app automatically tries `/fc/api` then `/findevents/fc/api` when the first returns non-JSON.
- For the **guest** Starfireara “Personal note” to show:
  1. **DB credentials** — The host must set `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE` (or fix `favcreators/docs/api/db_config.php`) so `status.php` and `get_notes.php` can connect. If you see “Access denied” in `status.php` JSON, fix credentials.
  2. **Seed default note (one-time)** — Open `https://findtorontoevents.ca/findevents/fc/api/seed_creator_defaults.php` (or `/fc/api/seed_creator_defaults.php` if that path works) to insert a default note for creator 6. Or log in as admin and save a note for Starfireara (writes to `creator_defaults`).
- See **favcreators/NOTES_GUEST_RETRIEVAL.md** for full flow and sign-of-life checks.

---

## Adding or Updating Issues

- **Title:** Short, descriptive.
- **Status:** e.g. Known, In progress, Fixed, Won’t fix.
- **Scope:** Which URLs/sections are affected.
- **Impact:** User-visible effect.
- **Possible causes / notes:** Optional; add when known.

---

*Last updated: 2026-02-01*
