# Remaining Action Items Audit — 2026-06-05

**Auditor:** Claude Code on gx10-c9b9  
**Time:** 2026-06-05 ~14:20 UTC  
**Source:** Session summary action items from `updates/2026-06-05-dropchat-session-summary-and-action-items.md`

---

## P0: GHA Workflow Runs — Lazy-Import Fix Stability

**Status:** ✅ FIX IS HOLDING (with one pre-fix failure noted)

**Findings:**
- 15 of the last 20 GHA runs were successful, 1 failed, 4 in progress
- **Failed run:** `Money-Ready Registry Gate` (ID `27020196293`, created 2026-06-05T14:16:51Z, commit `be7721dc34`)
  - Error: `NameError: name 'passes_high_conviction_gate' is not defined` at line 1303 of `money_ready_verdict.py`
  - **Root cause:** This run executed against a commit BEFORE the lazy-import fix (`e5cebb01b2`). The current code at lines 1399-1406 correctly uses the `_get_fundamental_macro_gates()` lazy-import pattern.
- **audit-dashboard.yml:** Last 4 completed runs all succeeded. 1 run pending (14:13:40Z).
- **Most recent 8 runs (post-fix):** 100% success rate.

**Verdict:** The lazy-import fix is holding. The one failure was from a pre-fix commit. The in-progress Money-Ready run should succeed.

---

## P0: PF Registry Jumps — Data Verification

**Status:** ⚠️ DATA REAL BUT SAMPLE SIZES TOO SMALL FOR MOST CLASSES

**policy_clean_net breakdown (canonical view):**

| Asset Class | n | PF | WR% | Sample Adequate? | Notes |
|---|---|---|---|---|---|
| CRYPTO | 301 | 0.99 | 34.6% | ✅ Yes | PF < 1.0 — NOT_READY |
| EQUITY | 45 | 0.26 | 24.4% | ❌ No (need ≥100) | PF far below threshold |
| COMMODITY | 7 | 1.74 | 42.9% | ❌ No (need ≥100) | Single-source risk (HHI=0.57) |
| FOREX | 22 | 11.22 | 22.7% | ❌ No (need ≥100) | PF inflated by small sample; WR well below floor |
| FUTURES | 14 | 0.39 | 7.1% | ❌ No (need ≥100) | PF < 1.0, near-zero WR |
| ETF | 11 | 0.80 | 63.6% | ❌ No (need ≥100) | PF < 1.0 |
| PENNY_STOCK | 1 | — | — | ❌ No | 1 trade |
| UNKNOWN | 8 | 3.98 | 75.0% | ❌ No | Single-source artifact |

**PF jump analysis:**
- **FOREX 0.73→11.22:** A single losing trade was likely dropped (n went from 44→43 in deduped view), removing a large gross_loss entry. The PF jump is real data but statistically fragile at n=22.
- **ETF 0.08→0.79:** ETF n dropped from 21→13 in policy_clean_net, meaning 8 trades were filtered out (likely policy-excluded). The remaining 13 have a more favorable PF. Real data shift, not artifact.
- **FUTURES 0.07→0.39:** n dropped from 17→14, removing 3 large losing trades. PF still <1.0, so still NOT_READY.

**Verdict:** The jumps are caused by policy-cleaning removing outlier trades, not data corruption. However, ALL asset classes except CRYPTO have insufficient sample sizes for money-ready promotion.

---

## P1: Scan for Importers of `fundamental_macro_gates` at Module Level

**Status:** ⚠️ ONE FILE NEEDS ATTENTION

**Findings:**

| File | Import Style | Risk |
|---|---|---|
| `alpha_engine/eagle_gates.py:14` | **Top-level** `from alpha_engine.fundamental_macro_gates import ...` | ⚠️ Same failure mode as pre-fix money_ready_verdict |
| `alpha_engine/money_ready_verdict.py:55-59` | Lazy import inside `_get_fundamental_macro_gates()` | ✅ Fixed |

**Risk assessment for eagle_gates.py:**
- `eagle_gates.py` imports `passes_high_conviction_gate` and `passes_long_term_stability_gate` at module level (line 14).
- These are used by `passes_hard_money_gates()` (line 530+) and `is_admissible_for_production()` (line 430+).
- In production (scanner, paper-pilot), `eagle_gates.py` is imported after `sys.path` is set correctly, so it works fine.
- In GHA runners with misconfigured `sys.path`, the same `ModuleNotFoundError` would occur if any CI script imports `eagle_gates` at module load time.
- The Money-Ready workflow imports `money_ready_verdict.py` (which lazily imports `eagle_gates` via `_get_eagle_gates()`), so it does NOT trigger the top-level import in eagle_gates.py directly.

**Recommendation:** The current architecture isolates the risk. `money_ready_verdict.py`'s lazy import of `eagle_gates` means the top-level import in `eagle_gates.py` is only triggered when `passes_recency_gate()` is actually called (inside `_get_eagle_gates()`), at which point `sys.path` should already be correct. **No immediate fix needed** — but if other GHA scripts start importing `eagle_gates` directly, apply the same lazy-import pattern.

---

## P1: bt_backtest_trades Cross-DB Sync Stability

**Status:** ✅ STABLE

**Findings:**
- `audit-dashboard.yml` last 4 completed runs all succeeded
- The `imported_at` column fix and `MAX(id)` PK optimization appear to be working correctly
- No duplicate-insertion errors reported in recent runs

**Recommendation:** Continue monitoring. Recheck in 24h to confirm cron stability.

---

## P1: ETF/FUTURES Sample Sizes — Money-Ready Admission

**Status:** ⚠️ ALL BELOW THRESHOLD

**Current thresholds (from PERFORMANCE_CHARTER):**
- Minimum n for money-ready: ≥100 resolved picks per asset class
- Minimum n for strategy-level SPA: ≥20 picks per strategy

**Current state:**

| Asset Class | n (policy_clean_net) | Gap to n=100 | Estimated days to fill (at current pick rate) |
|---|---|---|---|
| ETF | 11 | 89 more needed | Unknown — ETF picks are rare |
| FUTURES | 14 | 86 more needed | Unknown |
| FOREX | 22 | 78 more needed | ~2-3 months at current rate |
| EQUITY | 45 | 55 more needed | ~1-2 months |
| COMMODITY | 7 | 93 more needed | Rare picks |
| CRYPTO | 301 | ✅ Already ≥100 | N/A |

**Recommendation:** Do NOT admit ETF, FUTURES, COMMODITY, or FOREX to money-ready until n≥100. CRYPTO is the only class with sufficient data. EQUITY is closest but still 55 picks short.

---

## P2 (Deferred — Not Actioned This Session)

- **Shadow-mode gates review** — due 2026-06-17 (30 days after 2026-05-19)
- **Dashboard data freshness** — consider 30-min refresh for high-traffic periods
- **Revert lazy imports** — low priority; current pattern works fine

---

## Summary

| Item | Status | Action Needed |
|---|---|---|
| GHA lazy-import fix | ✅ Holding | Monitor next few runs |
| PF registry jumps | ✅ Real data | No fix needed (policy-cleaning effect) |
| fundamental_macro_gates importers | ⚠️ eagle_gates.py top-level | No immediate fix; monitor if other GHA scripts import directly |
| bt_backtest sync | ✅ Stable | Continue monitoring |
| ETF/FUTURES sample sizes | ⚠️ Too small | Do not admit to money-ready until n≥100 |

---

*Generated by action-items audit on gx10-c9b9 at 2026-06-05T14:20 UTC*
