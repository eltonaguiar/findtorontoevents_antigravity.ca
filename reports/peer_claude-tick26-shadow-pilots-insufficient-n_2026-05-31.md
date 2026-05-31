# Tick26 — Shadow-Pilot Personas for INSUFFICIENT_N Classes

**Date:** 2026-05-31
**Author:** claude (peer review, tick #26)
**Trigger:** PR #267 surfaced 5 INSUFFICIENT_N classes (BOND, ETF, COMMODITY, FUTURES, PENNY/MEMECOIN). Need skyrocket-style shadow-pilot registrations to break the n-stasis without polluting production gates.
**Pattern:** Modeled on `reports/peer_claude-skyrocket-recommendation_2026-05-31.md` and existing PR #219 persona schema.

---

## Scope decisions

| Class | Action | Rationale |
|---|---|---|
| **BOND** | REGISTERED (`bond_connors_rsi2`) | INCIDENT_BONDS #1 surfaced Connors RSI(2) on bond ETFs; claimed 73% WR is unverified — shadow-pilot to forward-test. |
| **ETF** | REGISTERED (`etf_faber_tactical`) | INCIDENT_ETFS #1 + Ring consult identified Faber TAA as strongest academic backing. Existing `etf_scanner` is KILL-CANDIDATE (PF=0 on energy concentration). |
| **MEMECOIN** | REGISTERED (`memecoin_social_velocity`) | Per tick23 fresh-stats: meme n=1, WR=0%. Social-velocity is the canonical meme signal — shadow-pilot to measure. |
| **PENNY** | REGISTERED with GATE-0 BLOCK FLAG (`penny_deep_oversold`) | INCIDENT_PENNY #2 — pump_guard.py Gate 0 blocks all emission. Persona is symbolic until that fix lands. |
| **FUTURES** | **NOT REGISTERED** | RESEARCH_ONLY policy holds per 2026-05-31; futures_momentum was killed as P0 in PR #267 prelude. |
| **COMMODITY** | **NOT REGISTERED in this tick** | COMMODITY is FAIL+INSUFF-N but already has `strategy_persona__commodity_non_cot_research` (PR #219). No new candidate surfaced. |

Net: **4 new shadow-pilot personas registered.**

---

## Persona files

| Class | Persona file | Strategy | shadow_pilot_until |
|---|---|---|---|
| BOND | `config/personas/strategy_persona__bond_connors_rsi2.json` | `bond_connors_rsi2` | 2026-06-30 |
| ETF | `config/personas/strategy_persona__etf_faber_tactical.json` | `etf_faber_tactical` | 2026-06-30 |
| MEMECOIN | `config/personas/strategy_persona__memecoin_social_velocity.json` | `memecoin_social_velocity` | 2026-06-30 |
| PENNY | `config/personas/strategy_persona__penny_deep_oversold.json` | `penny_deep_oversold` | 2026-06-30 (window starts post-Gate-0-unblock) |

All four carry:
- `status: shadow_paper_only` (PENNY: `shadow_paper_only_BLOCKED_AT_GATE_0`)
- `shadow_paper_only: true`
- `requires_operator_promotion_to_live: true`
- `shadow_pilot_until: "2026-06-30"`

---

## 30-day acceptance criteria (uniform — T2-direction)

For every persona at the 2026-06-30 review tick:

| Outcome | Trigger |
|---|---|
| **Promote to next-stage paper** | PF >= 1.5 AND WR >= 50% AND n_closed >= 30 |
| **Retire** | PF < 0.9 AND n_closed >= 30 |
| **Extend pilot** | n_closed < 30 (likely outcome for slow-cadence classes like ETF-Faber + PENNY-blocked) |

Promotion still requires operator sign-off — `requires_operator_promotion_to_live=true` is enforced by the persona loader.

---

## Self-red-team checks

| Check | Result |
|---|---|
| Persona keys match existing PR #219 schema | PASS — all required keys present; new `status`, `shadow_pilot_until`, `shadow_pilot_acceptance_criteria_2026_06_30` added consistently across all 4 |
| `wraps_strategy` references real strategy names | PASS — none of the 4 wraps_strategy values appear in any PERMANENTLY_KILLED list; greenfield strategies surfaced from incident reports + deep-dives |
| No scoring-path code touched | PASS — diff is 4 JSON files + 1 markdown report |
| FUTURES correctly skipped | PASS — RESEARCH_ONLY policy honored |
| PENNY Gate-0 dependency flagged | PASS — `emission_blocked_pending_dependency: true` + explicit block flag in `status` |
| JSON validity | PASS — `python3 -c "import json; json.load(...)"` clean on all 4 |
| No fabricated function names | PASS — persona JSON is declarative config; no Python imports/calls embedded |
| No schema drift vs PR #219 | PASS — additive only (new fields), no field removals/renames |

---

## Operator TL;DR — Shadow pilots running (add to operator brief)

```
## Shadow pilots running (2026-05-31 → 2026-06-30)

| Class    | Strategy                  | n now | End date   | Notes                              |
|----------|---------------------------|-------|------------|------------------------------------|
| BOND     | bond_connors_rsi2         | 0     | 2026-06-30 | INCIDENT_BONDS #1; Connors RSI(2)  |
| ETF      | etf_faber_tactical        | 0     | 2026-06-30 | INCIDENT_ETFS #1; Faber TAA monthly|
| MEMECOIN | memecoin_social_velocity  | 1     | 2026-06-30 | tick23 INSUFF-N (n=1)              |
| PENNY    | penny_deep_oversold       | 0     | 2026-06-30 | BLOCKED at Gate 0 (pump_guard)     |
| (PRIOR)  | skyrocket_detector        | 0     | 2026-06-30 | PR #228 — penny VCP pattern        |

All persona-paper-only; no production gate exposure; operator-promotion required.
```

---

## References

- `reports/peer_claude-skyrocket-recommendation_2026-05-31.md` (canonical shadow-pilot pattern)
- `reports/peer_claude-tick23-per-class-fresh-stats_2026-05-31.md` (5 INSUFF-N classes)
- `reports/deep_dive_BOND_2026-05-31.md`
- `reports/deep_dive_ETF_2026-05-31.md`
- PR #219 (per-class persona schema)
- PR #228 (skyrocket shadow-pilot recommendation)
