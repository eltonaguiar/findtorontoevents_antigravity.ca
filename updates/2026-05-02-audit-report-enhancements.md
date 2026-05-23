# Audit Report Enhancements — Resolver + Filter Calibration

**Date:** 2026-05-02
**Author:** Copilot review of [`audit_report.md`](../audit_report.md) (2026-05-01)
**Scope:** Deep-dive verification of every bug/filter the 2026-05-01 audit flagged in `outcome_resolver.py`, `hc_filter.js`, `hedge_fund_quality_gate.py`, `hf_quality_gates.json`, and `shadow_blocked.json`; calibrated, repo-accurate enhancement proposal.
**Frontend impact:** `findtorontoevents.ca/audit` (main dashboard) **and** `findtorontoevents.ca/audit/hyrotrader` (Hyro slice) — both consume the same resolved-pick ledger, so every fix below propagates to both surfaces.
**Major-goal alignment:** Goal #1 — *phenomenal performance across ALL asset classes on `/audit`* (per `AGENTS.md`). The 0% FOREX / near-zero COMMODITY tiles are the single biggest visible blocker to that goal today.

> **TL;DR:** The audit is mostly correct and high-value. 11 of 14 line-item diffs are verified against current code. 3 are partially incorrect or already partly implemented. The root-cause chain (broken resolver → corrupted stats → over-tightened filters → empty tiles) is the right mental model. **Order of operations matters:** ship resolver fixes (Section A) **first**, observe ≥7 days of post-v2 data, **then** relax filters (Section B). Doing them simultaneously risks publishing picks against still-corrupted WR.

---

## Section 0 — Verification Summary

| # | Audit claim | Verified against source? | Notes |
|---|---|---|---|
| Bug 1 | Infinite retry loop for non-crypto picks with missing OHLC | ✅ Verified | `outcome_resolver.py:621-631`, `:658-674`, `:489`, `:828-830`. Real, primary driver of zombie unresolved queue. |
| Bug 2 | Daily bar-replay includes pre-entry intraday action (lookahead) | ✅ Verified | `outcome_resolver.py:351-353`. Real lookahead bias for intraday non-crypto entries. |
| Bug 3 | Empty `[]` OHLC list bypasses replay (truthy check) | ✅ Verified | `outcome_resolver.py:608` uses `and ohlc_window:`. Empty list ≠ None handling collapses. |
| Bug 4 | `resolve_active_non_crypto` leaves picks active forever | ✅ Verified | `outcome_resolver.py:1909-1917` (audit cited 1908-1916, 1-line shift). Real zombie source. |
| Bug 5 | `_fetch_yfinance_ohlc_window` has no timeout | ✅ Verified | `outcome_resolver.py:315-325` — bare `ticker.history()` call, no timeout kwarg. |
| Bug 6 | 5bp floor misclassifies tight-TP forex scalps as FLAT | ⚠️ Partially verified | Real but limited — `PNL_WIN_THRESHOLD_BY_CLASS` has well-documented 5bp justification (lines 100-114). Only a real loss for sub-5bp TP strategies, which are uncommon. **Lower priority than audit suggests.** |
| Bug 7 | Breakeven fallback omits `status` stamp | ✅ Verified | `outcome_resolver.py:665-674`. Real downstream-integrity issue. |
| Filter 1 | `forwardWRMinPct` raised to 70 for all classes | ✅ Verified | `hc_filter.js:34-36, 339-346`. Audit's evidence-based critique is sound. |
| Filter 2 | `passesPerAssetTierContract` blocks all non-crypto tier-S + most A/B | ✅ Verified | `hc_filter.js:200-237`. Tier S is **mathematically impossible** for non-crypto (the loop only runs when `tier === 'A' || tier === 'B'`). |
| Filter 3 | `FOREX_BANNED_SYMBOLS` blanket-bans all majors | ✅ Verified | `hedge_fund_quality_gate.py:74-76`. Pre-v2 stats are explicitly cited in the comment block (`reports/SYNTHESIS_6_ANALYSES_AUDIT_WHATIF_2026_04_23.md`) — those numbers were computed before the resolver was fixed, so the audit's "corrupted basis" claim is correct. |
| Filter 4 | `FOREX_CONFIDENCE_REJECT_BANDS` = [0.95, 1.0001) | ✅ Verified | `hedge_fund_quality_gate.py:97-99`. n=38 is borderline for a hard ban. |
| Filter 5 | `min_elite_score: 80` is a latent foot-gun | ✅ Verified | `config/hf_quality_gates.json:5`. `enabled: false` so it's currently inert, but flipping the flag would brick the pipeline. |
| Filter 6 | `WINNER_FILTER` is "undocumented and hidden" | ❌ **Incorrect** | The filter **is** in the repo: `alpha_engine/forward_validator.py:399-461`. `confidence_max: 0.85` is real; the audit's substantive observation (stricter than HC's 0.90 and HF's 0.95) is correct. Re-frame: alignment problem, not visibility problem. |
| Filter 1 add'l | Audit's diff "adds" `forwardWRMinPctCommodity/Futures/Bond/ETF` keys | ⚠️ **Already exist** | `hc_filter.js:342-345` already references all four keys; defaults are 70. Only the **values** need lowering, not the schema. |

---

## Section A — Resolver Fixes (Land FIRST, Ship Together)

These break the zombie-queue chain. Until they land, every WR/PF stat downstream is corrupt and any filter changes will be calibrated against bad data.

### A.1 — Retry-cap + force-close (consolidates Bugs 1, 3, 7)

Adopt the audit's `MAX_RESOLVE_RETRIES = 3` design with one enhancement: emit a structured log line every time a pick force-closes so we can monitor the cap in production.

```python
# alpha_engine/outcome_resolver.py — near line 150
MAX_RESOLVE_RETRIES = int(os.environ.get("RESOLVE_MAX_RETRIES", "3"))
```

- Apply audit's diffs at lines 608-631, 658-674, 489, 828-830 (verified accurate).
- Set `pick["status"] = "FLAT"` in the breakeven fallback (Bug 7).
- Treat `ohlc_window` truthiness as `is not None` so empty lists fall through (Bug 3).
- **Add:** when force-close fires, `log.warning("FORCE_CLOSE retries=%d sym=%s class=%s", ...)` so the operations dashboard can alert if force-close > 5% of resolutions on any given day.

### A.2 — Lookahead-bias fix for intraday entries (Bug 2)

Adopt audit's diff at `outcome_resolver.py:351-353` verbatim. **Add a unit test** under `tests/` (or `alpha_engine/tests/`) that asserts: given a 14:00-UTC entry on 2026-04-15, `_fetch_yfinance_ohlc_window` returns bars whose first `date` is ≥ `2026-04-16`.

### A.3 — yfinance timeout (Bug 5) — **prefer `concurrent.futures` over `signal.alarm`**

The audit's primary fix uses `signal.alarm`, which is **Unix-only and unsafe** in multi-threaded callers. The audit's "alternative" footnote (`concurrent.futures.ThreadPoolExecutor` with `future.result(timeout=15)`) should be the **primary** recommendation. Reasons:

1. The audit dashboard pipeline runs in GitHub Actions (Linux, OK) **and** locally on Windows for dev (`signal.alarm` does not exist on Windows).
2. `signal.alarm` only fires in the main thread; if `_fetch_yfinance_ohlc_window` is ever called from a worker thread (which `audit_dashboard/dashboard_generator.py` does in places), the timeout silently never trips.
3. `ThreadPoolExecutor` is portable, thread-safe, and works the same in both environments.

```python
# Replacement primary diff (alpha_engine/outcome_resolver.py:315-325)
import concurrent.futures
YF_HISTORY_TIMEOUT = float(os.environ.get("YF_HISTORY_TIMEOUT", "15"))

def _yfinance_history_with_timeout(symbol, start_dt, end_dt):
    def _call():
        return yf.Ticker(symbol).history(
            start=start_dt.strftime("%Y-%m-%d"),
            end=(end_dt + timedelta(days=1)).strftime("%Y-%m-%d"),
            interval="1d",
            auto_adjust=False,
        )
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(_call).result(timeout=YF_HISTORY_TIMEOUT)
```

### A.4 — Active-pick zombie fix (Bug 4)

Adopt audit's diff at `outcome_resolver.py:1908-1916` (actual lines 1909-1917). **One refinement:** the audit's diff increments `report["sl_hits"]` for any non-WON outcome, including `FLAT`. Tighten:

```python
if outcome == "WON":
    report["tp_hits"] += 1
elif outcome == "LOST":
    report["sl_hits"] += 1
# FLAT: no counter increment, just resolved
```

### A.5 — Configurable forex floor (Bug 6) — **lower priority**

Audit's `FOREX_WIN_THRESHOLD_BP` env var is a clean addition. Default to 5bp (current behavior preserved). Ship in the same PR but treat as nice-to-have.

### A.6 — **NEW** observability: resolver health metrics

Add a daily `audit_dashboard/data/resolver_health.json` written at the end of every `resolve_outcomes()` run, capturing:

```json
{
  "ts": "2026-05-02T01:00:00Z",
  "resolver_version": "v2",
  "by_class": {
    "FOREX": {
      "input": 412,
      "resolved_replay": 198,
      "resolved_force_close": 14,
      "resolved_breakeven_fallback": 8,
      "still_unresolved": 192,
      "yf_timeouts": 3,
      "noise_share_pct": 6.2
    },
    "COMMODITY": { ... }
  },
  "queue_depth_unresolved": 192,
  "queue_depth_unresolved_age_p95_hours": 41.2
}
```

Render this on `/audit` (and `/audit/hyrotrader`) under a "Resolver Health" tile. **This is the operational gate** for Section B: do not relax filters until `still_unresolved` is < 5% of input AND `noise_share_pct` is < 10% on every class for 7 consecutive days.

---

## Section B — Filter Recalibration (Ship AFTER Section A + 7-day soak)

### B.1 — `hc_filter.js` per-class WR floors (Filter 1)

Audit proposes 50–55%. That's the right neighborhood, but I'd land slightly more conservative on the small-sample classes and explicitly date-stamp the change so future readers know the basis:

| Class | Current | Audit | **Proposal** | Rationale |
|---|---|---|---|---|
| CRYPTO | 70 | 55 | **55** | Match audit. Ledger median ~50%, 55% leaves a 5pp safety cushion. |
| EQUITY | 70 | 50 | **50** | Match audit. PEAD/QV strategies legitimately hit 50–55%. |
| FOREX | 70 | 55 | **55** | Match audit. Aligns with `forex_resolver_ab_2026-02-01_2026-04-29.md`. |
| COMMODITY | 70 | 50 | **52** | Slightly above audit. CTA strategies have wide variance; 52 is a small uplift over the EQUITY floor without being a lottery gate. |
| FUTURES | 70 | 50 | **50** | Match audit; tiny sample. |
| BOND | 70 | 50 | **50** | Match audit. |
| ETF | 70 | 50 | **50** | Match audit. |
| `forexRelaxedWRMinPct` (small-sample) | 65 | 50 | **50** | Match audit. |

**Schema correction vs. audit:** the diff at `hc_filter.js:23-40` should *modify values only* — the per-class keys (`forwardWRMinPctCommodity/Futures/Bond/ETF`) **already exist** at `hc_filter.js:342-345`. The audit's "// NEW" block reads as if it were adding them; that's a misread.

Also update `config/hc_gate_params.json` (audit didn't mention it) so the embedded defaults and the JSON-file defaults stay in sync — `hc_filter.js:3-4` explicitly says the JSON is the canonical source.

### B.2 — `passesPerAssetTierContract` non-equity bypass (Filter 2)

Adopt audit's diff. **Add S-tier handling** — the current code returns `false` for non-crypto tier-S because the inner `if` only runs for A/B. After audit's bypass for FOREX/COMMODITY/FUTURES, also explicitly accept non-crypto tier-S for **EQUITY/ETF/BOND/STOCK** when the strategy whitelist matches (or unconditionally, mirroring the crypto S-path), since the current code makes non-crypto tier-S unreachable.

### B.3 — `FOREX_BANNED_SYMBOLS` (Filter 3) — **partial unblock, not full**

Audit recommends clearing the set entirely. Safer alternative: keep two of the four banned and re-evaluate per-pair after 200 post-v2 picks. Pick the two with the worst pre-v2 PF; allow the other two back immediately. This way we get pipeline flow restored without committing fully to a still-uncalibrated reset.

```python
# alpha_engine/hedge_fund_quality_gate.py:74-76
# 2026-05-02: Phased unblock — pre-v2 PF<0.50 stats were corrupted by 0.1bp
# noise inflation. Re-allow EURUSD/AUDUSD majors (deepest liquidity) for
# post-v2 sample collection. Re-audit after 200 post-v2 resolved picks each.
FOREX_BANNED_SYMBOLS = frozenset({"CADJPY=X", "EURJPY=X"})
```

If, after 60 days, the post-v2 ledger still shows PF < 0.7 on EURJPY/CADJPY at n ≥ 100, leave them banned. Otherwise, clear the set entirely.

### B.4 — `FOREX_CONFIDENCE_REJECT_BANDS` (Filter 4)

Adopt audit's "convert to soft penalty" approach. Two small refinements:

1. The current codebase has no first-class "soft penalty" plumbing on this gate. Either:
   - **Disable the band immediately** and re-introduce after monitoring (audit's fallback path), OR
   - Add a `_hf_gate_soft_penalty_reasons` array on the pick dict and have `dashboard_generator.py` deduct 5 score points per reason. The latter is preferable but doubles the PR scope.
2. Track post-v2 high-confidence forex picks separately in `resolver_health.json` so we can re-enable the hard ban if the n ≥ 100 evidence justifies it.

### B.5 — `hf_quality_gates.json` `min_elite_score` (Filter 5)

Adopt audit's lowered default of 30. **Add a fail-safe:** load-time validation in whatever module reads this JSON — refuse to start if `enabled: true` AND `min_elite_score > 50` unless `_force_strict: true` is also set.

### B.6 — `WINNER_FILTER` confidence cap alignment (Filter 6 — corrected)

The filter exists at `alpha_engine/forward_validator.py:399-461`; this is an alignment fix, not a visibility fix:

```python
# forward_validator.py:436-437
# 2026-05-02: Aligned confidence_max with hc_filter.js (0.90) and HF gate
# (0.95). Previous 0.85 cap was set 2026-03-24 on stale, pre-v2 data and
# was the strictest layer in the stack — silently killing winners (see
# shadow_blocked.json: GIGGLEUSDT at confidence 0.902).
"confidence_min": 0.55,
"confidence_max": 0.90,
```

Also add `WINNER_FILTER_STATS["blocked_confidence"]` to the resolver-health surface so we can see how many picks this gate kills per cycle.

---

## Section C — Sequencing & Acceptance Criteria

1. **PR #1 — Resolver Fixes (Section A)** — must merge first. Acceptance:
   - All seven A.x bullets implemented.
   - `tests/test_outcome_resolver.py` covers: retry-cap force-close, intraday lookahead exclusion, empty-OHLC fallback, yf timeout, active-pick zombie, breakeven `status="FLAT"` stamp.
   - 7 days of `resolver_health.json` showing `still_unresolved < 5%` and `noise_share_pct < 10%` on FOREX, COMMODITY, EQUITY, ETF.
2. **PR #2 — Filter Recalibration (Section B)** — gated on PR #1 + 7-day soak. Acceptance:
   - Both `hc_filter.js` *and* `config/hc_gate_params.json` updated together.
   - Playwright test asserting `/audit` FOREX tile renders ≥ 1 pick after deploy (regression catch).
   - Playwright test asserting `/audit/hyrotrader` FOREX/COMMODITY tiles populate (same upstream, different surface).
   - `WINNER_FILTER` cap aligned to 0.90.
3. **PR #3 (optional) — Soft-penalty plumbing for Filter 4** — only if B.4's soft-penalty path is chosen.

---

## Section D — Tests to Add

Located in `tests/` or appropriate package-local `tests/` dirs:

| Test | What it asserts |
|---|---|
| `test_resolver_retry_cap` | Pick with mocked `ohlc_window=None` exits the retry loop after 3 attempts and lands as `resolved_by="outcome_resolver"` (not `_fallback`). |
| `test_resolver_intraday_lookahead` | Entry at 14:00 UTC on day D excludes day-D bar from replay; entry at 00:00 UTC on day D includes it. |
| `test_resolver_empty_ohlc` | `_fetch_yfinance_ohlc_window` returning `[]` does not loop; pick force-closes after `MAX_RESOLVE_RETRIES`. |
| `test_resolver_yf_timeout` | Mock yfinance to sleep 30s; assert `_fetch_yfinance_ohlc_window` returns `[]` within `YF_HISTORY_TIMEOUT + 1` seconds. |
| `test_resolver_active_zombie` | Active non-crypto pick with empty OHLC + valid live price closes via `non_crypto_resolver_fallback` exit reason. |
| `test_breakeven_fallback_status_flat` | Fallback path stamps `status="FLAT"`. |
| `test_hc_filter_per_class_floors` (JS, can use existing harness) | Crypto/Equity/Forex/Commodity floors gate at the new values. |
| `test_hc_filter_tier_contract_nonequity_bypass` | FOREX tier-A/B passes regardless of strategy substring. |
| `test_winner_filter_confidence_alignment` | Pick with `confidence=0.88` passes (was blocked at 0.85). |
| Playwright: `audit_forex_tile_populated.spec.ts` | After mock data load, FOREX tile shows ≥ 1 row on `/audit` and `/audit/hyrotrader`. |

---

## Section E — Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Relaxing filters too soon publishes garbage picks against still-broken WR data | Sequencing rule (Section C) — filters wait on resolver health. |
| `concurrent.futures` timeout leaves zombie threads | Use `ThreadPoolExecutor` as a context manager (it joins on exit); 15s cap is well under any reasonable scan budget. |
| Removing `FOREX_BANNED_SYMBOLS` floods the dashboard with bad picks | Phased unblock (Section B.3) keeps the two worst banned for 60 days. |
| `MAX_RESOLVE_RETRIES=3` is too aggressive and force-closes good picks during legitimate yfinance outages | Env var override (`RESOLVE_MAX_RETRIES`) + structured force-close log + `resolver_health.json` alarm at >5% force-close share. |
| Soft-penalty plumbing scope creep | Make B.4 a separate PR (#3); land the hard-ban removal first. |
| Schema drift between `hc_filter.js` embedded defaults and `config/hc_gate_params.json` | Section B.1 explicitly updates both in the same diff; add a CI check (`tools/check_hc_gate_params_sync.py`) if the drift recurs. |

---

## Section F — Items the Original Audit Missed or Got Wrong

1. **`WINNER_FILTER` is not undocumented.** It lives at `alpha_engine/forward_validator.py:399-461` with a 60-line comment block explaining its history. The audit's recommendation to align its confidence cap is still valid; the framing is wrong.
2. **Per-class WR floor *keys* already exist** in `hc_filter.js:342-345` (Commodity/Futures/Bond/ETF). Only the *values* and the embedded-defaults block at line 23-40 need editing. The audit's diff reads as if it's adding new keys.
3. **`config/hc_gate_params.json` is the canonical source** per the comment at `hc_filter.js:3`. The audit only edits the embedded defaults, which will be silently overridden in the browser. **Both files must be updated together.**
4. **Active-pick `report["sl_hits"]` increment** in audit's Bug 4 diff lumps FLAT outcomes into SL-hit count. Refinement in A.4 above.
5. **`signal.alarm` is the wrong primary fix for Bug 5** — Windows-incompatible and thread-unsafe. `concurrent.futures` should be the primary path; A.3 above re-prioritizes.
6. **No mention of `is_unresolved` returning True for picks with `_resolve_retry_count >= MAX_RESOLVE_RETRIES`** — the audit's diff at lines 460-498 handles the breakeven-equality case but **not** the `exit_raw is None` early-return at lines 475-477. After force-close, `exit_raw` is set, so this is moot, *but* if any caller pre-empts force-close it could regress. Add a defensive guard.

---

## References

- Source files inspected (all on `main` HEAD as of 2026-05-02):
  - `alpha_engine/outcome_resolver.py`
  - `audit_dashboard/hc_filter.js`
  - `alpha_engine/hedge_fund_quality_gate.py`
  - `config/hf_quality_gates.json`
  - `config/hc_gate_params.json`
  - `alpha_engine/data/shadow_blocked.json`
  - `alpha_engine/forward_validator.py`
- Prior reports in scope:
  - `reports/action_B_resolver_2026_04_27.md`
  - `reports/asset_class_independent_recompute_2026_04_27.md`
  - `reports/forex_resolver_ab_2026-02-01_2026-04-29.md`
  - `reports/hedge_fund_performance_review_summary_2026_04_27.md`
  - `reports/SYNTHESIS_6_ANALYSES_AUDIT_WHATIF_2026_04_23.md` (cited in code comments; basis for several pre-v2 filter decisions now flagged for re-audit)
- Original audit: `audit_report.md` (2026-05-01)
- Goal alignment: `AGENTS.md` → "MAJOR GOALS — Goal #1"
