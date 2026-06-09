# Due-Diligence Sweep — Gating, Splits, Data Quality, CI (2026-06-09)

Operator asked: verify proper gating + N-limits, reverse-split handling, one-more-pass data quality,
and check GitHub Actions job logs for affected pages + fix if needed.

## 1. Gating + N-limits — SOLID ✓
- **MIN_N_CLASS = 100** enforced (`money_ready_verdict.py:155`, `n_ok = n >= MIN_N_CLASS`).
- **DSR ≥ 0.95 / PBO ≤ 0.55** enforced — anti-overfit validator default-ON, verified biting (8/9
  strategies with ≥20 history rejected).
- **Concentration HHI < 0.25 — FAIL-CLOSED** (`admissibility_pipeline.py:699-728`). This CLOSES the
  CLAUDE.md P0 ("concentration gate not enforced before DSR/SPA → 2 false-Tier-1 PASSes 2026-05-17"):
  both admitting tiers (TIER_CORE, TIER_PROBATION) now require `conc_ok`; a concentrated/single-symbol
  strategy falls through to TIER_INCUBATOR (watch-only, never sized).
- **Per-class emission cap (Option A)** implemented + activated (`non_crypto_policy.py` + `scanner.py`):
  EQUITY 15/d, others 8/d, shadow-lane (`forward_test_only`) bypass, global backstop 40/d. Verified
  it unstarves EQUITY (was blocked under the old global-10 with 16 picks today; now 0/15).
- WF-efficiency floor 0.30 + forward-stability (step 9) present.

## 2. Reverse splits / split-adjustment — WIRED ✓
- Active path: `universal_pick_resolver.py:1169` calls `should_adjust_for_split()` against
  `audit_trail/reverse_split_symbols.py::REVERSE_SPLIT_SYMBOLS` (7 known reverse-split symbols:
  LODE, FFIE, WKHS, KULR, HOLO, GSAT, +1); stamps `_reverse_split_adjusted`.
- `stock_ohlcv` scanned (120d): split-clean — no unadjusted >3×/<0.33× jumps (1 low-cap crypto move only).
- Minor: `outcome_resolver.py:720 get_split_adjustment()` is an ORPHAN (0 callers) — dead code, the
  universal_pick_resolver path is the live one. Low-priority cleanup, no functional gap.

## 3. Data quality — scanned + FIXED the high-priority item
- Ghost rows: **0**. Non-canonical status: **0** (GREEN).
- **FIXED — scale-corruption (the headline):** 7 rows with `ABS(pnl_pct) > 1000%` (range −63,218% to
  +999,999%) from mis-scaled entry/exit prices (e.g., JUPUSDT entry 0.00024 vs real ~0.18; EURUSD
  exit 735 vs real 1.16). Just 4 of them inflated **CRYPTO raw PF from 1.023 → 13.628**. Backed up to
  `ejaguiar1_backups.trading_picks_scale_corrupt_quarantine_20260609T221001Z`, then quarantined
  (`pnl_pct = NULL` + `exit_reason` flag `SCALE_CORRUPT_QUARANTINE_20260609`). CRYPTO raw PF now 1.023;
  0 rows >1000% remain. (The honest surfaces — money_ready_verdict 0.90, intrabar 0.74 — were already
  clean via the read-time `clamp_pnl_pct_for_pick` crypto cap of +500%; this fix cleans raw/ad-hoc reads too.)
- Known/structural (not fixed this pass): 709 terminal-status NULL-pnl (697 recoverable from exit_price
  — Zoo's `backfill_resolved_pnl.py` in PR #557 addresses); 97.8% NULL `opened_at` in at_signal_outcomes
  (the resolver-keyspace gap — DeepSeek's resolver workstream); 44 dup signal-ts groups (minor
  over-emission, the per-class cap + dedup mitigates); 99 dormant scale-corrupt entries (clamp-covered,
  mostly resolved ~0%).

## 4. GitHub Actions (affected-page workflows) — ALL GREEN ✓
audit-dashboard, audit-hourly (db_health), picks-now-refresh, incidents-nightly, multi-asset-scanner,
etf-agent, futures-agent, etf-bond-scanner, daily-scrutiny-engine, walkforward-gate — all latest runs
success. The two real failures earlier today (picks-now rebase race; daily-scrutiny missing scipy)
were already fixed + verified green (`d6a2f31e7c`, `94726fbba4`); masking-lint gate fixed this session
(`a0409be02b`).

## Follow-ups (low priority)
- Root prevention: validate `entry_price` scale vs symbol market price at pick INGEST (reject off-scale)
  so the clamp + quarantine become belt-and-suspenders, not the only defense.
- Remove the orphan `outcome_resolver.get_split_adjustment` dead code.
- Recover the 709 NULL-pnl rows (PR #557 / backfill_resolved_pnl with the chk_pnl_sign_coherence guard).
