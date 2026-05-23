# COMMODITY SHORT-only Filter Investigation

## Context

You are a quantitative analyst for a live trading system at findtorontoevents.ca/audit.

The system trades COMMODITY picks (Cotton CT=F, Gold GC=F, Crude CL=F, Copper HG=F, Soybean Meal ZM=F, etc.).
KimiCLI found that COMMODITY SHORT-only picks may have PF=2.10 / WR=58% — a potential second real-money filter tier.

The system currently uses `audit_trail/quality_gates.py::passes_smart_gate()` and the filter engine at `tools/edge_filter_engine_v3.py`.

## Your Task

1. **Read** the following files:
   - `tools/edge_filter_engine_v3.py` — understand how to invoke it
   - `audit_dashboard/data/dashboard_data.json` — get current COMMODITY stats
   - `audit_trail/quality_gates.py` — look for COMMODITY-specific gate config (lines 1-100, search for COMMODITY)
   - `tools/weekly_filter_picks.py` — how the weekly filter works

2. **Analyze** the COMMODITY SHORT edge claim:
   - What is the current COMMODITY class WR, PF, n (from dashboard_data.json)?
   - Is CT=F on PROBATION? (check BLOCKED_ASSET_STRATEGY_PAIRS or similar)
   - What strategies drive COMMODITY picks?
   - Why would SHORT-only outperform LONG+SHORT? (COT theory: institutional SHORT hedging)

3. **Determine** whether the edge is real:
   - If you can run `python tools/edge_filter_engine_v3.py --direction SHORT --asset-class COMMODITY`, do it
   - Otherwise, derive from resolved picks in `audit_dashboard/data/dashboard_data.json` or `audit_trail/data/universal_resolved_picks.json`
   - Separate CT=F rows from HG=F, GC=F, CL=F, ZM=F rows to eliminate CT=F contamination

4. **Produce a recommendation** with:
   - VERDICT: REAL_EDGE / INSUFFICIENT_DATA / NOISE
   - Supporting stats: WR, PF, n (excluding CT=F)
   - Gate specification: what filter criteria would capture this edge
   - Implementation path: which function in quality_gates.py to modify

## Output Format (JSON)

```json
{
  "verdict": "REAL_EDGE | INSUFFICIENT_DATA | NOISE",
  "commodity_short_stats": {"wr": 0.0, "pf": 0.0, "n": 0, "excluding_ctf": true},
  "commodity_overall_stats": {"wr": 0.0, "pf": 0.0, "n": 0},
  "ct_f_contamination_removed": true,
  "recommended_gate": "direction == SHORT AND asset_class == COMMODITY AND elite_score >= X",
  "implementation_file": "audit_trail/quality_gates.py",
  "implementation_function": "passes_smart_gate",
  "confidence": "HIGH | MEDIUM | LOW",
  "rationale": "one paragraph"
}
```
