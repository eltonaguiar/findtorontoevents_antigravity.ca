# FIX-002 — FTP deploy without certificate verification

**File:** `.github/workflows/alpha-engine-daily-picks.yml`
**Severity:** P0
**Status:** Proposed (not yet applied)

## What was broken
The "Deploy picks to live site" step uploads picks to `findtorontoevents.ca/findstocks/alpha/` via plain `lftp` FTP with:
- `set ssl:verify-certificate no` (certificate verification disabled)
- FTP credentials (`FTP_SERVER`, `FTP_USER`, `FTP_PASS`) passed as step env from repository secrets
- `mput alpha_engine/output/*.json` / `*.md` uploaded unencrypted if FTPS not actually negotiated

This exposes pick data and risks credential interception.

## What to change
1. Replace `lftp` plain FTP with FTPS and **enable** certificate verification: `set ssl:verify-certificate yes` (or `set ftp:ssl-force true`).
2. Do not log FTP credentials; the `_sanitize` pattern from `safe_push.sh` is not present here — add output sanitization or avoid echoing creds.
3. Prefer the existing git-based deploy pattern (`safe_push.sh` + `contents: write`) used by `equities-agent.yml` / `forward-test-new-strategies.yml` instead of FTP, removing FTP dependency entirely.
4. Keep the "Skip if FTP credentials not configured" guard, but fail loudly (not silent `exit 0`) when creds are missing so the deploy is not mistakenly treated as success.

## How to verify
- `python3 -m py_compile` on any embedded script; validate the workflow YAML parses (`yamllint` or a GitHub Actions linter).
- Confirm `set ssl:verify-certificate yes` appears and `no` is removed.
- Confirm no `echo` of `$FTP_PASS` or raw creds in logs.
- Run workflow via `workflow_dispatch` with FTP creds set and confirm deploy succeeds over FTPS with cert verification.

## Related
PR #761 "fix: rotated FTP credentials, no embedded password defaults, verified FTPS" (open, 2026-10-23) addresses the credential portion; this fix completes the certificate-verification + deploy-pattern portion.