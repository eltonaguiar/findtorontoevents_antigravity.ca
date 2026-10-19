# FavCreators Debug Account Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a working session-backed email registration route, create a creator-list-only clone of user ID 2, and reproduce whether `@gurleen_dosanjh` persists after reload.

**Architecture:** A new PHP endpoint will validate and create email users while establishing the same `$_SESSION['user']` contract consumed by `session_auth.php`. The debug account will receive a copy of only the source creator-list JSON through an authenticated, one-off operation; the live UI will then exercise the normal `save_creators.php` path and a fresh database read will verify persistence.

**Tech Stack:** PHP 5.x-compatible API code, MySQLi, React/Vite prebuilt frontend, Playwright browser automation, FTPS deployment.

---

## File Structure

- Create `favcreators/docs/api/register.php`: email registration, validation, user insert, and secure session creation.
- Create `tests/favcreators-register-contract.spec.ts`: live/local HTTP contract checks for JSON responses and session behavior.
- Create `updates/2026-10-17-favcreators-email-registration-and-tiktok-persistence.md`: mandatory fix record and verification evidence.
- Use a session-workspace one-off script for the clone operation; do not commit credentials or account data.

### Task 1: Registration Contract Test

**Files:**
- Create: `tests/favcreators-register-contract.spec.ts`

- [ ] **Step 1: Write the failing endpoint contract test**

```ts
import { expect, test } from "@playwright/test";

test("registration endpoint rejects malformed input as JSON", async ({ request }) => {
  const response = await request.post("/fc/api/register.php", {
    data: { email: "not-an-email", password: "short", displayName: "" },
  });
  expect(response.headers()["content-type"]).toContain("application/json");
  expect(response.status()).toBe(400);
  await expect(response.json()).resolves.toMatchObject({ error: expect.any(String) });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
npx playwright test tests/favcreators-register-contract.spec.ts --project="Desktop Chrome"
```

Expected: FAIL because `/fc/api/register.php` falls through to HTML or does not return status 400 JSON.

- [ ] **Step 3: Commit the failing test**

```bash
git add tests/favcreators-register-contract.spec.ts
git commit -m "test: cover FavCreators registration contract" \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 2: Session-Backed Registration Endpoint

**Files:**
- Create: `favcreators/docs/api/register.php`
- Test: `tests/favcreators-register-contract.spec.ts`

- [ ] **Step 1: Implement strict request validation**

The endpoint must:

```php
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('HTTP/1.1 405 Method Not Allowed');
    echo json_encode(array('error' => 'POST required'));
    exit;
}

$data = json_decode(file_get_contents('php://input'), true);
$email = isset($data['email']) ? trim($data['email']) : '';
$password_value = isset($data['password']) ? $data['password'] : '';
$display_name_value = isset($data['displayName']) ? trim($data['displayName']) : '';

if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
    header('HTTP/1.1 400 Bad Request');
    echo json_encode(array('error' => 'Valid email required'));
    exit;
}
if ($display_name_value === '') {
    header('HTTP/1.1 400 Bad Request');
    echo json_encode(array('error' => 'Display name required'));
    exit;
}
if (strlen($password_value) < 12
    || !preg_match('/[A-Z]/', $password_value)
    || !preg_match('/[a-z]/', $password_value)
    || !preg_match('/[0-9]/', $password_value)
    || !preg_match('/[^A-Za-z0-9]/', $password_value)) {
    header('HTTP/1.1 400 Bad Request');
    echo json_encode(array('error' => 'Password does not meet requirements'));
    exit;
}
```

- [ ] **Step 2: Insert the user with the deployed login-compatible credential format**

Use `db_connect.php`, escape the three values with MySQLi, reject an existing email with status 409, and insert role `user`. Do not log or return the password.

- [ ] **Step 3: Establish the authenticated session**

```php
$user_obj = array(
    'id' => (int) $conn->insert_id,
    'email' => $email,
    'role' => 'user',
    'provider' => 'local',
    'display_name' => $display_name_value
);
session_set_cookie_params(86400, '/', null, true, true);
session_start();
$_SESSION['user'] = $user_obj;
$_SESSION['user_email'] = $email;
echo json_encode(array('user' => $user_obj));
```

- [ ] **Step 4: Syntax-check the endpoint**

Run:

```bash
php -l favcreators/docs/api/register.php
```

Expected: `No syntax errors detected`.

- [ ] **Step 5: Run the targeted Playwright contract test**

Run:

```bash
npx playwright test tests/favcreators-register-contract.spec.ts --project="Desktop Chrome"
```

Expected: PASS.

- [ ] **Step 6: Commit endpoint and test**

```bash
git add favcreators/docs/api/register.php tests/favcreators-register-contract.spec.ts
git commit -m "fix: restore FavCreators email registration" \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 3: Surgical API Deployment and Debug Account

**Files:**
- Deploy: `favcreators/docs/api/register.php`
- Create only in session workspace: `files/clone_favcreators_user_list.py`

- [ ] **Step 1: Upload only the registration endpoint**

Use `FTP_TLS` with `FTP_USER` and `FTP_PASS` to upload:

```text
favcreators/docs/api/register.php
-> /findtorontoevents.ca/fc/api/register.php
```

Do not run the full FavCreators deploy in the dirty shared worktree.

- [ ] **Step 2: Verify deployment**

Run:

```bash
curl -sS -D - -X POST 'https://findtorontoevents.ca/fc/api/register.php' \
  -H 'Content-Type: application/json' \
  --data '{"email":"bad","password":"short","displayName":""}'
```

Expected: HTTP 400, JSON content type, and a validation error.

- [ ] **Step 3: Register the dedicated debug account**

Use a unique plus-address under `zerounderscore@gmail.com` and a generated 20+ character password. Keep the password only in the current session and the user's final response; do not write it to the repository or logs.

- [ ] **Step 4: Confirm the session**

In the same cookie jar/browser context, request `/fc/api/session_check.php`.

Expected: `logged_in: true` and the newly assigned nonzero user ID.

- [ ] **Step 5: Clone only the creator list**

The one-off script must connect using locally resolved FavCreators credentials without printing them, select exactly one row from `user_lists WHERE user_id = 2`, and insert/update only the debug account's `user_lists` row. If a destination row exists, copy it to `ejaguiar1_backups` first and assert one affected destination row before commit.

### Task 4: TikTok Persistence Reproduction

**Files:**
- No repository file changes.

- [ ] **Step 1: Log in through the visible email form**

Use the debug email/password and verify `session_check.php` reports the debug user.

- [ ] **Step 2: Add the requested TikTok URL**

Enter:

```text
https://tiktok.com/@gurleen_dosanjh
```

Expected normalized account:

```json
{
  "platform": "tiktok",
  "username": "gurleen_dosanjh",
  "url": "https://www.tiktok.com/@gurleen_dosanjh"
}
```

- [ ] **Step 3: Capture the persistence response**

Wait for the debounced `save_creators.php` request and record its HTTP status/body. Treat 401, 403, non-JSON, or a response containing `error` as failure.

- [ ] **Step 4: Reload from the database**

Clear only the page's `fav_creators` localStorage key, reload, and request the authenticated `get_my_creators.php?user_id=<debug-id>`.

Expected: one creator/account entry contains username `gurleen_dosanjh`.

- [ ] **Step 5: Compare failure point if persistence fails**

Distinguish among:

1. Quick-add parser did not add the account.
2. Frontend did not issue `save_creators.php`.
3. Save endpoint rejected the session/request.
4. Save succeeded but database reload omitted or normalized away the account.

### Task 5: Documentation and Final Verification

**Files:**
- Create: `updates/2026-10-17-favcreators-email-registration-and-tiktok-persistence.md`

- [ ] **Step 1: Document what was broken, changed, and verified**

Include the missing registration route, the session contract, the debug user ID (not its password), the observed TikTok persistence result, and exact validation commands.

- [ ] **Step 2: Run focused verification**

```bash
php -l favcreators/docs/api/register.php
node favcreators/tests/quick_add_url_test.js
npx playwright test tests/favcreators-register-contract.spec.ts --project="Desktop Chrome"
```

Expected: all commands pass.

- [ ] **Step 3: Commit documentation**

```bash
git add updates/2026-10-17-favcreators-email-registration-and-tiktok-persistence.md
git commit -m "docs: record FavCreators TikTok persistence investigation" \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

- [ ] **Step 4: Request code review before any push**

Use the repository review workflow, inspect the branch history for unrelated authors/changes, and do not push this shared branch if it contains changes not created in this task.
