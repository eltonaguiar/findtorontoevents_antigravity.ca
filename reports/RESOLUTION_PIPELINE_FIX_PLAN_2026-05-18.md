# Resolution Pipeline — Root Causes & Staged Fix Plan — 2026-05-18

3-agent swarm investigation. The briefed "non-crypto 0% resolution" was a stale
Hermes artifact — **live DB: CRYPTO 65%, EQUITY 45%, FOREX 22%, FUTURES 8.7%,
ETF 33%.** Resolution works; it is partial and uneven. Three real defects found.

## Defect 1 — Symbol-format chaos (highest leverage, corrupts every cohort)

`at_raw_picks` has two insert paths with conflicting symbol conventions:
- `sync_all_picks_to_mysql.py:165` `_norm_symbol()` strips `=X` → 839 bare FOREX rows.
- `audit_trail/mysql_client.py:476` passes symbol raw → 6,984 `=X` FOREX rows.

Result: **14 FX instruments split across 2 symbol strings each** (`EURUSD` +
`EURUSD=X` counted as separate cohorts). Plus **1,226 `=F` futures rows
mis-classified** (1,222 UNKNOWN, 3 CRYPTO, 1 FOREX `NG=F`) and 6 junk bare
symbols (`CHF`,`JPY`). `tools/build_pf_registry.py::_norm()` does not strip the
suffix → FX cohorts double-counted in pf_registry.

**Fix:** (a) one-time DB normalization — ~2,086 rows: `=F`→FUTURES (1,226),
`=X`→FOREX (19), bare FOREX→`=X` (~835), quarantine junk (6). **Needs a backup
table + operator confirmation — irreversible UPDATE.** (b) write-time: a shared
`canonicalize_symbol()` in `asset_classification.py`, called by all 3 writers;
make `=F`/`=X` suffix override category hints; fix `build_pf_registry._norm()`.

## Defect 2 — FUTURES 8.7% resolution = orphan source

Not a symbol/price-feed bug (18/18 FUTURES symbols test-fetch fine on yfinance).
**86% of FUTURES rows (2,355/2,743) come from `alpha_engine_unified`** — a
source whose pick JSON is NOT registered in `universal_pick_resolver.py`
`SYSTEM_SOURCES`. The resolver never sees those picks; they sit OPEN forever
(age 17-37 days, far past the 96h/14d max-hold). Resolver-registered FUTURES
sources resolve at 47-100%.

**Fix:** wire `active_picks_sync` into CI (covers ALL orphan sources, all
classes — see Defect 3) + a one-time backlog sweep of the 2,505 past-max-hold
OPEN FUTURES rows. Optionally register `alpha_engine_unified`'s JSON in
`SYSTEM_SOURCES` if it writes one.

## Defect 3 — `active_picks_sync` writer is dry-run only

`alpha_engine/active_picks_sync.py` is the only MySQL-native resolver, but
`.github/workflows/audit-dashboard.yml:382-406` runs it without `--apply` and
only for CRYPTO/EQUITY. PR #2/#3 never shipped. Two code bugs block enabling it:
- **Bug 1:** `apply_transition` UPDATE `WHERE status='OPEN' OR NULL` but
  `fetch_active_picks` selects `OPEN`+`ACTIVE` → every `ACTIVE` row's UPDATE
  matches 0 rows yet still gets JSON-appended → DB/JSON divergence.
- **Bug 2:** `fetch_live_prices` silently returns `{}` on a wrong-symbol-format
  or yfinance-outage batch → all rows marked `no_price`, step exits green.

**Staged fix (swarm-vetted — deepseek+kilo: do not flip straight to prod):**
- **Stage A (safe, now):** extend the workflow `active_picks_sync` step to
  dry-run ALL asset classes + `pip install yfinance`. No writes — produces
  non-crypto verdict files for inspection.
- **Code fixes (prereq for B):** Bug 1 — UPDATE WHERE accepts `OPEN`+`ACTIVE`;
  append only DB-confirmed rows. Bug 2 — fail-loud (raise in APPLY mode) when a
  non-empty non-crypto symbol set yields 0 prices.
- **Stage B (gated):** add `--apply` + `ACTIVE_PICKS_SYNC_APPLY=1`, `--max-rows
  500` cap, shadow-diff log, after 3-5 clean Stage-A cycles. Keep the OPEN-only
  WHERE clause (no-reopen guard) and WON/LOST/EXPIRED whitelist.

## Recommended order

1. **Stage A** workflow edit + the 2 `active_picks_sync` code-bug fixes (safe,
   surgical, no production writes) — one focused tested PR.
2. **Symbol-format write-time fix** + `build_pf_registry._norm()` fix.
3. **DB symbol normalization** (~2,086-row UPDATE) — backup first, operator
   confirms.
4. **Stage B** writer flip after 3-5 clean Stage-A cycles.
5. FUTURES backlog sweep once the writer is live.

Also relevant (peer infra audit, `infra_fragility_audit_2026_05_18.md`):
asset-class agents fail-open green on 0 picks; ~147 `yf.*` callers bypass the
existing `ohlcv_failover.py`. Same theme — fix fail-open masking alongside.

*Investigation: 3 parallel subagents + a 3-engine swarm-plan
(`swarm_runs/resolution-fix-plan/`). No production code edited in this pass.*
