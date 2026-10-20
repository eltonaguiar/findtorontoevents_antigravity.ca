# Audit Dashboard Copy Trader Analysis - STALE DATA

**Analysis Time:** 2026-10-20T02:18:26+00:00  
**Data Source:** /home/eaguiar2015/findtorontoevents_antigravity.ca/audit_dashboard/data/copytrade_pm_consensus.json  
**Data Generated At:** 2026-04-12T21:48:49.130760Z  

## CONTINGENCY TRIGGERED: DATA IS STALE

The data in copytrade_pm_consensus.json is **stale** (generated 191 days, 4 hours, 29 minutes ago), which exceeds the 24-hour freshness threshold specified in the contingency instructions.

**Required Action:** Stop further analysis as per contingency protocol.

**Next Steps:** 
1. Refresh the copytrade_pm_consensus.json data source
2. Re-run analysis with fresh data (≤24h old)
3. Then evaluate each pick class against gates: n≥100, PF≥1.5, WR≥50%, MDD≤20%

**Note:** No financial analysis or class breakdown performed due to stale data condition.