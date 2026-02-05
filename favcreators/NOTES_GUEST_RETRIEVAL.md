# Guest User & Starfireara Personal Note Retrieval

## How notes are stored and retrieved

### Backend (PHP + MySQL)

- **get_notes.php**  
  - For **guest** (no user or `user_id=0`): returns notes from table **`creator_defaults`** only (global defaults).  
  - For **logged-in users** (`user_id > 0`): returns `creator_defaults` first, then overwrites with rows from **`user_notes`** for that user.

- **save_note.php**  
  - When **admin** saves (user_id = 0): writes to **`creator_defaults`** (columns `creator_id`, `note`).  
  - When a normal user saves: writes to **`user_notes`** (columns `user_id`, `creator_id`, `note`).

So the **guest** user (and admin, who uses id 0) see notes that come from **`creator_defaults`**, not from `user_notes`.

### Why Starfireara’s note might not be retrieved for guest

1. **Table `creator_defaults`**  
   - Must exist and have a row with `creator_id = '6'` (Starfireara’s id in the app).  
   - If the table is missing or that row doesn’t exist, `get_notes.php` returns no note for Starfireara.

2. **Creator id mismatch**  
   - The app uses creator id **`"6"`** for Starfireara (see `INITIAL_DATA` in `App.tsx`).  
   - The value in `creator_defaults.creator_id` must be exactly **`'6'`** (string) so the app can merge it into the creators list.

3. **API not called or failing**  
   - Guest requests use `get_notes.php?user_id=0`.  
   - If that request isn’t sent (e.g. no auth base), fails, or returns non-JSON (e.g. PHP/HTML error), the app won’t have notes to show.

4. **Local dev without PHP**  
   - When using `tools/serve_local.py`, the **mock** for `get_notes.php?user_id=0` returns a fixture:  
     `{"6": "Guest default note for Starfireara (local mock)"}`  
   - So locally, after login as admin, Starfireara’s personal note should show that text if the app loads notes from the API.

## Checking the database (production)

To see what the guest sees for Starfireara:

```sql
SELECT creator_id, note FROM creator_defaults WHERE creator_id = '6';
```

If this returns no rows, the guest will not see a note for Starfireara until one is saved (e.g. by admin) so that a row with `creator_id = '6'` exists in `creator_defaults`.

## Sign-of-life: status.php

**For the agent:** When DB/credentials need fixing (env vars not seen by PHP, or complex passwords), fix it yourself—e.g. ensure `fc/api/.env` exists on the server via deploy tooling—do **not** ask the user to change `.env` on the server.

To verify the backend can **read** from the database (and that Starfireara's note is there), the agent should call **status.php** (e.g. `https://findtorontoevents.ca/findevents/fc/api/status.php`). It returns JSON with `ok: true`, `read_ok: true`, `starfireara_note`, and `get_notes_sample` if DB read works. The app shows "Database: Connected — read ok. Starfireara note: …" when status is ok. The app tries `/fc/api` first, then `/findevents/fc/api` if the first returns non-JSON.

**creators** and **user_lists** are created and seeded automatically when **get_my_creators**, **save_creators**, or **sync_creators_table** is called; no user or agent action is required. If **creator_defaults** has no row for creator 6, the agent can deploy/call **seed_creator_defaults.php** (or ensure it is run by the deploy flow); do not ask the user to open URLs.

4. **PHP not seeing env vars:** If you set `MYSQL_PASSWORD` in the host control panel but status.php still returns "Access denied", the web server may not pass env to PHP. **Agent: Fix it yourself.** Ensure a `.env` file exists in `fc/api/` on the server (same directory as `db_config.php`): create it from `fc/api/.env.example` and set `MYSQL_PASSWORD` (and other `MYSQL_*` if needed) using deploy tooling—e.g. have `tools/deploy_to_ftp.py` write `fc/api/.env` from `MYSQL_*` env vars or from a local gitignored `.env` during deploy. Do **not** ask the user to manually upload or edit `.env` on the server. Alternatively ensure `fc/api/.htaccess` has `SetEnv MYSQL_PASSWORD ...` (see `.htaccess.example`). Do not commit `.env`.

5. **Complex passwords (Access denied with special chars):** If the password contains `#`, `$`, `"`, `'`, `&`, `!`, or spaces, the host’s env or shell may truncate or mangle it (e.g. `#` treated as comment, `$var` expanded). **Agent: Fix it yourself.** Ensure the password is in `fc/api/.env` on the server with **quotes** so the full value is preserved, e.g. via deploy tooling that writes `.env` from env vars or a secure local file:
   - `MYSQL_PASSWORD="your#p@ss$word"` or
   - `DB_PASS_SERVER_FAVCREATORS="your#p@ss$word"`
   The code reads `.env` with proper quoting and supports both variable names. Do **not** ask the user to manually change `.env` on the server. No regex or length limit is applied to the password in PHP.

## Playwright test

- **Test:** `tests/favcreators-admin-login.spec.ts` → “admin login then Starfireara personal note is retrieved (guest default from backend)”.
- **Steps:** Log in with username **admin**, password **admin** (no spaces), then assert that the Starfireara personal note field contains the fixture text returned by the local mock.
- **Run:** From project root, with `python tools/serve_local.py` running (or let Playwright start it):  
  `npx playwright test tests/favcreators-admin-login.spec.ts`

---

## Why the note is not retrieved on the live site (findtorontoevents.ca/fc/#/guest)

Two things are going on:

### 1. **Note save failed (404)** — backend not reachable

The dialog *"Note save failed: server returned an empty or invalid response (often 404). Use a backend with save_note.php for persistence."* means:

- The app calls `https://findtorontoevents.ca/fc/api/save_note.php` (and `get_notes.php` at the same base).
- The server is returning **404** for that URL, so the backend at **`/fc/api/`** is either:
  - **Not deployed** — PHP files under `favcreators/docs/api/` (e.g. `get_notes.php`, `save_note.php`) must be uploaded to the live server under `/fc/api/`. The deploy script `tools/deploy_to_ftp.py` uploads the whole `favcreators/docs` tree (including `docs/api/`) to `/fc/`; confirm that after deploy, `https://findtorontoevents.ca/fc/api/get_notes.php?user_id=0` returns JSON, not 404.
  - **PHP not executed** — the host may only run PHP in certain directories. If `/fc/api/*.php` is not executed, the server may return 404 or serve raw PHP. Check with your host that PHP runs for `/fc/api/` (or add an `.htaccess`/server config that enables PHP there).
  - **Wrong path** — the app uses `getAuthBase()` which is `origin + "/fc/api"` when the page is under `/fc/`. If the site is actually served from a different path, the API base may be wrong.

Until the server responds with **200 + JSON** for `get_notes.php?user_id=0` and `save_note.php` (POST), notes will not load and saves will show the 404 message.

### 2. **Retrieval: guest uses `creator_defaults` only**

For the **guest** page, the app requests `get_notes.php?user_id=0`. The PHP script returns notes from the **`creator_defaults`** table only. So:

- If **get_notes.php returns 404** (above), the app never gets any notes → Starfireara's personal note field stays empty.
- If **get_notes.php returns 200** but the JSON is `{}` or has no key `"6"`, then there is no row in `creator_defaults` for Starfireara (creator id `"6"`). Fix by inserting/updating a row, e.g. after logging in as admin and saving a note for Starfireara (which writes to `creator_defaults` when `user_id === 0`), or manually:

  ```sql
  INSERT INTO creator_defaults (creator_id, note) VALUES ('6', 'Your default note for Starfireara')
  ON DUPLICATE KEY UPDATE note = VALUES(note);
  ```

### Quick checks on the live site

1. **In the browser:** Open  
   `https://findtorontoevents.ca/fc/api/get_notes.php?user_id=0`  
   - If you see **404** → backend not deployed or PHP not run for `/fc/api/`.  
   - If you see **JSON** (e.g. `{}` or `{"6":"Some note"}`) → backend is reachable; if Starfireara's note is still missing, check `creator_defaults` for `creator_id = '6'`.

2. **In DevTools (Console):** After loading `https://findtorontoevents.ca/fc/#/guest`, look for a message like  
   `get_notes failed: <status> …`  
   That confirms the app requested notes and what response it got.
