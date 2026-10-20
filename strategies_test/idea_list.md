# Strategy Idea List for Nemotron Money Ready Evaluation

## 1. Bond Yield Curve Slope (bond_yield_curve_slope)
- **Source**: Fama-Bliss/Estrella-Mishkin academic theory; appeared in commodity_bond_v2 report (9/9 wins in 14d panel)
- **Claimed Performance**: Strong in-sample performance based on term premium signals
- **Why Stalled**: Theoretical strategy hasn't shown consistent OOS performance; sensitive to regime changes in interest rates; transaction costs erode edge in low-volatility bond markets

## 2. CTA Cross-Asset TS MOM (cta_cross_asset_tsmom)
- **Source**: CTA trend following literature; referenced in alpha_engine/CTA strategies
- **Claimed Performance**: Diversified momentum across asset classes; reported 0.8-1.2 Sharpe in literature
- **Why Stalled**: OOS performance degraded post-2008; crowded trade; whipsaws in sideways markets; high turnover increases costs

## 3. TIPS Breakeven Inflation (bond_tips_breakeven)
- **Source**: Bond market inflation expectations theory; implemented in bond_tips_breakeven.py
- **Claimed Performance**: Captures real yield and inflation expectations spread
- **Why Stalled**: TIPS liquidity issues; breaks down during flight-to-quality; Fed policy distortions; high bid-ask spreads

## 4. Equity Sector Rotation (equity_sector_rotation)
- **Source**: Classical sector rotation based on business cycle; implemented in equity_sector_rotation.py
- **Claimed Performance**: Rotates to leading sectors; reported annual returns of 10-15% in backtests
- **Why Stalled**: Sector correlations increased post-2008; ETF flows distort signals; rotation timing difficult; overweight to mega-cap stocks

## 5. Commodity Momentum Term Structure (commodity_momentum_term)
- **Source**: Commodity carry and momentum strategies; CTA_bridge.py wrapper
- **Claimed Performance**: Combines roll yield and momentum; reported 0.6-0.9 Sharpe
- **Why Stalled**: Contango/backwardation regime shifts; storage cost changes; ETF contango bleed; regulatory impacts on futures
