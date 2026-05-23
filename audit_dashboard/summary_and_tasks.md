# IDE Log Summary & Remaining Tasks

## Summary of Recent Changes
- **Trust‑tier scoring** added to `audit_dashboard/index.html` and `template.html` (PROVEN = 1.0×, SANDBOX = 0.25×, PROBATION = 0.1×).  
- **Score tooltip** now shows a “Trust” bar and tier badge (green P for PROVEN, red ! for PROBATION).  
- **Score badge** displays the tier badge next to the grade letter.  
- **DisplayName** reference error fixed in `renderAgreementMatrix`.  
- **Timezone bug** fixed – timestamps are now parsed as UTC (`…Z`).  
- **Sanity‑check** for risk‑reward ratio added to `alpha_engine/main.py` and corrected for SHORT trades.  
- **keltner & baby_strats** restored to PROBATION tier (user requested “don’t kill, sandbox”).  
- **Live Binance price enrichment** added to `audit_trail/dashboard_generator.py` to compute unrealized PnL.  
- **Best Picks filter** simplified – now only caps age (≤ 48 h) and relies on trust‑tier weighting.  
- **Aggressive battleground variants** (6 new strategies) and **fast Alpha Engine variants** (7 new strategies) committed and deployed.  
- All fixes have been pushed and the latest GitHub Actions run (`audit-dashboard`) succeeded, so the live dashboard at https://findtorontoevents.ca/audit/ reflects the updates.  

## Remaining / Open Tasks
1. **Verify Best Picks ordering** – ensure the increased freshness weight (now 30 %) and live age calculation correctly push today’s picks to the top.  
2. **Monitor trust‑tier evolution** – watch for PROVEN picks gaining full weight and PROBATION picks staying penalised.  
3. **Permutation Portfolio Integration** – add a link from the main audit dashboard to the permutation dashboard (`paper_trading/data/permutation_dashboard.html`) and optionally create a GitHub Actions workflow to refresh it regularly.  
4. **Add a “Refresh” button** on the audit dashboard (optional) to force a client‑side reload of the JSON payload for instant updates.  
5. **Documentation** – update `audit_dashboard/score_analysis.md` to describe the new freshness weighting and live‑price enrichment.  

These items are low‑priority; the core functionality (trust tiers, tooltip, badge, live PnL, and aggressive variants) is already live and working.
