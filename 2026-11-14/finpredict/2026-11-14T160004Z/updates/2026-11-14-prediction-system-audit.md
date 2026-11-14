# Prediction-System Audit — full findings (2026-11-14)

Auditor subtree: `finpredict`. Evidence sources: live `dashboard_data.json` (25 MB, generated `2026-11-14T14:30:07Z`, repo SHA `1b2c98e`), GitHub Actions API, Binance `api.binance.com/api/v3/ticker/price`, Frankfurter `api.frankfurter.app` (ECB, keyless), and repo source grep. Audit as-of `~16:00Z`.

---

## 0. Verdict (lead)

**FAIL — not genuinely profitable.** The system's own headline summary is negative: **WR 41.8%, profit factor 0.94, expectancy −0.11/trade, Sharpe −1.31 annualized, compounded PnL −62.65% (rolling-100) / −99% (equal-weight), 30d max DD 31.2%.** Crypto (the dominant class) is a net loser (PF 0.93). This is a multiple-testing + survivorship artifact, not an edge.

---

## 1. Actions health — FAIL

365 workflows (361 active, 4 disabled_manually). Last run: 295 success, **28 failure**, 11 cancelled, 10 in_progress, 1 skipped, **20 never run**. 51/365 have ≥1 failure in last 6 runs.

Recurring failures (named step): CI Tests (3.11+3.12 "Run all tests"); Live Trading Bot ×3, Autonomous Trading, Self-Optimizing, Crypto Picks Dispatch, Forward Test, Market Beating, robust-edge-miner — all at `Install dependencies`; Sports smoke at `Install Playwright`; ALPHA ENGINE Live/Dynamic/FAST at `Run Alpha Engine`; Daily Price Refresh + Daily Prices yfinance; Mirror deploy at FTP download. 24 workflows >30d stale (Forex Agent/Forex Smart Picks 164d, AI Tournament Pipeline 163d).

---

## 2. Active picks per asset class — FAIL (mostly stale, not "recent")

"Recent picks" are NOT actually recent for most classes. `picks.active_raw` = 4,148 rows, but the status split is the tell:

| class | OPEN | frozen at 0% (current==entry or null) | newest OPEN | age | verdict |
|---|---|---|---|---|---|
| CRYPTO | 402 | 334 (83%) | 11-14 13:54 | 2.0h | thin live minority; median age 30.5h |
| EQUITY | 94 | 40 (43%) | 11-14 13:06 | 2.8h | mixed |
| ETF | 30 | 15 (50%) | 11-14 12:53 | 3.0h | mixed |
| FOREX | 118 | 93 (79%) | 11-14 14:24 | 1.5h | heavily frozen |
| FUTURES | 3 | 3 (**100%**) | 11-14 13:06 | 2.8h | **dead** (0 closed ever, date-only seed) |
| BOND | 15 | 9 (60%) | 11-13 14:34 | **25.3h** | **effectively dead** |
| COMMODITY | 27 | 18 (67%) | 11-14 14:24 | 1.5h | mixed |
| SPORTS | 2 | 2 (**100%**) | 11-14 12:29 | 3.4h | **dead** |

`EXPIRED` rows inside `active_raw`: 3,377 (CRYPTO 3,100). These are the "STALE (auto-expired >5762h)" leftovers from March that still inflate the raw count.

**Only 123/691 OPEN picks (17.8%) carry a genuinely live, entry-differing price with non-zero PnL.** Of the 20 "clean" picks displayed, only **NEARUSDT** has real PnL; everything else is pinned at `current == entry` → 0%.

The "crypto 1.9h ago" banner is **signal age, not price age**: the newest crypto signal is 13:54Z, but XRP/BTC were never re-quoted at the 14:30Z build.

---

## 3. Frozen data — FAIL

- **`stock_forex_prices.json` `updated_at = 2026-04-11`** (217d) — server-side forex/stock cache dead.
- **Frozen "verified strategies" batch:** 127 OPEN picks seeded 2026-11-12 12:15–12:19; **123 (96.9%) frozen** at pnl 0 / current==entry. Strategies: PercentileRankMr, VolumeDivergence_Reversal, DrawdownRecoveryRSI*, HoffmanRoundNumber, BettingAgainstBeta, VolScaledTsmom, HurstRegimeFilter, ComboVolscaledTight, CTRENDFactor, IchimokuCloudBreakout, CCIDivergence, VerifiedStochRsi, VerifiedEmaStack, CorrVwapReversion, KimiLgbmFeatureProxy.
- **11 frozen closed phantoms:** FOREX (EURUSD, USDCHF, USDJPY, AUDUSD, GBPUSD, NZDUSD) + SOFI, March 2026, `exit UNKNOWN`, `exit_price == entry_price`, pnl 0.0 — never actually resolved.
- **Fabricated flat-3% cohort (placeholder P/L):** `signal_validation` (117 wins), `macd_rsi_confluence` (138), `meanreversionbb` (111), `macd_crossover`, `momentumema`, `bollinger_squeeze`, `gpx/gpm_gen*` — every win **exactly 3.00%, zero losers** (286 trades). Not market output.
- **`last_policy_change_at = 2026-04-09`** (7mo).
- **66 zero-pnl/flat** entries in headline summary.
- **Inventory mismatch:** 4,148 raw vs 263 (`concentration_summary.total_active`) vs 20 displayed vs 129 pre-gate.

---

## 4. Metric-field liveness — FAIL (most metrics dead)

Fraction of 691 OPEN picks with a meaningful value:

| field | alive % | verdict |
|---|---|---|
| `history_wr` / `history_trades` / `history_avg_pnl` | **0%** | DEAD |
| `profile_crypto_wr` | **0%** | DEAD |
| `strat_decay` | 0.1% | DEAD |
| `sym_track_wr` / `sym_track_total` | 2.7–3.6% | DEAD |
| `strat_fwd_pf` / `strat_csr` | 3.8% | DEAD |
| `forward_wr` | 8.7% | mostly dead |
| `forward_trades` | 10.1% | mostly dead |
| `strat_fwd_wr` / `strat_fwd_trades` | 6.9–8.5% | mostly dead |
| `rsi` | 21.0% | partial |
| `current_price` | 29.8% | partial |
| `strat_sample_quality` | 26.5% | partial |

Dashboard column provenance (from `audit_dashboard/template.html` + `dashboard_enhancements.js`):
- **EDGE** → `verified_edge` badge (derived from closed track record, not live).
- **Track** → `_ic_track` reads `sym_track_wr` (bold only n≥3), prefers `sym_dir_fwd_wr`.
- **FWD WR** → `strat_fwd_wr`; **FWD N** → `strat_fwd_trades`.
- `edge_ratio` is **absent from the main JSON** (peer v3) — the UI element reads a key that isn't emitted.

Because `strat_fwd_*` / `sym_track_*` are ~90% null/zero, the Edge/Track/FWD-WR/FWD-N columns render blank/zero for nearly all rows.

---

## 5. Data sources / strategies — REAL code, but dead feeds

Repo verification (grep of exact names) — **no phantoms/stubs**: every strategy label maps to real Python + a real external feed. The problem is the *data pipeline*, not the code:

| source | code | feed | status |
|---|---|---|---|
| `kalshi_signal_agent` / `kalshi_mtf_consensus` | `prediction_market_agents/kalshi_signal_agent.py` | Kalshi trade-api v2 | real code; **4 live picks all frozen current==entry, null stats; on-disk snapshot ~7mo stale** |
| `tsmom_strategy` / `tsmom_volscaled` | `alpha_engine/tsmom_strategy.py` | Binance klines (5 mirrors) | real; **price-alive (5 picks, non-zero PnL) but all metric fields null** |
| `non_crypto_consensus` (FOREX) | `copy_trader_intel/non_crypto_consensus.py` | downstream pick JSON | real aggregator; **underlying copy-trader feeds frequently empty (2-byte `[]`)** |
| `etf_all_strategies` + 6 ETF strats | `alpha_engine/etf_strategies.py` | yfinance | real |
| `commodity_carry_momo` / `commodity_rsi_divergence` | `tools/research/commodity_carry_momo.py`, `alpha_engine/commodities_strategies.py` | yfinance futures | real |
| `futures_connors_rsi2` | `alpha_engine/futures_strategies.py` | yfinance `=F` daily | real; **0 closed ever** |
| `regime_terminal` / `regime_*` | `regime_terminal/live_regime.py` + hmm engine | yfinance | real |
| `ueps` / `magic_formula_x_piotroski_x_acquirers` | `alpha_engine/value_screener.py` | SEC EDGAR + yfinance | real |
| `bond_*` | `alpha_engine/bond_strategies.py` + `bond_data_fred.py` | FRED + yfinance | real; **no price backfill → seeds null** |
| "verified strategies" batch | `incubator/backtest_team/forward_signal_scanner.py` | Binance forward harness | real; **frozen at dashboard (96.9%)** |

Conclusion: `kalshi_mtf_consensus` is real code, but its output in the dashboard is **frozen** (4 picks, `current==entry`, no forward stats, 7-month-old snapshot). Same pattern for the whole "verified" batch.

---

## 6. Live-price cross-check (what's real vs wrong)

| symbol/dir | dashboard current | reported PnL | live (source) | true PnL @ live | verdict |
|---|---|---|---|---|---|
| NEARUSDT SHORT (entry 3.324) | 3.233 | +2.74% | 3.222 (Binance) | +3.07% | **REAL & correct** (cur ~2h stale) |
| XRPUSDT SHORT (entry 0.9842) | 0.9842 | 0.0% | 0.9742 (Binance) | +1.0% | FROZEN (current==entry) |
| BTCUSDT SHORT (entry 66,300) | 66,300 | 0.0% | 65,839 (Binance) | +0.7% | FROZEN |
| USDCAD=X SHORT (entry 1.4269) | 1.4269 | −0.0% | 1.4258 (Frankfurter) | +0.08% | FROZEN |
| NZDUSD=X LONG (entry 0.552517) | 0.552517 | −0.0% | 0.5532 (Frankfurter) | +0.13% | FROZEN |

**NEARUSDT is genuine:** `(3.324−3.233)/3.324 = 2.738%` — exact. The "~3.1%" figure is the live price 3.222 (→3.07%), i.e. the pick is real but the stored current price is ~2h old. No fabrication in the arithmetic; only staleness.

---

## 7. Closed picks (recent realized) — FAIL

- `picks.recent_closed` (3,500): **42.2% WR**, sum PnL **−469.5%**, mean −0.134%. Last 7d: **34.6% WR, −381.3%**.
- Exit mix: SL_HIT 1,451 · TP_HIT 884 · FORCE_CLOSED 622 · TIME_EXIT 516 · UNKNOWN 22 · EXPIRED 5.
- By class: CRYPTO 40.2% / −689.9 · FOREX 39.0% / −29.0 · BOND 37.1% / −7.7 · COMMODITY 42.9% / −4.2 · EQUITY 47.0% / +238.4 · ETF 44.3% / +22.9.
- Headline `performance.by_asset_class`: CRYPTO PF 0.93 (net −458 over 4,907 closed); FOREX PF 0.48; ETF PF 0.76; BOND losing.
- **EQUITY is NOT a robust positive** — three inconsistent aggregators: headline n=8 (75% WR, PF 8.86, CI≈[0.41,0.93]); `non_crypto_performance` n=759 (46.1%); `recent_closed` n=738 (47.0%). Peer v3 reports full n=461 at ~43% / PF 0.70. Net: roughly breakeven, the n=8 "edge" is meaningless.

---

## 8. Dashboard structure — which tabs are stale vs real

Fresh (live build, <24h): core `dashboard_data.json` (Overview/Active/Smart/Closed/Leaderboard/Permutations/Performance/Score Tracker), `stock_prices.json` (14:13), `money_ready_verdict.json`, `crypto_rsi5070_us_forward_status.json`, `hyro_quan_bridge.json`, `cot_paper_pilot_status.json`, `ueps_picks.json`, plus live Binance/Bybit/CoinGecko/forex overlays.

Dead (embedded stale blocks inside the fresh file): `analyst_active_calls` + `analyst_leaderboard` (2026-03-26, 233d), `walkforward` (2026-04-15, 213d), `ml_health` (2026-05-25, 173d), `picks.active_raw` timestamps (2026-03-19, 240d).

Dead sidecar files: `strong_signals.json` (2026-04-15, 213d; peer reports 404 on a phase-2 path), `stock_forex_prices.json` (2026-04-11, 217d), `regime_report.json` (2026-06-05, 162d), `strategy_ic_analysis.json` (2026-05-29, 169d), and all 5 "AI battle" top-picks files `ag/claude/grok/mercury/kimi_top_3_live_picks.json` (2026-03-14, 245d).

Missing (404): `active_picks.json`, `strategy_tribunal_latest.json`, and the 5 `*_top_picks_phase2.json` battle cards.

Empty/placeholder: UEPS Swing + Closed Holds (n<100, no picks), `ta_baseline={}`, `macro_context={}`, `shadow_probation` (disabled), `extreme_conviction` (0 picks).

---

## 9. Multiple testing & survivorship (the verdict's core)

- **126 systems, 365 workflows, 112+ strategy names** in the recent closed set alone. With that many generators, a spread of "winners" is expected by chance; the aggregate proves no edge survives (PF 0.94, negative expectancy/Sharpe).
- **Survivorship:** `total_closed_picks 16,126` → `valid_closed_picks 7,914` (49%) with `integrity_excluded 7,567` and `auto_expired_excluded 8,888`. The headline 41.8% WR is computed on the surviving ~half.
- **Winners-only presentation:** `big_mover_monitor_3pct` shows +500% wins (HYPEUSDT `copy_hl_lb_none` ×many, `stochastic_momentum_index`, `crypto_vol_regime_accumulation`) without symmetric exposure of the matching −99% losers.
- **Concentration:** 25.8% of all PnL is BTCUSDT; top-3 source systems (`luxalgo_filters`, `kimi_riseoftheclaw`, `ml_bg_system_f`) = 88.5% of capped positive PnL.

---

## 10. Unverifiable / flagged, not guessed

- Individual US equity/ETF/futures marks against a paid-grade feed (Twelvedata/Stooq keyless endpoints rejected; Yahoo "Friday close" used by peer v3 for equities).
- Whether `FORCE_CLOSED`/`TIME_EXIT` closures were marked at fair market vs arbitrary exit.
- Real-money vs paper distinction for active picks.
- Exact full-sample EQUITY PF (three aggregators disagree: 8.86 vs positive-sum vs PF 0.70).

No fabricated numbers introduced; every figure above is read from the named file or API.
