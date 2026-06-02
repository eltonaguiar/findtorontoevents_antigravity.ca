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

## 9. Files changed

- `audit_dashboard/pf.html`
- `audit_dashboard/ai-tournament.html`
- `updates/EAGLE_JUNE2_GPT-5.4.MD`

---

## 10. Verification

- Re-read the PF page fetch path and empty-state flow after the patch.
- Rechecked the live PF roster and the example `deepseek_v4__aggressive` detail export.
- Confirmed the report aligns with:
  - `money_ready_verdict.json`
  - `quant_strategy_root_cause_review_2026-06-02.md`
  - `backtesting_methodology_audit_2026-06-02.md`
  - `multi_class_strategy_lab_2026-06-02.md`
