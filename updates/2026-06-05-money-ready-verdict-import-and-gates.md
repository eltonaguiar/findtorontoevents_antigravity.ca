# Money-ready verdict import fix + gate refresh — 2026-06-05

## What was broken

- `python alpha_engine/money_ready_verdict.py --json` failed with `ModuleNotFoundError: No module named 'alpha_engine'` when invoked as a script (GHA `tools/money_ready_snapshot.py` and local cron).
- Root cause: `from alpha_engine.eagle_gates` ran **before** `sys.path` inserted the repo root.

## What changed

1. **`alpha_engine/money_ready_verdict.py`**
   - Move `REPO_ROOT` + `sys.path` bootstrap above all `alpha_engine.*` imports.
   - `_resolved()`: drop sign-incoherent rows (WON with pnl≤0, LOST with pnl≥0) so verdict stats match resolver hygiene.

2. **`tools/money_ready_snapshot.py`**
   - Subprocess sets `PYTHONPATH=<repo>` when calling the verdict script.

3. **`audit_trail/dashboard_payload_health.py`**
   - Tolerate `unrealized_pnl_pct=None` and empty `active_picks` (fixes spurious `ueps` invalid_numeric_fields on Feed Health Check when optional fields are null).

4. **`audit_dashboard/data/money_ready_verdict.json`**
   - Refreshed via `python3 tools/money_ready_snapshot.py` (read-only verdict compute; not dashboard_generator).

## Verification

```bash
python3 -m py_compile alpha_engine/money_ready_verdict.py tools/money_ready_snapshot.py
python3 tools/money_ready_snapshot.py
python3 alpha_engine/money_ready_verdict.py --json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['CRYPTO']['top_sleeves'], d['CRYPTO']['recency_ok'])"
```

Expected: import succeeds; `MONEY_READY: none`; CRYPTO shows `top_sleeves` with `crypto_liquidity_wick_reversal_v1` (n=30, PF≈1.55, single-source flag).

## Live state (policy-clean, post-fix)

- **0/9 classes MONEY_READY** — correct per charter (n≥100, PF≥1.5, WR floors, net expectancy, DSR/SPA).
- **Only T2 sleeve across all classes:** `crypto_liquidity_wick_reversal_v1` (CRYPTO, n=30, single-source artifact).
- **mega_mutation unblock:** swarm 4/4 HOLD until ~2026-06-12 (7–10d clean sign-coherence + one post-fix close).

## Deploy

After merge: `python3 tools/deploy_audit_files.py --only updates` and `--only ai_tournament` if HTML touched; verify with curl cache-buster.