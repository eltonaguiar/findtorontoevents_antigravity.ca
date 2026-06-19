# Implementation Plan — Restore the Honest Measurement Layer (P0)

**Author:** claude-opus · 2026-06-19 · **Status:** plan for review (peer-review pending)
**Incident:** `reports/INCIDENT_honest_ledger_frozen_2026-06-19.md`

## Problem (verified)
`at_signal_outcomes` — the verdict-grade honest intrabar ledger that the ENTIRE money-ready program measures against — **stopped getting new rows on 2026-06-12** (row-counts: ~5–7k/day through 06-11 → 1165 on 06-12 → **0 since**), while CI stayed green. Consequences: every per-class verdict (0/9) and the `crypto_rsi5070_us` lead (frozen at n=108) are on a stale cohort, and the lead's n≥150 Jun-25 gate is **unreachable** until inserts resume.

### Root cause (direct-SQL + CI-verified)
- **Honest-ledger inserter is `outcome-resolver.yml`** (hourly `cron '15 */1'`), step **"Active Picks Sync — bridge ACTIVE → CLOSED for signal_outcomes"** — **failing 6/6 recent runs, 0 successes in last 20** since ~06-12. This is the freeze.
- Likely failure mode (same class seen in audit-dashboard's active-picks step): **equity price fetch via yfinance fails on GitHub-runner IPs** (Yahoo rate-limits/blocks cloud IPs; AAPL returns 0 prices → the sync safety-halts "refusing to proceed" rather than mass-skip). EXACT error to confirm (P0-2).
- **NOT** the at_signal_outcomes resolution step: `reresolve_intrabar_signal_outcomes.py --apply` loaded **0 unresolved rows** (existing rows already resolved) → the gap is INSERTS, not resolution. `DB_PASS_BACKUPS` is therefore moot for the freeze.
- **Separate (already FIXED):** `at_pick_outcomes` (a different table, written by `universal_pick_resolver`) froze on a missing DB-cred env on its audit-dashboard step → fixed (commit `e45c434b7`), verified fresh `resolved_at`=2026-06-19 01:12.

## Goals
1. **Un-freeze now** — resume `at_signal_outcomes` inserts (clear the 06-12→now backlog).
2. **Durable fix** — make the inserter robust to GH-runner price-source blocks so it can't refreeze.
3. **Un-mask** — ensure a future freeze surfaces immediately (no green-CI masking).

## Steps

### P0-1 — at_pick_outcomes creds  ✅ DONE
Wired DB secret onto the `universal_pick_resolver` step (`e45c434b7`); verified.

### P0-2 — Confirm exact outcome-resolver failure
Re-run `outcome-resolver.yml` via `workflow_dispatch` (dry_run input) and capture the "Active Picks Sync → signal_outcomes" step log; confirm the price-fetch (yfinance) failure vs any other cause. Acceptance: error text captured + classified.

### P0-3 — Durable price-source fix (the real fix)
Switch the bridge's **equity** price fetch **off yfinance** to the keyed providers already proven healthy in this env — **Finnhub / FMP / Tiingo / AlphaVantage** (keys in ENV per `reference-equity-prices-2026-verified`; `stock_ohlcv` ingress is healthy) — with failover. Crypto path: ensure the Binance→CoinGecko→KuCoin→CryptoCompare failover (CLAUDE.md API rule) engages on HTTP 451.
- Code: the bridge/sync price-fetch helper (identify exact module in P0-2).
- Workflow: add `FINNHUB_API_KEY`/`FMP_API_KEY`/`TIINGO`/`ALPHAVANTAGE` as GH secrets → env on `outcome-resolver.yml` + audit-dashboard active-picks step. **(secrets = operator)**
- Acceptance: a GH run fetches >0 equity prices and inserts rows.

### P0-4 — Immediate un-freeze (bridge the gap while P0-3 ships)
Run the signal_outcomes bridge from a **non-blocked host** (local — equity prices work here; backups creds present) to insert the 06-12→now backlog. **Dry-run first**, confirm price-fetch + row count, then `--apply` with backup-before-mutation. Idempotent. Acceptance: `at_signal_outcomes` `max(created_at)` advances to today; rows/day back to ~5k.

### P0-5 — Un-mask + freshness monitor
- Make the bridge **fail-hard** on price-fetch failure (or assert `rows_inserted > 0`) instead of green-on-empty; keep the safety-halt but make the WORKFLOW red so it's visible.
- Add a freshness assert/monitor: alert if `at_signal_outcomes max(created_at)` is > 2h old (the master-loop H5 coverage check should catch this). Acceptance: a simulated freeze turns CI red / fires the alert.

## Operator items
- Add/verify GH secrets: equity price keys (FINNHUB/FMP/TIINGO/ALPHAVANTAGE); confirm `MYSQL_PASSWORD` present (it is — sibling steps work).
- Approve the un-mask policy (fail-hard on a frozen ledger).

## Verification (end-to-end)
1. `SELECT MAX(created_at), COUNT(*) FROM at_signal_outcomes` advances past 06-12; rows/day ≈ pre-freeze ~5k.
2. `crypto_rsi5070_us` honest n resumes accruing toward 150.
3. `build_intrabar_truth_by_class.py` numbers are live (fresh `generated_at`).
4. `outcome-resolver.yml` goes green WITH non-zero inserts (not green-on-empty).

## Risks & mitigations
- **Production mutation (P0-4):** dry-run first; the bridge does backup-before-mutation; idempotent.
- **Hot-resolver edits (P0-3):** the change is an *additive price-source failover*, not resolution-logic — lowest-risk class; still ship with the shadow-diff discipline.
- **Secrets (P0-3):** operator-gated; do not commit keys.
- **Clock skew (local runs):** resolver stamps use DB `NOW()` (verified) — local box clock is irrelevant.

---

## Peer review — 3-model consensus (LiteLLM proxy paid-mode: paid-mode-large + nvidia-deepseek-v4-pro + deepseek-chat-direct), 2026-06-19

**Consensus verdict: NEEDS_CHANGES** (3/3). Valid critiques + the resulting revisions:

1. **P0-2 is redundant** (3/3) — root cause already verified (6/6 fails + yfinance). Don't gate the fix on re-confirming.
   → **REVISED:** demote P0-2 to "capture the exact error opportunistically *during* P0-4, not as a blocking pre-step."
2. **P0-4 "run from a non-blocked host" is dangerously vague** (3/3) — which host? same code/dep versions? idempotency? rollback? double-insert lock?
   → **REVISED P0-4:** (a) host = THIS local box at the current `main` checkout; (b) **first verify the bridge's INSERT semantics** (must be `INSERT ... ON DUPLICATE KEY UPDATE`/`INSERT IGNORE` or guarded by a unique key) before any apply — if not idempotent, do NOT run; (c) **snapshot `at_signal_outcomes` to `ejaguiar1_backups` first** (explicit, not "backup-before-mutation" handwave) = rollback path; (d) dry-run → diff row count → apply capped (`--max`).
3. **P0-3 failover under-specified + may not help if halt is batch-level** (3/3) — must define provider order, per-call timeout, retry/circuit-breaker, and **validate keys before deploy**; critically, **check whether the safety-halt aborts the WHOLE batch on ANY symbol failure** — if so, switch to **per-symbol skip-with-log** so one bad symbol can't freeze the ledger.
   → **REVISED P0-3:** add key-preflight + per-call timeout + ordered failover (Finnhub→FMP→Tiingo→yfinance-last); **audit the halt granularity (batch vs per-symbol) and make it per-symbol.**
4. **P0-5 "assert rows_inserted>0" is too blunt** (2/3) — false-positives on legit zero-days (holidays / no active signals).
   → **REVISED P0-5:** threshold = `rows_inserted >= 0.5 × trailing-7d-median` (or per-symbol coverage %), not `>0`; and the un-mask must **change the step EXIT CODE** (not just log an assertion) so CI actually goes red; add a **synthetic price-fetch canary from a GH runner** (known-good symbol) to alert on the dependency itself.
5. **NEW (nvidia): backlog-validity gate** — signals from 06-12→now may have expired / outcomes now uncomputable; **blindly backfilling could insert garbage.**
   → **REVISED P0-4:** add a validity filter — only resolve backlog signals whose TP/SL/time-exit is still computable from available bars; flag/skip stale ones.

**Net:** the plan is directionally right (un-freeze + durable price-source + un-mask) but the peer review hardened it on idempotency/rollback (P0-4), failover-granularity (P0-3), and a smarter un-mask predicate (P0-5). Proceed in this order: **P0-4 (idempotency-checked, snapshot-protected) → P0-3 durable → P0-5 un-mask**; P0-2 folded into P0-4.
