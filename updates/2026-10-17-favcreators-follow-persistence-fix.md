# FavCreators follow persistence fix — login + save pipeline (2026-10-17)

## Symptom (reported)

On `findtorontoevents.ca/fc/#/guest`, after signing in, adding
`https://tiktok.com/@gurleen_dosanjh` showed the creator **once** in the list,
but a page refresh made it disappear. Reads worked; nothing ever reached the
database.

## What was actually broken (4 independent defects, all verified against production)

1. **`ensure_tables.php` had a PHP parse error in production.**
   Line 135 used short array syntax `json_encode([...])` — a parse error on the
   server's PHP **5.2.17** (`ping.php` reports `phpversion()`).
   Direct probe: `GET /fc/api/ensure_tables.php` returned
   `Parse error: syntax error, unexpected '[' ... on line 135`.
   Every endpoint that `require`s this file fatals with **HTTP 500**:
   `save_creators.php` (the persistence write) and `login.php` (email login).
   Reads were unaffected (`get_my_creators.php` does not include it), which is
   exactly the "appears locally, gone after refresh" symptom: the SPA saves to
   localStorage, the server write 500s silently, and on reload the DB copy wins.
   Introduced by commit `733a86fe22` (2026-05-31).
   **Fix:** `array(...)` instead of `[]`.

2. **`login.php` lost the request body to include-scope variable clobbering.**
   `login.php` read `php://input` and ran `json_decode` *before*
   `require_once ensure_tables.php`, and `ensure_tables.php` (included at file
   scope) assigned the same `$data` variable from the guest-list JSON. By the
   time `login.php` used `$data['email']`, it was the creator list, so the query
   ran `WHERE email = ''` → `{"error":"User not found"}` for **every** login.
   Proven by temporary instrumentation of the deployed file: raw body correct
   (`raw_len: 79`), `json_decode` correct (`email_dump: 'fc.persist...@...'`),
   but `$email === ''` after the include. (Instrumentation removed afterwards.)
   **Fix:** capture `$login_email_value` / `$login_password_value` before the
   `require` block; also renamed `ensure_tables.php`'s `$data` →
   `$guest_seed_data` so no includer can ever be clobbered again.
   Sweep confirmed `login.php` was the only file with this ordering.

3. **`register.php` was missing in production.** The SPA's sign-up form posts to
   `/fc/api/register.php`; the route didn't exist (it fell through to the SPA
   HTML shell), so account creation was impossible.
   **Fix:** created `favcreators/docs/api/register.php` (PHP 5.2-safe): validates
   email + the 12-char upper/lower/digit/symbol policy, rejects duplicates with
   409, stores the credential in the format `login.php` compares against,
   establishes the same `$_SESSION['user']` contract, seeds the account with the
   default creator list, never echoes the password.

4. **The TikTok URL Quick-Add patch was never deployed.** The repo bundle had
   the parser fix from the earlier session
   (`updates/2026-10-17-favcreators-tiktok-url-persistence-fix.md`) but FTP
   comparison proved production's `main-DF_ZQ_dn.js` lacked it (`urlMatch`
   absent, 115 bytes smaller). A line-level diff showed that was the **only**
   difference, so the repo bundle (= prod + patch) was deployed.

Secondary fix while reproducing: `ensure_tables.php`'s test-user seeds
(`bob`, `johndoe`) omitted `created_at`, which the production `users` table
requires (insert failed silently under `error_reporting(0)`), so the seeded
test login could never be used. Seeds now pass `NOW()`.

## Verification (all against production, 2026-10-17)

### API round trip (`login → save_creators → get_my_creators`)

```
[PASS] login.php POST                 HTTP 200  user.id=7
[PASS] session_check                  HTTP 200  logged_in=True user_id=7
[PASS] get_my_creators baseline       HTTP 200  11 creators
[PASS] save_creators (+follow)        HTTP 200  {"status":"success"}
[PASS] fresh read after save          HTTP 200  12 creators, gurleen_dosanjh found: True
[PASS] save_creators (restore)        HTTP 200  {"status":"success"}
[PASS] fresh read after restore       HTTP 200  11 creators, follow removed: True
```

### Real-browser test, 2 test users × 2 add methods
(`node favcreators/tests/follow_persist_ui_test.js` → `ALL PASS`, exit 0)

Every phase first **resets the target handle out of the DB** and asserts a clean
baseline, so a pass can never be a pre-existing row:

| Phase | Baseline | Save | After RELOAD (fresh DB read) |
|---|---|---|---|
| User A / Quick-Add URL | 10, absent | `{"status":"success"}` | 11, `gurleen_dosanjh` present |
| User B (registered at runtime) / Quick-Add URL | 12, absent | `{"status":"success"}` | 13, `gurleen_dosanjh` present |
| User B / regular "Add Creator" form | 12, absent | `{"status":"success"}` | 13, `charlidamelio` present |

Also asserted each phase: SPA session active, creator enters SPA state,
localStorage mirror matches, no page errors.

`node favcreators/tests/quick_add_url_test.js` — passes (bundle patch present).

### Probe cleanup

Temporary diagnostic `_diag_users.php` and the instrumented `login.php` were
replaced/removed; production `login.php`, `ensure_tables.php` are byte-identical
to this repo after the fix (verified by FTP RETR + sha256).

## Files changed

- `favcreators/docs/api/ensure_tables.php` — parse-error fix (array()), seeds
  supply `created_at`, `$data` → `$guest_seed_data`
- `favcreators/docs/api/login.php` — capture credentials before includes
- `favcreators/docs/api/register.php` — new (SPA sign-up route, session-backed)
- `favcreators/tests/follow_persist_ui_test.js` — new end-to-end UI test
- (deployed separately, change already in repo from earlier session:
  `favcreators/docs/assets/main-DF_ZQ_dn.js` TikTok URL parser)

## Known remaining caveats (not in scope of this fix)

- Other API files still use PHP 5.4+ syntax and fatal on PHP 5.2 when called:
  `batch_update_streamer_last_seen.php`, `ft_test_db.php` (out of the
  login/save path; `ft_test_db.php` was also a candidate diagnostic).
- `login.php` compares passwords as stored (no hash) — matches the deployed
  contract; hashing would need a coordinated credential migration.
- The SPA also calls `PUT /fc/api/creators/mine`, which does not exist on the
  server (404, caught and logged client-side); `save_creators.php` is the
  authoritative write path.
