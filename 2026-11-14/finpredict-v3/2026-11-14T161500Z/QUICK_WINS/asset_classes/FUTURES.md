# FUTURES — Quick-Win Fix Proposals

Verified 2026-11-14 (live payload). Micro-audit for the FUTURES asset class.

## Class Verdict

**DEAD** — the class is a placeholder, not a live book: 3 OPEN seeds, 0 closed ever, `_gate_passed=false`, trust LOW.

## Evidence

- Class has 3 OPEN rows, zero closed rows in history.
- `ES=F` seed carries bare date strings `"2026-11-14"` for `signal_time`/`entry_time` → UI renders "no date".
- `_gate_passed=false`, trust LOW — the seed is a stub, not a live position.

---

## Quick Wins

### QW-F1 — Gate placeholder display (don't render non-live seeds)
- **Problem:** The `ES=F` placeholder shows as an active pick despite `_gate_passed=false` and no real position.
- **Fix:** In the normalize/merge step, exclude rows where `_gate_passed=false` (or the source is a stub/placeholder) from the active panel until a real, gate-passed futures position exists.
- **Impact:** Medium / **Effort:** Low / **Risk:** Low.
- **Target file(s):** `audit_trail/dashboard_generator.py` (`_normalize_pick` / active-merge path). Verified.

### QW-F2 — Fix datetime serialization for bare-date seeds
- **Problem:** `"2026-11-14"` is not parseable by `_parse_timestamp` (ISO-only formats), so `signal_time`/`entry_time` resolve to None and the UI shows "no date".
- **Fix:** Teach `_parse_timestamp` to also accept `%Y-%m-%d` (midnight UTC) as a valid timestamp, OR have the seeding side emit a full `T...Z` ISO string.
- **Impact:** Medium / **Effort:** Low / **Risk:** Low.
- **Target file(s):** `audit_trail/universal_pick_resolver.py` (`_parse_timestamp` ~line 743). Verified. Seed emitter origin: **UNVERIFIED** (no single ES=F seed emitter located; `alpha_engine/futures_strategies.py` exists and emits proper ISO, so the stub likely originates elsewhere).

### QW-F3 — Exclude unproven class from metrics until a real position exists
- **Problem:** With n=3 OPEN / 0 closed and health insufficient, FUTURES stats are noise in class-level aggregates.
- **Fix:** Mark the class `UNPROVEN`/excluded in classification and roll-ups until a gate-passed, real futures position settles its first trade.
- **Impact:** Medium / **Effort:** Low / **Risk:** Low.
- **Target file(s):** `audit_trail/asset_classification.py` (`resolve_asset_class` ~line 556). Verified; class gating also touches `alpha_engine/config.py`.

---

## Notes
- Target files verified except the ES=F seed emitter origin (marked UNVERIFIED above).
- No price/entry garbage observed in FUTURES because the class carries no real positions yet.
