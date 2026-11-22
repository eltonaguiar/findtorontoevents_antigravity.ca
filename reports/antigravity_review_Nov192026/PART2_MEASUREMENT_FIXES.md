# Part 2 · P2-3: Measurement-Fix Engineering Spec

**Author:** GitHub Copilot / Mercury-3 AI (`githubcopilot-mercury3AI`)
**Date:** 2026-11-22 03:30 EST

This spec covers the **three measurement blockers** identified in Part 1 — they make the gates untrustworthy regardless of strategy quality. Each fix is scoped to a file and has an acceptance test.

---

## Fix 1 · CRYPTO intrabar-vs-daily PF inflation (0.29×)

**Problem:** legacy daily-granularity resolution overstates edge ~3.4× (money_ready_verdict `intrabar_daily_divergence`: daily PF 0.26 vs honest intrabar PF 0.92 on n=3,726).

**Files:** `alpha_engine/money_ready_verdict.py` (produces verdict), `alpha_engine/audit3_selection_alpha.py` (uses intrabar truth).

**Action:**
1. Make `intrabar_truth` the **only** scoring source for CRYPTO aggregate verdicts (it already is the `sizing_source`; extend to `verdict_basis`).
2. Add a **dashboard flag** when `pf_inflation_x < 0.5` (i.e., daily/raw PF is ≥2× the intrabar truth) — display "INFLATED-SOURCE" next to the class.
3. Acceptance: for CRYPTO, `verdict_basis == "intrabar_truth"` and the `/audit` headline PF matches the intrabar PF (0.92), not the daily PF.

---

## Fix 2 · ETF slippage model (234% of per-trade PnL)

**Problem:** measured ETF slippage ≈ 234% of per-trade PnL (monthly cadence) — it is impossible for any ETF cell to pass G7 (cost gate).

**Files:** `alpha_engine/audit3_tribunal.py` (cost model `class_cost_pct` / `slippage_validation`), backtest frictions in `tools/backtest_cost_adjusted_wf.py`.

**Action:**
1. Re-measure ETF fill cost on a realistic cadence (daily/weekly, not monthly) — the 234% figure likely reflects cadence mismatch, not true cost.
2. If true cost is genuinely ~2.3× trade PnL, **stop emitting ETF picks** (they cannot be net-positive) OR switch the ETF sleeve to a lower-turnover/carry profile.
3. Acceptance: ETF `mean_cost_pct` drops under 50% of per-trade PnL, OR the class is put on an explicit no-emit list.

---

## Fix 3 · FOREX price backfill (fx_prices stale to 2026-02-09)

**Problem:** FX price history is stale ~9 months; `POD-FOREX-USDJPY-MOMENTUM` (Sharpe 2.02, n=42) cannot be forward-tested and the bid cannot measure FX.

**Files:** `tools/fx_backfill.py` (exists — needs to run), `alpha_engine/audit3_selection_alpha.py` (reads fx_prices).

**Action:**
1. Run `tools/fx_backfill.py` to backfill `fx_prices` to current.
2. Re-run the tribunal so FOREX cells get measured bars.
3. Acceptance: audit3 coverage panel shows FOREX ≥ 90% instruments measured (vs 12/17 today), and the forward clock gains FOREX rows.

---

## Fix 4 (bonus) · Dashboard freshness & shared denominator

**Files:** `audit_trail/dashboard_generator.py`, `audit_dashboard/data/dashboard_data.json` (currently 2026-10-19).

**Action:** regenerate `dashboard_data.json` from the canonical resolved view, and surface the ledger verdict (KILL/WEAK) on `/audit`. Acceptance: dashboard `generated_at` within 24h of ledger, and per-class WR/PF match the ledger.

---
*Not investment advice. File pointers verified in repo on 2026-11-22.*
