# Tick29 — Orphan Persona Fix (PR #271 follow-up)

**Date:** 2026-05-31
**Author:** Claude Opus 4.7 (tick29)
**Source red-team:** `reports/peer_claude-tick27-pr271-red-team_2026-05-31.md`
**Target persona:** `config/personas/strategy_persona__memecoin_social_velocity.json`

---

## 1. Orphan Persona Identified

Per tick27 red-team table:

| Persona | Strategy grep in code |
|---|---|
| `bond_connors_rsi2` | YES (bond_scanner, bond_strategies, non_crypto_policy) |
| `etf_faber_tactical` | YES (etf_scanner, etf_strategies, non_crypto_policy) |
| `memecoin_social_velocity` | **NO — 0 hits (greenfield)** |
| `penny_deep_oversold` | YES (production_scanner, strategy_block_expiry_audit) |

Orphan = **`memecoin_social_velocity`** (registered in PR #271 with `wraps_strategy: "memecoin_social_velocity"` and `asset_class: "MEMECOIN"`, but no MEMECOIN-class scanner exists).

## 2. Verbatim grep (tick29 re-verification)

Command:

```
grep -rln "memecoin_social_velocity\|social_velocity" alpha_engine/ tools/ multi_asset/ --include="*.py"
```

Result:

```
alpha_engine/equity_strategies.py
alpha_engine/scanner.py
alpha_engine/config.py
alpha_engine/non_crypto_quality_gate.py
```

Narrow grep for the exact persona-claimed name:

```
grep -rln "memecoin_social_velocity" alpha_engine/ tools/ multi_asset/ --include="*.py"
```

Result: **0 hits.**

The four files above all match the substring `social_velocity` via a DIFFERENT function name: `meme_social_velocity` (EQUITY class, alpha_engine/equity_strategies.py:238). That function:

- Iterates `EQUITY_SYMBOLS` filtered by `cat=="meme"` (equity meme tickers like GME/AMC, NOT crypto DOGE/SHIB).
- Returns signals with `"strategy": "meme_social_velocity"` — does NOT match the persona's `wraps_strategy: "memecoin_social_velocity"`.
- Is gated by `equity_macro_gate` + VIX — crypto-irrelevant gates.

**Conclusion:** the persona's `wraps_strategy` is a genuinely orphan crypto-side name. The lexically-similar EQUITY function is NOT a valid wraps target — it operates on the wrong asset class with the wrong gates.

## 3. Decision: PENDING_IMPLEMENTATION (not REMOVE)

**Rationale for keeping the persona as a placeholder:**

1. **Pre-registration intent is valid.** Tick23 fresh-stats show MEMECOIN at n=1 INSUFF-N stasis. The persona registry's whole purpose is *pre-registration* (rule M-107) — registering a candidate strategy before any backtest. Removing it would lose the pre-registration record and let a future agent silently re-invent it.
2. **Honest self-disclosure was already in place.** PR #271's `kill_registry_check` field openly stated "greenfield strategy." Tick27 red-team flagged it but did NOT recommend removal — it recommended *adding emission-block fields* mirroring the penny pattern.
3. **An operator plan exists** (`reports/asset_class_90day_plan_PENNY_MEME_2026-05-15.md`) that explicitly governs MEMECOIN — but the policy is **full quarantine / 0% allocation / research-only**. So even with a future scanner, emission requires a separate operator policy change. Keeping the persona as PENDING reflects that two-step gate honestly.
4. **The penny pattern is a proven template** for "registered but blocked-pending-dependency" — already shipped, already reviewed (tick27 verified it).

**Action applied:**

Edited `config/personas/strategy_persona__memecoin_social_velocity.json`:

- `status`: `"shadow_paper_only"` → `"shadow_paper_only_PENDING_IMPLEMENTATION"`
- Added `"requires_implementation": true`
- Added `"emission_blocked_pending_dependency": true`
- Added `"blocking_dependency": "..."` — describes the missing crypto scanner, calls out the lexically-similar but functionally-distinct `meme_social_velocity` EQUITY function, references the 2026-05-15 MEMECOIN quarantine policy gate.
- Updated `kill_registry_check` to clarify that emission is blocked via the new fields, not via the kill registry (which would falsely imply a kill list entry).
- Display name suffix changed from `(SHADOW PILOT, n<30)` to `(SHADOW PILOT, PENDING_IMPLEMENTATION)`.

**Schema parity with penny persona (PR #271 verified pattern):**

| Field | Penny persona | Memecoin persona (post-fix) |
|---|---|---|
| `status` | `shadow_paper_only_BLOCKED_AT_GATE_0` | `shadow_paper_only_PENDING_IMPLEMENTATION` |
| `emission_blocked_pending_dependency` | true | true |
| `blocking_dependency` | "INCIDENT_PENNY #2 — Gate 0 ..." | "No scanner implementation exists ..." |
| `requires_operator_promotion_to_live` | true | true |
| `shadow_pilot_until` | 2026-06-30 | 2026-06-30 |

JSON validation:

```
$ python3 -c "import json; json.load(open(...))" → VALID, 28 keys
```

## 4. Files Changed

- `config/personas/strategy_persona__memecoin_social_velocity.json` (5 lines added, 3 modified — within 2-file admin-merge scope)
- `reports/peer_claude-tick29-orphan-persona-fix_2026-05-31.md` (this file)

## 5. Self-red-team

- [x] Grep re-verified — 0 hits for exact `memecoin_social_velocity`.
- [x] EQUITY `meme_social_velocity` confirmed NOT a valid wraps target (different asset class, different gates).
- [x] JSON parses cleanly post-edit.
- [x] Schema mirrors the penny placeholder pattern (which tick27 verified).
- [x] No new strategy fabrication — the placeholder explicitly says "no implementation exists."
- [x] Emission is now physically blocked via `emission_blocked_pending_dependency: true` (consumer code that reads this flag will skip emission, same as penny).
- [x] Operator policy gate referenced (`asset_class_90day_plan_PENNY_MEME_2026-05-15.md`) so a future implementor sees the quarantine policy before greenlighting emission.

## 6. Follow-ups (not in this PR)

- Verify consumer code (persona registry loader) honors `emission_blocked_pending_dependency` for both PENNY and MEMECOIN — should be uniform.
- If/when MEMECOIN quarantine policy is relaxed, the 30-day shadow-pilot clock should be reset from the unblock date, NOT from 2026-05-31. The persona's `blocking_dependency` text says this explicitly.
