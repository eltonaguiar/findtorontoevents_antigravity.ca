# prediction_market_consensus: one promotion verdict, derived not asserted

## The contradiction

Two files carried opposite promotion verdicts for the same strategy:

| File | `promotion_ready` | `min_forward_n` |
|------|-------------------|-----------------|
| `verified_strategies/paper_pilot/prediction_market_consensus_pilot.json` | **true** | 50 |
| `verified_strategies/paper_pilot/prediction_market_consensus_state.json` | false | 150 (+ `max_drawdown_pct` 15) |
| `verified_strategies/paper_pilot/prediction_market_consensus_dashboard.json` | false | (mirrors the state file) |

`promotion_ready` is the flag a human or an automation reads before putting money behind a
strategy. This family's forward replay was REFUTED at 38.2 pct true WR, so a stale `true` is
exactly how something gets deployed.

## Writers and readers

**Writers**

- `tools/prediction_market_consensus_pilot.py` writes the pilot file. Its gate (old) was
  `resolved >= 50 and wr >= 60 and pf >= 1.5`, over `pilot["stats"]`.
- `tools/pmc_pilot_monitor.py` writes the state file and the dashboard. It never assigns
  `promotion_ready`; the dashboard line is literally
  `"promotion_ready": state.get("promotion_ready", False)`.
- `tools/track_pmc_paper_pilot.py` reads the state file and its `promotion_criteria`
  (`min_forward_n` 150, `min_wr` 60, `min_pf` 1.5, `max_drawdown_pct` 15) to decide
  `PROMOTION_ELIGIBLE`.

**Readers**: the dashboard snippet fetches `prediction_market_consensus_dashboard.json`, which
copies the state file's flag. The `/audit` surface lists `prediction_market_consensus` under CRYPTO
with null resolved / zero wins, so it shows nothing from either file. No workflow in `.github/`
runs any of these three scripts.

So the system in practice acts on the **state file** (150, with drawdown) via the dashboard; the
pilot file was a standalone writer that nobody but a reader of the raw JSON consulted, and it used
a weaker gate.

## The arithmetic that decides it

The pilot file's `true` came from `stats.resolved` = 837. But 774 of those 837 resolved picks were
resolved **before** the pilot started (`pilot_started_at` 2026-06-05) - backfilled history, not a
forward sample. Counted forward (resolved on/after the start date):

| Population | n | WR | PF | vs 50 | vs 150 |
|------------|----|----|----|-------|--------|
| Pilot file, all resolved (what the old gate used) | 837 | 64.76 | 2.02 | pass | pass |
| Pilot file, forward only (resolved >= start) | 63 | 47.62 | 1.05 | pass | **fail** |
| Paper log / state forward_n | 110 | 79.09 | 13.20 | pass | **fail** |

And accuracy, which neither gate's n check covers but the criteria do: the forward replay
(`reports/forward_paper_pilot_prediction_market_consensus_20260609T044529Z.json`) is REFUTED at
true WR 38.2 pct against a `min_wr` of 60 - a fail at any n. The pilot's own max drawdown is 69.17
pct (forward-only 39.0 pct) against the 15 pct cap.

At the true forward n (63 or 110), with accuracy applied, `promotion_ready` is **false** under both
thresholds. The pilot file's `true` was wrong; the state file was right.

## The fix

- `tools/prediction_market_consensus_pilot.py`: `PROMOTION_CRITERIA` now mirrors the state file
  (150 / 60 / 1.5 / 15 pct). A new `forward_stats()` restricts the gate to picks resolved on/after
  the pilot start, and the gate applies n, WR, PF **and** drawdown. The gate block is written into
  the file as `promotion_gate`, so the flag is derived from the data on every run.
- `verified_strategies/paper_pilot/prediction_market_consensus_pilot.json`: `promotion_ready`
  corrected to `false`; `min_forward_n` raised to 150 with the drawdown cap; a `promotion_gate`
  block records forward n 63, WR 47.62, PF 1.05, MDD 39.0. The 1016 picks are unchanged.

No investment verdict was changed. The dossier's UNKNOWN/UNMEASURED stands.

## Why the guard exists

`tests/test_pmc_promotion_consistency.py` reads the real committed files and recomputes the
forward sample from the picks list. It fails if `promotion_ready` is true below `min_forward_n`,
below `min_wr`, or if the flag does not match what the forward sample earns under the file's own
criteria; if the pilot, state and dashboard disagree; if the two files' thresholds differ; or if
the generator's constants drift from the state file. A one-time correction without a guard drifts
again - this repo has produced that failure repeatedly.
