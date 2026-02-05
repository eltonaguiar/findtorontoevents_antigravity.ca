# Debug logging (ejaguiar1_debuglog)

Temporary website logging to a database for debugging. Logs are written only when an **admin** user has turned on "Debug logging" in the sign-in modal.

## Database

- **Database:** `ejaguiar1_debuglog` (remote access enabled)
- **Password:** `debuglog` (or set `DEBUGLOG_MYSQL_*` in `.env`)
- **Table:** `debug_log` (created automatically on first write by `debuglog_ensure_table.php`)

Columns: `id`, `created_at`, `event_type`, `user_id`, `session_id`, `payload` (JSON), `ip`, `user_agent`.

**Schema (manual):** If the table doesn’t exist (e.g. DB user can’t CREATE TABLE), run `debuglog_schema.sql` in phpMyAdmin. The tables `eventslogs` and `favcreatorslogs` in that database are **not** used by the debug log API; only `debug_log` is.

## Env (optional)

In `favcreators/public/api/.env`:

- `DEBUGLOG_MYSQL_HOST` (default: localhost)
- `DEBUGLOG_MYSQL_USER` (default: ejaguiar1_debuglog)
- `DEBUGLOG_MYSQL_PASSWORD` (default: debuglog)
- `DEBUGLOG_MYSQL_DATABASE` (default: ejaguiar1_debuglog)

## Toggle (admin only)

1. Log in as **admin** (email: admin, password: admin).
2. Click **Sign in** (top-right or sidebar).
3. Modal shows **Account** with **Sign out** and **Debug logging (database)** checkbox.
4. Check the box to turn on; uncheck to turn off. State is stored in session.

## Event types logged (when enabled)

- **event_clicked** – User clicked a link that looks like an event (eventbrite, /event, ticket).
- **heart_click** – User clicked the heart to save an event (payload: user_id, event_id, has_user).
- **save_event_success** – Event was saved to the user’s profile (payload: event_id).
- **save_event_failure** – Save failed (payload: event_id, error).
- **login_success** – Email login succeeded (payload: user_id, provider: email).
- **login_failure** – Email login failed (payload: reason).

## API

- **POST debug_log.php** – Body: `{ "event_type": string, "payload": object }`. Writes only if session user is admin and `debug_log_enabled` is on.
- **POST debug_toggle.php** – Body: `{ "enabled": true|false }`. Admin only; sets session `debug_log_enabled`.
- **POST logout.php** – Destroys session (sign out).
