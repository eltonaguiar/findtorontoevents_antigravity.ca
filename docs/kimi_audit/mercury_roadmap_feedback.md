# Mercury's Feedback on Grok's World-Class Roadmap
## Date: 2026-03-16

## Key Enhancements Recommended

### 1. Conditional Blocks (not permanent kills)
- Don't permanently disable strategies — re-enable if they prove value in specific regimes
- Example: A strategy with 40% overall WR might be 70% WR in high-volatility regimes only
- **Status:** Not implemented. Our blocks are permanent. Consider adding regime-conditional re-enablement.

### 2. Continuous Penalty Function (not discrete tiers)
- Instead of discrete tiers (0.35/0.65/1.0/1.10/1.15), use:
  `multiplier = 1 - (0.1 * (1 - confidence))`
- Keeps marginal edges alive while still penalizing low-confidence
- **Status:** Using discrete tiers in Signal Insight Engine. Could smooth this.

### 3. Sliding ADX/Volatility Scale
- Binary ADX<20 = MR only is too blunt
- Mean-reversion opportunities exist at ADX 25-30
- Use sliding scale 15-30 and A/B test against binary
- **Status:** Our regime_meta_router uses weighted consensus which is already a sliding scale.

### 4. CI/CD Testing
- No automated tests for new strategy modules
- Could introduce regressions
- **Status:** No CI tests for strategies. Should add.

### 5. Real-Time Drift Detection
- Monitor live WR, PF, regime indicators
- Alert when metrics deviate >10% from expected
- **Status:** Pick monitor exists but no drift alerts.

### 6. Time-Based Trust Window
- 30-trade minimum too low for low-frequency assets
- Use 2-week window in addition to trade count
- **Status:** Not implemented. Good idea for forex/weekly strategies.

### 7. Net-Sharpe with Costs
- Paper trading should track "net-Sharpe" after 0.02% per trade costs
- **Status:** Score Leaders tracks commissions+slippage. Could compute net-Sharpe.

## Overall Assessment
"Well-structured, biggest risk is over-engineering without sufficient validation loops."
