# Phase 1 — Active-Gate Strengthening

_Ship date: 2026-04-17._

## Problem

Deep-dive analysis of 4,762 closed picks (2026-02-22 → 2026-04-17) showed a
cumulative P/L of **−673.75%** at a 31.5% win rate and PF 0.40. The ledger was
dominated by **CRYPTO (n=4,522, −672.43% cum)**. Two signals emerged that were
actionable without touching individual strategies:

1. **Self-reported confidence is near-noise overall** (Pearson ρ = +0.04) but
   stratifies cleanly:
   - conf 0.65–0.70 (n=1,463): WR **17.6%**, cum −203.79% — worst band
   - conf 0.80–1.00 (n=140):   WR 45.7%, PF **1.62**, cum **+1.17%** — only +EV band
2. **08:00–11:00 UTC is a consistent death window.** 697 picks in that span
   produced a combined −164% P/L (vs the aggregate total still negative but
   materially less bad outside the window).

See the source deep-dive in `docs/strategy_phase1/phase1_gate_backtest_report.txt`
and the ad-hoc analyser at `tools/phase1_gate_backtest.py`.

## What shipped

Two gates added to `audit_trail/quality_gates.py :: passes_active_gate`:

| Gate | Env var | Default | Hard-reject condition (crypto only) |
|---|---|---|---|
| Confidence | `PHASE1_CONF_GATE_ENABLED` / `PHASE1_CONF_GATE_THRESHOLD` | `1` / `0.80` | `confidence < threshold` |
| Time-of-day | `PHASE1_TOD_GATE_ENABLED` / `PHASE1_TOD_GATE_HOURS` | `1` / `8,9,10,11` | `entry_hour ∈ blocked_hours` (UTC) |

Both gates are:
- **Crypto-scoped.** Equity/forex/commodity evidence base is too small to
  justify applying the same filters there. Non-crypto picks flow through as
  before.
- **Shadow-capable.** Set `PHASE1_*_GATE_ENABLED=shadow` to tag picks with
  `_phase1_*_shadow_reject` without rejecting — useful for dry-runs.
- **Env-tunable.** Threshold and hours are adjustable without a redeploy.

## Expected uplift (backtest on the 4,762-pick ledger)

|                  | Baseline | Conf gate | TOD gate | Both |
|---|---:|---:|---:|---:|
| Picks passed      | 4,762 | 391   | 4,006 | 365 |
| Picks blocked     | –     | 4,371 | 756   | 4,397 |
| WR (overall)      | 31.5% | 39.4% | 32.5% | 39.2% |
| PF (overall)      | 0.40  | 0.90  | 0.44  | 0.90 |
| Total P/L         | −673.75% | −0.57% | −507.13% | **−0.54%** |
| **Crypto subset** | −672.43% | +0.75% (PF 1.33) | (n/a) | **+0.78% (PF 1.41)** |

The crypto cohort — where the evidence lives — flips from −672% to +0.78%
with PF 1.41. Aggregate total stays mildly negative because the untouched
OTHER bucket (copy-trader small-size, n=217) contributes −1.20% on its own.

## Rollback

Single-env kill-switch:

```bash
# Disable both gates instantly (any workflow or process that runs the gate):
PHASE1_CONF_GATE_ENABLED=0 PHASE1_TOD_GATE_ENABLED=0
```

Or relax individually, e.g. `PHASE1_CONF_GATE_THRESHOLD=0.65` to allow the
next tier down.

## Tests

`tests/test_phase1_active_gates.py` — 18 unit tests covering:

- High-conf / low-conf / boundary semantics (`>=` is inclusive)
- Each of the 4 blocked UTC hours
- Non-crypto pass-through
- Env disable + env tuning for both threshold and hour set
- Shadow mode tags without rejecting
- Picks missing `confidence` or `entry_time` fall through safely

Run: `python -m unittest tests.test_phase1_active_gates -v`

## Related memory

- `feedback_confidence_is_not_edge.md`
- `feedback_quick_guess_horizons.md`
- `project_clean_data_symbol_wr.md` — 22 UTC best hour, 08–09 worst
- `project_performance_reality.md`

## Not included (deferred)

- **Phase 2** — mutate top-5 losing strategies per `STRATEGY_INVESTIGATION_BEFORE_KILL.md`
- **Phase 3** — retrain the confidence calibrator so 0.65–0.70 is not the worst
  band by accident
- **LONG-bias inversion on `quan_engine`** — needs regime data before shipping
