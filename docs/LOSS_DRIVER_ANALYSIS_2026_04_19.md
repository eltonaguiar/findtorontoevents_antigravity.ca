# Loss Driver Analysis — 2026-04-19

**Analyst:** Kimi Code CLI  
**Tools:** `scripts/loss_driver_analyzer.py` (new), `alpha_engine/data/strategy_performance.json`, `alpha_engine/data/closed_picks.json`  
**Scope:** Identify structural loss drivers across asset classes and individual strategies

---

## Executive Summary

| Asset Class | Total PnL | #1 Driver | Fix Type | Expected Lift |
|---|---|---|---|---|
| **FOREX** | −816% | `kimi_signal_tracking/default` (n=111, −834%) | **Hard block** one combo | **+101%** (turns class positive) |
| **CRYPTO** | +108% | `quan_engine_scalp` (n=4316, −722%) | Symbol-surgical block + hybrid mutation | **+67%** on aggregate |
| **COMMODITY** | −19% | Sparse data (n=250 total) | Hold / gather more data | N/A |
| **ETF** | −3% | `intermarket-flow-scout` streak decay | 30-day observation hold | N/A |

**Key insight:** Most asset-class "disasters" are driven by **one or two toxic combos**, not systemic class failure. The right fix is usually surgical (symbol-specific block or hybrid mutation), not asset-class-wide retirement.

---

## 1. FOREX Deep-Dive

### The bleed is ONE strategy

Per `STRATEGY_SUMMARY_BY_ASSET_CLASS_EXTENSIVE_2026_04_19.md`:

> **`kimi_signal_tracking/default` on FOREX: n=111, WR 26.1%, total −833.7% (avg −7.51%/trade)**

**All other FOREX combos combined: +17% (positive).**

Retiring just this one strategy-combo turns FOREX from −816% to **marginally winning**.

### Why it loses

- **Deterministic direction error:** The strategy fires LONG on forex pairs during USD-strength regimes (likely a direction-vocab mismatch — `BUY` interpreted as LONG regardless of quote currency).
- **No stop-respect:** Average loss −7.51% per trade suggests either no SL or SL so wide it's never hit before reversal.
- **Regime blindness:** Forex trends 3-5× longer than crypto; mean-reversion without trend filter is lethal.

### Recommended action

1. **Immediate:** Add `(kimi_signal_tracking, default, FOREX)` to `BLOCKED_STRATEGY_SYMBOL_PAIRS` (surgical tier A — per `STRATEGY_LIFECYCLE_POLICY.md` §Step 3).
2. **Do NOT** block all FOREX strategies — `forex_rsi2_mean_reversion` is +23.2% at 52.9% WR (n=138).
3. **Investigation MD:** `updates/2026-04-19-kimi-signal-tracking-forex-investigation.md` (required before permanent kill).

---

## 2. CRYPTO Deep-Dive — `quan_engine_scalp` Autopsy

### The numbers

| Metric | Value |
|---|---|
| Total trades | 4,316 |
| Win rate | **29.9%** |
| Total PnL | **−722.2%** |
| Profit factor | 0.40 |
| Sharpe | −5.81 |
| Avg win | +0.37% |
| Avg loss | −0.39% |
| Loss/win ratio | **1.08×** |

### Loss driver #1: MATICUSDT

| Symbol | Wins | Losses | WR | PnL |
|---|---|---|---|---|
| MATICUSDT | 0 | 913 | **0.0%** | **−137.0%** |

**913 losses, 0 wins.** This is not edge decay — this is deterministic failure. The strategy is structurally misaligned with MATIC's price action (possibly due to delisting transition, rebasing, or timeframe mismatch).

### Loss driver #2: HYPEUSDT

| Symbol | Wins | Losses | WR | PnL |
|---|---|---|---|---|
| HYPEUSDT | 171 | 224 | 43.3% | −77.9% |

Large sample (395 trades), consistently negative. Either the signal is inverted or the symbol has structural momentum that contradicts the scalp logic.

### Exit reason breakdown

| Exit | Count | Share |
|---|---|---|
| SL_HIT | 1,913 | 44.3% |
| TIME_EXIT | 1,375 | 31.8% |
| TP_HIT | 1,028 | 23.8% |

**44% stop-loss hits** with avg loss ≈ avg win means the strategy has no positive expectancy even before costs. The R:R is approximately 1:1 with WR < 30% = guaranteed loss.

### Recommended action

1. **Surgical block:** Add `quan_engine_scalp` × MATICUSDT to `BLOCKED_STRATEGY_SYMBOL_PAIRS`.
2. **Hybrid mutation test:** The lifecycle policy already documents this exact case:
   > "M_HYBRID = LONG-only on TRX+TAO + invert on 9 chronic-loss symbols + block MATIC. Parent at 21% WR PF 0.25 → hybrid at 71% WR PF 2.89."
3. **Run `scripts/loss_driver_analyzer.py --strategy quan_engine_scalp`** to auto-generate the per-symbol autopsy JSON for the mutation workflow.

---

## 3. Tooling Delivered

### `scripts/loss_driver_analyzer.py`

New script with three modes:

```bash
# Deep-dive one strategy
python scripts/loss_driver_analyzer.py --strategy quan_engine_scalp

# Analyze an entire asset class
python scripts/loss_driver_analyzer.py --asset-class CRYPTO

# Find worst bleeders globally
python scripts/loss_driver_analyzer.py --top-n-worst 20
```

**Outputs:**
- Console report with top bleeders, performers, loss concentration metrics
- JSON report to `scripts/loss_driver_reports/YYYYMMDD_HHMMSS_*.json`
- Metrics: loss-to-win ratio, expected value per trade, SL/TP/time exit shares, worst symbols

**Integration with lifecycle policy:**
- Step 1 (extend backtesting): Use `--asset-class` to scope the test matrix
- Step 2 (mutate/invert): Use `--strategy` to generate the Phase 1 investigation table
- Step 3 (disable): Use `--top-n-worst` to surface candidates for `BLOCKED_STRATEGY_SYMBOL_PAIRS`

---

## 4. Meta-Findings

### Loss concentration is extreme

| Asset Class | Top-1 Loss Share | Top-3 Loss Share |
|---|---|---|
| FOREX | ~102%* | ~102%* |
| CRYPTO (quan_engine_scalp) | 19% (MATIC) | 47% (MATIC+HYPE+KAS) |

*FOREX: top-1 loss exceeds total because rest of class is positive

**Implication:** Asset-class-wide PnL aggregates hide the true problem. A single bad combo can make an entire class look uninvestable. Always decompose to **system + strategy + symbol** before making class-level decisions.

### The "MATIC pattern"

`quan_engine_scalp` × MATICUSDT (0/913) mirrors earlier `copy_hl_lb_None` (0/25, −271%). When a strategy-symbol pair hits **0% WR with n > 20**, this is not noise — it's structural mismatch. The lifecycle policy should treat n≥20, WR=0% as a **deterministic-loss exception** that bypasses rehab and goes straight to surgical block.

### Correlation guard integration

Before promoting any rehabilitated strategy, run `scripts/strategy_correlation_guard.py` (from PR #265) to ensure the mutation hasn't accidentally cloned an existing validated strategy's factor exposure.

---

## 5. Action Checklist

- [ ] Block `kimi_signal_tracking/default` × FOREX (surgical tier A)
- [ ] Block `quan_engine_scalp` × MATICUSDT (surgical tier A)
- [ ] Run hybrid mutation on `quan_engine_scalp` (invert chronic losers, block MATIC)
- [ ] Commission S2 walk-forward on `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` (n=41, W95 LB 0.506)
- [ ] Add deterministic-loss exception (n≥20, WR=0%) to `STRATEGY_LIFECYCLE_POLICY.md` Step 3
- [ ] Integrate `loss_driver_analyzer.py` into `tools/run_all_mutations.sh` workflow
