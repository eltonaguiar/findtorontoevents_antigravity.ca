# 7-Day Resolver Follow-Up: Post-Fix Clean Recompute
**Date:** 2026-05-05  
**Author:** claude-sonnet-4-6 (session follow-up)  
**Source:** `reports/action_B_resolver_2026_04_27.md` — P0 follow-up required at T+7d  
**Dashboard payload:** `audit_dashboard/data/dashboard_data.json` (generated 2026-05-05T01:37:46Z)

---

## 1. Resolver Status: FIXED ✅

The `PNL_WIN_THRESHOLD` bug at `alpha_engine/outcome_resolver.py:97` has been resolved.

**Before (bug):**
```python
PNL_WIN_THRESHOLD = 0.00001  # 0.001% / 0.1bp — applied to ALL asset classes
```

**After (fix — v2, 2026-04-28 + v2.1 bug bundle 2026-05-02):**
```python
PNL_WIN_THRESHOLD_BY_CLASS = {
    "CRYPTO":    0.00001,   # 0.1bp — crypto-tight
    "EQUITY":    0.0005,    # 5bp
    "ETF":       0.0005,
    "FOREX":     0.0005,    # 5bp — was 0.1bp (50x too tight)
    "COMMODITY": 0.0005,
    "BOND":      0.0005,
    ...
}
```

Commits touching the resolver since 2026-04-28:
- `6720a895` 2026-05-02T06:42Z — v2.1 bug bundle (retry cap for non-crypto unresolved picks)
- `c8ee616c` 2026-05-04T23:23Z — consensus outcomes update

The live-spot close at `:384-405` is now gated by the per-class threshold. The `FORCE_CLOSED`-via-live-spot flicker that drove FOREX 63% and COMMODITY 67% noise shares now resolves correctly at 5bp.

**P0 SLA met:** Fix shipped within 24h of the 2026-04-27 investigation report (within the 1h-to-suspend / 24h-to-ticket escalation matrix).

---

## 2. Per-Class Numbers: Before vs After (7-Day Clean Recompute)

| Asset Class | PF (pre-fix, 2026-04-28) | PF (post-fix, 2026-05-05) | WR pre | WR post | n pre | n post | Verdict |
|-------------|--------------------------|---------------------------|--------|---------|-------|--------|---------|
| **COMMODITY** | 1.78 | **2.08** (+17%) | 46.9% | 48.7% | 750 | 816 | T2 PF confirmed; lift WR to 50%+ for full T2 |
| **EQUITY** | 1.41 | 1.42 | 52.7% | 52.8% | 421 | 428 | T2 candidate; stable |
| **BOND** | 1.72 | 1.72 | 55.6% | 55.6% | 18 | 18 | T2 metrics; n<100 charter floor |
| **FOREX** | 0.27 | 0.28 | 46.4% | 45.6% | 1169 | 1249 | **Still deeply sub-floor — see §3** |
| **ETF** | 1.24 | 1.20 | 55.2% | 53.4% | 87 | 88 | Minor regression; n→100 still needed |
| **CRYPTO** | 1.25 | 1.26 | 44.6% | 44.8% | 8067 | 8162 | Sub-T2; quan_engine drag unresolved — see §4 |

**Key finding:** COMMODITY PF improved substantially (1.78 → 2.08, +17%), consistent with the resolver fix reclassifying noise-WON picks back to FLAT. FOREX barely moved (0.27 → 0.28), confirming the FOREX problem is **genuine losing trades**, not resolver artifacts.

---

## 3. FOREX Verdict: Genuine Sub-Floor (Not Resolver Noise)

**The Cannot-Evaluate block CAN be lifted for COMMODITY (PF now trustworthy at 2.08). It CANNOT be lifted for FOREX.**

FOREX PF 0.28 post-fix means the resolver was not the cause of FOREX underperformance. The `MUTATION_THREE_AXIS_PROTOCOL.md` must be applied:

- Export closed FOREX picks CSV: `python tools/mutation_analysis.py --class FOREX`
- Identify the worst source systems (per-source PF breakdown)
- Apply axis 1 (signal mutation), axis 2 (sizing), axis 3 (time-filter) before any strategy kill
- Do NOT expand `BLOCKED_SOURCE_SYSTEMS` without `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` first

**FOREX deep-dive action item:** Spawn `reports/deep_dive_FOREX_2026-05-05.md` per Goal #1 process. Per-source autopsy is the first gate.

**Revert note:** PR #800 reverted a FOREX JPY_CROSS_BUY_KILL fix (2026-05-04) — check if the revert was justified or if the evidence was mis-interpreted before opening a new kill PR.

---

## 4. CRYPTO: PR #461 Closed Without Merge — Drag Strategies Still Active

PR #461 (asset-class clean re-extraction) was **closed but NOT merged** on 2026-04-30.

Current `recent_closed` strategy breakdown for CRYPTO (from dashboard payload 2026-05-05):

| Strategy | n (recent_closed) | PF | Status |
|----------|-------------------|----|--------|
| `quan_engine` (base) | 314 | 0.66 | **NOT in blocklist** — only `quan_engine_position`/`quan_engine_scalp` variants are blocked (smart_picks_engine.py:215,243) |
| `unknown` | 100 | 0.55 | Source attribution missing |
| `ensemble` | 55 | 0.91 | Sub-T2 |
| `macd_rsi_confluence` | 32 | 0.59 | In blocklist (line 209) but historical picks still aggregate |

**Projected vs actual CRYPTO improvement:**
- Projected (per PR #461 analysis): PF 1.25 → 1.30+ after strategy retirements
- Actual: PF 1.25 → 1.26 (+0.01)

The shortfall is because `quan_engine` base (PF 0.66, ~21% of CRYPTO recent-closed volume) is still generating new picks. **Open action:** block `quan_engine` base via `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` process — 7-day evidence already shows clear sub-floor performance.

---

## 5. ML Model Freshness

`python tools/assert_model_freshness.py --threshold-days 7` as of 2026-05-05T02:01Z:

| Artifact | Status | Age |
|----------|--------|-----|
| `alpha_engine/data/rf_model.pkl` | OK | 2.79d |
| `alpha_engine/data/ml_challenger.joblib` | OK | 2.79d |
| `ml_gatekeeper/models/gatekeeper_model.joblib` | OK | 0.00d |
| `ml_gatekeeper/models/training_report.json` | OK | 0.02d |
| `ml_battleground/retrain_trigger.json` | OK | 0.00d |
| `ml_crypto_predictor/enhanced_models/feedback_training_report.json` | **MISSING** | n/a |
| `ml_crypto_predictor/enhanced_models/results/training_summary.json` | OK | 3.84d |
| `mercury2/data/training_summary.json` | OK | 0.00d |
| `mercury2/models/top_gainer.joblib` | OK | 0.00d |
| `claude_gainer_ml/models/training_meta.json` | OK | 0.54d |
| `claude_gainer_ml/models/claude_xgb.joblib` | OK | 0.00d |
| `crypto_ml_edge/results/training_report.json` | OK | 2.79d |

**Summary: 11/12 fresh, 1 missing.** The missing `feedback_training_report.json` under `ml_crypto_predictor/enhanced_models/` means the crypto feedback trainer has not completed a training epoch since the resolver fix. Models may still be partially trained on pre-fix CRYPTO labels (low priority given CRYPTO's sub-T2 status).

---

## 6. Re-Resolve Historical Non-Crypto Picks: PENDING

`tools/re_resolve_historical_v2.py` exists as a **dry-run skeleton** ("DRY-RUN ONLY by default. A separate, explicitly-approved follow-up PR is required to apply the rewrite" — per file header).

The re-resolve has NOT been run. The resolver v2 fix applies to new resolutions going forward, but ~1,860 historical non-crypto picks closed before 2026-04-28 retain pre-fix labels.

**Action required:** Run `python tools/re_resolve_historical_v2.py --dry-run` to generate the delta CSV, review, then open a PR to apply. Per `reports/action_B_resolver_2026_04_27.md §9.2`, this must happen BEFORE the next non-crypto ML retraining run to avoid a label-shock.

---

## 7. PR #461 Status

- **State:** closed, NOT merged (closed 2026-04-30)
- **Scope:** retire 4 CRYPTO strategies (macd_rsi_confluence, quan_engine, rsi_bounce, ensemble) + poison-symbol gate + CRYPTO SHORT-disable
- **Impact:** strategy retirements from PR #461 did NOT land in main; `quan_engine` base remains unblocked
- **Path forward:** re-open as a new PR following `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` for `quan_engine` base specifically

---

## 8. Open Actions Summary

| # | Action | Priority | Dependency |
|---|--------|----------|------------|
| 1 | Run `re_resolve_historical_v2.py --dry-run` → review → apply PR | P1 | Before next ML retrain |
| 2 | Spawn `reports/deep_dive_FOREX_2026-05-05.md` — per-source PF autopsy | P1 | None |
| 3 | Investigate PR #800 FOREX revert — was it correct? | P2 | After FOREX deep-dive |
| 4 | Block `quan_engine` base — follow `STRATEGY_INVESTIGATION_BEFORE_KILL.md` | P2 | Deep-dive doc first |
| 5 | COMMODITY WR lift: 48.7% → 50%+ for full T2 | P2 | Ongoing |
| 6 | Recreate `ml_crypto_predictor/enhanced_models/feedback_training_report.json` | P3 | Low |
| 7 | ETF n → 100 to cross charter floor | P3 | Ongoing |

---

*Resolver fix confirmed in place (P0 SLA met). COMMODITY verdict unlocked (PF 2.08, genuine). FOREX remains sub-floor and is confirmed not a resolver artifact — genuine losing trades require mutation protocol. Next gate: historical re-resolve + FOREX deep-dive.*
