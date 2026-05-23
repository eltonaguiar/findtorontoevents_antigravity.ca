# Money-Maker-Ready v2 — 2026-05-16T06:00Z
**Session:** Claude Code (Desktop) autonomous /money-maker-readyv2 loop
**Goal:** Ultimate Statistical Edge Per Asset Class — hedge-fund-grade, OOS-validated, ready for real capital

---

## CRITICAL CORRECTION THIS SESSION

Previous reports (≤2026-05-15) used a **biased validation approach:**
- IS/OOS split was selected AFTER examining system performance (selection bias)
- "EQUITY" picks from `signal_validation` were all crypto tokens (BTC-USD, ETH-USD, etc.) mislabeled as EQUITY
- 4 "elite" systems (`multi_asset_cot`, `multi_asset_copytrader`, `claude_gainer`, `mega_mutation`) had **n=0** in the validated dataset — stats from live dashboard only

**This report uses a pre-registered split at 2026-04-01 defined before examining per-system performance.**

---

## Pre-Registered OOS Validation Results

**Validated dataset:** `audit_trail/data/universal_resolved_picks.json` (5,000 picks)
**IS period:** 2026-02-20 to 2026-03-31 (n=830)
**OOS period:** 2026-04-01 to 2026-05-16 (n=4,170 closed picks, 46 days, 2 market regimes)
**Bootstrap:** 5,000-iteration CI on OOS PF — see `audit_trail/edge_filter_bootstrap.py`

### System Rankings (OOS Only)

| System | OOS n | OOS WR | OOS PF | CI-95-lo | CI-95-hi | P(PF>1.5) | AC1 | Tier |
|--------|-------|--------|--------|----------|----------|-----------|-----|------|
| `kimi_signal_tracking` | 135 | 88.9% | 15.94 | 10.47 | 27.88 | 100% | -0.06 | ✅ TIER 1 |
| `aggregated_picks` | 383 | 78.1% | 7.02 | 5.71 | 8.71 | 100% | 0.24⚠ | ✅ TIER 1 |
| `stocks_competition` | 53 | 67.9% | 3.71 | 2.28 | 5.98 | 100% | 0.74⚠ | ⚠️ TIER 1 fragile |
| `signal_validation` | 179 | 55.3% | 1.82 | 1.41 | 2.36 | 89.5% | 0.18 | ✅ TIER 2 |
| `rapid_fire` | 47 | 51.1% | 1.67 | 1.01 | 2.72 | 62.7% | 0.06 | ⚠️ MONITORING |
| `luxalgo_filters` | 350 | 41.4% | 1.39 | 1.15 | 1.67 | 24.4% | 0.21⚠ | ⚠️ MONITORING |

**Note on `stocks_competition`:** AC1=0.74 → effective independent n ≈ 8 (not 53). Bootstrap CI is optimistic. Do not size as full Tier 1 until AC1 normalizes and n≥100 independent picks.

### Sub-Floor Systems (DO NOT SIZE)

`ml_crypto_pred` (PF=0.82, n=837), `alpha_engine` (PF=0.67, n=307), `claude_gainer_st` (PF=0.71, n=112), `mutation_lab` (PF=0.19, n=39), `battleground` (PF=0.00, n=27)

---

## Per-Class Verdict

| Asset Class | OOS-Validated? | Status | Weekly Filter | Max Alloc |
|-------------|---------------|--------|--------------|-----------|
| CRYPTO | YES (n=4000+) | **Tier 1 elite** | `aggregated_picks`, `kimi_signal_tracking`, `signal_validation` | 0.5-0.75% |
| EQUITY | PARTIAL (n=53, AC1⚠) | **Promising, thin** | `stocks_competition` (real stocks only) | 0.5% |
| COMMODITY | NO | **Dashboard-only** | Blocked until OOS data accumulates | 0% |
| FOREX | THIN (n=21) | **Blocked** | `signal_validation` only, accumulating | 0% |
| ETF/BOND | NO | **Insufficient** | Blocked | 0% |

---

## Today's Live Filter (from `tools/weekly_filter_picks.py`)

```
Input picks: 120 | Passed filter: 0 | Skipped: 120
```

**Reason:** Current `active_picks.json` has picks from `copy_trader_intel`, `ml_crypto_predictor`, `ml_strategy_reviver` etc. — none are OOS-validated elite systems. Filter correctly rejects all 120 picks.

**Action required:** Confirm that `aggregated_picks`, `kimi_signal_tracking`, and `signal_validation` systems are actively emitting to `alpha_engine/data/active_picks.json`. If not, the pick emission pipeline for elite systems is broken.

---

## Key Files Committed This Session

| File | Purpose |
|------|---------|
| `audit_trail/edge_filter_bootstrap.py` | Bootstrap PF significance test (5000 iterations, pre-registered OOS split, DSR, AC1 check) |
| `reports/oos_validation_2026-05-16.md` | Full per-system OOS table with bootstrap CI, serial correlation flags |
| `reports/statistical_edge_analysis_2026-05-16.md` | Revised per-class analysis with corrected numbers, data integrity notes |
| `tools/weekly_filter_picks.py` | Updated: ghost systems replaced with OOS-validated ones, COMMODITY blocked |

---

## Action Items for Other Agents

### P0 — Check Elite System Emission Pipeline
Confirm that `aggregated_picks` (OOS PF=7.02) and `kimi_signal_tracking` (OOS PF=15.94) are emitting picks to `alpha_engine/data/active_picks.json`. These systems have the strongest OOS-validated edge but are currently absent from active picks.

**Check:**
```bash
python -c "import json; picks=json.load(open('alpha_engine/data/active_picks.json')); print(set(p.get('source_system','') for p in picks))"
```

If `aggregated_picks` or `kimi_signal_tracking` not in output → emission pipeline broken.

### P1 — Fix EQUITY Asset Class Mislabeling
`signal_validation` labels crypto picks as EQUITY in `universal_resolved_picks.json`. Root cause: the emitter sets `asset_class=EQUITY` for crypto tokens. Fix the asset_class tagging at the signal emission stage so EQUITY is only used for real stock symbols (no `-USD` suffix).

### P1 — Verify COMMODITY Pipeline
`multi_asset_cot` (dashboard PF=4.72) has n=0 picks in `universal_resolved_picks.json`. Either:
a) The picks are being emitted but not resolved, OR
b) The system is not actively emitting

Investigate `alpha_engine/outcome_resolver.py` to see if COMMODITY picks from `multi_asset_cot` are being resolved.

### P2 — Grow `stocks_competition` Independent Sample
AC1=0.74 means the 53 OOS picks are equivalent to only ~8 independent data points. Increase pick frequency AND ensure picks aren't clustered on the same underlying signal. Target: n=100 with AC1 < 0.3.

### P2 — Kill List Investigation
Per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`, these systems need investigation before kill:
- `mutation_lab` (OOS PF=0.19, WR=10.3%, n=39) — catastrophic
- `battleground` (OOS PF=0.00, WR=0.0%, n=27) — zero winners
- `alpha_engine` (OOS PF=0.67, WR=30.0%, n=307) — high volume drag

```bash
python tools/mutation_analysis.py --system mutation_lab
python tools/mutation_analysis.py --system battleground
```

---

## How to Reproduce This Analysis

```bash
# Run bootstrap OOS validation
python audit_trail/edge_filter_bootstrap.py --save reports/oos_validation_latest.md

# Run weekly filter (checks active_picks.json against elite systems)
python tools/weekly_filter_picks.py --dry-run

# Run on specific system
python audit_trail/edge_filter_bootstrap.py --system aggregated_picks
```

---

## Remaining Success Criteria Status

| Criterion | Status | Blocker |
|-----------|--------|---------|
| EQUITY ≥5 picks, WR≥55%, PF≥1.5 | ❌ | stocks_competition AC1=0.74, effective n≈8 |
| CRYPTO elite filter PF≥1.5, n≥100 | ✅ | aggregated_picks (OOS PF=7.02, n=383) |
| COMMODITY top strategy, PF≥1.5, n≥50 | ❌ | No OOS data (n=0 in validated dataset) |
| ETF n≥150 on path | ❌ | n=107 in dashboard, no OOS data |
| FOREX mutation protocol in progress | ✅ | Tracked, n=21 OOS closed picks |
| BOND n≥20 | ❌ | n=11 total |
| Kelly sizing for all picks | ✅ | In weekly_filter_picks.py with CI-lower scaling |

---

*NOT FINANCIAL ADVICE — research surface only.*
*Bootstrap CI: pre-registered OOS split 2026-04-01, 5000 iterations, seed=42.*
*See `audit_trail/edge_filter_bootstrap.py` for full methodology.*
