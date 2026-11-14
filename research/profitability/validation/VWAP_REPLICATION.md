# Independent Replication — "Regime-Filtered VWAP Mean Reversion (4h)" Profitability Claim

**Replication agent:** VWAP-R1 (independent)
**Date:** 2026-11-14
**Claim under test:** `updates/2026-11-14-PROFITABLE-APPROACH-VWAP-MEAN-REVERSION.md`
**Verdict:** **FAIL** — the arithmetic reproduces exactly, but the statistical and execution claims do not survive auditing. The approach is not "provably profitable"; the reported significance is an artifact of four measurement errors plus an optimistic fill/stop model.

> Reproduction = **PASS** (numbers match to the digit).
> Validity = **FAIL** (Sharpe inflated 3.19×, PBO is degenerate, DSR actually NaN, t-stat 0.91, 61% of stops ignored, OOS is 7 months not 22, portfolio model not implementable).

No repo source was modified. All replication scripts live in `/tmp/kilo/replication/`.

---

## 1. Verdict Summary

| # | Item | Result |
|---|---|---|
| 1 | Exact reproduction of claimed metrics | **PASS** (PF 1.2104, WR 44.19%, Ret 12.70%, MDD 9.99%, n=129) |
| 2 | Sharpe 3.76 | **FAIL** — correct value **1.179** (annualized over 215.6 trades/yr, not 2190) |
| 3 | PBO 0.489 | **FAIL** — the metric returns ~0.5 on *any* data, including pure noise (0.4935) |
| 4 | DSR P(Sharpe>0)=1.0000 | **FAIL** — the real DSR module returns **NaN / pass=False**; the printed 1.0 is a mislabeled homegrown statistic |
| 5 | Statistical significance | **FAIL** — pooled t-stat on the mean trade = **0.912** (p≈0.18, one-sided) |
| 6 | Stop-loss realism | **FAIL** — 79/129 trades (61%) breached the stop intrabar; with intrabar stops PF = **0.810**, Ret −17.4% |
| 7 | OOS length "~22 months" | **FAIL** — true OOS is **218.5 days = 7.18 months** (2026-04-10 → 2026-11-14) |
| 8 | Multi-symbol aggregation | **FAIL** — concurrent 40%/symbol = **−15.78%** return, MDD 25.4%, peak 280% gross exposure |
| 9 | "All 5 symbols profitable" / 129 trades | **FAIL** — 8 symbols were tested; DOGE/AVAX/LINK are losers; 129 is the **8-symbol** count, the 5-symbol count is **72** |
| 10 | Cost robustness | **FAIL** — PF falls below 1.0 at **25 bps round trip** (0.964), not the claimed 50 bps |

---

## 2. What the Harness Actually Does

Source read in full: `/tmp/kilo/regime_filtered_vwap_v12.py`, `/tmp/kilo/regime_filtered_vwap_v11.py`, `/tmp/kilo/vwap_4h_v7.py`, `verified_strategies/strategies/vwap_reversion.py`, `alpha_engine/regime_detector.py`, `alpha_engine/validation/statistical_gates.py`.

### 2.1 Data source and period
- `yfinance.download(symbol, period="730d", interval="4h", auto_adjust=False)`, symbols `BTC-USD, ETH-USD, SOL-USD, XRP-USD, ADA-USD, DOGE-USD, AVAX-USD, LINK-USD`.
- Fetched 2026-11-14: **4,373 bars per symbol**, `2024-11-15 00:00 UTC` → `2026-11-14 16:00 UTC` (= 730 days = 24.0 months total).
- Volume is present but yfinance 4h volume is exchange-aggregated and not validated here.

### 2.2 Train/test split and exact OOS range
- `te = int(n * 0.7) = int(4373*0.7) = 3061`.
- Train: bars `0..3060` → `2024-11-15 00:00` → `2026-04-10 00:00`.
- **OOS: bars `3061..4372`, 1,312 bars, `2026-04-10 04:00 UTC` → `2026-11-14 16:00 UTC` = 218.5 days = 7.18 months.**
- Effective tradable OOS is smaller still: VWAP warmup is up to 100 bars (16.7 days) and the regime warmup is 60 bars, both starting fresh at the test boundary.

### 2.3 Per-symbol parameters
Hardcoded in `BEST_PARAMS` (v12 lines 31–40), not re-optimized in v12. They originate from the `vwap_4h_v7.py` train-only grid search (4×5×4×4×3 = 960 combos/symbol, ranked by `sharpe*log(pf)`). Cross-checked against `/tmp/kilo/vwap_4h_v7.json`: BTC/ETH/SOL/XRP/ADA params match exactly.

**AVAX-USD and LINK-USD params (50/1.0/0.07/0.02/30) do not appear in the v7 grid output** (v7 tested only BTC/ETH/SOL/XRP/BNB/ADA/DOGE). Their provenance is **UNVERIFIED**; the doc's parameter table omits them entirely.

### 2.4 Regime source
- `detect_regime(close.iloc[:i+1])` — **per-symbol**, not BTC. The doc does not say this; it implies a market-wide regime.
- 60-bar lookback, computed inside the *test slice only*, using data through bar `i` inclusive.
- `MR_COMPATIBLE = {MEAN_REVERTING, CHOPPY_TIGHT, CHOPPY_WIDE, HIGH_VOLATILITY, CRISIS}`, plus an explicit **`UNKNOWN` bypass** (v12 line 73: `regime in MR_COMPATIBLE or regime == "UNKNOWN"`).
- **Unit bug:** `regime_detector.py` uses "7d/20d/30d" windows (7/20/30 *bars*). Fed 4h bars, "7d" is actually **28 hours**. In the whole OOS window only `MEAN_REVERTING` (126), `NEUTRAL` (113), `TRENDING_UP` (158), `TRENDING_DOWN` (191), `CRISIS` (1), `UNKNOWN` (2) ever occur — `CHOPPY_TIGHT`, `CHOPPY_WIDE`, `HIGH_VOLATILITY` **never fire**. The filter is effectively "20-bar ADX-proxy < 20 on 4h bars".
- **Doc/code mismatch:** the doc says "skip trades in TRENDING_UP/TRENDING_DOWN". The code is an allowlist that also drops all **113 NEUTRAL** trades.

### 2.5 Execution timing
- Signal and fill are on the **same bar's close**: `VWAPReversionStrategy.run` computes the band from `typical_price[i]` and `volume[i]` (bar `i` is complete) and fills at `close.iloc[i]`.
- This is not future data, but it requires computing the regime, VWAP band, and order at the exact closing print and filling at that same print. Quantified in §5.

### 2.6 Position sizing and multi-symbol aggregation
- `POSITION_SIZE = 0.4` applied uniformly to every trade.
- Each symbol is backtested **in isolation** on 10,000 capital; then all per-symbol PnL lists are **concatenated** (`all_pnls.extend(pnls)`) and compounded as one sequential chain: `cum *= (1+p)` over 129 trades. This silently assumes **one position at a time across the entire book**. See §6.

### 2.7 Cost model
- `COST_BPS = 10` per side; charged as `(2*10/10000)*0.4 = 8 bps of capital per trade`.
- No spread, no funding, no slippage on stop fills, no market impact.

---

## 3. Reproduction (Task 2) — PASS

Command (network equivalent of the claim; data cached to parquet):

```bash
cd /tmp/kilo/replication
python3 fetch_cache.py     # yfinance 1.3.0, 4h, 730d -> data/*.parquet
python3 replicate.py       # faithful re-run of v12 imports/params/filter/metrics
```

| Metric | Claim | Replication | Match |
|---|---|---|---|
| Trades | 129 | **129** | exact |
| Win rate | 44.2% | **44.186%** | exact |
| Profit factor | 1.210 | **1.2104** | exact |
| Sharpe | 3.76 | **3.7583** (same convention) | exact |
| Total return | 12.7% | **12.699%** | exact |
| Max drawdown | 10.0% | **9.994%** | exact |
| PBO | 0.489 | **0.489** (same formula) | exact |

Per-symbol (all 8 tested symbols, v12 convention):

| Symbol | Trades kept / raw | PF | WR | Return | MDD | Status in doc |
|---|---|---|---|---|---|---|
| BTC-USD | 11 / 48 | 1.670 | 54.5% | +2.91% | 2.62% | reported |
| ETH-USD | 21 / 93 | 1.564 | 57.1% | +3.50% | 2.70% | reported |
| SOL-USD | 26 / 101 | 1.266 | 57.7% | +2.48% | 3.52% | reported |
| XRP-USD | 7 / 47 | 1.388 | 28.6% | +1.56% | 2.62% | reported |
| ADA-USD | 7 / 57 | **2.987** | 42.9% | **+7.03%** | 2.62% | reported (as 2.23 / +4.2%) |
| DOGE-USD | 5 / 52 | **0.618** | 20.0% | **−1.37%** | 2.62% | **omitted** |
| AVAX-USD | 33 / 100 | **0.875** | 36.4% | **−2.51%** | 6.83% | **omitted** |
| LINK-USD | 19 / 93 | **0.906** | 31.6% | **−1.22%** | 5.96% | **omitted** |

**Test B (v11, 4 symbols) also reproduces:** n=65, PF **1.435** (claim 1.435), Sharpe 7.10 (claim 7.10), MDD 3.52% (claim 3.5%). So the claim's arithmetic is genuine, not fabricated.

> No Binance reimplementation was needed — yfinance returned all 4,373 bars without 429s. A Binance 4h fallback (`/tmp/kilo/*USDT.json`) was inspected but holds only 1,000 bars each and was not used.

---

## 4. Statistical Validity (Task 7 / headline claims) — FAIL

### 4.1 Sharpe is inflated 3.19× by a wrong annualization factor
`vwap_reversion` metrics compute `avg/std * sqrt(8760/4)` = `sqrt(2190)` = **46.80**, i.e. it assumes **2,190 independent trades/yr** (one per 4h bar, continuously). Actual trade rate over the 218.5-day OOS = **215.6 trades/yr**.

| Quantity | Value |
|---|---|
| Per-trade Sharpe (8-sym pooled) | 0.0803 |
| v12 annualizer | sqrt(2190) = 46.80 |
| **Reported Sharpe** | **3.758** |
| Correct annualizer | sqrt(215.6) = 14.68 |
| **Correct Sharpe (8-sym)** | **1.179** |
| Correct Sharpe (cherry-picked 5-sym) | 2.85 |

### 4.2 PBO 0.489 is degenerate — it measures nothing
The "PBO" is a bootstrap where the resample's Sharpe is compared to the observed Sharpe. Because the bootstrap is centered on the observed sample, the answer is ~0.5 by construction:

| Input | "PBO" |
|---|---|
| Real 129-trade pool | **0.489** |
| `N(0, 0.01)** pure noise, n=129 | **0.4935** |
| `N(0.01, 0.01)` strong synthetic edge, n=129 | **0.503** |

Identical for signal-free and strongly-profitable data. It is not the CSCV probability of backtest overfitting and carries zero information. "PBO 0.489 < 0.5 PASS" is vacuous.

### 4.3 DSR P(Sharpe>0)=1.0000 is not the DSR
- `deflated_sharpe_ratio(pool, 1, annualization_factor=2190)` from `alpha_engine.validation.statistical_gates` returns **`dsr_probability: NaN`, `pass: False`**, because at SR=3.758 with sample skew +1.062 the variance term `1 − skew·SR + (kurt/4)·SR² = −0.018 < 0`.
- The harness discards that result and prints a homegrown `p_pass` (v12 lines 183–185) that divides the **annualized** Sharpe by a **per-observation** standard error (`sqrt((1+0.5·SR²)/(n−1))`), yielding z≈15 and p≈1.0.
- Correct per-observation test: SR=0.0803, SE≈1/√129=0.0881, **z = 0.912 → P(Sharpe>0) ≈ 0.82**.
- Also note `num_trials=1`: no deflation is applied despite 960 param combos × 8 symbols of search.

### 4.4 The pooled mean trade return is not significant
- Pooled mean = 0.001004, std = 0.012501, n = 129 → **t = 0.912** (p ≈ 0.18 one-sided).
- For the cherry-picked 5 symbols: t = **1.647** (p ≈ 0.05), still not significant after any multiple-testing correction.

### 4.5 The "IS 0.28 → OOS 3.10" argument is inverted
The doc calls a 17× IS→OOS Sharpe improvement "the signature of a real edge." `verified_strategies/WALKFORWARD_REPORT.json` shows `vwap_reversion` IS Sharpe 0.277 (PF 1.017, n=1203) → OOS 3.102 (n=516), `decay_ratio 17.397`. A flat in-sample edge that suddenly becomes Sharpe 3.1 out-of-sample is the textbook signature of a **favorable OOS regime sample**, not confirmation. (Also: that raw OOS PF is 1.323 — *higher* than the regime-filtered 1.210 headline, contradicting the doc's "raw VWAP fails OOS" narrative.)

---

## 5. Lookahead / Execution Audit (Task 3)

### 5.1 Same-bar execution, close-only stops
- Entry signal: bar `i` close vs band built from bar `i` typical price/volume → fill at bar `i` close. Same-bar, same-instant. Borderline but not future data.
- **Stops are evaluated against the close only, not the intrabar low/high** (`vwap_reversion.py:82-98`). A stop breached on a wick and recovered is silently ignored. This is the largest bias in the study.

**79 of 129 kept trades (61.2%) breached their stop intrabar** and were not stopped out (BTC 5/11, ETH 12/21, SOL 11/26, XRP 4/7, ADA 5/7, DOGE 5/5, AVAX 23/33, LINK 14/19).

Re-run with intrabar, gap-aware stops (`/tmp/kilo/replication/realism.py`, variant B):

| Model | n | PF | Return | MDD |
|---|---|---|---|---|
| Harness (close-only stops) | 129 | 1.210 | +12.70% | 9.99% |
| **Intrabar stops (low/high, gap-aware)** | 161 | **0.810** | **−17.38%** | 24.65% |

The entire edge is produced by not honoring stops.

### 5.2 Regime timing sensitivity
37 of 129 trades flip from "MR-compatible" to "not" if the regime is computed with a **1-bar lag** (i.e. using information actually available at the prior close). With lagged regime: n=163, **PF 1.054, t = 0.29** — the edge disappears. A 4-hour lag is far larger than realistic latency, so this is a *fragility* signal rather than proof of lookahead; the regime does not use future bars.

### 5.3 Manual trace of 3 trades

**BTC-USD (SHORT, kept, clean):**
- Entry bar `2026-05-13 04:00`; close 80,996.01 > upper band 80,751.89 → signal holds.
- VWAP window = bars 99..198 of the test slice, **includes the entry bar**.
- Regime with/without bar `i`: `MEAN_REVERTING` / `MEAN_REVERTING`.
- Exit 2 bars later at `vwap_target` 78,783.04 → raw +2.732%, scaled +1.013%. Intrabar stop not hit.
- **Verdict: valid trade, no lookahead.**

**ETH-USD (LONG, kept via UNKNOWN bypass):**
- Entry `2026-04-19 20:00`; close 2,263.25 < lower band 2,308.33 → signal holds.
- Regime = `UNKNOWN` (fewer than 60 test bars) → admitted by the `or regime == "UNKNOWN"` bypass, **not** by an actual regime call.
- Exit 13 bars at `vwap_target` 2,364.16 → +4.459% raw, +1.703% scaled.
- **Verdict: the "regime filter" passes trades it never actually classified.**

**ADA-USD (LONG, both biases in one trade):**
- Entry `2026-06-05 00:00`; close 0.15830 < lower band 0.20548 → signal holds.
- Regime **including** entry bar = `CRISIS` (kept). Regime **excluding** entry bar = `TRENDING_DOWN` → would be **filtered out**.
- Held 40 bars; **min low during hold 0.14860 < stop 0.15513 → stop was breached intrabar but never honored**; exits `max_hold` at 0.1692 → raw +6.885%, scaled +2.674%.
- **Verdict: retained only because the entry bar's own close flipped the regime, and profitable only because the stop was ignored.**

---

## 6. OOS Length (Task 4)

`PERIOD=730d`, `TRAIN_FRAC=0.7` → OOS = 30% of 24 months.

| Claim | Measured |
|---|---|
| "~2025-01 to 2026-11 (~22 months)" | **2026-04-10 04:00 → 2026-11-14 16:00 = 218.5 days = 7.18 months** |

**The doc's 22-month figure is false.** It appears to conflate total data history (730d ≈ 24 months) with the OOS window. Train is 2024-11-15 → 2026-04-10.

---

## 7. Multi-Symbol Aggregation (Task 5)

The harness **serializes** all 129 trades into one chain: `cum *= (1+p)` with 40% sizing applied per trade, assuming you can hold only one position at a time across all 8 symbols on a single capital base.

Rebuilt as a true concurrent book (shared capital, 40% per open symbol, bar-level mark-to-market, 10 bps/side on turnover):

| Sizing | Return | MDD | Peak gross exposure | Avg exposure | Trades |
|---|---|---|---|---|---|
| Sequential chain (harness) | **+12.70%** | 9.99% | n/a (serialized) | 40% | 129 |
| Concurrent 8 sym @ 40% | **−15.78%** | 25.37% | **280%** | 41.6% | 129 |
| Concurrent 5 sym @ 40% | +4.90% | 12.80% | 160% | 24.2% | 72 |
| Concurrent 8 sym @ 12.5% (≤100% gross) | −4.80% | 8.53% | 88% | 13.0% | 129 |
| Concurrent 5 sym @ 20% (≤100% gross) | +2.62% | 6.57% | 80% | 12.1% | 72 |

40% × 8 symbols = up to **320%** gross; peak observed 280%. At the claimed 40%/symbol the realistic portfolio is **negative with a 25% drawdown**. Even capping gross exposure at 100%, the 8-symbol book is −4.8%. There is no sizing at which the claimed +12.7%/10% MDD is achievable with a concurrent multi-symbol implementation.

---

## 8. Symbol Selection / "All 5 Symbols Profitable" (Task 6)

- `SYMBOLS` in v12 is `[BTC, ETH, SOL, XRP, ADA, DOGE, AVAX, LINK]` — **8 symbols were tested**. All 8 appear in the saved `regime_filtered_vwap_v12_results.json`, and all 8 contribute to the **129-trade pooled total**.
- DOGE (PF 0.618), AVAX (PF 0.875), LINK (PF 0.906) are **all losing**. They were dropped from the doc's per-symbol table after results were seen.
- **The headline is mislabeled:** "Test A: 5 Symbols, 4h, 129 trades" is internally impossible. The 8-symbol pooled count is **129**; the 5-symbol count is **72** (PF 1.629, Sharpe 9.08 under the inflated convention, t = 1.647). The doc presents the 8-symbol pooled metrics under a "5 symbols" heading.
- The doc admits in caveat #2 that DOGE/AVAX/LINK fail — so the exclusion is disclosed, but the headline table and trade count are wrong, and no multiple-testing correction is applied for the 8-symbol × 960-param search.
- **Numeric inconsistency:** the doc's ADA row (PF 2.23, Sharpe 13.59, +4.2%) does **not** match the run (PF 2.987, Sharpe 19.64, +7.03%). The other 4 per-symbol rows match exactly, suggesting the ADA line was copied from an older run.

Whether the regime filter itself was chosen before looking at OOS results: **UNVERIFIED** (no pre-registration artifact in the repo).

---

## 9. Cost Robustness

| Round-trip cost | PF | Return | MDD |
|---|---|---|---|
| **20 bps (claim)** | 1.210 | +12.70% | 9.99% |
| 25 bps | **0.964** | −3.46% | 15.86% |
| 50 bps | 0.667 | −25.44% | 28.35% |

The doc says PF "would drop below 1.0" at 50 bps. In fact it is already below 1.0 at **25 bps** — a 5 bps round-trip increase wipes the edge out. Fee assumptions dominate the result.

The doc's "Without position sizing: MDD=45.8%" is **UNVERIFIED/CONTRADICTED**: at 100% sizing and 20 bps the same trades give return +30.0%, MDD 24.2%.

---

## 10. Commands Used

```bash
mkdir -p /tmp/kilo/replication && cd /tmp/kilo/replication
# 1. Data (yfinance 1.3.0, 4h, 730d -> parquet cache)
python3 fetch_cache.py
# 2. Faithful v12 reproduction (imports repo modules read-only)
python3 replicate.py
# 3. Sharpe / DSR / PBO degeneracy / regime distribution / OOS length
python3 analyze.py
# 4. Execution realism: intrabar stops, next-bar fill, 1-bar regime lag
python3 realism.py
# 5. Concurrent multi-symbol portfolio aggregation
python3 portfolio2.py
# 6. Manual 3-trade trace + v11 4-symbol cross-check
python3 trace.py
# 7. Ignored-intrabar-stop and regime-flip counts
python3 stats2.py
```

Artifacts: `/tmp/kilo/replication/{results,per_symbol,analysis,realism,portfolio2,trace,stats2,cost}.json`.

---

## 11. UNVERIFIED / Not Reproduced

- **UNVERIFIED** — selection order: whether the regime filter and the 5-symbol subset were fixed *before* OOS inspection (no pre-registration evidence).
- **UNVERIFIED** — provenance of AVAX/LINK parameters (not in the v7 grid output).
- **UNVERIFIED** — the doc's "raw VWAP 4h PF=1.067" executive-summary number; my raw no-filter 8-symbol PF is 1.053 and 5-symbol is 1.035 (same ballpark, different exact run).
- **UNVERIFIED** — the doc's ADA per-symbol row; it does not match the saved results JSON.
- **CONTRADICTED** — "Without position sizing MDD=45.8%"; measured 24.2%.
- **NOT TESTED** — funding costs, borrow, exchange outage/gap risk, and live slippage on the (ignored) stops.

---

## 12. Bottom Line

The harness genuinely produces PF 1.210 / n=129 / +12.7% / MDD 10.0% on the stated data — the claim is not fabricated. But every inferential claim attached to that number is wrong:

1. Sharpe 3.76 is **1.18** once trades/year is annualized correctly.
2. PBO 0.489 is a metric that returns ~0.5 for noise; it certifies nothing.
3. DSR actually returns **NaN**; the reported 1.0 is a different, mislabeled statistic.
4. The pooled mean return is **insignificant** (t = 0.91).
5. **61% of trades blew through their stop** intrabar; honoring stops turns PF 1.21 → 0.81.
6. OOS is **7.2 months**, not 22.
7. The multi-symbol book at the claimed 40%/symbol returns **−15.8%** with a 25% drawdown.
8. Three losing symbols were tested and dropped from presentation; the "129 trades / 5 symbols" label is internally inconsistent.

**Verdict: FAIL.** This is a thin, cost-fragile, stop-ignoring, serially-aggregated backtest of ~129 trades over 7 months, not a proven profitable edge.

> **NOT MONEY-READY. No picks, signals, or verdicts are produced by this document.**
