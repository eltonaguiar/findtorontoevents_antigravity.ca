# DB Creds → GitHub Secrets Migration — Scope

**Date:** 2026-06-02
**Source:** `reports/peer_claude-OWNERSHIP_QWEN_PENDING_WORK_2026-05-31.md` item #1 (DEFERRED, deepseek P1)
**Priority:** P1 (security)
**Source memory:** [[project-qwen-ownership-2026-05-31]]

## What's already in place (good)

Most scripts already use `os.environ.get()` with a fallback default. The pattern is:

```python
DB_HOST = os.environ.get("DB_HOST", "mysql.50webs.com")
DB_USER = os.environ.get("DB_USER", "ejaguiar1_stocks")
DB_NAME = os.environ.get("DB_NAME", "ejaguiar1_stocks")
# Password: try multiple env vars, fall back to convention
pw = (
    os.environ.get("DB_PASS_STOCKS")
    or os.environ.get("AUDIT_DB_PASS")
    or os.environ.get("DB_PASS")
    or os.environ.get("MYSQL_PASSWORD")
    or "stocks1234560"  # last-resort convention
)
```

Files that already follow this pattern (verified 2026-06-02):
- `alpha_engine/outcome_resolver.py:1845-1856, 1978-1991`
- `alpha_engine/mysql_trading_sync.py:92-101`
- `alpha_engine/forward_test.py:75-80` (PR #414 — just shipped)
- `audit_trail/sign_coherence_check.py:48-50` (PR #434 — just shipped)

## What still has a hardcoded fallback

Only one file I found with a hardcoded `stocks1234560` fallback that's NOT wrapped in an env-var check:

- `alpha_engine/rigorous_backtest_harness.py:109`
  ```python
  pw = os.environ.get('DB_PASS_STOCKS', 'stocks1234560')
  ```
  This is a one-line fix: remove the `'stocks1234560'` default and let the call fail loudly if env is unset.

## What still leaks host/user in git history

`alpha_engine/forward_test.py:74-76` (just shipped in PR #414):

```python
DB_HOST = "mysql.50webs.com"
DB_USER = "ejaguiar1_stocks"
DB_NAME = "ejaguiar1_stocks"
```

These are module-level constants. They should be read from env at call time, not at import time. Trivial fix.

## What needs the GitHub Secret wiring

The repo already has 2 DB-related env vars being read:
- `MYSQL_PASSWORD` / `AUDIT_DB_PASS` / `DB_PASS_STOCKS` (multiple names, all the same)
- `DB_HOST` (read by outcome_resolver + mysql_trading_sync)
- `DB_USER` (read by outcome_resolver + mysql_trading_sync)
- `DB_NAME` (read by outcome_resolver + mysql_trading_sync)

**Proposed canonical mapping:**

| GitHub Secret | Env var | Default fallback | Used by |
|---|---|---|---|
| `STOCKS_DB_HOST` | `DB_HOST` | `mysql.50webs.com` | outcome_resolver, mysql_trading_sync |
| `STOCKS_DB_USER` | `DB_USER` | `ejaguiar1_stocks` | outcome_resolver, mysql_trading_sync |
| `STOCKS_DB_NAME` | `DB_NAME` | `ejaguiar1_stocks` | outcome_resolver, mysql_trading_sync |
| `STOCKS_DB_PASS` | `DB_PASS_STOCKS` / `AUDIT_DB_PASS` / `DB_PASS` / `MYSQL_PASSWORD` | (no fallback — fail loud) | all DB consumers |
| `BACKTESTS_DB_PASS` | `DB_PASS_BACKTESTS` | (no fallback — fail loud) | backtests-side scripts |

## Migration steps (operator-run, not in this session)

1. **Add the 4 GitHub Secrets** to the repo (`STOCKS_DB_HOST`, `STOCKS_DB_USER`, `STOCKS_DB_NAME`, `STOCKS_DB_PASS`) via repo settings.
2. **Pick one canonical password env var name.** Recommend `DB_PASS_STOCKS` (already in use by rigorous_backtest_harness + others). Remove the other aliases in a follow-up PR.
3. **Update all workflow files** (`.github/workflows/*.yml`) to pass the env vars from secrets to jobs. Verify the existing sign-coherence-gate.yml + verified-pilot-daily.yml + 50+ others.
4. **Add a `_resolve_db_password()` helper** to `alpha_engine/db_credentials.py` (new file) that does the env-var lookup once and is imported by every script. This is a low-risk refactor.
5. **Remove the `stocks1234560` fallback** from `rigorous_backtest_harness.py:109` and the constants in `forward_test.py:74-76`. These should fail loud if env is unset, not silently use a hardcoded password.
6. **Audit `dbpasses.txt`** at `/home/eaguiar2015/dbpasses.txt` — confirm it's in `.gitignore`. If not, add it.

## Risk

- If the env var is unset and a script tries to run locally without the secret, the script will fail. This is the correct behavior.
- If a workflow forgets to pass the env var, the workflow will fail. This is also correct.
- The only risk is the cron jobs that read the env from the operator's local shell — those need the env in `~/.bashrc` or similar. Document this in the migration README.

## Why this is P1 (security) and not P2 (cleanup)

- The hardcoded `stocks1234560` fallback in `rigorous_backtest_harness.py` is in a public repo. If the DB ever moves off 50webs or the password rotates, every local consumer will silently use the old password.
- The `forward_test.py` constants leak the host+user into git history permanently.
- Anyone with read access to the repo can read these constants and attempt to use them with the public password convention.

The risk is low (the convention is documented anyway), but the practice is wrong. Cleaning it up prevents future drift.

## Files to touch (estimate)

- `alpha_engine/db_credentials.py` (new, ~30 lines)
- `alpha_engine/rigorous_backtest_harness.py` (1 line)
- `alpha_engine/forward_test.py` (3 lines, in PR #414 fix-up)
- `.github/workflows/*.yml` (potentially 5-10 workflows that touch the DB)
- `docs/DB_CREDENTIALS_MIGRATION.md` (new, doc + ops runbook)

## Status

**SCOPED. NOT YET EXECUTED.** This is a doc-only deliverable. The actual migration needs operator decision on (a) which env-var name is canonical, (b) where to add the GitHub Secrets, (c) when to remove the fallbacks. A 2-agent review pass is recommended before any secret is added to avoid lockout.
