# Phase 0 — Non-Crypto Outcome Resolver Fix Plan

**Date:** 2026-05-18
**Author:** read-only investigation subagent (Opus 4.7)
**Status:** PLAN ONLY — no production code changed. Keystone blocker for any money-ready edge claim.
**Files inspected:** `alpha_engine/outcome_resolver.py` (3,398 lines), `alpha_engine/forward_validator.py` (3,725 lines), memory note `feedback_noncrypto_resolver_live_close_bug.md`.

---

## 0. Scope of the bug, restated

5 of 6 non-crypto classes (EQUITY / FOREX / ETF / COMMODITY / BOND / FUTURES) close picks with `pnl_pct=0.0` placeholders and frequently NULL `closed_at`. Catalog evidence: of 61,101 picks/30d, 41,180 NULL `closed_at`, 11,225 `pnl_pct=0` placeholders, ~10,442 real outcomes (~96% CRYPTO). This makes those classes statistically unmeasurable. The crypto path works.

Two distinct resolution code paths exist and they do NOT agree on field semantics:

| Path | File | Writes `closed_at`? | Resolution method |
|---|---|---|---|
| Crypto live forward-tracking | `forward_validator.py` | **YES** (`:1363`) | TP/SL/trailing/max-hold bar checks against fetched OHLC |
| Non-crypto retroactive resolver | `outcome_resolver.py` | **NO** (writes `resolved_at` only) | yfinance OHLC bar-replay + retry/breakeven fallback |

---

## (a) Root-cause autopsy — file:line

### RC-1 — Resolver never writes `closed_at` (the NULL-`closed_at` root cause)

`resolve_single_pick` in `outcome_resolver.py` sets, on every successful resolution path:

- `outcome_resolver.py:1029` — `pick["resolved_at"] = datetime.now(timezone.utc).isoformat()`
- `outcome_resolver.py:964` — same in the breakeven/failed path.

**`closed_at` is never assigned anywhere in `outcome_resolver.py`.** A repo-wide grep confirms zero `closed_at` writes in that file; every `closed_at` hit in `forward_validator.py` (`:1363`, `:2089-2090`, etc.) is the crypto path. `_write_outcomes_to_mysql` (`:1906-1916`) inserts into `at_pick_outcomes` with columns `(pick_id, symbol, strategy, asset_class, status, resolution_method, pnl_pct, resolved_at, resolver_version)` — **no `closed_at` column at all**. And at `:1944` it derives `resolved_at` by reading `pick.get("closed_at") or pick.get("exit_date")` — i.e. it *reads* a field the resolver never *wrote*, so it always falls through to `now_str`.

Result: any pick whose outcome comes from `outcome_resolver.py` (the non-crypto majority) lands with `closed_at` NULL in whatever store keys on that column, because nothing upstream populates it. The crypto path writes `closed_at` at `forward_validator.py:1363` so crypto is unaffected — exactly matching the "96% of real outcomes are CRYPTO" catalog finding.

### RC-2 — `pnl_pct=0.0` placeholder is written by *design* on three non-crypto paths

The resolver writes `pnl_pct = 0.0` and returns early — a legitimate placeholder, but it permanently parks the pick as unmeasurable on these three branches:

1. **Retry-needed, OHLC present but no TP/SL touch & pick too young** — `outcome_resolver.py:888-893`. Increments `_resolve_retry_count`, sets `_resolve_retry_needed=True`, `return pick` with `pnl_pct` untouched (stays 0.0/None).
2. **No OHLC window at all (yfinance gap / weekend / delisted)** — `outcome_resolver.py:898-912`. Same retry-increment, `return pick`.
3. **Breakeven force-close after `MAX_RESOLVE_RETRIES=3`** — `outcome_resolver.py:939-990`. Explicitly sets `pick["exit_price"] = entry`, `pick["pnl_pct"] = 0.0` (`:961-962`), `exit_reason="RESOLVE_FAILED_MAX_RETRIES"`, `status="FLAT"`.

So a non-crypto pick that yfinance cannot OHLC-resolve within 3 resolver passes is **permanently** stamped `pnl_pct=0.0`, `status=FLAT`. That is correct *failure handling* but the volume of it (11,225 placeholders) means the real failure is upstream: **yfinance OHLC fetch is failing at scale for non-crypto symbols**, so the breakeven path is the rule not the exception.

### RC-3 — yfinance OHLC fetch is the actual choke point

`_fetch_yfinance_ohlc_window` (`:406-522`) is the only non-crypto resolution data source. It returns `[]` on: yfinance import failure, network error, `ThreadPoolExecutor` 15 s timeout (`:460-470`), empty history, or missing OHLC columns. An empty list routes the pick into the RC-2 #2 retry/breakeven path. Failure modes that hit non-crypto symbols hard:

- **Symbol-format mismatch.** `_resolve_asset_class` (`:736-741`) and `_is_non_crypto` (`:300-313`) trust the Yahoo suffixes `=X` / `=F`. But picks stored *without* the suffix (e.g. `EURUSD`, `GC`, plain equity tickers tagged `category=forex`) get the right asset class via the `category` field yet the bare symbol is passed verbatim to `yf.Ticker(symbol)` at `:447`. `yf.Ticker("EURUSD")` returns empty history; `yf.Ticker("EURUSD=X")` works. **No symbol normalization happens before the yfinance call.** This is the single highest-yield fix.
- **GitHub Actions geo/rate blocks.** The crypto docstring at `:330-338` already documents that GHA runners get HTTP 451 from Binance; yfinance is similarly rate-limited/blocked on shared runners, so OHLC windows come back empty in CI — the exact environment the hourly resolver runs in.
- **Weekend / delisted symbols** legitimately have no recent bars; expected and handled, but inflates the placeholder count.

### RC-4 — Legacy "close at live spot" bug: status

The memory note `feedback_noncrypto_resolver_live_close_bug.md` (26 days old) cites `outcome_resolver.py:384-405` closing non-crypto picks at live yfinance spot. **This specific bug is already fixed.** Current code (`:845-912`) routes non-crypto picks exclusively through OHLC bar-replay (`_scan_ohlc_for_touch`, `:525-577`) or the retry/breakeven path; the `live_price` branch at `:913-937` is explicitly fenced `elif live_price ...` and only reachable for crypto (`is_non_crypto` is false). The v2/v2.1/v2.2 history in the module docstrings (`:228-257`) confirms this was remediated 2026-04-28 → 2026-05-09. **Do not re-fix it.** The residual damage is RC-1 (`closed_at`) + RC-2/RC-3 (placeholder volume from OHLC fetch failure), not live-spot mislabeling.

### RC-5 — `at_pick_outcomes` schema has no `closed_at` column

`UPSERT_SQL` at `:1906-1916` cannot persist a close timestamp even if the resolver computed one. Any analytics keyed on `at_pick_outcomes.closed_at` will see NULL/absent regardless of code fixes. Schema change required (see scope item 4).

---

## (b) Smallest-safe-PR scope

Recommended split into **two PRs** so the low-risk timestamp fix can ship and be verified before the riskier fetch-reliability work. PR-A is the keystone.

### PR-A — "resolver writes `closed_at`" (low risk, ship first)

Goal: every resolved non-crypto pick carries a `closed_at` timestamp, matching the crypto path's contract.

1. **`outcome_resolver.py` `resolve_single_pick` — successful-resolution block (`~:1024-1031`).**
   Add `pick["closed_at"] = pick.get("closed_at") or pick["resolved_at"]` immediately after the `resolved_at` line. Prefer a replay-derived close time when available: if `pick.get("_replay_bar_date")` is set (TP/SL/TIME replay), use that date as `closed_at` (it is the *real* close moment, not resolver-run time) — fall back to `resolved_at` otherwise. Use `or` so an upstream-supplied `closed_at` is never clobbered.

2. **`outcome_resolver.py` breakeven/failed block (`~:960-990`).**
   In both the `retry_count >= MAX_RESOLVE_RETRIES` finalize branch and the below-cap branch, add `pick["closed_at"] = pick.get("closed_at") or pick["resolved_at"]`. A `RESOLVE_FAILED_MAX_RETRIES` pick is still *closed*; it must carry a close timestamp so it is countable (and excludable via `exit_reason`).

3. **`outcome_resolver.py` `_write_outcomes_to_mysql` (`:1906-1916`, `:1955-1959`).**
   Add `closed_at` to the INSERT column list, the `VALUES` placeholder tuple, and the `ON DUPLICATE KEY UPDATE` clause. Derive the bound value from `pick.get("closed_at")` (now reliably populated by steps 1-2); keep the existing `now_str` fallback. Requires the schema migration in scope item 4 to land first or concurrently.

4. **No behavior change to win/loss classification, thresholds, or the OHLC replay logic in PR-A.** Pure timestamp-population PR.

### PR-B — "non-crypto OHLC fetch reliability" (medium risk, ship second)

Goal: shrink the `pnl_pct=0.0` placeholder population by making `_fetch_yfinance_ohlc_window` succeed for the symbols it currently fails on.

5. **New helper `_to_yfinance_symbol(pick) -> str`** in `outcome_resolver.py`, called inside `_fetch_yfinance_ohlc_window` and `_fetch_yfinance_price` before `yf.Ticker(...)`:
   - If `asset_class`/`category` is `FOREX` and symbol lacks `=X`, append `=X` (e.g. `EURUSD` → `EURUSD=X`).
   - If `COMMODITY`/`FUTURES` and symbol lacks `=F`, append `=F` where the base is a known futures root.
   - Equity/ETF: pass through unchanged.
   This is the highest-yield change for RC-3 — it converts a large slice of "empty OHLC → breakeven 0.0" picks into real resolutions.

6. **Add a cache-file OHLC fallback.** `_fetch_yfinance_price` already falls back to `data/stock_forex_prices.json` (`:391-402`); add the analogous fallback to `_fetch_yfinance_ohlc_window` so CI runs (yfinance geo/rate-blocked, RC-3) can still bar-replay from a committed cache instead of mass-breakeven. If no cache, behavior is unchanged (empty list → retry path) — strictly additive.

7. **Optionally raise `MAX_RESOLVE_RETRIES`** (`:220`) from 3 only if telemetry after PR-A shows picks failing purely on transient yfinance timeouts. Defer until measured.

### Scope item 4 (schema) — `ejaguiar1_stocks.at_pick_outcomes`

`ALTER TABLE at_pick_outcomes ADD COLUMN closed_at DATETIME NULL AFTER resolved_at;`
Run via the standard DB-migration path (DB creds are Windows env vars `DB_PASS_STOCKS` etc. per memory; never hardcode). Nullable so existing rows are unaffected. Land before/with PR-A step 3.

**Out of scope (do NOT touch):** the v2.2 OHLC bar-replay logic, `PNL_WIN_THRESHOLD_BY_CLASS`, `PNL_SANITY_CAP_BY_CLASS`, the crypto `forward_validator.py` path, `BLACKLISTED_STRATEGIES` gates. The live-spot bug from the stale memory note is already fixed (RC-4).

---

## (c) Test plan (no generators run locally)

All verification is `py_compile` + targeted unit tests + dry-run. **Never** run `run_outcome_resolver()` non-dry against live files (it writes `closed_picks.json`); **never** run dashboard generators.

1. **Syntax gate.** `python -m py_compile alpha_engine/outcome_resolver.py` (and `forward_validator.py` if touched). Required green before commit.

2. **New unit test `tests/test_resolver_closed_at.py`** (synthetic fixture picks only — per memory `feedback_test_fixtures_vs_quarantine_data.md`, use synthetic strategy names, not real ones):
   - `test_successful_resolution_sets_closed_at`: build a non-crypto pick with a synthetic OHLC window that hits TP; call `resolve_single_pick`; assert `closed_at` is non-empty AND equals the replay bar date (not resolver-run time).
   - `test_breakeven_failed_pick_sets_closed_at`: pick with empty `ohlc_window`, run `resolve_single_pick` 3× to exhaust retries; assert final pick has `status=="FLAT"`, `exit_reason=="RESOLVE_FAILED_MAX_RETRIES"`, AND `closed_at` populated.
   - `test_upstream_closed_at_not_clobbered`: pick that already has `closed_at`; assert resolver preserves it.
   - `test_crypto_path_unchanged`: a crypto pick resolved via `live_price` still gets `closed_at` and identical `pnl_pct`/`status` vs pre-change (regression guard).

3. **New unit test `tests/test_resolver_symbol_normalization.py`** (PR-B):
   - `test_forex_symbol_gets_x_suffix`: `_to_yfinance_symbol` on a `category=forex` pick with bare `EURUSD` returns `EURUSD=X`.
   - `test_already_suffixed_unchanged`: `EURUSD=X` / `GC=F` pass through.
   - `test_equity_unchanged`: `AAPL` passes through.

4. **Regression pin against existing suites.** Run `tests/test_outcome_resolver_v21_bugfixes.py` and any `tests/test_outcome_resolver*.py` / `tests/test_charter_slippage.py` — must stay green (the v2.1 retry-cap / empty-list-guard behavior must not regress).

5. **Dry-run smoke (read-only).** `python alpha_engine/outcome_resolver.py --dry-run` — `resolve_outcomes(..., dry_run=True)` mutates nothing on disk (verified at `:1141-1171`); confirms the preview path still executes after edits.

6. **DB write path** is gated OFF by default (`PICK_OUTCOMES_MYSQL_ENABLED`, `:1843-1845`); the `_write_outcomes_to_mysql` change is exercised by a unit test that mocks `pymysql.connect` and asserts the SQL string contains `closed_at` in all three clauses — no live DB call in CI.

7. **Acceptance check (post-deploy, in CI logs / dashboard data).** After PR-A lands and one hourly resolver cycle runs on origin/main, pull `audit_dashboard/data/dashboard_data.json` from origin and confirm non-crypto closed picks now carry non-NULL `closed_at`. The NULL-`closed_at` share for non-crypto should drop toward the crypto baseline. PR-B success metric: `pnl_pct=0.0` placeholder count for non-crypto drops materially (target: cut the 11,225 placeholders by the FOREX/COMMODITY share that was failing purely on symbol-format).

---

## (d) Risk register

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | `closed_at` populated from `resolved_at` (resolver-run time) is *later* than the true close, biasing time-bucketed analytics. | Med | Low-Med | Prefer `_replay_bar_date` when present (PR-A step 1); only fall back to `resolved_at`. Document that breakeven/no-OHLC picks carry resolver-run time as a known approximation. |
| R2 | Schema `ALTER TABLE` on the live `at_pick_outcomes` causes a brief lock or breaks an in-flight write. | Low | Med | `ADD COLUMN ... NULL` is fast/online on MySQL; run during a low-traffic window; resolver MySQL write is opt-in/off by default so contention is minimal. |
| R3 | PR-A step 3 ships before the schema migration → INSERT fails on unknown column, resolver MySQL upsert errors. | Med | Low | The upsert is wrapped in `try/except` (`:1955-1963`, `log.debug` on failure) so it degrades gracefully; still, sequence migration first. Gate is OFF by default anyway. |
| R4 | PR-B symbol normalization mis-maps a symbol (e.g. an equity ticker that collides with a futures root) → wrong yfinance series → corrupt PnL. | Low-Med | High | Normalization is class-conditional (only forex→`=X`, only known futures roots→`=F`); equities pass through untouched. The `PNL_SANITY_CAP_BY_CLASS` gate (`:137-147`, `:996-1008`) already catches gross price-unit mismatches and parks them `_pnl_implausible` rather than writing corrupt PnL — a second safety net. Unit-test the mapping table explicitly. |
| R5 | More picks resolving (PR-B) shifts measured WR/PF for FOREX/COMMODITY — could move a class above/below a kill threshold. | High (by design) | Med | This is the *intended* outcome (making classes measurable). Communicate that post-Phase-0 numbers supersede pre-fix numbers; do not trigger any auto-kill on the first post-fix cycle — apply mutate-before-kill protocol. |
| R6 | Peer Claude instances editing `outcome_resolver.py` concurrently → merge conflict. | Med | Low | `set_summary` + `list_peers` + `check_messages` on first turn (per CLAUDE.md); keep the PR small and fast; `grep '^<<<<<<<'` after any stash-pop/rebase. |
| R7 | `closed_picks.json` is large; an unintended non-dry resolver run overwrites live data. | Low | High | Verification uses `--dry-run` and unit tests only; never run the generator/resolver non-dry locally (CLAUDE.md rule). |

---

## (e) Rollback path

- **PR-A (code).** `git revert <PR-A merge sha>` on `main`. Pure additive field write; reverting simply stops populating `closed_at` again — no data corruption, no downstream crash (consumers already tolerate NULL `closed_at` today). The hourly resolver picks up the revert on its next cycle.
- **PR-A (schema).** The `closed_at` column is nullable and additive; leaving it after a code revert is harmless (stays NULL). If full rollback is desired: `ALTER TABLE at_pick_outcomes DROP COLUMN closed_at;` — but recommended to **leave the column** even on revert, since it costs nothing and avoids a second migration on re-apply.
- **PR-B (code).** `git revert <PR-B merge sha>`. Symbol normalization and the OHLC cache fallback are both strictly additive (normalization only *adds* suffixes; cache fallback only fires when yfinance already returned empty). Reverting returns the resolver to "bare-symbol yfinance call" behavior — i.e. back to more placeholders, but no corruption.
- **Data already written.** Picks resolved during the PR-B window carry real `pnl_pct`/`closed_at`; a code revert does not unwrite them. If a normalization bug wrote corrupt PnL, the `_pnl_implausible` flag (R4) isolates those rows for a targeted re-resolution rather than a blanket rollback.
- **Kill switch already exists** for the MySQL write path: set `PICK_OUTCOMES_MYSQL_ENABLED=0` to instantly stop all `at_pick_outcomes` upserts without a deploy (`:1843-1845`).

---

## Appendix — key file:line index

- `outcome_resolver.py:120-131` — `PNL_WIN_THRESHOLD_BY_CLASS` (verified; do not change)
- `outcome_resolver.py:220` — `MAX_RESOLVE_RETRIES = 3`
- `outcome_resolver.py:406-522` — `_fetch_yfinance_ohlc_window` (RC-3 choke point)
- `outcome_resolver.py:525-577` — `_scan_ohlc_for_touch` (v2.2 bar-replay; do not change)
- `outcome_resolver.py:770-1065` — `resolve_single_pick` (PR-A edit sites)
- `outcome_resolver.py:845-912` — non-crypto OHLC/retry branches (RC-2)
- `outcome_resolver.py:913-937` — crypto live-spot branch (RC-4: already fenced, fixed)
- `outcome_resolver.py:939-990` — breakeven/RESOLVE_FAILED block (RC-2 #3, PR-A edit site)
- `outcome_resolver.py:1024-1031` — successful-resolution stamp block (PR-A edit site; writes `resolved_at`, **never `closed_at`** = RC-1)
- `outcome_resolver.py:1906-1959` — `_write_outcomes_to_mysql` UPSERT (RC-5: no `closed_at` column)
- `forward_validator.py:1335-1376` — crypto close block; `:1363` writes `closed_at` (the working contract)
