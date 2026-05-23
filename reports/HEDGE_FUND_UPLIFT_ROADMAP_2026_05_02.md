# Hedge-Fund-Grade Uplift Roadmap — 2026-05-02

**Author:** Claude Opus 4.7 — synthesizing across 4 reviewer sources + 2 active branches + Mercury 2 wishlist
**This PR (PR-A):** highest-leverage starting point — `transaction_cost_model` wired into `dashboard_generator._normalize_pick` behind `HF_NET_PF_ENABLED` env flag (default-OFF).

## Two competing branches, one common goal

| Branch | PR | Quality |
|---|---|---|
| `feat/hedge-fund-level-upgrade` (Xiaomi MIMO) | **#621** | 11 ORPHAN modules, 0 tests, 2 unfixed Codex bot runtime bugs (Holm + NameError), empty 0-byte docs file, TODO list instead of Wiring Plan |
| `copilot/research-revolutionary-strategies` (Cloud Agent) | **#626** | 4 modules + 8 personas + 20 unit tests + opt-in sidecar with explicit Wiring Plan + real backtest on 7,445 picks |

**Direct conflict:** both define `statistical_rigor.py` in different paths. PR #626 is the disciplined version.

## Concrete empirical findings from PR #626 backtest

1. Only `multi_asset_cot` (n=41, PF 8.03, p<10⁻⁴) survives BH-FDR at 5%
2. **100% of FOREX wins are <5 bps; 100% of EQUITY wins are <10 bps** (resolver flicker)
3. **Transaction-cost overlay flips every class except CRYPTO from gross-positive to net-negative** at literature-prior slippage
4. HRP returned 20% across all 5 sources (degenerate)
5. Vol-targeting on raw closed-pick stream made it worse (PF 0.41→0.37)

## Multi-PR roadmap (sequenced for max leverage)

| Phase | PR | Source | Wire-in | Tests | Flag |
|---|---|---|---|---|---|
| Phase 0 (done) | #617 | normalize_exit_reason regression fix | quality_gates.py | yes | n/a (bug fix) |
| Phase 0 (done) | #618 | UEPS comment leak + glossary | template.html | n/a (UI) | n/a |
| Phase 0 (done) | #599 | UEPS gate bypass | quality_gates.py | 12 | UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED |
| Phase 1 (open) | #610 | resolver v2.1 bug fixes | outcome_resolver.py | 9+29 | n/a (bug fix) |
| Phase 1 (open) | #626 | hedge-fund foundation | opt-in sidecar w/ Wiring Plan | 20 | per-module |
| **Phase 2 (this PR)** | **PR-A** | **transaction_cost_model** | **dashboard_generator._normalize_pick** | **42** | **HF_NET_PF_ENABLED** |
| Phase 3 (next) | PR-B | PR #626 wire-in: statistical_rigor + decay_tracker + reconciliation_report | dashboard_generator | TBD | per-module |
| Phase 4 | PR-C | liquidity_adjusted_costs (Mercury 2) | extends PR-A | TBD | LIQ_COSTS_ENABLED |
| Phase 5 | PR-D | walk_forward_validator (extend anti_overfit_validator) + Holm bug fix | tools/run_anti_overfit_audit.py | TBD | n/a (CLI) |
| Phase 6 | PR-E | regime_aware_gates | quality_gates.py:passes_active_gate | TBD | REGIME_GATE_ENABLED |
| Phase 7 | PR-F | risk_adjusted_metrics + atr_adaptive_stops (NameError fix) | dashboard + trade_geometry | TBD | per-module |
| Phase 8 | PR-G | cross_asset_correlation_engine | dashboard concentration panel | TBD | CONCENTRATION_PANEL_ENABLED |
| Phase 9 | wishlist | sentiment_signal_fusion / drift_detection / stress test / SHAP / compliance | per-module | TBD | per-module |

## Cross-cutting principles (per CLAUDE.md)

1. **Wire-Up Rule:** every PR ships its module wired into a production caller, OR is opt-in sidecar with explicit `## Wiring Plan` block.
2. **Default-OFF + 14d shadow:** every gate/scoring change starts default-OFF behind env flag for 14 days.
3. **No bundle PRs.** Each PR-A through PR-G is its own focused branch with tests + flag.
4. **No expansion of `BLOCKED_SOURCE_SYSTEMS`** without `STRATEGY_INVESTIGATION_BEFORE_KILL.md` + `MUTATION_THREE_AXIS_PROTOCOL.md` (the empirical BH-FDR finding starts that investigation).

## Recommendation

1. **Close PR #621** as superseded by the decomposition path
2. **Review and merge PR #626** (fix Codex Holm bug first)
3. **Merge this PR-A** — net-of-cost overlay wired, default-OFF, 42 tests
4. **Operator merges PR #610** (resolver v2.1) when ready

## References

- `reports/PR_621_REVIEW_2026_05_02.md` — 4-reviewer subagent verdict
- `reports/feedback/{deepseek,cerebras-qwen}-pr621.md` — adversarial AI reviews
- `reports/strategy_research_using_framework_2026_05_02.md` (in PR #626) — backtest findings
- `reports/PR_609_KIMI_DECOMPOSITION_2026_05_02.md` — earlier decomposition pattern
- `reports/UEPS_GATE_FIX_PLAN_2026_05_01.md` — earlier UEPS bypass plan
- `reports/PR_626_REVIEW_2026_05_02.md` — Cloud Agent foundation review
- `reports/INBOX_TRIAGE_2026_05_02.md` — open-PR inbox triage

---

## Grok's 6-step Master Audit Framework (Phase 10+)

Per Grok's external review (2026-05-02), once Phases 1-9 complete the system should run a structured **Master Audit Script** to validate institutional-grade discipline. This is the "external quant due-diligence" equivalent — 1-2 weeks of focused work after the wired modules are in production.

### Step 1 — Data & Labeling Integrity (foundation, fix first)
- **Check:** outcome_resolver.py logic post-fix; resolver-noise % per class/symbol/strategy
- **Metric target:** <10-20% noise per class
- **Status:** PR #610 (resolver v2.1) addresses this; awaiting operator merge

### Step 2 — Strategy/Portfolio Attribution & Decomposition
- **Break down PnL by:** strategy × symbol × LONG/SHORT × regime × entry-time cohort × holding period
- **Tools available:** `attribution_tracker.py`, `reporting/`, `ensemble/`
- **Action:** kill or demote anything < minimum edge (WR LB <50%, PF<1.1 after costs, negative contribution)
- **Wire to PR #626 BH-FDR finding:** rapid_fire (PF 0.158, p=1.0) is the cleanest demote candidate

### Step 3 — Statistical Rigor & Overfit Detection
- Purged K-fold CV + embargo
- Walk-forward optimization (out-of-sample Sharpe positive?)
- Monte Carlo / bootstrap deflated Sharpe
- Stress tests (crisis periods, slippage sensitivity)
- **NEW gate:** "live parity" — backtest vs. realized correlation >0.7
- **NEW gate:** auto-demote on rolling degradation
- **Status:** Phase 5 PR-D extends `anti_overfit_validator.py`

### Step 4 — Risk & Portfolio Construction
- Position sizing via Kelly fraction (cap ~0.25)
- Correlation matrix, sector/symbol caps, drawdown halts
- Portfolio-level equity curve simulation (not summed trades)
- Regime-aware allocation wired to live picks
- Funding-rate handling for crypto
- **Status:** Phase 6-8 PRs cover this; Mercury 2's `vol_targeted_sizer` is the wire-target

### Step 5 — Holistic Edge Validation
- Build "clean book" (post-resolver-fix, post-cull, post-gates)
- Benchmark vs. buy-hold per asset class, naive momentum, ETFs
- Information coefficient (IC) decay analysis
- Reserve last 1-3 months as true OOS
- **Status:** Phase 9 work; needs Phase 1-8 baseline first

### Step 6 — Process & Operational Review
- CI/CD freshness (models <7d old)
- Audit trail completeness
- Alerting on 7d/30d drops (drift_detection_monitor — Mercury 2)
- Update `PERFORMANCE_CHARTER.md` with current gates
- Multi-agent review with human final veto on promotions
- **Status:** drift_detection_monitor in Phase 9 wishlist

### Master Audit Script (Phase 10)

A single tool that runs the full pipeline: ingest → resolve → gate → attribute → metrics → report.
- Weekly canonical recompute
- Versioned "clean ledger" snapshots
- Defensible proof of edge per asset class

**Sequence:** PRs run sequentially (Phase 1 → 9), then this Master Audit becomes the perpetual operator-facing verification harness.

## Phase 10+ deferred items from external reviews

- CI freshness checks for models/data (Grok)
- Adversarial validation (Grok / partly in PR #626 personas)
- Live vs snapshot PnL parity gate (Grok)
- Funding rates ingestion (Mercury 2 / crypto)
- Monte Carlo simulations (Grok)
- CTA ETF replication for commodities (Grok — fallback when commodity edge thin)
- Prediction-market / verified-pro hybrid rows (Grok)
- SHAP explainability for top-ranked picks (Mercury 2)
- Compliance guards (position size > 5% ADV → market-impact flag) (Mercury 2)
