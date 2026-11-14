# Backtest / Simulation Improvement Plan (final_v3, 2026-11-14)

**Purpose:** Fix the backtesting and simulation infrastructure so that any candidate strategy can be tested honestly before deployment.  
**Current state:** 0/23 protocol research candidates passed strict proof; 0/166 live-ledger cells pass all gates.  
**Decision rule:** No algorithm is deployed until it passes all gates in a clean, cost-inclusive, benchmark-relative, out-of-sample test.

---

## D-1. Fix Horizon Harness (highest priority)

**File:** `final_2026_11_14/finpredict-v3/02_tools_guardian/tools/pi_horizon_validation.py`

**Bugs identified (peer adjudication):**

| Bug | Impact | Fix |
|---|---|---|
| `MIN_WINDOWS=4` declared but never enforced | Harness can pass with too few windows | Enforce `n_windows >= MIN_WINDOWS` |
| Multiple-testing only reports counts, no correction | False positive risk | Implement Benjamini-Hochberg + Bonferroni across strategy family |
| Windows split on gaps between adjacent trades, not fixed 60-day calendar intervals | Time leakage, non-independent windows | Use fixed calendar intervals with purge/embargo |
| PnL not netted for execution costs | Overstates profitability | Deduct slippage (5-15 bps/class) + fees from every trade |
| No valid `resolution_method` required (missing on all 3,500 closed rows) | Unresolved picks included as decisive | Require valid `resolution_method` (TP_HIT/SL_HIT/EXPIRED/TIME_EXIT) |

**Acceptance test:** Harness returns 0 passes on known-bad synthetic data (random walk, no edge).

---

## D-2. Fix Gap-Fill Pricing (already applied — verify CI coverage)

**File:** `audit_trail/universal_pick_resolver.py` (modified today)

**Fix:** `_gap_fill_price()` — when a bar gaps through a stop/TP level, fill at the bar open (what actually happens) instead of the level. Default ON via `RESOLVER_GAP_AWARE_FILL=1`.

**Acceptance test:** CI test covers:
- Gap-down bar: stop at 100, open at 95 → fill at 95 (worse for stop)
- Gap-up bar: TP at 110, open at 115 → fill at 115 (better for TP)
- No gap: fill at level (legacy behavior)

---

## D-3. Fix Per-Class Cost Gate Integration (already applied — verify ETF/COMMODITY blocked)

**File:** `tools/hc_gates_python.py` (modified today)

**Fix:** `passes_per_class_cost_gate()` — blocks pick when asset class avg PnL per closed trade < 3x round-trip cost. Fail-open on missing/stale data. `PER_CLASS_COST_GATE_ENABLED=1` default.

**Acceptance test:**
- ETF class (costs 267% of avg PnL) → gate blocks picks
- COMMODITY class (costs 422% of avg PnL) → gate blocks picks
- Missing index → gate passes (fail-open)
- Unknown class → gate passes (fail-open)

---

## D-4. Fix After-Cost Net Per-Trade (already applied — verify non-null)

**File:** `audit_trail/dashboard_generator.py` (modified today)

**Fix:** Fallback to `stamp_class_after_cost` from `tools/per_class_cost_gate.py` when `after_cost_net_per_trade` is None. Previously all 3,500 closed rows had null.

**Acceptance test:** `after_cost_net_per_trade` non-null for ≥95% of closed rows in dashboard payload.

---

## D-5. Add SubQ Comparison for Each Candidate

**Before any candidate is recommended, run SubQ across:**

| Coverage Dimension | CRYPCO Daily Trend | EQUITY Monthly QVM | MUTUAL_FUND NAV Tactical |
|---|---|---|---|
| Universe coverage | Frozen liquid crypto (5-10 symbols) | Fixed large-liquid equity universe (50-100 names) | 20 low-fee index funds |
| Time coverage | Daily ≥3 years | Monthly ≥5 years | Monthly NAV ≥5 years |
| Cost coverage | Taker+funding+spread | Turnover+spread+commission | ER only (no load/12b-1) |
| Regime coverage | Bull/bear/choppy | Bull/bear/low-vol | Market cycles |
| Source coverage | Multi-exchange | Multi-vendor fundamental | Fund issuer NAV data |

**Acceptance test:** SubQ coverage score ≥7/10 for any candidate before deployment consideration.

---

## D-6. Add Walk-Forward with Purged/Embargoed Windows

**Current:** Windows split on gaps between adjacent trades (non-independent).
**Fix:** Fixed 60-day calendar intervals with purge/embargo at boundaries to prevent leakage.

**Acceptance test:** WF windows are non-overlapping, purged, embargoed; benchmark-relative test included.

---

## D-7. Add Block-Bootstrap CI on Net Expectancy

**Current:** Not implemented.
**Fix:** Block-bootstrap 95% CI on net-of-cost expectancy; require lower bound > 0 for any "passing" candidate.

**Acceptance test:** CI excludes zero for any candidate flagged as passing.

---

## D-8. Add DSR with Cumulative Trial Count

**Current:** DSR computed within-run only.
**Fix:** DSR using cumulative trial count across all strategies tested (N≥38 for effective multiple testing).

**Acceptance test:** DSR ≥0.95 required for pass; DSR <0.95 fails even if other gates pass.

---

## D-9. Add PBO Calculation

**Current:** Not consistently applied.
**Fix:** PBO requires ≥2 strategies with n≥20, ≥5 strategies for statistical power; threshold PBO ≤0.10.

**Acceptance test:** PBO ≤0.10 required for pass; PBO >0.10 fails even if other gates pass.

---

## D-10. Add SPA Test (White's Reality Check / Hansen SPA)

**Current:** Not consistently applied.
**Fix:** Family-wise alpha 0.10; corrected p-value required.

**Acceptance test:** SPA p ≤0.10 required for pass.

---

## Candidate Testing Priority

| Priority | Candidate | Asset Class | First Test |
|---|---|---|---|
| 1 | CRYPCO daily 50/200 trend | CRYPCO | SubQ + cost modeling + regime testing |
| 2 | EQUITY monthly QVM | EQUITY | SubQ + cost modeling + mutual fund universe screen |
| 3 | MUTUAL_FUND monthly NAV tactical | MUTUAL_FUND | Build NAV history + benchmark + hard gates |
| 4 | H10 SPY/QQQ RSI(2) | EQUITY | Clean forward OOS (not contaminated) |
| 5 | H22 BTC funding carry | CRYPCO | Expand universe to n≥30 |

**Do not test:** ETF (cohort mismatch), FOREX (negative expectancy), COMMODITY (registry mismatch), BOND (insufficient data), FUTURES (insufficient data), MEME/PENNY_STOCK (blocked).
