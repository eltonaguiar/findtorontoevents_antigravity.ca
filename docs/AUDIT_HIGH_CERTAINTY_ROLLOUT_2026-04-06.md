# Audit High-Certainty Rollout

Date: 2026-04-06

## Purpose

Tighten the `/audit` Smart Picks surface so it behaves more like a tradable crypto shortlist and less like a broad idea feed with inflated conviction.

This rollout implements the narrowest live-code changes that match the latest closed-pick review:

- crypto Smart Picks now require real trust, not just a decent display score
- crypto SANDBOX strategies are excluded from Smart Picks
- `0.90+` confidence is treated as suspicious unless the pick is proven by trust or sample-backed forward edge
- consensus no longer earns a free bonus when the underlying edge is weak or low-trust
- Smart Pick summary counts are now computed from the final gated active list, not the raw pre-final pool

## Code Changes

### 1. Crypto tradability gate tightened

Updated [quality_gates.py](/e:/findtorontoevents_antigravity.ca/audit_trail/quality_gates.py):

- `passes_smart_gate()` now blocks crypto picks when:
  - strategy tier is `SANDBOX`
  - trust is unrated or below `trust_score >= 5`, unless `trust_tier == PROVEN`
  - confidence is `>= 0.90` without proven trust or strong sample-backed forward edge
  - consensus rows lack both trust and real forward edge

This keeps weak-but-loud crypto picks visible in Active when they clear active gates, while removing them from the premium Smart surface.

### 2. Smart ranking made less gullible

Updated [quality_gates.py](/e:/findtorontoevents_antigravity.ca/audit_trail/quality_gates.py):

- `calculate_smart_score()` now:
  - penalizes `0.90+` confidence unless the pick is proven
  - removes most positive consensus lift from low-trust or SANDBOX rows
  - adds negative consensus pressure for SANDBOX rows that would otherwise look “confirmed”

This shifts Smart ranking away from correlated model echo and toward trusted, sample-backed edge.

### 3. Dashboard summary count fixed

Updated [dashboard_generator.py](/e:/findtorontoevents_antigravity.ca/audit_trail/dashboard_generator.py):

- initial `summary.quality_stats.smart_picks_count` and percentage now use `final_active_picks`
- this avoids counting raw active rows that would never survive the final scored/gated pipeline

## Redis Bus Documentation

### New rollout topic

- `AUDIT_HIGH_CERTAINTY_ROLLOUT`

Publisher:

- [bus_post_audit_high_certainty_rollout.py](/e:/findtorontoevents_antigravity.ca/tools/bus_post_audit_high_certainty_rollout.py)

Changelog:

- [REDIS_BUS_CHANGELOG.md](/e:/findtorontoevents_antigravity.ca/docs/REDIS_BUS_CHANGELOG.md)

Schema note:

- [REDIS_BUS_SCHEMA.md](/e:/findtorontoevents_antigravity.ca/docs/REDIS_BUS_SCHEMA.md)

## Operational Intent

This is not a full hedge-fund stack rollout. It is a containment step.

The immediate goal is:

- fewer fake-high-conviction crypto picks
- lower Smart Pick count but higher average quality
- less promotion of unproven strategy families through consensus inflation

## Follow-Up Still Needed

1. Replay the new gate on closed picks and compare Smart cohort WR / PF before and after.
2. Add symbol/theme correlation caps so multiple BTC-beta names do not masquerade as diversification.
3. Split `/audit` presentation into `eligibility`, `edge score`, and `execution score` instead of one blended conviction number.
4. Replace legacy contradictory docs and heuristics that still argue for opposite routing logic.
