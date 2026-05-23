# Strategy Catalog & Past-Month Pick Audit — 2026-05-18

**Scope:** read-only audit of the live strategy catalog and `at_raw_picks` pick flow.
**Data sources:** MySQL `ejaguiar1_stocks` (live, host `mysql.50webs.com`); repo strategy modules.
**Window:** `recorded_at >= NOW() - INTERVAL 30 DAY` → **2026-04-18 10:26 → 2026-05-18 07:54**.
**Window total:** 61,101 picks in `at_raw_picks`; 1,036 distinct `strategy` values; 119 distinct source systems.

> Honesty notes carried through the whole report:
> - "WR/PF" is computed **only** on resolved picks where `pnl_pct IS NOT NULL AND pnl_pct <> 0`.
> - `pnl_pct = 0` rows are treated as **placeholders**, not real outcomes, and excluded from WR/PF (count reported separately).
> - n is always stated. Nothing here is called "an edge."

---

## PART 1 — STRATEGY CATALOG PER ASSET CLASS

### 1.1 `strategy_registry` table (catalog of record)

| asset_class | rows | active | banned | distinct strategy_name | distinct system_name |
|---|---|---|---|---|---|
| MULTI   | 695 | 695 | 0 | 695 | 3 |
| CRYPTO  | 471 | 471 | 9 | 449 | 14 |
| EQUITY  | 17  | 17  | 0 | 14  | 2 |
| FOREX   | 12  | 12  | 0 | 6   | 1 |
| **Total** | **1,195** | **1,195** | **9** | — | — |

The registry **has no rows** for COMMODITY, ETF, BOND, FUTURES, MEMECOIN, or PENNY_STOCK. It is heavily crypto/multi-weighted and is not a faithful inventory of what actually emits picks — see §1.3.

Registry by `system_name` (top): `alpha_engine` 903, `baby_strategies` 81, `pine_scripts` 47, `ml_infrastructure` 40, `kimi_riseoftheclaw` 24, `root_level` 23, `paper_trading` 14, `meta_strategy` 9, `ml_crypto_predictor` 9, `crypto_ml_edge` 8, `genome` 8, `quant_lab` 8.

### 1.2 Repo strategy modules

`alpha_engine/` carries **~130 `*strateg*.py` modules** plus `alpha_engine/strategies/` (~20 files), `alpha_engine/new_strategies/` (~16 generators), `coinglass_strategies/strategies/` (14 modules: calendar_spread, cross_exchange_spread, extreme_reversion, funding_confirmation, leverage_adjusted, news_sentiment, options_volatility, ratio_momentum, risk_parity, roll_yield, sentiment_index, spike_detection, top_trader_divergence), and `copy_trader_intel/` (40+ scrapers/replicators). `alpha_engine/_generate_600_strategies.py` and `generated_v2_bundle.py` are **bulk generators** — they are the primary source of variant sprawl, not 600 distinct edges.

### 1.3 What actually emits — `at_raw_picks` distinct strategies per class (30d)

| asset_class | distinct strategies | picks (30d) |
|---|---|---|
| CRYPTO       | 878 | 45,566 |
| (blank `''`) | 140 |  2,287 |
| EQUITY       | 37  |  5,194 |
| MEMECOIN     | 33  |    398 |
| FOREX        | 31  |  4,850 |
| ETF          | 20  |     76 |
| UNKNOWN      | 20  |    703 |
| PENNY_STOCK  | 18  |    104 |
| FUTURES      | 13  |  1,923 |
| **COMMODITY** | **0** | **0** |
| **BOND**      | **0** | **0** |

**COMMODITY and BOND emitted zero picks in the last 30 days.** Despite `commodities_strategies.py`, `bond_strategies.py`, `coinglass_strategies/strategies/roll_yield.py` etc. existing in the repo, no commodity/bond rows reached `at_raw_picks` in-window. CTA commodity signals are filed under `FUTURES` (`cta_commodity_momentum_term`, `cftc_cot_commercial_signal`).

The CRYPTO count of **878 distinct strategy strings is almost entirely sprawl** (see §1.4) — the number of genuinely distinct *strategy designs* is roughly **40–60**, not 878.

### 1.4 Duplicate / variant sprawl (FLAGGED)

The `strategy` column conflates strategy *design* with per-symbol / per-model / per-author *instances*. Counted families:

| family pattern | distinct strategy strings | picks (30d) | verdict |
|---|---|---|---|
| `quan_engine%` (`quan_engine`, `_scalp`, …) | 4 | 8,740 | core design + variants |
| `enhanced_ml%` (`enhanced_ml_A_xgboost`, …) | 3 | 5,591 | model-letter variants of 1 design |
| `reddit/reddit:u/<author>` | 17 (in-window; 100s historically) | 4,092 | **SPRAWL** — one "source" per Reddit user, not a strategy |
| `ml_enhanced_<SYMBOL>_<tf>_<model>` | **119** | 2,960 | **SPRAWL** — per-symbol×model instances of one ML template |
| `drawdown_recovery_rsi_<coin>` | 4 (eth/xrp/sol/…) | 2,059 | **SPRAWL** — one design fanned across coins |
| `regime_<state>` | 10 | 1,324 | regime-router buckets, 1 design |
| `gnews/gnews:<publisher>` | 9 | 872 | **SPRAWL** — news publisher = "strategy" |
| `copy_hl%` | 5 | 443 | copy-trade leaderboard variants |
| `futures_*` (`momentum`, `connors_rsi2`, `bb_mean_reversion`, `mean_reversion`) | 4 | 516 | distinct designs (NOT v1..v15 sprawl — that pattern is in module files/registry, not in-window picks) |

**Headline sprawl finding:** the 149-ish `ml_enhanced_*` family the brief flagged shows **119 distinct strings in just the 30-day window** (more historically) — these are `ml_enhanced_TRXUSDT_1d_B_lightgbm`, `ml_enhanced_INJUSDT_1d_B_lightgbm`, etc. They are **one ML pipeline instantiated per (symbol, timeframe, model)** and must be counted as **1 strategy design**, not 119. Likewise `reddit/...` (4,092 picks across 17+ author handles) and `gnews/...` (872 picks across 9 publishers) are **ingestion sources mislabelled as strategies** — they inflate the CRYPTO distinct count from a true ~40–60 to 878.

---

## PART 2 — PAST-MONTH PICK AUDIT TRAIL (30d)

### 2.1 Per-asset-class funnel

| class | emitted | OPEN | WON | LOST | CLOSED | EXPIRED | closed_at NULL | pnl≠NULL | pnl=0 (placeholder) | pnl real (≠0) |
|---|---|---|---|---|---|---|---|---|---|---|
| CRYPTO      | 45,566 | 24,873 | 523 | 877 | 19,079 | 214 | 25,177 | 20,511 | 10,457 | 10,054 |
| EQUITY      | 5,194  | 5,126  | 0   | 0   | 55     | 13  | 5,131  | 63     | 63     | **0** |
| FOREX       | 4,850  | 4,769  | 4   | 9   | 52     | 16  | 4,785  | 76     | 63     | 13 |
| `''` blank  | 2,287  | 1,730  | 0   | 0   | 557    | 0   | 1,730  | 557    | 556    | 1 |
| FUTURES     | 1,923  | 1,904  | 0   | 0   | 2      | 17  | 1,911  | 12     | 12     | **0** |
| UNKNOWN     | 703    | 653    | 0   | 0   | 50     | 0   | 653    | 50     | 50     | **0** |
| MEMECOIN    | 398    | 10     | 26  | 62  | 290    | 10  | 17     | 380    | 19     | 361 |
| PENNY_STOCK | 104    | 60     | 0   | 0   | 32     | 12  | 71     | 33     | 33     | **0** |
| ETF         | 76     | 55     | 0   | 0   | 14     | 7   | 60     | 16     | 16     | **0** |
| COMMODITY   | 0 | — | — | — | — | — | — | — | — | — |
| BOND        | 0 | — | — | — | — | — | — | — | — | — |

**Resolution reality:** of 61,101 picks, **66,000-ish are still effectively unresolved** — 41,180 have `closed_at` NULL, and of the 21,778 with a non-null `pnl_pct`, **11,225 are `pnl_pct = 0` placeholders**. Only **~10,442 picks have a real (non-zero) outcome**, and **96% of those (10,054) are CRYPTO**. EQUITY, FUTURES, ETF, PENNY_STOCK, UNKNOWN have **zero real-pnl resolved picks** — every "resolved" row in those classes is a `pnl_pct=0` placeholder.

### 2.2 Honest WR / PF per class (real-pnl picks only, exclude pnl=0)

| class | n (real) | wins | losses | gross_win | gross_loss | **WR** | **PF** | avg pnl_pct |
|---|---|---|---|---|---|---|---|---|
| CRYPTO   | 10,054 | 3,557 | 6,497 | 113,119.9 | 307,718.9 | **35.4%** | **0.37** | −19.36 |
| MEMECOIN | 361    | 140   | 221   | 5,064.4   | 8,162.5   | **38.8%** | **0.62** | −8.58 |
| FOREX    | 13     | 4     | 9     | 6.9       | 85.6      | **30.8%** | **0.08** | −6.06 (n=13, not interpretable) |
| EQUITY / FUTURES / ETF / PENNY_STOCK / UNKNOWN | 0 | — | — | — | — | n/a | n/a | no real outcomes |

Only CRYPTO has a statistically meaningful resolved sample (n=10,054), and at **WR 35.4% / PF 0.37** it is well below break-even. MEMECOIN (n=361) is also losing. FOREX has n=13 real picks — too thin to read. No other class has a single non-placeholder resolved pick in 30 days.

### 2.3 Top 25 strategies by 30-day volume

| strategy | class(es) | emitted | open | closed | real-n | WR | PF | flag |
|---|---|---|---|---|---|---|---|---|
| incubator_gainer | CRYPTO/MEMECOIN | 8,337 | 1,043 | 7,294 | **1** | 0.0% | 0.00 | resolved but 7,293/7,294 are pnl=0 placeholders |
| quan_engine | CRYPTO/MEMECOIN | 7,449 | 0 | 7,397 | 7,447 | **36.4%** | **0.48** | real data; `−15.0000` repeated 1,036× — partial placeholder contamination |
| enhanced_ml_A_xgboost | CRYPTO | 5,568 | 5,559 | 9 | 7 | 28.6% | 0.67 | 99.8% still OPEN |
| `''` (blank strategy) | mixed | 4,556 | 1,211 | 3,336 | 53 | 9.4% | 0.01 | **unattributed picks — no strategy label** |
| smart_money_consensus | EQUITY/UNKNOWN | 3,021 | 3,020 | 1 | 0 | — | — | 100% unresolved |
| ig_contrarian_sentiment | FOREX | 1,786 | 1,786 | 0 | 0 | — | — | **100% NULL closed_at — unresolvable** |
| stocks_rsi2_pullback | EQUITY/UNKNOWN | 1,608 | 1,608 | 0 | 0 | — | — | **100% NULL closed_at — unresolvable** |
| meta_strategy | CRYPTO/MEMECOIN | 1,253 | 0 | 1,253 | 1,248 | **42.9%** | **1.05** | real data; best PF of any high-volume strategy |
| prediction_market_consensus | CRYPTO | 1,189 | 1,122 | 67 | 0 | — | — | resolved rows all placeholder |
| quan_engine_scalp | CRYPTO/MEMECOIN | 1,086 | 0 | 1,086 | 1,086 | **24.4%** | **0.31** | real data; weak |
| forex_rsi2_mean_reversion | FOREX | 896 | 895 | 1 | 0 | — | — | **~100% unresolvable** |
| myfxbook_retail_contrarian | FOREX | 840 | 837 | 3 | 0 | — | — | ~100% unresolvable |
| drawdown_recovery_rsi_eth | CRYPTO | 703 | 675 | 28 | 0 | — | — | resolved rows all placeholder |
| drawdown_recovery_rsi_xrp | CRYPTO | 679 | 675 | 4 | 0 | — | — | ~100% unresolvable |
| drawdown_recovery_rsi_sol | CRYPTO | 675 | 671 | 4 | 0 | — | — | ~100% unresolvable |
| forex_carry_momentum | FOREX | 634 | 629 | 1 | 0 | — | — | ~100% unresolvable |
| luxalgo_confluence | CRYPTO | 588 | 588 | 0 | 0 | — | — | **100% NULL closed_at — unresolvable** |
| cta_commodity_momentum_term | FUTURES | 499 | 499 | 0 | 0 | — | — | **100% NULL closed_at — unresolvable** |
| cta_cross_asset_tsmom | FOREX/FUTURES/ETF | 489 | 487 | 2 | 0 | — | — | ~100% unresolvable |
| reddit/reddit:u/Gr33nHatt3R | CRYPTO | 487 | 486 | 1 | 1 | 100.0% | — | n=1, not interpretable; sprawl source |
| atr_percentile_gate | CRYPTO | 424 | 424 | 0 | 0 | — | — | **100% NULL closed_at — unresolvable** |
| cot_positioning | FOREX/FUTURES | 392 | 391 | 1 | 0 | — | — | ~100% unresolvable |
| crypto_liquidity_wick_reversal_v1 | CRYPTO | 366 | 366 | 0 | 0 | — | — | **100% NULL closed_at — unresolvable** |
| copy_hl_lb_None | CRYPTO | 362 | 362 | 0 | 0 | — | — | **100% NULL closed_at**; `_None` suffix = malformed leaderboard id |
| regime_mild_bull | mixed | 351 | 335 | 16 | 0 | — | — | resolved rows all placeholder |

### 2.4 Flagged failure modes

- **Unresolvable strategies:** 69 strategies with ≥50 picks in-window have **0% non-null `closed_at`** — they emit and never resolve. This includes all of FOREX (`ig_contrarian_sentiment`, `forex_rsi2_mean_reversion`, `myfxbook_retail_contrarian`, `forex_carry_momentum`, `cot_positioning`), all FUTURES (`cta_commodity_momentum_term`, `futures_*`, `cftc_cot_commercial_signal`), and many CRYPTO (`luxalgo_confluence`, `atr_percentile_gate`, `crypto_liquidity_wick_reversal_v1`, `copy_hl_lb_None`).
- **Placeholder-stat contamination:** 11,225 of 21,778 non-null `pnl_pct` rows are exactly `0` (placeholders, not flat trades). `incubator_gainer` (8,337 picks) has 7,294 "closed" rows but only **1** real-pnl row — its CLOSED count is illusory. `quan_engine` shows the value `−15.0000` repeated **1,036 times** — a likely default-fill artifact partially contaminating its PF 0.48.
- **Unattributed picks:** 4,556 picks (7.5% of the window) carry a **blank `strategy`** string, spanning every asset class — these cannot be attributed to any design.
- **Malformed ids:** `copy_hl_lb_None` (`_None` suffix from a null leaderboard id) — 362 picks.

---

## PART 3 — SUMMARY

1. **Genuinely-distinct strategy designs per class** (sprawl collapsed): the system *appears* to run 1,036 strategies but truly runs roughly **CRYPTO ~40–60, FOREX ~6–8, EQUITY ~5–8, FUTURES ~6, MEMECOIN ~4, ETF ~3 (regime + CTA buckets), COMMODITY 0, BOND 0**. The `strategy_registry` (1,195 rows, 695 "MULTI" + 471 CRYPTO) is itself padded by generators (`_generate_600_strategies.py`, `generated_v2_bundle.py`).

2. **Over-saturated with duplicates — CRYPTO.** 878 distinct strategy strings, but ~819 of them are sprawl: 119 `ml_enhanced_<symbol>_<model>` instances (1 ML template), 4,092 picks under 17+ `reddit/u/<author>` "strategies" (an ingestion source), 872 picks under 9 `gnews/<publisher>` strings, and `drawdown_recovery_rsi_<coin>` fanned across coins. These are sources/instances, not designs.

3. **Thin / dead classes:** COMMODITY and BOND emitted **0 picks in 30 days** — dormant despite live modules. ETF emitted only 76 (all via `regime_*` and `cta_*` buckets). PENNY_STOCK 104. None of these has a single real (non-placeholder) resolved outcome.

4. **Resolved-pick funnel (30d):** 61,101 emitted → 41,180 still `closed_at` NULL → 21,778 with a `pnl_pct` value → **11,225 of those are `pnl_pct=0` placeholders** → only **~10,442 picks have a real outcome, ~96% CRYPTO**. EQUITY, FOREX (effectively), FUTURES, ETF, PENNY_STOCK, UNKNOWN have **no usable resolved sample**. 69 strategies (≥50 picks each) never resolve a single pick.

5. **Honest per-class WR/PF (real-pnl only, n stated — none is an edge):** CRYPTO **WR 35.4% / PF 0.37 (n=10,054)** — clearly losing. MEMECOIN **WR 38.8% / PF 0.62 (n=361)** — losing. FOREX **WR 30.8% / PF 0.08 (n=13)** — sample too small to interpret. Best individual high-volume strategy is `meta_strategy` (WR 42.9% / PF 1.05, n=1,248) — the only ≥1,000-pick strategy at break-even or above; `quan_engine` (PF 0.48, n=7,447) and `quan_engine_scalp` (PF 0.31, n=1,086) are the volume leaders and both lose money. All other classes are unverifiable because the outcome resolver is not closing their picks.

---

*Report path: `reports/strategy_catalog_pick_audit_2026_05_18.md`. Read-only audit — no DB writes, no other files modified.*
