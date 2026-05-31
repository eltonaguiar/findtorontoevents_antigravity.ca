# Plan — /money-maker-readyv2 FOREX (Phase 10b)

Date: 2026-05-31  
Author: peer Claude (Opus 4.7)  
Class: FOREX (categories union: `'forex'`)

## Data sources pulled
1. Live `trading_picks` aggregations (90d + all-time) keyed by `source_system`, `strategy`, `symbol` — pulled via `pymysql` against `ejaguiar1_stocks` at 2026-05-31 ~06:30Z.
2. `audit_dashboard/data/money_ready_verdict.json` (generated 2026-05-31T01:57:16Z) → `classes.FOREX`.
3. `reports/deep_dive_FOREX_2026-05-31.md` — root-cause autopsy.
4. `reports/CYCLE_17_FOREX_BOND_BREAKTHROUGH_2026-05-29.md` — backtest evidence for `rsi_mr` (USDCHF 4.28 / EURUSD 2.46 / GBPUSD 2.40 all Tier 1).
5. Phase-3 MC watchlist: `fx_smart_carry_trade_momentum` P(T2@n=100)=64%, P(T1@n=100)=17%.

## Steps executed
1. Aggregated FOREX (lowercase) over 90d → 1,531 closed, 21 wins (raw status='WON' only), 1,379 losses, **but** `status='TP_HIT'` adds 904 rows and `'TIME_EXIT'` adds 11,601 rows. PF inflation in earlier reports came from 6 mislabeled `TP_HIT` rows with absurd exit_prices (CADJPY exit=611 from entry=115; USDJPY exit=1.358 from entry=158 — that's a EURUSD-range value).
2. Per-strategy ranking (closed-rows desc): `forex_rsi2_mean_reversion` (n=774, WR=40.6%, PF=0.255), `ig_contrarian_sentiment` (n=520, WR=34.8%, PF=1.97), `myfxbook_retail_contrarian` (n=479, WR=39.5%, PF=1.28), `cta_cross_asset_tsmom` (n=189, WR=53.4%, PF=3.57), `forex_carry_momentum` (n=178, WR=5%, PF=5.06 — one huge fake winner), `fx_smart_carry_trade_momentum` (MC candidate, n=56, WR=37.5%, PF=0.82).
3. Verdict cohort (policy-clean-net): n=29, WR=27.59%, PF=0.035, MDD=81%, expectancy=-4.58%. INSUFFICIENT_DATA on every gate.
4. Cross-checked against Cycle 17 (2026-05-29) which showed `rsi_mr` Tier 1 on USDCHF/EURUSD/GBPUSD in backtest — yet live `forex_rsi2_mean_reversion` is PF=0.255. **Backtest vs live divergence is the headline finding.** Likely cause: backtest used different RSI threshold / hold-period / TP-SL config than the live emitter. Mutate-before-kill applies.

## Output written
- `reports/peer_claude-phase10b-money-maker-FOREX_plan_2026-05-31.md` (this file)
- `reports/peer_claude-phase10b-money-maker-FOREX_result_2026-05-31.md` (the action plan)
