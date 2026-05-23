# Session Review — 2026-05-17 Session V (Final)

## Context
Final swarm review of sessions S through V. All previously identified action items have been addressed or confirmed done.

## Completed This Session (V)

### 1. CRYPTO P0 Stop-Loss Bug — FIXED
- File: `alpha_engine/outcome_resolver.py` (commit `fcf499355a`)
- Root cause: `_resolve_claude_gainer_ml_pick()` used `live_price <= sl` for ALL directions
- SHORT stops never fired when price rose above SL (APEUSDT SHORT: SL=$0.121, exit=$0.2098)
- Fix: direction-aware `live_price >= sl if is_short else live_price <= sl`
- Also fixed TP direction (SHORT: price goes DOWN to TP, not up)
- 169 tests pass

### 2. pending_spa_scan Wired to Dashboard
- File: `audit_trail/dashboard_generator.py` (commit `25bf5676eb`)
- `pending_spa_alerts` key added to dashboard payload alongside `money_ready_verdicts`
- Fail-open import — {} when tools.pending_spa_scan unavailable

### 3. EQUITY-specific DSR Threshold
- File: `alpha_engine/money_ready_verdict.py` (commit `25bf5676eb`)
- `MIN_WR_BY_CLASS = {"EQUITY": 0.52}` — institutional benchmark accepts 52% WR
- EQUITY WR=53.3% now passes wr_ok (vs generic 50% floor, not relevant to 55% DSR)
- 6/6 tests pass

### 4. FUTURES WR=3% Root Cause
- Investigation: `futures_momentum` strategy (201/203 picks) — already killed 2026-05-06
- NOT a data pipeline/expiry error — confirmed genuine historical pre-kill data
- 147/197 LOST picks hit -3% stop (strategy hit its stop consistently)
- FUTURES classification is working correctly; no action needed

### 5. combined_confidence Pre-Block
- Already applied by parallel agent (PR #1158, commit `fb0e647577`)
- `combined_confidence` in `BLOCKED_STRATEGIES` at line 1315

### 6. FOOLPROOF_ACTION_PLAN.md Amended
- FUTURES n=203 corrected (was n=0)
- P0/P1/P2 action items documented

## Open Items (Blocked or Long-Term)

| Item | Status | Blocker |
|------|--------|---------|
| MySQL ghost-row purge (655k stale rows) | BLOCKED | Needs PA console access |
| UEPS_ENABLE_PEAD=1 check | BLOCKED | Needs PA console |
| BOND n<50 — needs more picks to reach verdict | LONG-TERM | Natural accumulation |
| ETF n=74 → n=100 for T2 cert | LONG-TERM | Natural accumulation |
| CRYPTO MONEY_READY | LONG-TERM | Depends on MySQL purge (2026-05-24) |
| P4 volatility/threshold mutation axis doc | OPEN | Other agent handling |

## Questions for Swarm Review

**Q1: EQUITY verdict after 52% floor adjustment**
With MIN_WR_BY_CLASS["EQUITY"]=0.52 and current WR=53.3%, EQUITY's `wr_ok` is now True. Combined with PF=1.97 (≥1.5) and existing DSR/SPA tests, what verdict should EQUITY get under the new thresholds? Should it now be MONEY_READY or still WATCH pending DSR confirmation?

**Q2: FUTURES — should it be renamed/reclassified?**
All FUTURES picks are commodity futures (CT=F, SI=F, HG=F, KC=F etc.) and the only strategies ever run were `futures_momentum` (killed) + `futures_bb_mean_reversion` (blocked). Should FUTURES be merged into COMMODITY asset class in the dashboard, or kept separate as an asset class waiting for a viable futures strategy?

**Q3: Stop-loss fix validation**
The direction-aware SL fix changes behavior for all CRYPTO SHORT picks going forward. Are there any existing OPEN SHORT picks in `alpha_engine/data/active_picks.json` that have stops that should now be triggering? Should we run an immediate re-scan?

**Q4: pending_spa_alerts in dashboard**
Now that `pending_spa_alerts` is in the dashboard payload, how should it surface in the UI? Options: (a) badge on asset class tile when alerts exist, (b) new "Pre-SPA Warnings" section, (c) tooltip on strategy count. Which approach fits existing dashboard design (`audit_dashboard/template.html`)?

## Summary of Action Items Status

| P0 | CRYPTO stop-loss direction bug | DONE (fcf499355a) |
| P0 | combined_confidence pre-block | DONE (PR#1158) |
| P1 | pending_spa_scan wired to dashboard | DONE (25bf5676eb) |
| P1 | FUTURES pipeline audit | DONE (not a bug) |
| P2 | EQUITY asset-class DSR floor | DONE (25bf5676eb) |
| BLOCKED | MySQL ghost-row purge | PA console needed |
| BLOCKED | UEPS_ENABLE_PEAD | PA console needed |

## Required Output Format
```json
{
  "questions": [
    {
      "id": "Q1",
      "verdict": "pre-block|wait|needs-data|already-handled|recommend",
      "reasoning": "...",
      "recommended_action": "...",
      "files_to_change": ["..."]
    }
  ],
  "overall_session_grade": "A|B|C",
  "grade_reason": "one sentence",
  "remaining_blockers": ["..."],
  "additional_action_items": [
    {"priority": "P0|P1|P2", "description": "...", "owner": "claude-code|pa-console|human"}
  ]
}
```
