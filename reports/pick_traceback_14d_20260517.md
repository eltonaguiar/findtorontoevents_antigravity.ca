# Pick Trace-Back & Edge-Attribution — last 14 days

> NOTE: raw pre-canonical analysis (pre-dedup/pre-slippage/pre-policy). Verdict-grade numbers live in `pf_registry.json::by_asset_class_policy_clean_net`.

Window: resolved picks in the last 14 days. Closed n=977 · WR 29.5% · PF 8.00. Active picks tracked: 110.

## 1. Discrimination test — does any score separate winners from losers?

For each score the pipeline attaches to a pick: its mean over WON picks vs over LOST picks. A real edge signal separates the two (standardised gap `eff` ≥ 0.30). `eff` ≈ 0 = the score is noise — it does not predict outcome.

| Score field | mean(WON) | mean(LOST) | gap | eff | verdict |
|---|---|---|---|---|---|
| `confidence` | 0.6384 | 0.6694 | -0.0311 | 0.528 | EDGE |
| `elite_score` | 24.7352 | 25.189 | -0.4538 | 0.058 | NOISE |
| `ml_score` | 0.6304 | 0.6588 | -0.0284 | 0.288 | weak |
| `ml_composite_score` | 24.7352 | 25.189 | -0.4538 | 0.058 | NOISE |
| `method_a_score` | 41.4093 | 27.1798 | +14.2295 | 1.138 | EDGE |
| `forward_wr` | 0.0 | 0.0 | +0.0 | 0.0 | NOISE |
| `risk_reward` | 1.4 | 1.5656 | -0.1657 | 1.053 | EDGE |

**3 of 7 scores show real separation (eff≥0.30).** Scores flagged EDGE are the ones worth keeping in the gate.

## 2. Blueprint by source-strategy type

| source_strategy_type | n | WR | PF |
|---|---|---|---|
| reverse_engineered_multi_asset | 749 | 26.6% | 10.68 |
| academic_cta_replication | 180 | 41.7% | 0.26 |
| ? | 48 | 29.2% | 0.54 |

## 3. Blueprint by elite grade

Does a better grade mean a better outcome? (if WR is flat across grades, the grade is not an edge)

| elite_grade | n | WR | PF |
|---|---|---|---|
| ? | 23 | 30.4% | 0.27 |
| A | 2 | 50.0% | 2.67 |
| B | 6 | 33.3% | 1.39 |
| C | 49 | 10.2% | 0.09 |
| D | 428 | 35.0% | 1.22 |
| F | 469 | 26.2% | 20.07 |

## 4. Blueprint by strategy (n≥10)

| strategy | n | WR | PF |
|---|---|---|---|
| ig_contrarian_sentiment | 132 | 16.7% | 165.16 |
| cot_positioning | 91 | 76.9% | 3.97 |
| cftc_cot_commercial_signal | 100 | 72.0% | 3.92 |
| fx_smart_carry_trade_momentum | 19 | 26.3% | 0.62 |
| cta_cross_asset_tsmom | 165 | 43.6% | 0.34 |
| combined_confidence | 14 | 14.3% | 0.21 |
| forex_rsi2_mean_reversion | 78 | 14.1% | 0.20 |
| myfxbook_retail_contrarian | 56 | 16.1% | 0.18 |
| forex_carry_momentum | 108 | 7.4% | 0.13 |
| futures_momentum | 171 | 2.3% | 0.04 |
| cta_commodity_momentum_term | 11 | 0.0% | 0.00 |

## 5. Why-picked trace — sample (5 WON, 5 LOST)

- **[WON]** `CT=F` SHORT · cot_positioning · conf=0.65 elite=27.0 grade=D · pnl=0.044406
  - reason: COT positioning SHORT: Weekly RSI=87 overbought. Cotton.
- **[WON]** `CT=F` SHORT · cftc_cot_commercial_signal · conf=0.637 elite=26.200000000000003 grade=D · pnl=0.044406
  - reason: CFTC COT proxy (API unavailable): Weekly RSI=87 extreme overbought (>75); Commercials likely distributing (proxy). Cotton.
- **[WON]** `USDJPY=X` SHORT · cta_cross_asset_tsmom · conf=0.622 elite=19.5 grade=F · pnl=0.003
  - reason: Cross-Asset TSMOM: own 1m=-1.6% (signal=-1), cross=Risk sentiment SPY 1m=+10.0%. Blended=-0.48 -> SHORT. Pitkajarvi & Suominen (2020): Sharpe 1.84.
- **[WON]** `CT=F` SHORT · cot_positioning · conf=0.65 elite=27.0 grade=D · pnl=0.044502
  - reason: COT positioning SHORT: Weekly RSI=87 overbought. Cotton.
- **[WON]** `CT=F` SHORT · cftc_cot_commercial_signal · conf=0.637 elite=26.200000000000003 grade=D · pnl=0.044502
  - reason: CFTC COT proxy (API unavailable): Weekly RSI=87 extreme overbought (>75); Commercials likely distributing (proxy). Cotton.
- **[LOST]** `EURJPY=X` LONG · forex_rsi2_mean_reversion · conf=0.742 elite=53.0 grade=C · pnl=-0.005
  - reason: RSI(2)=0.4 oversold, RSI(14)=20.7. Backtest: 57.6% WR, +32% PnL on 118 trades.
- **[LOST]** `AUDJPY=X` LONG · forex_carry_momentum · conf=0.702 elite=52.0 grade=C · pnl=-0.005
  - reason: Carry yield diff=3.8%, 20d momentum=2.50%, vol_ratio=1.04. Burnside et al. (2011): Sharpe 0.9-1.2.
- **[LOST]** `EURJPY=X` LONG · ig_contrarian_sentiment · conf=0.658 elite=51.0 grade=C · pnl=-0.005
  - reason: IG/DailyFX contrarian: RSI(14)=21<40 + price below 50 SMA; Retail likely SHORT => contrarian LONG (60-70% edge). EUR/JPY.
- **[LOST]** `EURGBP=X` LONG · ig_contrarian_sentiment · conf=0.615 elite=50.0 grade=C · pnl=-0.002323
  - reason: IG/DailyFX contrarian: RSI(14)=35<40 + price below 50 SMA; Retail likely SHORT => contrarian LONG (60-70% edge). EUR/GBP.
- **[LOST]** `EURJPY=X` LONG · myfxbook_retail_contrarian · conf=0.693 elite=32.0 grade=D · pnl=-0.006
  - reason: Myfxbook contrarian (proxy): RSI(14)=21<35 + price below 50 SMA; Retail likely SHORT => contrarian LONG (proxy). EUR/JPY.