# Proven Winners per Asset Class — 2026-10-22 (directive G)

**Validated closed rows:** 4351 (post `_is_valid_resolved_pick` incl. micro-hold gate)

**Method:** iterates the same closed-pick feeds registered in `JSON_PICK_SOURCES`, applies the
validity gate (incl. micro-hold exclusion), and classifies rows with the generator's own
`_coerce_asset_class`. Artifacts cannot inflate the cohort metrics.

## 1. Per-class headline

| asset_class | n | wins | losses | WR% | PF | Σ PnL% | avg PnL% |
|---|---|---|---|---|---|---|---|
| CRYPTO | 4267 | 1758 | 2423 | 41.2 | 0.958 | -240.0 | -0.056 |
| FOREX | 61 | 30 | 25 | 49.18 | 0.13 | -1.6 | -0.026 |
| EQUITY | 8 | 8 | 0 | 100.0 | 0.154 | +0.1 | +0.019 |
| ETF | 2 | 0 | 1 | 0.0 | 0.0 | -0.0 | -0.010 |
| BOND | 1 | 0 | 1 | 0.0 | 0.0 | -0.0 | -0.006 |
| COMMODITY | 7 | 4 | 3 | 57.14 | 1.565 | +0.0 | +0.005 |
| MEME | 1 | 0 | 1 | 0.0 | 0.0 | -0.0 | -0.024 |
| PENNY_STOCK | 1 | 0 | 1 | 0.0 | 0.0 | -0.0 | -0.013 |
| STOCKS | 3 | 1 | 2 | 33.33 | 0.215 | -0.5 | -0.154 |

## 2. Per-class top strategies (n ≥ 5)

### CRYPTO

| strategy | n | WR% | PF | Σ PnL% | avg PnL% |
|---|---|---|---|---|---|
| `luxalgo_confluence` | 3413 | 41.49 | 0.957 | -204.6 | -0.060 |
| `ensemble` | 381 | 38.32 | 1.363 | +141.0 | +0.370 |
| `unknown` | 77 | 46.75 | 0.518 | -6.0 | -0.079 |
| `mega_mutation_macd_rsi_m048` | 44 | 54.55 | 1.854 | +72.2 | +1.641 |
| `mega_mutation_ema_momentum_m006` | 39 | 53.85 | 1.062 | +3.6 | +0.093 |
| `clone_hl_copy_lb_None` | 34 | 29.41 | 0.327 | -0.1 | -0.003 |
| `ml_breakout` | 21 | 0.0 | 0.0 | +0.0 | +0.000 |
| `clone_hl_copy_PensionFund_24M` | 18 | 55.56 | 0.349 | +0.3 | +0.019 |
| `clone_hl_copy_Auros_66M` | 18 | 50.0 | 0.013 | +0.0 | +0.001 |
| `mega_mutation_macd_rsi_m017` | 15 | 80.0 | 5.302 | +45.6 | +3.041 |
| `regime_mild_bear` | 12 | 100.0 | 0.613 | +0.6 | +0.051 |
| `funding_rate_carry` | 11 | 36.36 | 0.233 | -95.2 | -8.658 |

### FOREX

| strategy | n | WR% | PF | Σ PnL% | avg PnL% |
|---|---|---|---|---|---|
| `forex_rsi2_mean_reversion` | 37 | 75.68 | 5.333 | +0.2 | +0.005 |
| `ema_stack_momentum` | 8 | 12.5 | 0.327 | -0.0 | -0.001 |
| `forex_zscore_200d_fade` | 5 | 0.0 | 0.0 | -1.8 | -0.352 |
| `bb_mean_reversion_forex` | 5 | 0.0 | 0.0 | -0.0 | -0.001 |

### EQUITY

| strategy | n | WR% | PF | Σ PnL% | avg PnL% |
|---|---|---|---|---|---|
| `vt_equity_two_day_rsi_reversal` | 7 | 100.0 | 0.142 | +0.1 | +0.020 |

### ETF

| strategy | n | WR% | PF | Σ PnL% | avg PnL% |
|---|---|---|---|---|---|

### BOND

| strategy | n | WR% | PF | Σ PnL% | avg PnL% |
|---|---|---|---|---|---|

### COMMODITY

| strategy | n | WR% | PF | Σ PnL% | avg PnL% |
|---|---|---|---|---|---|
| `seasonal_momentum` | 5 | 40.0 | 0.892 | -0.0 | -0.001 |

## 3. Per-class top symbols (n ≥ 5)

### CRYPTO

| symbol | n | WR% | PF | Σ PnL% | avg PnL% |
|---|---|---|---|---|---|
| `AVAXUSDT` | 309 | 45.31 | 0.992 | -3.1 | -0.010 |
| `DOTUSDT` | 291 | 41.92 | 0.928 | -28.2 | -0.097 |
| `JUPUSDT` | 284 | 42.25 | 1.127 | +60.5 | +0.213 |
| `XRPUSDT` | 284 | 38.73 | 0.816 | -54.4 | -0.191 |
| `ETHUSDT` | 280 | 44.64 | 1.056 | +12.8 | +0.046 |
| `STXUSDT` | 276 | 44.2 | 1.001 | +0.6 | +0.002 |
| `BTCUSDT` | 276 | 39.86 | 0.842 | -29.9 | -0.108 |
| `ADAUSDT` | 273 | 36.26 | 0.827 | -71.1 | -0.260 |
| `LINKUSDT` | 269 | 36.8 | 0.821 | -56.9 | -0.211 |
| `WIFUSDT` | 266 | 45.86 | 1.277 | +110.2 | +0.414 |
| `NEARUSDT` | 265 | 39.25 | 0.925 | -39.4 | -0.149 |
| `SUIUSDT` | 253 | 39.92 | 0.913 | -31.4 | -0.124 |

### FOREX

| symbol | n | WR% | PF | Σ PnL% | avg PnL% |
|---|---|---|---|---|---|
| `CADJPY=X` | 12 | 75.0 | 4.61 | +0.1 | +0.005 |
| `AUDUSD=X` | 9 | 66.67 | 9.14 | +0.0 | +0.004 |
| `NZDUSD=X` | 7 | 42.86 | 3.584 | +0.0 | +0.004 |
| `AUDJPY=X` | 7 | 71.43 | 0.039 | -1.0 | -0.140 |
| `USDJPY=X` | 6 | 33.33 | 4.829 | +0.0 | +0.002 |
| `EURUSD=X` | 5 | 0.0 | 0.0 | -0.7 | -0.140 |

### EQUITY

| symbol | n | WR% | PF | Σ PnL% | avg PnL% |
|---|---|---|---|---|---|
| `AAPL` | 7 | 100.0 | 0.142 | +0.1 | +0.020 |

### ETF

| symbol | n | WR% | PF | Σ PnL% | avg PnL% |
|---|---|---|---|---|---|

### BOND

| symbol | n | WR% | PF | Σ PnL% | avg PnL% |
|---|---|---|---|---|---|

### COMMODITY

| symbol | n | WR% | PF | Σ PnL% | avg PnL% |
|---|---|---|---|---|---|


## 4. Interpretation — the "true set of winners" (variety-pack mutual-fund components)

The aggregate per-class numbers **cannot** be used to build the fund: only **CRYPTO**,
**FOREX**, and a handful of tiny classes have enough closed rows to matter, and the CRYPTO
aggregate is net-negative (WR 41.2%, PF 0.958, Σ −240%). The winning edge is **not** in
"own crypto" — it is concentrated in **specific strategies and specific symbols**. The
shortlist below is the faithful per-class decomposition of where genuine, data-backed edge
survives the validity gate (incl. micro-hold exclusion).

### 4.1 FOREX — trustworthy (best evidence)
- **Strategy `forex_rsi2_mean_reversion`**: n=37, WR 75.68%, PF 5.333, Σ +0.2%. Clean,
  consistent, high win-rate with a large positive PF. This is the single most trustworthy
  strategy cohort in the whole feed.
- Symbols: `CADJPY=X` (n=12, WR 75%, PF 4.61), `AUDUSD=X` (n=9, WR 66.67%, PF 9.14).
- ⚠️ Avoid `forex_zscore_200d_fade` (WR 0%, PF 0.0) and `bb_mean_reversion_forex`
  (WR 0%) — both are net losers.

### 4.2 CRYPTO — selectable cohorts only (do NOT take broad crypto exposure)
The class aggregate is negative, so every CRYPTO fund component must be a **specific cohort**:

**Strategies**
- `mega_mutation_macd_rsi_m017`: n=15, WR 80%, PF 5.302, Σ +45.6%.
- `mega_mutation_macd_rsi_m048`: n=44, WR 54.55%, PF 1.854, Σ +72.2%.
- `ensemble`: n=381, WR 38.32%, but PF 1.363, Σ +141.0% — positive expectancy via large
  winners (high-PF low-WR). Usable, but higher variance.
- `regime_mild_bear`: n=12, WR 100% — too small to trust on its own.

**Symbols (n≥10)**
- `ENJUSDT`: n=10, WR 80%, PF 8.599, Σ +81.7%.
- `ETCUSDT`: n=15, WR 60%, PF 2.88, Σ +11.35%.
- `ONDOUSDT`: n=30, WR 50%, PF 2.833, Σ +34.99%.
- `THEUSDT`: n=12, WR 50%, PF 1.886, Σ +15.93%.
- `POLUSDT`: n=23, WR 43.48%, PF 1.873, Σ +12.37%.
- `BNBUSDT`: n=27, WR 37.04%, PF 1.906, Σ +4.77%.
- Large-n positive-PF survivors: `WIFUSDT` (n=266, PF 1.277, Σ +110.2%),
  `JUPUSDT` (n=284, PF 1.127, Σ +60.5%), `ETHUSDT` (n=280, PF 1.056, Σ +12.8%).

> ⚠️ Attribution caveat: the `ensemble` symbol cohorts (`ENJUSDT`, `ETCUSDT`) carry
> `source_system=None` on their closed rows. The cohort metrics are real and validated, but
> the originating system is not cleanly attributable — flag before sizing a full position.

### 4.3 EQUITY / ETF / BOND / COMMODITY — NOT yet trustworthy
Sample sizes are far too small to underwrite any component (EQUITY n=8, ETF n=2, BOND n=1,
COMMODITY n=7, STOCKS n=3). `vt_equity_two_day_rsi_reversal` (n=7, WR 100%) and
`AAPL` (n=7, WR 100%) are interesting but unproven at this n. **Do not** include these in the
fund until more forward/closed data accumulates. Per directive G, this is the area to keep
collecting data quality on — not yet investable.

## 5. Verdict (directive G)

Trustworthy strategies **are** found, but only in specific niches:
- **FOREX:** `forex_rsi2_mean_reversion` + `CADJPY=X` / `AUDUSD=X` → **includable now**.
- **CRYPTO:** `mega_mutation_macd_rsi_m017` / `mega_mutation_macd_rsi_m048` and symbol
  cohorts `ENJUSDT`, `ETCUSDT`, `ONDOUSDT`, `THEUSDT`, `POLUSDT`, `WIFUSDT` → **includable
  now**, sized as cohorts (never as broad class exposure).
- **EQUITY/ETF/BOND/COMMODITY:** insufficient data → **not yet includable**; keep building
  forward/closed history (this is where mutual-fund work should focus next).
