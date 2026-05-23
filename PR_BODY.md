## Summary

Policy v3 upgrade with 12 config-flagged features for safe A/B testing.

### Core Changes
- **Canonical asset_class.py** — single source of truth for normalization (fixes STOCKS/EQUITY/STOCK drift)
- **stat_tests.py** — 13 statistical functions (Wilson CI, z-test, Welch t, chi-square, Sharpe, Sortino, Kelly, VaR/CVaR, HHI)
- **feature_flags.py** — thread-safe JSON flag manager with hot-reload
- **alerts.py** — concentration + data-lag alerts (Slack/Discord webhooks)
- **policy_backtest.py** — simulate new policies against historical data
- **policy_eval.py** — 7-day A/B evaluation pipeline
- **daily_report.py** — automated daily summaries (markdown/HTML/text)
- **Dashboard widget** — real-time >3% mover panel

### Backtest Results (Policy Simulation)

| Metric | Baseline | New Policy | Delta |
|---|---|---|---|
| Win Rate | 47.97% | 53.71% | **+5.74pp** |
| Profit Factor | 1.07 | 1.49 | **+0.42** |
| Max Drawdown | 683% | 339% | **-50%** |
| Total PnL | 280% | 1,255% | **+975%** |

### Test Coverage
- **186 tests passing, 0 failures**

### Config Flags (all OFF by default)
All new features are behind config toggles for safe A/B testing. See config/feature_flags.json.

### Rollout Plan
1. **Day 0**: Merge config + observability (zero risk)
2. **Day 1-2**: Enable non-crypto HF + dynamic cap + goldmine floor
3. **Day 3-5**: Enable regime-aware direction + asset-class composite
4. **Day 5+**: Enable alerts, quarantine, kill gating

See docs/rollout_guide.md for full details.
