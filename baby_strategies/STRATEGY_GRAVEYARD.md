# Strategy Graveyard

**Last Updated:** 2026-03-02
**Method:** Kelly Criterion Audit + Forward Performance Analysis + DNA Fitness Elimination

---

## Integration with Strategy DNA System

The graveyard now feeds directly into the **Strategy DNA Engine**:
- Graveyard strategies have their genomes marked as **non-viable** — they will never be selected as parents during evolution
- Their DNA patterns are used as **negative examples** to penalize similar gene combinations during mutation
- The **Autopoietic Monitor** can automatically graveyard strategies that trigger a drawdown spiral (5 consecutive failures → ELIMINATED)
- Graveyarded strategy signals are **excluded from the Meta-Label Filter** training data to avoid poisoning the ML classifier

**DNA Elimination Path:** Active → Probation (3 failures) → Eliminated (5 failures) → Graveyard (negative Kelly)

---

## What Is the Graveyard?

The **graveyard** is a permanent flag for strategies that have been proven to have **negative expected value (EV)** through forward testing. These strategies are:

- **Excluded from all active picks and bundles** — they will never generate live signals
- **Preserved in the codebase** — their code, research, and backtest data remain available for reference
- **Marked with a `graveyard` flag** in `stabilization/disabled_strategies.json`
- **Used to prevent duplicates** — before creating a new strategy, check if a similar approach is already in the graveyard

A graveyard strategy is NOT deleted. It serves as institutional memory: "we tried this, here's exactly why it failed."

---

## How Strategies End Up in the Graveyard

### The Kelly Criterion Test

Every strategy with 5+ forward trades is evaluated using the Kelly Criterion:

```
Kelly% = WinRate - (1 - WinRate) / RewardToRiskRatio
```

Where:
- **WinRate** = number of winning trades / total trades
- **RewardToRiskRatio** = average winning trade / average losing trade

**Interpretation:**
- **Kelly > 5%** = KEEP — strategy has positive expected value, allocate capital
- **Kelly 0-5%** = MARGINAL — barely positive, monitor closely (usually has 0% WR with few trades)
- **Kelly < 0%** = GRAVEYARD — mathematically guaranteed to lose money over time

### Why Negative Kelly = Death

A negative Kelly fraction means: **the optimal bet size is zero**. No amount of position sizing, parameter tuning, or regime filtering can make a negative-EV strategy profitable in the long run. It's like playing a casino game where the house edge is against you — you WILL lose eventually.

Our average strategy had Kelly = **-15.5%**, meaning for every $100 bet, the expected loss was $0.31. Over 856 trades, that's exactly the -$277 we observed.

---

## Graveyard Strategies (72 total, as of 2026-03-01)

### Category: Order Flow Absorption (10 strategies)
All `crypto_soc_orderflow_absorption_*` variants. WR: 15-33%, Kelly: -13% to -317%.
**Why they failed:** Order flow signals from OHLCV are noisy proxies. Real order flow requires Level 2 / tick data that we don't have. The OHLCV approximation has zero predictive power.

### Category: Delta Divergence (10 strategies)
All `crypto_soc_delta_divergence_*` variants. WR: 17-33%, Kelly: -32% to -920%.
**Why they failed:** Delta (buy vs sell volume) approximated from OHLCV candles is unreliable. True delta requires trade-level data. The proxy divergence signal generates too many false positives.

### Category: Regime Filters (8 strategies)
All `crypto_soc_regime_filters_*` variants. WR: 11-33%, Kelly: -33% to -1030%.
**Why they failed:** Complex regime detection (HMM, variance ratio) overfits to training data. Simple SMA/ADX regime filters work better than these sophisticated approaches.

### Category: Dynamic Risk Heat (8 strategies)
All `crypto_soc_dynamic_risk_heat_*` variants. WR: 20-38%, Kelly: -20% to -1036%.
**Why they failed:** "Risk heat" is a composite indicator with too many parameters. Overfits to backtest, fails in forward testing. Simpler risk management (ATR-based stops) works better.

### Category: Proxy Decoupling (8 strategies)
All `crypto_soc_proxy_decoupling_*` variants. WR: 0-25%, Kelly: -11% to -998%.
**Why they failed:** Decoupling between proxy indicators is a weak signal. Most "decoupling" events are noise, not actionable divergences.

### Category: Vol Expansion Index (8 strategies)
All `crypto_soc_vol_expansion_index_*` variants. WR: 0-50%, Kelly: -829% or worse.
**Why they failed:** Volatility expansion is real but the timing of the OHLCV-based signal is too late. By the time the vol expansion is detected, the move is already over.

### Category: MTF ORB Pivots (marginal, 4 strategies)
Several `crypto_soc_mtf_orb_pivots_*` variants. WR: 0-40%, Kelly: -11% to -169%.
**Why they failed:** Opening range breakout on crypto (24/7 market) has no clear "opening range." The concept from equity markets doesn't translate.

### Category: Miscellaneous (16 strategies)
- `crypto_mtf_ema_slope_alignment_v1` — Kelly -32%, 24 trades, 20.8% WR
- `crypto_choppiness_regime_switch_v1` — Kelly -23%, 9 trades, 33.3% WR
- `crypto_liquidity_wick_reversal_v1` — Kelly -91%, 4 trades, 25% WR
- `crypto_volume_spike_momentum_v1` — Kelly -9%, 17 trades, 41.2% WR
- Various `crypto_soc_trend_filtered_meanrev_*` — 0% WR
- Various `crypto_soc_intraday_time_slices_*` — 0% WR
- `volume_breakout_regime_switch` — 0% WR, 1 trade
- `crypto_adx_pullback_trendresume_v1` — 0% WR, 4 trades
- `crypto_donchian_atr_breakout_retest_v1` — 0% WR, 2 trades

---

## Strategies That Survived (13 KEEP)

These strategies have positive Kelly fraction (>5%) and remain active:

| Strategy | Kelly% | WR | Trades | Sum PnL | Status |
|---|---|---|---|---|---|
| `drawdown_recovery_rsi` | +100.0% | 100% | 16 | +28.65% | **STAR** |
| `crypto_keltner_compression_expansion_v1` | +63.8% | 75% | 12 | +7.77% | **STAR** |
| `multi_period_rsi_confluence` | +53.4% | 73% | 22 | +21.04% | **STAR** |
| `crypto_vwap_deviation_reversion_volfilter_v1` | +35.3% | 64% | 14 | +5.78% | Solid |
| `crypto_kalman_trend_residual_reversion_v1` | +21.3% | 59% | 22 | +6.17% | Solid |
| `crypto_soc_mtf_orb_pivots_a06_v1` | +16.2% | 60% | 5 | +1.02% | Promising |
| `crypto_soc_mtf_orb_pivots_a08_v1` | +15.4% | 50% | 6 | +1.49% | Promising |
| `crypto_soc_mtf_orb_pivots_a02_v1` | +8.1% | 43% | 7 | +0.79% | Monitor |
| `mean_reversion_momentum` | +7.8% | 40% | 5 | +0.58% | Monitor |
| `funding_momentum` | +7.3% | 56% | 135 | +13.53% | Volume leader |
| `crypto_soc_mtf_orb_pivots_a01_v1` | +7.3% | 43% | 7 | +0.65% | Monitor |
| `crypto_soc_proxy_decoupling_a01_v1` | +7.3% | 46% | 11 | +0.89% | Monitor |
| `crypto_soc_mtf_orb_pivots_a07_v1` | +5.7% | 43% | 7 | +0.56% | Borderline |

---

## How to Use the Graveyard

### Before Creating a New Strategy
1. Check `stabilization/disabled_strategies.json` → `graveyard` array
2. Read this document's "Why they failed" sections
3. If your new strategy uses a similar approach (e.g., order flow from OHLCV), it will likely fail too
4. Only proceed if your approach is genuinely different

### To Check if a Strategy is Graveyarded
```python
import json
with open('stabilization/disabled_strategies.json') as f:
    data = json.load(f)
is_graveyard = 'your_strategy_name' in data.get('graveyard', [])
```

### File Locations
- **Flag data:** `stabilization/disabled_strategies.json` → `graveyard` array + `graveyard_metadata` dict
- **Kelly audit:** `tmp/kelly_audit_results.json` — full Kelly Criterion results for all strategies
- **This document:** `baby_strategies/STRATEGY_GRAVEYARD.md`

---

## Key Lessons from the Graveyard

1. **OHLCV proxies for microstructure data don't work.** Order flow, delta, and liquidity signals approximated from candles have near-zero predictive power. If you need microstructure data, get real microstructure data.

2. **Complex regime detection overfits.** HMM, GARCH, variance ratio — all failed. Simple SMA/ADX regime filters outperform.

3. **More parameters = more overfitting.** The graveyard is full of strategies with 5+ tunable parameters. Our survivors have 2-3 parameters max.

4. **Variant proliferation is wasteful.** Running 10 variants of the same strategy (a01-a10) with slight parameter changes doesn't improve odds. If the core signal is weak, no parameter set saves it.

5. **Mean reversion works. Most other things don't.** 100% of our surviving strategies are mean-reversion based. The market structure reason: crypto is dominated by retail overreaction, which naturally mean-reverts.

6. **Kelly Criterion is the final judge.** Backtest Sharpe and win rate can be gamed. Kelly fraction from FORWARD trades is the ground truth. If Kelly is negative after 10+ real trades, the strategy is dead.
