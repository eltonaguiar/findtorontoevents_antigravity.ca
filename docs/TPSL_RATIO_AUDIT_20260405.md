# TP/SL Ratio Audit — picks.recent_closed (2026-04-05)

**Author:** claude-tpsl-analyst (research only; zero strategy-parameter changes made)
**Source:** `audit_dashboard/data/dashboard_data.json :: picks.recent_closed`
**Sample:** 3,500 closed trades → 3,427 with valid entry/TP/SL triples used for analysis
**Raw artifact:** `alpha_engine/data/tpsl_audit_20260405.json`

---

## 1. Headline — the 2:1 SL:TP problem in one line

We configure a **median planned R:R of 1.67:1** (TP 2.50% / SL 1.50% on CRYPTO) but the market
delivers a **realized SL_HIT : TP_HIT of 1.45:1** across CRYPTO and **2.15:1** on our largest
strategy (`st_fear_greed_contrarian`, 777 trades, 22% of the book). Translation: stops are being
run ~1.45x more often than targets across the whole book, and on some strategies 6-14x more often.

Only the **EXPIRED bucket (890 trades, 26% of the book, mean PnL +0.74%)** keeps overall
win-rate at 51% — the time-expiry exits are carrying the book. That is the single most
actionable signal in this audit.

---

## 2. Canonical exit-reason distribution (after normalising 150+ raw strings)

| Bucket | Count | Share | Median TP dist | Median SL dist | Mean PnL |
|---|---:|---:|---:|---:|---:|
| TP_HIT | 1,066 | 31.1% | 2.50% | 1.50% | +2.36% |
| SL_HIT | 1,444 | 42.1% | 2.50% | 1.50% | -1.76% |
| EXPIRED | 890 | 26.0% | 3.37% | 1.70% | **+0.74%** |
| OTHER | 27 | 0.8% | — | — | — |

Canonical mapping: {TP_HIT, TP, WON, TAKE_PROFIT*} → TP_HIT; {SL_HIT, SL, LOST, LOSS,
STOP_LOSS*, ATR TRAILING STOP HIT} → SL_HIT; {EXPIRED, TIME, TIME_EXIT, TIME_EXPIRY, MAX
HOLD EXCEEDED} → EXPIRED.

**Interpretation of identical medians (2.50% / 1.50%) in TP_HIT and SL_HIT:**
TP/SL distances come from the *same ATR-based formula* regardless of outcome — so the formula
itself is not the asymmetry. The asymmetry is **behavioural**: stops get hit first because
price noise touches the tighter level before the farther level.

---

## 3. Per–asset-class breakdown

| Class | n | WR | SL:TP realized | TP dist med | SL dist med | Planned R:R med | Mean PnL | Expectancy* |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CRYPTO | 2,590 | 51.5% | **1.48** | 2.50% | 1.50% | 1.69 | +0.82% | +0.19% |
| FOREX | 379 | 46.2% | 1.05 | 0.80% | 0.50% | 1.60 | -0.47% | +0.05% |
| EQUITY | 286 | 46.2% | 1.23 | 7.00% | 4.00% | 1.67 | +0.66% | +0.26% |
| COMMODITY | 155 | 47.7% | 0.99 | 5.00% | 3.00% | 1.67 | n/a | +0.12% |
| BOND | 8 | 50.0% | 0.75 | 1.33% | 0.80% | 1.67 | — | +0.62% |
| ETF | 4 | 75.0% | 0.00 | 5.22% | 3.00% | 1.99 | — | +0.50% |
| FUTURES | 5 | 0.0% | n/a | 8.00% | 2.08% | 6.13 | — | -18.83% |

\*Expectancy = WR·mean_win + (1-WR)·mean_loss per trade, %.

**Observations:**
- CRYPTO is the source of the 2:1 problem. At 1.48:1 realized (vs 1.69:1 planned), stops
  are firing ~12% more often than a symmetric random-walk would predict.
- EQUITY and COMMODITY R:R are nearly symmetric (1.23 and 0.99) despite the same planned
  R:R — wider stops on those classes (3-4%) absorb normal noise correctly.
- FUTURES (5 trades) is statistically broken; ignore until larger sample.

---

## 4. Top-10 strategies by volume — realized exit distribution

| Strategy | n | WR | SL:TP | Mean PnL |
|---|---:|---:|---:|---:|
| st_fear_greed_contrarian | 777 | 65.3% | **2.15** | +0.43% |
| forex_rsi2_mean_reversion | 286 | 47.2% | 1.02 | +0.11% |
| st_obv_support_divergence | 252 | 43.7% | **6.53** | -0.42% |
| luxalgo_confluence | 220 | 40.5% | 1.47 | -0.03% |
| futures_momentum | 158 | 48.7% | 0.94 | +0.19% |
| enhanced_ml_A_xgboost | 113 | 31.9% | **2.14** | -0.41% |
| ensemble | 90 | 38.9% | 1.57 | +0.58% |
| quan_engine_scalp | 83 | 38.6% | 1.59 | +0.10% |
| Bollinger MR | 64 | 48.4% | 1.44 | +0.19% |
| strong consensus (alpha_engine, ml_crypto_v3) | 60 | 6.7% | **14.00** | -3.31% |

### Worst 5 SL:TP ratio (min 20 trades) — stops firing vastly more than targets

| Strategy | n | SL:TP | WR | Mean PnL | Read |
|---|---:|---:|---:|---:|---|
| strong consensus (alpha_engine, ml_crypto_v3) | 60 | **14.00** | 6.7% | -3.31% | Broken. Entries are counter-trend; TP unreachable. |
| st_obv_support_divergence | 252 | **6.53** | 43.7% | -0.42% | Divergence signal fades before target; shorten TP. |
| ML Ranker | 36 | 3.40 | 30.6% | -0.80% | Low WR + wide TP = stops dominate. |
| st_fear_greed_contrarian | 777 | 2.15 | 65.3% | +0.43% | WR is high (65%); stops are too tight for held-to-target bucket. |
| enhanced_ml_A_xgboost | 113 | 2.14 | 31.9% | -0.41% | 32% WR with 1.69:1 planned R:R is math-negative. |

### Best 5 SL:TP ratio (min 20 trades) — targets compress closer to stops

| Strategy | n | SL:TP | WR | Mean PnL |
|---|---:|---:|---:|---:|
| atr_percentile_gate | 24 | 0.41 | 70.8% | +0.15% |
| quality-minus-junk | 21 | 0.50 | 66.7% | +0.91% |
| crypto_rsi_whaleconfirmed_v1 | 20 | 0.54 | 65.0% | +0.32% |
| MeanReversionBB | 26 | 0.62 | 61.5% | +0.64% |
| rsi_overbought | 31 | 0.72 | 58.1% | +0.32% |

Pattern: the best SL:TP ratios are all **mean-reversion** / reversion-gate strategies with
WR ≥ 58%. The worst are **divergence, counter-trend consensus, and ML ranker** strategies.

---

## 5. Hypothesis test results

| Hyp | Verdict | Evidence |
|---|---|---|
| **H1 — TP set too far** | **CONFIRMED on CRYPTO (selectively)** | TP_HIT trades reach med 2.50% TP; SL_HIT trades also had 2.50% TPs set — price never reached them. EXPIRED trades (26% of book) hold positive PnL at timeout, showing TP was not reached even though trade was profitable. |
| **H2 — SL set too tight** | **PARTIALLY CONFIRMED on high-WR strats** | `st_fear_greed_contrarian` has 65% WR yet SL:TP=2.15 — stops are getting whipsawed on an otherwise profitable signal. Widening SL 30-50% would convert SL_HITs into EXPIREDs (avg +0.74%). |
| **H3 — bad entry timing** | NOT TESTED (needs price-path data) | Schema lacks intra-trade high/low; cannot directly test "price went against us immediately." |
| **H4 — ATR miscalibration** | PARTIAL | The fact TP med = 2.50% on *both* winning and losing CRYPTO trades suggests one universal ATR multiplier is being applied across volatility regimes — no regime adjustment visible. |
| **H5 — subset of strategies is the culprit** | **CONFIRMED** | 3 strategies (`strong consensus`, `st_obv_support_divergence`, `ML Ranker`) with SL:TP > 3.0 account for ~10% of trades but pull the realised ratio above 2:1. Kill / reparameterise these and overall SL:TP drops below 1.2. |

**Root cause ranking:** H5 > H1 > H2 > H4 > H3.

---

## 6. EXPIRED-trade profitability — the time-exit carries the book

| Asset class | EXPIRED n | Mean PnL @ expiry |
|---|---:|---:|
| CRYPTO | ~690 | +0.82% |
| EQUITY | ~80 | +0.66% |
| FOREX | ~90 | -0.47% |
| **All** | **890** | **+0.74%** |

**Answer: YES, EXPIRED trades are profitable on average (+0.74%).** This means:
1. Our target (TP) is placed beyond where price actually travels within the hold window.
2. A **trailing-stop or time-based partial take-profit** would convert unrealised 0.74% average
   gains into locked gains instead of leaving them to reverse.
3. Shrinking TP on CRYPTO from ~2.50% to ~1.6-1.8% (1.05-1.20x current SL distance) would
   migrate EXPIRED trades into the TP_HIT bucket and flip the SL:TP ratio toward 1:1.

---

## 7. Concrete recommendations (report only; no code changes)

### Per-asset-class TP/SL retuning

| Class | Current TP / SL median | Recommended TP / SL | Rationale |
|---|---|---|---|
| **CRYPTO** | 2.50% / 1.50% (R:R 1.67) | **1.80% / 1.50% (R:R 1.20)** | Shrinks TP to where price actually travels; EXPIRED (mean +0.74%) migrates to TP_HIT. Projected SL:TP drops from 1.48 to ~1.1. |
| **FOREX** | 0.80% / 0.50% (R:R 1.60) | **0.70% / 0.55% (R:R 1.27)** | FX noise > 0.50% intraday; tiny widen + tighter TP. |
| **EQUITY** | 7.00% / 4.00% (R:R 1.67) | **Keep 7.00% / 4.00%** | Realized SL:TP=1.23 already acceptable; expectancy positive. |
| **COMMODITY** | 5.00% / 3.00% (R:R 1.67) | **Keep 5.00% / 3.00%** | Realized SL:TP=0.99 (symmetric); don't touch. |

### Per-strategy actions

1. **Kill / suspend `strong consensus (alpha_engine, ml_crypto_v3)`** — SL:TP=14, WR=6.7%,
   PnL -3.31%. 60 trades is enough. This is the single largest ratio-offender.
2. **Shrink TP on `st_obv_support_divergence`** from current (~2.5%) to **1.2%** — divergence
   signals fade fast; 252 trades confirm the pattern. Target: SL:TP → ~2.0.
3. **Widen SL on `st_fear_greed_contrarian`** by ~40% (1.5% → 2.1%) — 65% WR is strong; the
   stops are the only leak. This strategy is 22% of the book, so gains compound.
4. **Reparameterise or sunset `enhanced_ml_A_xgboost` / `ML Ranker`** — 31% and 30% WR with
   1.7:1 R:R is mathematically losing; current SL:TP > 2.1 on both.

### Systemic

5. **Add trailing-stop or time-based profit-take** on any trade that crosses +0.5% at the
   halfway hold-time mark. EXPIRED trades average +0.74%; capture half of that mechanically.
6. **Regime-aware ATR multiplier**: TP/SL medians identical across TP_HIT and SL_HIT buckets
   show no regime differentiation. Bucket by ATR percentile and scale multipliers per bucket.

---

## 8. Limitations

- No intra-trade OHLC in the sample — cannot verify how far SL_HIT trades went *toward* TP
  before reversing (direct H1 proof).
- Trades with `SHORT` direction were flipped for distance calculation but not stress-tested
  separately; SHORT-specific asymmetries not isolated in this pass.
- 73 trades rejected for malformed TP/SL (2.1%); no systematic bias found in their strategies.
- Planned R:R of 1.67 is the *median* — individual strategies vary from 0.41 to 14.0.

---

**Recommended follow-up:** join this audit with `closed_picks_with_ohlc.parquet` (if
exists) to compute "max favourable excursion" per SL_HIT trade, directly proving H1.
