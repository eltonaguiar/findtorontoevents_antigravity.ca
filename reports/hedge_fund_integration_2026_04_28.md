# Hedge-Fund Open-Source Integration — Gap Analysis & PR Record

**Date:** 2026-04-28
**Branch:** `feat/hedge-fund-integrations-2026-04-28`
**Authoring agent:** Claude Opus 4.7
**Goal:** Find the 1–3 highest-leverage features in well-known open-source quant repos that this project does NOT already have, integrate them as **opt-in sidecars** (per CLAUDE.md Wire-Up Rule), and document the gap analysis.

## TL;DR

After surveying the user's candidate repos against the existing infrastructure, the gap landscape collapses to: **observability** (per-asset-class tear-sheets) and **portfolio-construction tooling** (covariance shrinkage + HRP/MV optimizers). Two opt-in sidecars shipped:

| Sidecar | Lib | Lib license | Wired? | Production wiring deferred to |
|---|---|---|---|---|
| `tools/quantstats_tearsheets.py` | quantstats 0.0.81 | Apache-2.0 | Opt-in CLI | Future PR (auto-render in `audit-dashboard.yml` cycle, ~1d effort) |
| `tools/pypfopt_allocator.py` | PyPortfolioOpt 1.6.0 | MIT | Opt-in API | Future PR (extend `tools/hrp_allocator.py` with shrinkage option, ~0.5d) |

Three other plausible candidates (Alphalens, mlfinlab fractional differencing, FinRL) were **deliberately deferred** with reasoning below.

## Step 1 — Inventory of candidate repos

### Group A (the user's primary candidates)

| Repo | Distinct features | License | Last commit | Verdict |
|---|---|---|---|---|
| `virattt/ai-hedge-fund` | 19 LLM "investor persona" agents (Buffett/Burry/Wood) + valuation + risk + portfolio-manager + backtester. Hybrid prompt+quant-module. | MIT | Active (830 commits) | **Pass.** Equivalent functionality already present via `incubator/agents/ensemble_evolver.py`, `universal_evolver.py`, `orchestrator.py` (tournament agents). The "personas" are flavor, not new infra. |
| `51bitquant/ai-hedge-fund-crypto` | LangGraph DAG of {Data → Strategy → Risk → Portfolio} nodes. Multi-timeframe Binance integration. MACD strategy node. | MIT | Active | **Pass.** DAG orchestration is structurally similar to existing `genome/genetic_programmer.py` + `orchestrator.py` agent topology. Binance is already covered (per CLAUDE.md API failover rule, 3+ endpoint chain). MACD is already a strategy module. |
| `The-Swarm-Corporation/AutoHedge` (local copy at `./AutoHedge/`) | Director / Quant / RiskMgr / Execution multi-agent on Solana. | MIT | Local copy 2026-04-21 | **Pass.** Solana-only execution layer not relevant; the agent topology is again equivalent to existing universal_evolver / orchestrator. |

**Conclusion for Group A:** all three are LLM-prompt-orchestration frameworks. The existing `universal_evolver` / `ensemble_evolver` / `orchestrator` stack is structurally equivalent (or superior — it's already wired into `dashboard_generator.py` and the strategy registry). Adopting any Group A repo would be a side-grade or downgrade. **Not PR-worthy.**

### Group B (established quant libs the user listed)

| Lib | Status in this repo | Verdict |
|---|---|---|
| QuantConnect Lean | Not installed; too heavy to integrate in-repo (full C# trading engine) | Skip per user instruction (pattern only). |
| Zipline | Not installed; abandoned upstream | Skip. |
| backtesting.py | Not installed; light lib, but `scripts/local_backtest.py` (backtrader) + `alpha_engine/vectorbt_explorer.py` cover the same surface | Skip. |
| bt | Not in requirements; equivalent functionality in `scripts/unified_backtester.py` | Skip. |
| mlfinlab | Audited 2026-04-22 in `reports/HEDGE_LIBS_LEVERAGE_AUDIT_2026_04_22.md` (20/21 orphan rate — "fractional differencing" available but never wired). Wire-Up Rule applies; would need a real production caller. | **Defer.** > 1h to wire into ML pipeline. Out of budget. |
| Alphalens | Not installed; `reports/SYNTHESIS_2026_04_21.md` flagged `elite_score r=−0.001` (this is exactly the IC question Alphalens answers). | **Defer.** > 1h to wire factor-IC into existing scoring (need factor + forward-returns matrix builder). Out of budget; recommended next PR. |
| PyPortfolioOpt | Not installed; **gap confirmed**. Hand-rolled `tools/risk_parity_allocator.py` + `tools/hrp_allocator.py` exist but use raw Pearson correlation (unstable at small n; we have n=17 BOND, n=83 ETF). Neither is wired to production yet either. | **Ship as opt-in sidecar.** Adds Ledoit-Wolf shrinkage + EfficientFrontier + scipy-grade HRP clustering. |
| QuantStats | Not installed; **gap confirmed**. `reports/hedge_fund_performance_review_*.md` is hand-typed every cycle. No HTML tear-sheets. CRYPTO MDD-178% finding could have been auto-surfaced weeks earlier. | **Ship as opt-in sidecar.** Drop-in HTML tear-sheets per asset class. |
| FinRL | Not installed; RL agent infra. | Skip per user instruction (pattern only, heavy). |
| TA-Lib | Already standard in repo. | N/A. |
| CCXT | Already in scope via `binance_data_provider`-style modules + Binance failover chain. | N/A. |
| empyrical | Not installed; superset wrapped by QuantStats anyway. | Skip (covered by QuantStats). |
| riskfolio-lib | Declared in `requirements.txt`-related notes, but `grep` finds zero direct imports. | Skip (overlaps PyPortfolioOpt and skfolio; would only add tail-risk optimizer that is not the bottleneck). |

## Step 2 — Gap analysis (by leverage / cost / fit)

| Candidate feature | Missing? | Integration cost | Leverage | Decision |
|---|---|---|---|---|
| QuantStats HTML tear-sheet per asset class | Yes (no HTML reports anywhere; only hand-written `.md`) | LOW (drop-in pip + ~250 lines wiring) | HIGH (would have surfaced CRYPTO MDD-178% the day it crossed any threshold; auto-replaces hand-typed sections of `hedge_fund_performance_review_*.md`) | **SHIP** |
| PyPortfolioOpt HRP w/ Ledoit-Wolf shrinkage | Partially — hand-rolled HRP exists but uses raw Pearson | LOW (drop-in pip + ~150 lines wiring) | MEDIUM-HIGH (small-n BOND/ETF allocations are currently unstable; hedge-fund review explicitly calls out missing risk-parity-by-Sharpe allocator) | **SHIP** as opt-in extension |
| Alphalens factor IC | Yes | MEDIUM (~2-3h: need to build `factor + forward_return` panel from picks ledger first) | HIGH (`elite_score r=-0.001` is a known live finding) | **DEFER** to next PR — over the 1h-per-feature budget rule |
| mlfinlab fractional differencing | Yes | MEDIUM-HIGH (need a production ML caller; 2026-04-22 audit found 20/21 orphan rate on past attempts) | MEDIUM (only relevant once an ML feature path consumes it) | **DEFER** until ML feature path lands a real caller |
| virattt persona agents / 51bitquant DAG / AutoHedge | Already covered | N/A | LOW (side-grade) | **SKIP** |
| FinRL RL stack | Yes | HIGH (multi-week) | UNCLEAR (no RL training data pipeline exists) | **SKIP** per user instruction |
| backtesting.py / bt | Already covered | N/A | LOW | **SKIP** |
| Black-Litterman optimizer | Yes (PyPortfolioOpt provides it) | LOW (we get this for free with the PyPortfolioOpt install, but no production caller) | LOW (no view-source pipeline yet) | **SKIP** for this PR — defer to a future PR that needs Bayesian view-blending |

## Step 3 — Picks (ranked)

### #1 — `tools/quantstats_tearsheets.py` (QuantStats)

**Why this is the highest-leverage drop-in available:** the existing `reports/hedge_fund_performance_review_summary_2026_04_27.md` is the *exact* product QuantStats auto-generates, except it's hand-typed and only refreshed when a human runs the cycle. A standing tear-sheet would have flagged CRYPTO MDD-178% the moment it crossed 50%, instead of surfacing in a manual review cycles later.

**What it ships:**

- `load_closed_picks(path)` — supports all three pick-ledger shapes in this repo (`audit_dashboard/data/dashboard_data.json`, `audit_trail/data/dashboard_payload.json`, `audit_trail/data/universal_resolved_picks.json`).
- `picks_to_daily_returns(picks, asset_class)` — aggregates per-pick `pnl_pct` to a daily-indexed pandas Series. **Hardened against the cycle10 unit-mismatch bug** (`feedback_cycle10_unit_mismatch_bug.md`): raises if >1% of picks have `|pnl_pct|>5`, which would imply integer-percent units.
- `write_all_tearsheets(data_path, output_dir)` — emits one HTML tear-sheet per `asset_class` (EQUITY, CRYPTO, FOREX, COMMODITY, ETF, BOND) plus an aggregate `ALL`.
- CLI: `python tools/quantstats_tearsheets.py --asset-class EQUITY --asset-class CRYPTO`.

**Why opt-in (not auto-wired in this PR):** per CLAUDE.md Wire-Up Rule + user constraint ("DO NOT modify production pick-generation, score-generation, or active-gate code paths in this PR. Sidecar / opt-in only."). Production wiring (a step in `audit-dashboard.yml`) is a separate PR.

### #2 — `tools/pypfopt_allocator.py` (PyPortfolioOpt sidecar)

**Why ship alongside the existing hand-rolled HRP:** the hand-rolled `tools/hrp_allocator.py` is correct but uses raw Pearson correlation, which is unstable at the small per-class sample sizes we have (BOND n=17, ETF n=83). PyPortfolioOpt provides:

- `risk_models.CovarianceShrinkage(...).ledoit_wolf()` — well-conditioned covariance at small n.
- `HRPOpt` — SciPy single-linkage HRP (faster, more extensible).
- `EfficientFrontier` — mean-variance with shrinkage cov.

The sidecar is **import-safe even when PyPortfolioOpt isn't installed** (cvxpy is a transitive dep that can fail on first install on systems without a C compiler). `is_available()` is the probe; wrapper functions raise with an install hint if missing.

**API parity with the hand-rolled allocator:** `hrp_weights(returns_df) -> dict[str, float]` matches the shape of `tools/hrp_allocator.py:hrp_weights`, so a future production caller can A/B them with one import swap.

### Deferred (worth their own PRs)

- **Alphalens factor-IC report** — factor-quality measurement for `elite_score`, `ml_score`, `confluence_score`. Highest-leverage *next* PR.
- **mlfinlab fractional differencing** — gated on an ML feature consumer; can't ship without violating the Wire-Up Rule's anti-orphan stance.
- **PyPortfolioOpt Black-Litterman** — gets installed for free with this PR but isn't exposed because we have no view-source pipeline yet.

## Step 4 — Wiring plan (production)

Per CLAUDE.md "New integration modules must include at least one caller in the production pick-generation or scoring path — or be explicitly labeled opt-in with a wiring plan."

This PR is the **opt-in sidecar** path. The production wire-ups are scoped here for the follow-up PR(s):

### QuantStats wire-up (target: PR within 1 week of merge)
- **Target caller:** new step in `.github/workflows/audit-dashboard.yml` after the "Generate dashboard data" step — call `python tools/quantstats_tearsheets.py --out reports/tearsheets/`.
- **Output:** uploaded as workflow artifact + linked from `updates/index.html` "What's New" panel.
- **Acceptance:** every audit-dashboard cycle produces 7 HTML files (6 classes + ALL). MaxDD on each is computable from JS by parsing the QuantStats summary table.

### PyPortfolioOpt wire-up (target: PR within 2 weeks of merge)
- **Target caller:** new optional `--shrinkage-cov` flag on `tools/hrp_allocator.py`'s CLI that, when set, delegates to `tools/pypfopt_allocator.py:hrp_weights` and emits the same JSON shape.
- **Acceptance:** A/B comparison row in `audit_dashboard/data/portfolio_b_*.json` showing both raw-Pearson HRP and shrinkage-HRP weights for each asset class on the same input.

## Step 5 — Tests

- `tests/test_quantstats_tearsheets.py` — 11 unit tests covering pick-loader shape detection, daily-return aggregation, asset-class filtering, the unit-mismatch guard, and the render path (with QuantStats stubbed so the suite passes even on a slim CI image).
- `tests/test_pypfopt_allocator.py` — 8 unit tests: import-safety, diagnostic_report shape, RuntimeError raised when unavailable, and (when pypfopt IS installed) Ledoit-Wolf cov shape, HRP weights summing to 1, low-vol asset preference, mean-variance happy path, target-conflict ValueError.

Run:
```
python -m pytest -q tests/test_quantstats_tearsheets.py tests/test_pypfopt_allocator.py
```

## Step 6 — Tradeoffs (what was deliberately NOT integrated)

1. **Alphalens** — not shipped this PR despite being arguably the single highest-value remaining gap (live `elite_score r=-0.001` finding). Reason: building the factor + forward-return panel from `dashboard_data.json` is a > 1h job and the user budget cap is 4h total. Recommended as the immediate next PR.
2. **mlfinlab fractional differencing** — would land orphaned per the 2026-04-22 audit (20/21 historical orphan rate on hedge-fund-lib integrations); the Wire-Up Rule effectively blocks it until an ML feature path needs it.
3. **Group A repos (virattt / 51bitquant / AutoHedge)** — all three are LLM-agent orchestration frameworks structurally equivalent to the existing `universal_evolver` / `ensemble_evolver` / `orchestrator` stack. Adoption would be a side-grade.
4. **Black-Litterman** — gets pulled in by the PyPortfolioOpt install, but no production caller exists for "view sources" yet, so it's left unwired.
5. **CLA / cvxpy-heavy paths** — exposed via `mean_variance_weights` only; not a default. Cvxpy installs fragile across CI environments.

## Real-data smoke-test findings (2026-04-28 session)

Running `tools/quantstats_tearsheets.py` end-to-end against `audit_dashboard/data/dashboard_data.json` (3,500 closed picks) revealed a **mixed-unit ledger** that confirmed the cycle10 unit-mismatch bug pattern. Auto-detect output:

| Class | n | Detected pnl_pct unit | n_days | Compound cum return |
|---|---:|---|---:|---:|
| EQUITY | 381 | percent | 43 | +156.06% |
| CRYPTO | 1590 | percent | 24 | -4.86% |
| FOREX | 802 | decimal | 34 | absurd (1bp resolver flicker artifact, see Goal #1) |
| COMMODITY | 622 | decimal | 34 | absurd (same artifact) |
| ETF | 83 | percent | 30 | +14.20% |
| BOND | 17 | decimal | 13 | -99.78% |

EQUITY/CRYPTO/ETF/BOND auto-detection works cleanly. FOREX/COMMODITY tear-sheet numbers will **stay garbage until `alpha_engine/outcome_resolver.py:97 + :384-405` lands** (the resolver bug per CLAUDE.md Goal #1 / `reports/action_B_resolver_2026_04_27.md`). The tear-sheet is faithfully reflecting the ledger's existing contamination, not introducing a new bug. After the resolver fix, FOREX/COMMODITY tear-sheets become the cleanest available diagnostic.

The actual HTML render produces a 336 KB file with the standard QuantStats panels (cumulative, monthly heatmap, MaxDD, rolling Sharpe, distribution, etc.). Verified against real EQUITY data.

## References

- `reports/hedge_fund_performance_review_summary_2026_04_27.md` — the hand-typed report this work targets to auto-generate.
- `reports/SYNTHESIS_2026_04_21.md` — `elite_score r=-0.001` finding (Alphalens deferral motivation).
- `reports/HEDGE_LIBS_LEVERAGE_AUDIT_2026_04_22.md` — 20/21 orphan rate, source of the Wire-Up Rule.
- `reports/deep_dive_crypto_mdd_reduction_2026_04_28.md` — CRYPTO MDD-178% rescue plan (the diagnosis QuantStats automates).
- `tools/risk_parity_allocator.py`, `tools/hrp_allocator.py` — existing hand-rolled allocators that PyPortfolioOpt complements (does NOT replace).
