# Emitter Mute/Kill Proposal (S5) - 2026-11-25

READ-ONLY analysis. No code was changed, no DB row mutated, no git command run.
Strictly read-only SQL (SELECT/SHOW only, 15s timeouts, sequential); `smart_picks_engine.py`
and `check_active_picks.py` NOT run (per standing instruction).

Scope: "emitter" = a strategy/generator producing picks into (a) raw/shadow tables
(`trading_picks.strategy`, `at_raw_picks.strategy`), (b) JSON pick sources
(`JSON_PICK_SOURCES`, `active_*` JSONs), (c) workflow crons that feed them.

Status: COMPLETE - all 4 stages done. 25 read-only SELECT/SHOW statements + 17 read-only GitHub API reads. No mutations, no git commands, no other files touched.

---

## Stage 1 - Top emitters by volume (90d + 30d)

SQL: 8 statements in this stage (trading_picks schema + 90d aggregate, at_raw_picks
schema + 90d aggregate, at_local_picks OPEN aggregate, trading_picks category mix,
trading_picks_v2 clean-ledger class summary). "OPEN%-90d" = share of a strategy's 90d
rows carrying status OPEN/ACTIVE; "=0" columns are closed rows with pnl_pct exactly 0 (fake zeros,
cf. S4 Q2).

### 1a. trading_picks (THE 99,345-row backlog table) - top emitters, last 90d

| strategy | n90 | n30 | OPEN | OPEN%-90d | aged OPEN >7d | closed n | meas. W/L | WR (meas) | PF | =0 pnl | last emit | age |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| forex_rsi2_mean_reversion | 9,191 | 3,180 | 7,987 | 86.9% | 7,897 | 1,204 | 210/193 | 52.1% | 2.34 | **800/1,204 (66.4%)** | 2026-11-19 | 6.3d |
| non_crypto_consensus | 8,770 | 4,362 | **8,770** | **100%** | 8,114 | **0** | - | - | - | 0 | 2026-11-25 | live |
| forex_zscore_200d_fade | 8,623 | 2,070 | 8,580 | 99.5% | 7,635 | 43 | 8/35 | 18.6% | 1.08 | 0 | 2026-11-25 | live |
| combined_confidence | 2,785 | 1,469 | 2,771 | 99.5% | 2,719 | 14 | 4/10 | 28.6% | 1.47 | 0 | 2026-11-25 | live |
| luxalgo_confluence | 2,643 | 1,033 | 1,175 | 44.5% | 885 | 1,468 | 616/833 | 42.6% | 1.096 | 0 | 2026-11-25 | live |
| futures_bb_mean_reversion | 2,540 | 978 | **2,539** | **99.96%** | 2,031 | 1 | - | - | - | 0 | 2026-11-25 | live |
| short_dominant_engine | 2,341 | 531 | **2,341** | **100%** | 2,200 | 0 | - | - | - | 0 | 2026-11-25 | live |
| smart_money_accumulation | 2,272 | 797 | 2,271 | 99.96% | 1,873 | 1 | - | - | - | 0 | 2026-11-24 | 1.4d |
| futures_connors_rsi2 | 1,689 | 458 | 1,685 | 99.8% | 1,685 | 4 | - | - | - | 0 | 2026-11-18 | 7.8d |
| cftc_cot_commercial_signal | 1,576 | 489 | 1,574 | 99.9% | 1,564 | 2 | - | - | - | 0 | 2026-11-19 | 6.3d |
| regime_mild_bear | 1,354 | 224 | 1,242 | 91.7% | 1,218 | 112 | 45/66 | 40.5% | 0.97 | 0 | 2026-11-24 | 1.4d |
| stocks_ema_golden_cross | 1,316 | 321 | **1,316** | **100%** | 1,314 | 0 | - | - | - | 0 | 2026-11-24 | 1.4d |
| regime_accumulation | 1,017 | 116 | 932 | 91.6% | 916 | 85 | 39/46 | 45.9% | 0.74 | 0 | 2026-11-24 | 1.6d |
| copy_pm_pm_f705fa04 | 670 | 459 | 670 | 100% | 463 | 0 | - | - | - | 0 | 2026-11-25 | live |
| copy_pm_pm_06dc5182 | 666 | 209 | 666 | 100% | 568 | 0 | - | - | - | 0 | 2026-11-25 | 1d |
| regime_strong_bear | 637 | 160 | 589 | 92.5% | 528 | 48 | 21/27 | 43.8% | 0.76 | 0 | 2026-11-25 | 17h |
| regime_mild_bull | 536 | 110 | 500 | 93.3% | 480 | 36 | 8/28 | 22.2% | 0.52 | 0 | 2026-11-23 | 2.6d |
| copy_pm_tokor | 412 | 226 | 412 | 100% | 280 | 0 | - | - | - | 0 | 2026-11-25 | 12h |
| pm_macro_expansion | 353 | 353 | 353 | 100% | 0 | 0 | - | - | - | 0 | 2026-11-25 | 2h |
| etf_rsi2_pullback | 346 | 72 | 345 | 99.7% | 338 | 1 | 0/1 | 0% | 0.00 | 0 | 2026-11-19 | 6.4d |
| (empty strategy) | 266 | 45 | 134 | 50.4% | 128 | 132 | 105/27 | **79.5%** | 8.44 | 0 | 2026-11-25 | 11h |
| leveraged_etf_decay | 246 | 70 | 246 | 100% | 232 | 0 | - | - | - | 0 | 2026-11-25 | 5.5h |
| etf_faber_tactical | 205 | 55 | 198 | 96.6% | 197 | 7 | 0/7 | 0% | 0.00 | 0 | 2026-11-19 | 6.4d |
| rapid_momentum_filter_mut | 192 | 60 | 161 | 83.9% | 159 | 31 | 18/13 | 58.1% | 1.69 | 0 | 2026-11-25 | 14h |
| etf_dual_momentum | 177 | 47 | 177 | 100% | 173 | 0 | - | - | - | 0 | 2026-11-24 | 1.4d |
| bond_yield_momentum | 143 | 38 | 135 | 94.4% | 130 | 8 | **0/8** | 0% | 0.00 | 0 | 2026-11-20 | 5.4d |
| etf_sector_momentum | 153 | 46 | 152 | 99.3% | 151 | 1 | 0/1 | 0% | 0.00 | 0 | 2026-11-19 | 6.4d |
| funding_rate_arb | 144 | 80 | 144 | 100% | 132 | 0 | - | - | - | 0 | 2026-11-22 | 3.8d |
| etf_sector_dual_momentum | 144 | 36 | 144 | 100% | 138 | 0 | - | - | - | 0 | 2026-11-24 | 1.4d |

(Lower-volume tail omitted: copy_pm_* polymarket-copy family, regime_crash,
tv_community_consensus, tsmom_28d, high_trust_momentum, cnn_lite_pattern_signal all show
the same 100%-OPEN pattern.)

**Stage 1 headline facts (measured):**
- **"Emits but never closes" cluster = 100% OPEN over 90d:** non_crypto_consensus (8,770),
  short_dominant_engine (2,341), stocks_ema_golden_cross (1,316), every copy_pm_* clone
  (~2,500 rows across 9 emitters), leveraged_etf_decay, etf_dual_momentum, etf_sector_dual_momentum,
  futures_bb_mean_reversion (99.96%), smart_money_accumulation (99.96%), funding_rate_arb.
  These are pure backlog machines: each row enters the 99,345-row pile and never leaves.
- **Close-regime emitters (they do resolve):** luxalgo_confluence (44.5% open - closes),
  the regime_* family, rapid_momentum_filter_mut, the unlabeled '' cohort (WR 79.5%, PF 8.4!).
- **forex_rsi2 anomaly resolved in this table:** its 90d *closed* cohort has 66.4% of rows
  at exactly pnl_pct=0; the 403 measurable rows are WR 52.1% / PF 2.34 - i.e. the emitter
  itself is fine, the *measurement* is broken (S4 Q2 zero-cohort), and the 7,987 OPEN rows
  (7,897 >7d) are the closer's fault, not the strategy's. This is a REDUCE/keep-with-closer
  case, not a KILL.
- **P60 of rows in trading_picks 90d never close** (open% per row above): FOREX category
  alone is 27,147 rows/90d with 25,801 OPEN (95.0%).
- **2026-11-19 cluster:** forex_rsi2, etf_rsi2_pullback, etf_faber_tactical,
  etf_sector_momentum, cftc_cot all stop at 11-19 12:33/16:47 - one shared feed went dark
  6 days ago (see Stage 3).

### 1b. at_raw_picks (raw/shadow pipeline, 114k rows) - top emitters, last 90d

at_raw_picks closes normally (hourly stale sweep works here), so open% is low and WR/PF is real.

| strategy | n90 | n30 | OPEN | closed | won/lost | WR | gross W/L | PF | null/=0 | banned/stale hit | last emit |
|---|---|---|---|---|---|---|---|---|---|---|---|
| prediction_market_consensus | 3,914 | 1,048 | 0 | 3,914 | 1701/2152 | 44.1% | +4388/-3956 | 1.11 | 5/1 | 0/0 | 11-19 |
| forex_zscore_200d_fade | 3,424 | 691 | 4 | 3,420 | 958/1964 | **32.8%** | +507/-1003 | **0.51** | 127/277 | 0/0 | 11-23 |
| atr_percentile_gate_scanner | 2,600 | 644 | 0 | 2,600 | 952/1602 | 37.0% | +4228/-4661 | 0.92 | 4/42 | 0/0 | 11-19 |
| regime_mild_bear | 1,969 | 328 | 0 | 1,969 | 866/632 | 57.9% | +7752/-1871 | **4.14** | 117/341 | 0/0 | 11-21 |
| commodity_term_cot | 1,455 | 239 | 0 | 1,455 | 592/655 | 47.5% | +1130/-1054 | 1.07 | 6/201 | 0/0 | 11-19 |
| regime_accumulation | 1,402 | 166 | 0 | 1,402 | 459/745 | 38.1% | +1257/-4338 | 0.29 | 36/132 | 0/0 | 11-24 |
| luxalgo_confluence | 1,198 | 244 | 0 | 1,198 | 594/594 | 50.0% | +2306/-1749 | 1.32 | 0/1 | 0/0 | 11-19 |
| regime_strong_bear | 956 | 248 | 17 | 939 | 294/322 | 47.7% | +2377/-1170 | 2.03 | 63/258 | 0/0 | 11-25 |
| regime_mild_bull | 763 | 155 | 0 | 763 | 228/331 | 40.7% | +561/-1816 | 0.31 | 45/138 | 0/0 | 11-23 |
| commodity_momentum | 383 | 194 | 0 | 383 | 180/203 | 47.0% | +493/-387 | 1.28 | 0/0 | 0/0 | 11-19 |
| claude_ml_moderate_mut | 308 | 30 | 0 | 308 | 132/176 | 42.9% | +469/-544 | 0.86 | 0/0 | 0/0 | 11-13 |
| vix_regime_overlay | 258 | 75 | 8 | 250 | 69/124 | 35.7% | +154/-362 | 0.42 | 7/49 | 0/0 | 11-25 |
| rapid_momentum_filter_mut | 250 | 62 | 0 | 250 | 106/144 | 42.4% | +306/-350 | 0.87 | 0/0 | 0/0 | 11-18 |
| regime_crash | 208 | 152 | 37 | 171 | 13/53 | 19.7% | +67/-230 | 0.29 | 62/43 | 0/0 | 11-25 |
| futures_connors_rsi2 | 159 | 17 | 0 | 159 | 35/88 | 28.5% | +56/-144 | 0.39 | 0/36 | 0/0 | 11-17 |
| cta_golden_cross_200 | 159 | 25 | 0 | 159 | 35/78 | 31.0% | +29/-138 | 0.21 | 0/42 | 0/0 | 11-17 |
| quan_engine_swing | 123 | 6 | 0 | 123 | 35/88 | 28.5% | +155/-235 | 0.66 | 0/0 | 0/0 | 10-30 |
| high_trust_momentum | 119 | 0 | 0 | 119 | 65/50 | 56.5% | +196/-109 | 1.79 | 0/0 | 0/0 | **10-21** |
| claude_ml_conservative_mut | 64 | 4 | 0 | 64 | 24/40 | 37.5% | +48/-88 | 0.55 | 0/0 | 0/0 | 11-13 |
| A_amp_VolatilityRegimeSwitch_v0 | 32 | 3 | 0 | 32 | 8/23 | 25.8% | +9/-57 | 0.16 | 0/0 | 0/0 | 11-05 |


Note: `was_banned`/`was_stale` hits are 0/0 within 90d at strategy level here - the ban
flag banding S4 saw lives in older rows; the 74.7% `incubator_strategy` gate rejections all
happen *before* insert (at_filter_log) so they never appear in this table.

### 1d. Stage 1 classification (preliminary; refined in Stage 4)

- **DELETE-candidate -> "remove-from-cron" (owner may not delete code):**
  non_crypto_consensus (8,770 new OPEN/90d, 0 closed ever), short_dominant_engine
  (2,341/100% OPEN), the copy_pm_* polymarket-copy family (~2,500 rows/90d, all OPEN,
  no closer), futures_bb_mean_reversion (2,539 OPEN/90d, 1 close in 90d).
- **MUTE (stop emitting, keep history):** decided in Stage 4 after the FOREX/ETF deep dive;
  strongest candidate so far is forex_zscore_200d_fade (PF 0.51 / WR 32.8% on 2,922
  measurable at_raw_picks closes; WR 18.6% on 43 measurable trading_picks closes; 8,580
  OPEN rows).
- **REDUCE (narrow scope):** forex_rsi2_mean_reversion (best measurable large-emitter
  economics WR 52.1% PF 2.34 - but it emits ~7x what any closer can process and carries
  66.4% fake zeros); the etf_* cluster (each variant: ~150-350 rows, 97-100% OPEN, 1 or 0
  closes in 90d).
- **KEEP (demonstrated to close):** luxalgo_confluence (44.5% open, n=1,468 closed),
  regime_strong_bear (PF 2.03 at_raw) / regime_strong_bull, rapid_momentum_filter_mut
  (WR 58.1% PF 1.69 in trading_picks), the unlabeled '' cohort (WR 79.5%, PF 8.44).
- **Silent emitters (60h+, detailed in Stage 3):** the 2026-11-19 12:33 feed (etf_rsi2,
  etf_faber_tactical, etf_sector_momentum), forex_rsi2 + cftc_cot at 11-19 16:47,
  futures_connors_rsi2 11-18, at_raw (prediction_market_consensus / atr_percentile_gate /
  commodity_term_cot) 11-19, high_trust_momentum 10-21.


---

## Stage 2 - FOREX + ETF deep dive (the two FAIL classes)

### 2a. Class ledgers (measured)

`trading_picks` lifetime by category (all-time, not just 90d):

| class | rows | OPEN | closed | meas W/L | WR (meas) | PF (gains/losses) | zero-pnl closed | first/last emit |
|---|---|---|---|---|---|---|---|---|
| FOREX | 64,467 | **46,570 (72%)** | 17,897 | 8,580/7,490 | 52.8% | 1.21 | 1,782 | 2026-02-17 / live |
| ETF (category='ETF') | 1,047 | 640 | 407 | 177/160 | 52.6% | 1.51 | 66 | 2026-03-11 / live |
| ETF orphan (category='' - the etf_* family) | 2,632 | **2,477 (94%)** | 155 | 71/83 | 46.1% | 0.69 | 0 | 2026-02-20 / 11-19 |

FOREX alone is 47.6% of all `trading_picks` rows created in the last 90d
(27,147 of 57,025) and 48.5% of the 90d OPEN intake (25,801 of 53,221).

`at_pick_outcomes` (the metric-grade resolved ledger, `resolution_method`
TP_HIT/SL_HIT/TIME_EXPIRED) tells a much darker story than `trading_picks` - this is the
cohort family the money-ready audit's FAIL verdicts live in:

| strategy (asset_class) | n | W/L | WR | PF | zero-pnl rows |
|---|---|---|---|---|---|
| ig_contrarian_sentiment (FOREX) | 4,100 | 179/306 | 36.9% | 1.98 | 3,587 (87%) |
| non_crypto_consensus (FOREX) | 3,552 | 118/105 | 52.9% | 9.95 | 3,316 (93%) |
| myfxbook_retail_contrarian (FOREX) | 2,971 | 186/280 | 40.0% | 1.28 | 2,503 (84%) |
| **forex_rsi2_mean_reversion (FOREX)** | 2,852 | 437/660 | **39.8%** | **0.39** | 1,691 (59%) |
| forex_carry_momentum (FOREX) | 1,184 | 12/142 | 7.8% | 8.96* | 1,004 (85%) |
| cta_cross_asset_tsmom (FOREX) | 866 | 101/87 | 53.7% | 0.81 | 676 (78%) |
| forex_zscore_200d_fade (FOREX) | 65 | 1/1 | - | - | 61 (94%) |
| leveraged_etf_decay (ETF) | 43 | 0/0 | - | - | **43 (100%)** |
| etf_rsi2_pullback (ETF) | 37 | 2/1 | - | 24.5* | 34 (92%) |
| etf_faber_tactical (ETF) | 16 | 0/0 | - | - | 16 (100%) |
| etf_sector_momentum (ETF) | 15 | 0/0 | - | - | 15 (100%) |

\* PF distorted by one +428% feed-bug win (see `alpha_engine/production_scanner.py:1416-1425`,
which already documents `forex_carry_momentum n=1183 WR 1.0%` and
`forex_rsi2 n=2441 WR 12.7% PF 0.39` on this same cohort).

Note the three-way ledger disagreement for the SAME strategy: forex_rsi2 = PF 0.39
(at_pick_outcomes, n=2,852) vs PF 2.34 (trading_picks measurable, n=403)
vs PF ~2.4 (symbol-track "shadow", n=19). See 2d.

### 2b. Is FOREX unsalvageable, or dragged by 1-2 emitters?

Per source_system x strategy in `trading_picks`, last 90d:

| source_system / strategy | n90 | OPEN | closed | W/L | zero | verdict |
|---|---|---|---|---|---|---|
| multi_asset_copytrader / forex_rsi2 | 8,930 | 7,829 | 1,101 | 200/173 | **728 (66%)** | measurable WR 53.6% PF 2.34 - strategy possibly OK, measurement + closer broken |
| multi_asset_copytrader / forex_zscore_200d_fade | 6,555 | 6,539 | 16 | 2/14 | 0 | never closes; at_raw cohort says **WR 32.8% PF 0.51 (n=3,420)** |
| non_crypto_consensus / non_crypto_consensus | 6,441 | **6,441 (100%)** | 0 | - | - | pure backlog, zero measurement possible |
| forex_copy_trader / forex_zscore_200d_fade | 2,027 | 1,999 | 28 | 6/22 | 0 | WR 21.4% PF 0.47 |
| forex_copy_trader / forex_rsi2 | 256 | 158 | 98 | 10/20 | 68 | 69% zeros, meas WR 33% |
| combined_confidence_strategy / combined_confidence | 2,045 | 2,033 | 12 | 2/10 | 0 | WR 16.7% |
| regime_terminal / regime_accumulation..strong_bull (4 rows) | 618 | 598 | 43 | **34/9** | 0 | PF 1.23 - KEEP |
| fx_cot_extremes / fx_cot_extremes | 43 | 15 | 28 | 6/20 | 2 | PF 0.24 |
| alpha_engine_fast / alpha_engine_fast | 41 | 41 | 0 | - | - | no closes |

**Answer: the FOREX class is not uniformly dead - it is 2-3 emitters plus one measurement bug.**

- 21,986 of 27,147 FOREX rows/90d (81%) come from `multi_asset_copytrader`,
  `non_crypto_consensus` and `forex_copy_trader`. Stop those three from entering the DB
  funnel and the class's backlog cost collapses while `regime_terminal` FOREX (34/9 W/L),
  `fx_overnight_reversal` (8/4, PF 2.63) and the regime sleeves keep emitting.
- Class-level WR 52.8% / PF 1.21 in `trading_picks` vs WR ~32-40% / PF 0.39-0.66 in
  `at_pick_outcomes` is a cohort artifact, not a market verdict. `trading_picks` closes are
  dominated by the rsi2 zero-polluted subset (66-69% of rows exactly 0); `at_pick_outcomes`
  is dominated by the June-banned emitters (ig/myfxbook/carry, 84-93% zeros). Both
  ledgers are contaminated differently. Neither is decision-grade until S4 Q2 fix #3
  (stop writing 0-as-missing at `alpha_engine/outcome_resolver.py:2000 - 2005`) lands;
  `audit_trail/zero_pnl_detector.py` runs daily in `ab_analysis.yml:70` but only PRINTS
  the UPDATE (`zero_pnl_detector.py:145`), applying nothing.

### 2c. ETF: dead tail vs live core

- **Dead tail = `etf_all_strategies` (the category='' orphan cluster):** 2,632 rows
  lifetime, 2,477 OPEN, 155 closed; last emit **2026-11-19 12:33:44 (156h ago)**; 90d
  closed = 5 rows, **0 wins / 5 losses**. Its six strategies (etf_rsi2_pullback n=746,
  etf_faber_tactical 456, etf_sector_momentum 453, etf_dual_momentum 391,
  etf_sector_dual_momentum 141, etf_cross_sectional_momentum 89) all carry an EMPTY
  category, so they are invisible to every `category='ETF'` filter/gate while still
  inflating raw counts - the same class of bug flagged at
  `alpha_engine/mysql_trading_sync.py:79` and `:530`.
- **Live core = category='ETF':** 1,047 rows, closes normally (407 closed, WR 52.6%,
  PF 1.51) but is *small*. Component `leveraged_etf_decay` (247 rows/90d, 100% OPEN, 0
  closes; 43/43 zero-pnl in at_pick_outcomes) is a no-closer emitter with no measured
  history at all.
- **ETF's n=45 / WR 2.2 / PF 0.02 money-ready verdict is explained by `at_pick_outcomes`:**
  108+ of the class's rows there are zero-pnl-only (43+34+16+15 across four strategies,
  `forward_validated = 0` on every ETF row queried). ETF fails on *measurement emptiness
  + orphan labeling*, not on 45 honest trades.
- The `PROVEN_STRATEGIES` set (`alpha_engine/emitter_discipline.py:66-79`) explicitly
  lists etf_dual_momentum, etf_sector_momentum, etf_faber_tactical, etf_risk_parity_rotation,
  etf_trend_following - i.e. the ETF tail is *supposed* to be good. It is producing
  unusable rows because the sink is broken (empty category, no closer), not because the
  strategies are toxic. **REDUCE/REPAIR, not KILL, for that cluster.**

### 2d. Reconciling "forex_rsi2 shadow ~63% / PF 2.4 on n=19" with live emission

Not resolvable as a like-for-like A/B - and the reasons are themselves the finding:

1. **n=19 is a strategy-symbol track, not a cohort.** The dashboard's shadow/forward
   tracks are stamped point-in-time per (strategy,symbol):
   `audit_trail/dashboard_generator.py:16394` ("Leakage-free shadow metric: stamp
   sym_track_wr_pit / sym_track_total_pit") and `_build_strategy_symbol_track_stats`
   (:5895). n=19 cannot adjudicate a strategy whose ledgers hold 2,852 / 16,062 rows.
2. **The literal shadow resolver scores differently.** `alpha_engine/shadow_tracker.py`
   (writes `alpha_engine/data/shadow_blocked.json`, confirmed 500 records) scores blocked
   signals with a single `price_after_24h` sample plus boolean `would_have_hit_tp` /
   `would_have_hit_sl` flags (keys verified in the file): no intrabar ordering, no fees,
   no spread, no session filter, no hold-window. The live resolver orders TP/SL intrabar
   (`audit_trail/universal_pick_resolver.py::_check_tp_sl_intrabar`, whose
   `_ENTRY_ANCHORED` A/B is pre-registered with explicit flip thresholds in
   `tools/shadow_diff_entry_anchored.py:14-22` precisely because entry-anchoring flips
   outcomes).
3. **Entry vs exit conditions are governed in different places.** Signal generation:
   `alpha_engine/forex_strategies.py:360-445` - RSI2<5, RRSI2<10, stoch<20, above 200
   SMA, RSI14>=25 - with `TP/SL = _forex_tp_sl(tp_mult=1.5, sl_mult=1.0)`, `RR>=1.0`
   reject, `max_hold_bars=5` (daily bars => 5 sessions ~= 120h), `confidence` capped by
   `_forex_conf_cap(0.70,...)`, wrapped in `_session_guard` (:1105 session-hour filter).
   The *exit* clock is instead `tools/pick_hold_windows.py:13-31` = 72h for FOREX. The
   two disagree (120h vs 72h) and neither is enforced by a running closer for
   `trading_picks` (S4 Q1).
4. **No cost model anywhere in the shadow path**: `grep -i "spread|slippage|fee|commission"`
   over `tools/shadow_diff_entry_anchored.py` and `tools/new_strategies_shadow_tracker.py`
   returns 0 hits. `trading_picks.execution_slippage_pct` exists in schema but is not part
   of these WR/PF computations.

**Conclusion:** the live-vs-shadow divergence for forex_rsi2 is a measurement-pipeline
artifact, not evidence of tradable edge. Three cohorts give PF 0.39 (n=2,852), PF 2.34
(n=403 measurable, with 66% zeros excluded), PF 2.4 (n=19). **Do not keep it emitting on
the strength of the n=19 figure, and do not kill it purely on the class verdict -
REDUCE it and repair its measurement.** Note it is already *soft*-killed at feed level in
two places that evidently do not cover this path: `alpha_engine/fx_kill_switch.py`
`_KNOWN_TOXIC_FOREX_STRATEGIES` contains `forex_rsi2_mean_reversion`, and
`alpha_engine/emitter_whitelist.py` `HARDCODED_TOXIC_PAIRS` contains
`("FOREX","forex_rsi2_mean_reversion")` - yet it produced 9,191 rows in 90d. Root cause:
those gates run at *scanner intake / active-pick* level (and `EMITTER_WHITELIST_ENFORCE`
defaults off - shadow mode, see `emitter_whitelist.py:10-13`), while the row still enters
`trading_picks` through `alpha_engine/mysql_trading_sync.py::sync()`, whose only
class-level gate is `FOREX_HARD_DISABLE` (default OFF,
`alpha_engine/config.py:418-423`) plus the sleeve/CLEAN_INGEST gates at
`mysql_trading_sync.py:945-990`. **There is no per-strategy blocklist in that funnel.**

---

## Stage 3 - Silent + zombie check

Method: (a) `gh workflow list --limit 500 --json name,path,state` (read-only) for
scheduled-workflow state; (b) `gh run list --workflow=<file> --limit 1` for last-run
conclusion; (c) DB `MAX(created_at)` per source_system / per strategy (measured above).

### 3a. Workflow disable state - NOTHING is disabled

```
total workflows: 380
Counter({'active': 380})   # not one disabled_manually / disabled_inactivity
```

**No emitter is "disabled_manually" at the GitHub level**, so nothing is currently sitting
in a silently-disabled state that could be re-enabled unnoticed - equally, "the cron is
still there" does NOT mean "the emitter is alive" (3b). Removal-from-cron would have to be
done from the repo file or the GitHub UI; if the owner takes any KILL-cron action below,
the disabled state must be tracked outside this report (GitHub does not record it in YAML).

### 3b. Last-run state of the emitter workflows that matter (UTC, 2026-11-26 ~01:15)

| workflow | cron | last run | result | DB evidence |
|---|---|---|---|---|
| multi-asset-scanner.yml (`multi_asset_copytrader`) | `14/30 * * * *` | 11-26 00:53 | success | last emit 11-26 00:54 - ALIVE, 23,359 rows/90d |
| alpha-engine-live.yml | `25 */2 * * *` | 11-26 00:43 | in_progress | alive |
| alpha-engine-fast.yml (`alpha_engine_fast`) | `3,33 * * * *` | 11-26 00:33 | success | alive, 2,268 rows/90d, 100% OPEN |
| regime-terminal.yml (`regime_terminal`) | `36,6 * * * *` | 11-26 00:50 | success | alive; 3,750 rows/90d of which only 302 closed |
| specialized-scanners.yml (`short_dominant_engine`) | `32 1,5,9,13,17,21 * * *` | 11-25 21:35 | success | alive, 2,341 rows/90d 100% OPEN |
| copy-trader-intelligence.yml | `53,38 * * * *` | 11-26 00:57 | pending | alive |
| alpha-engine-etf.yml (`leveraged_etf_decay`) | `25 */6 * * *` | 11-26 00:45 | success | alive, 247 rows/90d 100% OPEN |
| **etf-agent.yml (ETF rotation family)** | `22 14 * * 1-5` | **11-25 14:28** | **success** | **but `etf_all_strategies` dead since 11-19 12:33 (156h)** - cron green, output dark |
| cftc-cot-refresh.yml (`cftc_socrata`) | `35 12 * * 6` (weekly) | 11-21 12:37 | success (weekly cadence) | **`cftc_socrata` dead since 11-19 16:47 (152h)** - 3,079 OPEN pinned; the 11-21 run emitted nothing |
| audit-dashboard.yml (`non_crypto_consensus` step :450-451) | `10 */3 * * *` | n/a | non-fatal step (`|| echo ...`) | alive: source emitting 4,362 rows/30d |
| ml-strategy-reviver.yml (`ml_strategy_reviver`) | `2 */2 * * *` | 11-26 00:32 | success | **source silent 638h (since 10-30)** - cron green, output dark |
| bond-agent.yml / etf-bond-scanner.yml (`bond_scanner`) | `29 13 * * 1-5` etc. | 11-25 14:05/14:34 | success | source silent 58h (since 11-23 14:39) |
| enhanced-ml-crypto.yml (`ml_crypto_predictor`) | `38 2 * * *` | 11-26 00:50 | success | **source silent 3,705h (since 06-24)** - cron green, output dark |
| signal-engine.yml | `39,9 * * * *` | 11-26 00:51 | success | previous emits to kimi_riseoftheclaw stopped 11-18 (193h) |

### 3c. Silent emitters in trading_picks - >48h since last row, with zombies still parked

| source_system | total rows | last emit | silent | rows OPEN now (cost) | workflow status |
|---|---|---|---|---|---|
| cta_replicator | 5,606 | 2026-06-12 | **3,987h (5.5 mo)** | **1,106** | already HARD_KILL + BLOCKED (drifted intent: emit stopped, backlog remains) |
| cftc_socrata | 3,122 | 2026-11-19 | 152h | **3,087** | cron weekly, runs green, no rows since 11-19 |
| etf_all_strategies | 2,720 | 2026-11-19 | 156h | **2,448** | cron daily green (etf-agent), output dark |
| ml_crypto_predictor | 2,311 | 2026-06-24 | 3,705h | **482** | cron green, output dark |
| polymarket_whale_tracker | 1,582 | 2026-05-25 | 4,420h | 0 | **no workflow file references it - dead path** |
| ml_strategy_reviver | 835 | 2026-10-30 | 638h | **352** | cron every 2h green, output dark |
| copy_trader_intel | 538 | 2026-06-03 | 4,212h | 4 | dead path (superseded) |
| bond_scanner | 406 | 2026-11-23 | 58h | **340** | cron daily weekdays green |
| signal_validation | 404 | 2026-06-08 | 4,101h | **398** | **no workflow references it - dead path** |
| polymarket_momentum | 402 | 2026-05-22 | 4,494h | 0 | dead path |
| multi_asset_cot | 387 | 2026-11-23 | 68h | **250** | in alpha-engine-live/ci-tests |
| ml_strategy_reviver_inverse | 365 | 2026-07-11 | 3,309h | **125** | cron green, output dark |
| prediction_market_consensus | 316 | 2026-05-04 | 4,921h | 0 | HARD_KILL already |
| battleground_luxalgo | 301 | 2026-06-12 | 3,993h | 42 | HARD_KILL already |
| coinglass_sentiment | 219 | 2026-06-25 | 3,692h | 6 | dead path |
| kimi_riseoftheclaw_equity_breakout | 175 | 2026-11-18 | 193h | **16** | signal-engine green |
| kimi_signal_tracking | 173 | 2026-03-29 | 5,809h | 0 | HARD_KILL already |
| battleground | 152 | 2026-03-28 | 5,809h | 0 | dead path |

**Zombies owed by silents ~ 8,656 OPEN rows** (sum of the OPEN column above) - i.e. ~8.7%
of the 99,345-row backlog is parked behind sources that are no longer producing anything.

### 3d. Silent *strategies* inside still-alive sources (the sneakier case)

Live source, dead strategy - these need a strategy-level mute, not a cron kill:

| source / strategy | total | last emit | silent | OPEN pinned |
|---|---|---|---|---|
| multi_asset_copytrader / **forex_rsi2_mean_reversion** | 16,062 | 11-19 16:47 | 152h | **11,558** |
| multi_asset_copytrader / futures_connors_rsi2 | 3,273 | 11-18 04:47 | 188h | **2,773** |
| cftc_socrata / cftc_cot_commercial_signal | 3,114 | 11-19 16:47 | 152h | **3,079** |
| multi_asset_copytrader / ig_contrarian_sentiment | 4,680 | 06-12 | 3,987h | 395 |
| multi_asset_copytrader / myfxbook_retail_contrarian | 3,034 | 06-12 | 3,987h | 103 |
| multi_asset_copytrader / futures_momentum | 2,586 | 06-12 | 3,987h | 204 |
| multi_asset_copytrader / stocks_rsi2_pullback | 2,041 | 06-12 | 3,987h | 466 |
| multi_asset_copytrader / forex_carry_momentum | 1,257 | 06-12 | 3,987h | 80 |
| prediction_market_agents / prediction_market_consensus | 3,000 | 06-12 | 3,987h | 251 |
| cta_replicator / cta_cross_asset_tsmom + cta_commodity_momentum_term + cta_golden_cross_200 | 5,559 | 06-12 | 3,987h | **1,106** |
| etf_all_strategies / etf_rsi2_pullback + faber + sector + dual (4) | 2,046 | 11-19 12:33 | 156h | **1,836** |
| regime_terminal / regime_mild_bull | 1,288 | 11-23 18:32 | 54h | 1,172 |
| bond_scanner / bond_yield_momentum | 321 | 11-20 14:05 | 131h | 292 |
| forex_copy_trader / forex_rsi2_mean_reversion | 873 | 11-19 12:23 | 156h | 418 |

Note the **2026-06-12 21:36 clustered stop** (six strategies, 3,987h) - that is the mass
HARD_KILL event; those strategies leave open positions behind every time and nothing
reaps them (S4 Q1 root cause 1-3). The **2026-11-18/19 cluster** (forex_rsi2,
futures_connors_rsi2, cftc, etf_all_strategies, bond_yield_momentum) is a second, newer
shared stop whose trigger was NOT located in code during this run - worth a follow-up
because it spans three independent producers simultaneously (market-data gate? a shared
`at_raw`/price-fetch failure on 11-19?).

### 3e. Zombie check: workflows with cron but no reachable output

- **Dead paths (no workflow references the module):** `polymarket_whale_tracker`,
  `signal_validation`, `polymarket_momentum`, `coinglass_sentiment`, `battleground`,
  `copy_trader_intel` (superseded) - 3,297 lifetime rows of which 408 still OPEN. Their crons
  do not exist, so "nothing resurrects silently" holds **only if the JSON source files
  they wrote are also removed/emptied** - each may still be listed in `JSON_PICK_SOURCES`
  (`audit_trail/dashboard_generator.py:3718+`, 66 sources) and will be read as long as the
  file exists.
- **Green-cron-but-dark (the dangerous category):** etf-agent, ml-strategy-reviver,
  enhanced-ml-crypto, bond-scanner, cftc-cot-refresh all report `success` while their
  `trading_picks` output stopped 58h-3,705h ago. Muting decisions must not assume "cron
  alive == emitter alive".
- **HARD_KILL already-effective sources** (cta_replicator, prediction_market_consensus,
  kimi_signal_tracking, battleground_luxalgo, ig/myfxbook/carry family) confirm the
  intake-level kill mechanism works *where wired* - but every one of them still parks an
  OPEN residue (8,656 rows total) because no reaper runs (S4 Q1).

---

## Stage 4 - Ranked emitter proposal (NOT executed - owner decides)

Legend for **where it hurts**:
- **(a)** dashboard-visible surface = JSON source read by `/audit` via
  `JSON_PICK_SOURCES` (`audit_trail/dashboard_generator.py:3718+`, 66 sources) or a panel
  fed from `trading_picks`
- **(b)** DB backlog = rows landing in `trading_picks` / `at_local_picks` (the 99,345 +
  33,515 OPEN pile; every row costs resolver time now and future audit cost later)
- **(c)** silent/dead = cron or source with no output (nothing to mute in the DB; the
  cost is its parked OPEN residue + the false "cron is green" signal)

**Mechanics already in-repo (reuse, do not invent):** the write funnel every JSON-source
pick crosses is `alpha_engine/mysql_trading_sync.py::sync()` (`mysql_trading_sync.py:863`,
row loop `:945-990`) and it currently gates ONLY `FOREX_HARD_DISABLE`
(`alpha_engine/config.py:418-423`, default OFF), the INVERSE_ML sleeve gate and the
opt-in `CLEAN_INGEST_V2_ENFORCE`. Per-strategy blocking exists at *read/intake* level in
five independent places - `alpha_engine/strategy_blocklist.py` (via
`feed_hygiene.py:233 is_blocked_pick`), `alpha_engine/emitter_discipline.HARD_KILL_STRATEGIES`
(wired at `production_scanner.py:4127`), `alpha_engine/fx_kill_switch.py`,
`alpha_engine/emitter_whitelist.HARDCODED_TOXIC_PAIRS` (enforce flag default off), and
`audit_trail/quality_gates.py` BLOCKED_* sets (`:1941`, `:2184`, `:2584`, `:2600`) -
**none of them runs inside the DB write loop.** That asymmetry is why
`forex_rsi2_mean_reversion` is on three kill lists and still produced 9,191 rows in 90d,
and why nothing that is muted on the dashboard stops adding to the 99,345-row backlog.

| # | emitter (source_system / strategy) | class | evidence (n, WR, PF, OPEN cost, staleness) | recommendation | blast radius if muted | risk | owner-decision |
|---|---|---|---|---|---|---|---|
| 1 | **multi_asset_copytrader** (forex_rsi2, forex_zscore, tv_community_consensus + June-killed family) | FOREX-dominant | 23,359 rows/90d = **24.8% of all `trading_picks` inflow**; 22,238 OPEN/90d; forex_zscore sleeve at_raw PF **0.51** (n=3,420, WR 32.8%); forex_rsi2 outcomes PF **0.39** (n=2,852 zeros 59%); forex_rsi2 alone pins **11,558 OPEN**; already in `HARDCODED_TOXIC_PAIRS` + `BANNED_SOURCES` yet bypasses them (scraper `copy_trader_intel/multi_asset_copytrader_scraper.py` writes JSON straight to disk); alive (last run 11-26 00:53, cron `14/30 * * * *`) | **MUTE at DB funnel** (add to sync-time denylist) **+ REDUCE source scope** (drop FOREX sleeve, keep equity/futures/commodity sleeves until measured). Optional stronger variant: KILL-cron on `multi-asset-scanner.yml` | (a) if funnel-only: NONE - the 4 JSON files (`multi_asset_picks`, `forex_copytrader_picks`, `stocks_copytrader_picks`, `commodity_copytrader_picks`, `dashboard_generator.py:3937-3957`) keep updating so cards stay live; (b) `trading_picks` inflow -23.4k rows/90d (largest single cut). KILL-cron variant freezes those 4 panels instead | Low (funnel) / Medium (cron) | **Y** |
| 2 | **non_crypto_consensus** (source + strategy) | FOREX 90d 6,441 / mixed | **8,770 rows/90d, 100% OPEN, 0 closed ever**, 8,114 already >7d; at_raw history 3,552 rows but **93% zero-pnl** (WR 52.9% is computed on 223 rows); step `audit-dashboard.yml:450-451` runs non-fatally every `10 */3 * * *` | **MUTE (DB funnel)** until a closer exists; keep emitting JSON for the consensus panel (a) | (a) none if funnel-only; (b) **-8,770 rows/90d (15.4%)**, removes the #2 backlog machine; dashboard consensus cards unaffected | Low | **Y** |
| 3 | **forex_zscore_200d_fade** (strategy, in sources 1 + forex_copy_trader) | FOREX | trading_picks 90d: 8,623 rows, **99.5% OPEN** (8,580), 43 closed -> meas WR 18.6%, PF 1.08; **at_raw_picks: WR 32.8%, PF 0.51, n=3,420** -> the single worst statistically-validated emitter; not on any kill list; last emit live (11-26 00:54) | **MUTE (strategy)** - both at funnel and at `emitter_discipline.HARD_KILL_STRATEGIES` (mirrors the treatment given `forex_carry_momentum`) | (a) it does not have its own JSON source (rides multi_asset/forex_copy_trader files) so panels keep the parent source's other picks; (b) -8,582 FOREX rows/90d (6,555 via multi_asset_copytrader + 2,027 via forex_copy_trader) | Low-Medium: FOREX class n-build slows, but its closed cohort is worthless (PF 0.51) so it cannot legitimately carry the class anyway | **Y** |
| 4 | **short_dominant_engine** (source+strategy) + **futures_bb_mean_reversion**, **stocks_ema_golden_cross**, **smart_money_accumulation**, **funding_rate_arb** (family) | multi | 100%/99.96% OPEN over 90d with **0/1/0/1/0 closes** (2,341 + 2,540 + 1,316 + 2,272 + 144 = **8,613 rows/90d, 8,611 OPEN**); all alive (jobs green) so this is pure backlog burn, not silence | **MUTE (DB funnel) / REDUCE emission** until S4 action #1 (`--table trading_picks` on the hourly sweep) is live; then re-measure before restoring | (a) `short_dominant_engine` has no JSON source of record in our sample (comes via specialized-scanners), fastest-reverting panels unaffected; (b) -8.6k rows/90d of which ~100% is zombie-eligible | Low; sole risk is removing raw supply that is currently *mislabeled* supply anyway | **Y** |
| 5 | **etf_all_strategies / etf_* family** (etf_rsi2_pullback, etf_faber_tactical, etf_sector_momentum, etf_dual_momentum, etf_sector_dual_momentum, etf_cross_sectional_momentum) | ETF-orphan (category='') | 2,632 rows lifetime, **2,477 OPEN (94%)**, 155 closed; 90d closes = **5 rows, 0W/5L**; last emit **156h ago** while `etf-agent.yml` reports SUCCESS daily; category='' hides them from every `category='ETF'` gate; at_pick_outcomes: 79 of 88 ETF rows there are pure zero-pnl; BUT these 5 strategies are listed in `emitter_discipline.PROVEN_STRATEGIES:66-79` | **REDUCE + REPAIR**, not kill: (i) do not re-point the dark feed until category='' is stamped `'ETF'`; (ii) keep the 5 PROVEN strategies in paper/shadow; (iii) drop the two non-proven variants (etf_risk_parity_rotation n=31 9d-old, etf_trend_following) from DB insert until measured; KILL-cron is NOT recommended | (a) `active_picks_etf.json` + ETF rows on the dashboard already starve (5 closes/90d) - muting changes little; (b) stops 1,164 rows/90d + 1,836 already-parked OPEN becoming unreapable | Medium: if `category` is fixed instead of mutating, ETF's n-build resumes quickly (this is the cheapest path to un-failing ETF) | **Y** |
| 6 | **leveraged_etf_decay** (source+strategy) | ETF | 247 rows/90d, **100% OPEN, 0 closes**; at_pick_outcomes **43/43 rows = 100% zero-pnl**, forward_validated 0; alive (alpha-engine-etf, 11-26 00:45) | **MUTE (DB funnel)** with an explicit re-enable condition: re-enable when either a closer resolves a first cohort or a real n>=20 measured history exists | (a) `active_picks_etf.json` (also feeds `alpha_engine/etf_scanner.py:89` merge) keeps flowing - panel unaffected; (b) -247 rows/90d | Low | **Y** |
| 7 | **copy_trader_polymarket** + `copy_pm_*` strategies (`copy_pm_pm_f705fa04`, `copy_pm_pm_06dc5182`, `copy_pm_tokor`, `copy_pm_getbipped`, `copy_pm_sharky6999`, `copy_pm_eager47259`, `copy_pm_cleancoinflip`, `copy_pm_jnstrtprdctnmrkts`, `copy_pm_egozic86`) + `pm_macro_expansion` | CRYPTO / prediction-market | source 3,700 rows/90d (100% OPEN, 0 closes), of which ~2,634 are the copy_pm_* clones (all 100% OPEN), + 358 `pm_macro_expansion` = ~4,058 rows/90d, some 80+ days stale (`copy_pm_jnstrtprdctnmrkts` last emit 2026-09-06, 113 rows all OPEN); alive (cron every 30 min) | **REDUCE** (cap to top-N / paper-only sleeve) rather than kill: these are paper-only and harmless to live money, but they are **(b)-class cost** - they inflate raw counts and the 99k pile while never closing | (a) polymarket panel keeps history if funnel-only mute; (b) -4.3k rows/90d of pure OPEN | Low. Keep them separate from "harmless shadow" - they are harmless *to P&L* but costly *to the funnel* | **Y** |
| 8 | **cftc_socrata / cftc_cot_commercial_signal** | COMMODITY/FOREX (COT) | 1,572 rows/90d, **1,564 >7d**, 3,087 OPEN parked; **silent 152h** though `cftc-cot-refresh.yml` ran SUCCESS 11-21 12:37 (weekly `35 12 * * 6`); 90d closed = 2; historically n=72 (below the n=100 floor) and 20 NULL/0-polluted (S4) | **KEEP the cron** (weekly, cheap, data-source legit) + **do not re-expand emission until the 11-19 stop is diagnosed**; the action item is reaping its 3,087 OPEN (S4 closer fix), not muting | (a) COT panel/edge reports keep their history; (b) no new rows while dark; reap path needs S4 #1 | Low; flag: the 11-21 green run producing zero rows is a **telemetry discrepancy** to chase, not a reason to kill | **Y** |
| 9 | **Dead paths**: `polymarket_whale_tracker`, `signal_validation`, `polymarket_momentum`, `coinglass_sentiment`, `battleground`, `copy_trader_intel` + **green-cron-dark**: `ml_crypto_predictor`, `ml_strategy_reviver`, `ml_strategy_reviver_inverse` | mixed | dead paths: 3,297 lifetime rows, **408 OPEN**, no workflow references the modules; green-cron-dark: 3,511 rows, **959 OPEN**, silent 638h/3,705h/3,309h while `ml-strategy-reviver.yml` and `enhanced-ml-crypto.yml` run SUCCESS | **KILL-cron-equivalent = remove from `JSON_PICK_SOURCES` + stop treating them as live** (there is no cron left to kill for the first group); for green-cron-dark: **investigate then MUTE** - a SUCCESS run that emits nothing is worse than a failed run because dashboards assume freshness | (a) only the JSON files they still write; verify each has no live panel before delisting (66-source list, `dashboard_generator.py:3718+`) - any panel that still reads them goes empty, which is truthful; (b) 1,367 zombie OPEN become reapable once removed from "active" mental model | Medium: delisting silently can hide a regression that is actually a bug; pair with one-line "dead since <date>" notes in the source list | **Y** |
| 10 | **bond_scanner / bond_yield_momentum** | BOND | 179 rows/90d, 157 OPEN, silent 58h; strategy closed 90d = **0W/8L, PF 0.00, -59.56 gross**; bonds are the class where high-alert rolling-WR drops were flagged; workflows `bond-agent.yml` / `etf-bond-scanner.yml` green 11-25 | **KEEP (monitor)** - n=8 is under any kill threshold (`fx_kill_switch`-style rules need 15-20 trades); do not promote to tier 2/3 | (a) bond panel + BOND class n-building stops if muted - and BOND has only 67 rows in the clean ledger already | Low but self-inflicted: muting here destroys the class's only live supply | **Y** |
| 11 | **regime_terminal** (regime_mild_bear/strong_bear/accumulation/...) | multi incl. FOREX+ETF | FOREX sleeve **34W/9L** in 90d (PF 1.23), at_raw regime_mild_bear PF 4.14 (n=1,969); closes 302/3,750 = genuine resolver throughput; alive | **KEEP** | n/a | - | **Y** |
| 12 | **luxalgo_confluence / luxalgo_filters** | multi | 2,643 rows/90d, closes 1,468 (44.5% OPEN), WR 42.6%, PF 1.096, at_raw PF 1.32 (n=1,198); the only large emitter whose close ratio is healthy | **KEEP** (best evidence that the pipeline can work when the closer runs for it) | n/a | - | **Y** |
| 13 | **forex_rsi2_mean_reversion** (in multi_asset + forex_copy_trader) | FOREX | 9,191 rows/90d (7,987 OPEN) but measurable cohort WR 52.1% / PF 2.34; outcomes-ledger PF 0.39 (n=2,852); shadow n=19 PF 2.4; on 3 kill lists but none apply to its path; silent 152h since 11-19; `execution_slippage_pct`/spread never modeled | **REDUCE + REPAIR MEASUREMENT** (not KILL, not keep-as-is): stop the FOREX sleeve now (rows #1/#3 above already stop it), leave the code, fix zero-pnl writes (S4 Q2 #3) and entry-vs-exit hold mismatch (`forex_strategies.py:400 max_hold_bars=5` vs `pick_hold_windows.py:72h`), then re-decide with a repaired ledger. Explicitly: **do not re-enable on the n=19 shadow number** | (a) the FOREX cards already mostly show other sources; (b) bundled into rows 1+3 | Medium: if the repaired ledger later shows PF>1.5, re-enable is a config flip (silently reversible) - asymmetric upside | **Y** |
| 14 | **alpha_engine_fast**, **combined_confidence_strategy** | EQUITY/CRYPTO avg | 2,268 + 2,773 rows/90d at **100% / 99.5% OPEN**, 0-14 closes; both alive | **REDUCE** (cap daily insert volume; keep JSON emission for their panels) pending the closer fix | (a) `active_picks_fast.json` panel unaffected if funnel-only; (b) -5.0k rows/90d | Low; risk is symmetric (fast sleeve is a money-ready candidate, so cap not kill) | **Y** |
| 15 | Unlabeled '' cohort (266 rows/90d, **WR 79.5%, PF 8.44**) | mixed | best measured cohort in the table, but `strategy` is empty -> invisible to every per-strategy gate and could be silently muting ITSELF from tier flooring | **KEEP + LABEL** (stamp source/strategy on insert) | n/a | Low | **Y** |

### Class-level switches kept on the table (blunt instruments)

| switch | what it does | when it is the right call | risk |
|---|---|---|---|
| `FOREX_HARD_DISABLE=1` | blocks ALL FOREX at the DB funnel (`mysql_trading_sync.py:959`), scanner (`scanner.py:2606`) and risk validator (`risk_regime_validator.py:304`) | only if the owner accepts FOREX class elimination: today FOREX = 47.6% of inflow and includes the 2 keepers (regime sleeves, fx_overnight_reversal) | High blast radius on (a) panels and BOND/ETF-adjacent cross-class logic; not reversible per-strategy |
| `EMITTER_WHITELIST_ENFORCE=1` | switches `emitter_whitelist` from shadow to reject mode for all `pf_registry`-derived toxic pairs | catches emitters we did not personally enumerate (incl. copy_pm_* clones) in one flag | Medium: default-off exists for a reason - a stale/empty registry would reject everything; audit `pf_registry.json` freshness first |
| `CLEAN_INGEST_V2_ENFORCE=1` | already present in the same funnel (opt-in) | use as the *labeling* enforcement (drops implausible rows) rather than as a mute | Low-medium |

### Top 5 safest high-impact actions (all owner-decision = YES)

1. **Add a per-strategy/source denylist check inside `mysql_trading_sync.sync()`'s row loop
   (`alpha_engine/mysql_trading_sync.py:945-990`), reusing the EXISTING
   `strategy_blocklist.is_blocked_pick` + `quality_gates.BLOCKED_STRATEGY_*` sets.**
   Biggest structural win: MUTE finally reaches the backlog. Dashboard (a) surfaces keep
   reading JSON, so rows 1/2/3/4/6/14 above mute without a single panel going dark;
   blast radius is (b) only, exactly where it is wanted. *(Y)*
2. **MUTE the three biggest backlog machines at that funnel: `multi_asset_copytrader`
   FOREX sleeve + `non_crypto_consensus` + `forex_copy_trader`** - 23,359 + 8,770
   (first two = **56.3% of all 90d `trading_picks` inflow**) and 34,457 rows together
   (**60.4%**), i.e. ~31k of the OPEN intake, from emitters that are already blocked on
   paper but not in practice. `forex_zscore_200d_fade` alone accounts for 8,582 of those
   rows across the two FOREX sources. *(Y)*
3. **Reap, then delist, the (c) dead emitters:** the 18 silent sources hold **8,656 OPEN
   rows today**; first land S4's closer fix (hourly sweep `--table trading_picks` + daily
   resolver apply), then remove the 6 workflow-less sources from `JSON_PICK_SOURCES` so
   they cannot resurrect as stale panels. Never delete their history rows. *(Y)*
4. **Repair instead of killing the ETF orphan cluster:** stamp `category='ETF'` on the
   `etf_*` family (they are already `PROVEN_STRATEGIES`), then let `etf_all_strategies`
   resume; keep `leveraged_etf_decay` muted until it has >=20 measurable closes. This is
   the cheapest route to un-failing the ETF class (currently n=45, WR 2.2, PF 0.02 purely
   from 100%-zero rows). *(Y)*
5. **Diagnose the 2026-11-18/19 silent cluster before any FOREX re-enable**
   (forex_rsi2, futures_connors_rsi2, cftc_socrata, etf_all_strategies, bond_yield_momentum
   all stop within ~28h of each other across 3 independent producers) - then keep
   forex_rsi2 marked REDUCE-REPAIR, and promote `luxalgo_confluence` / `regime_*` as the
   KEEP template for what a healthy emitter looks like (measured: closes 40-50% of what it
   emits, PF > 1). *(Y)*

### Explicit non-actions

- **No history deleted anywhere.** All recommendations are "stop emitting" / "reap OPEN" /
  "relabel"; `trading_picks`, `at_raw_picks`, `at_pick_outcomes` rows stay.
- **No code changed** in this run (report file only), no cron/workflow touched, no DB
  mutation.
- **`smart_picks_engine.py` and `check_active_picks.py` were NOT run.**

---

## Method / appendix

- SQL: strictly SELECT/SHOW, one connection per statement, 15s connect/read timeouts,
  sequential; a local guard script additionally rejects any statement that does not start
  with SELECT/SHOW/EXPLAIN or contains DML/DDL keywords. **25 statements executed**
  (11 schema/SHOW probes, 14 aggregates) against `ejaguiar1_stocks` - within the <=30
  budget. No writes; no retries that widen timeouts (two GROUP BYs were re-scoped instead).
- GitHub reads: `gh workflow list --json ... state` (380 rows) and
  `gh run list --workflow=<file> --limit 1` for 16 workflows - read-only.
- Time base: DB `NOW()` is UTC (max `created_at` 2026-11-26 00:54 = 19:54 EST on
  2026-11-25 local). "silent" hours are therefore UTC-to-UTC.
- Files touched: this report only.
- Known limits / caveats: (1) local JSON file mtimes in this checkout reflect the last
  git sync (mostly 2026-11-23), NOT production update times - production freshness was
  taken from DB `MAX(created_at)` and workflow run timestamps instead; (2) the "shadow
  ~63%/PF 2.4 on n=19" figure is carried from the task brief - its exact artifact file
  could not be pinned to a single file in this checkout (three candidate mechanisms
  documented in 2d), so it is treated as an unreproducible input rather than re-verified;
  (3) `at_local_picks` (76M rows) was only sampled via its `idx_status` path for OPEN
  counts; (4) workflow *run* results are a 1-run sample per workflow, not a 30-day
  history; (5) FOREX class lifetime ledger includes the June-banned emitters, so its
  52.8%/1.21 headline is not a clean-eligible number - both raw and clean views are shown
  in 2a/2b for exactly that reason.
