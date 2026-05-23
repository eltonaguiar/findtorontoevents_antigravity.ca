# Swarm review: PF/WR improvement plan per asset class

You are a quant-risk reviewer. Read the attached plan and the canonical ledger
numbers. Critique with **specific evidence**, do NOT praise.

## Inputs

1. **Plan under review:** `reports/PF_IMPROVEMENT_PER_CLASS_2026-05-19T2137Z.md`
2. **Canonical ledger:** `audit_dashboard/data/pf_registry.json` keys
   `by_asset_class_policy_clean_net` + `by_asset_class_strategy_policy_clean_net`
3. **Authoritative verdict context:** `reports/EDGE_VERDICT_2026-05-18.md` +
   `reports/EDGE_HUNT_EXHAUSTED_2026-05-18.md` (17 pre-registered causal
   hypotheses, 0 admissible under unmodified harness)
4. **Companion merged plan:** `reports/MERGED_ACTION_PLAN_2026-05-19.md`

## What we want from you

For each numbered section of the plan (CRYPTO C-1..C-7, FOREX F-1..F-5,
COMMODITY K-1..K-4, EQUITY E-1..E-3, FUTURES FU-1..FU-2, UNKNOWN U-1..U-3,
X-1..X-6 infra, end-state math, acceptance gate), score:

- **VERDICT:** AGREE / DISAGREE / NEEDS_EVIDENCE
- **EVIDENCE:** quote the specific canonical number or registry entry that
  supports or refutes the action
- **RISK:** what breaks if we ship this as-is

Specifically scrutinize:

1. **C-1/C-2 — kill `ensemble` CRYPTO.** Is n=79 / WR 5.1% / PF 0.01 / pnl −56pp
   evidence of a real drag, OR is this a single-symbol ghost like the
   historical MATIC artifact (`project_quan_engine_matic_positive_artifact.md`)?
   Recommend mutation/inverse before kill?
2. **F-1 — whitelist `cta_replicator` FOREX.** n=97 WR 64.9% PF 2.38 +0.11pnl
   — close to T2 density. But: has this passed `edge_stability_harness.py`?
   If not, is whitelisting it as "the only FOREX emitter" premature?
3. **C-5 — reject `ml_enhanced_*USDT_*` cohorts with 89-97% WR + n<50 as
   overfit.** Is the "single-symbol/timeframe" heuristic sufficient, or should
   we require harness clearance?
4. **End-state math claim:** "remove `ensemble` n=79 → CRYPTO PF 0.64 → ~1.4-1.7".
   Compute the actual canonical aggregate AFTER excluding `ensemble` rows. Show
   your work. Flag if my math is off.
5. **Convergence risk:** does this plan repeat the data-dredging trap by
   re-aggregating the SAME ledger after cuts? Or is it legitimate emitter
   hygiene?

## Output format (strict JSON)

```json
{
  "engine": "<your name>",
  "overall_verdict": "AGREE|MAJOR_REVISION|REJECT",
  "section_findings": [
    {"section": "C-1", "verdict": "AGREE|DISAGREE|NEEDS_EVIDENCE",
     "evidence": "...", "risk": "..."}
  ],
  "math_check_ensemble_exclusion": {
    "claimed": "CRYPTO PF 0.64 -> ~1.4-1.7",
    "actual_post_exclusion": "<your computed PF/pnl>",
    "verdict": "AGREE|DISAGREE",
    "evidence": "..."
  },
  "top_3_practical_lifts_per_class": {
    "CRYPTO": ["...","...","..."],
    "FOREX": ["...","...","..."],
    "COMMODITY": ["...","...","..."]
  },
  "missed_opportunities": ["..."],
  "must_not_ship": ["..."]
}
```

Be terse, specific, evidence-only. No filler.
