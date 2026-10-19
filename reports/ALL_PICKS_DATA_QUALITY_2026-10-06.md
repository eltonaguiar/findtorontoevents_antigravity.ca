# All-Picks Data-Quality & Reasoning Audit — by Asset Class

**Source:** live `https://findtorontoevents.ca/audit/data/dashboard_data.json`
**generated_at:** `2026-10-06T00:48:47.724226+00:00`  ·  **repo_sha:** `84f680bdf5ef3419d6b841b1db4ddfa94a2651bf`
**payload_lag_seconds:** `5240.724226`

Scope: the full payload book — `picks.active_raw` by status + `picks.recent_closed`. A pick is **documented** when `reason` or `notes` is non-empty; it is **qualified** when that text also carries a measurable quantity (indicator + number), vs **placeholder** when it names a missing value (`None`/`nan`).

## 0. Scope caveat

- `active_raw` = **4104** rows (OPEN 829, EXPIRED 3231, other 44).
- `recent_closed` = **3500** rows — the payload exposes only a windowed sample, while `summary.total_closed_picks` = **12255**. Closed-book findings below cover the exposed window only.

## TL;DR

- **Reasoning is missing on half the open book and most of the closed book.** 829 OPEN picks are only 50% documented (416 carry no reason/notes); the 3500 exposed closed picks are 43% documented.
- **EQUITY is the worst open class** and **ETF the worst closed class** (see sections 1–2).
- **59 OPEN picks carry zero/missing entry-TP-SL prices** (genome `GPX_*`/`GPM_*` + `prediction_market_consensus`) — unusable for any PnL math.
- **3 OPEN picks are already past their TP/SL** and were never resolved; plus 1 FOREX pick with a garbage-scale TP/SL (USDCAD=X 1.422 → TP 812.43).
- **452 OPEN picks have no `current_price`** — the dashboard cannot compute live PnL for them.
- **119 rows leak `lb_None`** (an unresolved leaderboard label) into the reason text.
- **2 SPORTS bet(s)** sit inside the tradeable active book.
- **Duplication:** 391 of 829 OPEN rows belong to duplicate (symbol, direction, strategy) groups.

## 1. Reasoning coverage — OPEN active picks (what the page shows)

| Asset class | OPEN | Documented | Qualified | Prose | Placeholder | Missing |
|---|---|---|---|---|---|---|
| BOND | 25 | 25 (100%) | 23 | 2 | 0 | 0 |
| COMMODITY | 50 | 47 (94%) | 47 | 0 | 0 | 3 |
| CRYPTO | 468 | 167 (36%) | 131 | 36 | 0 | 301 |
| EQUITY | 100 | 10 (10%) | 10 | 0 | 0 | 90 |
| ETF | 36 | 24 (67%) | 22 | 2 | 0 | 12 |
| FOREX | 135 | 128 (95%) | 127 | 1 | 0 | 7 |
| FUTURES | 13 | 12 (92%) | 12 | 0 | 0 | 1 |
| SPORTS | 2 | 0 (0%) | 0 | 0 | 0 | 2 |
| **ALL** | **829** | **413 (50%)** | **372** | **41** | **0** | **416** |

## 2. Reasoning coverage — closed picks (exposed window)

| Asset class | Closed | Documented | Qualified | Prose | Placeholder | Missing |
|---|---|---|---|---|---|---|
| BOND | 29 | 2 (7%) | 1 | 1 | 0 | 27 |
| COMMODITY | 3 | 3 (100%) | 3 | 0 | 0 | 0 |
| CRYPTO | 2149 | 1432 (67%) | 1432 | 0 | 0 | 717 |
| EQUITY | 637 | 24 (4%) | 24 | 0 | 0 | 613 |
| ETF | 471 | 0 (0%) | 0 | 0 | 0 | 471 |
| FOREX | 210 | 58 (28%) | 54 | 4 | 0 | 152 |
| FUTURES | 1 | 0 (0%) | 0 | 0 | 0 | 1 |
| **ALL** | **3500** | **1519 (43%)** | **1514** | **5** | **0** | **1981** |

## 3. Structural integrity — OPEN picks by class

| Asset class | OPEN | zero/missing prices | null current_price | TP wrong side | SL past entry | TP reached / SL breached (still OPEN) |
|---|---|---|---|---|---|---|
| BOND | 25 | 0 | 8 | 0 | 0 | 0 |
| COMMODITY | 50 | 0 | 34 | 0 | 0 | 0 |
| CRYPTO | 468 | 59 | 279 | 0 | 8 | 0 |
| EQUITY | 100 | 0 | 22 | 0 | 4 | 2 |
| ETF | 36 | 0 | 12 | 0 | 0 | 0 |
| FOREX | 135 | 0 | 92 | 0 | 1 | 1 |
| FUTURES | 13 | 0 | 3 | 0 | 0 | 0 |
| SPORTS | 2 | 0 | 2 | 0 | 0 | 0 |

## 4. Closed-book integrity by class

| Asset class | Closed | pnl_pct==0 | UNKNOWN exit | None pnl (null) |
|---|---|---|---|---|
| BOND | 29 | 1 | 1 | 0 |
| COMMODITY | 3 | 1 | 0 | 0 |
| CRYPTO | 2149 | 0 | 4 | 0 |
| EQUITY | 637 | 10 | 5 | 0 |
| ETF | 471 | 0 | 3 | 0 |
| FOREX | 210 | 39 | 11 | 0 |
| FUTURES | 1 | 0 | 0 | 0 |

## 5. Duplication — OPEN picks by class

| Asset class | OPEN | duplicate (symbol,direction,strategy) groups | rows in dup groups |
|---|---|---|---|
| BOND | 25 | 5 | 11 |
| COMMODITY | 50 | 18 | 43 |
| CRYPTO | 468 | 62 | 158 |
| EQUITY | 100 | 12 | 26 |
| ETF | 36 | 6 | 12 |
| FOREX | 135 | 41 | 129 |
| FUTURES | 13 | 4 | 10 |
| SPORTS | 2 | 1 | 2 |

## 6. Cross-cutting flags

- **`lb_None` in reason** (missing leaderboard label leaked into text): **119** rows.
- **SPORTS rows inside the tradeable active book**: **2**.
- **OPEN picks older than 7 days**: **0**.

SPORTS rows found:
  - `Montreal Canadiens vs Buffalo Sabres` LONG (value_bet)
  - `Montreal Canadiens vs Buffalo Sabres` LONG (value_bet)

## 7. Worst reasoning emitters (no reason/notes)

**OPEN active picks:**

| strategy | undocumented / total |
|---|---|
| `inverse_luxalgo_confluence` | 75 / 75 |
| `magic_formula_x_piotroski_x_acquirers` | 24 / 24 |
| `penny_stock_screener` | 20 / 20 |
| `incubator_gainer` | 20 / 20 |
| `kimi_signal_tracking` | 18 / 18 |
| `incubator_gainer_composite` | 15 / 15 |
| `regime_terminal` | 11 / 11 |
| `quan_engine` | 9 / 9 |
| `super signal (strong) via kimi` | 7 / 7 |
| `regime_mild_bear` | 7 / 7 |
| `funding-rate-reversal` | 6 / 8 |
| `vwma_momentum_trend` | 5 / 5 |

**Closed picks (exposed window):**

| strategy | undocumented / total |
|---|---|
| `rs-breakout-scout` | 109 / 109 |
| `intermarket-flow-scout` | 91 / 91 |
| `quality-minus-junk` | 83 / 83 |
| `adx-trend-scout` | 83 / 83 |
| `luxalgo_confluence` | 75 / 1253 |
| `MomentumEMA` | 73 / 73 |
| `momentum-factor` | 70 / 70 |
| `vol-contraction-scout` | 67 / 67 |
| `rsi-divergence-scout` | 67 / 67 |
| `unknown` | 66 / 66 |
| `london-breakout-scout` | 64 / 64 |
| `strong consensus (alpha_engine, luxalgo_filters)` | 58 / 58 |

## 8. Exact structural defect rows (OPEN)

**Zero / missing prices** (59 rows), by strategy:

| strategy | rows |
|---|---|
| `GPX_Gen106_b7909b` | 3 |
| `GPM_Gen327_231c8d` | 3 |
| `GPX_Gen219_fa5210` | 3 |
| `GPX_Gen452_8666a5` | 3 |
| `GPX_Gen468_011ae5` | 3 |
| `GPX_Gen259_a85ace` | 3 |
| `GPX_Gen411_b7fef3` | 3 |
| `GPX_Gen371_017f32` | 3 |
| `prediction_market_consensus` | 3 |
| `GPX_Gen207_8299f3` | 2 |
| `GPX_Gen10_52eed1` | 2 |
| `GPX_Gen32_d1aed6` | 2 |

**TP/SL scale anomaly** (|TP-entry| or |entry-SL| > 50x entry → garbage scale):

| class | symbol | dir | entry | TP | SL | strategy |
|---|---|---|---|---|---|---|
| FOREX | `USDCAD=X` | LONG | 1.422 | 812.43 | 721.74 | `regime_mild_bull` |

**Breached but still OPEN** (price beyond TP or SL — resolver gap):

| tag | class | symbol | dir | entry | TP | SL | current | strategy |
|---|---|---|---|---|---|---|---|---|
| tp_reached_open | EQUITY | `DNA` | LONG | 12.35 | 13.28 | 11.79 | 14.979999542236328 | `regime_accumulation` |
| tp_reached_open | EQUITY | `DNA` | LONG | 12.35 | 13.28 | 11.79 | 14.979999542236328 | `regime_accumulation` |
| sl_breached_open | FOREX | `USDCAD=X` | LONG | 1.422 | 812.43 | 721.74 | 1.4254800081253052 | `regime_mild_bull` |

## 9. Reasoning examples

**Qualified (indicator + number):**
- `XRPUSDT` SHORT — Kalshi consensus: SHORT XRPUSDT (2/3 timeframes agree, net score: -0.36)
- `BTCUSDT` SHORT — Kalshi consensus: SHORT BTCUSDT (2/5 timeframes agree, net score: -0.14)
- `LABD` SHORT — 3x Short Biotech ETF - structural decay harvest. 3x leveraged products lose value via volatility drag (realized vol=75%). Backtest: 76.9% WR, PF 2.94, avg +3.38%/trade on 39 trades. Underlying XBI 20d

**Missing (no reason/notes):**
- `TRXUSDT` LONG (super signal (strong) via kimi) — no reason/notes
- `DOTUSDT` LONG (super signal (super) via kimi) — no reason/notes
- `JUPUSDT` LONG (inverse_luxalgo_confluence) — no reason/notes

## 10. Recommendations

1. **Block reason-less picks from the book.** A pick with no `reason`/`notes` should be rejected at emit time. Prioritise the emitters in section 7 — EQUITY (`magic_formula_x_piotroski_x_acquirers`, `penny_stock_screener`) and CRYPTO (`inverse_luxalgo_confluence`, `incubator_gainer`, `kimi_signal_tracking`).
2. **Reject zero/missing-price rows.** The 59 genome/prediction-market OPEN picks have entry=TP=SL=0 and are unusable; they inflate the active count.
3. **Fix the resolver gaps.** The 3 breached-but-open picks (DNA ×2, USDCAD=X) and the garbage-scale USDCAD=X row should be force-resolved or quarantined.
4. **Backfill `current_price`** for the OPEN picks missing it, or exclude them from live PnL/score surfaces.
5. **Strip `lb_None` placeholder text** at emit time — do not interpolate an unresolved label into the reason.
6. **Dedupe at the source.** Collapse duplicate (symbol, direction, strategy) groups before they reach `active_raw`.
7. **Route SPORTS picks out of the trading book** into the sports pipeline.

---
*Generated by `tools/audit_all_picks_quality.py`. Read-only; reproducible from `dashboard_data.json::picks.active_raw` + `::picks.recent_closed`.*
