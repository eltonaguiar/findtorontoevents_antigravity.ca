# PRODUCTION READINESS FRAMEWORK

**Version:** 1.0
**Created:** 2026-05-31
**Status:** CANONICAL — companion to `docs/PERFORMANCE_CHARTER.md`. The Charter defines the *tier thresholds*; this document defines the *statistical-validity gates* and the operational *checklist* that must be cleared before any strategy is sized up with real capital.
**Trigger:** user idea 2026-05-31 #1 — *"even if we back-test, we aren't sure how to properly measure future performance, and how many trades would be considered a statistically valid edge? How can we determine if a strategy is ready for production?"*

---

## §1 The seven gates of production readiness

A strategy is "ready for real money" only when ALL seven gates clear simultaneously on the most recent rolling window (≤90 days) AND a separate, frozen, multi-month walk-forward window. Single-window passes are not promotable.

| # | Gate | Threshold | Source code |
|---|---|---|---|
| 1 | Sample size `n` | n ≥ 100 closed clean picks per class (Charter §10); n ≥ 20 per strategy for SPA inclusion | `money_ready_verdict.py:MIN_N_CLASS=50` (verdict floor) / Charter §10 (promotion floor 100) |
| 2 | Tier metrics (PF / WR / MDD) | Tier 2 floor: PF ≥ 1.5, WR ≥ per-class floor, MDD ≤ 20% | `CLASS_WR_FLOORS`, Charter §2 |
| 3 | DSR (Deflated Sharpe Ratio) | DSR probability ≥ 0.95 with `nb_trials` correction reflecting actual #strategies tested | `DSR_THRESHOLD=0.95`, `NB_TRIALS_BY_CLASS` |
| 4 | SPA (White's Reality Check) | family-wise p ≤ 0.10 with ≥ 1 strategy passing at α=0.10 | `SPA_ALPHA=0.10`, `MIN_N_STRATEGY=20` |
| 5 | PBO (Probability of Backtest Overfit) | PBO ≤ 0.55; requires ≥ 5 strategies for meaningful power (Bailey et al. 2016) | `PBO_THRESHOLD=0.55`, `MIN_STRATEGIES_FOR_PBO=5` |
| 6 | Symbol/source concentration | top symbol ≤ 60% (COMMODITY 85%); top source ≤ 40% (COMMODITY 60%) | `MAX_SYMBOL_CONCENTRATION`, `MAX_SOURCE_CONCENTRATION` |
| 7 | Net-of-slippage expectancy | `adj_win × WR − adj_loss × (1−WR) > 0` after per-class slippage bps | `SLIPPAGE_BPS`, `expectancy_ok` |

Risk overlay (Charter §7) is enforced independently — it can veto a promotion but never substitute for the seven gates.

## §2 How many trades constitutes a statistically valid edge?

The honest answer is *it depends on effect size, but here are the floors this repo enforces*:

| Tier | Minimum n (closed clean) | Statistical rationale |
|---|---|---|
| Class-level **verdict** | 50 | `MIN_N_CLASS` in `money_ready_verdict.py`. Below this the class shows `INSUFFICIENT_DATA` regardless of metrics. |
| Strategy-level **SPA inclusion** | 20 | `MIN_N_STRATEGY`. Bootstrap stability collapses below ~20. |
| Promotion to **Tier 2 live capital** | 100 | Charter §10. Wilson 95% CI half-width on WR is ±~10pp at n=100, ±~7pp at n=200, ±~5pp at n=400. |
| Promotion to **Tier 1** | 200 | Charter §2. |
| PBO/CSCV detection power | ≥ 5 strategies | Bailey, López de Prado, Borwein, Zhu (2016) — below 5 strategies the PBO statistic is essentially random. |

**Effect-size sanity (Wilson 95% lower bound):** a strategy with observed WR = 55% needs **n ≥ 100** before the Wilson 95% lower bound clears the 50% break-even line for a symmetric payoff. For asymmetric payoffs (e.g. PF target 1.5 with avg_win = 2×avg_loss), break-even WR is ~33% and a 55% point estimate clears at n ≥ ~30 — but the Charter still requires n ≥ 100 to suppress regime-luck.

## §3 OOS validation requirements

1. **Walk-forward** (Charter §9): 4 overlapping sleeves, quarterly rebalance. Train 2012-2018 / Validate 2019-2021 / Test 2022-2025.
2. **No in-sample backtests** may be cited as "proven edge."
3. **OOS sample-size floor:** test window must contribute ≥ 100 closed picks OR ≥ 30% of the total `n` used in the readiness verdict, whichever is larger.
4. **DSR with correct `nb_trials`:** the `NB_TRIALS_BY_CLASS` correction (CRYPTO=14, FOREX=6, COMMODITY=3) prevents the *familywise inflation* that comes from testing many sleeves on the same data. **`nb_trials = 1` is statistically meaningless** for any real-money decision.

## §4 The "ready for real money" checklist

A PR or strategy promotion request must check off **every** box. Anything unchecked blocks promotion.

- [ ] `pf_registry.by_asset_class_policy_clean_net` shows the strategy in a class with `n_resolved ≥ 100` for the relevant window.
- [ ] `money_ready_verdict.json` returns `verdict=MONEY_READY` (NOT `WATCH`, NOT `INSUFFICIENT_DATA`, NOT `NOT_READY`).
- [ ] DSR ≥ 0.95 with `nb_trials` ≥ count of strategies actually tested in the same class (no `nb_trials=1`).
- [ ] PBO ≤ 0.55 measured with ≥ 5 strategies.
- [ ] SPA family-wise p ≤ 0.10 with ≥ 1 strategy passing.
- [ ] Symbol concentration ≤ 60% (or 85% for COMMODITY); source concentration ≤ 40% (or 60% for COMMODITY).
- [ ] Walk-forward OOS test window contains ≥ 100 closed picks (Charter §9).
- [ ] Resolver path is correct for the asset class (`outcome_resolver.PNL_WIN_THRESHOLD_BY_CLASS` applied; `swing_resolver.py` used for swing; no leakage signals such as EXPIRED→WON mislabels, duplicate signal-timestamps, look-ahead in features).
- [ ] Recency check: the **14d/48h panels** (`audit_dashboard/data/pick_summary_stats_{14d,48h}.json`) corroborate the 90d numbers — no collapse in last 14d.
- [ ] No P0 leakage signals open in `reports/STOP_*.md` for the relevant class.
- [ ] Risk caps (Charter §7) implemented in the live wrapper, not just documented.
- [ ] Charter §8 promotion process completed: 3 consecutive months of clean Tier-2 metrics in walk-forward + n ≥ 100.

## §5 Cross-check against today's verdict (2026-05-31)

Snapshot of `audit_dashboard/data/money_ready_verdict.json` generated 2026-05-30T23:05:42Z:

| Class | n_resolved | WR | PF | verdict | gate failure |
|---|---|---|---|---|---|
| CRYPTO | 327 | 37.6% | 0.89 | NOT_READY | PF<1.5, WR<50%, MDD=1.0 (max), source concentration 57% |
| EQUITY | 39 | 28.2% | 0.15 | INSUFFICIENT_DATA | n<50, WR<52%, PF<1.5 |
| FOREX | 28 | 28.6% | 0.04 | INSUFFICIENT_DATA | n<50, all metrics fail |
| COMMODITY | 9 | 44.4% | 1.81 | INSUFFICIENT_DATA | n<50 (only gate failed; PF passes T2 floor) |
| FUTURES | 12 | 16.7% | 0.54 | INSUFFICIENT_DATA | n<50, top_source 91.7% (single-source) |
| ETF | 4 | 50% | 0.48 | INSUFFICIENT_DATA | n<50 |
| BOND | 0 | — | — | INSUFFICIENT_DATA | n=0 |
| PENNY_STOCK | 1 | 0% | 0 | INSUFFICIENT_DATA | n<50 |
| UNKNOWN | 6 | 66.7% | 2.63 | INSUFFICIENT_DATA | n<50, unclassified |

**Result:** 0 of 9 classes pass the seven gates. The framework therefore **confirms today's verdict of NO_EDGE**. No class is currently promotable.

## §6 Verdict per user idea (and tier label)

The user's question is a *meta-policy* question, not a strategy backtest. There is no per-strategy n / WR / PF to compute. The verdict applies to the *framework itself*:

- **Verdict tier:** N/A (meta) — categorized as **INSUFFICIENT_N** for the per-asset-class tier system (n=0 for the framework as a "strategy") and **NO_EDGE** for the current production-readiness verdict across classes (0/9 pass).
- **Confidence:** HIGH — every gate value above is sourced directly from `money_ready_verdict.py` constants and the latest verdict JSON; no model-fabricated numbers.

## §7 Recommended next step

1. **Adopt this framework** as the canonical companion to `docs/PERFORMANCE_CHARTER.md`. Cite both in every promotion PR.
2. **Wire the §4 checklist into PR templates** for any branch touching `BLOCKED_SOURCE_SYSTEMS`, `quality_gates.py`, or `money_ready_verdict.py`.
3. **No size-ups** until at least one class clears all seven gates on both a rolling-90d AND a frozen walk-forward window. Current count of classes that pass: 0/9. **Recommendation: continue plumbing work** (resolver intrabar, dormant backtest edges per MEMORY 2026-05-31 — money-ready bottleneck is plumbing, not strategies) **rather than further strategy invention.**
4. **Track sample-size growth** weekly: the binding constraint for 8 of 9 classes is `n_resolved < 50`. Without more closed clean picks, no statistical gate (DSR/SPA/PBO) can produce a meaningful pass.

## §8 References

- `docs/PERFORMANCE_CHARTER.md` v1.0 — tier thresholds (§2), risk caps (§7), walk-forward standard (§9)
- `alpha_engine/money_ready_verdict.py` lines 135–234 — all gate constants
- `audit_dashboard/data/money_ready_verdict.json` — live verdict
- `audit_dashboard/data/pf_registry.json` — per-class policy-clean net stats
- Bailey, López de Prado, Borwein, Zhu (2016) — PBO/CSCV
- Bailey & López de Prado (2014) — Deflated Sharpe Ratio
- Hansen (2005) — SPA / White's Reality Check
- CLAUDE.md MAJOR GOAL #1 — tier definitions referenced by this framework

## §9 Version history

| Version | Date | Author | Notes |
|---|---|---|---|
| 1.0 | 2026-05-31 | Claude Opus 4.7 | Initial framework — codifies the seven gates already implemented in `money_ready_verdict.py` into a single human-readable checklist. Closes user idea #1 of 2026-05-31. |
