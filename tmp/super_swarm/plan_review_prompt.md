# Critique this Unified Test + Integration Plan

You are reviewing a multi-stage implementation plan for findtorontoevents.ca. Surface any issues that would cause the plan to fail in execution. Be aggressive — this plan will ship code, so false positives now save real outages later.

## Read the plan

The plan is at `reports/unified_test_integration_plan_2026_05_04.md`. Read it fully before responding.

## Required output JSON

```json
{
  "engine": "<your engine name>",
  "verdict": "ship-as-is|ship-with-minor-revisions|major-revisions-needed|reject",
  "top_concerns": [
    {
      "id": "C-XX",
      "severity": "critical|high|medium|low",
      "section": "<which plan section>",
      "issue": "<what's wrong>",
      "suggested_fix": "<concrete change>",
      "confidence": 0.0-1.0
    }
  ],
  "missing_items": [
    "<P0/P1 item the plan should have but doesn't>"
  ],
  "ordering_critique": "<is the P0/P1/P2 ordering correct? What should move?>",
  "test_plan_critique": "<are the selectors, assertions, and console-error patterns sufficient?>",
  "rollback_critique": "<are rollback paths concrete and reversible?>",
  "risks_undocumented": [
    "<risks not mentioned in the plan>"
  ],
  "approval_for_round2": true|false
}
```

## Hard rules

- DO NOT propose changes that contradict the architecture anchors (vanilla JS only on host page; no PHP backend on 50webs static host; `THE_ODDS_API_KEY` env var name; Tailwind class chip detection).
- DO NOT recommend blanket CRYPTO halt (CLAUDE.md mutate-before-kill protocol).
- DO NOT propose adopting React `GearSettingsModal.tsx`.
- DO surface execution risks like CI flakiness, merge conflicts, mid-deploy outages.
- DO surface scope creep — anything in P0 that should be P1 or vice versa.

Output ONLY the JSON envelope.
