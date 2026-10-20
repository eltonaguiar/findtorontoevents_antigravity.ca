# Strategy Idea List for Nemotron Money Ready Evaluation

## 1. Bond Yield Curve Slope (bond_yield_curve_slope) - TESTED
- **Source**: Fama-Bliss/Estrella-Mishkin academic theory; appeared in commodity_bond_v2 report (9/9 wins in 14d panel)
- **Claimed Performance**: Strong in-sample performance based on term premium signals
- **Actual OOS Results**: PF=1.115, WR=53.3%, MDD=2.0%, n=1530
- **Why Stalled/Failed**: PF too low (1.115 < 1.5), PF CI too low (1.000 < 1.2), MC percentile insufficient (48.20 < 95), PF at 2x costs ineffective (0.003 < 1.3), concentration risk - all trades in one symbol (100% > 30%)
- **Label**: FAIL

## 2. CTA Cross-Asset TS MOM (cta_cross_asset_tsmom) - NOT TESTED
- **Source**: CTA trend following literature; referenced in alpha_engine/CTA strategies
- **Claimed Performance**: Diversified momentum across asset classes; reported 0.8-1.2 Sharpe in literature
- **Why Stalled**: OOS performance degraded post-2008; crowded trade; whipsaws in sideways markets; high turnover increases costs; FOREX category hard-blocked due to 0/86 WR in live audit
- **Note**: Bond/equity/commodity components may still be viable

## 3. TIPS Breakeven Inflation (bond_tips_breakeven) - NOT TESTED
- **Source**: Bond market inflation expectations theory; implemented in bond_tips_breakeven.py
- **Claimed Performance**: Captures real yield and inflation expectations spread
- **Why Stalled**: TIPS liquidity issues; breaks down during flight-to-quality; Fed policy distortions; high bid-ask spreads

## 4. Equity Sector Rotation (equity_sector_rotation) - PARTIALLY TESTED
- **Source**: Classical sector rotation based on business cycle; implemented in equity_sector_rotation.py
- **Claimed Performance**: Rotates to leading sectors; reported annual returns of 10-15% in backtests
- **Actual OOS Results**: PF=2.136, WR=70.1%, MDD=15.5%, n=127 (from backtest)
- **Why Stalled**: Sector correlations increased post-2008; ETF flows distort signals; rotation timing difficult; overweight to mega-cap stocks
- **Current Assessment**: Strong candidate - only MC percentile slightly below threshold in estimates
- **Label**: CANDIDATE (pending full MC test)

## 5. Commodity Momentum Term Structure (commodity_momentum_term) - NOT TESTED
- **Source**: Commodity carry and momentum strategies; CTA_bridge.py wrapper
- **Claimed Performance**: Combines roll yield and momentum; reported 0.6-0.9 Sharpe
- **Actual OOS Results (from report)**: PF=1.69, WR=58.3%, MDD=-33.8%
- **Why Stalled**: Contango/backwardation regime shifts; storage cost changes; ETF contango bleed; regulatory impacts on futures
- **Label**: FAIL (based on report - MDD too high)
