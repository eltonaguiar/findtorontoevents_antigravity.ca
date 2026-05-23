# High Conviction Picks Deep Analysis (2026-04-14)

## Scope
Requested tasks:
1. Pull latest code from GitHub.
2. Investigate why /audit high-conviction pick count is low.
3. Verify whether Claude-deployed fixes actually work.

## Git Sync Status
Repository was synced successfully via stash + rebase pull + stash pop.
- Branch after sync: feat/enhancements-high-conviction-hyrotrader-copytrader
- Remote main updated during pull: d558dafa -> d6f68ffe
- Local uncommitted files were restored without conflict.

## What Was Verified

### 1) Fixes are present in code and production
- HC filter includes PROBATION blacklist in embedded defaults: audit_dashboard/hc_filter.js
- Runtime config fetch exists and is wired in browser init: audit_dashboard/hc_filter.js
- Live file confirms same logic is deployed: https://findtorontoevents.ca/audit/hc_filter.js
- Live config file exists at /audit/config and includes PROBATION: https://findtorontoevents.ca/audit/config/hc_gate_params.json

### 2) Dashboard payload has many stamped HF tiers, but very few pass HC button filter
Using local payload mirror from audit_dashboard/data/dashboard_data.json:
- active total: 74
- picks with stamped hf_conviction_tier in S/A/B: 19
- picks passing passes_high_conviction_pick: 3
- picks passing strict overlay (button path): 3

This means tier stamping exists, but does not translate into final high-conviction visibility.

### 3) Gate-level rejection profile for stamped picks
For the 19 stamped S/A/B active picks:
- 10 fail Gate G3b forwardWRMinPct (forward WR < 45%)
- 5 fail score gates (G1/G1b)
- 2 pass
- 2 additional passes come from non-stamped path, yielding total 3 final HC picks

Top blocker is forward WR threshold, not missing tier stamping.

## Critical Mismatch: Fix Intent vs Runtime Behavior
PR notes claim tier path should restore conviction contract and even show examples like “Tier S pick should pass even if some gates fail.”

Actual runtime logic does not do that.

Current logic in both JS and Python mirror:
1. Try full hard gates.
2. If fail, try stamped tier supplemental path.
3. Supplemental path again calls evaluate gates (only optionally skipping independent consensus for S/A), so most hard-gate failures still fail.

Evidence:
- passesHighConvictionPick uses evaluateHcGates1to9 first, then passesStampedTierSupplementalPath: audit_dashboard/hc_filter.js
- passesStampedTierSupplementalPath still calls evaluateHcGates1to9: audit_dashboard/hc_filter.js
- Python mirror is identical: tools/dashboard_hc_rules.py

Direct runtime check:
- Tier-S sample with valid contract returns:
  - passesPerAssetTierContract = true
  - passesHighConvictionPick = false

So the documented expected behavior is currently false in implementation.

## Why the Count Is Low on /audit
Primary cause:
- High Conviction button path depends on hard gates, especially forward WR >= 45% and score floors.
- Most stamped S/A/B picks currently fail those same hard gates.

Secondary cause:
- New enhancement modules are mostly standalone and not integrated into the dashboard generator path that drives /audit counts.
- Example files exist but are not referenced by audit pipeline call sites:
  - alpha_engine/high_conviction_enhancements.py
  - alpha_engine/hyrotrader_enhanced_scoring.py
  - alpha_engine/copytrader_integration.py

Result:
- Deployed fixes improved alignment plumbing (PROBATION + config fetch + tier fields present)
- But they did not materially increase final HC eligible picks under current gate semantics.

## Verdict on Claude Fixes
- Alignment fixes: PASS
  - PROBATION blacklist parity: fixed
  - Browser config fetch: fixed and deployed
  - Tier stamping pipeline: present

- Outcome fix for low HC count: PARTIAL / EFFECTIVELY FAILING
  - Tier path currently does not rescue picks that fail major gates.
  - With current payload, final HC visible picks remain 3.

## Recommended Remediation
1. Decide intended policy explicitly:
   - Option A: Tier is advisory only (keep current strict gate behavior).
   - Option B: Tier is a true supplemental admission path (allow selected gate bypasses).

2. If Option B, implement targeted bypass contract:
   - For stamped S/A, allow bypass of G3b and/or G1b under strict constraints (trust tier, capped confidence, regime-safe, no failing WF).
   - Keep hard vetoes for blacklist trust tiers and explicit walk-forward FAILING.

3. Add parity tests for policy intent:
   - A Tier-S synthetic case that is expected to pass (or fail) by design.
   - Regression test that compares JS and Python mirror outputs on a fixed fixture set.

4. Expose gate-failure analytics in payload:
   - Per-pick fail reason field for HC (first failed gate).
   - Aggregate panel: counts by gate reason.

5. Integrate enhancement modules or remove from expected-outcome docs:
   - If hyrotrader/copytrader enhancements are expected to raise HC counts, they must feed the same fields used by HC gating in the dashboard pipeline.

## Evidence Artifacts Produced
- Parity output written to: audit_trail/data/dashboard_hc_parity_latest.json
- This report: HIGH_CONVICTION_DEEP_ANALYSIS_2026-04-14.md

## Notes
Live endpoint currently reports Unified Audit Dashboard v99.0 and shows active counts consistent with the local dashboard payload shape, supporting that this analysis reflects production behavior rather than a stale local-only artifact.
