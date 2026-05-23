# EQ-1 PEAD Mid-Cap -- S1 Backtest Results
Generated: 2026-04-19T02:26:21.254505+00:00

## Verdict: **FAIL**

Failed S1 criteria:
- IS Sharpe -0.02 <= 1.0
- Win rate 0.366 <= 0.55
- OOS2 Sharpe -0.28 < 0.7*IS -0.02

## Pre-emption kill-switch (DS-v3.1)
- mean CAR 48h (directional): 0.00129
- mean CAR 30d (raw, long-biased sign): 0.00470
- ratio (48h / 30d): 0.276
- threshold: > 0.70 = FAIL
- triggered: False

## Spec
- `sue_long`: 2.5
- `sue_short`: -2.5
- `hold_days`: 30
- `stop_car`: -0.05
- `txn_bps_roundtrip`: 30
- `window`: ['2020-01-01', '2025-12-31']
- `universe_size`: 63
- `universe`: ['GEN', 'JBL', 'MANH', 'WEX', 'ACIW', 'LSCC', 'SAIC', 'CIEN', 'TOL', 'RBC', 'SAIA', 'GGG', 'WWD', 'AAON', 'ATR', 'CW', 'BJ', 'TXRH', 'WING', 'MUSA', 'DECK', 'ANF', 'BLD', 'FIVE', 'CBSH', 'EWBC', 'PNFP', 'WBS', 'PFG', 'RGA', 'MTG', 'MEDP', 'UTHR', 'HALO', 'CRL', 'RVTY', 'NEOG', 'OVV', 'RRC', 'MUR', 'SM', 'PR', 'RGLD', 'CMC', 'AA', 'IDA', 'NFG', 'OGE', 'BRX', 'LAMR', 'EPR', 'SLG', 'CHDN', 'JAZZ', 'MASI', 'ENS', 'WSO', 'RHI', 'OLLI', 'THG', 'UNM', 'ORI', 'FHB']
- `entry_rule`: next_trading_day_open (conservative; FMP date precision unverified)
- `fmp_timestamp_note`: FMP stable/earnings `date` field precision is unverified on free tier; free tier does not expose pre/after-market `time` flag. Per DS-v3.1 we adopt the conservative next-open entry to eliminate same-day-close lookahead risk.

## Totals
- events_found_in_window: 216
- trades_simulated: 216
- skipped_no_price: 0
- skipped_short_history: 0

## Combined (all trades)
| metric | value |
|---|---|
| label | combined_all |
| n | 216 |
| longs | 175 |
| shorts | 41 |
| win_rate | 0.36574074074074076 |
| wilson_lb_95 | 0.3043756291441181 |
| avg_winner | 0.11537718326081332 |
| avg_loser | -0.06431787346993895 |
| wl_magnitude_ratio | 1.793858799058999 |
| mean_pnl | 0.001403929686215817 |
| median_pnl | -0.05469376428882439 |
| std_pnl | 0.10738518670065393 |
| sharpe | 0.037891397562731126 |
| max_dd | -1.0953464487536766 |
| sum_pnl | 0.30324881222261646 |
| stop_hit_rate | 0.5648148148148148 |
| mean_car_30d | 0.004696082316968773 |
| mean_car_48h_directional | 0.001294965547438315 |

## Long only (SUE>=2.5)
| metric | value |
|---|---|
| label | long_only |
| n | 175 |
| longs | 175 |
| shorts | 0 |
| win_rate | 0.36 |
| wilson_lb_95 | 0.29259319039369425 |
| avg_winner | 0.11812758027023468 |
| avg_loser | -0.062359252327507594 |
| wl_magnitude_ratio | 1.8943071935794658 |
| mean_pnl | 0.0026160074076796314 |
| median_pnl | -0.05454615553942743 |
| std_pnl | 0.10814606338165374 |
| sharpe | 0.0701080515186631 |
| max_dd | -1.0838574923942685 |
| sum_pnl | 0.4578012963439355 |
| stop_hit_rate | 0.56 |
| mean_car_30d | 0.005616007407679634 |
| mean_car_48h_directional | 0.0021889264983667657 |

## Short only (SUE<=-2.5)
| metric | value |
|---|---|
| label | short_only |
| n | 41 |
| longs | 0 |
| shorts | 41 |
| win_rate | 0.3902439024390244 |
| wilson_lb_95 | 0.2565593521532712 |
| avg_winner | 0.10454749503621663 |
| avg_loser | -0.0730924961880314 |
| wl_magnitude_ratio | 1.4303451173327948 |
| mean_pnl | -0.0037695727834468062 |
| median_pnl | -0.05709273465650633 |
| std_pnl | 0.10522660222543022 |
| sharpe | -0.10382602540008282 |
| max_dd | -0.6946551477115624 |
| sum_pnl | -0.15455248412131906 |
| stop_hit_rate | 0.5853658536585366 |
| mean_car_30d | 0.0007695727834468036 |
| mean_car_48h_directional | -0.0025207214382319014 |

## IS (first 70%)
| metric | value |
|---|---|
| label | IS_70pct |
| n | 151 |
| longs | 127 |
| shorts | 24 |
| win_rate | 0.3576158940397351 |
| wilson_lb_95 | 0.28557084895621565 |
| avg_winner | 0.11734450580420076 |
| avg_loser | -0.0666610893383832 |
| wl_magnitude_ratio | 1.7603148548704295 |
| mean_pnl | -0.000857763923154483 |
| median_pnl | -0.05472008198038225 |
| std_pnl | 0.10795728737259018 |
| sharpe | -0.023027959431439107 |
| max_dd | -2.308688062931798 |
| sum_pnl | -0.12952235239632692 |
| stop_hit_rate | 0.5695364238410596 |
| mean_car_30d | 0.002102333663241679 |
| mean_car_48h_directional | 0.00022581604376526045 |

## OOS1 (next 15%)
| metric | value |
|---|---|
| label | OOS_15pct_a |
| n | 32 |
| longs | 27 |
| shorts | 5 |
| win_rate | 0.46875 |
| wilson_lb_95 | 0.30869129901682335 |
| avg_winner | 0.10815002062593798 |
| avg_loser | -0.052472744958524026 |
| wl_magnitude_ratio | 2.06107038447146 |
| mean_pnl | 0.022819176409192527 |
| median_pnl | -0.0023364813015405135 |
| std_pnl | 0.11909466465069811 |
| sharpe | 0.555325099328753 |
| max_dd | -0.269804810688855 |
| sum_pnl | 0.7302136450941609 |
| stop_hit_rate | 0.4375 |
| mean_car_30d | 0.007354551101122295 |
| mean_car_48h_directional | 0.009226314185669483 |

## OOS2 (last 15%)
| metric | value |
|---|---|
| label | OOS_15pct_b |
| n | 33 |
| longs | 21 |
| shorts | 12 |
| win_rate | 0.30303030303030304 |
| wilson_lb_95 | 0.17375347814547223 |
| avg_winner | 0.11559438547883391 |
| avg_loser | -0.0631907102288503 |
| wl_magnitude_ratio | 1.8292939747029182 |
| mean_pnl | -0.009013408499249007 |
| median_pnl | -0.05810206388084971 |
| std_pnl | 0.0922554261798201 |
| sharpe | -0.2831631780125998 |
| max_dd | -0.6764861859936198 |
| sum_pnl | -0.29744248047521726 |
| stop_hit_rate | 0.6666666666666666 |
| mean_car_30d | 0.013986538244843881 |
| mean_car_48h_directional | -0.001503870251615203 |

## Yearly
| year | n | sharpe | win_rate | mean_pnl | mean_car_30d |
|---|---|---|---|---|---|
| 2020 | 55 | -1.002 | 0.164 | -0.03292 | -0.02105 |
| 2021 | 44 | 0.295 | 0.455 | 0.00969 | -0.00223 |
| 2022 | 36 | 0.737 | 0.472 | 0.03433 | 0.05211 |
| 2023 | 25 | 0.685 | 0.560 | 0.03236 | 0.01970 |
| 2024 | 29 | -0.632 | 0.310 | -0.01414 | -0.02334 |
| 2025 | 27 | 0.057 | 0.370 | 0.00195 | 0.02143 |

## Notes
- Universe is a static ~60-ticker proxy for S&P 400 mid-caps. Survivorship bias is possible; S1 is a go/no-go gate, not a production sim.
- FMP free-tier timestamp precision unverified; conservative next-open entry used.
- No parameter iteration on fail, per protocol. Result stands.