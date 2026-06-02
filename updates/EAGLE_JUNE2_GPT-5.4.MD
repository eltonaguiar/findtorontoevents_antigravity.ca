# EAGLE_JUNE2_GPT-5.4

**Date:** 2026-06-02  
**Model:** GPT-5.4  
**Scope:** Quant review of `/audit`, `/audit/ai-tournament.html`, `/audit/pick_funnel.html`, and PF portfolios, plus tightly-coupled UI fixes for portfolio empty-state diagnosis.

---

## 1. Executive verdict

This is **not primarily a "wait longer" problem**.

The main `/audit` production book is weak because the system currently mixes four different universes and treats them too similarly:

1. **Policy-clean money-ready truth** - the only capital-allocation layer that should drive sizing.
2. **Tournament / PF books** - useful paper portfolios, but not equivalent to deployable production edge.
3. **Pick-funnel discovery cells** - useful for finding candidate filters, but often concentrated, disputed, or not holdout-safe.
4. **Lab / verified sleeves** - the best future promotion candidates, but many are still sidecars and not yet forward-proven.

The research-to-production gap is the core failure mode. A few sleeves show promise, but the bulk deployed emitter mix is still low quality after dedup, policy-clean filters, and live resolver realities.

---

## 2. Current state by asset class

Canonical live source: `audit_dashboard/data/money_ready_verdict.json` generated 2026-06-02.

| Asset class | Live state | Main diagnosis | Recommended action |
| --- | --- | --- | --- |
| **CRYPTO** | n~374, WR 35.6%, PF 0.89, verdict `NOT_READY` | Real sub-cohort edge exists, but deployed aggregate book loses because selection/gating/concentration are wrong | Quarantine weak aggregate emitters; promote only proven filtered sleeves after forward proof |
| **EQUITY** | n~52, WR 26.9%, PF 0.33, verdict `NOT_READY` | Honest production failure, not a patience issue | Mutate or depromote weak emitters; do not size until a verified sleeve graduates |
| **ETF** | n~3, WR 66.7%, PF 1.46, verdict `INSUFFICIENT_DATA` | Best candidate class, but forward sample is too small | Wait for forward n, prioritize ETF dual momentum for promotion |
| **FOREX** | n~32, WR 28.1%, PF 0.48 | Resolver/label contamination plus weak live edge | Fix labels/resolver hygiene before trusting any WR headline |
| **COMMODITY** | n~4, PF 1.68 | Too little clean live sample to trust | Wait for more sample; avoid broad promotion claims |
| **FUTURES** | n~13, PF 0.52 | Concentration/artifact risk dominates interpretation | Clean concentration and duplicate issues before drawing conclusions |
| **BOND** | No meaningful clean live sample | Data/backfill gap | Fix data coverage first, then evaluate sleeves |

**Bottom line:** CRYPTO, EQUITY, and FOREX are not failing because they merely need time. ETF is the clearest "wait for forward n" case.

---

## 3. Where edge exists right now

### 3.1 Main `/audit`

There is **no deployable money-ready edge right now**. The live policy-clean layer still fails the repo's own institutional bars.

### 3.2 `/audit/ai-tournament.html` and `pf.html`

This is the strongest current **paper** edge. The live PF roster shows:

- `pf_portfolios.json` has **81 portfolios**
- **66** currently have open positions
- `deepseek_v4__aggressive` currently has **11 open names**

Most credible tournament edge today:

1. `deepseek_v4`
2. `gpt4o`
3. `grok3`

These are still **paper/tournament** signals, not production money-ready proof.

### 3.3 `/audit/pick_funnel.html`

Useful for discovery, but not for sizing. Some green cells are real candidate filters, but many are:

- overly concentrated in one source
- too small to generalize
- affected by disputed cohorts or resolver contamination

### 3.4 Verified sleeves

Best promotion candidates:

1. **ETF dual momentum**
2. **Crypto VWAP walk-forward sleeves**
3. **Crypto Bollinger walk-forward sleeves**

These are where the next real edge should come from if forward evidence holds.

---

## 4. Root causes

### 4.1 Research != production

The lab and the live scanner are still too different. Verified sleeves live in sidecars while the main production scanner still emits from a broader, noisier universe.

### 4.2 Breadth over depth

Too many emitters are allowed to contribute before they have enough forward proof. That dilutes the few sleeves that actually look promising.

### 4.3 Concentration masquerading as edge

Some surfaces look strong only because a single source/system dominates the cohort. That is not the same as broad, deployable edge.

### 4.4 Resolver / label / duplicate contamination

This is especially damaging in disputed cohorts and in classes like FOREX. High WR with terrible PF is a classic red flag that the labels and path-to-close rules are distorting the story.

### 4.5 Inconsistent validation methodology

Too much of the strategy stack is still judged under weaker backtest standards than the standards implied by live capital deployment.

---

## 5. Proper backtesting methodology

Every strategy should pass a single admissibility pipeline before it can affect capital.

### Stage 0 - Hypothesis registration

- Pre-register the thesis, parameters, and target asset class.
- No post-hoc "discovered edge" should bypass registration.

### Stage 1 - Real data only

- Use explicit data provenance and fallback chain.
- No synthetic replay, no hidden backfill shortcuts, no ambiguous source merges.

### Stage 2 - Purged and embargoed walk-forward

- Replace simple chronological splits with purged/embargoed walk-forward.
- Promotion should use the strongest available engine, not the easiest one.

### Stage 3 - Costed OOS evaluation

- Apply asset-class costs and slippage in every engine.
- OOS PF/WR must be reported net of realistic frictions.

### Stage 4 - Multiple-testing controls

- DSR
- PBO
- SPA / reality-check style controls when multiple sleeves compete

### Stage 5 - Dependence-aware robustness

- Use block bootstrap instead of i.i.d. shuffle
- Test regime robustness across trend and volatility states

### Stage 6 - Forward paper gate

Require a forward-paper hurdle before promotion:

- meaningful forward n
- PF and WR remain acceptable
- forward PF stays reasonably close to lab OOS PF

### Stage 7 - Shadow sizing and gradual scale

- start tiny
- scale only after live performance remains within acceptable drift bounds
- depromote quickly when live performance diverges from lab expectations

### Example standardized validation pipeline

```python
from dataclasses import dataclass

@dataclass
class ValidationResult:
    hypothesis_id: str
    asset_class: str
    oos_pf: float
    oos_wr: float
    dsr: float
    pbo: float
    forward_n: int
    promote: bool


def run_validation_pipeline(strategy, bars, cost_model, hypothesis_id, asset_class):
    folds = build_purged_embargoed_walk_forward(
        bars,
        train_days=180,
        test_days=30,
        purge_days=30,
        embargo_days=10,
    )
    fold_results = []
    for fold in folds:
        signal_df = strategy.generate_signals(fold.train, fold.test)
        net_df = apply_asset_class_costs(signal_df, cost_model, asset_class)
        fold_results.append(score_fold(net_df))

    summary = summarize_oos(fold_results)
    dsr = compute_deflated_sharpe(summary.returns)
    pbo = compute_probability_of_backtest_overfitting(fold_results)
    forward = load_forward_paper_stats(hypothesis_id)
    promote = (
        summary.pf >= 1.50
        and summary.win_rate >= 0.55
        and dsr >= 0.95
        and pbo <= 0.55
        and forward.n_closed >= 50
        and forward.pf >= 1.30
        and abs(forward.pf - summary.pf) <= 0.20
    )
    return ValidationResult(
        hypothesis_id=hypothesis_id,
        asset_class=asset_class,
        oos_pf=summary.pf,
        oos_wr=summary.win_rate,
        dsr=dsr,
        pbo=pbo,
        forward_n=forward.n_closed,
        promote=promote,
    )
```

### Minimal implementation sequence

1. Register the hypothesis in git before the first run.
2. Build folds with purge and embargo sized to the holding period.
3. Apply per-class costs before scoring PF/WR.
4. Compute DSR/PBO on the same OOS fold set.
5. Compare forward-paper drift against the lab OOS baseline.
6. Promote only when both the statistical gate and the forward gate pass.

---

## 6. Mutation, inversion, or waiting?

| Action | When to use it | Current examples |
| --- | --- | --- |
| **Wait** | Only when a sleeve looks good but lacks enough forward sample | ETF dual momentum, crypto verified sidecars |
| **Mutate** | When a sleeve is plausible but degraded live | Selected equity and crypto candidates |
| **Invert** | Only after explicit OOS evidence that the signed edge is consistently wrong | Rare; do not invert class-wide by intuition |
| **Kill / depromote** | When live policy-clean performance is clearly bad and no rescue evidence exists | Weak aggregate EQUITY / CRYPTO / FOREX production emitters |

**Quant answer:** mutation should be selective, inversion should be rare, and waiting is only justified for small-sample verified sleeves - not for the current production aggregate book.

---

## 7. Portfolio empty-page diagnosis

The example portfolio was **not actually empty** on the live server.

The issue was diagnostic ambiguity:

- `pf.html` fetched `pf_portfolio_<safeKey>.json`
- the live PF roster existed
- the example book had open positions
- the page still fell back to a generic "pending first daily run" message whenever detail fetch failed

That generic fallback hid the real causes:

1. corrupted or pasted portfolio keys
2. stale deploys
3. roster/detail JSON mismatch

### Fix shipped in this PR

`audit_dashboard/pf.html` now:

- strips invisible Unicode from pasted `?key=`
- distinguishes among:
  - missing key
  - roster found but detail JSON missing
  - unknown key
  - roster unavailable
- gives the operator an actionable recovery path back to `ai-tournament.html`

`audit_dashboard/ai-tournament.html` now uses clearer PF-roster unavailability messaging instead of always implying "first daily run pending."

---

## 8. Enhancement plan

### Immediate

1. Treat `money_ready_verdict.json` as the only sizing truth.
2. Keep tournament edge, funnel edge, and money-ready edge explicitly separated.
3. Depromote weak aggregate production sleeves in CRYPTO, EQUITY, and FOREX.
4. Keep ETF dual momentum and verified crypto walk-forward sleeves on the promotion path.

### 30-day

1. Standardize on one promotion-grade backtesting pipeline.
2. Clean resolver and duplicate contamination in disputed cohorts.
3. Require provenance and cost modeling across all engines.

### 90-day

1. Shrink the production emitter zoo.
2. Promote only sleeves that survive forward-paper gates.
3. Track concentration and drift as first-class risk metrics.

---

## 9. Real-time monitoring metrics and thresholds

### 9.1 Concentration

Use both simple and exposure-weighted concentration metrics:

| Metric | Definition | Warning | Hard gate |
| --- | --- | --- | --- |
| **HHI by source** | Sum of squared source weights in active picks | `> 0.18` | `> 0.25` |
| **HHI by strategy** | Sum of squared strategy weights in active picks | `> 0.15` | `> 0.22` |
| **Top-1 source share** | Largest single source share | `> 35%` | `> 50%` |
| **Top-3 share** | Sum of top 3 source shares | `> 70%` | `> 85%` |
| **Single-symbol gross exposure** | Largest symbol gross exposure share | `> 8%` | `> 12%` |

Example monitoring query shape:

```python
def hhi(weights):
    return sum(w * w for w in weights if w > 0)


def compute_source_concentration(active_positions):
    gross = sum(abs(p["weight"]) for p in active_positions) or 1.0
    by_source = {}
    for pos in active_positions:
        by_source[pos["source_system"]] = by_source.get(pos["source_system"], 0.0) + abs(pos["weight"]) / gross
    return {
        "source_hhi": hhi(by_source.values()),
        "top1_share": max(by_source.values(), default=0.0),
        "top3_share": sum(sorted(by_source.values(), reverse=True)[:3]),
    }
```

### 9.2 Resolver dispute rate

Track dispute rate at both the cohort and asset-class level:

| Metric | Definition | Warning | Hard gate |
| --- | --- | --- | --- |
| **Dispute rate** | `disputed_resolutions / closed_picks` | `> 1%` | `> 2%` |
| **Zero-PnL terminal rate** | closed picks with terminal status and `pnl_pct = 0` | `> 3%` | `> 5%` |
| **Duplicate timestamp rate** | duplicate `(symbol, source, emitted_at)` groups / raw picks | `> 0.5%` | `> 1%` |
| **TIME_EXIT skew** | `% of closes by TIME_EXIT with PF collapse` | monitor | hard gate if coupled with PF `< 0.7` |

Example alert logic:

```python
def resolver_health(closed_rows):
    total = max(len(closed_rows), 1)
    disputes = sum(1 for r in closed_rows if r.get("resolver_disputed"))
    zero_pnl = sum(1 for r in closed_rows if r.get("terminal") and abs(float(r.get("pnl_pct", 0.0))) < 1e-9)
    return {
        "dispute_rate": disputes / total,
        "zero_pnl_terminal_rate": zero_pnl / total,
        "healthy": disputes / total <= 0.01 and zero_pnl / total <= 0.03,
    }
```

### 9.3 Operating policy

1. Warning threshold: flag the dashboard cell amber and block new promotions in that cohort.
2. Hard-gate threshold: freeze sizing increases and remove the cohort from any "money-ready" narrative.
3. Three consecutive healthy daily reads are required before re-enabling promotions.

---

## 10. Mutation testing framework

Mutation should be a disciplined search around a plausible sleeve, not a random parameter sweep.

### 10.1 Candidate selection

Only mutate sleeves that satisfy all three:

1. coherent economic story
2. at least one OOS or forward slice with PF near viability
3. failure mode is diagnosable (cost sensitivity, regime mismatch, concentration, timing)

### 10.2 Mutation axes

| Axis | Examples |
| --- | --- |
| **Entry logic** | tighter signal threshold, confirmation filter, alternate breakout lookback |
| **Exit logic** | ATR stop, time-stop band, partial take-profit, trailing stop |
| **Regime filter** | trend filter, vol filter, macro regime allowlist |
| **Universe filter** | liquidity floor, spread cap, session/time-of-day filter |
| **Position sizing** | capped Kelly fraction, volatility target, regime position scalar |

### 10.3 Framework

```python
def mutate_strategy(base_config):
    for threshold in [0.8, 1.0, 1.2]:
        for atr_stop in [1.5, 2.0, 2.5]:
            for regime_gate in ["off", "trend_only", "trend_plus_vol"]:
                yield {
                    **base_config,
                    "signal_threshold": threshold,
                    "atr_stop": atr_stop,
                    "regime_gate": regime_gate,
                }


def score_mutations(base_strategy, bars, cost_model, hypothesis_id, asset_class):
    results = []
    for config in mutate_strategy(base_strategy.config):
        candidate = base_strategy.with_config(config)
        result = run_validation_pipeline(
            candidate,
            bars=bars,
            cost_model=cost_model,
            hypothesis_id=hypothesis_id,
            asset_class=asset_class,
        )
        if result.oos_pf > 1.0:
            results.append((config, result))
    return sorted(results, key=lambda item: (item[1].promote, item[1].oos_pf), reverse=True)
```

### 10.4 Tooling recommendation

1. **Core research:** Python + pandas/numpy for event alignment and feature generation.
2. **Optimization control:** Optuna for constrained search spaces, not unconstrained brute force.
3. **Validation stats:** custom wrappers around DSR/PBO/SPA calculations so every run emits the same schema.
4. **Experiment tracking:** MLflow or a lightweight sqlite/jsonl registry keyed by hypothesis id.
5. **Promotion audit trail:** write every mutation result to a single comparable table/json so losers are not forgotten and re-tested as "new."

### 10.5 Acceptance rule

Promote a mutation candidate only if:

- OOS PF improves by at least `0.10`
- DSR does not degrade
- forward PF drift stays within `0.20`
- concentration does not worsen past the warning threshold
- the mutation still has a coherent thesis you can explain in one sentence

---

## 11. Files changed

- `audit_dashboard/pf.html`
- `audit_dashboard/ai-tournament.html`
- `updates/EAGLE_JUNE2_GPT-5.4.MD`

---

## 12. Verification

- Re-read the PF page fetch path and empty-state flow after the patch.
- Rechecked the live PF roster and the example `deepseek_v4__aggressive` detail export.
- Confirmed the report aligns with:
  - `money_ready_verdict.json`
  - `quant_strategy_root_cause_review_2026-06-02.md`
  - `backtesting_methodology_audit_2026-06-02.md`
  - `multi_class_strategy_lab_2026-06-02.md`
