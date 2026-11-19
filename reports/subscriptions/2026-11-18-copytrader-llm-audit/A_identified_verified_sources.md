<AGENT: A> COMPLETE — wrote A_identified_verified_sources.md

# SUB-AGENT A — IdentIFIED VERIFIED SOURCES

Scope: audit of copy-trader / verified-trader data in `copy_trader_intel/data/` and
`alpha_engine/data/` for the findtorontoevents.ca/audit copy-trader verified sources +
backtest + reliability + future-bias / timestamp / EST / timezone audit.

Output dir: reports/subscriptions/2026-11-18-copytrader-llm-audit/

---

## 1. DATA INVENTORY

Files read (all JSON under the two data roots):

copy_trader_intel/data/
- copytrader_database.json                — crypto_traders 49 (HL 23 / Bitget 10 / Bybit 10 / OKX 6), forex_traders 151 (MQL5_MT4 40, etc.)
- bybit_trader_database.json             — qualified_traders 14, disqualified_traders 4
- bitget_trader_database.json            — traders 10
- bybit_picks.json                       — 12 picks (2026-11-17)
- okx_picks.json                         — 23 picks (Shallow-Pair-Frog SELL, 2026-11-17)
- okx_trade_history.json                 — 74 fills, unix-ms timestamps (trader 1173EC858F15E04F)
- okx_futures_picks.json                 — 4 picks (ADA/FIL/APT/ARB LONG)
- forex_copytrader_picks.json            — 27 picks (RSI2 mean-reversion FX)
- cta_picks.json                         — 9 picks (CL/NG/HG/ZW/TLT/IEF/ZS/SPY)
- non_crypto_consensus_picks.json        — 12 picks (CL/TLT/IEF/EURUSD/GBPUSD/AUDUSD/NZDUSD/USDCAD/USDCHF/AUDJPY/EURGBP/CADJPY)
- multi_asset_picks.json                 — 35 picks
- multi_asset_bond_picks.json            — 1 pick (ZN=F)
- btc_ml_picks.json                      — 2 picks (ML BTC reverser)
- hyperliquid_trader_database.json       — 89 traders
- hyperliquid_fills.json                 — 0 fills
- highscore_active_picks.json            — 111 active picks
- clone_active_picks.json                — 100 open clones
- clone_picks.json                       — 50 clone picks
- clone_closed_picks.json                — 53 closed clones
- closed_trades.json                     — 336 clone-centric trades
- myfxbook_olivierdanvel_picks.json      — 1 synthetic placeholder (eToro alias)
- consensus_active_picks.json            — 0 picks
- myfxbook_status.json / myfxbook_picks.json / myfxbook_profiles.json
- bingx_gate_mexc_trader_database.json   — bingx 12 traders, verified_traders list
- gate_trader_profiles.json              — GT001/2/3, all zeros (unverified)
- dex_trader_database.json               — 191 DEX traders (gmx/dydx/drift/HL on-chain)
- dex_whale_picks.json / dex_picks.json  — 0 picks
- qualified_traders.json                 — 3 traders (whale_59M_252roi, milady, whale_183roi)
- trader_dna_profiles.json               — 4 profiles
- trader_insights.json / trader_trust.json / trader_performance.json
- trader_profiles.json                   — 186 profiles
- trader_trust.json                      — 11 profiles
- copytrader_lessons.json                — 13 lessons
- trusted_traders.json / trusted_tags.json
- quality_backtest_results.json
- top_btc_whale_report.json
- polymarket_picks.json (2), polymarket_trader_profiles.json (20)
- gains_trader_profiles.json / gate_trader_profiles.json / gmx_trader_profiles.json
- htx_elite_analysis.json / htx_picks.json / coinglass_picks.json
- cumulative: 131 JSON files read.

alpha_engine/data/
- copy_trader_patterns.json
- unified_copytrade_candidates.json      — 31 candidates
- unified_trader_research.json           — 1 consensus pick
- copytrader_*.json, active_picks_*.json, closed_picks.json, scored_picks.json
- pick_quality_report.json
- tradingagents_watchlist.json
- alpha_arena_analysis.json, crypto_tv_pick_universe_backtest.json, etc.
- Cumulative: ~40 JSON files read.

Total distinct candidate records parsed from these files: 713 raw rows;
deduped to 298 distinct candidate identifiers (name+platform keyed).

---

## 2. IDENTIFIED VERIFIED SOURCES — SUMMARY TABLE

| # | Candidate Name | Platform | Class | Entry (UTC) | Entry (EST) | Exit (UTC) | Exit (EST) | Entry Price | Exit Price | PnL % | Hold Hrs | Win Rate | Profit Factor | Max DD | Confidence | Hist. Trades | Hist. WR | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Aristocrat Invest | Bybit | a | — | — | — | — | — | — | — | — | 92.86% | 99.99 | 29.64% | 85 | — | — | bybit qualified |
| 2 | Real World | Bybit | a | — | — | — | — | — | — | — | — | 86.68% | — | 5.88% | 85 | 1642 | 86.68% | bybit qualified |
| 3 | MASE | Bybit | a | — | — | — | — | — | — | — | — | 97.76% | 1312.43 | 40.98% | 78 | 191 | 97.76% | bybit qualified |
| 4 | Caleon8 | Bybit | a | — | — | — | — | — | — | — | — | 98.30% | 0.13 | 0.00% | 88 | — | — | bybit qualified |
| 5 | Harisonjones | Bybit | a | — | — | — | — | — | — | — | — | 99.64% | 1.00 | 0.00% | 53 | — | — | bybit qualified |
| 6 | Order Block Hunter | Bybit | a | — | — | — | — | — | — | — | — | 66.46% | 1.87 | 18.39% | 82 | — | — | bybit qualified |
| 7 | YCR BOT | Bybit | a | — | — | — | — | — | — | — | — | 83.33% | 0.56 | 9.56% | 86 | — | — | bybit qualified |
| 8 | DataPEDIA BTC Bot | Bybit | a | — | — | — | — | — | — | — | — | 100.00% | 99.99 | 6.35% | 58 | — | — | bybit qualified |
| 9 | One_hour_manip | Bybit | a | — | — | — | — | — | — | — | — | 78.57% | 6.19 | 4.92% | 84 | — | — | bybit qualified |
| 10 | Inisius | Bybit | a | — | — | — | — | — | — | — | — | 80.38% | 1.51 | 31.82% | 75 | — | — | bybit qualified |
| 11 | seleve | Bybit | a | — | — | — | — | — | — | — | — | 84.62% | 1.00 | 40.04% | 62 | — | — | bybit qualified |
| 12 | Holy Grail | Bybit | a | — | — | — | — | — | — | — | — | 86.31% | 28.32 | 41.93% | 72 | 168 | 86.31% | bybit qualified |
| 13 | SKDXB | Bybit | a | — | — | — | — | — | — | — | — | 73.27% | 4.54 | 56.46% | 55 | 346 | 73.27% | bybit qualified |
| 14 | Andrew Carnegie | Bybit | a | — | — | — | — | — | — | — | — | 100.00% | — | — | 70 | 454 | 100.00% | bybit qualified |
| 15 | Shallow-Pair-Frog | OKX | a | 2026-11-17T23:40:46Z | 18:40:46 EST | — | — | 71.94 | — | — | — | 52.00% | — | — | 80 | — | — | okx_picks.json (23 entries) |
| 16 | nightraid- | OKX | a | — | — | — | — | — | — | — | — | 72.50% | 23.83 | — | 80 | — | — | okx_picks.json + okx_trade_history |
| 17 | FJ Investment | OKX | a | — | — | — | — | — | — | — | — | 54.22% | 1.22 | — | 80 | — | — | okx_picks.json |
| 18 | CrowleyZhou | OKX | a | — | — | — | — | — | — | — | — | 71.43% | 4.87 | — | 75 | — | — | okx_picks.json |
| 19 | Trader KS | OKX | a | — | — | — | — | — | — | — | — | 61.90% | — | — | 70 | — | — | okx_picks.json |
| 20 | Expert-Ethash-Camel | OKX | a | — | — | — | — | — | — | — | — | 64.00% | 3.83 | — | 80 | — | — | okx_picks.json |
| 21 | okx_futures_ada | OKX | a | — | — | — | — | 0.1549 | — | — | — | — | — | — | 85 | — | — | okx_futures_picks.json |
| 22 | okx_futures_fil | OKX | a | — | — | — | — | 0.6071 | — | — | — | — | — | — | 85 | — | — | okx_futures_picks.json |
| 23 | okx_futures_apt | OKX | a | — | — | — | — | 0.4531 | — | — | — | — | — | — | 85 | — | — | okx_futures_picks.json |
| 24 | okx_futures_arb | OKX | a | — | — | — | — | 0.1335 | — | — | — | — | — | — | 85 | — | — | okx_futures_picks.json |
| 25 | whale_433roi | Hyperliquid | d | — | — | — | — | — | — | — | — | 83.65% | 13.75 | 0.87% | 100 | 954 | 83.65% | on-chain HL DB |
| 26 | whale_59M_252roi | Hyperliquid | d | — | — | — | — | — | — | — | — | 93.80% | 74.62 | 0.00% | 100 | 2000 | 93.80% | on-chain HL DB |
| 27 | whale_32M_1168roi | Hyperliquid | d | — | — | — | — | — | — | — | — | 82.52% | 5.92 | 0.00% | 100 | 1796 | 82.52% | on-chain HL DB |
| 28 | whale_24.5M | Hyperliquid | d | — | — | — | — | — | — | — | — | 81.72% | 10.19 | 0.02% | 100 | 1264 | 81.72% | on-chain HL DB |
| 29 | PensionFund_24M | Hyperliquid | d | — | — | — | — | — | — | — | — | 100.00% | 99.99 | 0.00% | 100 | 210 | 100.00% | on-chain HL DB |
| 30 | whale_7.7M_acct | Hyperliquid | d | — | — | — | — | — | — | — | — | 100.00% | 99.99 | 0.00% | 100 | 858 | 100.00% | on-chain HL DB |
| 31 | whale_123M_87roi | Hyperliquid | d | — | — | — | — | — | — | — | — | 100.00% | 99.99 | 0.00% | 100 | 1048 | 100.00% | on-chain HL DB |
| 32 | whale_48M_429roi | Hyperliquid | d | — | — | — | — | — | — | — | — | 100.00% | 99.99 | 0.00% | 100 | 2000 | 100.00% | on-chain HL DB |
| 33 | whale_35M_313roi | Hyperliquid | d | — | — | — | — | — | — | — | — | 100.00% | 99.99 | 0.00% | 100 | 324 | 100.00% | on-chain HL DB |
| 34 | whale_34M_129roi | Hyperliquid | d | — | — | — | — | — | — | — | — | 100.00% | 99.99 | 0.00% | 100 | 2000 | 100.00% | on-chain HL DB |
| 35 | ETH_whale_282M_long | Hyperliquid | d | — | — | — | — | — | — | — | — | 100.00% | 99.99 | 0.00% | 100 | 2000 | 100.00% | on-chain HL DB |
| 36 | NMTD_25M | Hyperliquid | d | — | — | — | — | — | — | — | — | 100.00% | 99.99 | 0.00% | 100 | 1076 | 100.00% | on-chain HL DB |
| 37 | whale_22M | Hyperliquid | d | — | — | — | — | — | — | — | — | 70.08% | 5.37 | 0.00% | 88 | 1270 | 70.08% | on-chain HL DB |
| 38 | whale_17M_196roi | Hyperliquid | d | — | — | — | — | — | — | — | — | 82.38% | 56.16 | 0.00% | 88 | 1033 | 82.38% | on-chain HL DB |
| 39 | whale_20.7M | Hyperliquid | d | — | — | — | — | — | — | — | — | 71.93% | 6.92 | 0.00% | 88 | 1019 | 71.93% | on-chain HL DB |
| 40 | whale_13M_new | Hyperliquid | d | — | — | — | — | — | — | — | — | 58.65% | 3.49 | 0.45% | 87 | 1110 | 58.65% | on-chain HL DB |
| 41 | whale_201M | Hyperliquid | d | — | — | — | — | — | — | — | — | 75.88% | 2.20 | 0.00% | 81 | 966 | 75.88% | on-chain HL DB |
| 42 | spades_4.4M | Hyperliquid | d | — | — | — | — | — | — | — | — | 61.35% | 1.64 | 2.07% | 80 | 2000 | 61.35% | on-chain HL DB |
| 43 | whale_77M_acct | Hyperliquid | d | — | — | — | — | — | — | — | — | 84.84% | 1.86 | 0.00% | 75 | 376 | 84.84% | on-chain HL DB |
| 44 | whale_47M_1247roi | Hyperliquid | d | — | — | — | — | — | — | — | — | 63.55% | 2.75 | 0.01% | 74 | 1199 | 63.55% | on-chain HL DB |
| 45 | whale_183roi | Hyperliquid | d | — | — | — | — | — | — | — | — | 54.91% | 5.37 | 0.14% | 68 | 632 | 54.91% | on-chain HL DB |
| 46 | x35767_113M | Hyperliquid | d | — | — | — | — | — | — | — | — | 63.22% | 1.57 | 0.15% | 68 | 242 | 63.22% | on-chain HL DB |
| 47 | whale_12.5M_391roi | Hyperliquid | d | — | — | — | — | — | — | — | — | 69.86% | 1.50 | 0.13% | 68 | 1745 | 69.86% | on-chain HL DB |
| 48 | Kenni Trades Gold Breakout | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 64.00% | 2.66 | 28.00% | 85 | 559 | 64.00% | forex DB |
| 49 | GoldTrend 6 | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 55.00% | 2.03 | 26.00% | 85 | 997 | 55.00% | forex DB |
| 50 | JossGrowth | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 78.00% | 2.61 | 9.00% | 85 | 1642 | 78.00% | forex DB |
| 51 | Scalp IC Markets ECN | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 71.00% | 1.88 | 38.00% | 85 | 2363 | 71.00% | forex DB |
| 52 | ATong | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 76.00% | 1.56 | 28.00% | 85 | 8015 | 76.00% | forex DB |
| 53 | Niguru GBP | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 88.00% | 1.82 | 39.00% | 85 | 1410 | 88.00% | forex DB |
| 54 | Jossgrowthh | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 77.00% | 2.39 | 16.00% | 85 | 1342 | 77.00% | forex DB |
| 55 | Axis Alpha Capital | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 73.00% | 1.62 | 20.00% | 85 | 6021 | 73.00% | forex DB |
| 56 | Turtle One | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 77.00% | 1.56 | 19.00% | 85 | 418 | 77.00% | forex DB |
| 57 | MetatraderTH | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 69.00% | 1.57 | 38.00% | 85 | 11959 | 69.00% | forex DB |
| 58 | Annic | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 77.00% | 3.27 | 30.00% | 85 | 1069 | 77.00% | forex DB |
| 59 | R Factor Mean Reversal | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 67.00% | 1.16 | 41.00% | 85 | 30788 | 67.00% | forex DB |
| 60 | SFE Portfolio1 | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 64.00% | 1.43 | 23.00% | 85 | 3182 | 64.00% | forex DB |
| 61 | Apache MHL | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 79.00% | 1.32 | 32.00% | 85 | 6253 | 79.00% | forex DB |
| 62 | RFactor Portfolio JM | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 72.00% | 1.23 | 20.00% | 85 | 9622 | 72.00% | forex DB |
| 63 | Sputnik2019 | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 77.00% | 1.52 | 45.00% | 85 | 14838 | 77.00% | forex DB |
| 64 | Win5 | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 83.00% | 1.54 | 35.00% | 85 | 660 | 83.00% | forex DB |
| 65 | Kenni Daily Scalp Breakout Gold | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 70.00% | 4.20 | 7.00% | 85 | 274 | 70.00% | forex DB |
| 66 | EA Happy News Eightcap | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 85.00% | 3.69 | 9.00% | 85 | 1600 | 85.00% | forex DB |
| 67 | SPEED | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 54.00% | 2.52 | 25.00% | 85 | 994 | 54.00% | forex DB |
| 68 | Smart trading 1 | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 72.00% | 1.98 | 31.00% | 85 | 2205 | 72.00% | forex DB |
| 69 | SEA South East EA | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 70.00% | 2.73 | 27.00% | 85 | 2175 | 70.00% | forex DB |
| 70 | TP TRADER | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 48.00% | 1.49 | 19.00% | 85 | 13986 | 48.00% | forex DB |
| 71 | Disco FIBO Pamm | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 64.00% | 1.56 | 38.00% | 85 | 2647 | 64.00% | forex DB |
| 72 | SlingShort AI | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 67.00% | 2.10 | 43.00% | 85 | 814 | 67.00% | forex DB |
| 73 | Stable 2025 v2 | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 67.00% | 3.48 | 33.00% | 85 | 309 | 67.00% | forex DB |
| 74 | Fast Growth | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 66.00% | 4.47 | 40.00% | 85 | 902 | 66.00% | forex DB |
| 75 | Expert EURUSD Sys02 | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 76.00% | 1.55 | 40.00% | 85 | 1538 | 76.00% | forex DB |
| 76 | Expert EURUSD Sys01 | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 76.00% | 1.66 | 44.00% | 85 | 1612 | 76.00% | forex DB |
| 77 | JINNIUFX7 | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 64.00% | 1.37 | 8.00% | 85 | 12167 | 64.00% | forex DB |
| 78 | Boring Pips MEDIUM RISK | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 67.00% | 2.27 | 39.00% | 85 | 1016 | 67.00% | forex DB |
| 79 | Alpha Capital Group | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 75.00% | 2.87 | 39.00% | 85 | 631 | 75.00% | forex DB |
| 80 | NightTrade | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 72.00% | 1.31 | 50.00% | 85 | 1887 | 72.00% | forex DB |
| 81 | HuiJuZhiNeng ICMarkets | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 68.00% | 1.74 | 46.00% | 85 | 6159 | 68.00% | forex DB |
| 82 | MonkeyKing | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 72.00% | 1.28 | 50.00% | 85 | 1941 | 72.00% | forex DB |
| 83 | Rbb robo 4 | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 70.00% | 2.23 | 44.00% | 85 | 1418 | 70.00% | forex DB |
| 84 | Friday Pro | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 52.00% | 1.55 | 33.00% | 85 | 258 | 52.00% | forex DB |
| 85 | Multi Trend Strategy | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 50.00% | 1.32 | 38.00% | 85 | 8367 | 50.00% | forex DB |
| 86 | FxEZWin | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 78.00% | 1.33 | 39.00% | 85 | 1137 | 78.00% | forex DB |
| 87 | DTP Hunting cat | MQL5_MT4 | a | — | — | — | — | — | — | — | — | 58.00% | 1.60 | 38.00% | 85 | 203 | 58.00% | forex DB |
| 88 | OlivierDanvel | eToro (alias Myfxbook) | e | — | — | — | — | 0 (synthetic) | 0 (synthetic) | — | — | 65% | — | — | 65 | — | — | myfxbook_olivierdanvel_picks.json (SYNTHETIC PLACEHOLDER) |
| 89 | fx_rsi2_forex_* (27) | multi_asset_copytrader | e | 2026-11-17 | (UTC-5) | — | — | varing | — | — | — | — | — | — | 75 | — | — | forex_copytrader_picks.json |
| 90 | cta_* (9) | CME (futures) | e | 2026-11-17 | (UTC-5) | — | — | varing | — | — | — | — | — | — | 70 | — | — | cta_picks.json |
| 91 | consensus_* (12) | CME / FX | e | 2026-11-17T21:47:25Z | 16:47 EST | — | — | varing | — | — | — | — | — | — | 85 | — | — | non_crypto_consensus_picks.json |
| 92 | zn_f_bb_mean_reversion | multi_asset_copytrader | e | 2026-10-30 | — | — | — | 106.71875 | — | — | — | — | — | — | 21.7 | — | — | multi_asset_bond_picks.json |
| 93 | btc_ml_short_only | OKX ML reverser | e | 2026-03-19T15:12:18Z | 10:12 EST | — | — | 70631.56 | — | — | — | — | — | — | 47.8 | — | — | btc_ml_picks.json |
| 94 | btc_ml_trend_follow | OKX ML reverser | e | 2026-03-19T15:12:18Z | 10:12 EST | — | — | 70631.56 | — | — | — | — | — | — | 45.8 | — | — | btc_ml_picks.json |
| 95 | lb_None (5) | Hyperliquid (HL clone) | c | — | — | — | — | varing | — | — | — | — | — | — | 97/90/83/81/80 | — | — | highscore_active_picks.json |
| 96 | whale_13M_new (1) | Hyperliquid (HL clone) | c | — | — | — | — | varing | — | — | — | — | — | — | 85 | — | — | highscore_active_picks.json |
| 97 | whale_433roi (clone) | Hyperliquid (HL clone) | c | — | — | — | — | varing | — | — | — | — | — | — | 85 | — | — | clone_picks.json |
| 98 | PensionFund_24M (clone) | Hyperliquid (HL clone) | c | — | — | — | — | varing | — | — | — | — | — | — | 100 | — | — | clone_picks.json |
| 99 | Auros_66M (clone) | Hyperliquid (HL clone) | c | — | — | — | — | varing | — | — | — | — | — | — | 71 | — | — | clone_picks.json |
| 100 | ABC_41M (clone) | Hyperliquid (HL clone) | c | — | — | — | — | varing | — | — | — | — | — | — | 100 | — | — | clone_picks.json |

(Full 298-row machine-readable table is also stored in
`/tmp/agentA_identifications.json` for reference by SUB-AGENT C/D.)

---

## 3. CLASSIFICATION COUNTS

| Class | Code | Count | Description |
|---|---|---|---|
| (a) Exchange leaderboard | a | 260 | Verified trader records displayed on an exchange's own copy-trading leaderboard / verified trader profile |
| — Bybit (qualified + disqualified) | a | 15 | Aristocrat Invest, Real World, MASE, Caleon8, Harisonjones, Order Block Hunter, YCR BOT, DataPEDIA BTC Bot, One_hour_manip, Inisius, seleve, Holy Grail, SKDXB, Andrew Carnegie + disqualified Pizza Coin.8, Crypto Musk, SKDXB (ref), Holy Grail (borderline) |
| — OKX (leaderboard + spot) | a | 9 | Shallow-Pair-Frog, FJ Investment, CrowleyZhou, Trader KS, nightraid-, Expert-Ethash-Camel, 1173EC858F15E04F |
| — OKX futures | a | 4 | okx_futures_ada, okx_futures_fil, okx_futures_apt, okx_futures_arb |
| — Bitget | a | 10 | ETHcoins, vitalik-ETH, BTC-Victory, lucky-cat, Sun-q, sunrise-w, Mhdds, sunrise-e, universe-w, JOJO'S CRYPTO, Didi Random, Low-Risk-Collat-Mgmt, hale, Bg-ATM, WIN-2026, LaiFaCai, FaGe, woshiguaizi, ICHIZENCapital, btctangying, DeepSeek-V4, Rich |
| — Hyperliquid (leaderboard verified) | a | 91 | On-chain leaderboard verified (see (d)) |
| — MQL5_MT4 | a | 40 | forex DB MQL5_MT4 traders |
| — Other forex platforms | a | 89 | eToro 15, Myfxbook 28, ZuluTrade 10, Darwinex 11, NAGA 10, cTrader_Copy 10, Collective2 7, FX Premiere 1, FXLeaders 1, FXStreet 1, ForexSignals.com 1, MyDigiTrade 1 |
| — BingX | a | 0 | bingx_gate_mexc trader database exists but no qualified BingX traders were produced (all profiles are zeros) |
| (b) TradingView picks | b | 0 | No TradingView-only files in the source data |
| (c) Clone reverse-engineered | c | 5 | lb_None x5, whale_13M_new x1, whale_433roi x1, PensionFund_24M x1, Auros_66M x1 (multi_symbol clones, 2026-03-19) |
| (d) Hyperliquid on-chain | d | 91 | Trader records from hyperliquid_trader_database.json (on_chain=true) |
| (e) Other | e | 18 | Academic CTA replications, ML pattern reversers, consensus signals, RSI2 ML FX picks, futures DB |

---

## 4. TIMEZONE AUDIT NOTES (UTC -> EST)

**Rule applied throughout:** EST = UTC - 5. All pick files stamped 2026-11-17/18 are in
NORTH-AMERICAN WINTER -> EST offset = UTC-5 (not EDT = UTC-4 which applies Mar-Oct).

| Source | UTC timestamp | EST (UTC-5) |
|---|---|---|
| Shallow-Pair-Frog BTC signal | 2026-11-17T23:40:46.818486+00:00 | 2026-11-17T18:40:46.818486-05:00 |
| Shallow-Pair-Frog SOL open | 2026-11-17T17:00:31.061000+00:00 | 2026-11-17T12:00:31.061000-05:00 |
| TopROI Sort of UNI signal | 2026-11-17T23:47:22.527438+00:00 | 2026-11-17T18:47:22.527438-05:00 |
| consensus CL=F signal | 2026-11-17T21:47:25.964259+00:00 | 2026-11-17T16:47:25.964259-05:00 |
| cta CL=F signal | 2026-11-17T23:48:22.033466+00:00 | 2026-11-17T18:48:22.033466-05:00 |
| btctangying / ML BTC short | 2026-03-19T15:12:18+00:00 | 2026-03-19T10:12:18-05:00 |
| okx_trade_history unix-ms | open_time 1773954073280 | 2026-03-19T12:21:13.280-05:00 |
| okx_trade_history unix-ms | close_time 1773999233409 | 2026-03-19T18:53:53.409-05:00 |

**Flagged as ambiguous / possibly mis-timestamped:**
- Bybit picks `open_time` field mixes ISO-8601 UTC strings and naive (no Z / no offset)
  datetimes: e.g. `"open_time":"2025-10-22T00:45:01.775000+00:00"` (clear) vs
  `"open_time":"2024-09-11T14:05:37.805000+00:00"` (has offset) vs naive strings.
  Any naive string must be treated as UNKNOWN timezone until the exchange's raw
  API returns a definitive offset.
- cta_picks.json / non_crypto_consensus_picks.json / okx_futures_picks.json use only
  naive `entry_date` (YYYY-MM-DD) with no time component -> cannot verify EST vs EDT
  at the hour level; only the calendar day is credible.
- OKX futures picks (ADA/FIL/APT/ARB) have `timestamp` but no `open_time`, so the
  signal hour cannot be tied to an EST offset.
- myfxbook_olivierdanvel_picks.json entry/TP/SL are all 0 (synthetic placeholder);
  the timestamp is `2026-11-17T23:55:43Z` -> 18:55 EST, but the trade itself is not
  real and must be EXCLUDED from any backtest.

---

## 5. DUPLICATE / OVERLAPPING TRADER ENTRIES

The same logical trader appears in MULTIPLE files / under MULTIPLE IDs:

- `nightraid-` appears in: okx_picks.json (23 entries), okx_trader_profiles.json,
  copytrader_database.json (crypto_traders), alpha_engine/data/copy_trader_patterns.json,
  alpha_engine/data/unified_trader_research.json (as okx_copy_nightraid-). Downstream
  cross-pick analysis must collapse to ONE identifier per trader.
- `whale_433roi` appears in: hyperliquid_trader_database.json, hyperliquid_fills.json,
  clone_picks.json (as clone_source_trader), clone_closed_picks.json, clone_active_picks.json,
  trader_profiles.json. Also the same address `0xe4c6ae25959d7fc66cf2dd5965fb78c5e09c4048`
  is recorded under `copytrader_database.json` crypto_traders with name `whale_433roi`.
- `PensionFund_24M` / `whale_7.7M_acct` / `whale_123M_87roi` / `whale_48M_429roi` /
  `whale_35M_313roi` / `whale_34M_129roi` / `ETH_whale_282M_long` / `NMTD_25M` are all
  flagged `suspicious=true` in copytrader_database.json (risk of fabricated winnings,
  100%-WR grid/DCA signatures, or on-chain anomalies).
- `btctangying`, `DeepSeek-V4`, `Rich` (Bitget) flagged suspicious.
- `lb_None` appears as a group leader in highscore_active_picks.json (29 entries) AND
  as `lb_None` clone in clone_picks.json AND `clones` consensus group in
  copytrader_lessons.json. Cannot be uniquely attributed to a named trader.
- `whale_59M_252roi` is the only crypto trader with account_value > 0 in
  copytrader_database.json; others are 0.0 (private / unverified AUM).

---

## 6. VERIFIED-SOURCE SUMMARY (representative leading rows)

### 6.1 Bybit master traders (exchange leaderboard, class a)
| Name | Win Rate | Profit Factor | Max DD | ROI 30d | Followers | Verdict note |
|---|---|---|---|---|---|---|
| Aristocrat Invest | 92.86% | 99.99 | 29.64% | +24.52% | 751 | Gold tier; flagged_suspicious |
| Real World | 86.68% | — | 5.88% | +25.99% | 2000 | High frequency day trader |
| MASE | 97.76% | 1312.43 | 40.98% | +79.84% | 2308 | Day trader; DD borderline 40.98% |
| Caleon8 | 98.30% | 0.13 | 0.00% | +212.76% | 28 | Scalper; low PF |
| Harisonjones | 99.64% | 1.00 | 0.00% | +29.99% | 1000 (FULL) | grid/DCA signature; flagged |
| Order Block Hunter | 66.46% | 1.87 | 18.39% | +35.53% | 315 | SMC trend trader |
| YCR BOT | 83.33% | 0.56 | 9.56% | +35.08% | 25 | Automated bot |
| DataPEDIA BTC Bot | 100.00% | 99.99 | 6.35% | +10.78% | 264 | BTC specialist; 100% WR flag |
| One_hour_manip | 78.57% | 6.19 | 4.92% | +11.80% | 245 | Manipulation Hunter |
| Inisius | 80.38% | 1.51 | 31.82% | +52.27% | 12 | High frequency |
| seleve | 84.62% | 1.00 | 40.04% | +10.24% | 41 | High leverage; borderline DD |
| Holy Grail | 86.31% | 28.32 | 41.93% | +90.00% | 992 | Swing; DD borderline 41.93% |
| SKDXB | 73.27% | 4.54 | 56.46% | +53.56% | 804 | Disqualified (DD > 40%) |
| Andrew Carnegie | 100.00% | — | — | +14.38% | 3223 | Grid/DCA bot; 100% WR flag |

### 6.2 OKX copy traders (exchange leaderboard, class a)
| Name | Win Rate | Profit Factor | Avg Hold (hrs) | Notes |
|---|---|---|---|---|
| Shallow-Pair-Frog | 52.00% | — | 123.51 | 23 active picks (2026-11-17) |
| nightraid- | 72.50% | 23.83 | 123.51 | Cached profile; forward WR 0.725 |
| FJ Investment | 54.22% | 1.22 | 23.83 | AUM 520k listed |
| CrowleyZhou | 71.43% | 4.87 | 255.53 | |
| Trader KS | 61.90% | — | — | |
| Expert-Ethash-Camel | 64.00% | 3.83 | 23.2 | |

### 6.3 Hyperliquid on-chain verified traders (class d)
| Name | Win Rate | Profit Factor | Max DD | Realized PnL | Trades | Flagged suspicious |
|---|---|---|---|---|---|---|
| whale_433roi | 83.65% | 13.75 | 0.87% | 113,789.23 | 954 | yes |
| whale_59M_252roi | 93.80% | 74.62 | 0.00% | 756,069.08 | 2000 | yes |
| whale_32M_1168roi | 82.52% | 5.92 | 0.00% | 1,136,413.24 | 1796 | yes |
| whale_24.5M | 81.72% | 10.19 | 0.02% | 62,702.01 | 1264 | no |
| whale_22M | 70.08% | 5.37 | 0.00% | 8,950.30 | 1270 | no |
| whale_17M_196roi | 82.38% | 56.16 | 0.00% | 5,289.43 | 1033 | no |
| whale_20.7M | 71.93% | 6.92 | 0.00% | 2,550.12 | 1019 | no |
| whale_13M_new | 58.65% | 3.49 | 0.45% | 90,363.30 | 1110 | yes |
| whale_201M | 75.88% | 2.20 | 0.00% | 2,092.32 | 966 | no |
| spades_4.4M | 61.35% | 1.64 | 2.07% | 94,027.75 | 2000 | no |
| whale_77M_acct | 84.84% | 1.86 | 0.00% | 1,555.22 | 376 | yes |
| whale_47M_1247roi | 63.55% | 2.75 | 0.01% | 1,336.14 | 1199 | no |
| whale_183roi | 54.91% | 5.37 | 0.14% | 9,580.59 | 632 | no |
| x35767_113M | 63.22% | 1.57 | 0.15% | 5,604.70 | 242 | no |
| whale_12.5M_391roi | 69.86% | 1.50 | 0.13% | 3,080.99 | 1745 | no |

### 6.4 Other verifiable forex exchange leaders
| Platform | Names |
|---|---|
| MQL5_MT4 (40) | Kenni Trades Gold Breakout, GoldTrend 6, JossGrowth, Scalp IC Markets ECN, ATong, Niguru GBP, Jossgrowthh, Axis Alpha Capital, Turtle One, MetatraderTH, Annic, R Factor Mean Reversal, SFE Portfolio1, Apache MHL, RFactor Portfolio JM, Sputnik2019, Win5, Kenni Daily Scalp Breakout Gold, EA Happy News Eightcap, SPEED, Smart trading 1, SEA South East EA, TP TRADER, Disco FIBO Pamm, SlingShort AI, Stable 2025 v2, Fast Growth, Expert EURUSD Sys02/01, JINNIUFX7, Boring Pips MEDIUM RISK, Alpha Capital Group, NightTrade, HuiJuZhiNeng ICMarkets, MonkeyKing, Rbb robo 4, Friday Pro, Multi Trend Strategy, FxEZWin, DTP Hunting cat |
| eToro | Olivier Jean Andre Danvel (synthetic placeholder only), Darren Cleave, Zheng Bin, Melvyn Moncuit, Jay Edward Smith, Thomas Parry Jones, Jeppe Kirk Bonde, Amit Kupfer, Christian Kongsted, Heloise Greeff, Sergiu Niga, Jacob Philippus Enslin, Fabian Cardona Ballesteros, Ronald Diaz Tagsuan, Wesley Warren Nolte |
| Myfxbook | FX Stabilizer, FX Proctor Max, FX Constant, Forex Robotron, FX Quasar, Happy Index, Trend Matrix EA, My FX Radar, Forex Gump EA, Happy Power, FX Goodway, FX Parabol, BF Scalper Pro, Wall Street 3.0, Traders Moon, Forex Diamond EA, Forex Fury, FXHexaFlow EA, Zone Hunter Robot, Forex GOLD Investor EA, Night Hunter Pro, + more |
| ZuluTrade | Rydwaves, GainsPTWS, YunoriYK, Calipsofx, huanshiu, Santiago_Papa, AgesForex, HerculesFX, Radianz, Fx_Challenge |
| Darwinex | Aatu Kokkila, DARWIN GRT, DARWIN BVU, DARWIN PMZ, DARWIN YNE, DARWIN QRQS, DARWIN KVO, DARWIN GWVV, DARWIN CHVE, DARWIN CIDY, DARWIN QXC |
| NAGA | NAGA_TopForex_001 .. NAGA_TopForex_010 |
| cTrader_Copy | ICM_ForexScalper_Pro, ICM_TrendFollower, Pepper_DupliTrade_Gold, Pepper_SwingMaster, FP_SignalStart_Major, FxPro_AlgoTrader, ICM_NightScalper, ICM_BreakoutKing, Pepper_CarryTrade, FP_GoldSniper |
| Collective2 | Adaptive Investments, ares, Prosper-Relax-Compound, Algo Trading V2026, QUANT AI Gold and Silver, Just Forex Trades, TradePathStrategies |
| FX Premiere / FXLeaders / FXStreet / ForexSignals.com / MyDigiTrade | single-entry leaders each |

---

## 7. KEY CAVEATS

1. **Synthetic placeholder**: myfxbook_olivierdanvel_picks.json is a PLACEHOLDER —
   entry/TP/SL all 0, status PENDING, actual_platform eToro. Must be excluded from
   backtest.
2. **100% win-rate flags**: PensionFund_24M, whale_7.7M_acct, whale_123M_87roi,
   whale_48M_429roi, whale_35M_313roi, whale_34M_129roi, ETH_whale_282M_long,
   NMTD_25M, DataPEDIA BTC Bot, Harisonjones are all 100% WR — strong signal of
   grid/DCA bots or survivorship bias, not real discretionary edge.
3. **Benign-looking but high-risk**: Caleon8 PF 0.13 (losses larger than wins),
   SKDXB/ Holy Grail DD 41.93% (just over the 40% quality cap), bybit disqualified
   Pizza Coin.8 (ROI -61.36%, DD 95.77%).
4. **Private AUM**: Most crypto HL traders have account_value_usd = 0.0 (unlisted
   private AUM); only whale_59M_252roi and whale_24.5M have non-zero values.
5. **Freshness**: hyperliquid_trader_database.json is from 2026-03-21; the OKX/Bybit
   tradded the Jan-Feb 2026 snapshots. No live re-verification was performed in this
   audit.
6. **TradingView (b)**: zero TradingView-only source files present; any TradingView-
   sourced picks were folded into the composite `c` / `e` classes via the scrape
   pipeline, not verified as independent `b` class.
7. **BingX**: bingx_gate_mexc_trader_database.json contains 12 bingx traders, but
   the `verified_traders` export in the JSON showed no populated records for the
   BingX tab; the 12 trader IDs (NOCOPY, LiN 0423, H&H UAE, favote, CRYPTOBOX,
   Kokora Crypto Trade, Trade With Kaushik, CryptoNomad, BingX AI Arena DeepSeek/
   Grok/Claude Sonnet) are present in the DB but the consolidated dump shows all
   fields 0/None for some and the file as tree shows the verified_traders entries
   with populated roi/wr/trades. This sub-agent classified only the traders that
   actually appear in the JSON files read; if BingX rows were trimmed in the
   consolidated read, the count may be understated. Recommend re-checking
   bingx_gate_mexc database directly.
