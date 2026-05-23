# Super-Swarm Analysis: findtorontoevents.ca/audit

You are one of 11 diverse AI engines reviewing the **prediction-edge audit dashboard** at https://findtorontoevents.ca/audit (and /audit/hyrotrader). Provide rigorous, evidence-cited analysis. Treat this as institutional-grade hedge-fund review.

## Context

The /audit page surfaces alpha-engine performance across 9 asset classes (EQUITY, CRYPTO B-tier, FOREX, COMMODITY, BOND, ETF, etc). Backing data: `audit_dashboard/data/dashboard_data.json` (`performance.asset_class_health`). Charter floors: T2 = PF>1.5 / WR>50 / MDD<20; T1 = PF>2 / WR>55 / MDD<10.

**Recent state (2026-05-03 post-resolver-v2 noise filter):**
- EQUITY: PF 1.41 / WR 52.7% / n=421 (T2-candidate)
- COMMODITY: PF 1.78 / WR 46.9% / n=750 (PF tier-2; lift WR)
- BOND: PF 1.72 / WR 55.6% / n=18 (n below floor)
- CRYPTO: PF 1.25 / WR 44.6% / n=8067 (drag from quan_engine 18% vol @ PF 0.70)
- ETF: PF 1.24 / WR 55.2% / n=87 (borderline, n→100)
- FOREX: PF 0.27 / WR 46.4% / n=1169 (sub-floor — mutate-before-kill protocol)

**Kimi golden finding to validate:** R:R band [1.5, 2.0] PF 5.81 vs >2.0 PF 0.35. Currently shadow-mode gate proposed.

## Your task

Produce a structured JSON envelope with these top-level keys:

```json
{
  "engine": "<your engine name>",
  "verdict_summary": "<2-3 sentence overall assessment of /audit>",
  "top_findings": [
    {
      "id": "AUDIT-XX",
      "severity": "critical|high|medium|low",
      "claim": "<specific, evidence-backable assertion>",
      "evidence": "<file path / data point / dashboard field>",
      "confidence": 0.0-1.0,
      "suggested_action": "<concrete patch direction>"
    }
  ],
  "edge_health_assessment": {
    "<asset_class>": {"verdict": "deploy|caution|halt|investigate", "reasoning": "..."}
  },
  "missing_features": ["<institutional-grade things /audit should show but doesn't>"],
  "data_integrity_concerns": ["<staleness, survivorship, look-ahead, etc>"],
  "questions_for_humans": ["<if you cannot determine X without more info>"]
}
```

## Rules

- Cite specific files/fields (e.g., `dashboard_data.json::performance.asset_class_health.EQUITY.pf`).
- Do NOT fabricate numbers. If you don't have access, say so under `questions_for_humans`.
- Each finding's `confidence` should reflect how strongly you'd defend it under cross-examination.
- Prefer fewer, well-evidenced findings over many speculative ones.
- Flag any methodology pitfalls (look-ahead bias, survivorship, p-hacking, regime concentration).

Output ONLY the JSON envelope. No prose preamble.
