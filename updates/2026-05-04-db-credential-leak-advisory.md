# Security advisory — `ejaguiar1_memecoin` password leak in repo

**Severity:** medium-high (publicly readable repo + live password)
**Status:** confirmed reproducible 2026-05-04
**Surface:** 5 files in main branch, plaintext credential

> **NOTE:** This advisory deliberately does **not** quote the leaked password value. The literal credential is committed in the 5 files listed below — operators with repo access can grep for it. Republishing it inline here would marginally widen the exposure.

## What's exposed

The MySQL credential `ejaguiar1_memecoin / <REDACTED>` is committed in plaintext at:

| File | Line | Use |
|---|---|---|
| `db_sync.py` | 62 | DB sync table tuple |
| `live-monitor/api/goldmine_tracker.php` | 725 | `mysqli(...)` direct connect |
| `live-monitor/api/pair_fingerprint.php` | 59 | `mysqli(...)` direct connect |
| `tmp/check_all_dbs.php` | 6 | DB check tuple |
| `tmp/export_memecoin.php` | 3 | DB export connect |

## Validation (this session)

Connected to `mysql.50webs.com` directly with these creds. Confirmed:
- Authentication succeeds → password is current and active.
- `ejaguiar1_memecoin.mc_winners` has **476 rows** (Hermes's earlier 260 estimate was incomplete).
- The user's existing IP allowlist on the host is what currently makes this less catastrophic — but anyone reaching the IP from a whitelisted network with the leaked creds gets full access.

## Why this is not just "Hermes added it"

Hermes Agent #3 wrote `scripts/mc_resolution_tracker.py` with `os.environ.get('MEMECOIN_DB_PASS', '<leaked-pw>')` — a hardcoded default copy of the existing committed password. Those scripts are **still stashed locally**, not committed. Even if those land later, the leak surface doesn't grow — the password is already public in 5 files.

The actual problem is the 5 pre-existing committed instances.

## Recommended remediation (user-side, not committable from here)

Step 1 — **Rotate the password on `mysql.50webs.com`:**
```sql
-- via cPanel / phpMyAdmin / mysql admin shell:
ALTER USER 'ejaguiar1_memecoin'@'%' IDENTIFIED BY '<new_strong_random_password>';
FLUSH PRIVILEGES;
```

Avoid passwords containing `!` `$` `\` `'` `"` — cPanel-side shells frequently escape or strip these and the password actually saved differs from what was typed (this session encountered exactly that — the "rotated" password the user provided did not authenticate, suggesting cPanel transformed the input).

Step 2 — **After rotation, validate the new password** by connecting from an IP-allowlisted host before relying on it. Don't commit anything against an unvalidated password.

Step 3 — **Migrate the 5 files to env-var-driven config in a follow-up PR** (only after Step 2 confirms the new password works):
- Python: read `MEMECOIN_DB_PASS` from `os.environ`; raise on absent (no insecure default).
- PHP: read `getenv('MEMECOIN_DB_PASS')`; require non-empty; otherwise fail closed.
- Provision the new password via the host's environment (cPanel → "Setup Site" → environment variables, or via `.htaccess` `SetEnv`, or via a non-tracked include file like `live-monitor/api/secrets.local.php` already in `.gitignore`).
- Provision the new password as a GitHub Actions secret `MEMECOIN_DB_PASS` for any workflow that needs it.

Step 4 — **Audit-log past commits with the leaked password:**
The plaintext is in git history. Even after Step 3, the *historical* leak persists in the public repo's git log forever. Two options:
- **Accept the historical leak** (after rotation, the historical password is dead — preferred for a small-team / non-regulated context).
- **Or rewrite history** with `git filter-repo` or BFG to scrub the password from all commits, then force-push (destructive — every clone needs to re-fetch; CI tags / releases referencing old SHAs may break). **Not recommended unless the historical password is high-value across multiple services.**

## What this PR contains

This PR is the **advisory only**. Do not bundle the migration code with the advisory — the migration must follow the rotation (otherwise the env-var-loaded code points at the still-committed password and nothing actually changes on the server).

## Sequence

1. **Now (advisory committed):** This file lands on main, alerting any operator running production from this branch.
2. **User-side, manual:** Rotate the password on `mysql.50webs.com`. Provision new password as `MEMECOIN_DB_PASS` env on host + GH Actions. **Validate connectivity with the new password before announcing rotation complete.**
3. **Follow-up PR (after Step 2):** Migrate the 5 committed files to env-var reads. CI smoke-tests the live PHP endpoints (`live-monitor/api/goldmine_tracker.php`, `pair_fingerprint.php`) for non-zero `ok=true` after the migration.
4. **Optional:** Same env-var split for other database creds. Quick grep:

```
git grep -nE "password\\s*=\\s*['\"][^'\"$]+['\"]" -- '*.py' '*.php'
```

…will find similar default-credential patterns for `ejaguiar1_stocks`, `ejaguiar1_sportsbet`, etc. that should be lifted to env at the same time.

## Hermes-side note (mc_winners scripts)

Hermes #3's `scripts/mc_resolution_tracker.py` / `mc_inverted_strategy.py` / `meme_coin_backtest.py` are currently **stashed only**. Their factor analysis was on a biased sample (257 of 476 rows; ~86% had broken resolution tracking; only 10 wins). **Don't promote any "inverted strategy" or factor weights derived from that sample** — sample size and resolution bias make the numbers unreliable. Resolution-tracker logic itself is sound and worth rebuilding cleanly with env-var creds + an OHLCV backfill that resolves all 476 rows before any strategy claim.
