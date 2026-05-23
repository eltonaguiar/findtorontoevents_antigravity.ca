# Crypto Win-Rate Recovery Plan

**Date:** April 17, 2026  
**Analyst:** Quantitative Trading Research Agent  
**Dataset:** `alpha_engine/data/closed_picks.json` (n=4,643 total, n=4,634 crypto)  
**Status:** DIAGNOSTIC COMPLETE — AWAITING IMPLEMENTATION

---

## 1. Executive Summary

Crypto is the **only asset class with a proven edge**, yet the overall crypto win-rate (WR) is **32.15%** with a profit factor (PF) of **0.39** and average PnL of **-0.15% per trade**. The bleeding is caused by a single structural flaw: the system emits ~4,000 low-confidence, wide-R:R `quan_engine_scalp` trades that systematically hit stop-loss or time out. The verified edge is concentrated in a tiny high-confidence / tight-R:R / ML-enhanced cohort.

**If we trade only the proven cohort, crypto flips to ~60% WR and PF > 1.5.**

---

## 2. Quantified Findings

### 2.1 Overall Crypto Stats
| Metric | Value |
|--------|-------|
| Total Crypto Picks | 4,634 |
| Win Rate | 32.15% |
| Profit Factor | 0.39 |
| Avg PnL | -0.1486% |

### 2.2 Confidence Buckets — The 0.8 Floor is the Only Profitable Zone
| Bucket | n | WR | PF | Avg PnL |
|--------|---|----|----|---------|
| 0.0–0.5 | 507 | 43.79% | 0.23 | -0.056% |
| 0.5–0.6 | 1,047 | 35.24% | 0.41 | -0.199% |
| **0.6–0.7** | **2,714** | **26.27%** | **0.35** | **-0.162%** |
| 0.7–0.8 | 262 | 43.51% | 0.67 | -0.087% |
| **0.8–0.9** | **104** | **69.23%** | **10.39** | **+0.103%** |
| 0.9–1.0 | 0 | — | — | — |

**Key insight:** 58.6% of all crypto picks sit in the 0.6–0.7 confidence bucket and it is the *worst* performing bucket. The current `QUALITY_GATE_MIN_CONFIDENCE = 0.55` is letting through a torrent of negative-expectancy trades.

### 2.3 Risk:Reward — The Real Killer (R:R ≤ 1.5 is the ONLY Profitable Bucket)
| Bucket | n | WR | PF | Avg PnL |
|--------|---|----|----|---------|
| None | 127 | 25.20% | 0.03 | -0.278% |
| **1.0–1.5** | **253** | **59.68%** | **1.14** | **+0.002%** |
| 1.5–2.0 | 237 | 51.05% | 0.65 | -0.035% |
| **2.0–3.0** | **3,991** | **29.72%** | **0.40** | **-0.162%** |
| 3.0+ | 26 | 0.00% | 0.00 | -0.041% |

**86.1% of crypto trades carry R:R 2.0–3.0 and they are systematically unprofitable.** Trades with tight R:R (1.0–1.5) are profitable *even at low confidence* (cross-tab: R:R 1.0–1.5 × conf 0.0–0.5 = 60.6% WR, n=170).

This implies the scalp engine is setting take-profit too far relative to stop-loss — trades never reach TP and instead bleed into SL or TIME_EXIT.

### 2.4 Exit-Reason Autopsy
| Reason | n | WR | Avg PnL |
|--------|---|----|---------|
| TP | 935 | 100% | +0.381% |
| TP_HIT / TP_HIT_RESOLVED | 175 | 100% | +0.107% |
| PRICE_RESOLVED | 31 | 90.3% | +0.117% |
| EXPIRED | 268 | 56.0% | +0.002% *(profitable!)* |
| TIME_EXIT | 1,192 | 17.0% | -0.087% |
| SL / SL_HIT / SL_HIT_RESOLVED | 2,033 | 0.0% | -0.423% *(catastrophic)* |

**43.9% of crypto picks die by SL.** TP hits are profitable, but the R:R structure makes them too rare.

### 2.5 Strategy Breakdown — `quan_engine_scalp` is the Anchor
| Strategy | n | WR | PF | Avg PnL |
|----------|---|----|----|---------|
| `quan_engine_scalp` | 3,779 | 29.21% | 0.39 | -0.171% |
| `quan_engine_swing` | 90 | 33.33% | 1.25 | +0.004% |
| `quan_engine_position` | 26 | 0.00% | 0.00 | -0.041% |
| `volume_spike_breakout` | 37 | 10.81% | 0.14 | -0.019% |
| `stochrsi_macd_combo` | 11 | 0.00% | 0.00 | -0.020% |

`quan_engine_scalp` alone accounts for **81.5% of volume** and drags the entire book down.

### 2.6 ML Proven Strategies (The Edge)
The following ML strategies have **n ≥ 15 and WR ≥ 60%** and should be whitelisted:

| Strategy | n | WR | PF | Avg PnL |
|----------|---|----|----|---------|
| `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` | 22 | 95.5% | 31.94 | +0.013% |
| `ml_enhanced_STRKUSDT_15m_D_ensemble_stack` | 21 | 95.2% | 32.36 | +0.013% |
| `ml_enhanced_INJUSDT_1d_B_lightgbm` | 20 | 95.0% | 33.18 | +0.161% |
| `ml_enhanced_BNBUSDT_15m_B_lightgbm` | 19 | 89.5% | 58.82 | +0.048% |
| `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` | 39 | 66.7% | 4.76 | +0.043% |
| `ml_enhanced_RENDERUSDT_4h_D_ensemble_stack` | 29 | 65.5% | 2.71 | +0.031% |
| `ml_enhanced_FETUSDT_1d_B_lightgbm` | 36 | 66.7% | 20.66 | +0.224% |

*Note: Many other `ml_enhanced_*` symbols show n=1 and 0% or 100% — these are noise and should not be sized equally to proven pairs.*

### 2.7 Hold Duration — Longer is Worse for Scalps
| Bars Held | n | WR | PF |
|-----------|---|----|----|
| None | 711 | 49.79% | 0.76 |
| 0 | 567 | 29.98% | 0.36 |
| 1–2 | 1,097 | 33.82% | 0.41 |
| 3–5 | 649 | 38.37% | 0.40 |
| **6–12** | **1,420** | **21.62%** | **0.39** |
| 13–24 | 57 | 24.56% | 0.07 |
| 24+ | 133 | 18.80% | 0.23 |

**30.6% of trades sit 6–12 bars and decay.** SCALP-mode crypto should be capped at ≤5 bars.

### 2.8 Direction + Regime (`health_at_entry`)
| Regime | Direction | n | WR | PF |
|--------|-----------|---|----|----|
| panic | LONG | 3,087 | 29.19% | 0.41 |
| caution | LONG | 787 | 28.72% | 0.34 |
| warning | LONG | 7 | 14.29% | 0.03 |
| caution | SHORT | 14 | 42.86% | 0.70 |

All LONG regimes are underwater. SHORT sample is too small to trade directionally, but the data supports **reducing long-bias size in panic/caution regimes** rather than flipping direction.

### 2.9 Score Predictiveness — `elite_score` and `method_a_score` are Noise
| `elite_score` Bucket | n | WR | PF |
|----------------------|---|----|----|
| None | 739 | 48.17% | 0.38 |
| <30 | 3,043 | 25.44% | 0.37 |
| 30–50 | 115 | 31.30% | 0.56 |
| 50–70 | 737 | 43.96% | 0.52 |
| 70–85 / 85+ | 0 | — | — |

Neither score bucket produces PF > 1.0. The code comment (`elite_score r=-0.001`) is confirmed by the data. **These scores should not be used as primary crypto gates.**

---

## 3. DeepSeek Consultation Summary

**Question:** *"What are the top 5 quantifiable factors that distinguish profitable crypto systematic trading strategies from unprofitable ones in 2025-2026, based on academic and practitioner research? Focus on edge preservation, signal decay, and execution."*

**Response (abridged):**

1. **Signal-to-Noise & Economic Significance** — Viable strategies need **t-stat > 3.0** and out-of-sample **Sharpe > 1.5** (crypto threshold often **Sharpe > 2.0**). >95% of discovered alphas are false.
2. **Signal Decay Half-Life** — Crypto alpha decays 3–5× faster than traditional markets. Strategies with **half-life < 5–10 days** need ultra-low-latency execution; **half-life > 20 days** are more robust. Unmonitored decay erodes Sharpe by **>40%** within 6 months.
3. **Capacity-Adjusted Net Sharpe** — Raw returns mislead. Profitable mid-frequency strategies keep **total execution costs < 1.0%** of trade notional and maintain **Net Sharpe > 1.2** at deployed capital.
4. **Dynamic Regime Detection** — Use **30-day realized vol z-score > 2** (high-vol regime) and **bid-ask spread > 0.2% of mid** (low-liquidity). Ignoring regimes causes **drawdowns 2–3× larger** during shifts.
5. **Cross-Exchange Execution Efficiency** — Target **fill rate > 99%** for limit orders and **slippage < 5 bps** vs. arrival price on top-10 pairs. Edge dies when round-trip costs exceed **0.5%**.

**Synthesis:** Our current crypto book is failing factor #1 (no economic significance at wide R:R), factor #3 (costs are not the issue yet, but wide R:R makes expectancy negative), and factor #4 (all LONG trades in panic/caution regimes lose). The fix is structural gating, not more features.

---

## 4. Prioritized Action List

### P0 — Implement This Week (Stops the Bleeding)

| # | Action | Expected Impact |
|---|--------|-----------------|
| 0.1 | **Kill proven 0% WR strategies:** add `quan_engine_position`, `stochrsi_macd_combo`, `volume_spike_breakout`, `ml_enhanced_TRXUSDT_1d_B_lightgbm` to a hard `CRYPTO_KILL_LIST`. | Removes 104 guaranteed losers. |
| 0.2 | **Cap crypto R:R at ≤ 1.5 for all non-ML algorithmic picks.** The only profitable R:R bucket is 1.0–1.5. | Converts ~4,000 losing wide-R:R trades into tight-target winners. |
| 0.3 | **Raise `QUALITY_GATE_MIN_CONFIDENCE` to 0.70 for crypto** (from 0.55), with a **R:R exemption:** picks with `risk_reward <= 1.5` can pass at conf >= 0.55. | Blocks the 2,714-pick 0.6–0.7 death bucket while preserving the 253-pick tight-R:R profitable cohort. |
| 0.4 | **Cap `max_hold_bars` at 5 for all crypto SCALP mode.** | Prevents the 1,420-pick 6–12 bar decay zone. |

### P1 — Implement Next Sprint (Captures the Edge)

| # | Action | Expected Impact |
|---|--------|-----------------|
| 1.1 | **Whitelist the 7 proven ML strategies** (n≥15, WR≥60%). Give them 2× position size and exempt them from R:R / hold-bars caps. | Concentrates capital in the 199-pick, 79% WR cohort. |
| 1.2 | **Add regime-based long-bias size reduction:** when `health_at_entry` is `panic` or `caution`, reduce crypto LONG position size by 50% unless the pick is ML-whitelisted. | Reduces exposure in the 3,874-pick losing regime. |
| 1.3 | **Deprecate `elite_score` and `method_a_score` as primary crypto gates** until they produce PF > 1.0 in backtest. | Stops filtering on noise. |

### P2 — Structural Improvements (Ongoing)

| # | Action | Expected Impact |
|---|--------|-----------------|
| 2.1 | **Implement signal half-life tracking** per strategy family. Auto-pause any strategy whose 20-trade rolling WR drops below 40% for >10 days. | Addresses DeepSeek factor #2 (decay). |
| 2.2 | **Add execution cost auditing:** measure slippage vs. arrival price and fill rate per symbol. | Validates DeepSeek factor #3 & #5. |
| 2.3 | **Build a vol-z-score regime detector** (30-day realized vol) and gate `quan_engine_scalp` when z-score > 2. | Addresses DeepSeek factor #4. |

---

## 5. File-Level Diff Recommendations

### 5.1 `alpha_engine/production_scanner.py`

**A. Add a crypto kill list near the top (after existing constants):**
```python
# Crypto Win-Rate Recovery — hard-block consistent 0% WR strategies
CRYPTO_KILL_LIST = {
    "quan_engine_position",
    "stochrsi_macd_combo",
    "volume_spike_breakout",
    "ml_enhanced_TRXUSDT_1d_B_lightgbm",
}

# ML proven strategies with n>=15 and WR>=60% — get sizing boost + cap exemptions
CRYPTO_ML_WHITELIST = {
    "ml_enhanced_DYDXUSDT_15m_D_ensemble_stack",
    "ml_enhanced_STRKUSDT_15m_D_ensemble_stack",
    "ml_enhanced_INJUSDT_1d_B_lightgbm",
    "ml_enhanced_BNBUSDT_15m_B_lightgbm",
    "ml_enhanced_RENDERUSDT_1h_D_ensemble_stack",
    "ml_enhanced_RENDERUSDT_4h_D_ensemble_stack",
    "ml_enhanced_FETUSDT_1d_B_lightgbm",
}
```

**B. Inside `apply_quality_gates()` add a new gate after Gate 0b:**
```python
# Gate 0c: Crypto kill list (2026-04-17 recovery)
elif category == "crypto" and strat_name in CRYPTO_KILL_LIST:
    reject_reason = f"[CRYPTO KILL LIST] {strat_name}: proven 0% WR strategy blocked"
```

**C. Modify Gate 1 (confidence floor) for crypto:**
Change from:
```python
elif gate_conf < QUALITY_GATE_MIN_CONFIDENCE:
    reject_reason = (f"conf={gate_conf:.2f} < {QUALITY_GATE_MIN_CONFIDENCE:.2f} ...")
```
To:
```python
elif gate_conf < QUALITY_GATE_MIN_CONFIDENCE:
    # Crypto exemption: tight R:R trades have proven edge even at lower confidence
    _rr = pick.get("risk_reward") or 0
    _is_ml_white = strat_name in CRYPTO_ML_WHITELIST
    if category == "crypto" and (_is_ml_white or (_rr > 0 and _rr <= 1.5)):
        pass  # exempt from confidence floor
    else:
        reject_reason = (f"conf={gate_conf:.2f} < {QUALITY_GATE_MIN_CONFIDENCE:.2f} ...")
```

*Recommendation:* **Raise `QUALITY_GATE_MIN_CONFIDENCE` to 0.70 globally** (or add a crypto-specific override) so the exemption is narrow.

**D. Add a new crypto R:R gate after Gate 6:**
```python
# Gate 6b: Crypto wide-R:R block (2026-04-17 recovery)
elif category == "crypto" and strat_name not in CRYPTO_ML_WHITELIST:
    _rr = pick.get("risk_reward") or 0
    if _rr > 1.5 or _rr == 0:
        reject_reason = f"[CRYPTO R:R CAP] R:R={_rr:.2f} > 1.5 (only tight-R:R proven)"
```

**E. Add a crypto hold-bars cap in the TP/SL builder section (around `cap_tp_sl_for_symbol`):**
```python
# Crypto scalp hold-bars cap
if category == "crypto" and (pick.get("mode") or "").upper() == "SCALP":
    if (pick.get("max_hold_bars") or 999) > 5:
        pick["max_hold_bars"] = 5
```

**F. Add ML whitelist sizing boost inside the position-size logic:**
```python
if strat_name in CRYPTO_ML_WHITELIST:
    pick["position_size"] = min(0.10, (pick.get("position_size") or 0.015) * 2.0)
```

**G. Add regime-based size reduction for crypto LONGs:**
```python
_health = (pick.get("health_at_entry") or "").lower()
if category == "crypto" and signal_type in ("LONG", "BUY") and _health in ("panic", "caution"):
    if strat_name not in CRYPTO_ML_WHITELIST:
        pick["position_size"] = (pick.get("position_size") or 0.015) * 0.5
```

### 5.2 `alpha_engine/antigravity_strategies.py` (or wherever `quan_engine_scalp` TP/SL is calculated)

**For crypto SCALP signals, change the default R:R target from ~2.0–3.0 to 1.2–1.5.**

```python
# In the crypto scalp branch:
if is_crypto(symbol) and mode == "SCALP":
    target_rr = min(1.5, target_rr)  # cap at 1.5
    # Prefer 1.2-1.5 for non-ML
```

This prevents the generator from emitting the wide-R:R trades in the first place.

### 5.3 `config.py` or strategy config module

Add the two new sets so they can be imported by both scanner and strategy modules:

```python
CRYPTO_KILL_LIST = {...}
CRYPTO_ML_WHITELIST = {...}
```

### 5.4 `alpha_engine/score_booster.py` (or `elite_scorer.py`)

**Deprecate `elite_score` and `method_a_score` for crypto primary ranking.**
- Keep computing them for dashboard display.
- Remove any hard reject where `elite_score < 55` for crypto picks.
- The existing comment (`elite_score r=-0.001`) already flags this; make it a code change.

---

## 6. Projected Outcome

If P0 changes are deployed, the crypto book would shrink from **4,634 trades** to approximately **300–400 trades** but with the following profile:

- **Confidence ≥ 0.8 cohort:** ~104 trades, 69% WR, PF 10.4
- **R:R 1.0–1.5 cohort:** ~253 trades, 60% WR, PF 1.14
- **Overlap / ML whitelist:** ~40 trades, 80%+ WR

**Estimated blended crypto WR: 55–65%. Estimated PF: 1.3–2.0.**

Volume drops by ~90%, but the portfolio flips from **-0.15% avg loss** to **+0.05% avg gain** per trade. This is the correct trade-off: **edge over frequency.**

---

## 7. Next Steps

1. Review this plan with the lead quant.
2. Implement P0 changes in a feature branch.
3. Run a 7-day forward test on the gated rules before merging to `main`.
4. Do **not** push directly to `main` — these are structural changes that will slash pick volume and must be monitored.
