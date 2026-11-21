# QA Market Validation: reconcile its counters, quarantine the mis-resolved bond, fix the stale JPY leg

**Date:** 2026-11-21
**Files:** `tools/qa_ledger.py`, `tools/live_pnl_tracker.py`,
`.github/workflows/qa-market-validation.yml`, `tests/test_qa_ledger_rules.py`

## What was broken

`QA Market Validation` had been red on every hourly run (8/8 in the window), and its
red could not be explained by its own output:

1. **Counters that do not reconcile.** Run 44849286981 printed `18 flags (12
   critical)` while the per-class lines summed to 11. `PNL_OUT_OF_BOUNDS` was
   appended as a flag and put in the critical set, but never counted in
   `by_class`. The missing one was `MBS` (BOND), entry 8.295 → current 58.215 =
   **+601.81%**.
2. **A stale JPY leg.** Every JPY cross was ~0.7% away from the independent feed
   while every non-JPY pair agreed within 0.05pp. Git history shows why: at
   22:26 and 23:26 the tracker held USDJPY **158.512** (what the feed still
   reports), then at 00:43 it wrote **159.707** and stayed pinned there for two
   hours while EURUSD/USDCAD moved normally. `yfinance.fastInfo` served a frozen
   tick; 11 of 23 crosses then breached the 0.5pp FX tolerance.
3. **The artifact was never committed.** The workflow had
   `permissions: contents: read` and no commit step, so
   `audit_dashboard/data/qa_market_validation.json` on `main` was from
   **2026-11-15** with `n_picks: 4390` while the job was printing 183 picks. The
   dashboard panel read a six-day-old verdict.

## What changed

1. **`qa_ledger.py`** — `out_of_bounds`, `self_inconsistent`, `quarantined` and
   `quarantine_leak` counters are now incremented and printed, so the per-class
   lines always explain the critical total. Two checks were added: a published
   PnL must be implied by the row's *own* `entry_price`/`current_price`
   (`SELF_INCONSISTENT`, critical; 0 rows today), and a row marked
   `quarantined` must publish no PnL (`QUARANTINE_LEAK`, critical) instead of
   being reported as merely unpriced.
2. **`live_pnl_tracker.py`** — FOREX quotes are cross-checked against
   `alpha_engine.forex_price_failover`; when the two disagree by more than 0.25%
   the failover feed wins and the disagreement is logged. A BOND row whose live
   move exceeds 100% is a symbol-resolution collision, so it is published as
   `current_price: null, pnl_pct: null, quarantined: true` with a warning — the
   panel no longer shows +602%, and the gate verifies the quarantine.
3. **`qa-market-validation.yml`** — `contents: write` plus an `if: always()`
   step that commits the artifact (with retry), even when the gate is red: a red
   gate's flags are exactly what the panel should display.

## Verification

- `pytest tests/test_qa_ledger_rules.py tests/test_detect_merge_hybrid.py -q` →
  **29 passed** (6 new: clean pass, out-of-bounds counted and reconciling,
  quarantine accepted, quarantine leak critical, self-inconsistency critical,
  blank TP/SL non-critical).
- Replay of the real 183-pick artifact with network checks disabled:
  `18 flags (12 critical)` → **`7 flags (1 critical)`**, `BOND bounds=1`, and the
  single critical is exactly the `MBS` bound — the summary now explains itself.
- `yaml.safe_load` on the workflow; `contents: write` present.
- The 11 FX mismatches are removed at the source (cross-checked quotes), not by
  widening the 0.5pp tolerance.

## Limits

- The tracker fix only takes effect on its next run (`:24`): until then the
  committed artifact still holds the frozen 159.707.
- The `MBS` entry price in `picks_now_tracker` is still wrong (8.295); the row is
  quarantined rather than repaired. Fixing the emitter is a separate change.
- `blank_tp/sl` (6 EQUITY rows) stays non-critical by the original design.
