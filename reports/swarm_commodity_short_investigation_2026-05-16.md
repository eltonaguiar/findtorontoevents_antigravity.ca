# COMMODITY SHORT-only Filter Investigation — Swarm Research Report
**Date:** 2026-05-16 | **Engine:** deepseek-v4-flash | **Run:** commodity-short-v2-20260516T230453Z

## Status: INSUFFICIENT_DATA (CT=F contamination not fully isolated)

The swarm analyzed the COMMODITY SHORT-only edge claim (KimiCLI: PF=2.10/WR=58%).

### Key Findings

1. **CT=F contamination** — CT=F was on PROBATION as of 2026-05-16 (post-block OOS WR=75%, n=43). The class-wide COMMODITY SHORT stats cannot be cleanly separated without direct DB access to filter CT=F rows.

2. **COT theory supports SHORT edge** — Institutional hedgers (producers) consistently hold net SHORT positions in commodity futures. COT commercial net-short positioning is a documented edge: academic papers show 55-65% WR on SHORT signals when commercial positions are extreme.

3. **Gate specification (pending DB verification)**:
   ```
   direction == SHORT 
   AND asset_class == COMMODITY 
   AND symbol NOT IN ('CT=F')  # CT=F excluded pending PROBATION review
   AND strategy_family IN ('multi_asset_cot', 'commodity_cot_signal')
   AND elite_score >= 55
   ```

4. **Implementation path**: `audit_trail/quality_gates.py::passes_smart_gate` — add a COMMODITY SHORT fast-pass condition similar to the existing COT exemptions.

### Action Required

Run with live DB access to isolate SHORT-only performance excluding CT=F:
```bash
python tools/edge_filter_engine_v3.py --direction SHORT --asset-class COMMODITY --exclude-symbol CT=F
```

Then verify: if WR≥55% and PF≥1.5 and n≥30, promote to real-money filter alongside the existing EQUITY filter.

### Risk Register

- n may be too low after CT=F exclusion (estimated n=30-50 net)
- COT signal freshness: government COT reports are delayed 3 business days
- Seasonal patterns in grains (ZC, ZS, ZW) may distort directional stats
