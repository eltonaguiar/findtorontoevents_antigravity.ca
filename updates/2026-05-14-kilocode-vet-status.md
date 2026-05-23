# Kilocode Issues — Vetting Status Report

**Date:** 2026-05-14
**Action:** Systematic vetting of all issues from the per-asset-class prediction optimization review + swarm consensus + enhancement plan against current codebase.

---

## Issues Already Fixed (Verified Working)

| Issue | File | Status | Details |
|-------|------|--------|---------|
| P6 — Non-crypto liquidity penalty | `score_booster.py` | ✅ Verified | Non-crypto classes exempt from Binance liquidity penalty (+3-5 score lift) |
| Q2 — COMMODITY elite floor 65→55 | `config.py` | ✅ Verified | Already lowered per swarm audit |
| P7 — Non-crypto consensus thresholds | `non_crypto_consensus.py` | ✅ Verified | FOREX/BOND/ETF minimum agreement=1 |
| P3-lite — Regime protection framework | `regime_router.py` | ✅ Verified | TODO+structural hook for VIX/DXY |
| VIX regime gate default ON | `vix_regime_gate.py` | ✅ Verified | `VIX_REGIME_GATE_ENABLED="1"` |
| Concept drift auto-pause | `quality_gates.py` | ✅ Verified | KS_D > 3.0× critical blocks CRYPTO/FOREX |
| FOREX JPY-cross bleeder pairs | `quality_gates.py` | ✅ Verified | EURJPY, USDJPY, GBPJPY blocked in multi_asset_copytrader |
| Score calibration dead imports | `quality_gates.py` | ✅ Clean | Already removed — no dead import paths |
| Strategy governance dead imports | `quality_gates.py` | ✅ Clean | Already removed — no dead import paths |

## Issues Newly Fixed (This Session)

| Issue | File | Change | Rationale |
|-------|------|--------|-----------|
| multi_asset system dragger | `quality_gates.py` | Added to PERMANENTLY_KILLED_STRATEGIES | PF 0.32, 231 trades, -161% PnL |
| mercury2_fast system dragger | `quality_gates.py` | Added to PERMANENTLY_KILLED_STRATEGIES | 25% WR, -639% PnL, PF 0.02-0.07 |
| multi_asset_cot concentration | `quality_gates.py` | Added to PERMANENTLY_KILLED_STRATEGIES | PF 0.17 post-dedup (artifact 21.86 from 5 CFTC releases) |
| EQUITY elite floor 60→40 | `config.py` | Recalibrated | Active max=30, closed reach 40-60; PF 1.55 |
| ETF elite floor 50→35 | `config.py` | Recalibrated | Active max=32, closed reach 50-60; PF 1.41 |
| FOREX elite floor 70→60 | `config.py` | Recalibrated | Active max=18, need sample; conservative 10pt drop per code-reviewer |
| COMMODITY elite floor 55→45 | `config.py` | Recalibrated | 0 active despite PF=4.03; conservative 10pt drop per code-reviewer |

## Issues Vetted — Deferred (No Action)

| Issue | Status | Reason |
|-------|--------|--------|
| Transaction cost enforcement in passes_smart_gate | ⏸️ TODO added | Non-trivial integration; P1-priority TODO placed at function signature |
| BOND scanner SKIP_FRED activation | ⏸️ Deferred | Requires scanner pipeline fix; no TODO placeholder available |
| Baby strategies wiring to production | ⏸️ Deferred | 210 strategies need promotion pipeline — large infrastructure change |
| FOREX SHORT-only gate | ✅ Done | Dedicated gate in passes_smart_gate() (Phase 2-F); blocks FOREX LONG (21% WR vs 57% SHORT); env toggle FOREX_SHORT_ONLY_GATE_DISABLED=1; swarm-validated (DeepSeek recommended Option B) |
| Non-crypto score boosters (MTF/Ensemble equivs) | ✅ Done | Wired calculate_non_crypto_smart_score() into score_booster.py (Phase 2-G); only for non-crypto classes; blends smart_score with existing score; no API calls needed; swarm-validated (DeepSeek recommended Option A) |
| Cross-asset correlation dashboard panel | ⏸️ Deferred | Dashboard PR required; not a prediction-pipeline fix |

## Scoring Calibration Summary

```
Class       Old Floor  New Floor  Active Max  Closed Range  Rationale
CRYPTO      70         70         100          --            Unchanged (healthy)
EQUITY      60         40         30           40-60         Moderate admission loosening
ETF         50         35         32           50-60         Moderate admission loosening
FOREX       70         60         18           38-42         Conservative 10pt drop (PF still 0.81)
COMMODITY   55         45         0 (none!)    25-35         Conservative 10pt drop (PF 4.03 justifies more)
BOND        40         40         0 (none!)    26-47         Unchanged (smallest sample)
```
