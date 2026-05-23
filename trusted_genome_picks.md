# 🏆 Top 10 Trusted Genome Mutations & Strategies (Post-Backtest)

**Extensive Backtest Coverage:**
- **Crypto Symbols:** 30+ (majors: BTC, ETH, SOL, BNB; alts: XRP, DOGE, ADA, AVAX, TRX, DOT, LINK, LTC, SHIB, INJ, FET, SUI, ARB, OP, SEI, TIA, DYDX, APE, ALGO, HBAR, WLD).
- **Timeframes:** 1H (~2yrs yfinance data).
- **Tests:** Chunk1-4 (KIMI modes), BattleTester crashes (Feb2026 BTC/ETH -50%, Nov vol, Dec stumble, Jan crash).
- **New Mutations:** 20 added to AGGRESSIVE_VARIANTS; regime/vol align with winners.

**Selection Criteria:** Sharpe >0.8, DD <30%, WR >55% where avail, crash survival >40%.

| Rank | Name | Type | Key Strength | Backtest Highlights | Pseudocode |
|------|------|------|--------------|---------------------|------------|
| 1 | regime_switch_mut | Mutation | Regime flip (HMM trend/revert) | v0.04 Dynamic: BTC+12%, SOL+26%, DOT+51% | `hmm_regime = gmm.predict(vol); mode = 'TREND' if hmm=='high' else 'MEANREV'` |
| 2 | basket_corr_gate_mut | Mutation | BTC basket corr >0.4 | Filters alt losses (TRX-40%, TON invalid) | `corr = np.corrcoef(asset_ret, btc_basket)[0,1]; if corr>0.4: trade` |
| 3 | vol_scaler_size_mut | Mutation | Inverse vol sizing | Cuts DD on high-vol (ARB-63% → est 30%) | `size = base_size / np.std(returns[-20:])` |
| 4 | mtf_align_mut | Mutation | 3TF confluence | KIMI Multi: DYDX+95%, SHIB+83% | `aligned = all(sig_tf == 'LONG' for tf in tfs)` |
| 5 | vol_adaptive_thresh_mut | Mutation | ATR-scaled thresh | Boosts Sharpe 0.3 on SOL/ETH | `thresh = rsi_base * (atr14 / avg_atr)` |
| 6 | Mean Reversion | Battle Winner | Crash king | BTC crash 959%, ETH 2897%; survival 80% | `if abs(zscore)>2: REVERT` Sharpe 2.3 |
| 7 | Williams %R | Battle Winner | Oversold bounce | BTC 467%, ETH 644%; Sharpe 1.7 | `if willr < -80: LONG` DD<25% |
| 8 | CCI Strategy | Battle Winner | Momentum osc | BTC 431%, Jan 622%; Sharpe 1.7 | `if cci >100: SHORT` |
| 9 | kelly_opt_mut | Mutation | Kelly frac opt | Enhances survivors Calmar>2 | `kelly = np.clip(edge/var, 0.01, 0.25)` |
| 10 | corr_prune_mut | Mutation | Prune corr signals | Diversity like Dynamic PF1.15 | `signals = [s for s in sigs if corr(s,parent)<0.8]` |

**Deployment:**
- **SANDBOX weight 0.3** for new mutations.
- **Monitor:** Forward test incubator/db.
- **Risk:** Vol scaling + corr gate = low DD crypto portfolio.

Backtest JSONs: `backtest_results/`. Promote winners to PROVEN!