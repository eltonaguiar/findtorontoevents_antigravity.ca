# Events API Session Validation – Findings & Fix

## Analyst finding

**Issue:** `get_my_events.php` and `save_events.php` did **not** use session validation. They trusted the `user_id` parameter from the client (GET query or POST body). That is a **security and correctness** problem:

- **Security:** A client could read or write any user’s saved events by changing `user_id`.
- **Functionality:** Data could be attributed to the wrong user if the client sent a bad or stale `user_id`.

## Root cause

- **get_my_events.php:** Used `$user_id = isset($_GET['user_id']) ? intval($_GET['user_id']) : 0` and queried by that value.
- **save_events.php:** Used `$user_id = intval($data['user_id'])` from the POST body and performed add/remove for that user.

Neither file started a session nor checked `$_SESSION['user']`.

## Fix implemented

### 1. Session auth helper

- **File:** `favcreators/public/api/session_auth.php`
- **Role:** Starts the session (same cookie params as the rest of the FC API) and exposes `get_session_user_id()`.
- **Returns:** Logged-in user id (int) or `null` if not logged in.
- **Usage:** Any API that must act “as the current user” can `require_once` this file and use the returned id only.

### 2. get_my_events.php

- **Before:** Used `user_id` from `$_GET['user_id']`.
- **After:**
  - Requires `session_auth.php` and uses `get_session_user_id()`.
  - If no session user → **401** and JSON `{ "error": "Unauthorized", "events": [] }`.
  - All reads use the **session user id only**; any `user_id` in the request is ignored.
- **Headers:** Added `Access-Control-Allow-Credentials: true` so browsers send cookies with cross-origin requests when the client uses `credentials: 'include'`.

### 3. save_events.php

- **Before:** Used `user_id` from POST body.
- **After:**
  - Requires `session_auth.php` and uses `get_session_user_id()`.
  - If no session user → **401** and JSON `{ "error": "Unauthorized" }`.
  - All add/remove operations use the **session user id only**; `user_id` in the body is no longer required or used.
- **Request body:** Now only requires `event` (and optional `action`). `user_id` in the body is ignored if present.
- **Headers:** Added `Access-Control-Allow-Credentials: true` for cookie-based auth.

## Behaviour change for clients

| Scenario | Before | After |
|----------|--------|--------|
| No session, any `user_id` | Returned/updated that user’s events | **401 Unauthorized** |
| Valid session | Worked if client sent matching `user_id` | Works using **session user only**; client `user_id` ignored |
| Client sends wrong `user_id` | Could read/write another user’s data | Cannot; server uses session id only |

Clients must send credentials (cookies) so the session is established (e.g. `credentials: 'include'` in fetch). No change to the response shape for successful GET (events list) or POST (status/error).

## Files touched

- **New:** `favcreators/public/api/session_auth.php`
- **Updated:** `favcreators/public/api/get_my_events.php`
- **Updated:** `favcreators/public/api/save_events.php`

## Deployment

Deploy the three files above to the live FC API (e.g. `findtorontoevents.ca/fc/api/`). Ensure the app that calls these endpoints uses cookie-based login and sends credentials so the session is available on the server.

## Recommendation

Consider applying the same pattern to other FC APIs that currently trust client-supplied `user_id` (e.g. creators/notes if they are not already session-scoped), so all user-scoped data is consistently protected by session validation.
