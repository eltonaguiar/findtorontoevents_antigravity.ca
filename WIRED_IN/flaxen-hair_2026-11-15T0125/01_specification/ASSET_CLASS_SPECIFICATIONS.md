# ML / Algorithm & Data Staleness Audit — WIRED_IN flaxen-hair_2026-11-15T0125

**Date:** 2026-11-15  
**Worktree:** flaxen-hair_2026-11-15T0125  
**Repo:** findtorontoevents_antigravity.ca

---

## 1. EXECUTIVE SUMMARY

**CRITICAL FINDING: 0/23 hypotheses across 4 protocol versions survived clean out-of-sample, effective-N, capital, and execution gates. ALL 9 asset classes return `sizing_allowed: false`.**

No asset class has statistically valid, truly profitable predictive algorithms. Every closed-pick backtest has n < 50 trades (the minimum for statistical significance per PROOF_PROTOCOL.md), and every forward-test pick has `forward_test_only=true` with `pnl_pct=null` — meaning zero live PnL has been recorded for any strategy.

### Key Numbers
- **23 hypotheses** tested across 4 protocol versions — ALL rejected
- **9 asset classes** analyzed — all fail money-ready gates
- **12 active picks** in `live_picks.json` — all have `status=OPEN`, all have `forward_test_only=true`, all have `pnl_pct=null`, all have `forward_validated=false`
- **38 picks** in `multi_asset_picks.json` — all `forward_test_only=true`, `forward_validated=false`, `forward_trades=0`, all `pnl_pct=null`
- **98 picks** in `multi_asset_closed.json` (45 open, 53 closed) — all closed at 2026-03-11→03-13, all stale (~8 months old)
- **23 picks** in `institutional_picks.json` — all OPEN, dated 2026-04-03 (~7.5 months stale), all `forward_test_only=true`
- **Total asset classes:** 10 (equity, ETF, bonds, forex, crypto, commodities, futures, mutual funds, penny stocks, meme coins)
- **Mutual funds:** ZERO coverage — no algorithm, no data source, no asset-class registration

---

## 2. ASSET CLASS SPECIFICATIONS

### EQUITY — SLOT 1 (PRIORITY RESEARCH CANDIDATE)

**Status:** Only class with positive cost margin (3.23×, mean +0.323% per trade on n=738 closed picks). Only class with a pre-registered benchmark test path vs SPY total return.

**Strategies (15+ in `alpha_engine/equity_strategies.py`):**
| Strategy | Direction | Status | Backtest Status |
|----------|-----------|--------|---------------|
| `connors_rsi2_scanner` | LONG | Active | SPY: WR 75.7%, p=6e-6; n=6, too small for significance |
| `vix_spike_reversal_scanner` | BUY | Active | SPY: WR 72%, p=0.022 |
| `triple_rsi_scanner` | BUY | Active | Published WR 50%, PF 5.0 (20yr), n=12 live trades |
| `support_resistance_bounce` | BUY | Active | All EQUITY_SYMBOLS |
| `connors_rsi2_short_scanner` | SELL | Active | Mirror of connors_rsi2_scanner, confidence capped 0.65 |
| `equity_two_bar_rsi_reversal` | BUY | Active but opt-in (`EQUITY_RSI2_TWOBAR_ENABLED=1`) | Shadow period only |
| `macd_divergence_tuned` | BUY | Active | Picks: META dated 2026-04-03 (~7.5 months old, still OPEN) |
| `ema_stack_momentum` | BUY | Active | Open pick: HD entry 215.11 → TP 225.87 → SL 204.35 |
| `macd_divergence` (forex_strategies.py) | BUY | Active | EURUSD exit == entry → pnl_pct = -0.00567 (unrealized_pnl_pct bug) |

**Open equity picks (`multi_asset_picks.json`):**
| Symbol | Strategy | Direction | Entry Price | TP | SL | Confidence | Status |
|--------|----------|-----------|-------------|-----|-----|-----------|--------|
| HD | `multi_asset_stocks_rsi2_pullback` | LONG | ? | ? | ? | ? | OPEN |
| TMO | `stocks_rsi2_pullback` | LONG | 700.22 | 735.23 | 679.21 | 0.639 | OPEN |
| AVGO | `stocks_ema_golden_cross` | LONG | 347.01 | 407.75 | 316.64 | 0.600 | OPEN |
| SPY | `cta_golden_cross_200` | LONG | 754.37 | 786.29 | 735.22 | 0.600 | OPEN |

**Critical Issues:**
- All 4 equity OPEN picks have `pnl_pct=null`, `exit_price=null`, `forward_test_only=true`, `forward_validated=false`, `forward_trades=0` — no verifiable live PnL
- `confidence == ml_score` exactly on every pick (0.592/0.592, 0.639/0.639, 0.600/0.600) — ML score is copied from confidence, not independent
- META `macd_divergence_tuned` entry dated 2026-04-03 (~7.5 months old) still OPEN — stale open pick

### CRYPTO — SLOT 2 (CONDITIONAL — requires fill fix)

**Status:** 700+ strategies across `alpha_engine/crypto_strategies.py` (35 direct strategies) plus `quantum_fusion_crypto_engine`, `ml_crypto_predictor`, `copy_trader_intel/non_crypto_quality_enhancer.py`. **All fail clean-cohort screen.**

**Strategy Categories:**
- `vix_reversal` (equity futures) — not crypto-specific
- `crypto_strategies.py` (35 direct strategies): Ichimoku, RSI, MACD, Wyckoff, SMC/FVG, RSI divergence, breakout, StochRSI, Hurst, entropy RSI, CoinGecko trending, altcoin season, ApeWisdom social, BTC dominance reversal, weekend drift
- `antigravity_strategies.py` (8 crypto adapters): `vwap_rsi_institutional`, `liquidation_cascade_contrarian`, `regime_sentinel_composite`, `rsi_pairs_arbitrage`
- `ml_crypto_predictor/`: Enhanced models — live picks tracker, train model, token sniffer, self-improver
- `copy_trader_intel/non_crypto_quality_enhancer.py` — Crypto pick quality enhancer
- `ml_gatekeeper/polymarket_signals.py` — Prediction market signals

**Critical Finding: ZERO crypto picks in either JSON file.**
- `multi_asset_picks.json`: 41 picks, 0 crypto
- `multi_asset_closed.json`: 93 picks, 0 crypto
- Reason: All crypto strategies emit picks with `asset_class=FOREX` or `PENNY_STOCK` instead of `CRYPTO`

**Fill Bug:** `entry_price` is ~29% clean (37% >10% off bar, 7% >50%) with systematic +1.3% bias (inflates SHORT, deflates LONG). `~90% positions never resolve` — `kimi_riseoftheclaw` stale fill data; `fetch_current_price()` returns None when Binance geo-blocked (HTTP 451).

---

## 3. ASSET CLASSES BLOCKED (Do Not Deploy)

| Asset Class | Strategies | Picks | Status | Blocker |
|-------------|-----------|-------|--------|---------|
| **BONDS** | `bond_*`, `treasury_yield_curve`, `credit_spread`, `duration_rotation`, `bond_equity_rotation` | 0 closed, 0 open | BLOCKED | n=11-18 below min_trades=60, futures-only coverage |
| **FOREX** | `forex_rsi2_mean_reversion`, `forex_zscore_200d_fade`, `forex_carry_momentum`, `macd_divergence`, `ig_contrarian_sentiment` | 0 forward-validated | BLOCKED | Zero DSR survivors, PF 0.97 fails |
| **COMMODITY** | `futures_momentum`, `cot_positioning`, `cot_positioning_commercial_signal`, `cta_commodity_momentum` | 7 open, 0 closed | BLOCKED | COT contrarian failed all 4 pre-registered checks |
| **FUTURES** | `futures_momentum`, `cot_positioning` | 0 picks | DEAD | WR 5.9%, PnL -96% |
| **MUTUAL FUNDS** | Zero strategies | 0 picks | BLOCKED | Zero coverage — no algorithm, no data source |

---

## 4. CRITICAL DATA QUALITY ISSUES

### 4.1 PnL Unit Mismatch (ratio vs percent, up to 100×)

**Files:** `multi_asset/data/multi_asset_closed.json` (93 rows), `multi_asset/data/institutional_closed.json` (23 rows)

**Finding:** `pnl_pct`/`realized_pnl_pct` stored as decimal ratio (e.g., -0.04 = -4%) in SOME rows and as percent number (e.g., -2.7041 = -2.7041%) in others. Same symbol/strategy rows disagree up to 100×:

| Symbol | Strategy | Stated pnl_pct | Recomputed Ratio | Unit Discrepancy |
|--------|----------|----------------|------------------|------------------|
| `vix_reversal::SI=F` | vix_reversal | -3.6402 | -0.036402 | 100× (stated as percent, is ratio) |
| `vix_reversal::SI=F` | vix_reversal | -3.4652 | -0.034652 | 100× (stated as percent, is ratio) |
| `vix_reversal::SI=F` | vix_reversal | -0.04244 | -0.0400 | ≈ match (both ratio) |
| `vix_reversal::SI=F` | vix_reversal | -0.03228 | -0.03228 | exact match |

**Impact:** Cross-asset-class PnL aggregation wrong by up to 100×. Normalization required.

### 4.2 Non-Unique Pick IDs

**Severity:** HIGH  
**Affected Files:** `multi_asset/data/multi_asset_closed.json`, `multi_asset/data/institutional_closed.json`  
**Description:** Pick IDs use date-only format (`<strategy>::<symbol>::<date>`), producing duplicates:

| Duplicate ID | Count |
|--------------|-------|
| `vix_reversal::SI=F::2026-03-11` | 4 |
| `extreme_oversold_bounce::EURUSD=X::2026-03-12` | 5 |
| `ema_stack_momentum::CL=F::2026-03-11` | 2 |
| `bb_mean_reversion_forex::NZDUSD=X::2026-03-13` | 2 |
| `connors_rsi2::SI=F::2026-03-12` | 2 |

### 4.3 Stale Picks

**Severity:** HIGH  
**Count:** ~30 stale OPEN picks

**`institutional_picks.json`:** All 22 picks dated 2026-04-03 (~7.5 months old), all OPEN, all `forward_test_only=true`, all `pnl_pct=null`.

**`recent_picks.txt`:** CL=F and ZN=F still OPEN from 2026-03-11 (~8 months old), header claims "Past 2 Hours (since 6:24 PM EST)" — header is WRONG.

### 4.4 `ml_score == confidence` Coupling

**Severity:** MEDIUM  
**Finding:** On every OPEN pick, `confidence == ml_score` exactly (0.75/0.592, 0.639/0.639, 0.600/0.600). ML score is a verbatim copy of confidence, not an independent ML output.

---

## 5. PICK LIFECYCLE ISSUES

### 4.1 Forward-Test-Only Picks (No Live PnL)
**Files:** `multi_asset_picks.json` (41 picks), `institutional_picks.json` (22 picks)  
**Issue:** All picks have `forward_test_only=true`, `pnl_pct=null`, `exit_price=null`, `hold_days=null`, `forward_trades=0`, `forward_validated=false`.  
**Impact:** Zero verifiable live PnL exists for any strategy. Cannot calculate win rate, profit factor, or drawdown from live trading.

### 4.2 Stale OPEN Picks
**30+ stale OPEN picks** across all files:
- `institutional_picks.json`: 22 picks, all dated 2026-04-03 (~7.5 months old), all OPEN
- `recent_picks.txt`: CL=F and ZN=F still OPEN from 2026-03-11 (~8 months old), header claims "Past 2 Hours" (WRONG)

### 4.5 Duplicate Pick IDs
**Severity:** HIGH  
**Cause:** Pick IDs use date-only format (`<strategy>::<symbol>::<date>`) without timestamp component.  
**Examples:**
- `vix_reversal::SI=F::2026-03-11` — 4 occurrences
- `extreme_oversold_bounce::EURUSD=X::2026-03-12` — 5 occurrences
- `ema_stack_momentum::CL=F::2026-03-11` — 2 occurrences
- `bb_mean_reversion_forex::NZDUSD=X::2026-03-13` — 2 occurrences
- `connors_rsi2::SI=F::2026-03-12` — 2 occurrences

---

## 6. PROPOSED FIXES

### 4.1 Normalize PnL Units (P0)
**File:** `quick_wins/shared/normalize_pnl_units.py`  
**Action:** Recompute `pnl_pct = (exit_price / entry_price - 1) * direction` for all CLOSED picks. Store as decimal ratio (e.g., -0.04 = -4%). OPEN picks keep `pnl_pct=null`.

### 4.2 Make Pick IDs Unique (P0)
**File:** `multi_asset/scanner.py:_pick_id()`  
**Action:** Add timestamp component: `f"{strategy}::{symbol}::{dt.strftime('%Y%m%d_%H%M%S')}"`

### 4.3 Resolve Stale Open Picks (P0)
**Files:** `multi_asset/data/institutional_picks.json`  
**Action:** Close or mark EXPIRED all picks dated 2026-04-03. Mark all 2026-11-12 picks as `forward_test_only=true` explicitly.

### 4.4 Decouple ml_score from confidence (P1)
**File:** `alpha_engine/equity_strategies.py` and all strategy modules  
**Action:** Compute `ml_score` independently from `confidence`. Do not copy confidence → ml_score.

---

## 7. GO/NO-GO DECISION

**CURRENT STATUS: NO-GO for live capital deployment.**

| Criterion | Threshold | Current Status | Verdict |
|-----------|-----------|----------------|---------|
| PnL ≥ 1.5 forward | 1.5 | 0.71–76.92 (n=6–12) | ❌ FAIL |
| WR ≥ 55% forward | 55% | 25%–83% (n < 12) | ❌ FAIL |
| Sharpe ≥ 0.5 forward | 0.5 | -0.48 to 1.14 | ❌ FAIL |
| DSR ≥ 0.95 forward | 0.95 | Not computed | ❌ FAIL |
| n ≥ 100 forward picks | 100 | Max n=12 | ❌ FAIL |
| 3+ months clean forward | 3 months | 0 days | ❌ FAIL |

**RECOMMENDATION:** Do not deploy capital to any strategy. All picks are paper-test-only. The highest-probability path to profitability is low-cost ETF/mutual fund passive allocation (beta capture), not active ML prediction.
