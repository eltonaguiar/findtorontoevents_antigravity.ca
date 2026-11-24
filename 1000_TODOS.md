# 1000-TODO evidence backlog

Generated 2026-11-24T01:39:15.866969+00:00 by `tools/gen_1000_todos.py`. Machine state: `1000_TODOS.json`. Do not hand-edit the counts - rerun the generator.

**Worked 36 of 1000.** open 926 | claimed 4 | blocked_no_data 34

## Done condition (identical for every cell)

Report n (closed trades), net mean bp/trade after 26bp round-turn, 95% bootstrap CI, permutation p, and DSR. Cell is DONE when a JSON artifact exists under results/cells/<symbol>_<strategy>_<horizon>.json carrying those five numbers plus git SHA. Cell is KILLED (also complete) when n<30 or CI includes 0 or permutation p>0.05. Cell is BLOCKED_NO_DATA only when the instrument has no bars at that horizon in the repo - and then the bar count must be recorded to prove it.

A KILL is a completed cell. Null results are the expected majority; they are the product.

## BTCUSDT - 28/50 worked

| cell | status | artifact |
|---|---|---|
| [~] `BTCUSDT/trend_pullback/15m` | claimed | `results/cells/BTCUSDT_trend_pullback_15m.json` |
| [~] `BTCUSDT/trend_pullback/1h` | claimed | `results/cells/BTCUSDT_trend_pullback_1h.json` |
| [~] `BTCUSDT/trend_pullback/4h` | claimed | `results/cells/BTCUSDT_trend_pullback_4h.json` |
| [x] `BTCUSDT/trend_pullback/1d` | killed | `results/cells/BTCUSDT_trend_pullback_1d.json` |
| [x] `BTCUSDT/trend_pullback/1w` | done | `results/cells/BTCUSDT_trend_pullback_1w.json` |
| [x] `BTCUSDT/rsi2_pullback/15m` | done | `results/cells/BTCUSDT_rsi2_pullback_15m.json` |
| [-] `BTCUSDT/rsi2_pullback/1h` | blocked_no_data | `results/cells/BTCUSDT_rsi2_pullback_1h.json` |
| [-] `BTCUSDT/rsi2_pullback/4h` | blocked_no_data | `results/cells/BTCUSDT_rsi2_pullback_4h.json` |
| [x] `BTCUSDT/rsi2_pullback/1d` | done | `results/cells/BTCUSDT_rsi2_pullback_1d.json` |
| [x] `BTCUSDT/rsi2_pullback/1w` | done | `results/cells/BTCUSDT_rsi2_pullback_1w.json` |
| [x] `BTCUSDT/vol_compression/15m` | killed | `results/cells/BTCUSDT_vol_compression_15m.json` |
| [-] `BTCUSDT/vol_compression/1h` | blocked_no_data | `results/cells/BTCUSDT_vol_compression_1h.json` |
| [-] `BTCUSDT/vol_compression/4h` | blocked_no_data | `results/cells/BTCUSDT_vol_compression_4h.json` |
| [x] `BTCUSDT/vol_compression/1d` | killed | `results/cells/BTCUSDT_vol_compression_1d.json` |
| [x] `BTCUSDT/vol_compression/1w` | done | `results/cells/BTCUSDT_vol_compression_1w.json` |
| [-] `BTCUSDT/breakout/15m` | blocked_no_data | `results/cells/BTCUSDT_breakout_15m.json` |
| [-] `BTCUSDT/breakout/1h` | blocked_no_data | `results/cells/BTCUSDT_breakout_1h.json` |
| [-] `BTCUSDT/breakout/4h` | blocked_no_data | `results/cells/BTCUSDT_breakout_4h.json` |
| [x] `BTCUSDT/breakout/1d` | done | `results/cells/BTCUSDT_breakout_1d.json` |
| [x] `BTCUSDT/breakout/1w` | done | `results/cells/BTCUSDT_breakout_1w.json` |
| [-] `BTCUSDT/donchian/15m` | blocked_no_data | `results/cells/BTCUSDT_donchian_15m.json` |
| [x] `BTCUSDT/donchian/1h` | killed | `results/cells/BTCUSDT_donchian_1h.json` |
| [-] `BTCUSDT/donchian/4h` | blocked_no_data | `results/cells/BTCUSDT_donchian_4h.json` |
| [x] `BTCUSDT/donchian/1d` | done | `results/cells/BTCUSDT_donchian_1d.json` |
| [x] `BTCUSDT/donchian/1w` | done | `results/cells/BTCUSDT_donchian_1w.json` |
| [-] `BTCUSDT/ma_cross/15m` | blocked_no_data | `results/cells/BTCUSDT_ma_cross_15m.json` |
| [x] `BTCUSDT/ma_cross/1h` | done | `results/cells/BTCUSDT_ma_cross_1h.json` |
| [-] `BTCUSDT/ma_cross/4h` | blocked_no_data | `results/cells/BTCUSDT_ma_cross_4h.json` |
| [x] `BTCUSDT/ma_cross/1d` | done | `results/cells/BTCUSDT_ma_cross_1d.json` |
| [x] `BTCUSDT/ma_cross/1w` | done | `results/cells/BTCUSDT_ma_cross_1w.json` |
| [-] `BTCUSDT/bb_meanrev/15m` | blocked_no_data | `results/cells/BTCUSDT_bb_meanrev_15m.json` |
| [x] `BTCUSDT/bb_meanrev/1h` | killed | `results/cells/BTCUSDT_bb_meanrev_1h.json` |
| [-] `BTCUSDT/bb_meanrev/4h` | blocked_no_data | `results/cells/BTCUSDT_bb_meanrev_4h.json` |
| [x] `BTCUSDT/bb_meanrev/1d` | done | `results/cells/BTCUSDT_bb_meanrev_1d.json` |
| [x] `BTCUSDT/bb_meanrev/1w` | done | `results/cells/BTCUSDT_bb_meanrev_1w.json` |
| [-] `BTCUSDT/vwap_reversion/15m` | blocked_no_data | `results/cells/BTCUSDT_vwap_reversion_15m.json` |
| [x] `BTCUSDT/vwap_reversion/1h` | killed | `results/cells/BTCUSDT_vwap_reversion_1h.json` |
| [-] `BTCUSDT/vwap_reversion/4h` | blocked_no_data | `results/cells/BTCUSDT_vwap_reversion_4h.json` |
| [x] `BTCUSDT/vwap_reversion/1d` | killed | `results/cells/BTCUSDT_vwap_reversion_1d.json` |
| [x] `BTCUSDT/vwap_reversion/1w` | done | `results/cells/BTCUSDT_vwap_reversion_1w.json` |
| [-] `BTCUSDT/momentum_12_1/15m` | blocked_no_data | `results/cells/BTCUSDT_momentum_12_1_15m.json` |
| [x] `BTCUSDT/momentum_12_1/1h` | killed | `results/cells/BTCUSDT_momentum_12_1_1h.json` |
| [-] `BTCUSDT/momentum_12_1/4h` | blocked_no_data | `results/cells/BTCUSDT_momentum_12_1_4h.json` |
| [x] `BTCUSDT/momentum_12_1/1d` | killed | `results/cells/BTCUSDT_momentum_12_1_1d.json` |
| [x] `BTCUSDT/momentum_12_1/1w` | done | `results/cells/BTCUSDT_momentum_12_1_1w.json` |
| [-] `BTCUSDT/gap_fade/15m` | blocked_no_data | `results/cells/BTCUSDT_gap_fade_15m.json` |
| [x] `BTCUSDT/gap_fade/1h` | done | `results/cells/BTCUSDT_gap_fade_1h.json` |
| [-] `BTCUSDT/gap_fade/4h` | blocked_no_data | `results/cells/BTCUSDT_gap_fade_4h.json` |
| [x] `BTCUSDT/gap_fade/1d` | done | `results/cells/BTCUSDT_gap_fade_1d.json` |
| [x] `BTCUSDT/gap_fade/1w` | done | `results/cells/BTCUSDT_gap_fade_1w.json` |

## ETHUSDT - 8/50 worked

| cell | status | artifact |
|---|---|---|
| [-] `ETHUSDT/trend_pullback/15m` | blocked_no_data | `results/cells/ETHUSDT_trend_pullback_15m.json` |
| [-] `ETHUSDT/trend_pullback/1h` | blocked_no_data | `results/cells/ETHUSDT_trend_pullback_1h.json` |
| [-] `ETHUSDT/trend_pullback/4h` | blocked_no_data | `results/cells/ETHUSDT_trend_pullback_4h.json` |
| [~] `ETHUSDT/trend_pullback/1d` | claimed | `results/cells/ETHUSDT_trend_pullback_1d.json` |
| [x] `ETHUSDT/trend_pullback/1w` | done | `results/cells/ETHUSDT_trend_pullback_1w.json` |
| [-] `ETHUSDT/rsi2_pullback/15m` | blocked_no_data | `results/cells/ETHUSDT_rsi2_pullback_15m.json` |
| [-] `ETHUSDT/rsi2_pullback/1h` | blocked_no_data | `results/cells/ETHUSDT_rsi2_pullback_1h.json` |
| [-] `ETHUSDT/rsi2_pullback/4h` | blocked_no_data | `results/cells/ETHUSDT_rsi2_pullback_4h.json` |
| [x] `ETHUSDT/rsi2_pullback/1d` | done | `results/cells/ETHUSDT_rsi2_pullback_1d.json` |
| [x] `ETHUSDT/rsi2_pullback/1w` | done | `results/cells/ETHUSDT_rsi2_pullback_1w.json` |
| [-] `ETHUSDT/vol_compression/15m` | blocked_no_data | `results/cells/ETHUSDT_vol_compression_15m.json` |
| [-] `ETHUSDT/vol_compression/1h` | blocked_no_data | `results/cells/ETHUSDT_vol_compression_1h.json` |
| [-] `ETHUSDT/vol_compression/4h` | blocked_no_data | `results/cells/ETHUSDT_vol_compression_4h.json` |
| [x] `ETHUSDT/vol_compression/1d` | done | `results/cells/ETHUSDT_vol_compression_1d.json` |
| [x] `ETHUSDT/vol_compression/1w` | done | `results/cells/ETHUSDT_vol_compression_1w.json` |
| [-] `ETHUSDT/breakout/15m` | blocked_no_data | `results/cells/ETHUSDT_breakout_15m.json` |
| [-] `ETHUSDT/breakout/1h` | blocked_no_data | `results/cells/ETHUSDT_breakout_1h.json` |
| [-] `ETHUSDT/breakout/4h` | blocked_no_data | `results/cells/ETHUSDT_breakout_4h.json` |
| [x] `ETHUSDT/breakout/1d` | done | `results/cells/ETHUSDT_breakout_1d.json` |
| [x] `ETHUSDT/breakout/1w` | done | `results/cells/ETHUSDT_breakout_1w.json` |
| [-] `ETHUSDT/donchian/15m` | blocked_no_data | `results/cells/ETHUSDT_donchian_15m.json` |
| [-] `ETHUSDT/donchian/1h` | blocked_no_data | `results/cells/ETHUSDT_donchian_1h.json` |
| [-] `ETHUSDT/donchian/4h` | blocked_no_data | `results/cells/ETHUSDT_donchian_4h.json` |
| [x] `ETHUSDT/donchian/1d` | done | `results/cells/ETHUSDT_donchian_1d.json` |
| [ ] `ETHUSDT/donchian/1w` | open | `results/cells/ETHUSDT_donchian_1w.json` |
| [ ] `ETHUSDT/ma_cross/15m` | open | `results/cells/ETHUSDT_ma_cross_15m.json` |
| [ ] `ETHUSDT/ma_cross/1h` | open | `results/cells/ETHUSDT_ma_cross_1h.json` |
| [ ] `ETHUSDT/ma_cross/4h` | open | `results/cells/ETHUSDT_ma_cross_4h.json` |
| [ ] `ETHUSDT/ma_cross/1d` | open | `results/cells/ETHUSDT_ma_cross_1d.json` |
| [ ] `ETHUSDT/ma_cross/1w` | open | `results/cells/ETHUSDT_ma_cross_1w.json` |
| [ ] `ETHUSDT/bb_meanrev/15m` | open | `results/cells/ETHUSDT_bb_meanrev_15m.json` |
| [ ] `ETHUSDT/bb_meanrev/1h` | open | `results/cells/ETHUSDT_bb_meanrev_1h.json` |
| [ ] `ETHUSDT/bb_meanrev/4h` | open | `results/cells/ETHUSDT_bb_meanrev_4h.json` |
| [ ] `ETHUSDT/bb_meanrev/1d` | open | `results/cells/ETHUSDT_bb_meanrev_1d.json` |
| [ ] `ETHUSDT/bb_meanrev/1w` | open | `results/cells/ETHUSDT_bb_meanrev_1w.json` |
| [ ] `ETHUSDT/vwap_reversion/15m` | open | `results/cells/ETHUSDT_vwap_reversion_15m.json` |
| [ ] `ETHUSDT/vwap_reversion/1h` | open | `results/cells/ETHUSDT_vwap_reversion_1h.json` |
| [ ] `ETHUSDT/vwap_reversion/4h` | open | `results/cells/ETHUSDT_vwap_reversion_4h.json` |
| [ ] `ETHUSDT/vwap_reversion/1d` | open | `results/cells/ETHUSDT_vwap_reversion_1d.json` |
| [ ] `ETHUSDT/vwap_reversion/1w` | open | `results/cells/ETHUSDT_vwap_reversion_1w.json` |
| [ ] `ETHUSDT/momentum_12_1/15m` | open | `results/cells/ETHUSDT_momentum_12_1_15m.json` |
| [ ] `ETHUSDT/momentum_12_1/1h` | open | `results/cells/ETHUSDT_momentum_12_1_1h.json` |
| [ ] `ETHUSDT/momentum_12_1/4h` | open | `results/cells/ETHUSDT_momentum_12_1_4h.json` |
| [ ] `ETHUSDT/momentum_12_1/1d` | open | `results/cells/ETHUSDT_momentum_12_1_1d.json` |
| [ ] `ETHUSDT/momentum_12_1/1w` | open | `results/cells/ETHUSDT_momentum_12_1_1w.json` |
| [ ] `ETHUSDT/gap_fade/15m` | open | `results/cells/ETHUSDT_gap_fade_15m.json` |
| [ ] `ETHUSDT/gap_fade/1h` | open | `results/cells/ETHUSDT_gap_fade_1h.json` |
| [ ] `ETHUSDT/gap_fade/4h` | open | `results/cells/ETHUSDT_gap_fade_4h.json` |
| [ ] `ETHUSDT/gap_fade/1d` | open | `results/cells/ETHUSDT_gap_fade_1d.json` |
| [ ] `ETHUSDT/gap_fade/1w` | open | `results/cells/ETHUSDT_gap_fade_1w.json` |

## SOLUSDT - 0/50 worked

| cell | status | artifact |
|---|---|---|
| [ ] `SOLUSDT/trend_pullback/15m` | open | `results/cells/SOLUSDT_trend_pullback_15m.json` |
| [ ] `SOLUSDT/trend_pullback/1h` | open | `results/cells/SOLUSDT_trend_pullback_1h.json` |
| [ ] `SOLUSDT/trend_pullback/4h` | open | `results/cells/SOLUSDT_trend_pullback_4h.json` |
| [ ] `SOLUSDT/trend_pullback/1d` | open | `results/cells/SOLUSDT_trend_pullback_1d.json` |
| [ ] `SOLUSDT/trend_pullback/1w` | open | `results/cells/SOLUSDT_trend_pullback_1w.json` |
| [ ] `SOLUSDT/rsi2_pullback/15m` | open | `results/cells/SOLUSDT_rsi2_pullback_15m.json` |
| [ ] `SOLUSDT/rsi2_pullback/1h` | open | `results/cells/SOLUSDT_rsi2_pullback_1h.json` |
| [ ] `SOLUSDT/rsi2_pullback/4h` | open | `results/cells/SOLUSDT_rsi2_pullback_4h.json` |
| [ ] `SOLUSDT/rsi2_pullback/1d` | open | `results/cells/SOLUSDT_rsi2_pullback_1d.json` |
| [ ] `SOLUSDT/rsi2_pullback/1w` | open | `results/cells/SOLUSDT_rsi2_pullback_1w.json` |
| [ ] `SOLUSDT/vol_compression/15m` | open | `results/cells/SOLUSDT_vol_compression_15m.json` |
| [ ] `SOLUSDT/vol_compression/1h` | open | `results/cells/SOLUSDT_vol_compression_1h.json` |
| [ ] `SOLUSDT/vol_compression/4h` | open | `results/cells/SOLUSDT_vol_compression_4h.json` |
| [ ] `SOLUSDT/vol_compression/1d` | open | `results/cells/SOLUSDT_vol_compression_1d.json` |
| [ ] `SOLUSDT/vol_compression/1w` | open | `results/cells/SOLUSDT_vol_compression_1w.json` |
| [ ] `SOLUSDT/breakout/15m` | open | `results/cells/SOLUSDT_breakout_15m.json` |
| [ ] `SOLUSDT/breakout/1h` | open | `results/cells/SOLUSDT_breakout_1h.json` |
| [ ] `SOLUSDT/breakout/4h` | open | `results/cells/SOLUSDT_breakout_4h.json` |
| [ ] `SOLUSDT/breakout/1d` | open | `results/cells/SOLUSDT_breakout_1d.json` |
| [ ] `SOLUSDT/breakout/1w` | open | `results/cells/SOLUSDT_breakout_1w.json` |
| [ ] `SOLUSDT/donchian/15m` | open | `results/cells/SOLUSDT_donchian_15m.json` |
| [ ] `SOLUSDT/donchian/1h` | open | `results/cells/SOLUSDT_donchian_1h.json` |
| [ ] `SOLUSDT/donchian/4h` | open | `results/cells/SOLUSDT_donchian_4h.json` |
| [ ] `SOLUSDT/donchian/1d` | open | `results/cells/SOLUSDT_donchian_1d.json` |
| [ ] `SOLUSDT/donchian/1w` | open | `results/cells/SOLUSDT_donchian_1w.json` |
| [ ] `SOLUSDT/ma_cross/15m` | open | `results/cells/SOLUSDT_ma_cross_15m.json` |
| [ ] `SOLUSDT/ma_cross/1h` | open | `results/cells/SOLUSDT_ma_cross_1h.json` |
| [ ] `SOLUSDT/ma_cross/4h` | open | `results/cells/SOLUSDT_ma_cross_4h.json` |
| [ ] `SOLUSDT/ma_cross/1d` | open | `results/cells/SOLUSDT_ma_cross_1d.json` |
| [ ] `SOLUSDT/ma_cross/1w` | open | `results/cells/SOLUSDT_ma_cross_1w.json` |
| [ ] `SOLUSDT/bb_meanrev/15m` | open | `results/cells/SOLUSDT_bb_meanrev_15m.json` |
| [ ] `SOLUSDT/bb_meanrev/1h` | open | `results/cells/SOLUSDT_bb_meanrev_1h.json` |
| [ ] `SOLUSDT/bb_meanrev/4h` | open | `results/cells/SOLUSDT_bb_meanrev_4h.json` |
| [ ] `SOLUSDT/bb_meanrev/1d` | open | `results/cells/SOLUSDT_bb_meanrev_1d.json` |
| [ ] `SOLUSDT/bb_meanrev/1w` | open | `results/cells/SOLUSDT_bb_meanrev_1w.json` |
| [ ] `SOLUSDT/vwap_reversion/15m` | open | `results/cells/SOLUSDT_vwap_reversion_15m.json` |
| [ ] `SOLUSDT/vwap_reversion/1h` | open | `results/cells/SOLUSDT_vwap_reversion_1h.json` |
| [ ] `SOLUSDT/vwap_reversion/4h` | open | `results/cells/SOLUSDT_vwap_reversion_4h.json` |
| [ ] `SOLUSDT/vwap_reversion/1d` | open | `results/cells/SOLUSDT_vwap_reversion_1d.json` |
| [ ] `SOLUSDT/vwap_reversion/1w` | open | `results/cells/SOLUSDT_vwap_reversion_1w.json` |
| [ ] `SOLUSDT/momentum_12_1/15m` | open | `results/cells/SOLUSDT_momentum_12_1_15m.json` |
| [ ] `SOLUSDT/momentum_12_1/1h` | open | `results/cells/SOLUSDT_momentum_12_1_1h.json` |
| [ ] `SOLUSDT/momentum_12_1/4h` | open | `results/cells/SOLUSDT_momentum_12_1_4h.json` |
| [ ] `SOLUSDT/momentum_12_1/1d` | open | `results/cells/SOLUSDT_momentum_12_1_1d.json` |
| [ ] `SOLUSDT/momentum_12_1/1w` | open | `results/cells/SOLUSDT_momentum_12_1_1w.json` |
| [ ] `SOLUSDT/gap_fade/15m` | open | `results/cells/SOLUSDT_gap_fade_15m.json` |
| [ ] `SOLUSDT/gap_fade/1h` | open | `results/cells/SOLUSDT_gap_fade_1h.json` |
| [ ] `SOLUSDT/gap_fade/4h` | open | `results/cells/SOLUSDT_gap_fade_4h.json` |
| [ ] `SOLUSDT/gap_fade/1d` | open | `results/cells/SOLUSDT_gap_fade_1d.json` |
| [ ] `SOLUSDT/gap_fade/1w` | open | `results/cells/SOLUSDT_gap_fade_1w.json` |

## XRPUSDT - 0/50 worked

| cell | status | artifact |
|---|---|---|
| [ ] `XRPUSDT/trend_pullback/15m` | open | `results/cells/XRPUSDT_trend_pullback_15m.json` |
| [ ] `XRPUSDT/trend_pullback/1h` | open | `results/cells/XRPUSDT_trend_pullback_1h.json` |
| [ ] `XRPUSDT/trend_pullback/4h` | open | `results/cells/XRPUSDT_trend_pullback_4h.json` |
| [ ] `XRPUSDT/trend_pullback/1d` | open | `results/cells/XRPUSDT_trend_pullback_1d.json` |
| [ ] `XRPUSDT/trend_pullback/1w` | open | `results/cells/XRPUSDT_trend_pullback_1w.json` |
| [ ] `XRPUSDT/rsi2_pullback/15m` | open | `results/cells/XRPUSDT_rsi2_pullback_15m.json` |
| [ ] `XRPUSDT/rsi2_pullback/1h` | open | `results/cells/XRPUSDT_rsi2_pullback_1h.json` |
| [ ] `XRPUSDT/rsi2_pullback/4h` | open | `results/cells/XRPUSDT_rsi2_pullback_4h.json` |
| [ ] `XRPUSDT/rsi2_pullback/1d` | open | `results/cells/XRPUSDT_rsi2_pullback_1d.json` |
| [ ] `XRPUSDT/rsi2_pullback/1w` | open | `results/cells/XRPUSDT_rsi2_pullback_1w.json` |
| [ ] `XRPUSDT/vol_compression/15m` | open | `results/cells/XRPUSDT_vol_compression_15m.json` |
| [ ] `XRPUSDT/vol_compression/1h` | open | `results/cells/XRPUSDT_vol_compression_1h.json` |
| [ ] `XRPUSDT/vol_compression/4h` | open | `results/cells/XRPUSDT_vol_compression_4h.json` |
| [ ] `XRPUSDT/vol_compression/1d` | open | `results/cells/XRPUSDT_vol_compression_1d.json` |
| [ ] `XRPUSDT/vol_compression/1w` | open | `results/cells/XRPUSDT_vol_compression_1w.json` |
| [ ] `XRPUSDT/breakout/15m` | open | `results/cells/XRPUSDT_breakout_15m.json` |
| [ ] `XRPUSDT/breakout/1h` | open | `results/cells/XRPUSDT_breakout_1h.json` |
| [ ] `XRPUSDT/breakout/4h` | open | `results/cells/XRPUSDT_breakout_4h.json` |
| [ ] `XRPUSDT/breakout/1d` | open | `results/cells/XRPUSDT_breakout_1d.json` |
| [ ] `XRPUSDT/breakout/1w` | open | `results/cells/XRPUSDT_breakout_1w.json` |
| [ ] `XRPUSDT/donchian/15m` | open | `results/cells/XRPUSDT_donchian_15m.json` |
| [ ] `XRPUSDT/donchian/1h` | open | `results/cells/XRPUSDT_donchian_1h.json` |
| [ ] `XRPUSDT/donchian/4h` | open | `results/cells/XRPUSDT_donchian_4h.json` |
| [ ] `XRPUSDT/donchian/1d` | open | `results/cells/XRPUSDT_donchian_1d.json` |
| [ ] `XRPUSDT/donchian/1w` | open | `results/cells/XRPUSDT_donchian_1w.json` |
| [ ] `XRPUSDT/ma_cross/15m` | open | `results/cells/XRPUSDT_ma_cross_15m.json` |
| [ ] `XRPUSDT/ma_cross/1h` | open | `results/cells/XRPUSDT_ma_cross_1h.json` |
| [ ] `XRPUSDT/ma_cross/4h` | open | `results/cells/XRPUSDT_ma_cross_4h.json` |
| [ ] `XRPUSDT/ma_cross/1d` | open | `results/cells/XRPUSDT_ma_cross_1d.json` |
| [ ] `XRPUSDT/ma_cross/1w` | open | `results/cells/XRPUSDT_ma_cross_1w.json` |
| [ ] `XRPUSDT/bb_meanrev/15m` | open | `results/cells/XRPUSDT_bb_meanrev_15m.json` |
| [ ] `XRPUSDT/bb_meanrev/1h` | open | `results/cells/XRPUSDT_bb_meanrev_1h.json` |
| [ ] `XRPUSDT/bb_meanrev/4h` | open | `results/cells/XRPUSDT_bb_meanrev_4h.json` |
| [ ] `XRPUSDT/bb_meanrev/1d` | open | `results/cells/XRPUSDT_bb_meanrev_1d.json` |
| [ ] `XRPUSDT/bb_meanrev/1w` | open | `results/cells/XRPUSDT_bb_meanrev_1w.json` |
| [ ] `XRPUSDT/vwap_reversion/15m` | open | `results/cells/XRPUSDT_vwap_reversion_15m.json` |
| [ ] `XRPUSDT/vwap_reversion/1h` | open | `results/cells/XRPUSDT_vwap_reversion_1h.json` |
| [ ] `XRPUSDT/vwap_reversion/4h` | open | `results/cells/XRPUSDT_vwap_reversion_4h.json` |
| [ ] `XRPUSDT/vwap_reversion/1d` | open | `results/cells/XRPUSDT_vwap_reversion_1d.json` |
| [ ] `XRPUSDT/vwap_reversion/1w` | open | `results/cells/XRPUSDT_vwap_reversion_1w.json` |
| [ ] `XRPUSDT/momentum_12_1/15m` | open | `results/cells/XRPUSDT_momentum_12_1_15m.json` |
| [ ] `XRPUSDT/momentum_12_1/1h` | open | `results/cells/XRPUSDT_momentum_12_1_1h.json` |
| [ ] `XRPUSDT/momentum_12_1/4h` | open | `results/cells/XRPUSDT_momentum_12_1_4h.json` |
| [ ] `XRPUSDT/momentum_12_1/1d` | open | `results/cells/XRPUSDT_momentum_12_1_1d.json` |
| [ ] `XRPUSDT/momentum_12_1/1w` | open | `results/cells/XRPUSDT_momentum_12_1_1w.json` |
| [ ] `XRPUSDT/gap_fade/15m` | open | `results/cells/XRPUSDT_gap_fade_15m.json` |
| [ ] `XRPUSDT/gap_fade/1h` | open | `results/cells/XRPUSDT_gap_fade_1h.json` |
| [ ] `XRPUSDT/gap_fade/4h` | open | `results/cells/XRPUSDT_gap_fade_4h.json` |
| [ ] `XRPUSDT/gap_fade/1d` | open | `results/cells/XRPUSDT_gap_fade_1d.json` |
| [ ] `XRPUSDT/gap_fade/1w` | open | `results/cells/XRPUSDT_gap_fade_1w.json` |

## DOGEUSDT - 0/50 worked

| cell | status | artifact |
|---|---|---|
| [ ] `DOGEUSDT/trend_pullback/15m` | open | `results/cells/DOGEUSDT_trend_pullback_15m.json` |
| [ ] `DOGEUSDT/trend_pullback/1h` | open | `results/cells/DOGEUSDT_trend_pullback_1h.json` |
| [ ] `DOGEUSDT/trend_pullback/4h` | open | `results/cells/DOGEUSDT_trend_pullback_4h.json` |
| [ ] `DOGEUSDT/trend_pullback/1d` | open | `results/cells/DOGEUSDT_trend_pullback_1d.json` |
| [ ] `DOGEUSDT/trend_pullback/1w` | open | `results/cells/DOGEUSDT_trend_pullback_1w.json` |
| [ ] `DOGEUSDT/rsi2_pullback/15m` | open | `results/cells/DOGEUSDT_rsi2_pullback_15m.json` |
| [ ] `DOGEUSDT/rsi2_pullback/1h` | open | `results/cells/DOGEUSDT_rsi2_pullback_1h.json` |
| [ ] `DOGEUSDT/rsi2_pullback/4h` | open | `results/cells/DOGEUSDT_rsi2_pullback_4h.json` |
| [ ] `DOGEUSDT/rsi2_pullback/1d` | open | `results/cells/DOGEUSDT_rsi2_pullback_1d.json` |
| [ ] `DOGEUSDT/rsi2_pullback/1w` | open | `results/cells/DOGEUSDT_rsi2_pullback_1w.json` |
| [ ] `DOGEUSDT/vol_compression/15m` | open | `results/cells/DOGEUSDT_vol_compression_15m.json` |
| [ ] `DOGEUSDT/vol_compression/1h` | open | `results/cells/DOGEUSDT_vol_compression_1h.json` |
| [ ] `DOGEUSDT/vol_compression/4h` | open | `results/cells/DOGEUSDT_vol_compression_4h.json` |
| [ ] `DOGEUSDT/vol_compression/1d` | open | `results/cells/DOGEUSDT_vol_compression_1d.json` |
| [ ] `DOGEUSDT/vol_compression/1w` | open | `results/cells/DOGEUSDT_vol_compression_1w.json` |
| [ ] `DOGEUSDT/breakout/15m` | open | `results/cells/DOGEUSDT_breakout_15m.json` |
| [ ] `DOGEUSDT/breakout/1h` | open | `results/cells/DOGEUSDT_breakout_1h.json` |
| [ ] `DOGEUSDT/breakout/4h` | open | `results/cells/DOGEUSDT_breakout_4h.json` |
| [ ] `DOGEUSDT/breakout/1d` | open | `results/cells/DOGEUSDT_breakout_1d.json` |
| [ ] `DOGEUSDT/breakout/1w` | open | `results/cells/DOGEUSDT_breakout_1w.json` |
| [ ] `DOGEUSDT/donchian/15m` | open | `results/cells/DOGEUSDT_donchian_15m.json` |
| [ ] `DOGEUSDT/donchian/1h` | open | `results/cells/DOGEUSDT_donchian_1h.json` |
| [ ] `DOGEUSDT/donchian/4h` | open | `results/cells/DOGEUSDT_donchian_4h.json` |
| [ ] `DOGEUSDT/donchian/1d` | open | `results/cells/DOGEUSDT_donchian_1d.json` |
| [ ] `DOGEUSDT/donchian/1w` | open | `results/cells/DOGEUSDT_donchian_1w.json` |
| [ ] `DOGEUSDT/ma_cross/15m` | open | `results/cells/DOGEUSDT_ma_cross_15m.json` |
| [ ] `DOGEUSDT/ma_cross/1h` | open | `results/cells/DOGEUSDT_ma_cross_1h.json` |
| [ ] `DOGEUSDT/ma_cross/4h` | open | `results/cells/DOGEUSDT_ma_cross_4h.json` |
| [ ] `DOGEUSDT/ma_cross/1d` | open | `results/cells/DOGEUSDT_ma_cross_1d.json` |
| [ ] `DOGEUSDT/ma_cross/1w` | open | `results/cells/DOGEUSDT_ma_cross_1w.json` |
| [ ] `DOGEUSDT/bb_meanrev/15m` | open | `results/cells/DOGEUSDT_bb_meanrev_15m.json` |
| [ ] `DOGEUSDT/bb_meanrev/1h` | open | `results/cells/DOGEUSDT_bb_meanrev_1h.json` |
| [ ] `DOGEUSDT/bb_meanrev/4h` | open | `results/cells/DOGEUSDT_bb_meanrev_4h.json` |
| [ ] `DOGEUSDT/bb_meanrev/1d` | open | `results/cells/DOGEUSDT_bb_meanrev_1d.json` |
| [ ] `DOGEUSDT/bb_meanrev/1w` | open | `results/cells/DOGEUSDT_bb_meanrev_1w.json` |
| [ ] `DOGEUSDT/vwap_reversion/15m` | open | `results/cells/DOGEUSDT_vwap_reversion_15m.json` |
| [ ] `DOGEUSDT/vwap_reversion/1h` | open | `results/cells/DOGEUSDT_vwap_reversion_1h.json` |
| [ ] `DOGEUSDT/vwap_reversion/4h` | open | `results/cells/DOGEUSDT_vwap_reversion_4h.json` |
| [ ] `DOGEUSDT/vwap_reversion/1d` | open | `results/cells/DOGEUSDT_vwap_reversion_1d.json` |
| [ ] `DOGEUSDT/vwap_reversion/1w` | open | `results/cells/DOGEUSDT_vwap_reversion_1w.json` |
| [ ] `DOGEUSDT/momentum_12_1/15m` | open | `results/cells/DOGEUSDT_momentum_12_1_15m.json` |
| [ ] `DOGEUSDT/momentum_12_1/1h` | open | `results/cells/DOGEUSDT_momentum_12_1_1h.json` |
| [ ] `DOGEUSDT/momentum_12_1/4h` | open | `results/cells/DOGEUSDT_momentum_12_1_4h.json` |
| [ ] `DOGEUSDT/momentum_12_1/1d` | open | `results/cells/DOGEUSDT_momentum_12_1_1d.json` |
| [ ] `DOGEUSDT/momentum_12_1/1w` | open | `results/cells/DOGEUSDT_momentum_12_1_1w.json` |
| [ ] `DOGEUSDT/gap_fade/15m` | open | `results/cells/DOGEUSDT_gap_fade_15m.json` |
| [ ] `DOGEUSDT/gap_fade/1h` | open | `results/cells/DOGEUSDT_gap_fade_1h.json` |
| [ ] `DOGEUSDT/gap_fade/4h` | open | `results/cells/DOGEUSDT_gap_fade_4h.json` |
| [ ] `DOGEUSDT/gap_fade/1d` | open | `results/cells/DOGEUSDT_gap_fade_1d.json` |
| [ ] `DOGEUSDT/gap_fade/1w` | open | `results/cells/DOGEUSDT_gap_fade_1w.json` |

## ADAUSDT - 0/50 worked

| cell | status | artifact |
|---|---|---|
| [ ] `ADAUSDT/trend_pullback/15m` | open | `results/cells/ADAUSDT_trend_pullback_15m.json` |
| [ ] `ADAUSDT/trend_pullback/1h` | open | `results/cells/ADAUSDT_trend_pullback_1h.json` |
| [ ] `ADAUSDT/trend_pullback/4h` | open | `results/cells/ADAUSDT_trend_pullback_4h.json` |
| [ ] `ADAUSDT/trend_pullback/1d` | open | `results/cells/ADAUSDT_trend_pullback_1d.json` |
| [ ] `ADAUSDT/trend_pullback/1w` | open | `results/cells/ADAUSDT_trend_pullback_1w.json` |
| [ ] `ADAUSDT/rsi2_pullback/15m` | open | `results/cells/ADAUSDT_rsi2_pullback_15m.json` |
| [ ] `ADAUSDT/rsi2_pullback/1h` | open | `results/cells/ADAUSDT_rsi2_pullback_1h.json` |
| [ ] `ADAUSDT/rsi2_pullback/4h` | open | `results/cells/ADAUSDT_rsi2_pullback_4h.json` |
| [ ] `ADAUSDT/rsi2_pullback/1d` | open | `results/cells/ADAUSDT_rsi2_pullback_1d.json` |
| [ ] `ADAUSDT/rsi2_pullback/1w` | open | `results/cells/ADAUSDT_rsi2_pullback_1w.json` |
| [ ] `ADAUSDT/vol_compression/15m` | open | `results/cells/ADAUSDT_vol_compression_15m.json` |
| [ ] `ADAUSDT/vol_compression/1h` | open | `results/cells/ADAUSDT_vol_compression_1h.json` |
| [ ] `ADAUSDT/vol_compression/4h` | open | `results/cells/ADAUSDT_vol_compression_4h.json` |
| [ ] `ADAUSDT/vol_compression/1d` | open | `results/cells/ADAUSDT_vol_compression_1d.json` |
| [ ] `ADAUSDT/vol_compression/1w` | open | `results/cells/ADAUSDT_vol_compression_1w.json` |
| [ ] `ADAUSDT/breakout/15m` | open | `results/cells/ADAUSDT_breakout_15m.json` |
| [ ] `ADAUSDT/breakout/1h` | open | `results/cells/ADAUSDT_breakout_1h.json` |
| [ ] `ADAUSDT/breakout/4h` | open | `results/cells/ADAUSDT_breakout_4h.json` |
| [ ] `ADAUSDT/breakout/1d` | open | `results/cells/ADAUSDT_breakout_1d.json` |
| [ ] `ADAUSDT/breakout/1w` | open | `results/cells/ADAUSDT_breakout_1w.json` |
| [ ] `ADAUSDT/donchian/15m` | open | `results/cells/ADAUSDT_donchian_15m.json` |
| [ ] `ADAUSDT/donchian/1h` | open | `results/cells/ADAUSDT_donchian_1h.json` |
| [ ] `ADAUSDT/donchian/4h` | open | `results/cells/ADAUSDT_donchian_4h.json` |
| [ ] `ADAUSDT/donchian/1d` | open | `results/cells/ADAUSDT_donchian_1d.json` |
| [ ] `ADAUSDT/donchian/1w` | open | `results/cells/ADAUSDT_donchian_1w.json` |
| [ ] `ADAUSDT/ma_cross/15m` | open | `results/cells/ADAUSDT_ma_cross_15m.json` |
| [ ] `ADAUSDT/ma_cross/1h` | open | `results/cells/ADAUSDT_ma_cross_1h.json` |
| [ ] `ADAUSDT/ma_cross/4h` | open | `results/cells/ADAUSDT_ma_cross_4h.json` |
| [ ] `ADAUSDT/ma_cross/1d` | open | `results/cells/ADAUSDT_ma_cross_1d.json` |
| [ ] `ADAUSDT/ma_cross/1w` | open | `results/cells/ADAUSDT_ma_cross_1w.json` |
| [ ] `ADAUSDT/bb_meanrev/15m` | open | `results/cells/ADAUSDT_bb_meanrev_15m.json` |
| [ ] `ADAUSDT/bb_meanrev/1h` | open | `results/cells/ADAUSDT_bb_meanrev_1h.json` |
| [ ] `ADAUSDT/bb_meanrev/4h` | open | `results/cells/ADAUSDT_bb_meanrev_4h.json` |
| [ ] `ADAUSDT/bb_meanrev/1d` | open | `results/cells/ADAUSDT_bb_meanrev_1d.json` |
| [ ] `ADAUSDT/bb_meanrev/1w` | open | `results/cells/ADAUSDT_bb_meanrev_1w.json` |
| [ ] `ADAUSDT/vwap_reversion/15m` | open | `results/cells/ADAUSDT_vwap_reversion_15m.json` |
| [ ] `ADAUSDT/vwap_reversion/1h` | open | `results/cells/ADAUSDT_vwap_reversion_1h.json` |
| [ ] `ADAUSDT/vwap_reversion/4h` | open | `results/cells/ADAUSDT_vwap_reversion_4h.json` |
| [ ] `ADAUSDT/vwap_reversion/1d` | open | `results/cells/ADAUSDT_vwap_reversion_1d.json` |
| [ ] `ADAUSDT/vwap_reversion/1w` | open | `results/cells/ADAUSDT_vwap_reversion_1w.json` |
| [ ] `ADAUSDT/momentum_12_1/15m` | open | `results/cells/ADAUSDT_momentum_12_1_15m.json` |
| [ ] `ADAUSDT/momentum_12_1/1h` | open | `results/cells/ADAUSDT_momentum_12_1_1h.json` |
| [ ] `ADAUSDT/momentum_12_1/4h` | open | `results/cells/ADAUSDT_momentum_12_1_4h.json` |
| [ ] `ADAUSDT/momentum_12_1/1d` | open | `results/cells/ADAUSDT_momentum_12_1_1d.json` |
| [ ] `ADAUSDT/momentum_12_1/1w` | open | `results/cells/ADAUSDT_momentum_12_1_1w.json` |
| [ ] `ADAUSDT/gap_fade/15m` | open | `results/cells/ADAUSDT_gap_fade_15m.json` |
| [ ] `ADAUSDT/gap_fade/1h` | open | `results/cells/ADAUSDT_gap_fade_1h.json` |
| [ ] `ADAUSDT/gap_fade/4h` | open | `results/cells/ADAUSDT_gap_fade_4h.json` |
| [ ] `ADAUSDT/gap_fade/1d` | open | `results/cells/ADAUSDT_gap_fade_1d.json` |
| [ ] `ADAUSDT/gap_fade/1w` | open | `results/cells/ADAUSDT_gap_fade_1w.json` |

## LINKUSDT - 0/50 worked

| cell | status | artifact |
|---|---|---|
| [ ] `LINKUSDT/trend_pullback/15m` | open | `results/cells/LINKUSDT_trend_pullback_15m.json` |
| [ ] `LINKUSDT/trend_pullback/1h` | open | `results/cells/LINKUSDT_trend_pullback_1h.json` |
| [ ] `LINKUSDT/trend_pullback/4h` | open | `results/cells/LINKUSDT_trend_pullback_4h.json` |
| [ ] `LINKUSDT/trend_pullback/1d` | open | `results/cells/LINKUSDT_trend_pullback_1d.json` |
| [ ] `LINKUSDT/trend_pullback/1w` | open | `results/cells/LINKUSDT_trend_pullback_1w.json` |
| [ ] `LINKUSDT/rsi2_pullback/15m` | open | `results/cells/LINKUSDT_rsi2_pullback_15m.json` |
| [ ] `LINKUSDT/rsi2_pullback/1h` | open | `results/cells/LINKUSDT_rsi2_pullback_1h.json` |
| [ ] `LINKUSDT/rsi2_pullback/4h` | open | `results/cells/LINKUSDT_rsi2_pullback_4h.json` |
| [ ] `LINKUSDT/rsi2_pullback/1d` | open | `results/cells/LINKUSDT_rsi2_pullback_1d.json` |
| [ ] `LINKUSDT/rsi2_pullback/1w` | open | `results/cells/LINKUSDT_rsi2_pullback_1w.json` |
| [ ] `LINKUSDT/vol_compression/15m` | open | `results/cells/LINKUSDT_vol_compression_15m.json` |
| [ ] `LINKUSDT/vol_compression/1h` | open | `results/cells/LINKUSDT_vol_compression_1h.json` |
| [ ] `LINKUSDT/vol_compression/4h` | open | `results/cells/LINKUSDT_vol_compression_4h.json` |
| [ ] `LINKUSDT/vol_compression/1d` | open | `results/cells/LINKUSDT_vol_compression_1d.json` |
| [ ] `LINKUSDT/vol_compression/1w` | open | `results/cells/LINKUSDT_vol_compression_1w.json` |
| [ ] `LINKUSDT/breakout/15m` | open | `results/cells/LINKUSDT_breakout_15m.json` |
| [ ] `LINKUSDT/breakout/1h` | open | `results/cells/LINKUSDT_breakout_1h.json` |
| [ ] `LINKUSDT/breakout/4h` | open | `results/cells/LINKUSDT_breakout_4h.json` |
| [ ] `LINKUSDT/breakout/1d` | open | `results/cells/LINKUSDT_breakout_1d.json` |
| [ ] `LINKUSDT/breakout/1w` | open | `results/cells/LINKUSDT_breakout_1w.json` |
| [ ] `LINKUSDT/donchian/15m` | open | `results/cells/LINKUSDT_donchian_15m.json` |
| [ ] `LINKUSDT/donchian/1h` | open | `results/cells/LINKUSDT_donchian_1h.json` |
| [ ] `LINKUSDT/donchian/4h` | open | `results/cells/LINKUSDT_donchian_4h.json` |
| [ ] `LINKUSDT/donchian/1d` | open | `results/cells/LINKUSDT_donchian_1d.json` |
| [ ] `LINKUSDT/donchian/1w` | open | `results/cells/LINKUSDT_donchian_1w.json` |
| [ ] `LINKUSDT/ma_cross/15m` | open | `results/cells/LINKUSDT_ma_cross_15m.json` |
| [ ] `LINKUSDT/ma_cross/1h` | open | `results/cells/LINKUSDT_ma_cross_1h.json` |
| [ ] `LINKUSDT/ma_cross/4h` | open | `results/cells/LINKUSDT_ma_cross_4h.json` |
| [ ] `LINKUSDT/ma_cross/1d` | open | `results/cells/LINKUSDT_ma_cross_1d.json` |
| [ ] `LINKUSDT/ma_cross/1w` | open | `results/cells/LINKUSDT_ma_cross_1w.json` |
| [ ] `LINKUSDT/bb_meanrev/15m` | open | `results/cells/LINKUSDT_bb_meanrev_15m.json` |
| [ ] `LINKUSDT/bb_meanrev/1h` | open | `results/cells/LINKUSDT_bb_meanrev_1h.json` |
| [ ] `LINKUSDT/bb_meanrev/4h` | open | `results/cells/LINKUSDT_bb_meanrev_4h.json` |
| [ ] `LINKUSDT/bb_meanrev/1d` | open | `results/cells/LINKUSDT_bb_meanrev_1d.json` |
| [ ] `LINKUSDT/bb_meanrev/1w` | open | `results/cells/LINKUSDT_bb_meanrev_1w.json` |
| [ ] `LINKUSDT/vwap_reversion/15m` | open | `results/cells/LINKUSDT_vwap_reversion_15m.json` |
| [ ] `LINKUSDT/vwap_reversion/1h` | open | `results/cells/LINKUSDT_vwap_reversion_1h.json` |
| [ ] `LINKUSDT/vwap_reversion/4h` | open | `results/cells/LINKUSDT_vwap_reversion_4h.json` |
| [ ] `LINKUSDT/vwap_reversion/1d` | open | `results/cells/LINKUSDT_vwap_reversion_1d.json` |
| [ ] `LINKUSDT/vwap_reversion/1w` | open | `results/cells/LINKUSDT_vwap_reversion_1w.json` |
| [ ] `LINKUSDT/momentum_12_1/15m` | open | `results/cells/LINKUSDT_momentum_12_1_15m.json` |
| [ ] `LINKUSDT/momentum_12_1/1h` | open | `results/cells/LINKUSDT_momentum_12_1_1h.json` |
| [ ] `LINKUSDT/momentum_12_1/4h` | open | `results/cells/LINKUSDT_momentum_12_1_4h.json` |
| [ ] `LINKUSDT/momentum_12_1/1d` | open | `results/cells/LINKUSDT_momentum_12_1_1d.json` |
| [ ] `LINKUSDT/momentum_12_1/1w` | open | `results/cells/LINKUSDT_momentum_12_1_1w.json` |
| [ ] `LINKUSDT/gap_fade/15m` | open | `results/cells/LINKUSDT_gap_fade_15m.json` |
| [ ] `LINKUSDT/gap_fade/1h` | open | `results/cells/LINKUSDT_gap_fade_1h.json` |
| [ ] `LINKUSDT/gap_fade/4h` | open | `results/cells/LINKUSDT_gap_fade_4h.json` |
| [ ] `LINKUSDT/gap_fade/1d` | open | `results/cells/LINKUSDT_gap_fade_1d.json` |
| [ ] `LINKUSDT/gap_fade/1w` | open | `results/cells/LINKUSDT_gap_fade_1w.json` |

## SPY - 0/50 worked

| cell | status | artifact |
|---|---|---|
| [ ] `SPY/trend_pullback/15m` | open | `results/cells/SPY_trend_pullback_15m.json` |
| [ ] `SPY/trend_pullback/1h` | open | `results/cells/SPY_trend_pullback_1h.json` |
| [ ] `SPY/trend_pullback/4h` | open | `results/cells/SPY_trend_pullback_4h.json` |
| [ ] `SPY/trend_pullback/1d` | open | `results/cells/SPY_trend_pullback_1d.json` |
| [ ] `SPY/trend_pullback/1w` | open | `results/cells/SPY_trend_pullback_1w.json` |
| [ ] `SPY/rsi2_pullback/15m` | open | `results/cells/SPY_rsi2_pullback_15m.json` |
| [ ] `SPY/rsi2_pullback/1h` | open | `results/cells/SPY_rsi2_pullback_1h.json` |
| [ ] `SPY/rsi2_pullback/4h` | open | `results/cells/SPY_rsi2_pullback_4h.json` |
| [ ] `SPY/rsi2_pullback/1d` | open | `results/cells/SPY_rsi2_pullback_1d.json` |
| [ ] `SPY/rsi2_pullback/1w` | open | `results/cells/SPY_rsi2_pullback_1w.json` |
| [ ] `SPY/vol_compression/15m` | open | `results/cells/SPY_vol_compression_15m.json` |
| [ ] `SPY/vol_compression/1h` | open | `results/cells/SPY_vol_compression_1h.json` |
| [ ] `SPY/vol_compression/4h` | open | `results/cells/SPY_vol_compression_4h.json` |
| [ ] `SPY/vol_compression/1d` | open | `results/cells/SPY_vol_compression_1d.json` |
| [ ] `SPY/vol_compression/1w` | open | `results/cells/SPY_vol_compression_1w.json` |
| [ ] `SPY/breakout/15m` | open | `results/cells/SPY_breakout_15m.json` |
| [ ] `SPY/breakout/1h` | open | `results/cells/SPY_breakout_1h.json` |
| [ ] `SPY/breakout/4h` | open | `results/cells/SPY_breakout_4h.json` |
| [ ] `SPY/breakout/1d` | open | `results/cells/SPY_breakout_1d.json` |
| [ ] `SPY/breakout/1w` | open | `results/cells/SPY_breakout_1w.json` |
| [ ] `SPY/donchian/15m` | open | `results/cells/SPY_donchian_15m.json` |
| [ ] `SPY/donchian/1h` | open | `results/cells/SPY_donchian_1h.json` |
| [ ] `SPY/donchian/4h` | open | `results/cells/SPY_donchian_4h.json` |
| [ ] `SPY/donchian/1d` | open | `results/cells/SPY_donchian_1d.json` |
| [ ] `SPY/donchian/1w` | open | `results/cells/SPY_donchian_1w.json` |
| [ ] `SPY/ma_cross/15m` | open | `results/cells/SPY_ma_cross_15m.json` |
| [ ] `SPY/ma_cross/1h` | open | `results/cells/SPY_ma_cross_1h.json` |
| [ ] `SPY/ma_cross/4h` | open | `results/cells/SPY_ma_cross_4h.json` |
| [ ] `SPY/ma_cross/1d` | open | `results/cells/SPY_ma_cross_1d.json` |
| [ ] `SPY/ma_cross/1w` | open | `results/cells/SPY_ma_cross_1w.json` |
| [ ] `SPY/bb_meanrev/15m` | open | `results/cells/SPY_bb_meanrev_15m.json` |
| [ ] `SPY/bb_meanrev/1h` | open | `results/cells/SPY_bb_meanrev_1h.json` |
| [ ] `SPY/bb_meanrev/4h` | open | `results/cells/SPY_bb_meanrev_4h.json` |
| [ ] `SPY/bb_meanrev/1d` | open | `results/cells/SPY_bb_meanrev_1d.json` |
| [ ] `SPY/bb_meanrev/1w` | open | `results/cells/SPY_bb_meanrev_1w.json` |
| [ ] `SPY/vwap_reversion/15m` | open | `results/cells/SPY_vwap_reversion_15m.json` |
| [ ] `SPY/vwap_reversion/1h` | open | `results/cells/SPY_vwap_reversion_1h.json` |
| [ ] `SPY/vwap_reversion/4h` | open | `results/cells/SPY_vwap_reversion_4h.json` |
| [ ] `SPY/vwap_reversion/1d` | open | `results/cells/SPY_vwap_reversion_1d.json` |
| [ ] `SPY/vwap_reversion/1w` | open | `results/cells/SPY_vwap_reversion_1w.json` |
| [ ] `SPY/momentum_12_1/15m` | open | `results/cells/SPY_momentum_12_1_15m.json` |
| [ ] `SPY/momentum_12_1/1h` | open | `results/cells/SPY_momentum_12_1_1h.json` |
| [ ] `SPY/momentum_12_1/4h` | open | `results/cells/SPY_momentum_12_1_4h.json` |
| [ ] `SPY/momentum_12_1/1d` | open | `results/cells/SPY_momentum_12_1_1d.json` |
| [ ] `SPY/momentum_12_1/1w` | open | `results/cells/SPY_momentum_12_1_1w.json` |
| [ ] `SPY/gap_fade/15m` | open | `results/cells/SPY_gap_fade_15m.json` |
| [ ] `SPY/gap_fade/1h` | open | `results/cells/SPY_gap_fade_1h.json` |
| [ ] `SPY/gap_fade/4h` | open | `results/cells/SPY_gap_fade_4h.json` |
| [ ] `SPY/gap_fade/1d` | open | `results/cells/SPY_gap_fade_1d.json` |
| [ ] `SPY/gap_fade/1w` | open | `results/cells/SPY_gap_fade_1w.json` |

## QQQ - 0/50 worked

| cell | status | artifact |
|---|---|---|
| [ ] `QQQ/trend_pullback/15m` | open | `results/cells/QQQ_trend_pullback_15m.json` |
| [ ] `QQQ/trend_pullback/1h` | open | `results/cells/QQQ_trend_pullback_1h.json` |
| [ ] `QQQ/trend_pullback/4h` | open | `results/cells/QQQ_trend_pullback_4h.json` |
| [ ] `QQQ/trend_pullback/1d` | open | `results/cells/QQQ_trend_pullback_1d.json` |
| [ ] `QQQ/trend_pullback/1w` | open | `results/cells/QQQ_trend_pullback_1w.json` |
| [ ] `QQQ/rsi2_pullback/15m` | open | `results/cells/QQQ_rsi2_pullback_15m.json` |
| [ ] `QQQ/rsi2_pullback/1h` | open | `results/cells/QQQ_rsi2_pullback_1h.json` |
| [ ] `QQQ/rsi2_pullback/4h` | open | `results/cells/QQQ_rsi2_pullback_4h.json` |
| [ ] `QQQ/rsi2_pullback/1d` | open | `results/cells/QQQ_rsi2_pullback_1d.json` |
| [ ] `QQQ/rsi2_pullback/1w` | open | `results/cells/QQQ_rsi2_pullback_1w.json` |
| [ ] `QQQ/vol_compression/15m` | open | `results/cells/QQQ_vol_compression_15m.json` |
| [ ] `QQQ/vol_compression/1h` | open | `results/cells/QQQ_vol_compression_1h.json` |
| [ ] `QQQ/vol_compression/4h` | open | `results/cells/QQQ_vol_compression_4h.json` |
| [ ] `QQQ/vol_compression/1d` | open | `results/cells/QQQ_vol_compression_1d.json` |
| [ ] `QQQ/vol_compression/1w` | open | `results/cells/QQQ_vol_compression_1w.json` |
| [ ] `QQQ/breakout/15m` | open | `results/cells/QQQ_breakout_15m.json` |
| [ ] `QQQ/breakout/1h` | open | `results/cells/QQQ_breakout_1h.json` |
| [ ] `QQQ/breakout/4h` | open | `results/cells/QQQ_breakout_4h.json` |
| [ ] `QQQ/breakout/1d` | open | `results/cells/QQQ_breakout_1d.json` |
| [ ] `QQQ/breakout/1w` | open | `results/cells/QQQ_breakout_1w.json` |
| [ ] `QQQ/donchian/15m` | open | `results/cells/QQQ_donchian_15m.json` |
| [ ] `QQQ/donchian/1h` | open | `results/cells/QQQ_donchian_1h.json` |
| [ ] `QQQ/donchian/4h` | open | `results/cells/QQQ_donchian_4h.json` |
| [ ] `QQQ/donchian/1d` | open | `results/cells/QQQ_donchian_1d.json` |
| [ ] `QQQ/donchian/1w` | open | `results/cells/QQQ_donchian_1w.json` |
| [ ] `QQQ/ma_cross/15m` | open | `results/cells/QQQ_ma_cross_15m.json` |
| [ ] `QQQ/ma_cross/1h` | open | `results/cells/QQQ_ma_cross_1h.json` |
| [ ] `QQQ/ma_cross/4h` | open | `results/cells/QQQ_ma_cross_4h.json` |
| [ ] `QQQ/ma_cross/1d` | open | `results/cells/QQQ_ma_cross_1d.json` |
| [ ] `QQQ/ma_cross/1w` | open | `results/cells/QQQ_ma_cross_1w.json` |
| [ ] `QQQ/bb_meanrev/15m` | open | `results/cells/QQQ_bb_meanrev_15m.json` |
| [ ] `QQQ/bb_meanrev/1h` | open | `results/cells/QQQ_bb_meanrev_1h.json` |
| [ ] `QQQ/bb_meanrev/4h` | open | `results/cells/QQQ_bb_meanrev_4h.json` |
| [ ] `QQQ/bb_meanrev/1d` | open | `results/cells/QQQ_bb_meanrev_1d.json` |
| [ ] `QQQ/bb_meanrev/1w` | open | `results/cells/QQQ_bb_meanrev_1w.json` |
| [ ] `QQQ/vwap_reversion/15m` | open | `results/cells/QQQ_vwap_reversion_15m.json` |
| [ ] `QQQ/vwap_reversion/1h` | open | `results/cells/QQQ_vwap_reversion_1h.json` |
| [ ] `QQQ/vwap_reversion/4h` | open | `results/cells/QQQ_vwap_reversion_4h.json` |
| [ ] `QQQ/vwap_reversion/1d` | open | `results/cells/QQQ_vwap_reversion_1d.json` |
| [ ] `QQQ/vwap_reversion/1w` | open | `results/cells/QQQ_vwap_reversion_1w.json` |
| [ ] `QQQ/momentum_12_1/15m` | open | `results/cells/QQQ_momentum_12_1_15m.json` |
| [ ] `QQQ/momentum_12_1/1h` | open | `results/cells/QQQ_momentum_12_1_1h.json` |
| [ ] `QQQ/momentum_12_1/4h` | open | `results/cells/QQQ_momentum_12_1_4h.json` |
| [ ] `QQQ/momentum_12_1/1d` | open | `results/cells/QQQ_momentum_12_1_1d.json` |
| [ ] `QQQ/momentum_12_1/1w` | open | `results/cells/QQQ_momentum_12_1_1w.json` |
| [ ] `QQQ/gap_fade/15m` | open | `results/cells/QQQ_gap_fade_15m.json` |
| [ ] `QQQ/gap_fade/1h` | open | `results/cells/QQQ_gap_fade_1h.json` |
| [ ] `QQQ/gap_fade/4h` | open | `results/cells/QQQ_gap_fade_4h.json` |
| [ ] `QQQ/gap_fade/1d` | open | `results/cells/QQQ_gap_fade_1d.json` |
| [ ] `QQQ/gap_fade/1w` | open | `results/cells/QQQ_gap_fade_1w.json` |

## IWM - 0/50 worked

| cell | status | artifact |
|---|---|---|
| [ ] `IWM/trend_pullback/15m` | open | `results/cells/IWM_trend_pullback_15m.json` |
| [ ] `IWM/trend_pullback/1h` | open | `results/cells/IWM_trend_pullback_1h.json` |
| [ ] `IWM/trend_pullback/4h` | open | `results/cells/IWM_trend_pullback_4h.json` |
| [ ] `IWM/trend_pullback/1d` | open | `results/cells/IWM_trend_pullback_1d.json` |
| [ ] `IWM/trend_pullback/1w` | open | `results/cells/IWM_trend_pullback_1w.json` |
| [ ] `IWM/rsi2_pullback/15m` | open | `results/cells/IWM_rsi2_pullback_15m.json` |
| [ ] `IWM/rsi2_pullback/1h` | open | `results/cells/IWM_rsi2_pullback_1h.json` |
| [ ] `IWM/rsi2_pullback/4h` | open | `results/cells/IWM_rsi2_pullback_4h.json` |
| [ ] `IWM/rsi2_pullback/1d` | open | `results/cells/IWM_rsi2_pullback_1d.json` |
| [ ] `IWM/rsi2_pullback/1w` | open | `results/cells/IWM_rsi2_pullback_1w.json` |
| [ ] `IWM/vol_compression/15m` | open | `results/cells/IWM_vol_compression_15m.json` |
| [ ] `IWM/vol_compression/1h` | open | `results/cells/IWM_vol_compression_1h.json` |
| [ ] `IWM/vol_compression/4h` | open | `results/cells/IWM_vol_compression_4h.json` |
| [ ] `IWM/vol_compression/1d` | open | `results/cells/IWM_vol_compression_1d.json` |
| [ ] `IWM/vol_compression/1w` | open | `results/cells/IWM_vol_compression_1w.json` |
| [ ] `IWM/breakout/15m` | open | `results/cells/IWM_breakout_15m.json` |
| [ ] `IWM/breakout/1h` | open | `results/cells/IWM_breakout_1h.json` |
| [ ] `IWM/breakout/4h` | open | `results/cells/IWM_breakout_4h.json` |
| [ ] `IWM/breakout/1d` | open | `results/cells/IWM_breakout_1d.json` |
| [ ] `IWM/breakout/1w` | open | `results/cells/IWM_breakout_1w.json` |
| [ ] `IWM/donchian/15m` | open | `results/cells/IWM_donchian_15m.json` |
| [ ] `IWM/donchian/1h` | open | `results/cells/IWM_donchian_1h.json` |
| [ ] `IWM/donchian/4h` | open | `results/cells/IWM_donchian_4h.json` |
| [ ] `IWM/donchian/1d` | open | `results/cells/IWM_donchian_1d.json` |
| [ ] `IWM/donchian/1w` | open | `results/cells/IWM_donchian_1w.json` |
| [ ] `IWM/ma_cross/15m` | open | `results/cells/IWM_ma_cross_15m.json` |
| [ ] `IWM/ma_cross/1h` | open | `results/cells/IWM_ma_cross_1h.json` |
| [ ] `IWM/ma_cross/4h` | open | `results/cells/IWM_ma_cross_4h.json` |
| [ ] `IWM/ma_cross/1d` | open | `results/cells/IWM_ma_cross_1d.json` |
| [ ] `IWM/ma_cross/1w` | open | `results/cells/IWM_ma_cross_1w.json` |
| [ ] `IWM/bb_meanrev/15m` | open | `results/cells/IWM_bb_meanrev_15m.json` |
| [ ] `IWM/bb_meanrev/1h` | open | `results/cells/IWM_bb_meanrev_1h.json` |
| [ ] `IWM/bb_meanrev/4h` | open | `results/cells/IWM_bb_meanrev_4h.json` |
| [ ] `IWM/bb_meanrev/1d` | open | `results/cells/IWM_bb_meanrev_1d.json` |
| [ ] `IWM/bb_meanrev/1w` | open | `results/cells/IWM_bb_meanrev_1w.json` |
| [ ] `IWM/vwap_reversion/15m` | open | `results/cells/IWM_vwap_reversion_15m.json` |
| [ ] `IWM/vwap_reversion/1h` | open | `results/cells/IWM_vwap_reversion_1h.json` |
| [ ] `IWM/vwap_reversion/4h` | open | `results/cells/IWM_vwap_reversion_4h.json` |
| [ ] `IWM/vwap_reversion/1d` | open | `results/cells/IWM_vwap_reversion_1d.json` |
| [ ] `IWM/vwap_reversion/1w` | open | `results/cells/IWM_vwap_reversion_1w.json` |
| [ ] `IWM/momentum_12_1/15m` | open | `results/cells/IWM_momentum_12_1_15m.json` |
| [ ] `IWM/momentum_12_1/1h` | open | `results/cells/IWM_momentum_12_1_1h.json` |
| [ ] `IWM/momentum_12_1/4h` | open | `results/cells/IWM_momentum_12_1_4h.json` |
| [ ] `IWM/momentum_12_1/1d` | open | `results/cells/IWM_momentum_12_1_1d.json` |
| [ ] `IWM/momentum_12_1/1w` | open | `results/cells/IWM_momentum_12_1_1w.json` |
| [ ] `IWM/gap_fade/15m` | open | `results/cells/IWM_gap_fade_15m.json` |
| [ ] `IWM/gap_fade/1h` | open | `results/cells/IWM_gap_fade_1h.json` |
| [ ] `IWM/gap_fade/4h` | open | `results/cells/IWM_gap_fade_4h.json` |
| [ ] `IWM/gap_fade/1d` | open | `results/cells/IWM_gap_fade_1d.json` |
| [ ] `IWM/gap_fade/1w` | open | `results/cells/IWM_gap_fade_1w.json` |

## AAPL - 0/50 worked

| cell | status | artifact |
|---|---|---|
| [ ] `AAPL/trend_pullback/15m` | open | `results/cells/AAPL_trend_pullback_15m.json` |
| [ ] `AAPL/trend_pullback/1h` | open | `results/cells/AAPL_trend_pullback_1h.json` |
| [ ] `AAPL/trend_pullback/4h` | open | `results/cells/AAPL_trend_pullback_4h.json` |
| [ ] `AAPL/trend_pullback/1d` | open | `results/cells/AAPL_trend_pullback_1d.json` |
| [ ] `AAPL/trend_pullback/1w` | open | `results/cells/AAPL_trend_pullback_1w.json` |
| [ ] `AAPL/rsi2_pullback/15m` | open | `results/cells/AAPL_rsi2_pullback_15m.json` |
| [ ] `AAPL/rsi2_pullback/1h` | open | `results/cells/AAPL_rsi2_pullback_1h.json` |
| [ ] `AAPL/rsi2_pullback/4h` | open | `results/cells/AAPL_rsi2_pullback_4h.json` |
| [ ] `AAPL/rsi2_pullback/1d` | open | `results/cells/AAPL_rsi2_pullback_1d.json` |
| [ ] `AAPL/rsi2_pullback/1w` | open | `results/cells/AAPL_rsi2_pullback_1w.json` |
| [ ] `AAPL/vol_compression/15m` | open | `results/cells/AAPL_vol_compression_15m.json` |
| [ ] `AAPL/vol_compression/1h` | open | `results/cells/AAPL_vol_compression_1h.json` |
| [ ] `AAPL/vol_compression/4h` | open | `results/cells/AAPL_vol_compression_4h.json` |
| [ ] `AAPL/vol_compression/1d` | open | `results/cells/AAPL_vol_compression_1d.json` |
| [ ] `AAPL/vol_compression/1w` | open | `results/cells/AAPL_vol_compression_1w.json` |
| [ ] `AAPL/breakout/15m` | open | `results/cells/AAPL_breakout_15m.json` |
| [ ] `AAPL/breakout/1h` | open | `results/cells/AAPL_breakout_1h.json` |
| [ ] `AAPL/breakout/4h` | open | `results/cells/AAPL_breakout_4h.json` |
| [ ] `AAPL/breakout/1d` | open | `results/cells/AAPL_breakout_1d.json` |
| [ ] `AAPL/breakout/1w` | open | `results/cells/AAPL_breakout_1w.json` |
| [ ] `AAPL/donchian/15m` | open | `results/cells/AAPL_donchian_15m.json` |
| [ ] `AAPL/donchian/1h` | open | `results/cells/AAPL_donchian_1h.json` |
| [ ] `AAPL/donchian/4h` | open | `results/cells/AAPL_donchian_4h.json` |
| [ ] `AAPL/donchian/1d` | open | `results/cells/AAPL_donchian_1d.json` |
| [ ] `AAPL/donchian/1w` | open | `results/cells/AAPL_donchian_1w.json` |
| [ ] `AAPL/ma_cross/15m` | open | `results/cells/AAPL_ma_cross_15m.json` |
| [ ] `AAPL/ma_cross/1h` | open | `results/cells/AAPL_ma_cross_1h.json` |
| [ ] `AAPL/ma_cross/4h` | open | `results/cells/AAPL_ma_cross_4h.json` |
| [ ] `AAPL/ma_cross/1d` | open | `results/cells/AAPL_ma_cross_1d.json` |
| [ ] `AAPL/ma_cross/1w` | open | `results/cells/AAPL_ma_cross_1w.json` |
| [ ] `AAPL/bb_meanrev/15m` | open | `results/cells/AAPL_bb_meanrev_15m.json` |
| [ ] `AAPL/bb_meanrev/1h` | open | `results/cells/AAPL_bb_meanrev_1h.json` |
| [ ] `AAPL/bb_meanrev/4h` | open | `results/cells/AAPL_bb_meanrev_4h.json` |
| [ ] `AAPL/bb_meanrev/1d` | open | `results/cells/AAPL_bb_meanrev_1d.json` |
| [ ] `AAPL/bb_meanrev/1w` | open | `results/cells/AAPL_bb_meanrev_1w.json` |
| [ ] `AAPL/vwap_reversion/15m` | open | `results/cells/AAPL_vwap_reversion_15m.json` |
| [ ] `AAPL/vwap_reversion/1h` | open | `results/cells/AAPL_vwap_reversion_1h.json` |
| [ ] `AAPL/vwap_reversion/4h` | open | `results/cells/AAPL_vwap_reversion_4h.json` |
| [ ] `AAPL/vwap_reversion/1d` | open | `results/cells/AAPL_vwap_reversion_1d.json` |
| [ ] `AAPL/vwap_reversion/1w` | open | `results/cells/AAPL_vwap_reversion_1w.json` |
| [ ] `AAPL/momentum_12_1/15m` | open | `results/cells/AAPL_momentum_12_1_15m.json` |
| [ ] `AAPL/momentum_12_1/1h` | open | `results/cells/AAPL_momentum_12_1_1h.json` |
| [ ] `AAPL/momentum_12_1/4h` | open | `results/cells/AAPL_momentum_12_1_4h.json` |
| [ ] `AAPL/momentum_12_1/1d` | open | `results/cells/AAPL_momentum_12_1_1d.json` |
| [ ] `AAPL/momentum_12_1/1w` | open | `results/cells/AAPL_momentum_12_1_1w.json` |
| [ ] `AAPL/gap_fade/15m` | open | `results/cells/AAPL_gap_fade_15m.json` |
| [ ] `AAPL/gap_fade/1h` | open | `results/cells/AAPL_gap_fade_1h.json` |
| [ ] `AAPL/gap_fade/4h` | open | `results/cells/AAPL_gap_fade_4h.json` |
| [ ] `AAPL/gap_fade/1d` | open | `results/cells/AAPL_gap_fade_1d.json` |
| [ ] `AAPL/gap_fade/1w` | open | `results/cells/AAPL_gap_fade_1w.json` |

## MSFT - 0/50 worked

| cell | status | artifact |
|---|---|---|
| [ ] `MSFT/trend_pullback/15m` | open | `results/cells/MSFT_trend_pullback_15m.json` |
| [ ] `MSFT/trend_pullback/1h` | open | `results/cells/MSFT_trend_pullback_1h.json` |
| [ ] `MSFT/trend_pullback/4h` | open | `results/cells/MSFT_trend_pullback_4h.json` |
| [ ] `MSFT/trend_pullback/1d` | open | `results/cells/MSFT_trend_pullback_1d.json` |
| [ ] `MSFT/trend_pullback/1w` | open | `results/cells/MSFT_trend_pullback_1w.json` |
| [ ] `MSFT/rsi2_pullback/15m` | open | `results/cells/MSFT_rsi2_pullback_15m.json` |
| [ ] `MSFT/rsi2_pullback/1h` | open | `results/cells/MSFT_rsi2_pullback_1h.json` |
| [ ] `MSFT/rsi2_pullback/4h` | open | `results/cells/MSFT_rsi2_pullback_4h.json` |
| [ ] `MSFT/rsi2_pullback/1d` | open | `results/cells/MSFT_rsi2_pullback_1d.json` |
| [ ] `MSFT/rsi2_pullback/1w` | open | `results/cells/MSFT_rsi2_pullback_1w.json` |
| [ ] `MSFT/vol_compression/15m` | open | `results/cells/MSFT_vol_compression_15m.json` |
| [ ] `MSFT/vol_compression/1h` | open | `results/cells/MSFT_vol_compression_1h.json` |
| [ ] `MSFT/vol_compression/4h` | open | `results/cells/MSFT_vol_compression_4h.json` |
| [ ] `MSFT/vol_compression/1d` | open | `results/cells/MSFT_vol_compression_1d.json` |
| [ ] `MSFT/vol_compression/1w` | open | `results/cells/MSFT_vol_compression_1w.json` |
| [ ] `MSFT/breakout/15m` | open | `results/cells/MSFT_breakout_15m.json` |
| [ ] `MSFT/breakout/1h` | open | `results/cells/MSFT_breakout_1h.json` |
| [ ] `MSFT/breakout/4h` | open | `results/cells/MSFT_breakout_4h.json` |
| [ ] `MSFT/breakout/1d` | open | `results/cells/MSFT_breakout_1d.json` |
| [ ] `MSFT/breakout/1w` | open | `results/cells/MSFT_breakout_1w.json` |
| [ ] `MSFT/donchian/15m` | open | `results/cells/MSFT_donchian_15m.json` |
| [ ] `MSFT/donchian/1h` | open | `results/cells/MSFT_donchian_1h.json` |
| [ ] `MSFT/donchian/4h` | open | `results/cells/MSFT_donchian_4h.json` |
| [ ] `MSFT/donchian/1d` | open | `results/cells/MSFT_donchian_1d.json` |
| [ ] `MSFT/donchian/1w` | open | `results/cells/MSFT_donchian_1w.json` |
| [ ] `MSFT/ma_cross/15m` | open | `results/cells/MSFT_ma_cross_15m.json` |
| [ ] `MSFT/ma_cross/1h` | open | `results/cells/MSFT_ma_cross_1h.json` |
| [ ] `MSFT/ma_cross/4h` | open | `results/cells/MSFT_ma_cross_4h.json` |
| [ ] `MSFT/ma_cross/1d` | open | `results/cells/MSFT_ma_cross_1d.json` |
| [ ] `MSFT/ma_cross/1w` | open | `results/cells/MSFT_ma_cross_1w.json` |
| [ ] `MSFT/bb_meanrev/15m` | open | `results/cells/MSFT_bb_meanrev_15m.json` |
| [ ] `MSFT/bb_meanrev/1h` | open | `results/cells/MSFT_bb_meanrev_1h.json` |
| [ ] `MSFT/bb_meanrev/4h` | open | `results/cells/MSFT_bb_meanrev_4h.json` |
| [ ] `MSFT/bb_meanrev/1d` | open | `results/cells/MSFT_bb_meanrev_1d.json` |
| [ ] `MSFT/bb_meanrev/1w` | open | `results/cells/MSFT_bb_meanrev_1w.json` |
| [ ] `MSFT/vwap_reversion/15m` | open | `results/cells/MSFT_vwap_reversion_15m.json` |
| [ ] `MSFT/vwap_reversion/1h` | open | `results/cells/MSFT_vwap_reversion_1h.json` |
| [ ] `MSFT/vwap_reversion/4h` | open | `results/cells/MSFT_vwap_reversion_4h.json` |
| [ ] `MSFT/vwap_reversion/1d` | open | `results/cells/MSFT_vwap_reversion_1d.json` |
| [ ] `MSFT/vwap_reversion/1w` | open | `results/cells/MSFT_vwap_reversion_1w.json` |
| [ ] `MSFT/momentum_12_1/15m` | open | `results/cells/MSFT_momentum_12_1_15m.json` |
| [ ] `MSFT/momentum_12_1/1h` | open | `results/cells/MSFT_momentum_12_1_1h.json` |
| [ ] `MSFT/momentum_12_1/4h` | open | `results/cells/MSFT_momentum_12_1_4h.json` |
| [ ] `MSFT/momentum_12_1/1d` | open | `results/cells/MSFT_momentum_12_1_1d.json` |
| [ ] `MSFT/momentum_12_1/1w` | open | `results/cells/MSFT_momentum_12_1_1w.json` |
| [ ] `MSFT/gap_fade/15m` | open | `results/cells/MSFT_gap_fade_15m.json` |
| [ ] `MSFT/gap_fade/1h` | open | `results/cells/MSFT_gap_fade_1h.json` |
| [ ] `MSFT/gap_fade/4h` | open | `results/cells/MSFT_gap_fade_4h.json` |
| [ ] `MSFT/gap_fade/1d` | open | `results/cells/MSFT_gap_fade_1d.json` |
| [ ] `MSFT/gap_fade/1w` | open | `results/cells/MSFT_gap_fade_1w.json` |

## NVDA - 0/50 worked

| cell | status | artifact |
|---|---|---|
| [ ] `NVDA/trend_pullback/15m` | open | `results/cells/NVDA_trend_pullback_15m.json` |
| [ ] `NVDA/trend_pullback/1h` | open | `results/cells/NVDA_trend_pullback_1h.json` |
| [ ] `NVDA/trend_pullback/4h` | open | `results/cells/NVDA_trend_pullback_4h.json` |
| [ ] `NVDA/trend_pullback/1d` | open | `results/cells/NVDA_trend_pullback_1d.json` |
| [ ] `NVDA/trend_pullback/1w` | open | `results/cells/NVDA_trend_pullback_1w.json` |
| [ ] `NVDA/rsi2_pullback/15m` | open | `results/cells/NVDA_rsi2_pullback_15m.json` |
| [ ] `NVDA/rsi2_pullback/1h` | open | `results/cells/NVDA_rsi2_pullback_1h.json` |
| [ ] `NVDA/rsi2_pullback/4h` | open | `results/cells/NVDA_rsi2_pullback_4h.json` |
| [ ] `NVDA/rsi2_pullback/1d` | open | `results/cells/NVDA_rsi2_pullback_1d.json` |
| [ ] `NVDA/rsi2_pullback/1w` | open | `results/cells/NVDA_rsi2_pullback_1w.json` |
| [ ] `NVDA/vol_compression/15m` | open | `results/cells/NVDA_vol_compression_15m.json` |
| [ ] `NVDA/vol_compression/1h` | open | `results/cells/NVDA_vol_compression_1h.json` |
| [ ] `NVDA/vol_compression/4h` | open | `results/cells/NVDA_vol_compression_4h.json` |
| [ ] `NVDA/vol_compression/1d` | open | `results/cells/NVDA_vol_compression_1d.json` |
| [ ] `NVDA/vol_compression/1w` | open | `results/cells/NVDA_vol_compression_1w.json` |
| [ ] `NVDA/breakout/15m` | open | `results/cells/NVDA_breakout_15m.json` |
| [ ] `NVDA/breakout/1h` | open | `results/cells/NVDA_breakout_1h.json` |
| [ ] `NVDA/breakout/4h` | open | `results/cells/NVDA_breakout_4h.json` |
| [ ] `NVDA/breakout/1d` | open | `results/cells/NVDA_breakout_1d.json` |
| [ ] `NVDA/breakout/1w` | open | `results/cells/NVDA_breakout_1w.json` |
| [ ] `NVDA/donchian/15m` | open | `results/cells/NVDA_donchian_15m.json` |
| [ ] `NVDA/donchian/1h` | open | `results/cells/NVDA_donchian_1h.json` |
| [ ] `NVDA/donchian/4h` | open | `results/cells/NVDA_donchian_4h.json` |
| [ ] `NVDA/donchian/1d` | open | `results/cells/NVDA_donchian_1d.json` |
| [ ] `NVDA/donchian/1w` | open | `results/cells/NVDA_donchian_1w.json` |
| [ ] `NVDA/ma_cross/15m` | open | `results/cells/NVDA_ma_cross_15m.json` |
| [ ] `NVDA/ma_cross/1h` | open | `results/cells/NVDA_ma_cross_1h.json` |
| [ ] `NVDA/ma_cross/4h` | open | `results/cells/NVDA_ma_cross_4h.json` |
| [ ] `NVDA/ma_cross/1d` | open | `results/cells/NVDA_ma_cross_1d.json` |
| [ ] `NVDA/ma_cross/1w` | open | `results/cells/NVDA_ma_cross_1w.json` |
| [ ] `NVDA/bb_meanrev/15m` | open | `results/cells/NVDA_bb_meanrev_15m.json` |
| [ ] `NVDA/bb_meanrev/1h` | open | `results/cells/NVDA_bb_meanrev_1h.json` |
| [ ] `NVDA/bb_meanrev/4h` | open | `results/cells/NVDA_bb_meanrev_4h.json` |
| [ ] `NVDA/bb_meanrev/1d` | open | `results/cells/NVDA_bb_meanrev_1d.json` |
| [ ] `NVDA/bb_meanrev/1w` | open | `results/cells/NVDA_bb_meanrev_1w.json` |
| [ ] `NVDA/vwap_reversion/15m` | open | `results/cells/NVDA_vwap_reversion_15m.json` |
| [ ] `NVDA/vwap_reversion/1h` | open | `results/cells/NVDA_vwap_reversion_1h.json` |
| [ ] `NVDA/vwap_reversion/4h` | open | `results/cells/NVDA_vwap_reversion_4h.json` |
| [ ] `NVDA/vwap_reversion/1d` | open | `results/cells/NVDA_vwap_reversion_1d.json` |
| [ ] `NVDA/vwap_reversion/1w` | open | `results/cells/NVDA_vwap_reversion_1w.json` |
| [ ] `NVDA/momentum_12_1/15m` | open | `results/cells/NVDA_momentum_12_1_15m.json` |
| [ ] `NVDA/momentum_12_1/1h` | open | `results/cells/NVDA_momentum_12_1_1h.json` |
| [ ] `NVDA/momentum_12_1/4h` | open | `results/cells/NVDA_momentum_12_1_4h.json` |
| [ ] `NVDA/momentum_12_1/1d` | open | `results/cells/NVDA_momentum_12_1_1d.json` |
| [ ] `NVDA/momentum_12_1/1w` | open | `results/cells/NVDA_momentum_12_1_1w.json` |
| [ ] `NVDA/gap_fade/15m` | open | `results/cells/NVDA_gap_fade_15m.json` |
| [ ] `NVDA/gap_fade/1h` | open | `results/cells/NVDA_gap_fade_1h.json` |
| [ ] `NVDA/gap_fade/4h` | open | `results/cells/NVDA_gap_fade_4h.json` |
| [ ] `NVDA/gap_fade/1d` | open | `results/cells/NVDA_gap_fade_1d.json` |
| [ ] `NVDA/gap_fade/1w` | open | `results/cells/NVDA_gap_fade_1w.json` |

## JPM - 0/50 worked

| cell | status | artifact |
|---|---|---|
| [ ] `JPM/trend_pullback/15m` | open | `results/cells/JPM_trend_pullback_15m.json` |
| [ ] `JPM/trend_pullback/1h` | open | `results/cells/JPM_trend_pullback_1h.json` |
| [ ] `JPM/trend_pullback/4h` | open | `results/cells/JPM_trend_pullback_4h.json` |
| [ ] `JPM/trend_pullback/1d` | open | `results/cells/JPM_trend_pullback_1d.json` |
| [ ] `JPM/trend_pullback/1w` | open | `results/cells/JPM_trend_pullback_1w.json` |
| [ ] `JPM/rsi2_pullback/15m` | open | `results/cells/JPM_rsi2_pullback_15m.json` |
| [ ] `JPM/rsi2_pullback/1h` | open | `results/cells/JPM_rsi2_pullback_1h.json` |
| [ ] `JPM/rsi2_pullback/4h` | open | `results/cells/JPM_rsi2_pullback_4h.json` |
| [ ] `JPM/rsi2_pullback/1d` | open | `results/cells/JPM_rsi2_pullback_1d.json` |
| [ ] `JPM/rsi2_pullback/1w` | open | `results/cells/JPM_rsi2_pullback_1w.json` |
| [ ] `JPM/vol_compression/15m` | open | `results/cells/JPM_vol_compression_15m.json` |
| [ ] `JPM/vol_compression/1h` | open | `results/cells/JPM_vol_compression_1h.json` |
| [ ] `JPM/vol_compression/4h` | open | `results/cells/JPM_vol_compression_4h.json` |
| [ ] `JPM/vol_compression/1d` | open | `results/cells/JPM_vol_compression_1d.json` |
| [ ] `JPM/vol_compression/1w` | open | `results/cells/JPM_vol_compression_1w.json` |
| [ ] `JPM/breakout/15m` | open | `results/cells/JPM_breakout_15m.json` |
| [ ] `JPM/breakout/1h` | open | `results/cells/JPM_breakout_1h.json` |
| [ ] `JPM/breakout/4h` | open | `results/cells/JPM_breakout_4h.json` |
| [ ] `JPM/breakout/1d` | open | `results/cells/JPM_breakout_1d.json` |
| [ ] `JPM/breakout/1w` | open | `results/cells/JPM_breakout_1w.json` |
| [ ] `JPM/donchian/15m` | open | `results/cells/JPM_donchian_15m.json` |
| [ ] `JPM/donchian/1h` | open | `results/cells/JPM_donchian_1h.json` |
| [ ] `JPM/donchian/4h` | open | `results/cells/JPM_donchian_4h.json` |
| [ ] `JPM/donchian/1d` | open | `results/cells/JPM_donchian_1d.json` |
| [ ] `JPM/donchian/1w` | open | `results/cells/JPM_donchian_1w.json` |
| [ ] `JPM/ma_cross/15m` | open | `results/cells/JPM_ma_cross_15m.json` |
| [ ] `JPM/ma_cross/1h` | open | `results/cells/JPM_ma_cross_1h.json` |
| [ ] `JPM/ma_cross/4h` | open | `results/cells/JPM_ma_cross_4h.json` |
| [ ] `JPM/ma_cross/1d` | open | `results/cells/JPM_ma_cross_1d.json` |
| [ ] `JPM/ma_cross/1w` | open | `results/cells/JPM_ma_cross_1w.json` |
| [ ] `JPM/bb_meanrev/15m` | open | `results/cells/JPM_bb_meanrev_15m.json` |
| [ ] `JPM/bb_meanrev/1h` | open | `results/cells/JPM_bb_meanrev_1h.json` |
| [ ] `JPM/bb_meanrev/4h` | open | `results/cells/JPM_bb_meanrev_4h.json` |
| [ ] `JPM/bb_meanrev/1d` | open | `results/cells/JPM_bb_meanrev_1d.json` |
| [ ] `JPM/bb_meanrev/1w` | open | `results/cells/JPM_bb_meanrev_1w.json` |
| [ ] `JPM/vwap_reversion/15m` | open | `results/cells/JPM_vwap_reversion_15m.json` |
| [ ] `JPM/vwap_reversion/1h` | open | `results/cells/JPM_vwap_reversion_1h.json` |
| [ ] `JPM/vwap_reversion/4h` | open | `results/cells/JPM_vwap_reversion_4h.json` |
| [ ] `JPM/vwap_reversion/1d` | open | `results/cells/JPM_vwap_reversion_1d.json` |
| [ ] `JPM/vwap_reversion/1w` | open | `results/cells/JPM_vwap_reversion_1w.json` |
| [ ] `JPM/momentum_12_1/15m` | open | `results/cells/JPM_momentum_12_1_15m.json` |
| [ ] `JPM/momentum_12_1/1h` | open | `results/cells/JPM_momentum_12_1_1h.json` |
| [ ] `JPM/momentum_12_1/4h` | open | `results/cells/JPM_momentum_12_1_4h.json` |
| [ ] `JPM/momentum_12_1/1d` | open | `results/cells/JPM_momentum_12_1_1d.json` |
| [ ] `JPM/momentum_12_1/1w` | open | `results/cells/JPM_momentum_12_1_1w.json` |
| [ ] `JPM/gap_fade/15m` | open | `results/cells/JPM_gap_fade_15m.json` |
| [ ] `JPM/gap_fade/1h` | open | `results/cells/JPM_gap_fade_1h.json` |
| [ ] `JPM/gap_fade/4h` | open | `results/cells/JPM_gap_fade_4h.json` |
| [ ] `JPM/gap_fade/1d` | open | `results/cells/JPM_gap_fade_1d.json` |
| [ ] `JPM/gap_fade/1w` | open | `results/cells/JPM_gap_fade_1w.json` |

## XLE - 0/50 worked

| cell | status | artifact |
|---|---|---|
| [ ] `XLE/trend_pullback/15m` | open | `results/cells/XLE_trend_pullback_15m.json` |
| [ ] `XLE/trend_pullback/1h` | open | `results/cells/XLE_trend_pullback_1h.json` |
| [ ] `XLE/trend_pullback/4h` | open | `results/cells/XLE_trend_pullback_4h.json` |
| [ ] `XLE/trend_pullback/1d` | open | `results/cells/XLE_trend_pullback_1d.json` |
| [ ] `XLE/trend_pullback/1w` | open | `results/cells/XLE_trend_pullback_1w.json` |
| [ ] `XLE/rsi2_pullback/15m` | open | `results/cells/XLE_rsi2_pullback_15m.json` |
| [ ] `XLE/rsi2_pullback/1h` | open | `results/cells/XLE_rsi2_pullback_1h.json` |
| [ ] `XLE/rsi2_pullback/4h` | open | `results/cells/XLE_rsi2_pullback_4h.json` |
| [ ] `XLE/rsi2_pullback/1d` | open | `results/cells/XLE_rsi2_pullback_1d.json` |
| [ ] `XLE/rsi2_pullback/1w` | open | `results/cells/XLE_rsi2_pullback_1w.json` |
| [ ] `XLE/vol_compression/15m` | open | `results/cells/XLE_vol_compression_15m.json` |
| [ ] `XLE/vol_compression/1h` | open | `results/cells/XLE_vol_compression_1h.json` |
| [ ] `XLE/vol_compression/4h` | open | `results/cells/XLE_vol_compression_4h.json` |
| [ ] `XLE/vol_compression/1d` | open | `results/cells/XLE_vol_compression_1d.json` |
| [ ] `XLE/vol_compression/1w` | open | `results/cells/XLE_vol_compression_1w.json` |
| [ ] `XLE/breakout/15m` | open | `results/cells/XLE_breakout_15m.json` |
| [ ] `XLE/breakout/1h` | open | `results/cells/XLE_breakout_1h.json` |
| [ ] `XLE/breakout/4h` | open | `results/cells/XLE_breakout_4h.json` |
| [ ] `XLE/breakout/1d` | open | `results/cells/XLE_breakout_1d.json` |
| [ ] `XLE/breakout/1w` | open | `results/cells/XLE_breakout_1w.json` |
| [ ] `XLE/donchian/15m` | open | `results/cells/XLE_donchian_15m.json` |
| [ ] `XLE/donchian/1h` | open | `results/cells/XLE_donchian_1h.json` |
| [ ] `XLE/donchian/4h` | open | `results/cells/XLE_donchian_4h.json` |
| [ ] `XLE/donchian/1d` | open | `results/cells/XLE_donchian_1d.json` |
| [ ] `XLE/donchian/1w` | open | `results/cells/XLE_donchian_1w.json` |
| [ ] `XLE/ma_cross/15m` | open | `results/cells/XLE_ma_cross_15m.json` |
| [ ] `XLE/ma_cross/1h` | open | `results/cells/XLE_ma_cross_1h.json` |
| [ ] `XLE/ma_cross/4h` | open | `results/cells/XLE_ma_cross_4h.json` |
| [ ] `XLE/ma_cross/1d` | open | `results/cells/XLE_ma_cross_1d.json` |
| [ ] `XLE/ma_cross/1w` | open | `results/cells/XLE_ma_cross_1w.json` |
| [ ] `XLE/bb_meanrev/15m` | open | `results/cells/XLE_bb_meanrev_15m.json` |
| [ ] `XLE/bb_meanrev/1h` | open | `results/cells/XLE_bb_meanrev_1h.json` |
| [ ] `XLE/bb_meanrev/4h` | open | `results/cells/XLE_bb_meanrev_4h.json` |
| [ ] `XLE/bb_meanrev/1d` | open | `results/cells/XLE_bb_meanrev_1d.json` |
| [ ] `XLE/bb_meanrev/1w` | open | `results/cells/XLE_bb_meanrev_1w.json` |
| [ ] `XLE/vwap_reversion/15m` | open | `results/cells/XLE_vwap_reversion_15m.json` |
| [ ] `XLE/vwap_reversion/1h` | open | `results/cells/XLE_vwap_reversion_1h.json` |
| [ ] `XLE/vwap_reversion/4h` | open | `results/cells/XLE_vwap_reversion_4h.json` |
| [ ] `XLE/vwap_reversion/1d` | open | `results/cells/XLE_vwap_reversion_1d.json` |
| [ ] `XLE/vwap_reversion/1w` | open | `results/cells/XLE_vwap_reversion_1w.json` |
| [ ] `XLE/momentum_12_1/15m` | open | `results/cells/XLE_momentum_12_1_15m.json` |
| [ ] `XLE/momentum_12_1/1h` | open | `results/cells/XLE_momentum_12_1_1h.json` |
| [ ] `XLE/momentum_12_1/4h` | open | `results/cells/XLE_momentum_12_1_4h.json` |
| [ ] `XLE/momentum_12_1/1d` | open | `results/cells/XLE_momentum_12_1_1d.json` |
| [ ] `XLE/momentum_12_1/1w` | open | `results/cells/XLE_momentum_12_1_1w.json` |
| [ ] `XLE/gap_fade/15m` | open | `results/cells/XLE_gap_fade_15m.json` |
| [ ] `XLE/gap_fade/1h` | open | `results/cells/XLE_gap_fade_1h.json` |
| [ ] `XLE/gap_fade/4h` | open | `results/cells/XLE_gap_fade_4h.json` |
| [ ] `XLE/gap_fade/1d` | open | `results/cells/XLE_gap_fade_1d.json` |
| [ ] `XLE/gap_fade/1w` | open | `results/cells/XLE_gap_fade_1w.json` |

## GLD - 0/50 worked

| cell | status | artifact |
|---|---|---|
| [ ] `GLD/trend_pullback/15m` | open | `results/cells/GLD_trend_pullback_15m.json` |
| [ ] `GLD/trend_pullback/1h` | open | `results/cells/GLD_trend_pullback_1h.json` |
| [ ] `GLD/trend_pullback/4h` | open | `results/cells/GLD_trend_pullback_4h.json` |
| [ ] `GLD/trend_pullback/1d` | open | `results/cells/GLD_trend_pullback_1d.json` |
| [ ] `GLD/trend_pullback/1w` | open | `results/cells/GLD_trend_pullback_1w.json` |
| [ ] `GLD/rsi2_pullback/15m` | open | `results/cells/GLD_rsi2_pullback_15m.json` |
| [ ] `GLD/rsi2_pullback/1h` | open | `results/cells/GLD_rsi2_pullback_1h.json` |
| [ ] `GLD/rsi2_pullback/4h` | open | `results/cells/GLD_rsi2_pullback_4h.json` |
| [ ] `GLD/rsi2_pullback/1d` | open | `results/cells/GLD_rsi2_pullback_1d.json` |
| [ ] `GLD/rsi2_pullback/1w` | open | `results/cells/GLD_rsi2_pullback_1w.json` |
| [ ] `GLD/vol_compression/15m` | open | `results/cells/GLD_vol_compression_15m.json` |
| [ ] `GLD/vol_compression/1h` | open | `results/cells/GLD_vol_compression_1h.json` |
| [ ] `GLD/vol_compression/4h` | open | `results/cells/GLD_vol_compression_4h.json` |
| [ ] `GLD/vol_compression/1d` | open | `results/cells/GLD_vol_compression_1d.json` |
| [ ] `GLD/vol_compression/1w` | open | `results/cells/GLD_vol_compression_1w.json` |
| [ ] `GLD/breakout/15m` | open | `results/cells/GLD_breakout_15m.json` |
| [ ] `GLD/breakout/1h` | open | `results/cells/GLD_breakout_1h.json` |
| [ ] `GLD/breakout/4h` | open | `results/cells/GLD_breakout_4h.json` |
| [ ] `GLD/breakout/1d` | open | `results/cells/GLD_breakout_1d.json` |
| [ ] `GLD/breakout/1w` | open | `results/cells/GLD_breakout_1w.json` |
| [ ] `GLD/donchian/15m` | open | `results/cells/GLD_donchian_15m.json` |
| [ ] `GLD/donchian/1h` | open | `results/cells/GLD_donchian_1h.json` |
| [ ] `GLD/donchian/4h` | open | `results/cells/GLD_donchian_4h.json` |
| [ ] `GLD/donchian/1d` | open | `results/cells/GLD_donchian_1d.json` |
| [ ] `GLD/donchian/1w` | open | `results/cells/GLD_donchian_1w.json` |
| [ ] `GLD/ma_cross/15m` | open | `results/cells/GLD_ma_cross_15m.json` |
| [ ] `GLD/ma_cross/1h` | open | `results/cells/GLD_ma_cross_1h.json` |
| [ ] `GLD/ma_cross/4h` | open | `results/cells/GLD_ma_cross_4h.json` |
| [ ] `GLD/ma_cross/1d` | open | `results/cells/GLD_ma_cross_1d.json` |
| [ ] `GLD/ma_cross/1w` | open | `results/cells/GLD_ma_cross_1w.json` |
| [ ] `GLD/bb_meanrev/15m` | open | `results/cells/GLD_bb_meanrev_15m.json` |
| [ ] `GLD/bb_meanrev/1h` | open | `results/cells/GLD_bb_meanrev_1h.json` |
| [ ] `GLD/bb_meanrev/4h` | open | `results/cells/GLD_bb_meanrev_4h.json` |
| [ ] `GLD/bb_meanrev/1d` | open | `results/cells/GLD_bb_meanrev_1d.json` |
| [ ] `GLD/bb_meanrev/1w` | open | `results/cells/GLD_bb_meanrev_1w.json` |
| [ ] `GLD/vwap_reversion/15m` | open | `results/cells/GLD_vwap_reversion_15m.json` |
| [ ] `GLD/vwap_reversion/1h` | open | `results/cells/GLD_vwap_reversion_1h.json` |
| [ ] `GLD/vwap_reversion/4h` | open | `results/cells/GLD_vwap_reversion_4h.json` |
| [ ] `GLD/vwap_reversion/1d` | open | `results/cells/GLD_vwap_reversion_1d.json` |
| [ ] `GLD/vwap_reversion/1w` | open | `results/cells/GLD_vwap_reversion_1w.json` |
| [ ] `GLD/momentum_12_1/15m` | open | `results/cells/GLD_momentum_12_1_15m.json` |
| [ ] `GLD/momentum_12_1/1h` | open | `results/cells/GLD_momentum_12_1_1h.json` |
| [ ] `GLD/momentum_12_1/4h` | open | `results/cells/GLD_momentum_12_1_4h.json` |
| [ ] `GLD/momentum_12_1/1d` | open | `results/cells/GLD_momentum_12_1_1d.json` |
| [ ] `GLD/momentum_12_1/1w` | open | `results/cells/GLD_momentum_12_1_1w.json` |
| [ ] `GLD/gap_fade/15m` | open | `results/cells/GLD_gap_fade_15m.json` |
| [ ] `GLD/gap_fade/1h` | open | `results/cells/GLD_gap_fade_1h.json` |
| [ ] `GLD/gap_fade/4h` | open | `results/cells/GLD_gap_fade_4h.json` |
| [ ] `GLD/gap_fade/1d` | open | `results/cells/GLD_gap_fade_1d.json` |
| [ ] `GLD/gap_fade/1w` | open | `results/cells/GLD_gap_fade_1w.json` |

## TLT - 0/50 worked

| cell | status | artifact |
|---|---|---|
| [ ] `TLT/trend_pullback/15m` | open | `results/cells/TLT_trend_pullback_15m.json` |
| [ ] `TLT/trend_pullback/1h` | open | `results/cells/TLT_trend_pullback_1h.json` |
| [ ] `TLT/trend_pullback/4h` | open | `results/cells/TLT_trend_pullback_4h.json` |
| [ ] `TLT/trend_pullback/1d` | open | `results/cells/TLT_trend_pullback_1d.json` |
| [ ] `TLT/trend_pullback/1w` | open | `results/cells/TLT_trend_pullback_1w.json` |
| [ ] `TLT/rsi2_pullback/15m` | open | `results/cells/TLT_rsi2_pullback_15m.json` |
| [ ] `TLT/rsi2_pullback/1h` | open | `results/cells/TLT_rsi2_pullback_1h.json` |
| [ ] `TLT/rsi2_pullback/4h` | open | `results/cells/TLT_rsi2_pullback_4h.json` |
| [ ] `TLT/rsi2_pullback/1d` | open | `results/cells/TLT_rsi2_pullback_1d.json` |
| [ ] `TLT/rsi2_pullback/1w` | open | `results/cells/TLT_rsi2_pullback_1w.json` |
| [ ] `TLT/vol_compression/15m` | open | `results/cells/TLT_vol_compression_15m.json` |
| [ ] `TLT/vol_compression/1h` | open | `results/cells/TLT_vol_compression_1h.json` |
| [ ] `TLT/vol_compression/4h` | open | `results/cells/TLT_vol_compression_4h.json` |
| [ ] `TLT/vol_compression/1d` | open | `results/cells/TLT_vol_compression_1d.json` |
| [ ] `TLT/vol_compression/1w` | open | `results/cells/TLT_vol_compression_1w.json` |
| [ ] `TLT/breakout/15m` | open | `results/cells/TLT_breakout_15m.json` |
| [ ] `TLT/breakout/1h` | open | `results/cells/TLT_breakout_1h.json` |
| [ ] `TLT/breakout/4h` | open | `results/cells/TLT_breakout_4h.json` |
| [ ] `TLT/breakout/1d` | open | `results/cells/TLT_breakout_1d.json` |
| [ ] `TLT/breakout/1w` | open | `results/cells/TLT_breakout_1w.json` |
| [ ] `TLT/donchian/15m` | open | `results/cells/TLT_donchian_15m.json` |
| [ ] `TLT/donchian/1h` | open | `results/cells/TLT_donchian_1h.json` |
| [ ] `TLT/donchian/4h` | open | `results/cells/TLT_donchian_4h.json` |
| [ ] `TLT/donchian/1d` | open | `results/cells/TLT_donchian_1d.json` |
| [ ] `TLT/donchian/1w` | open | `results/cells/TLT_donchian_1w.json` |
| [ ] `TLT/ma_cross/15m` | open | `results/cells/TLT_ma_cross_15m.json` |
| [ ] `TLT/ma_cross/1h` | open | `results/cells/TLT_ma_cross_1h.json` |
| [ ] `TLT/ma_cross/4h` | open | `results/cells/TLT_ma_cross_4h.json` |
| [ ] `TLT/ma_cross/1d` | open | `results/cells/TLT_ma_cross_1d.json` |
| [ ] `TLT/ma_cross/1w` | open | `results/cells/TLT_ma_cross_1w.json` |
| [ ] `TLT/bb_meanrev/15m` | open | `results/cells/TLT_bb_meanrev_15m.json` |
| [ ] `TLT/bb_meanrev/1h` | open | `results/cells/TLT_bb_meanrev_1h.json` |
| [ ] `TLT/bb_meanrev/4h` | open | `results/cells/TLT_bb_meanrev_4h.json` |
| [ ] `TLT/bb_meanrev/1d` | open | `results/cells/TLT_bb_meanrev_1d.json` |
| [ ] `TLT/bb_meanrev/1w` | open | `results/cells/TLT_bb_meanrev_1w.json` |
| [ ] `TLT/vwap_reversion/15m` | open | `results/cells/TLT_vwap_reversion_15m.json` |
| [ ] `TLT/vwap_reversion/1h` | open | `results/cells/TLT_vwap_reversion_1h.json` |
| [ ] `TLT/vwap_reversion/4h` | open | `results/cells/TLT_vwap_reversion_4h.json` |
| [ ] `TLT/vwap_reversion/1d` | open | `results/cells/TLT_vwap_reversion_1d.json` |
| [ ] `TLT/vwap_reversion/1w` | open | `results/cells/TLT_vwap_reversion_1w.json` |
| [ ] `TLT/momentum_12_1/15m` | open | `results/cells/TLT_momentum_12_1_15m.json` |
| [ ] `TLT/momentum_12_1/1h` | open | `results/cells/TLT_momentum_12_1_1h.json` |
| [ ] `TLT/momentum_12_1/4h` | open | `results/cells/TLT_momentum_12_1_4h.json` |
| [ ] `TLT/momentum_12_1/1d` | open | `results/cells/TLT_momentum_12_1_1d.json` |
| [ ] `TLT/momentum_12_1/1w` | open | `results/cells/TLT_momentum_12_1_1w.json` |
| [ ] `TLT/gap_fade/15m` | open | `results/cells/TLT_gap_fade_15m.json` |
| [ ] `TLT/gap_fade/1h` | open | `results/cells/TLT_gap_fade_1h.json` |
| [ ] `TLT/gap_fade/4h` | open | `results/cells/TLT_gap_fade_4h.json` |
| [ ] `TLT/gap_fade/1d` | open | `results/cells/TLT_gap_fade_1d.json` |
| [ ] `TLT/gap_fade/1w` | open | `results/cells/TLT_gap_fade_1w.json` |

## EURUSD - 0/50 worked

| cell | status | artifact |
|---|---|---|
| [ ] `EURUSD/trend_pullback/15m` | open | `results/cells/EURUSD_trend_pullback_15m.json` |
| [ ] `EURUSD/trend_pullback/1h` | open | `results/cells/EURUSD_trend_pullback_1h.json` |
| [ ] `EURUSD/trend_pullback/4h` | open | `results/cells/EURUSD_trend_pullback_4h.json` |
| [ ] `EURUSD/trend_pullback/1d` | open | `results/cells/EURUSD_trend_pullback_1d.json` |
| [ ] `EURUSD/trend_pullback/1w` | open | `results/cells/EURUSD_trend_pullback_1w.json` |
| [ ] `EURUSD/rsi2_pullback/15m` | open | `results/cells/EURUSD_rsi2_pullback_15m.json` |
| [ ] `EURUSD/rsi2_pullback/1h` | open | `results/cells/EURUSD_rsi2_pullback_1h.json` |
| [ ] `EURUSD/rsi2_pullback/4h` | open | `results/cells/EURUSD_rsi2_pullback_4h.json` |
| [ ] `EURUSD/rsi2_pullback/1d` | open | `results/cells/EURUSD_rsi2_pullback_1d.json` |
| [ ] `EURUSD/rsi2_pullback/1w` | open | `results/cells/EURUSD_rsi2_pullback_1w.json` |
| [ ] `EURUSD/vol_compression/15m` | open | `results/cells/EURUSD_vol_compression_15m.json` |
| [ ] `EURUSD/vol_compression/1h` | open | `results/cells/EURUSD_vol_compression_1h.json` |
| [ ] `EURUSD/vol_compression/4h` | open | `results/cells/EURUSD_vol_compression_4h.json` |
| [ ] `EURUSD/vol_compression/1d` | open | `results/cells/EURUSD_vol_compression_1d.json` |
| [ ] `EURUSD/vol_compression/1w` | open | `results/cells/EURUSD_vol_compression_1w.json` |
| [ ] `EURUSD/breakout/15m` | open | `results/cells/EURUSD_breakout_15m.json` |
| [ ] `EURUSD/breakout/1h` | open | `results/cells/EURUSD_breakout_1h.json` |
| [ ] `EURUSD/breakout/4h` | open | `results/cells/EURUSD_breakout_4h.json` |
| [ ] `EURUSD/breakout/1d` | open | `results/cells/EURUSD_breakout_1d.json` |
| [ ] `EURUSD/breakout/1w` | open | `results/cells/EURUSD_breakout_1w.json` |
| [ ] `EURUSD/donchian/15m` | open | `results/cells/EURUSD_donchian_15m.json` |
| [ ] `EURUSD/donchian/1h` | open | `results/cells/EURUSD_donchian_1h.json` |
| [ ] `EURUSD/donchian/4h` | open | `results/cells/EURUSD_donchian_4h.json` |
| [ ] `EURUSD/donchian/1d` | open | `results/cells/EURUSD_donchian_1d.json` |
| [ ] `EURUSD/donchian/1w` | open | `results/cells/EURUSD_donchian_1w.json` |
| [ ] `EURUSD/ma_cross/15m` | open | `results/cells/EURUSD_ma_cross_15m.json` |
| [ ] `EURUSD/ma_cross/1h` | open | `results/cells/EURUSD_ma_cross_1h.json` |
| [ ] `EURUSD/ma_cross/4h` | open | `results/cells/EURUSD_ma_cross_4h.json` |
| [ ] `EURUSD/ma_cross/1d` | open | `results/cells/EURUSD_ma_cross_1d.json` |
| [ ] `EURUSD/ma_cross/1w` | open | `results/cells/EURUSD_ma_cross_1w.json` |
| [ ] `EURUSD/bb_meanrev/15m` | open | `results/cells/EURUSD_bb_meanrev_15m.json` |
| [ ] `EURUSD/bb_meanrev/1h` | open | `results/cells/EURUSD_bb_meanrev_1h.json` |
| [ ] `EURUSD/bb_meanrev/4h` | open | `results/cells/EURUSD_bb_meanrev_4h.json` |
| [ ] `EURUSD/bb_meanrev/1d` | open | `results/cells/EURUSD_bb_meanrev_1d.json` |
| [ ] `EURUSD/bb_meanrev/1w` | open | `results/cells/EURUSD_bb_meanrev_1w.json` |
| [ ] `EURUSD/vwap_reversion/15m` | open | `results/cells/EURUSD_vwap_reversion_15m.json` |
| [ ] `EURUSD/vwap_reversion/1h` | open | `results/cells/EURUSD_vwap_reversion_1h.json` |
| [ ] `EURUSD/vwap_reversion/4h` | open | `results/cells/EURUSD_vwap_reversion_4h.json` |
| [ ] `EURUSD/vwap_reversion/1d` | open | `results/cells/EURUSD_vwap_reversion_1d.json` |
| [ ] `EURUSD/vwap_reversion/1w` | open | `results/cells/EURUSD_vwap_reversion_1w.json` |
| [ ] `EURUSD/momentum_12_1/15m` | open | `results/cells/EURUSD_momentum_12_1_15m.json` |
| [ ] `EURUSD/momentum_12_1/1h` | open | `results/cells/EURUSD_momentum_12_1_1h.json` |
| [ ] `EURUSD/momentum_12_1/4h` | open | `results/cells/EURUSD_momentum_12_1_4h.json` |
| [ ] `EURUSD/momentum_12_1/1d` | open | `results/cells/EURUSD_momentum_12_1_1d.json` |
| [ ] `EURUSD/momentum_12_1/1w` | open | `results/cells/EURUSD_momentum_12_1_1w.json` |
| [ ] `EURUSD/gap_fade/15m` | open | `results/cells/EURUSD_gap_fade_15m.json` |
| [ ] `EURUSD/gap_fade/1h` | open | `results/cells/EURUSD_gap_fade_1h.json` |
| [ ] `EURUSD/gap_fade/4h` | open | `results/cells/EURUSD_gap_fade_4h.json` |
| [ ] `EURUSD/gap_fade/1d` | open | `results/cells/EURUSD_gap_fade_1d.json` |
| [ ] `EURUSD/gap_fade/1w` | open | `results/cells/EURUSD_gap_fade_1w.json` |

## USDJPY - 0/50 worked

| cell | status | artifact |
|---|---|---|
| [ ] `USDJPY/trend_pullback/15m` | open | `results/cells/USDJPY_trend_pullback_15m.json` |
| [ ] `USDJPY/trend_pullback/1h` | open | `results/cells/USDJPY_trend_pullback_1h.json` |
| [ ] `USDJPY/trend_pullback/4h` | open | `results/cells/USDJPY_trend_pullback_4h.json` |
| [ ] `USDJPY/trend_pullback/1d` | open | `results/cells/USDJPY_trend_pullback_1d.json` |
| [ ] `USDJPY/trend_pullback/1w` | open | `results/cells/USDJPY_trend_pullback_1w.json` |
| [ ] `USDJPY/rsi2_pullback/15m` | open | `results/cells/USDJPY_rsi2_pullback_15m.json` |
| [ ] `USDJPY/rsi2_pullback/1h` | open | `results/cells/USDJPY_rsi2_pullback_1h.json` |
| [ ] `USDJPY/rsi2_pullback/4h` | open | `results/cells/USDJPY_rsi2_pullback_4h.json` |
| [ ] `USDJPY/rsi2_pullback/1d` | open | `results/cells/USDJPY_rsi2_pullback_1d.json` |
| [ ] `USDJPY/rsi2_pullback/1w` | open | `results/cells/USDJPY_rsi2_pullback_1w.json` |
| [ ] `USDJPY/vol_compression/15m` | open | `results/cells/USDJPY_vol_compression_15m.json` |
| [ ] `USDJPY/vol_compression/1h` | open | `results/cells/USDJPY_vol_compression_1h.json` |
| [ ] `USDJPY/vol_compression/4h` | open | `results/cells/USDJPY_vol_compression_4h.json` |
| [ ] `USDJPY/vol_compression/1d` | open | `results/cells/USDJPY_vol_compression_1d.json` |
| [ ] `USDJPY/vol_compression/1w` | open | `results/cells/USDJPY_vol_compression_1w.json` |
| [ ] `USDJPY/breakout/15m` | open | `results/cells/USDJPY_breakout_15m.json` |
| [ ] `USDJPY/breakout/1h` | open | `results/cells/USDJPY_breakout_1h.json` |
| [ ] `USDJPY/breakout/4h` | open | `results/cells/USDJPY_breakout_4h.json` |
| [ ] `USDJPY/breakout/1d` | open | `results/cells/USDJPY_breakout_1d.json` |
| [ ] `USDJPY/breakout/1w` | open | `results/cells/USDJPY_breakout_1w.json` |
| [ ] `USDJPY/donchian/15m` | open | `results/cells/USDJPY_donchian_15m.json` |
| [ ] `USDJPY/donchian/1h` | open | `results/cells/USDJPY_donchian_1h.json` |
| [ ] `USDJPY/donchian/4h` | open | `results/cells/USDJPY_donchian_4h.json` |
| [ ] `USDJPY/donchian/1d` | open | `results/cells/USDJPY_donchian_1d.json` |
| [ ] `USDJPY/donchian/1w` | open | `results/cells/USDJPY_donchian_1w.json` |
| [ ] `USDJPY/ma_cross/15m` | open | `results/cells/USDJPY_ma_cross_15m.json` |
| [ ] `USDJPY/ma_cross/1h` | open | `results/cells/USDJPY_ma_cross_1h.json` |
| [ ] `USDJPY/ma_cross/4h` | open | `results/cells/USDJPY_ma_cross_4h.json` |
| [ ] `USDJPY/ma_cross/1d` | open | `results/cells/USDJPY_ma_cross_1d.json` |
| [ ] `USDJPY/ma_cross/1w` | open | `results/cells/USDJPY_ma_cross_1w.json` |
| [ ] `USDJPY/bb_meanrev/15m` | open | `results/cells/USDJPY_bb_meanrev_15m.json` |
| [ ] `USDJPY/bb_meanrev/1h` | open | `results/cells/USDJPY_bb_meanrev_1h.json` |
| [ ] `USDJPY/bb_meanrev/4h` | open | `results/cells/USDJPY_bb_meanrev_4h.json` |
| [ ] `USDJPY/bb_meanrev/1d` | open | `results/cells/USDJPY_bb_meanrev_1d.json` |
| [ ] `USDJPY/bb_meanrev/1w` | open | `results/cells/USDJPY_bb_meanrev_1w.json` |
| [ ] `USDJPY/vwap_reversion/15m` | open | `results/cells/USDJPY_vwap_reversion_15m.json` |
| [ ] `USDJPY/vwap_reversion/1h` | open | `results/cells/USDJPY_vwap_reversion_1h.json` |
| [ ] `USDJPY/vwap_reversion/4h` | open | `results/cells/USDJPY_vwap_reversion_4h.json` |
| [ ] `USDJPY/vwap_reversion/1d` | open | `results/cells/USDJPY_vwap_reversion_1d.json` |
| [ ] `USDJPY/vwap_reversion/1w` | open | `results/cells/USDJPY_vwap_reversion_1w.json` |
| [ ] `USDJPY/momentum_12_1/15m` | open | `results/cells/USDJPY_momentum_12_1_15m.json` |
| [ ] `USDJPY/momentum_12_1/1h` | open | `results/cells/USDJPY_momentum_12_1_1h.json` |
| [ ] `USDJPY/momentum_12_1/4h` | open | `results/cells/USDJPY_momentum_12_1_4h.json` |
| [ ] `USDJPY/momentum_12_1/1d` | open | `results/cells/USDJPY_momentum_12_1_1d.json` |
| [ ] `USDJPY/momentum_12_1/1w` | open | `results/cells/USDJPY_momentum_12_1_1w.json` |
| [ ] `USDJPY/gap_fade/15m` | open | `results/cells/USDJPY_gap_fade_15m.json` |
| [ ] `USDJPY/gap_fade/1h` | open | `results/cells/USDJPY_gap_fade_1h.json` |
| [ ] `USDJPY/gap_fade/4h` | open | `results/cells/USDJPY_gap_fade_4h.json` |
| [ ] `USDJPY/gap_fade/1d` | open | `results/cells/USDJPY_gap_fade_1d.json` |
| [ ] `USDJPY/gap_fade/1w` | open | `results/cells/USDJPY_gap_fade_1w.json` |

## GBPUSD - 0/50 worked

| cell | status | artifact |
|---|---|---|
| [ ] `GBPUSD/trend_pullback/15m` | open | `results/cells/GBPUSD_trend_pullback_15m.json` |
| [ ] `GBPUSD/trend_pullback/1h` | open | `results/cells/GBPUSD_trend_pullback_1h.json` |
| [ ] `GBPUSD/trend_pullback/4h` | open | `results/cells/GBPUSD_trend_pullback_4h.json` |
| [ ] `GBPUSD/trend_pullback/1d` | open | `results/cells/GBPUSD_trend_pullback_1d.json` |
| [ ] `GBPUSD/trend_pullback/1w` | open | `results/cells/GBPUSD_trend_pullback_1w.json` |
| [ ] `GBPUSD/rsi2_pullback/15m` | open | `results/cells/GBPUSD_rsi2_pullback_15m.json` |
| [ ] `GBPUSD/rsi2_pullback/1h` | open | `results/cells/GBPUSD_rsi2_pullback_1h.json` |
| [ ] `GBPUSD/rsi2_pullback/4h` | open | `results/cells/GBPUSD_rsi2_pullback_4h.json` |
| [ ] `GBPUSD/rsi2_pullback/1d` | open | `results/cells/GBPUSD_rsi2_pullback_1d.json` |
| [ ] `GBPUSD/rsi2_pullback/1w` | open | `results/cells/GBPUSD_rsi2_pullback_1w.json` |
| [ ] `GBPUSD/vol_compression/15m` | open | `results/cells/GBPUSD_vol_compression_15m.json` |
| [ ] `GBPUSD/vol_compression/1h` | open | `results/cells/GBPUSD_vol_compression_1h.json` |
| [ ] `GBPUSD/vol_compression/4h` | open | `results/cells/GBPUSD_vol_compression_4h.json` |
| [ ] `GBPUSD/vol_compression/1d` | open | `results/cells/GBPUSD_vol_compression_1d.json` |
| [ ] `GBPUSD/vol_compression/1w` | open | `results/cells/GBPUSD_vol_compression_1w.json` |
| [ ] `GBPUSD/breakout/15m` | open | `results/cells/GBPUSD_breakout_15m.json` |
| [ ] `GBPUSD/breakout/1h` | open | `results/cells/GBPUSD_breakout_1h.json` |
| [ ] `GBPUSD/breakout/4h` | open | `results/cells/GBPUSD_breakout_4h.json` |
| [ ] `GBPUSD/breakout/1d` | open | `results/cells/GBPUSD_breakout_1d.json` |
| [ ] `GBPUSD/breakout/1w` | open | `results/cells/GBPUSD_breakout_1w.json` |
| [ ] `GBPUSD/donchian/15m` | open | `results/cells/GBPUSD_donchian_15m.json` |
| [ ] `GBPUSD/donchian/1h` | open | `results/cells/GBPUSD_donchian_1h.json` |
| [ ] `GBPUSD/donchian/4h` | open | `results/cells/GBPUSD_donchian_4h.json` |
| [ ] `GBPUSD/donchian/1d` | open | `results/cells/GBPUSD_donchian_1d.json` |
| [ ] `GBPUSD/donchian/1w` | open | `results/cells/GBPUSD_donchian_1w.json` |
| [ ] `GBPUSD/ma_cross/15m` | open | `results/cells/GBPUSD_ma_cross_15m.json` |
| [ ] `GBPUSD/ma_cross/1h` | open | `results/cells/GBPUSD_ma_cross_1h.json` |
| [ ] `GBPUSD/ma_cross/4h` | open | `results/cells/GBPUSD_ma_cross_4h.json` |
| [ ] `GBPUSD/ma_cross/1d` | open | `results/cells/GBPUSD_ma_cross_1d.json` |
| [ ] `GBPUSD/ma_cross/1w` | open | `results/cells/GBPUSD_ma_cross_1w.json` |
| [ ] `GBPUSD/bb_meanrev/15m` | open | `results/cells/GBPUSD_bb_meanrev_15m.json` |
| [ ] `GBPUSD/bb_meanrev/1h` | open | `results/cells/GBPUSD_bb_meanrev_1h.json` |
| [ ] `GBPUSD/bb_meanrev/4h` | open | `results/cells/GBPUSD_bb_meanrev_4h.json` |
| [ ] `GBPUSD/bb_meanrev/1d` | open | `results/cells/GBPUSD_bb_meanrev_1d.json` |
| [ ] `GBPUSD/bb_meanrev/1w` | open | `results/cells/GBPUSD_bb_meanrev_1w.json` |
| [ ] `GBPUSD/vwap_reversion/15m` | open | `results/cells/GBPUSD_vwap_reversion_15m.json` |
| [ ] `GBPUSD/vwap_reversion/1h` | open | `results/cells/GBPUSD_vwap_reversion_1h.json` |
| [ ] `GBPUSD/vwap_reversion/4h` | open | `results/cells/GBPUSD_vwap_reversion_4h.json` |
| [ ] `GBPUSD/vwap_reversion/1d` | open | `results/cells/GBPUSD_vwap_reversion_1d.json` |
| [ ] `GBPUSD/vwap_reversion/1w` | open | `results/cells/GBPUSD_vwap_reversion_1w.json` |
| [ ] `GBPUSD/momentum_12_1/15m` | open | `results/cells/GBPUSD_momentum_12_1_15m.json` |
| [ ] `GBPUSD/momentum_12_1/1h` | open | `results/cells/GBPUSD_momentum_12_1_1h.json` |
| [ ] `GBPUSD/momentum_12_1/4h` | open | `results/cells/GBPUSD_momentum_12_1_4h.json` |
| [ ] `GBPUSD/momentum_12_1/1d` | open | `results/cells/GBPUSD_momentum_12_1_1d.json` |
| [ ] `GBPUSD/momentum_12_1/1w` | open | `results/cells/GBPUSD_momentum_12_1_1w.json` |
| [ ] `GBPUSD/gap_fade/15m` | open | `results/cells/GBPUSD_gap_fade_15m.json` |
| [ ] `GBPUSD/gap_fade/1h` | open | `results/cells/GBPUSD_gap_fade_1h.json` |
| [ ] `GBPUSD/gap_fade/4h` | open | `results/cells/GBPUSD_gap_fade_4h.json` |
| [ ] `GBPUSD/gap_fade/1d` | open | `results/cells/GBPUSD_gap_fade_1d.json` |
| [ ] `GBPUSD/gap_fade/1w` | open | `results/cells/GBPUSD_gap_fade_1w.json` |

