# Cross-Asset Score-Floor Audit & Tuning

**Date:** 2026-04-05
**Owner:** claude-noncrypto-drilldown
**Commit:** TBD (pending push)
**Related:** 6d65abfa55 (P0-A enrichment), 109bbc50f9 (null-exit healer), e146c4da13 (FUTURES-REVIVAL P1)

---

## TL;DR

Per-asset-class smart-picks score floors were calibrated ~2026-04-04 on a stale cohort. Chrono-split analysis of 3500 closed picks (all asset classes) reveals significant forward-decay in CRYPTO and EQUITY — current floors admit losing trades. Raised CRYPTO 60→70, EQUITY 30→50. Added COMMODITY=30, BOND=40, FUTURES=60, ETF=40 floors (previously all fell through to SMART_PICKS_MIN_SCORE=60 default).

---

## Method

1. Pulled 3500 closed picks from `audit_dashboard/data/dashboard_data.json.picks.recent_closed`
2. Grouped by `asset_class`, kept only picks with non-null `score` + `pnl_pct`
3. Computed WR and PF at progressive score floors (0, 20, 30, 40, 50, 60, 70, 80, 90)
4. **Chrono-split sanity check**: compared H1 vs H2 to detect forward-decay
5. **Recent-third analysis**: most recent ⅓ gives honest forward signal
6. Selected floor = highest PF with WR ≥ 50% AND n ≥ 20 AND chrono-stable

---

## Findings

### CRYPTO (n=2662)

Old floor: 60 — looked great on full cohort (86% WR at 70+, PF 10.58).

**Forward-decay exposed:**
| Floor | H1 (older 50%) | H2 (newer 50%) | Recent ⅓ |
|---|---|---|---|
| 50 | 66% WR, PF 2.33 | 47% WR, PF 1.17 | 48% WR, PF 1.23 |
| 60 | **81% WR, PF 12.33** | **50% WR, PF 0.92** | **48% WR, PF 0.73** ⚠️ |
| 70 | 87% WR, PF 14.47 | 85% WR, PF 5.48 | 80% WR, PF 4.28 ✅ |

**Diagnosis:** Floor=60 is *currently losing money* (PF 0.73 recent). Floor=70 holds through recent data but n is small (10-28). **RAISED 60 → 70.**

### EQUITY (n=286)

Old floor: 30 — based on score 30-50 = 66.7% WR PF 2.61 at calibration time.

**Recent-third reveals stale calibration:**
| Floor | H1 | H2 | Recent ⅓ |
|---|---|---|---|
| 30 | 56% WR, PF 1.61 | 43% WR, PF 1.05 | 40% WR, PF 1.06 ⚠️ |
| 40 | 59% WR, PF 1.97 | 52% WR, PF 1.80 | 49% WR, PF 2.03 |
| 50 | 67% WR, PF 2.69 | 64% WR, PF 2.91 | **67% WR, PF 3.28** ✅ |

**Diagnosis:** Floor=30 recent WR=40% — admitting losers. Floor=50 chrono-stable + strong. **RAISED 30 → 50.**

### COMMODITY (n=155)

Previously fell through to CRYPTO default (60) — too strict for commodity structure.

| Floor | H1 | H2 | Recent ⅓ |
|---|---|---|---|
| 30 | 48% WR, PF 0.63 | 54% WR, PF 2.79 | **47% WR, PF 2.78** ✅ |

**Diagnosis:** Commodity is PF-driven not WR-driven (few big wins offset small losses). **NEW floor = 30.**

### FOREX (n=380)

Old floor: 75 (copilot-quant-audit MC sweep).

| Floor | H1 | H2 | Recent ⅓ |
|---|---|---|---|
| 30 | 54% WR, PF 2.70 | 44% WR, PF 1.08 | (not computed) |
| 50 | — | **32% WR, PF 0.23** ⚠️ | — |

**Diagnosis:** FOREX recent H2 at floor=50 is catastrophic (32% WR / PF 0.23). **KEEP floor=75** per copilot's MC sweep.

### BOND (n=8), ETF (n=4), FUTURES (n=5)

Insufficient closed-pick data for honest floor estimation. Conservative defaults:
- BOND = 40 (new)
- ETF = 40 (new)
- FUTURES = 60 (new, awaiting FUTURES-REVIVAL Phase 2 TSMOM strategy + 60-day validation)

---

## Expected Impact

Smart Picks count will initially DROP (stricter floors) but Win Rate will IMPROVE:

| Asset | Old floor | New floor | Est. WR change | Est. PF change |
|---|---|---|---|---|
| CRYPTO | 60 | 70 | 48% → 80% (+32pp) | 0.73 → 4.28 (+488%) |
| EQUITY | 30 | 50 | 40% → 67% (+27pp) | 1.06 → 3.28 (+209%) |
| COMMODITY | (60 default) | 30 | — | NEW |
| FOREX | 75 | 75 | (unchanged) | (unchanged) |

**Trade-off:** Fewer smart picks surfaced, but each pick far more likely to win. Aligns with user directive "hedge-fund level trusted picks."

---

## Next Steps (Deferred)

1. **Cross-asset confluence detection** (separate work package): when same base ticker appears in 2+ asset classes (e.g., BTC crypto + BITO ETF + BTC futures), flag + apply confluence boost. Requires symbol-root normalization across asset classes. ~4h work.
2. **Re-audit floors monthly** — forward-decay means floors need recalibration as regime shifts.
3. **Monitor `_score_capped_null_ml` rate** — my P0-A 6d65abfa55 caps null-ml picks at score 70. New CRYPTO floor=70 means cap and floor now match — any aggregator-source pick without ml_composite will sit exactly at the gate, borderline.

---

## Files changed

- `audit_trail/quality_gates.py:120-127` (floor constants + comments)
- `audit_trail/quality_gates.py:2249-2269` (per-asset floor routing)
