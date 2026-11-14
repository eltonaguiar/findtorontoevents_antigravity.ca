# Local Uncommitted Files — Last 24 Hours (Financial Prediction)

**Worktree:** flaxen-hair_2026-11-14T2150 | **Scope:** uncommitted files in the local tree related to financial prediction

## Git Status

Modified: `___HELL_HEALTH_OPENCODE.MD`

Untracked (financial-prediction-relevant subset):
- `dashboard/live_picks.json`
- `mercury2/data/metrics_report.json`
- `research/profitability/*` (protocol, hypotheses, scorecard, runs v1-v4, validation, forward ledger)
- `research/asset_class/equity/run_*/` (multiple backtest runs)

## Key Findings

### MARKET_BEATING_REPORT.md (auto-generated, 18:43Z)

- Total signals tracked: 409; validated: 406
- Overall accuracy: 58.3% (target 60%, below target)
- Crypto: BTC-USD 50% (48 sig), ETH-USD 64% (55 sig), SOL-USD 47% (33 sig), ADA-USD 66.7% (32 sig), DOT-USD 60% (37 sig)
- Forex: EUR-USD 61.9% (22), GBP-USD 54.2% (25), USD-JPY 58.8% (17)
- Status: OPTIMIZING / BELOW TARGET

**Assessment:** Accuracy below target, small samples, no cost model, no statistical controls. Not proof of edge.

### dashboard/live_picks.json

39 active picks across systems/strategies. Notable:
- All bond strategies: 0 winners, 0.0 PnL
- `atr_percentile_gate_scanner`: 6 picks, 3 winners, +0.0057% total PnL
- Multiple `inverse_ml_enhanced_*` strategies: 0 winners, 0.0 PnL
- `luxalgo_confluence`: 3 picks, 0 winners, −0.0152% PnL

**Assessment:** Live picks are near break-even or negative. No strategy shows meaningful positive PnL.

### mercury2/data/metrics_report.json (18:39Z)

- Closed trades: 469; rows with confidence+pnl: 466
- Win rate (economic PnL): 40.09%
- Pearson IC (confidence vs PnL): 0.0391; Spearman IC: 0.1046 — **near-zero correlation**
- Hit rate @ top 3: 0.0%; @ top 5: 0.0%; @ top 10: 20.0%
- Quality flags: `low_linear_ic`, `weak_top5_hit_rate`

**Assessment:** ML confidence has essentially no linear relationship with PnL. Confidence cannot be used to rank picks.

### research/profitability/* (23 hypotheses, v1-v4)

**0/23 PROVED.** Scorecard: 7.0/10 overall, 0/10 actual profitability proof.

Best candidates:
- H10 RSI(2)+cash (SPY/QQQ): Sharpe 1.83, CAGR 22.0% — but contaminated OOS, effective N≈38, single-day dependence, execution fragility
- H22 BTC funding carry: Sharpe 14.24, 4.8% capital-adjusted — but n=10 < 30 minimum

All other candidates: NOT_PROVED with negative or negligible edge.

### research/asset_class/equity/* (multiple backtest runs)

All equity strategies: MIXED or NO_EDGE. Tiny samples (3-6 trades), simplified signal parsing (SMA crossover proxy), insufficient for robust inference. No strategy meets the 100-trade minimum.

## Conclusion from Local Files

No local uncommitted file demonstrates a profitable approach. The strongest signal (H10 RSI(2)) fails the strict proof standard. The live dashboard and ML metrics both show near-zero or negative predictive value. The 90-day execution roadmap in final_v3/01_focus_decision/DECISION.md remains the correct path.
