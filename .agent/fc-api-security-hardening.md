# FavCreators API – Security Hardening (Session + Admin-Only Override)

## Problem

- **get_notes.php?user_id=3** (and similar endpoints) allowed any visitor to view or change another user’s data by changing `user_id` in the URL or request body.
- No session checks: the server trusted client-supplied `user_id`.

## Approach

- **Session required** for all user-specific data (notes, creators, link lists, events).
- **Effective user** is always the session user, unless the session user is **admin**, in which case the requested `user_id` is allowed (for viewing/editing any user or guest list).
- **Guest (user_id=0)** is allowed only when the session is unauthenticated (for public guest list/notes) or when the session user is admin.

## Changes

### 1. session_auth.php

- **get_session_user_id()**: returns authenticated user id or null.
- **is_session_admin()**: returns true when `$_SESSION['user']['role'] === 'admin'` or `$_SESSION['user']['provider'] === 'admin'`.
- **require_session()**: 401 and exit if not logged in (for endpoints that must act on behalf of the current user).
- **require_session_admin()**: 401 if not logged in, 403 if not admin, then exit (for maintenance/diagnostic endpoints).

### 2. get_notes.php

- Requires **session_auth**.
- **Not logged in:** only `user_id=0` (guest) is allowed. Any other `user_id` → **403** and empty notes.
- **Logged in:** allowed only for own `user_id`, guest (0), or any `user_id` if **admin**. Otherwise **403**.

### 3. save_note.php

- Requires **session**; **401** if not logged in.
- Saves only to **session user** or to **user_id=0** (global default) if **admin**. Otherwise **403**.

### 4. save_secondary_note.php

- Requires **session**; **401** if not logged in.
- **user_id** is taken from **session only** (body `user_id` ignored).

### 5. get_my_creators.php

- Requires **session_auth**.
- **Not logged in:** only `user_id=0` (guest list) allowed; any other → **403**.
- **Logged in:** allowed only for own `user_id`, guest (0), or any `user_id` if **admin**. Otherwise **403**.

### 6. save_creators.php

- Requires **session**; **401** if not logged in.
- Saves only to **session user** or to **user_id=0** (guest list) if **admin**. Otherwise **403**.

### 7. get_link_lists.php

- Requires **session**; **401** if not logged in.
- Returns lists only for **session user** or for requested `user_id` if **admin**. Otherwise **403**.

### 8. save_link_list.php

- Requires **session**; **401** if not logged in.
- **user_id** from **session only** (body `user_id` ignored).

### 9. delete_link_list.php

- Requires **session**; **401** if not logged in.
- Deletes only lists belonging to **session user** (body `user_id` ignored; `id`/`list_name` must refer to that user’s list).

### 10. get_my_events.php & save_events.php

- Already session-only (no client `user_id`); unchanged.

### 11. status.php

- **require_session()**: only logged-in users can run it (avoids anonymous note-related queries).
- **Note content** (`starfireara_note`, `get_notes_sample`) returned only when **admin**; non-admin get `ok`, `db`, `read_ok`, `notes_count` only.

### 12. proxy.php

- **require_session()**: logged-in users only (prevents open proxy abuse).

### 13. sync_creators_table.php & add_creator_for_guest.php

- **require_session_admin()**: admin only (modify guest list / creators table).

### 14. get_logs.php & view_logs.php

- **require_session_admin()**: admin only (view FavCreators logs or file logs).

### 15. get_all_followed_creators.php

- **require_session_admin()**: admin only (aggregate data across all user lists).

### 16. Maintenance / diagnostic scripts (admin only)

All of the following now call **require_session_admin()** so only admins can run them; unauthenticated or non-admin get 401/403:

- fix_user2_brunitarte_and_dedup.php  
- debug_user2.php, debug_json.php  
- backfill_guest_list.php, get_user2_nocache.php  
- add_brunitarte_to_user2.php, ensure_brunitarte.php, diagnostic_brunitarte.php, emergency_check.php  
- sync_user_lists_from_creators.php  
- run_setup_then_validate.php, validate_tables.php, setup_tables.php, seed_creator_defaults.php  
- clone_to_bob.php, create_bob_user.php, create_bob1_user.php, create_test_user.php  

**fix_user2_list_cli.php** is CLI-only (exits if not `php_sapi_name() === 'cli'`); not web-callable.

## Headers

- **Access-Control-Allow-Credentials: true** added where needed so browsers send the session cookie with cross-origin requests when the client uses `credentials: 'include'`.

## Frontend

- No change required: the app already calls the API with the logged-in user’s id and uses same-origin (or credentials) where needed. The server now enforces that the session user can only access their own data (or any user if admin).

## Verification

1. **Not logged in:**  
   - `get_notes.php?user_id=3` → **403** and empty notes.  
   - `get_notes.php?user_id=0` or no param → guest notes (unchanged).  
   - `get_my_creators.php?user_id=3` → **403**.  
   - `get_my_creators.php?user_id=0` → guest list (unchanged).

2. **Logged in as user 2:**  
   - `get_notes.php?user_id=2` → OK (own notes).  
   - `get_notes.php?user_id=3` → **403**.  
   - `get_my_creators.php?user_id=2` → OK.  
   - `get_my_creators.php?user_id=3` → **403**.

3. **Logged in as admin:**  
   - `get_notes.php?user_id=3` → OK (admin can view any user).  
   - `get_my_creators.php?user_id=3` → OK.  
   - Saving to `user_id=0` (guest list) → OK.

4. **Direct URL / query tampering:**  
   - Changing `user_id` in the URL or body only works for the session user’s own id or, for admin, any id. Otherwise **403** or **401**.
