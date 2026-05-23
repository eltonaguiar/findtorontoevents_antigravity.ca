# Research Sidecar Harness Verdicts — 2026-05-19

Ran `tools/edge_stability_harness.py` (via each sidecar's `__main__`) on the
3 opt-in research sidecars built this session cycle. All three **REJECTED** —
none admissible, none wired to production. Consistent with the system-wide
no-edge verdict and the 9 prior harness kills.

| Hypothesis | Sidecar | Verdict | Detail |
|------------|---------|---------|--------|
| H-026 ET-1 | `tools/et1_etf_creation_redemption_research.py` | **REJECTED** | 0/62 windows reach eff≥0.3; net_edge_bps −9.24; cost gate fails |
| H-027 CO-1 | `tools/co1_commodity_inventory_surprise_research.py` | **REJECTED** | 0/0 windows reach eff≥0.3 (seasonal_proxy consensus too sparse); net_edge_bps −13.66 |
| H-028 E-1 | `tools/e1_insider_cluster_buy_research.py` | **REJECTED / UNTESTED-data-gap** | free SEC EDGAR Form-4 dense code-P cluster tape unavailable → synthetic fallback; harness 0/10 windows, net_edge_bps −17.47 |

`reports/hypothesis_registry.json` H-026/H-027/H-028 updated: status UNTESTED →
REJECTED, result recorded.

**Action item resolution:** the "wire ET-1/CO-1/E-1 into `passes_active_gate`"
item is **closed — do NOT wire**. All three fail the admissibility harness.
E-1 specifically could not be genuinely tested (no free dense Form-4 code-P
cluster feed); it would need a paid insider-data source to evaluate, which is
out of scope for the harness-gated free-data sidecar model.
