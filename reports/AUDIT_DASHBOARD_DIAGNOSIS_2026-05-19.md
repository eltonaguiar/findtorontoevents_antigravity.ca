# /audit Dashboard — Diagnosis & Fixes — 2026-05-19

Session findings on why the /audit dashboard showed stale data, 404s, and
all-zero asset-class tiles. Multi-agent investigation.

## 1. Stale data + 6 resource 404s — FIXED (verified)

The FTP-deploy embedded Python in `.github/workflows/audit-dashboard.yml` had a
**syntax error** (`ensure_nested_dir`/`upload_research_tree` indented 12sp not
10sp; 3 research-artifact blocks 16sp not 14sp) — the deploy step could not run.
Plus: `pf_registry.json`/`money_ready_verdict.json` starved by the 17.8MB
`dashboard_data.json` mid-glob; `money_ready_filter.js`/`hc_filter.js`/
`validation_metrics.js`/`ml_gatekeeper/data/active_picks.json` never deployed;
`active_picks_ab_new.json` a dead JS fetch.

**Fix `b863dc392f7`** — indentation repair + `dashboard_data.json` uploads last
+ missing JS/ml_gatekeeper uploads + dead-fetch removal. **Verified:** run
`26076021330` succeeded, all 6 resources now 200, dashboard fresh.

## 2. All 7 asset-class tiles "active 0 | smart 0" — FIXED

**Root cause:** `audit_trail/safety_status.py::get_binance_circuit_breaker_status()`
returned `{"open": True, "reason": "CI_GEO_BLOCK"}` for **any** CI run with no
breaker-state file. That fed `safety_status` verdict=STOP, and the M-049
safety-halt gate (`quality_gates.py:6300`) rejects 100% of picks on STOP — so
the generator gated out all 162 active picks every run and published
`picks.active=[]` → every tile zero.

A CI runner geo-blocked from Binance is a *data-source* problem (handled by the
3+ API failover chain), **not** a circuit-breaker trip. **Fix `5f036a205bc`** —
CI geo-block now reports `open: False` (reason kept for visibility). Repro
confirmed: `GITHUB_ACTIONS=true` + no breaker file → verdict CAUTION (was STOP).

## 3. Per-asset-class pick freshness — thin/empty lanes

Latest pick per class (live `dashboard_data.json` 2026-05-19, `active_raw`
162 + `recent_closed` 3500):

| class | latest pick (UTC) | 24h | 7d | 30d |
|-------|-------------------|-----|-----|-----|
| CRYPTO | 05:44 today | 289 | 1120 | 3019 |
| COMMODITY | 05:44 today | 6 | 28 | 62 |
| EQUITY | 03:47 today | 23 | 31 | 95 |
| FOREX | 05:44 today | 4 | 12 | 80 |
| ETF | 04:10 today | 8 | 20 | 48 |
| FUTURES | 05:43 today | 4 | 4 | 6 |
| BOND | 03:17 today | 1 | 1 | 1 |

Picks ARE being generated fresh for every class — thinness is a **delivery**
problem, not generation:

- **`active_raw` is not the pre-gate pool it claims.** `dashboard_generator.py:16841`
  snapshots `active_raw` AFTER the staleness auto-expiry pass (NON_CRYPTO_MAX_AGE
  240h) — non-crypto emitter picks get expired before the snapshot. The generator
  log reads "10204 active" from 142 sources but only 162 reach `active_raw`.
  **DEFERRED FIX:** capture `active_raw` before the `:9092` expiry pass. Not done
  this session — `dashboard_generator.py` had concurrent peer WIP; editing it
  would entangle peer code.
- **BOND:** scanner runs + generates 5 picks, but the commit step staged the
  wrong path and chronically failed on unmerged files → picks never persisted.
  **Fix `6a007ad0732`** — `etf-bond-scanner.yml` now stages
  `alpha_engine/data/active_picks_bond.json` (the path the dashboard reads) and
  uses conflict-safe `safe_push.sh`.
- **ETF:** `etf_sector_picks.json` has 19 fresh picks that never appear in any
  dashboard row — dropped at the `active_raw` post-expiry snapshot (same bug).
- **FUTURES:** genuine under-generation — `non_crypto_agent/data/futures_picks.json`
  is empty (count 0); live FUTURES picks come only from `multi_asset_copytrader`.
  Plus `alpha_engine_unified` FUTURES rows are MySQL-direct orphans (per
  RESOLUTION_PIPELINE_FIX_PLAN). Operator-gated.
- **FOREX:** least broken — thin but live (80/30d).

## 4. Shadow gates (resolver-plan step 3) — identifiers found

Both real, both in `alpha_engine/money_ready_verdict.py`, both default-shadow:
- `ML_ENHANCED_CRYPTO_QUARANTINE` (env flag, M-105) — `:49-62`/`:421-435`.
  Flip `=1` → drops ml_enhanced crypto picks → CRYPTO sub-floor n → NOT_READY.
  Genuinely wired. Monotone-conservative.
- `MDD_GATE_ENFORCE` (env flag, I-3) — `:64-76`/`:676-732`. **Wiring bug:**
  enforce mode flips the stamp but `_verdict()` never reads `_MDD_GATE_ENFORCE`,
  so it does NOT change the verdict. Needs a 1-line wire-in to `_verdict()`
  mirroring the `_SLIPPAGE_GATE_ENABLED` block. Monotone-conservative by design.

## Fixes shipped this session

| commit | what |
|--------|------|
| `b863dc392f7` | deploy-Python syntax repair + 6 dashboard 404 fixes (verified live) |
| `5f036a205bc` | CI geo-block no longer false-trips Binance breaker — unblocks tiles |
| `6a007ad0732` | etf-bond-scanner: correct bond commit path + conflict-safe push |

## Still open

- `active_raw` pre-expiry snapshot fix — deferred (peer WIP on dashboard_generator.py).
- FUTURES under-generation (empty futures emitter) — operator-gated.
- `MDD_GATE_ENFORCE` wiring bug — 1-line fix, gated on the step-3 decision.
- Duplicate bond workflows (`etf-bond-scanner.yml` vs `alpha-engine-bond.yml`) +
  missing `fredapi`/`pandas_datareader` deps — operator-gated.
