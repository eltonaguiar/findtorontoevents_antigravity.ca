# Red-Team Review: PR #271 Shadow-Pilot Persona Registrations

**Date:** 2026-05-31
**Reviewer:** Claude Opus 4.7 (tick27 red-team)
**Target PR:** #271 — `feat(personas): shadow-pilot personas for INSUFFICIENT_N classes (4 variants)`
**State:** MERGED 2026-05-31T20:31:03Z
**Verdict:** **VERIFIED (with one noted gap)**

---

## Method

Following the discipline that every "registered=N" claim gets verified, this red-team:
1. Confirmed each persona file exists post-merge.
2. Validated JSON parses cleanly.
3. Compared schema to PR #219 (the actual upstream schema reference — PR body says "skyrocket pattern PR #228" but #228 only ships JS/Python, no persona JSONs; #219 is the persona JSON schema source).
4. Grepped each `wraps_strategy` value against `alpha_engine/` + `tools/` Python code.
5. Verified `shadow_pilot_until = 2026-06-30` math (= 2026-05-31 + 30 days).
6. Spot-checked one persona's content (`bond_connors_rsi2`) for field plausibility.

---

## Per-Persona Verdict

| Persona | File exists | JSON valid | Schema match | Strategy in code | Verdict |
|---|---|---|---|---|---|
| `strategy_persona__bond_connors_rsi2.json` | YES | YES | YES (+3 shadow fields) | YES — `bond_scanner.py`, `bond_strategies.py`, `non_crypto_policy.py` | VERIFIED |
| `strategy_persona__etf_faber_tactical.json` | YES | YES | YES (+3 shadow fields) | YES — `etf_scanner.py`, `etf_strategies.py`, `non_crypto_policy.py` | VERIFIED |
| `strategy_persona__memecoin_social_velocity.json` | YES | YES | YES (+3 shadow fields) | **NO** — 0 hits in alpha_engine/tools | GREENFIELD (self-disclosed) |
| `strategy_persona__penny_deep_oversold.json` | YES | YES | YES (+blocking_dependency, +emission_blocked) | YES — `production_scanner.py`, `strategy_block_expiry_audit.py` | VERIFIED (GATE-0 blocked, status correctly reflects) |

**Strategies grep-found in code: 3/4**

---

## Schema Match Analysis vs PR #219 Baseline

PR #219 baseline keys (e.g., `crypto_trust7_promoter`): 21 keys.

PR #271 personas add 3-5 new keys consistently:
- `status` (replaces implicit "shadow_paper_only" boolean)
- `shadow_pilot_until` (ISO date `2026-06-30`)
- `shadow_pilot_acceptance_criteria_2026_06_30`
- `references` (3 personas have this; PR #219 personas don't)
- `asset_symbol_whitelist` (bond + etf only; reasonable scoping)

PENNY persona adds 2 extra honest-disclosure fields:
- `blocking_dependency`
- `emission_blocked_pending_dependency`

All 4 carry the mandatory triad correctly:
- `requires_operator_promotion_to_live: true` (4/4)
- `shadow_pilot_until: "2026-06-30"` (4/4)
- `status`: `"shadow_paper_only"` (3/4) or `"shadow_paper_only_BLOCKED_AT_GATE_0"` (penny — accurately reflects blocked state)

**Date math:** `(2026-06-30 − 2026-05-31).days == 30` ✓

---

## Per-Strategy Grep Evidence

```
=== bond_connors_rsi2 ===
alpha_engine/bond_scanner.py
alpha_engine/non_crypto_policy.py
alpha_engine/bond_strategies.py

=== etf_faber_tactical ===
alpha_engine/etf_scanner.py
alpha_engine/etf_strategies.py
alpha_engine/non_crypto_policy.py

=== memecoin_social_velocity ===
(zero hits — greenfield)

=== penny_deep_oversold ===
alpha_engine/production_scanner.py
tools/research/strategy_block_expiry_audit.py
tools/audit_pick_funnel/seed_incidents_enhancements.py
```

---

## Memecoin Greenfield Disclosure Check

The `memecoin_social_velocity` strategy has **zero implementation in code**. However, the persona is **not fabricated** because it openly self-discloses:

```json
"kill_registry_check": "PASSED — memecoin_social_velocity not in any kill list (greenfield strategy)."
```

`shadow_paper_only` status + `requires_operator_promotion_to_live: true` + greenfield disclosure = honest pre-registration of a strategy that needs to be implemented before any emission. This is exactly the pre-registration intent of the persona registry, not a fabricated "this works" claim.

**Recommendation:** Add a follow-up incident or PR to either (a) implement `memecoin_social_velocity` scanner stub or (b) add `emission_blocked_pending_dependency: "scanner_not_implemented"` to mirror the penny pattern, so it cannot accidentally emit before code lands.

---

## Spot-Check: bond_connors_rsi2

Content review:
- **Symbol whitelist:** `{TLT, IEF, AGG, LQD, HYG}` — real US bond ETF tickers.
- **Entry:** `RSI(2) < 10`, `Close > 200-day SMA`, `MOVE index < 130`, FOMC blackout T-2 to T+1.
- **Exit:** `Close > 5-day SMA` (canonical Connors exit), 10-day time-stop, 2x ATR stop.
- **References:** `reports/peer_claude-skyrocket-recommendation_2026-05-31.md` ✓ exists, `reports/deep_dive_BOND_2026-05-31.md` ✓ exists.

All field semantics match real Larry Connors RSI(2) mean-reversion strategy literature. Asset class scoping is coherent (BOND on bond ETFs, not equities). Constraint logic references real data fields (RSI, SMA, MOVE index, ATR).

---

## Overall Verdict: VERIFIED

- 4/4 persona files exist with valid JSON.
- 4/4 schemas match PR #219 baseline + add documented shadow-pilot fields consistently.
- 3/4 strategies have prior code implementations grep-confirmed.
- 1/4 (`memecoin_social_velocity`) is greenfield but **openly self-disclosed** — pre-registration of a not-yet-implemented strategy, not fabrication.
- Date math correct, status fields correct, operator-promotion gate correct.
- No invented strategy names; the greenfield case is honest.

**Action:** Mark PR #271 as **trusted** in operator TL;DR. Single follow-up: add emission-block on `memecoin_social_velocity` so it can't fire before the scanner is implemented.

---

## Comparison vs PR #232 / #235 (revoked fabrications)

PR #232 / #235 invented strategy names with no code AND no greenfield disclosure — the personas implied live-ready coverage. PR #271 is qualitatively different: the one greenfield strategy is **explicitly flagged** as greenfield in its own kill-registry check, and the penny case **explicitly flags** Gate-0 blocking. The pattern is operator-honest pre-registration, not fabrication.

No revoke or correction PR required.
