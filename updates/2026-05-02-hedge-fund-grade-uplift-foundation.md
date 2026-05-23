# 2026-05-02 — Hedge-Fund-Grade Audit Uplift: Foundation PR

**Branch:** `copilot/research-revolutionary-strategies`
**Plan source:** the `<plan>` block authored in the previous session and re-supplied in this session's problem statement (Themes A-F + 8 new personas).
**Status:** opt-in sidecar — no production behaviour changes; new modules ready for wire-up in the follow-up PRs sequenced in the plan.

## What was broken

The plan from the prior session enumerated six revolutionary themes:

| Theme | Already landed before this PR? | Gap |
|---|---|---|
| A — Constant-Vol Risk Engine | Substantially: `alpha_engine/vol_targeted_sizer.py`, `regime_position_sizer.py`, `kelly_position_sizer.py` exist | Not wired into production scoring path; no transaction-cost layer |
| B — Resolver / Settlement SLA | Substantially: `outcome_resolver.py` v2 with asset-class-gated thresholds (lines 97-126) | No reconciliation report surface for the audit page |
| C — Regime-stratified performance | Partially: `regime_researcher.py`, `regime_terminal` source-system | No HMM with conditional Sharpe; no per-regime audit blocks |
| D — HRP allocator + factor sleeves | **Missing entirely** | No HRP module; no per-class factor sleeves |
| E — Hybrid swarm orchestration | Partially: 19 fixed personas in `ml_crypto_predictor/researchers/` | No dynamic-spawn → fixed-handoff bridge; the proposed personas didn't exist |
| F — Statistical rigor | Partially: `deflated_sharpe.py` exists | No bootstrap CIs, no BH-FDR, no PSR, no decay tracker |

The plan's TL;DR: *"If only one thing ships from this plan: constant-vol risk targeting + resolver fix + bootstrap CIs on every metric."* Vol-targeting and resolver are landed; **bootstrap CIs were the highest-leverage missing piece**.

## What changed

### New foundation modules in `alpha_engine/`

| File | Purpose | Wire-up target (next PR) |
|---|---|---|
| `statistical_rigor.py` | Bootstrap CIs (paired-bootstrap, reproducible via seed), Benjamini-Hochberg FDR, Probabilistic Sharpe Ratio, plus `audit_metrics_block(...)` one-call helper. Pure-Python fallbacks for scipy and numpy. | `audit_trail/dashboard_generator.py` — wrap PF/WR/Sharpe per class with `[lo, hi]` band |
| `hrp_allocator.py` | López de Prado 2016 HRP over `{source_system: returns}`. Pure-numpy single-linkage clustering + recursive bisection; no scipy dependency. Drops thin sources (< `min_observations`); equal-weight fallback when numpy unavailable. | `alpha_engine/regime_position_sizer.py` — multiplicative stack with per-symbol vol-target |
| `decay_tracker.py` | Rolling 90d / 365d Sharpe ratio per source-system → `{healthy, decaying, insufficient}` status; configurable thresholds; injectable `now=` for tests. | `audit_trail/dashboard_generator.py` — coloured decay tile per source-system |
| `reconciliation_report.py` | Per-class + portfolio settlement-integrity block: % resolved, median/p95 latency, v2 vs legacy resolver share, `needs_attention` flag at <95% resolved or p95 > 7 days. | `audit_trail/dashboard_generator.py` — top-of-page reconciliation row |

### 8 new researcher personas in `ml_crypto_predictor/researchers/`

All concrete subclasses of `Researcher`; all four abstract methods (`formulate_questions`, `prepare_data`, `conduct_experiment`, `validate_findings`) implemented. Each persona seeds the methodology, success criteria, and recommended production wire-up target so a follow-up PR can pick up immediately.

| Persona | Theme | Productionizes into |
|---|---|---|
| `vol_targeting_researcher.py` | A | `alpha_engine/vol_targeted_sizer.py` (caller: `regime_position_sizer.py`) |
| `reconciliation_researcher.py` | B | `alpha_engine/outcome_resolver.py` + `reconciliation_report.py` |
| `hmm_regime_researcher.py` | C | `alpha_engine/system_trend_detector.py` (deepens `regime_researcher.py`) |
| `risk_parity_researcher.py` | D | `alpha_engine/hrp_allocator.py` (caller: `regime_position_sizer.py`) |
| `factor_overlay_researcher.py` | D | `alpha_engine/baby_strategies/` (gate: `anti_overfit_validator.py`) |
| `multiple_testing_researcher.py` | F | `alpha_engine/anti_overfit_validator.py` (utility: `statistical_rigor.py`) |
| `meta_orchestrator_researcher.py` | E | `ml_crypto_predictor/researchers/coordinator.py` (HANDOFF_MAP defined) |
| `transaction_cost_researcher.py` | A/D | `alpha_engine/execution_researcher` callers (draft: `reports/RESEARCH_KELLY_AND_SLIPPAGE.md`) |

All eight are wired into `ml_crypto_predictor/researchers/__init__.py` via the existing `_try_import` pattern, so they participate in `__all__` automatically.

### Coupled bug fixes (justified per AGENTS.md "fix bugs tightly coupled to the code you're changing")

The researcher framework was completely unimportable on a clean install before this PR (none of the existing 19 personas could load either). My new personas inherit from `Researcher` and the meta-orchestrator wires through `__init__.py`, so I had to land two minimal fixes to make the wiring contract real:

1. **`base.py`**: added `from __future__ import annotations` (line 8). Without it, `pd.DataFrame` and `Union[str, Exchange]` annotations were evaluated at class-definition time and crashed the module load before any subclass could import it.
2. **`base.py`**: fixed the `HAS_DATA_ACCESS` / `DataManager` undefined-name pair in the `__init__` constructor. Both were referenced unconditionally but never assigned in the `except ImportError:` fallback branch. Now both are assigned (`HAS_DATA_ACCESS = False`, `DataManager = None`) so missing optional dependencies cleanly degrade to a warning instead of crashing instantiation.
3. **`__init__.py`**: extended `_try_import` to also swallow `NameError` so a single torch-less environment (e.g. `sequence_researcher.py` annotates `-> nn.Module`) doesn't kill the whole package import. Other personas that do load (the new 8 plus any whose optional deps are installed) survive.

These three fixes are minimal and only touch lines that were directly blocking the new wiring. No semantics change for any working consumer.

### Tests

| File | Coverage |
|---|---|
| `tests/test_statistical_rigor.py` | Profit factor edge cases, win rate, Sharpe zero-variance, bootstrap CI reproducibility under fixed seed, BH-FDR all-significant / none-significant / partial, PSR shape, full audit block shape |
| `tests/test_hrp_allocator.py` | Thin-source exclusion, single-source weight=1.0, no-qualifying-sources empty path, weights sum to 1, lower-vol gets higher weight |
| `tests/test_decay_and_reconciliation.py` | Decay insufficient / healthy / decaying paths; reconciliation per-class + portfolio shape; unresolved-pick `needs_attention` flag |

20 new tests, all green locally:

```
$ python -m pytest tests/test_statistical_rigor.py tests/test_hrp_allocator.py tests/test_decay_and_reconciliation.py -q
....................                                                     [100%]
20 passed in 0.94s
```

Persona smoke-test (instantiate, formulate, run, validate all 8):

```
$ python -c "from ml_crypto_predictor.researchers import VolTargetingResearcher, ..."
vol_targeting        OK  q=vt_001  val=pending
reconciliation       OK  q=rec_001  val=pending
hmm_regime           OK  q=hmm_001  val=pending
risk_parity          OK  q=rp_001  val=pending
factor_overlay       OK  q=fac_001  val=pending
multiple_testing     OK  q=mt_001  val=pending
meta_orchestrator    OK  q=mo_001  val=pending
transaction_cost     OK  q=tc_001  val=pending
All 8 personas instantiate, formulate, run, validate.
```

## What was deliberately NOT shipped here (sequencing per the plan)

* **No `audit_trail/dashboard_generator.py` changes.** Plan Part 6 explicitly forbids "big-bang dashboard rewrites" and prescribes feature-flagged tile-by-tile rollout via `tools/mutation_analysis.py`. Wire-up is the next PR.
* **No new gates or pick filters.** All four foundation modules are pure functions; no production callers added in this PR. Each module's docstring carries the `## Wiring Plan` so the next PR can drop it in cleanly.
* **No template HTML edits.** Per the project rule "edit `audit_dashboard/template.html`, NOT `index.html`" — but also per plan Part 6 "no big-bang dashboard rewrite", visual changes wait for the post-validation PR.
* **No `BLOCKED_SOURCE_SYSTEMS` expansions.** Per AGENTS.md and the plan: requires `STRATEGY_INVESTIGATION_BEFORE_KILL.md` + 3-axis mutation protocol first.

## Sequencing — what unblocks what

This PR is the **Week-1 foundation** in the plan's 4-week sequence:

1. ✅ This PR — foundation modules + 8 personas (Week-1 base for all subsequent themes)
2. ⏭️ Next PR (Week 2) — wire `statistical_rigor` + `decay_tracker` + `reconciliation_report` into `audit_trail/dashboard_generator.py`; add tier badges
3. ⏭️ Week 3 — wire `hrp_allocator` into `regime_position_sizer.py`; add EQUITY momentum/quality factor sleeves
4. ⏭️ Week 4 — activate `meta_orchestrator_researcher` trigger watchdog; first dynamic-swarm task is the FOREX deep-dive once the resolver fix has produced clean data

## Verification

* New tests: 20/20 passing (`pytest tests/test_statistical_rigor.py tests/test_hrp_allocator.py tests/test_decay_and_reconciliation.py`)
* Persona import smoke: 8/8 instantiate
* No production code paths modified — so no regression risk for `findtorontoevents.ca/audit` rendering today.
* No template changes, no HTML changes, no `dashboard_payload.json` shape changes.

## References

* Plan source: previous session `<plan>` block, re-supplied as this session's problem statement
* `reports/hedge_fund_performance_review_summary_2026_04_27.md` — tier table
* `reports/HEDGE_LIBS_LEVERAGE_AUDIT_2026_04_22.md` — 20/21 orphan rate (motivates Wire-Up Rule compliance)
* `reports/RESEARCH_KELLY_AND_SLIPPAGE.md` — drafted, not yet wired (transaction-cost persona owns landing)
* `AGENTS.md` — Goal #1, Wire-Up Rule, "fix bugs tightly coupled to your changes"
