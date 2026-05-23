# Mutation Investigation Report — 2026-05-17

**Protocol:** `docs/MUTATION_THREE_AXIS_PROTOCOL.md`  
**Data source:** `alpha_engine/data/closed_picks.json` via `python tools/mutation_analysis.py --json --min-trades 20`  
**Date:** 2026-05-17  
**Status:** INVESTIGATION COMPLETE — Gate updates applied; direction-block pending user approval

---

## 1. Matrix Symbol Gates Updated (DONE)

`alpha_engine/data/matrix_symbol_gates.json` updated with new block rules. Gate is **ON by default** (`MATRIX_SYMBOL_GATES=1`). Disable with `MATRIX_SYMBOL_GATES=0`.

### New blocks added this session

#### cta_replicator (Axis 3 — Symbol)
| Symbol | n | WR | Avg PnL | Action |
|--------|---|----|---------|--------|
| NG=F | 24 | **0.0%** | -3.0% | BLOCKED |
| CL=F | 47 | **19.1%** | -1.5% | BLOCKED |
| USDJPY=X | 112 | 70.5% | -0.2% | Allowed (passing) |
| NZDUSD=X | 60 | 41.7% | +0.0% | Allowed (marginal) |

**Impact estimate:** Removes 71 losing trades (NG=F + CL=F) from cta_replicator. Explains `COMMODITY 7d PF=0.64` drag observed in PR #1126 audit.

#### multi_asset_copytrader (Axis 3 — Symbol)
| Symbol | n | WR | Avg PnL | Action |
|--------|---|----|---------|--------|
| EURJPY=X | 154 | **1.95%** | -0.5% | BLOCKED |
| USDJPY=X | 133 | **3.01%** | -0.5% | BLOCKED |
| GBPJPY=X | 87 | **10.3%** | -0.4% | BLOCKED |
| AUDJPY=X | 84 | **3.57%** | -0.5% | BLOCKED |
| NZDUSD=X | 59 | **15.3%** | -0.3% | BLOCKED |
| CADJPY=X | 41 | **9.76%** | -0.4% | BLOCKED |
| SI=F | 45 | **2.22%** | -2.8% | BLOCKED |
| HG=F | 33 | **0.0%** | -2.7% | BLOCKED |
| KC=F | 22 | **4.55%** | -2.6% | BLOCKED |
| EURGBP=X | 48 | 70.8% | +0.2% | Passing |
| GBPUSD=X | 30 | 66.7% | +0.3% | Passing |
| CT=F | 175 | 57.1% | +1.5% | Passing |

**Impact estimate:** Multi_asset_copytrader overall WR was 21.7% (1069 trades) — dragged by JPY-crosses. With JPY-cross blocks, remaining portfolio (EURGBP + GBPUSD + CT=F + AUDUSD) should be 55-70%+ WR. This strengthens the FOREX_COPYTRADER_ENABLE bypass case.

#### quan_engine (Axis 3 — Symbol, updated)
Added LTCUSDT (23.6% WR, 89 trades) and RENDERUSDT (30.8% WR, 240 trades) to existing blocks.

---

## 2. Direction Flip — PENDING USER APPROVAL

### ig_contrarian_sentiment (Axis 1 — Direction)

| Direction | n | WR | Avg PnL |
|-----------|---|----|---------|
| SHORT | 57 | **61.4%** | ~0% |
| LONG | 197 | **16.8%** | ~0% |
| **Spread** | | **45pp** | |

**Interpretation:** ig_contrarian_sentiment is a strong SHORT signal. The LONG direction is deeply negative (n=197, WR=16.8%). This is Axis 1 (direction flip) per the three-axis protocol.

**Proposed action:** Add `("ig_contrarian_sentiment", "LONG")` to `BLOCKED_ASSET_STRATEGY_PAIRS` in `audit_trail/quality_gates.py`.

**Impact:** Would block 197 trades (all LONG ig_contrarian_sentiment picks). The SHORT side (n=57, WR=61.4%) would continue.

**Awaiting user approval before adding to BLOCKED_ASSET_STRATEGY_PAIRS per CLAUDE.md.**

---

## 3. Direction Flip — Secondary Candidates

### forex_rsi2_mean_reversion (Axis 1 — Direction)
| Direction | n | WR |
|-----------|---|-----|
| SHORT | 23 | 34.8% |
| LONG | 108 | 7.4% |

27pp spread. SHORT is also below T2 threshold. Recommend monitoring until n≥30 per side; LONG is toxic (WR=7.4%).

### cta_cross_asset_tsmom (Axis 1 — Direction)
| Direction | n | WR |
|-----------|---|-----|
| SHORT | 164 | 52.4% |
| LONG | 84 | 29.8% |

23pp spread. SHORT borderline T2. LONG below floor. Investigate separately.

---

## 4. Axis 4 (Threshold-Normalization) — Research Only

Systems where standard WR thresholds may be mis-scaled vs asset-class volatility:

| System | WR | n | Axis 4 Recommendation |
|--------|----|----|----------------------|
| multi_asset_copytrader | 21.7% | 1069 | After symbol blocks, re-measure |
| rapid_fire | 29.0% | 207 | Monitor post-symbol-block |
| quan_engine | 30.4% | 5896 | Monitor post-symbol-block |

**Action:** Re-run mutation_analysis after 30d of new data with matrix gates active.

---

## 5. Summary of Gate Changes

| Change | Type | Evidence | Status |
|--------|------|----------|--------|
| cta_replicator NG=F block | Matrix gate | WR=0%, n=24 | ✅ SHIPPED |
| cta_replicator CL=F block | Matrix gate | WR=19%, n=47 | ✅ SHIPPED |
| multi_asset_copytrader 9× JPY/metals block | Matrix gate | WR=0-15%, n=20-154 | ✅ SHIPPED |
| quan_engine LTCUSDT block | Matrix gate | WR=23.6%, n=89 | ✅ SHIPPED |
| quan_engine RENDERUSDT block | Matrix gate | WR=30.8%, n=240 | ✅ SHIPPED |
| ig_contrarian_sentiment LONG block | BLOCKED_ASSET_STRATEGY_PAIRS | WR=16.8%, n=197 | ⏳ PENDING USER APPROVAL |

---

*Produced by Claude Code (claude-sonnet-4-6) autonomous session 2026-05-17*
