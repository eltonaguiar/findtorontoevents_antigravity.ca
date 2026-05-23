# Deployment Status - March 8, 2026

## GitHub Sync

| Status | Details |
|--------|---------|
| **Status** | ✅ SYNCED |
| **Latest Commit** | 80bfb3654 - feat(alpha-engine): deploy 6 proven prop-firm elite strategies (Wave 20, 156 total) |
| **Previous** | 62f96da37 - Update HTML page with futures market comparison - March 8, 2026 |

### Files Synced to GitHub
- `updates/index.html` - Updated with futures market comparison
- `updates_findtorontoevents.md` - Markdown updates
- `PROP_FIRM_FUTURES_COMPARISON_SUMMARY.md` - Full comparison report
- `NEW_STRATEGIES_FINAL_REPORT.md` - Strategy final report
- `backtest_results/futures_comparison/` - Analysis data
- `futures_market_comparison_analysis.py` - Analysis engine
- `generate_futures_comparison_chart.py` - Chart generator

## Remote Site Deployment

### Automatic Deployment (GitHub Actions)
The site is automatically deployed via GitHub Actions when changes are pushed to main:

| Workflow | Trigger | Status |
|----------|---------|--------|
| `deploy-riseoftheclaw.yml` | Push to main, every 20 min | Active |
| `deploy-pages.yml` | Manual (disabled) | Disabled |

### Deployment URLs

| Resource | URL |
|----------|-----|
| **Updates Page** | https://findtorontoevents.ca/updates/ |
| **GitHub Pages** | https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/ |
| **Comparison Report** | https://findtorontoevents.ca/PROP_FIRM_FUTURES_COMPARISON_SUMMARY.md |
| **Strategy Report** | https://findtorontoevents.ca/NEW_STRATEGIES_FINAL_REPORT.md |

## What's New on Updates Page

### March 8, 2026 - Futures Market Comparison Analysis

**Key Metrics Displayed:**
- Win Rate: 70.7% (Our) vs 64.8% (Futures Elite) = **+5.9% advantage**
- Profit Factor: 1.94 vs 1.79 = **+0.15 advantage**
- Sharpe Ratio: 1.41 vs 1.20 = **+0.21 advantage**

**Prop Firm Challenge Pass Probabilities:**
- KC_SCALP_v1: **90%** pass probability
- MTF_RSI_v1: **85%** pass probability
- FLASH_REV_v1: **85%** pass probability
- FUNDING_PRO_v1: **75%** pass probability
- BB_SQUEEZE_v1: **70%** pass probability

**Firm-Specific Recommendations:**
- FTMO: KC_SCALP_v1 (90% pass rate)
- The5ers: FLASH_REV_v1 combo
- MyForexFunds: MTF_RSI_v1
- TrueForexFunds: KC_SCALP_v1

## Verification Checklist

- [x] GitHub commit pushed
- [x] GitHub Actions triggered
- [x] Updates page HTML updated
- [x] Markdown files synced
- [x] Backtest results uploaded

## Next Steps

1. **Verify deployment**: Check https://findtorontoevents.ca/updates/ in 5-10 minutes
2. **Monitor GitHub Actions**: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions
3. **Test links**: Ensure all report links work correctly

---

*Last updated: March 8, 2026*  
*Deployment method: GitHub Actions (automated)*
