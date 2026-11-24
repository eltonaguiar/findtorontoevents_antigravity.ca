# 200-round development programme — 2026-11-22

**Goal.** Find one or more asset classes with an edge that is at least backtest-proven under the
G0–G8 contract, then keep it honest with forward pods, CI monitoring and paper portfolios.

**Shape.** 200 rounds in 7 phases. One round = one PR that adds or stress-tests **one**
pre-registered cell, or one operationally-verified live step. A round is only closed when its
artifact exists and the gate result is recorded — a failed cell is a closed round, not a lost one.

| phase | rounds | what it settles |
|---|---|---|
| P0 data integrity | 10 | whether the series can be measured at all |
| P1 mechanism hunt | 40 | which mechanisms produce a signal above costs |
| P2 robustness | 35 | whether a passing cell survives stress |
| P3 live sprint | 45 | whether the machinery can open and close on live data |
| P4 forward pods | 30 | whether the edge persists out of sample |
| P5 portfolio | 25 | whether combining cells beats the best single cell |
| P6 governance | 15 | whether the edge is still there next month |

## Rounds

| # | phase | class | round | gate | artifact |
|---|---|---|---|---|---|
| 1 | P0 data integrity | EQUITY | audit and repair the EQUITY price series (roll gaps, negatives, splits, survivorship) | series usable: no negative prints, no recurring month-day spikes, documented source | `reports/rounds/001_equity_integrity.md` |
| 2 | P0 data integrity | ETF | audit and repair the ETF price series (roll gaps, negatives, splits, survivorship) | series usable: no negative prints, no recurring month-day spikes, documented source | `reports/rounds/002_etf_integrity.md` |
| 3 | P0 data integrity | CRYPTO | audit and repair the CRYPTO price series (roll gaps, negatives, splits, survivorship) | series usable: no negative prints, no recurring month-day spikes, documented source | `reports/rounds/003_crypto_integrity.md` |
| 4 | P0 data integrity | COMMODITY | audit and repair the COMMODITY price series (roll gaps, negatives, splits, survivorship) | series usable: no negative prints, no recurring month-day spikes, documented source | `reports/rounds/004_commodity_integrity.md` |
| 5 | P0 data integrity | FOREX | audit and repair the FOREX price series (roll gaps, negatives, splits, survivorship) | series usable: no negative prints, no recurring month-day spikes, documented source | `reports/rounds/005_forex_integrity.md` |
| 6 | P0 data integrity | BOND | audit and repair the BOND price series (roll gaps, negatives, splits, survivorship) | series usable: no negative prints, no recurring month-day spikes, documented source | `reports/rounds/006_bond_integrity.md` |
| 7 | P0 data integrity | FUTURES | audit and repair the FUTURES price series (roll gaps, negatives, splits, survivorship) | series usable: no negative prints, no recurring month-day spikes, documented source | `reports/rounds/007_futures_integrity.md` |
| 8 | P0 data integrity | INDEX | audit and repair the INDEX price series (roll gaps, negatives, splits, survivorship) | series usable: no negative prints, no recurring month-day spikes, documented source | `reports/rounds/008_index_integrity.md` |
| 9 | P0 data integrity | MUTUAL_FUND | audit and repair the MUTUAL_FUND price series (roll gaps, negatives, splits, survivorship) | series usable: no negative prints, no recurring month-day spikes, documented source | `reports/rounds/009_mutual_fund_integrity.md` |
| 10 | P0 data integrity | PENNY_STOCK | audit and repair the PENNY_STOCK price series (roll gaps, negatives, splits, survivorship) | series usable: no negative prints, no recurring month-day spikes, documented source | `reports/rounds/010_penny_stock_integrity.md` |
| 11 | P1 mechanism hunt | EQUITY | 12-1 time-series momentum | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/011_equity_12-1.md` |
| 12 | P1 mechanism hunt | EQUITY | xsmom top-3 6m | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/012_equity_xsmom.md` |
| 13 | P1 mechanism hunt | EQUITY | dollar-neutral top3/bottom3 momentum | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/013_equity_dollar-neutral.md` |
| 14 | P1 mechanism hunt | EQUITY | PEAD on 12-quarter SUE | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/014_equity_pead.md` |
| 15 | P1 mechanism hunt | ETF | sector rotation 12m | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/015_etf_sector.md` |
| 16 | P1 mechanism hunt | ETF | dual momentum (GEM) | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/016_etf_dual.md` |
| 17 | P1 mechanism hunt | ETF | risk-parity weights | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/017_etf_risk-parity.md` |
| 18 | P1 mechanism hunt | ETF | vol-targeted SPY | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/018_etf_vol-targeted.md` |
| 19 | P1 mechanism hunt | CRYPTO | 6m time-series momentum | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/019_crypto_6m.md` |
| 20 | P1 mechanism hunt | CRYPTO | xsmom top-3 3m | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/020_crypto_xsmom.md` |
| 21 | P1 mechanism hunt | CRYPTO | funding carry (delta-neutral) | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/021_crypto_funding.md` |
| 22 | P1 mechanism hunt | CRYPTO | cash-and-carry basis | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/022_crypto_cash-and-carry.md` |
| 23 | P1 mechanism hunt | COMMODITY | TSMOM on ETF basket | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/023_commodity_tsmom.md` |
| 24 | P1 mechanism hunt | COMMODITY | xsmom on ETF basket | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/024_commodity_xsmom.md` |
| 25 | P1 mechanism hunt | COMMODITY | roll yield (needs curves) | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/025_commodity_roll.md` |
| 26 | P1 mechanism hunt | COMMODITY | nat-gas winter seasonality | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/026_commodity_nat-gas.md` |
| 27 | P1 mechanism hunt | FOREX | carry (rate differential) | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/027_forex_carry.md` |
| 28 | P1 mechanism hunt | FOREX | TSMOM long/short | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/028_forex_tsmom.md` |
| 29 | P1 mechanism hunt | FOREX | cross-sectional momentum | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/029_forex_cross-sectional.md` |
| 30 | P1 mechanism hunt | FOREX | PPP value | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/030_forex_ppp.md` |
| 31 | P1 mechanism hunt | BOND | TLT 12-1 trend | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/031_bond_tlt.md` |
| 32 | P1 mechanism hunt | BOND | xsmom duration | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/032_bond_xsmom.md` |
| 33 | P1 mechanism hunt | BOND | credit spread (HYG vs IEF) | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/033_bond_credit.md` |
| 34 | P1 mechanism hunt | BOND | yield-curve slope | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/034_bond_yield-curve.md` |
| 35 | P1 mechanism hunt | FUTURES | index TSMOM | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/035_futures_index.md` |
| 36 | P1 mechanism hunt | FUTURES | contract-curve xsmom | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/036_futures_contract-curve.md` |
| 37 | P1 mechanism hunt | FUTURES | roll yield | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/037_futures_roll.md` |
| 38 | P1 mechanism hunt | FUTURES | term-structure carry | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/038_futures_term-structure.md` |
| 39 | P1 mechanism hunt | INDEX | GSPC 12-1 TSMOM | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/039_index_gspc.md` |
| 40 | P1 mechanism hunt | INDEX | xsmom across indices | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/040_index_xsmom.md` |
| 41 | P1 mechanism hunt | INDEX | vol-targeted index | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/041_index_vol-targeted.md` |
| 42 | P1 mechanism hunt | INDEX | drawdown-recovery rule | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/042_index_drawdown-recovery.md` |
| 43 | P1 mechanism hunt | MUTUAL_FUND | fund momentum | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/043_mutual_fund_fund.md` |
| 44 | P1 mechanism hunt | MUTUAL_FUND | expense-ratio screen | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/044_mutual_fund_expense-ratio.md` |
| 45 | P1 mechanism hunt | MUTUAL_FUND | manager persistence | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/045_mutual_fund_manager.md` |
| 46 | P1 mechanism hunt | MUTUAL_FUND | category rotation | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/046_mutual_fund_category.md` |
| 47 | P1 mechanism hunt | PENNY_STOCK | TSMOM | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/047_penny_stock_tsmom.md` |
| 48 | P1 mechanism hunt | PENNY_STOCK | reversal | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/048_penny_stock_reversal.md` |
| 49 | P1 mechanism hunt | PENNY_STOCK | liquidity screen | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/049_penny_stock_liquidity.md` |
| 50 | P1 mechanism hunt | PENNY_STOCK | volatility breakout | G0-G8: CI-LB>0, 2x cost, both halves, excess vs bench, DSR>=0.95, n>=30 | `reports/rounds/050_penny_stock_volatility.md` |
| 51 | P2 robustness | EQUITY | cost grid 1x/2x/3x on the best EQUITY cell | the cell must survive the stress or be withdrawn | `reports/rounds/051_equity_robust.md` |
| 52 | P2 robustness | ETF | decade subsamples on the best ETF cell | the cell must survive the stress or be withdrawn | `reports/rounds/052_etf_robust.md` |
| 53 | P2 robustness | CRYPTO | regime split (VIX terciles) on the best CRYPTO cell | the cell must survive the stress or be withdrawn | `reports/rounds/053_crypto_robust.md` |
| 54 | P2 robustness | COMMODITY | parameter sensitivity (+/-25%) on the best COMMODITY cell | the cell must survive the stress or be withdrawn | `reports/rounds/054_commodity_robust.md` |
| 55 | P2 robustness | FOREX | walk-forward 5-fold on the best FOREX cell | the cell must survive the stress or be withdrawn | `reports/rounds/055_forex_robust.md` |
| 56 | P2 robustness | BOND | DSR/PBO with true trial count on the best BOND cell | the cell must survive the stress or be withdrawn | `reports/rounds/056_bond_robust.md` |
| 57 | P2 robustness | FUTURES | survivorship re-test on delisted names on the best FUTURES cell | the cell must survive the stress or be withdrawn | `reports/rounds/057_futures_robust.md` |
| 58 | P2 robustness | INDEX | cost grid 1x/2x/3x on the best INDEX cell | the cell must survive the stress or be withdrawn | `reports/rounds/058_index_robust.md` |
| 59 | P2 robustness | MUTUAL_FUND | decade subsamples on the best MUTUAL_FUND cell | the cell must survive the stress or be withdrawn | `reports/rounds/059_mutual_fund_robust.md` |
| 60 | P2 robustness | PENNY_STOCK | regime split (VIX terciles) on the best PENNY_STOCK cell | the cell must survive the stress or be withdrawn | `reports/rounds/060_penny_stock_robust.md` |
| 61 | P2 robustness | EQUITY | parameter sensitivity (+/-25%) on the best EQUITY cell | the cell must survive the stress or be withdrawn | `reports/rounds/061_equity_robust.md` |
| 62 | P2 robustness | ETF | walk-forward 5-fold on the best ETF cell | the cell must survive the stress or be withdrawn | `reports/rounds/062_etf_robust.md` |
| 63 | P2 robustness | CRYPTO | DSR/PBO with true trial count on the best CRYPTO cell | the cell must survive the stress or be withdrawn | `reports/rounds/063_crypto_robust.md` |
| 64 | P2 robustness | COMMODITY | survivorship re-test on delisted names on the best COMMODITY cell | the cell must survive the stress or be withdrawn | `reports/rounds/064_commodity_robust.md` |
| 65 | P2 robustness | FOREX | cost grid 1x/2x/3x on the best FOREX cell | the cell must survive the stress or be withdrawn | `reports/rounds/065_forex_robust.md` |
| 66 | P2 robustness | BOND | decade subsamples on the best BOND cell | the cell must survive the stress or be withdrawn | `reports/rounds/066_bond_robust.md` |
| 67 | P2 robustness | FUTURES | regime split (VIX terciles) on the best FUTURES cell | the cell must survive the stress or be withdrawn | `reports/rounds/067_futures_robust.md` |
| 68 | P2 robustness | INDEX | parameter sensitivity (+/-25%) on the best INDEX cell | the cell must survive the stress or be withdrawn | `reports/rounds/068_index_robust.md` |
| 69 | P2 robustness | MUTUAL_FUND | walk-forward 5-fold on the best MUTUAL_FUND cell | the cell must survive the stress or be withdrawn | `reports/rounds/069_mutual_fund_robust.md` |
| 70 | P2 robustness | PENNY_STOCK | DSR/PBO with true trial count on the best PENNY_STOCK cell | the cell must survive the stress or be withdrawn | `reports/rounds/070_penny_stock_robust.md` |
| 71 | P2 robustness | EQUITY | survivorship re-test on delisted names on the best EQUITY cell | the cell must survive the stress or be withdrawn | `reports/rounds/071_equity_robust.md` |
| 72 | P2 robustness | ETF | cost grid 1x/2x/3x on the best ETF cell | the cell must survive the stress or be withdrawn | `reports/rounds/072_etf_robust.md` |
| 73 | P2 robustness | CRYPTO | decade subsamples on the best CRYPTO cell | the cell must survive the stress or be withdrawn | `reports/rounds/073_crypto_robust.md` |
| 74 | P2 robustness | COMMODITY | regime split (VIX terciles) on the best COMMODITY cell | the cell must survive the stress or be withdrawn | `reports/rounds/074_commodity_robust.md` |
| 75 | P2 robustness | FOREX | parameter sensitivity (+/-25%) on the best FOREX cell | the cell must survive the stress or be withdrawn | `reports/rounds/075_forex_robust.md` |
| 76 | P2 robustness | BOND | walk-forward 5-fold on the best BOND cell | the cell must survive the stress or be withdrawn | `reports/rounds/076_bond_robust.md` |
| 77 | P2 robustness | FUTURES | DSR/PBO with true trial count on the best FUTURES cell | the cell must survive the stress or be withdrawn | `reports/rounds/077_futures_robust.md` |
| 78 | P2 robustness | INDEX | survivorship re-test on delisted names on the best INDEX cell | the cell must survive the stress or be withdrawn | `reports/rounds/078_index_robust.md` |
| 79 | P2 robustness | MUTUAL_FUND | cost grid 1x/2x/3x on the best MUTUAL_FUND cell | the cell must survive the stress or be withdrawn | `reports/rounds/079_mutual_fund_robust.md` |
| 80 | P2 robustness | PENNY_STOCK | decade subsamples on the best PENNY_STOCK cell | the cell must survive the stress or be withdrawn | `reports/rounds/080_penny_stock_robust.md` |
| 81 | P2 robustness | EQUITY | regime split (VIX terciles) on the best EQUITY cell | the cell must survive the stress or be withdrawn | `reports/rounds/081_equity_robust.md` |
| 82 | P2 robustness | ETF | parameter sensitivity (+/-25%) on the best ETF cell | the cell must survive the stress or be withdrawn | `reports/rounds/082_etf_robust.md` |
| 83 | P2 robustness | CRYPTO | walk-forward 5-fold on the best CRYPTO cell | the cell must survive the stress or be withdrawn | `reports/rounds/083_crypto_robust.md` |
| 84 | P2 robustness | COMMODITY | DSR/PBO with true trial count on the best COMMODITY cell | the cell must survive the stress or be withdrawn | `reports/rounds/084_commodity_robust.md` |
| 85 | P2 robustness | FOREX | survivorship re-test on delisted names on the best FOREX cell | the cell must survive the stress or be withdrawn | `reports/rounds/085_forex_robust.md` |
| 86 | P3 live sprint | CRYPTO | live paper sprint: EMA20/60 trend on 1m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_01.json` |
| 87 | P3 live sprint | CRYPTO | live paper sprint: RSI(14) 30/70 reversal on 3m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_02.json` |
| 88 | P3 live sprint | CRYPTO | live paper sprint: Donchian 20 breakout on 5m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_03.json` |
| 89 | P3 live sprint | CRYPTO | live paper sprint: VWAP fade on 15m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_04.json` |
| 90 | P3 live sprint | CRYPTO | live paper sprint: funding-spike fade on 1h bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_05.json` |
| 91 | P3 live sprint | CRYPTO | live paper sprint: 3-bar momentum on 1m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_06.json` |
| 92 | P3 live sprint | CRYPTO | live paper sprint: volatility contraction then expansion on 3m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_07.json` |
| 93 | P3 live sprint | CRYPTO | live paper sprint: range-break retest on 5m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_08.json` |
| 94 | P3 live sprint | CRYPTO | live paper sprint: opening-range breakout on 15m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_09.json` |
| 95 | P3 live sprint | CRYPTO | live paper sprint: EMA20/60 trend on 1h bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_10.json` |
| 96 | P3 live sprint | CRYPTO | live paper sprint: RSI(14) 30/70 reversal on 1m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_11.json` |
| 97 | P3 live sprint | CRYPTO | live paper sprint: Donchian 20 breakout on 3m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_12.json` |
| 98 | P3 live sprint | CRYPTO | live paper sprint: VWAP fade on 5m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_13.json` |
| 99 | P3 live sprint | CRYPTO | live paper sprint: funding-spike fade on 15m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_14.json` |
| 100 | P3 live sprint | CRYPTO | live paper sprint: 3-bar momentum on 1h bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_15.json` |
| 101 | P3 live sprint | CRYPTO | live paper sprint: volatility contraction then expansion on 1m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_16.json` |
| 102 | P3 live sprint | CRYPTO | live paper sprint: range-break retest on 3m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_17.json` |
| 103 | P3 live sprint | CRYPTO | live paper sprint: opening-range breakout on 5m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_18.json` |
| 104 | P3 live sprint | CRYPTO | live paper sprint: EMA20/60 trend on 15m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_19.json` |
| 105 | P3 live sprint | CRYPTO | live paper sprint: RSI(14) 30/70 reversal on 1h bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_20.json` |
| 106 | P3 live sprint | CRYPTO | live paper sprint: Donchian 20 breakout on 1m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_21.json` |
| 107 | P3 live sprint | CRYPTO | live paper sprint: VWAP fade on 3m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_22.json` |
| 108 | P3 live sprint | CRYPTO | live paper sprint: funding-spike fade on 5m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_23.json` |
| 109 | P3 live sprint | CRYPTO | live paper sprint: 3-bar momentum on 15m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_24.json` |
| 110 | P3 live sprint | CRYPTO | live paper sprint: volatility contraction then expansion on 1h bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_25.json` |
| 111 | P3 live sprint | CRYPTO | live paper sprint: range-break retest on 1m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_26.json` |
| 112 | P3 live sprint | CRYPTO | live paper sprint: opening-range breakout on 3m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_27.json` |
| 113 | P3 live sprint | CRYPTO | live paper sprint: EMA20/60 trend on 5m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_28.json` |
| 114 | P3 live sprint | CRYPTO | live paper sprint: RSI(14) 30/70 reversal on 15m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_29.json` |
| 115 | P3 live sprint | CRYPTO | live paper sprint: Donchian 20 breakout on 1h bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_30.json` |
| 116 | P3 live sprint | CRYPTO | live paper sprint: VWAP fade on 1m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_31.json` |
| 117 | P3 live sprint | CRYPTO | live paper sprint: funding-spike fade on 3m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_32.json` |
| 118 | P3 live sprint | CRYPTO | live paper sprint: 3-bar momentum on 5m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_33.json` |
| 119 | P3 live sprint | CRYPTO | live paper sprint: volatility contraction then expansion on 15m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_34.json` |
| 120 | P3 live sprint | CRYPTO | live paper sprint: range-break retest on 1h bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_35.json` |
| 121 | P3 live sprint | CRYPTO | live paper sprint: opening-range breakout on 1m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_36.json` |
| 122 | P3 live sprint | CRYPTO | live paper sprint: EMA20/60 trend on 3m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_37.json` |
| 123 | P3 live sprint | CRYPTO | live paper sprint: RSI(14) 30/70 reversal on 5m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_38.json` |
| 124 | P3 live sprint | CRYPTO | live paper sprint: Donchian 20 breakout on 15m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_39.json` |
| 125 | P3 live sprint | CRYPTO | live paper sprint: VWAP fade on 1h bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_40.json` |
| 126 | P3 live sprint | CRYPTO | live paper sprint: funding-spike fade on 1m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_41.json` |
| 127 | P3 live sprint | CRYPTO | live paper sprint: 3-bar momentum on 3m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_42.json` |
| 128 | P3 live sprint | CRYPTO | live paper sprint: volatility contraction then expansion on 5m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_43.json` |
| 129 | P3 live sprint | CRYPTO | live paper sprint: range-break retest on 15m bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_44.json` |
| 130 | P3 live sprint | CRYPTO | live paper sprint: opening-range breakout on 1h bars | must open AND close inside the window, net of 24bps round trip; report win/loss either way | `data/realtime_challenge/sprint_45.json` |
| 131 | P4 forward pods | EQUITY | register/refresh the EQUITY forward pod and its CI monitor | pod emits picks daily, resolver closes them, by_pod stats published | `audit_dashboard/data/forward_book_pod_equity.json` |
| 132 | P4 forward pods | ETF | register/refresh the ETF forward pod and its CI monitor | pod emits picks daily, resolver closes them, by_pod stats published | `audit_dashboard/data/forward_book_pod_etf.json` |
| 133 | P4 forward pods | CRYPTO | register/refresh the CRYPTO forward pod and its CI monitor | pod emits picks daily, resolver closes them, by_pod stats published | `audit_dashboard/data/forward_book_pod_crypto.json` |
| 134 | P4 forward pods | COMMODITY | register/refresh the COMMODITY forward pod and its CI monitor | pod emits picks daily, resolver closes them, by_pod stats published | `audit_dashboard/data/forward_book_pod_commodity.json` |
| 135 | P4 forward pods | FOREX | register/refresh the FOREX forward pod and its CI monitor | pod emits picks daily, resolver closes them, by_pod stats published | `audit_dashboard/data/forward_book_pod_forex.json` |
| 136 | P4 forward pods | BOND | register/refresh the BOND forward pod and its CI monitor | pod emits picks daily, resolver closes them, by_pod stats published | `audit_dashboard/data/forward_book_pod_bond.json` |
| 137 | P4 forward pods | FUTURES | register/refresh the FUTURES forward pod and its CI monitor | pod emits picks daily, resolver closes them, by_pod stats published | `audit_dashboard/data/forward_book_pod_futures.json` |
| 138 | P4 forward pods | INDEX | register/refresh the INDEX forward pod and its CI monitor | pod emits picks daily, resolver closes them, by_pod stats published | `audit_dashboard/data/forward_book_pod_index.json` |
| 139 | P4 forward pods | MUTUAL_FUND | register/refresh the MUTUAL_FUND forward pod and its CI monitor | pod emits picks daily, resolver closes them, by_pod stats published | `audit_dashboard/data/forward_book_pod_mutual_fund.json` |
| 140 | P4 forward pods | PENNY_STOCK | register/refresh the PENNY_STOCK forward pod and its CI monitor | pod emits picks daily, resolver closes them, by_pod stats published | `audit_dashboard/data/forward_book_pod_penny_stock.json` |
| 141 | P4 forward pods | EQUITY | register/refresh the EQUITY forward pod and its CI monitor | pod emits picks daily, resolver closes them, by_pod stats published | `audit_dashboard/data/forward_book_pod_equity.json` |
| 142 | P4 forward pods | ETF | register/refresh the ETF forward pod and its CI monitor | pod emits picks daily, resolver closes them, by_pod stats published | `audit_dashboard/data/forward_book_pod_etf.json` |
| 143 | P4 forward pods | CRYPTO | register/refresh the CRYPTO forward pod and its CI monitor | pod emits picks daily, resolver closes them, by_pod stats published | `audit_dashboard/data/forward_book_pod_crypto.json` |
| 144 | P4 forward pods | COMMODITY | register/refresh the COMMODITY forward pod and its CI monitor | pod emits picks daily, resolver closes them, by_pod stats published | `audit_dashboard/data/forward_book_pod_commodity.json` |
| 145 | P4 forward pods | FOREX | register/refresh the FOREX forward pod and its CI monitor | pod emits picks daily, resolver closes them, by_pod stats published | `audit_dashboard/data/forward_book_pod_forex.json` |
| 146 | P4 forward pods | BOND | register/refresh the BOND forward pod and its CI monitor | pod emits picks daily, resolver closes them, by_pod stats published | `audit_dashboard/data/forward_book_pod_bond.json` |
| 147 | P4 forward pods | FUTURES | register/refresh the FUTURES forward pod and its CI monitor | pod emits picks daily, resolver closes them, by_pod stats published | `audit_dashboard/data/forward_book_pod_futures.json` |
| 148 | P4 forward pods | INDEX | register/refresh the INDEX forward pod and its CI monitor | pod emits picks daily, resolver closes them, by_pod stats published | `audit_dashboard/data/forward_book_pod_index.json` |
| 149 | P4 forward pods | MUTUAL_FUND | register/refresh the MUTUAL_FUND forward pod and its CI monitor | pod emits picks daily, resolver closes them, by_pod stats published | `audit_dashboard/data/forward_book_pod_mutual_fund.json` |
| 150 | P4 forward pods | PENNY_STOCK | register/refresh the PENNY_STOCK forward pod and its CI monitor | pod emits picks daily, resolver closes them, by_pod stats published | `audit_dashboard/data/forward_book_pod_penny_stock.json` |
| 151 | P4 forward pods | EQUITY | register/refresh the EQUITY forward pod and its CI monitor | pod emits picks daily, resolver closes them, by_pod stats published | `audit_dashboard/data/forward_book_pod_equity.json` |
| 152 | P4 forward pods | ETF | register/refresh the ETF forward pod and its CI monitor | pod emits picks daily, resolver closes them, by_pod stats published | `audit_dashboard/data/forward_book_pod_etf.json` |
| 153 | P4 forward pods | CRYPTO | register/refresh the CRYPTO forward pod and its CI monitor | pod emits picks daily, resolver closes them, by_pod stats published | `audit_dashboard/data/forward_book_pod_crypto.json` |
| 154 | P4 forward pods | COMMODITY | register/refresh the COMMODITY forward pod and its CI monitor | pod emits picks daily, resolver closes them, by_pod stats published | `audit_dashboard/data/forward_book_pod_commodity.json` |
| 155 | P4 forward pods | FOREX | register/refresh the FOREX forward pod and its CI monitor | pod emits picks daily, resolver closes them, by_pod stats published | `audit_dashboard/data/forward_book_pod_forex.json` |
| 156 | P4 forward pods | BOND | register/refresh the BOND forward pod and its CI monitor | pod emits picks daily, resolver closes them, by_pod stats published | `audit_dashboard/data/forward_book_pod_bond.json` |
| 157 | P4 forward pods | FUTURES | register/refresh the FUTURES forward pod and its CI monitor | pod emits picks daily, resolver closes them, by_pod stats published | `audit_dashboard/data/forward_book_pod_futures.json` |
| 158 | P4 forward pods | INDEX | register/refresh the INDEX forward pod and its CI monitor | pod emits picks daily, resolver closes them, by_pod stats published | `audit_dashboard/data/forward_book_pod_index.json` |
| 159 | P4 forward pods | MUTUAL_FUND | register/refresh the MUTUAL_FUND forward pod and its CI monitor | pod emits picks daily, resolver closes them, by_pod stats published | `audit_dashboard/data/forward_book_pod_mutual_fund.json` |
| 160 | P4 forward pods | PENNY_STOCK | register/refresh the PENNY_STOCK forward pod and its CI monitor | pod emits picks daily, resolver closes them, by_pod stats published | `audit_dashboard/data/forward_book_pod_penny_stock.json` |
| 161 | P5 portfolio | MULTI | equal-weight combo of passing cells (variant 1) | portfolio Sharpe > best single cell AND maxDD within mandate | `reports/rounds/161_portfolio.md` |
| 162 | P5 portfolio | MULTI | inverse-vol weights (variant 1) | portfolio Sharpe > best single cell AND maxDD within mandate | `reports/rounds/162_portfolio.md` |
| 163 | P5 portfolio | MULTI | correlation cap 0.7 (variant 1) | portfolio Sharpe > best single cell AND maxDD within mandate | `reports/rounds/163_portfolio.md` |
| 164 | P5 portfolio | MULTI | drawdown-throttled sizing (variant 1) | portfolio Sharpe > best single cell AND maxDD within mandate | `reports/rounds/164_portfolio.md` |
| 165 | P5 portfolio | MULTI | kill-switch on 3 sigma day (variant 1) | portfolio Sharpe > best single cell AND maxDD within mandate | `reports/rounds/165_portfolio.md` |
| 166 | P5 portfolio | MULTI | rebalance cadence sweep (variant 1) | portfolio Sharpe > best single cell AND maxDD within mandate | `reports/rounds/166_portfolio.md` |
| 167 | P5 portfolio | MULTI | cash-yield on idle margin (variant 1) | portfolio Sharpe > best single cell AND maxDD within mandate | `reports/rounds/167_portfolio.md` |
| 168 | P5 portfolio | MULTI | equal-weight combo of passing cells (variant 2) | portfolio Sharpe > best single cell AND maxDD within mandate | `reports/rounds/168_portfolio.md` |
| 169 | P5 portfolio | MULTI | inverse-vol weights (variant 2) | portfolio Sharpe > best single cell AND maxDD within mandate | `reports/rounds/169_portfolio.md` |
| 170 | P5 portfolio | MULTI | correlation cap 0.7 (variant 2) | portfolio Sharpe > best single cell AND maxDD within mandate | `reports/rounds/170_portfolio.md` |
| 171 | P5 portfolio | MULTI | drawdown-throttled sizing (variant 2) | portfolio Sharpe > best single cell AND maxDD within mandate | `reports/rounds/171_portfolio.md` |
| 172 | P5 portfolio | MULTI | kill-switch on 3 sigma day (variant 2) | portfolio Sharpe > best single cell AND maxDD within mandate | `reports/rounds/172_portfolio.md` |
| 173 | P5 portfolio | MULTI | rebalance cadence sweep (variant 2) | portfolio Sharpe > best single cell AND maxDD within mandate | `reports/rounds/173_portfolio.md` |
| 174 | P5 portfolio | MULTI | cash-yield on idle margin (variant 2) | portfolio Sharpe > best single cell AND maxDD within mandate | `reports/rounds/174_portfolio.md` |
| 175 | P5 portfolio | MULTI | equal-weight combo of passing cells (variant 3) | portfolio Sharpe > best single cell AND maxDD within mandate | `reports/rounds/175_portfolio.md` |
| 176 | P5 portfolio | MULTI | inverse-vol weights (variant 3) | portfolio Sharpe > best single cell AND maxDD within mandate | `reports/rounds/176_portfolio.md` |
| 177 | P5 portfolio | MULTI | correlation cap 0.7 (variant 3) | portfolio Sharpe > best single cell AND maxDD within mandate | `reports/rounds/177_portfolio.md` |
| 178 | P5 portfolio | MULTI | drawdown-throttled sizing (variant 3) | portfolio Sharpe > best single cell AND maxDD within mandate | `reports/rounds/178_portfolio.md` |
| 179 | P5 portfolio | MULTI | kill-switch on 3 sigma day (variant 3) | portfolio Sharpe > best single cell AND maxDD within mandate | `reports/rounds/179_portfolio.md` |
| 180 | P5 portfolio | MULTI | rebalance cadence sweep (variant 3) | portfolio Sharpe > best single cell AND maxDD within mandate | `reports/rounds/180_portfolio.md` |
| 181 | P5 portfolio | MULTI | cash-yield on idle margin (variant 3) | portfolio Sharpe > best single cell AND maxDD within mandate | `reports/rounds/181_portfolio.md` |
| 182 | P5 portfolio | MULTI | equal-weight combo of passing cells (variant 4) | portfolio Sharpe > best single cell AND maxDD within mandate | `reports/rounds/182_portfolio.md` |
| 183 | P5 portfolio | MULTI | inverse-vol weights (variant 4) | portfolio Sharpe > best single cell AND maxDD within mandate | `reports/rounds/183_portfolio.md` |
| 184 | P5 portfolio | MULTI | correlation cap 0.7 (variant 4) | portfolio Sharpe > best single cell AND maxDD within mandate | `reports/rounds/184_portfolio.md` |
| 185 | P5 portfolio | MULTI | drawdown-throttled sizing (variant 4) | portfolio Sharpe > best single cell AND maxDD within mandate | `reports/rounds/185_portfolio.md` |
| 186 | P6 governance | ALL | monthly decay review of every live pod | evidence on file before any capital moves | `reports/rounds/186_governance.md` |
| 187 | P6 governance | ALL | retire a cell after 2 sigma degradation | evidence on file before any capital moves | `reports/rounds/187_governance.md` |
| 188 | P6 governance | ALL | re-run DSR with the true cumulative trial count | evidence on file before any capital moves | `reports/rounds/188_governance.md` |
| 189 | P6 governance | ALL | independent replication of the best cell | evidence on file before any capital moves | `reports/rounds/189_governance.md` |
| 190 | P6 governance | ALL | capital-scaling checklist before any real money | evidence on file before any capital moves | `reports/rounds/190_governance.md` |
| 191 | P6 governance | ALL | documented stop conditions per strategy | evidence on file before any capital moves | `reports/rounds/191_governance.md` |
| 192 | P6 governance | ALL | quarterly data-source audit | evidence on file before any capital moves | `reports/rounds/192_governance.md` |
| 193 | P6 governance | ALL | monthly decay review of every live pod | evidence on file before any capital moves | `reports/rounds/193_governance.md` |
| 194 | P6 governance | ALL | retire a cell after 2 sigma degradation | evidence on file before any capital moves | `reports/rounds/194_governance.md` |
| 195 | P6 governance | ALL | re-run DSR with the true cumulative trial count | evidence on file before any capital moves | `reports/rounds/195_governance.md` |
| 196 | P6 governance | ALL | independent replication of the best cell | evidence on file before any capital moves | `reports/rounds/196_governance.md` |
| 197 | P6 governance | ALL | capital-scaling checklist before any real money | evidence on file before any capital moves | `reports/rounds/197_governance.md` |
| 198 | P6 governance | ALL | documented stop conditions per strategy | evidence on file before any capital moves | `reports/rounds/198_governance.md` |
| 199 | P6 governance | ALL | quarterly data-source audit | evidence on file before any capital moves | `reports/rounds/199_governance.md` |
| 200 | P6 governance | ALL | monthly decay review of every live pod | evidence on file before any capital moves | `reports/rounds/200_governance.md` |

## Standing rules

- M-107: the hypothesis is in `reports/hypothesis_registry.json` before the first backtest of that round.
- A cell that fails is reported with its failure mode (`REFUTED_OR_WEAK`, `FAILS_2X_COST`, `FAILS_BENCHMARK`, `DATA_INTEGRITY_FAIL`, `INSUFFICIENT_N`) and never deleted.
- Class claims always quote population and cost basis, never a PF alone.
- `PASSES_ALL_BACKTEST_GATES` is a backtest verdict. Money requires G8 (n>=100 closed forward trades), which no class has yet.
- Machine-readable plan: `reports/round_plan_200.json`.
