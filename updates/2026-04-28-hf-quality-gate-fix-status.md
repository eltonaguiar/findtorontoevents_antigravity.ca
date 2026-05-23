# 2026-04-28 — HF Quality Gate test fixture fix + sports playwright favicon

## Status

- **Branch:** `fix/hf-quality-gate-wire-2026-04-28` (cut from `origin/main`, in `.worktrees/fix-hf-quality-gate-2026-04-28/`)
- **Tests:** 49/49 passing locally on the two files touched (`tests/test_hf_quality_gate_wire.py`, `tests/test_quality_gates.py`)
- **PR:** not yet opened

## Why this fix exists

CI Tests workflow on `main` had been failing every run. Cursor proposed a fix in the local `audit-improvements-2026-04-28` workspace that **rewrote the test contract** with weaker assertions (inverted booleans, dropped reason-string checks, added soft-fail escape hatches). On review:

- The test file `tests/test_hf_quality_gate_wire.py` already exists on `origin/main` (added by PR #471). Cursor's "new" file was a parallel rewrite, not an addition.
- The on-main test was failing 4/6 against on-main code on this branch (which has the HF wire-up *deleted*) and 2/6 against `origin/main` proper (where the wire-up is present).
- Cursor's solution would have shipped green CI but masked the real signal that the test was broken.

## Root cause

The on-main `_pick()` fixture in `tests/test_hf_quality_gate_wire.py` does not construct a pick that survives `passes_active_gate`'s score-penalty pass:

1. **Missing `ml_score` field** → triggers `null_ml_solo_source` -20 score penalty.
2. **`datetime.now(timezone.utc)` timestamp** → varies by test-run hour, exposing time-of-day penalties (`dead_zone_morning` -8, `dead_zone_us_close` -15, `dead_zone_evening` -6) and freshness penalties (`crypto_very_stale` -35).
3. **No forward-validation fields** → score floor (`SMART_PICKS_MIN_SCORE = 60`, raised from 50 on 2026-04-21) cannot be bypassed.

With `confidence=0.65, score=70`, `passes_active_gate` mutates `pick["score"]` to **59** via `_apply_score_penalties`. `passes_smart_gate` then rejects at line 4218 (score floor) **before** the HF wire-up at line 4349 ever runs. Hence the on-main assertions about HF reasons populating fail — HF never executes.

The HF wire-up itself works correctly. Verified directly:
- `passes_hedge_fund_gate({...confidence: 0.65...})` returns `(False, "HF_GATE: CRYPTO confidence 0.650 in dead band [0.60,0.70) (PF 0.69 on n=882)")` ✓
- `passes_hedge_fund_gate({...symbol: 'DOGEUSDT'...})` returns `(False, "HF_GATE: CRYPTO banned symbol DOGEUSDT (lifetime PF < 0.50 on n>=52)")` ✓

## What this PR changes

### `tests/test_hf_quality_gate_wire.py`
1. Replace `datetime.now(timezone.utc).isoformat()` with a `_safe_timestamp()` helper that anchors to the most-recent 22:00 UTC (the empirically-best window per the `dead_zone_evening` comment table). Stable across CI runs.
2. Add `ml_score: 0.72` to the fixture (avoids -20 `null_ml_solo_source` penalty).
3. Add `forward_trades: 30, forward_wr: 0.55` (and the legacy `strat_fwd_*` aliases) so `_forward_bypass` clears the score floor regardless of penalty stacking. The tests now actually exercise the HF wire-up rather than the active-gate score path.

All 6 tests now pass against unchanged on-main `audit_trail/quality_gates.py`.

### `tests/sports_betting_js_errors.spec.js`
Add a `page.route('**/favicon.ico', ...)` fulfillment that returns 204 for the missing favicon. Suppresses the recurring `Failed to load resource: the server responded with a status of 404 ()` console error at the network layer.

The local Cursor-workspace version of this file added a **broad string filter** that would have matched ANY 404 console error, not just favicon. That's deliberately omitted here — real backend 404s get caught explicitly via the existing `apiFailures` listener on the `response` event, so favicon is the only intended suppression.

## What is intentionally not in this PR

- **No changes to `audit_trail/quality_gates.py`.** The implementation is correct; the test fixture was wrong.
- **No changes to `alpha_engine/hedge_fund_quality_gate.py`.** The HF gate's dead-band logic and symbol blocklist work as designed.
- **No changes to the `audit-improvements-2026-04-28` branch** (where peer w03yqel9 has 19 unique commits including UEPS work). That branch is 951 commits behind main and has its own HF wire-up state (deleted); merging is out of scope here.

## Coordination notes

- **PR #478** (`feat/goal1-wave2-strict-gate-2026-04-28`, peer ee95rosa) adds a new opt-in gate (`HF_AUDIT_SMART_STRICT`) **after** the existing HF wire-up at the bottom of `passes_smart_gate`. Purely additive in `quality_gates.py`. Modifies different test files. No conflict.
- **Peer w03yqel9** holds the `audit-improvements-2026-04-28` UEPS branch with the deleted HF wire-up. After this PR lands on main, w03yqel9 should restore the wire-up before merging UEPS work back, or accept that HF strict mode won't fire on that branch.
- **Peer fd0uag0p** owns the Goal #1 PR queue (#462–#472). This fix is unrelated to those PRs.

## Next steps

1. Push `fix/hf-quality-gate-wire-2026-04-28`.
2. Open PR against `main` titled "fix(test): make HF wire-up fixture survive active-gate penalty pass".
3. Watch CI Tests turn green on the new run.
4. Notify peers via `claude-peers` send_message with this MD link.

## Files

- `tests/test_hf_quality_gate_wire.py` — fixture rewrite
- `tests/sports_betting_js_errors.spec.js` — favicon route
- `updates/2026-04-28-hf-quality-gate-fix-status.md` — this doc

## Reproducer

```bash
cd .worktrees/fix-hf-quality-gate-2026-04-28
python -m pytest tests/test_hf_quality_gate_wire.py tests/test_quality_gates.py -v
# 49 passed
node --check tests/sports_betting_js_errors.spec.js
# clean
```
