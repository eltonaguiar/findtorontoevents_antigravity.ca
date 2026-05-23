# Non-Crypto Win-Rate Recovery Plan

**Date:** 2026-04-17  
**Analyst:** Quantitative Trading Research Agent  
**Scope:** Diagnose why non-crypto asset classes show negative aggregate stats and propose a concrete recovery plan.

---

## Executive Summary

The non-crypto crisis is **not** a strategy-quality problem in the traditional sense—it is a **pipeline-wiring problem**. The academically-backed non-crypto strategies sitting in `alpha_engine/` are **completely disconnected** from production. The picks that actually make it into the live pipeline come from copy-trader scrapers and external signal trackers that have no proven edge. Until the dedicated strategy files are wired into `production_scanner.py`, non-crypto will continue to bleed capital.

---

## 1. Quantified Findings

### 1.1 `alpha_engine/data/closed_picks.json` (Primary Source)

| Asset Class | Count | Win Rate | Profit Factor | Avg PnL |
|-------------|-------|----------|---------------|---------|
| CRYPTO      | 4,634 | 32.2%    | 0.39          | -0.149% |
| FOREX       | 6     | 0.0%     | 0.00          | -0.000% |
| FUTURES     | 2     | 0.0%     | 0.00          | -0.016% |
| EQUITY      | 1     | 0.0%     | 0.00          | -0.031% |

**Critical observation:** Only **9 non-crypto picks** exist in the main closed-picks file (0.19% of the dataset). Non-crypto is practically **absent** from the primary back-test and closed-pick pipeline.

**Source breakdown (9 picks):**
- `multi_asset_copytrader`: 7 picks, 0% WR, PF 0.00
- `forex_copy_trader`: 1 pick, 0% WR
- `multi_asset_cot`: 1 pick, 0% WR

**Profitable strategies (PF > 1.5, n >= 10):** **None.**

### 1.2 `audit_trail/data/universal_resolved_picks.json` (Cross-Check)

| Asset Class | Count | Win Rate | Profit Factor | Avg PnL |
|-------------|-------|----------|---------------|---------|
| CRYPTO      | 3,985 | 48.4%    | 1.59          | +0.488% |
| EQUITY      | 641   | 39.8%    | 1.04          | +0.046% |
| FOREX       | 9     | 44.4%    | 1.31          | +0.291% |

**Non-crypto source breakdown (650 picks):**

| Source System              | Count | WR    | PF   | Avg PnL |
|----------------------------|-------|-------|------|---------|
| `kimi_signal_tracking`     | 409   | 36.7% | 0.99 | -0.011% |
| `signal_validation`        | 134   | 57.5% | 2.14 | +0.793% |
| `stocks_competition`       | 47    | 29.8% | 0.72 | -0.521% |
| `regime_terminal`          | 22    | 36.4% | 1.07 | +0.068% |
| `alpha_engine`             | 16    | 43.8% | 0.84 | -0.326% |
| `riseoftheclaw`            | 16    | 18.8% | 0.33 | -1.323% |
| `alpha_engine_fast`        | 6     | 0.0%  | 0.00 | -3.352% |

**Profitable strategies (PF > 1.5, n >= 10):**
1. `MeanReversionBB` — n=99, WR=56.6%, PF=2.04
2. `MomentumEMA` — n=35, WR=60.0%, PF=2.40

Both profitable strategies are dominated by the `signal_validation` source system.

### 1.3 `audit_trail/data/dashboard_payload.json` (Full Historical Aggregate)

| Asset Class | Closed | WR    | PF   | Assessment                     |
|-------------|--------|-------|------|--------------------------------|
| CRYPTO      | 18,818 | 46.4% | 1.18 | Only stable profit engine      |
| EQUITY      | 721    | 52.0% | 1.39 | *Positive aggregate*           |
| FOREX       | 1,185  | 45.1% | 0.26 | **Severely underwater**        |
| COMMODITY   | 420    | 40.2% | 1.14 | Barely breakeven               |
| ETF         | 74     | 48.4% | 0.86 | **Negative edge**              |
| FUTURES     | 19     | 0.0%  | 0.00 | Dead pipeline                  |
| BOND        | 17     | 50.0% | 1.60 | Thin sample                    |

**System-level non-crypto disasters (selected):**

| System                      | Closed | WR    | PF   | Asset Classes         |
|-----------------------------|--------|-------|------|-----------------------|
| `forex_copy_trader`         | 61     | 3.0%  | 0.31 | FOREX, COMMODITY      |
| `fast_stocks_competition`   | 60     | 0.0%  | 0.00 | EQUITY                |
| `goldmine_stocks`           | 183    | 0.0%  | 0.00 | EQUITY, ETF           |
| `non_crypto_consensus`      | 64     | 0.0%  | 0.00 | COMMODITY, FOREX      |
| `kimi_claw_research`        | 50     | 0.0%  | 0.00 | CRYPTO, EQUITY, FOREX |
| `kimi_signal_tracking`      | 272    | 35.8% | 0.38 | CRYPTO, EQUITY, FOREX |

**System-level non-crypto winners (preserve):**

| System                | Closed | WR    | PF   | Asset Classes         |
|-----------------------|--------|-------|------|-----------------------|
| `signal_validation`   | 256    | 56.5% | 1.93 | CRYPTO, FOREX         |
| `aggregated_picks`    | 316    | 56.7% | 2.33 | CRYPTO, EQUITY, FOREX |
| `super_signals`       | 163    | 88.3% | 9.17 | CRYPTO, EQUITY, ETF   |

### 1.4 Confidence Observations (Current Data)

Because `closed_picks.json` contains only 9 non-crypto picks, independent confidence-bucket analysis is underpowered. However, the existing picks align with the prior finding that mid-range confidence is toxic for non-crypto:

- **Forex** (6 picks): all locked at `confidence=0.7500`, 0% WR
- **Futures** (1 pick): `confidence=0.5500`, loser
- **Equity** (1 pick): `confidence=0.6800`, loser

In `universal_resolved_picks.json`, the `kimi_signal_tracking` equity pool (409 picks, PF=0.99) is essentially breakeven, while the `signal_validation` pool (134 picks, PF=2.14) is the only non-crypto sub-system with a meaningful edge. This suggests **source-system quality matters far more than confidence alone** for non-crypto.

---

## 2. Root Cause Assessment

### 2.1 The Smoking Gun: Orphaned Strategy Files

A grep of `alpha_engine/production_scanner.py` reveals that **NONE** of the dedicated non-crypto strategy modules are imported or invoked:

| Strategy File                        | Wired into `production_scanner.py`? |
|--------------------------------------|-------------------------------------|
| `alpha_engine/equity_strategies.py`  | ❌ NO                               |
| `alpha_engine/forex_strategies.py`   | ❌ NO                               |
| `alpha_engine/commodities_strategies.py` | ❌ NO                           |
| `alpha_engine/etf_strategies.py`     | ❌ NO                               |
| `alpha_engine/bond_strategies.py`    | ❌ NO                               |
| `copy_trader_intel/non_crypto_consensus.py` | ❌ NO                        |

**Implication:** The academically-backed strategies (momentum factor, RSI2 mean reversion, seasonal commodities, dual-momentum ETF rotation, bond yield momentum) are **dead code**. They generate no picks. All non-crypto exposure comes from external scrapers and copy-trader integrations that were never validated.

### 2.2 Where Non-Crypto Picks Actually Come From

`production_scanner.py` pulls non-crypto picks from three places:

1. **`copy_trader_intel/data/forex_copytrader_picks.json`** — merged directly into active pipeline (line ~3005)
2. **`isolated_signal_integrator.py`** — pulls from `regime_terminal`, `rapid_fire`, etc. (line ~3037)
3. **Various `multi_asset_*` scrapers** — `multi_asset_copytrader`, `multi_asset_cot`, `multi_asset_scanner`, `multi_asset_institutional`

These sources have **no back-tested edge**. They are sentiment aggregators, social-copy feeds, and competition scrapers—not quant strategies.

### 2.3 The Auto-Tuner Is Already Blocking Most Non-Crypto

`production_scanner.py` contains:

```python
_BLOCKED_CATEGORIES = {"equity", "stock", "etf", "commodity", "futures", "bond"}
```

and:

```python
QUALITY_GATE_FOREX_MIN_WR = 0.30
```

This means the system **already knows** non-crypto is broken and is trying to contain the damage. But because the pipeline is fed by scrapers rather than validated strategies, the bleed continues from the few sources that slip through (forex copy-trader, fast stocks competition, etc.).

---

## 3. Prioritized Recovery Plan

### P0 — Stop the Bleeding (Do Immediately)

1. **Disable all unprofitable non-crypto source systems** in `production_scanner.py`.
   - `forex_copy_trader` (3% WR, PF 0.31)
   - `fast_stocks_competition` (0% WR)
   - `goldmine_stocks` (0% WR)
   - `non_crypto_consensus` (0% WR)
   - `kimi_claw_research` (0% WR)
   - `multi_asset_cot` (0% WR on commodities)
   - `cta_replicator` (8.4% WR, PF 0.65)

2. **Preserve only the three proven non-crypto sources:**
   - `signal_validation`
   - `aggregated_picks`
   - `super_signals`

3. **Add a hard `source_system` whitelist** for non-crypto in `production_scanner.py`. Any non-crypto pick from a source not explicitly whitelisted should be dropped at ingestion.

### P1 — Wire the Real Strategies (This Week)

4. **Integrate `alpha_engine/*_strategies.py` into `production_scanner.py`.**
   - Create a `run_non_crypto_strategies(data)` helper that calls:
     - `equity_strategies.momentum_factor_12m()`
     - `equity_strategies.mean_reversion_bb()`
     - `forex_strategies.connors_rsi2()`
     - `forex_strategies.london_breakout()`
     - `commodities_strategies.seasonal_momentum()`
     - `etf_strategies.etf_dual_momentum()`
     - `bond_strategies.bond_yield_momentum()`
   - Route their outputs through the same confidence gates and enrichment pipeline used for crypto.

5. **Wire `copy_trader_intel/non_crypto_consensus.py` into the pipeline.**
   - The consensus engine already aggregates CTA, forex copy-trader, multi-asset, commodity, equity, and futures picks.
   - **But:** it must be gated by the same whitelist. Do not allow consensus to launder picks from disabled sources.

### P2 — Validate, Gate, and Gradually Re-Enable (Next 2–4 Weeks)

6. **Implement per-asset-class confidence gates** in `production_scanner.py`:
   - **Equity:** require `confidence >= 0.90` OR `confidence <= 0.50` (avoid the 0.85–0.90 death zone)
   - **Forex:** require `confidence >= 0.75` AND `confidence <= 0.80` (only proven band)
   - **Commodity:** require `confidence >= 0.70` AND `confidence <= 0.75`
   - **ETF/Futures/Bond:** block entirely until at least one strategy proves PF > 1.5 on 20+ live trades

7. **Add macro regime filters:**
   - Equity: only trade when SPY 20d SMA > 50d SMA (bull regime)
   - Forex: block when 14d ATR > 2x baseline (news/flash-crash regime)
   - Commodities: only trade in seasonally bullish months with USD trend confirmation

8. **Run a 30-trade forward-test pilot** for each newly wired strategy:
   - Start with 0.5% risk per trade
   - Require PF > 1.3 and WR > 45% to graduate to full sizing
   - Log all results to `audit_trail/data/non_crypto_forward_test.json`

---

## 4. File-Level Recommendations

| File | Action | Rationale |
|------|--------|-----------|
| `alpha_engine/production_scanner.py` | Add `NON_CRYPTO_SOURCE_WHITELIST`; block all non-crypto not from `signal_validation`, `aggregated_picks`, or `super_signals` | Stops bleeding from toxic scrapers |
| `alpha_engine/production_scanner.py` | Import and call `equity_strategies`, `forex_strategies`, `commodities_strategies`, `etf_strategies`, `bond_strategies` | Brings academically-backed strategies online |
| `alpha_engine/production_scanner.py` | Add per-asset-class confidence buckets (equity bipolar gate, forex 0.75–0.80 band, etc.) | Filters out the confidence zones proven to lose |
| `copy_trader_intel/non_crypto_consensus.py` | Wire into `production_scanner.py`; respect the source whitelist | Prevents consensus from laundering bad picks |
| `alpha_engine/equity_strategies.py` | Add `forward_test_only=True` flag to all signals until 20-trade validation | Safe rollout |
| `alpha_engine/forex_strategies.py` | Add `forward_test_only=True` flag to all signals until 20-trade validation | Safe rollout |
| `alpha_engine/commodities_strategies.py` | Add `forward_test_only=True` flag to all signals until 20-trade validation | Safe rollout |
| `alpha_engine/etf_strategies.py` | Add `forward_test_only=True` flag to all signals until 20-trade validation | Safe rollout |
| `alpha_engine/bond_strategies.py` | Add `forward_test_only=True` flag to all signals until 20-trade validation | Safe rollout |
| `alpha_engine/non_crypto_quality_gate.py` (or create it) | Implement macro regime checks (SPY trend, VIX, FX vol, USD trend) | Ensures non-crypto only trades when macro tailwinds exist |

---

## 5. Summary

Non-crypto is losing because **the wrong code is running in production**. The quant strategies that were designed for equities, forex, commodities, ETFs, and bonds are sitting unused in `alpha_engine/`, while the live pipeline is fed by unvalidated copy-trader scrapers with 0–8% win rates. 

**The recovery is straightforward:**
1. **Cut** the toxic scrapers (P0).
2. **Wire** the real strategies (P1).
3. **Gate** them by confidence and macro regime (P2).
4. **Forward-test** before scaling.

Until these steps are complete, the only defensible non-crypto exposure should come from the three proven sources: `signal_validation`, `aggregated_picks`, and `super_signals`.
