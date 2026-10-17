# FavCreators Debug Account Design

## Problem

Google Identity Services does not complete reliably in the shared virtual browser. The
existing FavCreators email registration UI posts to `/fc/api/register.php`, but that
route is not deployed and currently falls through to the SPA HTML shell. A Google-created
account also has no operator-known email password, so email login cannot be used to
inspect user ID 2 (`zerounderscore@gmail.com`).

## Scope

Create a dedicated email/password debug account and copy only the creator-list JSON from
user ID 2. Do not change user ID 2, copy notes, expose an existing password, or bypass
session authorization.

## Design

1. Add `favcreators/docs/api/register.php`.
   - Accept JSON `email`, `password`, and `displayName`.
   - Validate email and the UI's 12-character upper/lower/digit/symbol password policy.
   - Reject duplicate email addresses.
   - Store credentials using the authentication format supported by the deployed login
     endpoint.
   - Create the same secure PHP session shape used by Google sign-in and `login.php`.
   - Return a JSON `user` object; never return the password or password hash.
2. Create a dedicated debug account through the live registration endpoint.
3. Copy only `user_lists.creators` from user ID 2 to the new account. The source row is
   read-only. If the destination row already exists, back it up before replacing it.
4. Log in through the visible email form, add
   `https://tiktok.com/@gurleen_dosanjh`, and capture the `save_creators.php` response.
5. Reload the page and query the authenticated creator list to verify that the creator
   survives a fresh read from the database.

## Error Handling

- Registration failures return a non-2xx status and JSON error.
- Duplicate accounts are never silently reused.
- Clone operations assert exactly one source user-list row and one destination user.
- A failed save or failed reload is reported as a failure, not treated as success based
  on localStorage.

## Verification

- PHP syntax-check the registration endpoint.
- Add targeted endpoint tests for validation, duplicate rejection, session creation, and
  response shape where the repository test harness permits.
- Verify live `session_check.php` reports the debug user's ID after registration/login.
- Verify `save_creators.php` returns success rather than 401/403.
- Verify a new authenticated `get_my_creators.php` response contains
  `gurleen_dosanjh` after reload.

## Deployment

Deploy only the new/changed FavCreators API files needed for registration and the
verification flow. Do not deploy unrelated dirty-worktree changes.
