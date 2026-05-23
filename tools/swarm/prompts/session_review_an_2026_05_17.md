# Session AN — Swarm Review Request
# Date: 2026-05-17
# Session: AN (following AM — APPROVE)

## Context

Session AN: diagnostic follow-up after AM. Found and fixed a real code bug (M-080) in the
`money_ready_verdict` dashboard_fallback path. Also identified a data quality artifact
(one mislabeled BOND pick).

## Session AN Findings

### 1. M-080 Bug Fixed — ETF win_rate field name mismatch

**Root cause:** `money_ready_verdict.py` initial `class_stats` population for dashboard-only
classes (those with 0 resolved picks in `closed_picks.json`) used `health.get("wr")` which
doesn't exist in `asset_class_health` (the field is `win_rate` / `wr_pct`). This set `wr=0.0`.
Because `n=74` was then ≥ MIN_N_CLASS=50, the downstream override block (which has the correct
`win_rate` lookup) never fired. Result: ETF showed `wr=0.0` in `money_ready_verdicts` despite
real `win_rate=67.6%`, causing `wr_ok=False` and potentially suppressing a WATCH→MONEY_READY
promotion when ETF accumulates enough per-strategy picks.

**Fix (M-080):**
```python
# Before (bug):
class_stats[ac_up] = {
    "n": health.get("n", 0),
    "wr": health.get("wr") or 0.0,   # ← "wr" key doesn't exist → always 0.0
    "pf": health.get("pf") or 0.0,
    ...
}

# After (fix):
_raw_wr = health.get("win_rate") or health.get("wr_pct") or health.get("wr") or 0
_wr = float(_raw_wr) / 100 if float(_raw_wr or 0) > 1 else float(_raw_wr or 0)
_pf = float(health.get("pf") or health.get("profit_factor") or 0)
class_stats[ac_up] = {"n": ..., "wr": _wr, "pf": _pf, ...}
```

**Verified:**
- ETF WR: `0.0 → 0.676` after fix
- 9/9 money_ready_verdict tests pass
- 110/110 quality_gates tests pass
- Commit `4ae5629ac1` pushed to main

### 2. Current money_ready_verdicts (post M-080 fix, dashboard 15:04 UTC)

| Class | n | WR | PF | Verdict | Source |
|-------|---|----|----|---------|--------|
| CRYPTO | 475 | 68.2% | 2.60 | MONEY_READY | closed_picks |
| EQUITY | 240 | 54.2% | 2.04 | WATCH | dashboard_fallback |
| COMMODITY | 354 | 60.2% | 2.15 | WATCH | closed_picks |
| ETF | 74 | **67.6%** (was 0.0%) | 2.49 | WATCH | dashboard_fallback |
| FOREX | 618 | 33.3% | 0.48 | NOT_READY | closed_picks |
| BOND | 12 | 50.0% | 0.66 | INSUFFICIENT_DATA | dashboard_fallback |

### 3. BOND top_symbol=USDJPY=X — Data Quality Artifact

In `closed_picks.json`, there is 1 resolved BOND pick with:
- symbol: `USDJPY=X` (clearly FOREX)
- strategy: `cta_fx_multifactor`
- source_system: `cta_replicator`
- status: LOST
- pick_id: null, entry_time: null, exit_time: null

This is a legacy artifact — `cta_replicator` emitted a FOREX pick tagged as `asset_class=BOND`.
The pick has null pick_id and null timestamps, suggesting it predates proper pick tracking.
**No immediate action taken** — closed_picks.json was not edited manually (high data risk).
The BOND money_ready_verdict (INSUFFICIENT_DATA) is correct despite this artifact.

### 4. CI Status — All Green

- 0 stale failures across all workflows
- No open PRs
- All 20 workflows showing `success` in most recent run

### 5. FOOLPROOF Remaining Items

All open FOOLPROOF items are either externally blocked or monitoring notes:
- COT feature enrichment (`cot_net_z` not populated upstream) — external
- Per-class `ml_score` gate ≥55 — ml_score not populated upstream
- FRED GDP/ISM macro overlay — FRED API key needed
- BOND PF monitoring (n=12, review at n=30 if PF<0.80)
- COT PF > 4.0 target by 2026-05-23 — external data dependency

## Questions for Swarm

1. **M-080 approval**: Is the fix correct and sufficient? The `_raw_wr` / `_wr` / `_pf` computation
   now matches the override block logic exactly. Any edge cases to worry about?

2. **BOND USDJPY=X artifact**: Should we add a validation rule in `feed_hygiene.py` or the
   outcome resolver to reject/reclassify picks where symbol doesn't match claimed asset_class?
   (e.g., USDJPY=X tagged as BOND should be auto-reclassified to FOREX.) Risk: false positives
   on unusual instruments.

3. **ETF verdict**: ETF now shows WR=67.6% PF=2.49 but still WATCH. CB-30d WR=67.5% n=40. The
   path to MONEY_READY requires ≥2 strategies with n≥20 (PBO/SPA), but ETF has 0 closed_picks
   in the per-pick store (all fallback). Is the ETF scanner generating resolved picks anywhere?
   Should we investigate why `closed_picks.json` has 0 ETF picks despite n=74 in dashboard?

4. **COMMODITY concentration**: CT=F is 65.25% of resolved COMMODITY picks (verdict WATCH not
   MONEY_READY due to concentration cap). Is this acceptable? CT=F has WR=77.5% PF=4.69 (n=40,
   deduped). Should we raise MAX_SYMBOL_CONCENTRATION for COMMODITY specifically?

5. **Overall verdict**: Is Session AN APPROVE?

## Verification

- CI: 0 failures, 20 success (latest run)
- M-080: 9/9 money_ready tests + 110/110 quality gates tests pass
- ETF WR: fixed 0.0 → 0.676
- BOND data artifact: documented, no edits to closed_picks.json
- Commit: `4ae5629ac1`
