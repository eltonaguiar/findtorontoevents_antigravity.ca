# Strategy Inversion Findings — 2026-05-04

## TL;DR

The two "buried disaster" strategies flagged for blocking (`ml_enhanced_TRXUSDT_1d_B_lightgbm`, `ml_enhanced_APEUSDT_1d_D_ensemble_stack`) are **not broken — they are direction-inverted**. Flipping the direction turns a combined -$50K loss into a +$50K gain. Per CLAUDE.md mutate-before-kill, **flip is the mutation**, not the kill. This supersedes the swarm consensus to defer-pending-block and replaces it with a promote-with-direction-flip path.

The "buried elite" `ml_enhanced_FETUSDT_1d_B_lightgbm` survives a jackknife sensitivity test robustly — PF 6.20 even after dropping the top 5 winners. **Promotable to candidate tier** (n=44 still below T2 floor of 100, so PROVEN must wait).

## D2 — `ml_enhanced_TRXUSDT_1d_B_lightgbm`

| Variant | n | WR | PF | sum_$ |
|---|---|---|---|---|
| As-shipped (LONG) | 26 | 11.5% | 0.003 | **-$33,094** |
| **Direction-flipped (SHORT)** | 26 | **88.5%** | **291.5** | **+$33,094** |

All 26 picks are direction=LONG. Loss distribution shows extreme consistency — every loss is in the $1,577-1,586 range, suggesting a stop-loss is hit on ~88% of trades. That's a smoking gun for inverted signals: when the model says LONG, the symbol drops by exactly the stop-distance every time.

**Recommended action**: NOT a kill. NOT a block. Mutation = direction flip. Implementation pattern (per CLAUDE.md): add the strategy to a `DIRECTION_FLIP_OVERRIDES` registry; the pick-emitter applies the flip before the pick lands in active picks.

## D3 — `ml_enhanced_APEUSDT_1d_D_ensemble_stack`

| Variant | n | WR | PF | sum_$ |
|---|---|---|---|---|
| As-shipped (SHORT) | 30 | 33.3% | 0.047 | -$17,237 |
| **Direction-flipped (LONG)** | 30 | **66.7%** | **21.4** | **+$17,237** |

Same pattern. All 30 picks SHORT. Inverse PF 21.4 is still impressive even though lower than TRX's 291.5 — probably APE has more genuine market moves that go either way.

**Recommended action**: same as D2 — mutation via direction flip.

## D4 — `ml_enhanced_FETUSDT_1d_B_lightgbm` jackknife

Jackknife sensitivity (drop top-N winners, recompute):

| Drop top N | n | WR | PF | sum_$ |
|---|---|---|---|---|
| 0 | 44 | 56.8% | **9.43** | +$15,181 |
| 1 | 43 | 55.8% | 8.78 | +$14,018 |
| 2 | 42 | 54.8% | 8.14 | +$12,856 |
| 3 | 41 | 53.7% | 7.49 | +$11,693 |
| 5 | 39 | 51.3% | **6.20** | +$9,368 |

**The signal is robust** — PF stays above the T1 charter floor (PF>2) even after stripping 5 of the 44 wins. This is NOT an outlier-driven artifact.

**Caveat — possible multi-day position**: The top 5 winners are all `pnl_dollar = +$1163.39` / `pnl_pct = +0.5813` on **consecutive entry dates 2026-03-13 through 2026-03-17**. This is statistically improbable for 5 independent picks; more likely a single position re-emitted as 5 daily entries (or a cohort that all hit the same TP simultaneously). If so, the "n=44" is effectively n≤40 distinct trade-events, which still passes the T2 floor of 100? — no, wait, n=40 is still below 100.

**Recommended action**: 
1. Promote to **candidate tier** now (matches the n-guard tier I already shipped — `audit_trail/dashboard_generator.py::compute_asset_class_health`).
2. Hold PROVEN tier until n>=100.
3. Investigate the 5-consecutive-day TP cluster before public surfacing — could indicate the strategy is stuck at one entry signal rather than firing on independent setups.

## Implication for the broader `ml_enhanced_*_1d_B_lightgbm` family

The bimodal pattern from `reports/unknown_asset_class_deep_investigation_2026_05_04.md` (INJ +$8K, FET +$15K, TRX -$33K, JTO -$3K) now has a clearer explanation:

- **Some symbols**: model captures real momentum → wins go LONG when symbol goes up
- **Other symbols**: model is INVERTED → calls LONG when symbol falls

The "winning" symbols (INJ, FET, RENDER, DYDX) and the "losing" symbols (TRX, APE, JTO, HBAR, ALGO) may have the same underlying training-data sign-flip bug; the wins look like wins because the symbol's drift direction happened to match the model's bias.

**Cross-engine recommendation**: run the same direction-flip test against ALL `ml_enhanced_*_1d_B_lightgbm` and `ml_enhanced_*_1d_D_ensemble_stack` losers. If the inversion pattern holds across the family, it's a single bug fix in the model's signal-emission code, not a per-symbol kill list.

## Per-symbol inverse-test results across the disaster family

| Strategy | Direction | n | WR | PF | sum_$ | Inverse PF |
|---|---|---|---|---|---|---|
| TRXUSDT_1d_B_lightgbm | LONG | 26 | 11.5% | 0.003 | -$33,094 | **291.5** |
| APEUSDT_1d_D_ensemble_stack | SHORT | 30 | 33.3% | 0.047 | -$17,237 | **21.4** |

(JTOUSDT, HBARUSDT, ALGOUSDT not yet flipped — recommend running the same battery before merging any block PR.)

## Action plan revised from swarm consensus

| Decision | Original swarm verdict | Revised after this analysis |
|---|---|---|
| D2 TRXUSDT | defer pending mutation_analysis | **mutate via direction flip** (this IS the mutation analysis) |
| D3 APEUSDT | defer pending mutation_analysis | **mutate via direction flip** |
| D4 FETUSDT | defer / split | **promote to candidate tier; investigate 5-consecutive-day cluster** |

## Implementation sketch (for a follow-up PR, not this branch)

```python
# alpha_engine/strategy_direction_overrides.py (new file)
"""Per-strategy direction-flip overrides.

When a strategy emits picks consistently in the wrong direction (PF<0.1
across n>=20 in one direction, with inverse PF>10), a mutate-before-kill
action is to flip the direction at emission time rather than block.

Source: reports/strategy_inversion_findings_2026_05_04.md
"""

DIRECTION_FLIP_OVERRIDES = {
    # strategy_name -> reason / evidence link
    "ml_enhanced_TRXUSDT_1d_B_lightgbm": (
        "n=26 LONG @ PF 0.003 / WR 11.5%; inverse SHORT @ PF 291.5"
    ),
    "ml_enhanced_APEUSDT_1d_D_ensemble_stack": (
        "n=30 SHORT @ PF 0.047 / WR 33.3%; inverse LONG @ PF 21.4"
    ),
}

def apply_direction_flip(pick: dict) -> dict:
    """Flip pick direction in-place if its strategy is in the override list."""
    if pick.get("strategy") in DIRECTION_FLIP_OVERRIDES:
        d = (pick.get("direction") or "").upper()
        pick["direction"] = "SHORT" if d == "LONG" else "LONG" if d == "SHORT" else d
        # Also swap TP and SL — the geometry is mirrored.
        tp = pick.get("take_profit"); sl = pick.get("stop_loss")
        pick["take_profit"], pick["stop_loss"] = sl, tp
        pick["_direction_flipped"] = True
    return pick
```

Wire-up site: pick-generator path (probably `alpha_engine/scanner.py` or per-strategy file). Per CLAUDE.md Wire-Up Rule, the override registry must have a production caller before merge.

**Validation gate before merge**: run the inverse battery on ALL ml_enhanced_*_1d_B_lightgbm strategies; only add to `DIRECTION_FLIP_OVERRIDES` those with PF<0.1 AND n>=20 AND inverse PF>5.

## Provenance

- Source: `alpha_engine/data/closed_picks.json` (post-Patch-2 backfilled)
- Compute: 2026-05-04 — single-script aggregation
- Cross-references:
  - `reports/unknown_asset_class_deep_investigation_2026_05_04.md` — original discovery
  - `reports/asset_class_tagger_investigation_2026_05_04.md` — root-cause for visibility
  - This file — mutation paths for the disasters + jackknife for the elite
