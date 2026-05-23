# Session AD Review — 2026-05-17

## Context
Continuation of autonomous trading-edge improvement session on findtorontoevents.ca/audit.
This session follows Sessions AA/AB/AC which shipped M-073/M-074 + new-strategies-scanner.

## Deliverables This Session

### 1. Session inventory and triage
- Verified all prior P0/P1 items from FOOLPROOF_ACTION_PLAN:
  - CRYPTO SL enforcement bug (SHORT stops not firing): ALREADY FIXED in Session V (outcome_resolver.py lines 1582-1585, direction-aware `>=` vs `<=`)
  - combined_confidence block: ALREADY DONE (quality_gates.py lines 1316 + 2547-2549)
  - EQUITY MIN_WR=0.52: ALREADY DONE (money_ready_verdict.py line 74)
  - pending_spa_scan wired: ALREADY DONE (dashboard_generator.py lines 49 + 16042-16043)
  - AB panel + zero-PnL nightly: ALREADY DONE (ab_analysis.yml)
  - COMMODITY survivorship bias warning: ALREADY DONE (template.html line 856)
  - PR #1132: MERGED (C1 paths B/C + D2 systems[] dedup)

### 2. MONEY READY tooltip correction
Fixed inconsistency in `audit_dashboard/template.html` line 1309:
- Before: "COMMODITY WATCH (PF=1.25 policy-clean, n=160, needs n≥100 confirmation)"
- After: "NOT_READY: COMMODITY (PF=1.25, WR=45.0% < 50% T2 floor, n=160 policy-clean — DXY booster active)"
The banner at line 899 already said NOT_READY; now the MONEY READY button tooltip is consistent.

### 3. CI/test health confirmed
- 4926 tests passing (4959 collected, 37 skipped, 4 xfail) locally
- All GH Actions in-progress (our M-074 commit triggered CI)

### 4. State review
- Sessions AA/AB/AC all swarm-APPROVED
- Session AC fixups applied (stale threshold 72h, min bar guard 25)
- DXY state: STRONG (99.27, +1.46% 5d) — COMMODITY LONG penalty active

## Remaining Blocked Items (not actionable without PA console)
- MySQL ghost-row purge (655k stale rows, target 2026-05-24)
- UEPS_ENABLE_PEAD=1 prod .env
- FRED_API_KEY GitHub secret
- connors_rsi2_scanner shadow (need n=20 resolved)
- OVERCONFIDENCE_DECAY A/B (need 30d tagged picks)

## Open Questions for Swarm Review

1. **DXY booster stale threshold**: We set 72h. On public holidays (e.g. US Memorial Day May 26, cron skips), the state could be 96h stale. Should we set a higher threshold (96h) or add a "max(last_fri_close, 72h)" logic?

2. **COMMODITY NOT_READY vs MONEY READY tooltip**: We've corrected the tooltip. Is there a risk the MONEY READY button still shows COMMODITY picks (since hc_filter.js might not filter by MONEY_READY verdict)? Should we add `asset_class != 'COMMODITY'` to the applyMoneyReady() filter function?

3. **DXY booster in score_booster.run_score_booster()**: The M-074 block iterates all `active_picks`. But `active_picks` at that point has already been filtered by `passes_active_gate()`. Are there any COMMODITY picks that would benefit from the DXY boost but are currently score=0 (blocked by gate) that the boost might rescue?

4. **Session cadence**: We've completed Sessions AA (M-073), AB (new-strat scanner), AC (M-074 DXY), AD (triage+tooltip). All swarm reviews APPROVE. Are there any remaining code-actionable items from the full session transcript that should be tackled before declaring the loop done?

5. **New strategies shadow period**: The `new-strategies-scanner.yml` runs daily but picks are shadow-mode only (no sizing) until 2026-05-31. Should we wire a "shadow performance tracker" to measure WR/PF of shadow picks vs gate, so we have data ready for the 2026-05-31 promotion decision?

## Output Format Required
Provide a JSON assessment:
- verdict: APPROVE, REQUEST_CHANGES, or NEEDS_DISCUSSION
- concerns: list of {severity, area, issue, recommendation}
- action_items: list of {priority, description, file, rationale}
- summary: one paragraph overall assessment
