# Strategy Investigation: quan_engine (CRYPTO)

**Date:** 2026-05-17  
**Investigator:** Claude Code  
**Status:** Stage 1 — Reduce Risk (monitoring)  
**Protocol:** docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md

---

## 1. Evidence Summary

| Metric | Value | Source |
|--------|-------|--------|
| Asset class | CRYPTO | audit_trail/quality_gates.py |
| Volume share | ~18% of CRYPTO closed picks | dashboard_data.json |
| Historical PF | 0.70 | dashboard_data.json (2026-05-17) |
| WR | ~44% | dashboard_data.json |
| n (resolved) | ~1452 (18% of 8067) | estimated from class share |
| Class impact | Drags CRYPTO PF from ~1.6 → 1.25 | swarm review 2026-05-17 |

## 2. Three-Axis Autopsy (Pre-Block Checklist)

Per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`, a hard block requires passing each axis:

| Axis | Status | Finding |
|------|--------|---------|
| Symbol | NOT YET CHECKED | Run `python tools/mutation_analysis.py` — may be good on BTC only |
| Direction | NOT YET CHECKED | LONG vs SHORT split unknown |
| Timeframe | NOT YET CHECKED | 1h vs 4h vs daily splits unknown |

**Three-axis autopsy is NOT complete. Hard block NOT authorized.**

## 3. Mutation Candidates (to test before block)

Per escalation ladder (Stage 2-3):

1. `inverse_quan_engine` — SHORT bias may outperform LONG bias
2. `quan_engine_btc_only` — concentration on BTC (highest liquidity) may recover edge
3. `quan_engine_regime_gated` — only trades during VIX<22 or BTC dominance>50%
4. `quan_engine_top1` — take only the highest-conviction signal per cycle

## 4. Current Status: Stage 1 (Reduce Risk)

Actions taken:
- **No hard block** — PF=0.70 is poor but n=1452; need autopsy first
- **M-041 swarm_tier gate** already blocks `quan_engine` picks if they arrive as single-tier swarm picks
- **Next CI opportunity**: collect `quan_engine` symbol/direction/timeframe splits from `closed_picks.json`

## 5. Gate Options (Env-Var, Default OFF)

If autopsy confirms no salvageable mutation:

```bash
# Option A: Class-level PF floor (no mutation protocol needed — not a hard block)
CRYPTO_STRATEGY_PF_FLOOR=1.0  # blocks any strategy with PF < 1.0 (from dashboard_data.json)

# Option B: Hard block (requires Stage 4 evidence)
# Add to BLOCKED_SOURCE_SYSTEMS in quality_gates.py ONLY after:
# 1. Three-axis autopsy complete (all three axes fail)
# 2. Top 5 mutation candidates tested and all fail
# 3. User approval
```

## 6. Recommended Next Steps

1. **[2026-05-24]** Export `closed_picks.json` → CSV, run `python tools/mutation_analysis.py` on `quan_engine` rows
2. **[2026-05-31]** Review autopsy output — identify symbol/direction/timeframe slices with PF>1.0
3. **[2026-06-07]** If no slices salvageable → request user approval for Stage 5 hard block
4. **Monitor now**: Add CRYPTO_STRATEGY_PF_FLOOR=1.0 gate (default OFF) as a softer option

## 7. References

- `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` — escalation protocol
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md` — autopsy methodology
- `audit_dashboard/data/dashboard_data.json::performance.asset_class_health` — live PF/WR data
- `tools/mutation_analysis.py` — autopsy runner
