# P0-1/P0-3 fixes: surface parity assertion + compounded drawdown

**Date:** 2026-11-23
**Worktree:** vanilla-handsaw (feat/coms-final-notes-2026-11-20)
**Author:** Kilo

## What was broken

Per the consolidated audit plan (`docs/AUDIT_SURFACES_CONSOLIDATED_PLAN_2026-11-20.md` §3.3):

- **P0-1:** No hard CI test enforced byte-identity of the two live ledger copies (`/audit3/audit3_ledger.json` vs `/audit/data/audit3_ledger.json`) or `status.json.stale == false`. A drift or stale publish would have gone undetected until a human noticed.
- **P0-3:** The tribunal (`alpha_engine/audit3_tribunal.py`) had **zero drawdown code**. F1 "arithmetic-sum drawdown" was a documented requirement but never implemented; any equity curve that went +50% then −50% would have reported 0% drawdown (wrong) instead of the compounded −25% net / 50% peak-to-trough (correct).

## What changed

### 1. P0-1 — `tools/assert_surface_parity.py` + test
- New script: byte-for-byte SHA-256 comparison of N ledger copies, `status.json.stale` gate, optional `audit2.js` `LEDGER_SERVED_FROM` disclosure check.
- New test: `tests/test_assert_surface_parity.py` (smoke: identical ledgers + fresh status → exit 0).
- 1 test added, passes.

### 2. P0-3 — F1 compounded drawdown
- Added `compounded_max_drawdown(nets_pct)` helper that builds equity multiplicatively (`equity *= 1 + r/100`) and returns the worst peak-to-trough loss as a positive percent.
- Wired into `evaluate_cell`: `max_drawdown_pct` now appears on every cell (None when n=0).
- 4 new deterministic tests in `tests/test_audit3_tribunal.py`:
  - `+50%, −50% → 50%` (geometric, not arithmetic 0%).
  - Monotone winner → 0.0.
  - Empty → None.
  - `evaluate_cell` reports the key.
- All 38 tribunal tests still pass (34 pre-existing + 4 new).

### 3. P1-4 / P0-2 already satisfied
- `tools/pod_emission_audit.py --strict` and its 4 tests already existed and pass.
- `audit3_verdict_history.json` has exactly one `--history-write` site (`audit3-ledger.yml:201`); deploy pipeline only consumes.

## Verification

```bash
python3 -m pytest tests/test_audit3_tribunal.py tests/test_assert_surface_parity.py \
                  tests/test_pod_emission_audit.py tests/test_audit3_cli_smoke.py \
                  tests/test_audit3_ledger_e2e.py -q
# 48 passed
```

Lint/typecheck not applicable (Python, no mypy in this repo for these modules).

## Commits

- `7439a6c` — coms artifacts (9 files)
- `b80ccea` — P0-1 parity tool + test
- `ca011db` — P0-3 drawdown helper + 4 tests

## Next (unchanged from plan)

P1-5 (H-119 benchmark coverage 0.798) and P2-7 (FX backfill) remain DB-credential blocked; operator action required.

*Nothing here is investment advice. 0 PROVEN / 0 CANDIDATE on the live ledger.*
