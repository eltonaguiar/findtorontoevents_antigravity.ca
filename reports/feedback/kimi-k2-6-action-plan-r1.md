The user wants me to review a draft action plan for a multi-asset hedge-fund-style alpha pipeline. I need to reply in 4 sections (A, B, C, D) with 300-500 words total. I need to be specific, cite item numbers from the sequence table, and not repeat the plan.

Key constraints from the system prompt:
- Wire-Up Rule: every new integration must have a production caller OR be opt-in with explicit wiring plan
- Default-OFF for any new gate or scoring change; 14-day shadow before flip-on
- Each PR ships small (1-3 files typical), with tests + per-PR doc
- safe_push.sh handles concurrency for auto-commit workflows

Let me analyze the plan:

Strengths:
- Verification-first approach (Wave 1 / Items 1) before writing new code
- Explicit risk ratings and gating (B5 gated on B4 soak, B13 on B12 soak)
- Small PRs with tests + docs
- Uses safe_push.sh
- Defers high-risk items (B5, B13) until soak complete
- Acknowledges degraded performance metrics and prioritizes EQUITY-REGRESS (Item 2)
- Separates blocked/operator-decision items (Wave 6)

Contradictions/Blockers/Missing Prerequisites:
- Wire-Up Rule violation: Item 10 (B9 TradingAgents wire-in) says "Ready to schedule for shadow-mode 14-day run in `long_term_pick_contract.py::emit_long_term_picks`" but does it have a production caller or explicit opt-in wiring plan? The plan mentions shadow mode but needs explicit wiring.
- Item 5 (B19 pair-level carve-out): This is a registry entry `(atr_percentile_gate, BTCUSDT, LONG)`. Is this a gate change? If so, Default-OFF requires 14-day shadow before flip-on. But the plan puts it at Order 5 without mentioning shadow/gating. The acceptance criteria wants PF 0.98→1.05 in 14 days, but B19 might need shadow time.
- Item 8 (FOREX-RESOLVER-2): This drops threshold 5.0 → 1.5. This is a scoring/gate change. It should be Default-OFF with 14-day shadow, but plan says "ship if Sharpe lift ≥ 0.5" without mentioning the mandatory 14-day shadow period.
- Item 12 (B5 Cursor Phase 3 scoring): HIGH risk. Plan says "gated on B4 soaking 48h post-merge". But the codebase constraints say "Default-OFF for any new gate or scoring change; 14-day shadow before flip-on". The plan mentions 48h soak for gating start, but B5 is a scoring change so it needs 14-day shadow, not just 48h. Also, B5 is HIGH risk but plan says "lands behind shadow flag for ≥48h" in risk controls — contradicts the 14-day shadow rule.
- Item 14/15 (B17/B18): Gated on B16 7d data, but B16 just merged. Plan says "can start once B16's daily artifact accrues 7+ days of data" — this is fine, but do these items respect the 14-day shadow for gating changes? B17 is "HC button after-cost gating" — that's a gate change, needs 14-day shadow.
- Item 3 (B6 Cursor Phase 5 UI filters): LOW risk UI. But it depends on concept_family field appearing on every pick (V6). If it's UI-only, maybe fine, but if it filters/scores picks, could affect production flow. Need to ensure it's read-only UI.
- Missing explicit Wire-Up plan for B9 (Item 10). Also B7 (