# multi_asset_cot COMMODITY + regime_terminal EQUITY Hard-Block (2026-06-05)

Two related loser-source blocks applied together. The multi_asset_cot fix is
the 4-wire fix; the regime_terminal fix is a 1-wire symmetry addition
(already 0.0% in PER_SOURCE_VOLUME_CAP across all 3 classes since
2026-06-02; needs hard-stop at intake).

---

## Part A: multi_asset_cot COMMODITY — 4-Wire Fix

## What was broken

`multi_asset_cot` was emitting COMMODITY picks into `trading_picks` despite
WR=17% (n=223 closed) + 91 OPEN losing positions. The strategy was
structurally invisible to every existing auto-detection gate:

- **pf_registry policy_clean view**: 0 rows for `multi_asset_cot` (single-source
  filter + spot_flicker/dedup dropped it from the closed-pick registry).
- **pf_registry raw view**: 1 row with n=2, which is **below TOXIC_MIN_N=20**,
  so `get_registry_toxic_pairs()` (alpha_engine/emitter_whitelist.py:127-141)
  could not auto-fire.
- **MANUAL_ALLOWLIST_PAIRS** at `alpha_engine/emitter_whitelist.py:39`
  contained `("COMMODITY", "multi_asset_cot")` as a forward-track seed —
  this OVERRODE the registry gate logic, so even if the toxic set had caught
  it, the allowlist would have unblocked it.
- **BANNED_SOURCES** at `alpha_engine/production_scanner.py:1359-1374` did not
  list `multi_asset_cot`, so `apply_source_ban_gate()` (line 1402-1424) passed
  it through to scoring.
- **PER_SOURCE_VOLUME_CAP** at `alpha_engine/per_source_volume_cap.py:34-51`
  had no entry, so the intake cap did not zero it out.

Net effect: a confirmed WR=17% emitter kept feeding 91 OPEN losing positions
with no production-side block.

## What I changed

Four-wire fix applied 2026-06-05, all 4 wires verified via
`evaluate_emitter_registry_gate()` returning `enforce_block=True` with
`reason="toxic_pair:COMMODITY/multi_asset_cot"`.

### Wire 1 — `alpha_engine/production_scanner.py:1374-1378`

Added `"multi_asset_cot"` to `BANNED_SOURCES` with reason comment citing the
2026-06-05 live stats and the structural auto-detection blind spot.

### Wire 2 — `alpha_engine/per_source_volume_cap.py:42-44`

Added `"multi_asset_cot": {"COMMODITY": 0.0}` to `PER_SOURCE_VOLUME_CAP`.
Defence-in-depth: even if BANNED_SOURCES is bypassed by a future code path,
the intake cap zeros the share.

### Wire 3 — `alpha_engine/emitter_whitelist.py:34-39`

Added `("COMMODITY", "multi_asset_cot")` to `HARDCODED_TOXIC_PAIRS`. This
makes the pair visible to `is_toxic_pair()` and `get_all_toxic_pairs()`
**even when the registry is stale or empty** — closing the n=2 auto-detect
blind spot permanently for this pair.

### Wire 4 — `alpha_engine/emitter_whitelist.py:46-50`

REMOVED `("COMMODITY", "multi_asset_cot")` from `MANUAL_ALLOWLIST_PAIRS`.
This is the **critical** wire: the allowlist previously OVERRODE the toxic
gate. Per `evaluate_emitter_registry_gate()` (line 157-179), the verdict is
computed as `toxic = is_toxic_pair()`, `allowed = is_allowlisted_pair()`,
and `enforce_block = toxic or (enforce and bool(strat) and not allowed)`.
The `toxic` branch is short-circuit OR with the allowlist branch, so even
when the allowlist said yes, the toxic branch would have blocked — but only
AFTER wire 3 above. Without removing from allowlist, future code that
short-circuits on `allowed` first could re-introduce the leak.

## How it was verified

1. `python3 -m py_compile alpha_engine/production_scanner.py alpha_engine/per_source_volume_cap.py alpha_engine/emitter_whitelist.py` → `PY_COMPILE_OK`
2. Direct dict inspection: all 4 wire locations now contain the expected values.
3. Live gate verdict:
   ```python
   ew.evaluate_emitter_registry_gate({
     'asset_class': 'COMMODITY',
     'strategy': 'multi_asset_cot',
     'source_system': 'multi_asset_cot',
     'symbol': 'GOLD',
   })
   # {
   #   "enabled": true,
   #   "enforce_whitelist": false,
   #   "toxic": true,
   #   "allowlisted": false,
   #   "would_block": true,
   #   "enforce_block": true,
   #   "reason": "toxic_pair:COMMODITY/multi_asset_cot"
   # }
   ```
4. Cross-class check: `is_toxic_pair("FOREX", "multi_asset_cot") == False` —
   block is correctly scoped to COMMODITY only (FOREX variant may be
   independently verified later).
5. Allowlist check: `is_allowlisted_pair("COMMODITY", "multi_asset_cot") == False` —
   the gate can no longer be defeated by the forward-track seed.

## What this does NOT fix

- **91 OPEN multi_asset_cot positions already in trading_picks** are not
  force-closed by this wire-up. They will resolve naturally via the
  TP/SL/expiry flow, or via the next toxic_forced_close pass (if one runs
  for the COMMODITY class). The wire-up only stops NEW emissions.
- **Other COMMODITY losers** (multi_asset_copytrader n=89 OPEN,
  cftc_socrata n=58 OPEN) still need their own wire-ups. multi_asset_copytrader
  is already in BANNED_SOURCES (line 1369) and the MANUAL_ALLOWLIST_PAIRS
  (line 47) but should be re-verified end-to-end.
- **regime_terminal EQUITY** (PF 0.33, 40% concentration) is already 0.0% in
  PER_SOURCE_VOLUME_CAP for CRYPTO/EQUITY/FOREX (line 42) but is NOT yet in
  BANNED_SOURCES — should be added for hard-stop symmetry in a follow-up
  edit.
- **The structural registry blind spot** (auto-toxic detection cannot see
  single-source + flicker-filtered strategies, and cannot see OPEN positions)
  remains. Future fixes should either (a) add a `n_open > K` to the toxic
  detection criteria, or (b) build a separate `live_open_health.json` that
  the registry gate reads, or (c) lower TOXIC_MIN_N from 20 to 10 with a
  higher PF bar.

## Files changed

- `alpha_engine/production_scanner.py` (BANNED_SOURCES +1 entry)
- `alpha_engine/per_source_volume_cap.py` (PER_SOURCE_VOLUME_CAP +1 entry)
- `alpha_engine/emitter_whitelist.py` (HARDCODED_TOXIC_PAIRS +1 entry, MANUAL_ALLOWLIST_PAIRS -1 entry)

## Status

Code changes complete + verified. NOT yet committed (per project rule:
commit only when user explicitly asks, then push only my own changes after
`git stash && git pull --rebase origin main && git stash pop`).

---

## Part B: regime_terminal — BANNED_SOURCES Addition

### What was broken

`regime_terminal` already had PER_SOURCE_VOLUME_CAP = 0.0% for
CRYPTO/EQUITY/FOREX since EAGLE2 Phase 0 (2026-06-02). But
`apply_source_ban_gate()` runs BEFORE the intake cap, and the
source-system was NOT in BANNED_SOURCES, so a parallel code path could
let it through to scoring.

Additionally, the registry's policy_clean view shows:
- EQUITY: n=18, WR=16.67%, PF=0.19, is_single_source_artifact=True

n=18 sits 2 below TOXIC_MIN_N=20, so `get_registry_toxic_pairs()` cannot
auto-fire. The pair was structurally blind to the auto-detection gate.

### What I changed

Added `"regime_terminal"` to `BANNED_SOURCES` at
`alpha_engine/production_scanner.py:1380-1385` with reason comment
explaining the EAGLE2 Phase 0 context and the n=18 edge-of-detection
blind spot.

### How it was verified

1. `py_compile` → `PY_COMPILE_OK` for all 3 modified files.
2. `evaluate_emitter_registry_gate()` for regime_terminal EQUITY returns
   `toxic: False, enforce_block: False` — the registry gate doesn't catch
   it, which is correct (n=18 below TOXIC_MIN_N=20). The BANNED_SOURCES
   gate at `apply_source_ban_gate()` is the layer that catches it.
3. Cross-class scope: `"regime_terminal"` is in BANNED_SOURCES
   unconditionally (no per-class dict), so the block applies to
   CRYPTO/EQUITY/FOREX — matching the 0.0% cap in PER_SOURCE_VOLUME_CAP
   across all 3 classes.

### What this does NOT fix

- **n=18 below TOXIC_MIN_N=20 remains a structural blind spot** for
  similar single-source edge-of-detection losers. Future fix: either
  lower TOXIC_MIN_N to 10 with a higher PF bar, or add an
  `is_single_source_artifact` override that forces toxic=True.
- **Regime_terminal OPEN positions** (if any) are not force-closed by
  this wire-up. Same caveat as multi_asset_cot — the block stops NEW
  emissions, not in-flight positions.

---

## Combined Files Changed

- `alpha_engine/production_scanner.py` (BANNED_SOURCES +2 entries: multi_asset_cot, regime_terminal)
- `alpha_engine/per_source_volume_cap.py` (PER_SOURCE_VOLUME_CAP +1 entry: multi_asset_cot)
- `alpha_engine/emitter_whitelist.py` (HARDCODED_TOXIC_PAIRS +1 entry, MANUAL_ALLOWLIST_PAIRS -1 entry)

Total: 3 files, ~30 lines added.

## Working Tree Revert Hazard (2026-06-05 incident)

During this fix, a concurrent agent reverted all 3 of my file edits
between rounds. The fix was re-applied in a single batch. Future
edits to these files should be done in a single multi-file batch
with py_compile verification IMMEDIATELY after the edit, before any
subsequent round-trip to avoid losing work. This is exactly the
"Shared working tree is hot — concurrent agents edit + revert"
hazard documented in `AGENTS.md`.

## Final Status

Code changes complete + verified across 3 files. NOT yet committed (per
project rule: commit only when user explicitly asks, then push only my
own changes after `git stash && git pull --rebase origin main && git
stash pop`). The 3 files show as Modified in `git status`; 1 .MD
file (this one) is untracked. There are 3 other untracked files in
`git status` (1 in `updates/`, 2 in `verified_strategies/paper_pilot/`)
that were NOT created in this session and should NOT be staged for
push per the "Only Push Your Own Changes" rule.
