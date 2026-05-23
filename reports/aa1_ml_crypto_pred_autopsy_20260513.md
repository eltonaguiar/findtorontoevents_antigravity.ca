# AA-1 ml_crypto_pred autopsy

**Date:** 2026-05-13
**Source:** `audit_dashboard/data/dashboard_data.json::systems[name=ml_crypto_pred]`

## TL;DR — "80-day death" claim falsified, replaced with nuanced verdict

Original framing ("ml_crypto_pred 80-day silent-dead") is wrong:
- **System-level `last_signal_at` = 2026-05-13T01:23Z** (today). System is emitting.
- BUT the original sub-strategy is dying staggered, and 3 of 4 sub-strategies look terminal.

## Per-strategy decomposition

| Strategy | Resolved | W | L | WR% | LONG WR | SHORT WR | Last signal | Days stale | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|---:|---|
| ml_crypto_pred (orig) | 32 | 9 | 23 | 28.1 | 12.0 (3/25) | 85.7 (6/7) | 2026-03-25 | **49** | **DYING-SLOW** — over 30d charter cutoff |
| unknown | 7 | 0 | 7 | 0.0 | 0.0 | 0.0 | 2026-05-10 | 3 | **DEAD-EDGE** — 0% WR n=7 |
| enhanced_ml_B_lightgbm | 1 | 0 | 1 | 0.0 | 0.0 | — | 2026-05-08 | 5 | **PREMATURE-EDGE** — n=1 |
| enhanced_ml_A_xgboost | **0** | 0 | 0 | — | — | — | 2026-05-13 | 0 | **NO-DATA** — actively emitting, zero resolved |

System-level aggregate (hides above):
- closed_picks=848, resolved_picks=40, **excluded_closed=808 (95.3%)**
- WR 22.5%, PF 1.86 (asymmetric: avg_win 7.83% vs avg_loss 1.22%)
- max_drawdown 19.52%, calmar 0.5

## Findings

**Finding 1 — Resolver gap 95%.** 808 of 848 closed picks did not reach resolved-valid status. This is the same pattern as the FOREX/COMMODITY non-crypto resolver bug (`feedback_noncrypto_resolver_live_close_bug.md`), but ml_crypto_pred is supposed to be on the CRYPTO path. Probable causes: (a) pre-resolver-v2 backfill rows still pending, (b) different close-time path than the standard pipeline, (c) `forward_validator.py` skipping ML-strategy keys.

**Finding 2 — LONG inversion within ml_crypto_pred sub-strategy.** LONG 3W/22L (12%), SHORT 6W/1L (85.7%). The model is reading direction correctly but acting reversed on LONG, or the LONG calibration is broken. SHORT-only mutation candidate.

**Finding 3 — `unknown` strategy is pure loser.** 7 resolved, 0 wins. Either label-leak (unmapped strategy key) or genuinely broken signal. Either way, contributes 7L/0W to system aggregate.

**Finding 4 — `enhanced_ml_A_xgboost` is a phantom emitter.** Emits today (last_signal 2026-05-13) but has 0 resolved despite the parent system having 848 closed. New code path that hasn't completed a single close cycle. Either: new model just deployed, or resolver doesn't see its closes.

**Finding 5 — PF 1.86 is a small-sample asymmetric-payoff illusion.** 9 wins averaging +7.83% vs 31 losses averaging -1.22%. Looks like trailing-stop strategy; if win-side regime shifts (volatility compression), system collapses. Calmar 0.5 + DD 19.52% on n=40 is not a real-money signal.

## Recommendations (gated on user approval)

**R1 — Investigate resolver gap (P1, blocking).** Why 95% of closes don't resolve. Run:
```
python -c "
import json
rows = [r for r in json.load(open('alpha_engine/data/closed_picks.json', encoding='utf-8')) if r.get('source_system','').startswith('ml_crypto')]
print(len(rows))  # currently 3 in this file
"
```
If `ml_crypto_pred` closes live somewhere other than `closed_picks.json`, find that path. Without resolution path repair, no metric is trustworthy.

**R2 — SHORT-only mutation on `ml_crypto_pred` sub-strategy (P2, surgical).** Per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` Axis-2: 12% LONG WR vs 85.7% SHORT WR is decisive. Block LONG, keep SHORT.

```python
# audit_trail/quality_gates.py
("CRYPTO", "ml_crypto_pred", "LONG"),  # to BLOCKED_ASSET_STRATEGY_DIRECTION_TRIPLES if exists, else new struct
```

**R3 — Quarantine `unknown` sub-strategy (P2).** Either map the label (find why these picks have `unknown` strategy) or block — 0W/7L is bleed.

**R4 — Hold off on `enhanced_ml_A_xgboost` claims until ≥30 resolved.** Per `docs/PERFORMANCE_CHARTER.md` n-floor.

**R5 — Don't trust system aggregate.** Until sub-strategies decomposed correctly, the system-level PF 1.86 / WR 22.5% conflates one stale strategy + one phantom + two losers. Report card per sub-strategy, not parent.

## What this autopsy does NOT do

- Doesn't access database directly (would need DB_PASS_STOCKS). Numbers are from dashboard payload.
- Doesn't backtest the SHORT-only mutant (queued).
- Doesn't trace the resolver gap to source (R1 follow-up).
- Doesn't propose system-wide kill — sub-strategies vary too much.

NFA. Reversible (no production change made).
