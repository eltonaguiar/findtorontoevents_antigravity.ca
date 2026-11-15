# Proposed profitability framework

**Review date:** 2026-11-15 UTC. **Priority:** Goal #1, trustworthy risk-adjusted financial results.
**Status:** research/design proposal, not an approved implementation, winning-strategy certification or capital allocation.

## 1. Answer first

The strongest starting point is **low-cost, diversified, unleveraged allocation**, with an independently tested **monthly ETF tactical-allocation challenger**. Concentrated stock selection and intraday/scalping should be separate, tightly bounded research lanes, not the default money-making plan.

This does not mean mutual funds are intrinsically safer than ETFs, or that an ETF wrapper makes a bad trading strategy good. Risk comes principally from underlying exposures, leverage, concentration, horizon, liquidity and implementation costs.

The July money-maker edition already moved the primary research track toward ETF tactical asset allocation. That direction remains reasonable, but its "validated/deployed" language must not substitute for independent reproduction and continuous forward evidence. This review reproduced defects in its actual blend tracker.

**No reviewed current prediction class is established as capital-ready.** Conversely, failure of the existing predictors is not proof that investing in those underlying markets cannot be profitable.

## 2. Scope, sources and limits

- GitHub source pin: `1b3c7fe67a32f4d6f87e568641118f13fc61f0b5`, committed 2026-11-15 00:21:32 UTC.
- Local peer-code reference: `b2187f4f5dfeed56af639744b5a6758e51cc1079`. Peer-code inspection was read-only; no peer-file modification was performed.
- The pasted Windows list contains **466 path lines, 236 distinct Windows paths and 31 distinct basenames**. Worktree copies and repeated lines collapse to **24 mapped repository documents**. All 24 exist on the GitHub pin and were reviewed in full; their contents are distinct, not 24 copies of one report.
- Historical coverage and raw-blob hashes: [historical document review](./HISTORICAL_MONEY_PLAN_REVIEW.md). The private machine-path mapping is intentionally excluded from publication.
- The two missing file basenames are `2026-05-11-money-maker-ready-plan.md` and the exported `money-maker-ready-june112026edition.skill`; the other unmatched basenames describe skill/workspace directories or old git ref logs. Four tracked money-maker skill Markdown files provide the available skill definitions. The referenced historical branch did not appear in the exact remote-ref lookup.
- Parent review additionally covered all four money-maker skills, the June master loop, July edition review, cross-asset/entry-integrity/free-data syntheses, performance charter and relevant testing-protocol sections. The asset-class reviewer covers the complete strategy catalogue and registrations.
- Graph navigation was unavailable because the checkout has no existing graph file; no expensive graph rebuild was substituted for source review.
- This is **not a claim to have read every Markdown file in the gigantic mixed-purpose repository**, nor a fresh audit of all databases. Current numbers below are published snapshot evidence, not independently re-queried database results.
- General fund mechanics and day-trading risks were corroborated through FINRA. Other requested public research sources were blocked/unavailable; no SPIVA, individual-stock or day-trader profitability percentage is asserted from those failed requests.

## 3. Asset taxonomy: do not rank unlike things

The current verdict snapshot tracks nine labels: **CRYPTO, MEME, EQUITY, PENNY_STOCK, ETF, FOREX, COMMODITY, FUTURES and BOND**. These are operational labels, not nine mutually exclusive economic asset classes.

- MEME is a speculative crypto subset; PENNY_STOCK is an equity subset.
- ETFs and mutual funds are wrappers that may hold stocks, bonds, commodities or mixed allocations.
- Futures/perpetuals/options are contracts on underlying exposures, with their own financing, margin, expiry and execution risks.
- REIT/property, gold, credit, inflation-linked and cash/Treasury exposures belong in look-through allocation even when represented only by ETFs.
- Copytraders, fundamentals, news, ML and prediction-market-derived signals are **sources/methods**, not automatically independent asset classes or independent alpha.
- Sports betting is separately evaluated under Goal #2. Toronto events, movies and creator listings are not investment asset classes.

Every research record should therefore specify:

`underlying exposure | instrument/wrapper | venue | currency | strategy | direction | horizon | signal source | execution model | lifecycle | evidence cohort`

The detailed [attempted-class map](./ASSET_CLASS_COVERAGE.md) is supplied separately by the asset-class reviewer. An absent verdict row means absent coverage, not automatically "no attempt" or "no edge."

## 4. Current evidence, not the May headlines

Published `money_ready_verdict.json`, generated **2026-11-15 00:05:20 UTC**, pinned above:

| Operational class | Published n | WR | PF | Published verdict |
|---|---:|---:|---:|---|
| CRYPTO | 3,705 | 35.87% | 0.9196 | NOT_READY |
| EQUITY | 250 | 59.20% | 0.9392 | NOT_READY |
| FOREX | 612 | 32.19% | 0.6596 | NOT_READY |
| COMMODITY | 229 | 40.17% | 1.0256 | WATCH |
| ETF | 45 | 2.22% | 0.0216 | INSUFFICIENT_DATA |
| FUTURES | 52 | 42.31% | 1.0936 | INSUFFICIENT_DATA |
| BOND | 1 outer / 26 intrabar | 0% outer / 7.69% intrabar | 0 outer / 0.3915 intrabar | INSUFFICIENT_DATA |
| MEME | 10 | 10.00% | 0.0234 | INSUFFICIENT_DATA |
| PENNY_STOCK | 4 | 50.00% | 0.1779 | INSUFFICIENT_DATA |

`summary.money_ready` is empty. The BOND count mismatch is explicitly retained rather than silently choosing a convenient cohort. This is a cumulative published cohort at the stated snapshot, not a newly verified uniform 24-hour interval; the snapshot does not expose one shared inception window for this table.

The registry generated at **00:07:10 UTC** uses a different cohort: ETF **n=19/PF=1.7877**, CRYPTO **n=22,089/PF=0.2576**, EQUITY **n=475/PF=0.6336**. All rows deny promotion. Do not average these with the verdict table or interpret the ETF discrepancy as proof of a winning ETF strategy. Some registry source labels identify input files, not independent economic emitters.

### The recent improvement worth investigating, without promoting it

Raw recency sidecars generated at **00:13:06 UTC**, with `fallback_mode=false`:

| Class | 14-day decisive n / PF | 48-hour decisive n / PF | Interpretation |
|---|---|---|---|
| CRYPTO | 1,390 / 1.059 | 146 / 1.678 | Potential recent improvement; 12 duplicate groups and about 98.6% AlphaEngine source share in 48h |
| EQUITY | 17 / 1.007 | 0 / undefined | Insufficient recent evidence |
| ETF | 47 / 0.621 | 0 / undefined | Existing active ETF selectors are not a successful fund-allocation strategy |
| FOREX | 159 / 0.087 | 2 / 3.244 | Two observations cannot establish a turnaround |
| FUTURES | 189 / 1.376 | 7 / 4.888 | Small recent sample; 71.4% NG=F concentration in 48h |

The 14-day interval is **2026-11-01 00:13:05 to 2026-11-15 00:13:05 UTC**; 48h is **2026-11-13 00:13:06 to 2026-11-15 00:13:06 UTC**. These are terminal-event recency views, not policy-clean, fully cost-verified admission cohorts. The writer flags duplicate groups but does not remove them before these metrics (`tools/audit_pick_funnel/build_recency_summary.py:81-110`). No capital-ready claim follows from a 48h point estimate.

## 5. What the historical plans teach

### Keep

- Truth-layer-first state transitions and a weekly MEASURE -> DIAGNOSE -> ACT -> FORWARD -> RATCHET loop.
- All-class measurement coverage, but only two or three focused research tracks.
- Point-in-time entry features, event-time execution checks, economic deduplication and cumulative trial accounting.
- Independent benchmark controls, risk/cost stress and forward confirmation.
- Mutation before permanent retirement, with immediate containment of invalid measurement or unsafe execution.
- Explicit forward/replay divergence, source freshness, coverage and model-health reporting.

### Correct or reject

- "SHIPPED" in a report, green CI and a new webpage are not evidence of deployed profitable execution.
- May PF/WR, old PR numbers, fixed freshness assessments and "dead" labels are history, not current state.
- Clamp/winsorize, invent an exit date, replace unknown with zero, or map a TP label to WON: none repairs provenance.
- Excluding all TIME_EXIT or flat outcomes biases economic performance.
- Yield observations are not executable bond/futures prices.
- More simulations, more models or more same-day picks do not create independent evidence.
- The July phrase "alpha is impossible on free data" is too universal: the studies establish failures under their particular universe, execution, data and costs, not a theorem about all strategies.
- The June claim "measurement fixed" and July claim "measurement broken" are dated assessments. November zero/blank/event-time findings require fresh acceptance checks.

## 6. Three approaches and recommended allocation of research effort

| Approach | Strength | Main failure mode | Recommendation |
|---|---|---|---|
| Diversified low-cost core + independently tested monthly TAA challenger | Low turnover, simple benchmark, manageable data/execution, captures investment risk premia without pretending to predict every tick | Market loss, rates correlation, whipsaw, taxes, inaccessible share classes | **Primary research approach** |
| Point-in-time diversified equity selection | Potential fundamentals/quality contribution, clear stock benchmark | Survivorship, selection of today's NVDA-like winners, tech concentration, unavailable delisted/PIT data | One conditional challenger, after data/execution requirements |
| Broad ML/intraday/scalping search | Can test mechanisms and identify narrow effects | Small gross edge versus fees/spread/latency, leakage, many correlated trials, leverage and margin | Paper-only, bounded experiments; lowest initial priority |

These are qualitative priorities under low-turnover, no-leverage, multi-year growth assumptions, **not estimated future-success percentages**. For short-horizon nominal capital preservation, cash/short Treasury exposure can instead lead, with lower return potential and inflation/currency risk. Investor constraints are not known; no weights are recommended.

Mutual funds may fit periodic long-term contributions. ETFs are operationally easier for a monthly rotation where intraday execution is needed. Neither automatically dominates the other. Picking today's leading individual stock after seeing its history is not a fair alternative to a frozen diversified strategy.

## 7. Applied risk results: mutual funds are not automatically low risk

Recomputed from retained public Yahoo adjusted-close histories: common sessions **2021-11-15 to 2026-11-13**, **1,254 daily returns**. Calendar-year CAGR uses 365.25 days; volatility/Sharpe use 252 sessions. All NAV curves include initial capital.

| Instrument | Wrapper / exposure | Calendar CAGR | Annual volatility | MDD loss | Daily ES97.5 loss | Excess Sharpe vs SGOV |
|---|---|---:|---:|---:|---:|---:|
| FZROX | Mutual fund / US stocks | 10.70% | 17.63% | 25.12% | 3.17% | 0.450 |
| FXAIX | Mutual fund / US large-cap | 11.63% | 17.17% | 24.50% | 3.11% | 0.506 |
| VTSAX | Mutual fund / US stocks | 10.48% | 17.61% | 25.36% | 3.17% | 0.439 |
| SPY | ETF / US large-cap | 11.54% | 17.33% | 24.50% | 3.13% | 0.498 |
| VTI | ETF / US stocks | 10.49% | 17.66% | 25.36% | 3.17% | 0.438 |
| BND | ETF / bonds | -0.28% | 6.07% | 17.31% | 0.97% | -0.648 |
| SGOV | ETF / short Treasuries | 3.89% | 0.24% | 0.03% | 0.01% | Not applicable |

Source hashes and recomputation: [framework-passive-risk-verified.json](./framework-passive-risk-verified.json). Small CAGR differences from the earlier report reflect calendar-year versus 252-session annualization; price window, volatility, drawdown and Sharpe are unchanged.

**Limits:** one vendor; adjusted prices assume distributions/splits handled correctly, not independently confirmed; platform, spreads, taxes and currency conversion excluded. This is passive descriptive history, not proof of prediction or an all-in net tactical strategy.

The retained 2,000-draw, 60-session moving-block-bootstrap FXAIX excess-Sharpe 95% interval is **[-0.116, 1.352]**; FZROX/VTSAX also cross zero. This is illustrative uncertainty, not calibrated future success. Block sensitivity and selection corrections remain required.

### Stress arithmetic, not an investment recommendation

A hypothetical 60% equity / 30% bonds / 10% cash basket:

- Equity -35%, bonds -10%, cash 0% -> **-24%**.
- Equity -50%, bonds -20%, cash 0% -> **-36%**.

Thus neither low fees nor a generic 60/40-style mix establishes a 20% drawdown guarantee. Bond/cash sleeves need duration/credit/currency analysis; AGG is a bond fund, not cash. A stop or volatility target cannot guarantee a gap-free maximum loss.

## 8. The existing TAA candidate needs reproduction, not blind adoption

The July report claims a 2007-2026 rotation Sharpe **0.88**, MDD **19%**, versus SPY **0.74/51%**; the blend claims **0.89/16%**. These are **attributed historical report results**, not independently reproduced by this review. Common history, total-return adjustments, costs, calendar and benchmark alignment are required before accepting them. Related variants sharing markets/data are not independent confirmations.

Actual current-code concerns:

| Reproduced or inspected issue | Why it matters |
|---|---|
| Blend's rotation sleeve allocates to negative-momentum ETFs rather than implementing its component's absolute filter (`tools/tactical_blend_tracker.py:34-51`) | Reported strategy and actual target generator differ |
| Four available rotation instruments produce weights totaling **0.90**, with no declared remaining cash | Missing history becomes an apparently valid allocation |
| SPY selected by both components receives **0.60** | Overlap breaches the proposed 35% single-ETF cap before looking through correlated holdings |
| Per-symbol latest observations are independently ranked, while output exposes only a maximum date | One fresh instrument can mask stale/incompatible inputs |
| Rotation uses a 6-month parameter but emits `mom_9m`; fallback instrument is AGG (`tools/tactical_rotation_tracker.py:41-53,73-106`) | Parameter contract and defensive-risk labels are misleading |
| No committed rotation/blend status JSON at the source pin; bounded workflow/caller search found no regular tracker driver | Continuous forward tracking is not established |

Three pure offline fixtures reproduced the negative-momentum, 90%-weight and 60%-overlap cases. No DB/network access or generator execution was used.

The July POC has a real checkpoint workflow and two successful July runs. However, its **committed verdict is an empty code block**, old run logs are unavailable (HTTP 410), and the workflow is a July-date reminder, not a monthly allocation NAV tracker. `resolve_poc_picks.py:31-39,78-106` uses the latest downloaded close and renormalizes surviving priced legs, which is not proof of complete, event-time-matched basket performance. These facts do not prove the POC lost; they mean its claimed financial result and 6-12-month tracking have not been demonstrated.

**Research order:** reproduce one frozen rotation implementation; establish a passive benchmark; only then compare the blend on the same timeline. Do not increase variant count because the best historical headline looks attractive.

## 9. Framework architecture: five bounded work packages

### A. Evidence ledger and complete lifecycles

Start with all OPEN and recent terminal records, not just zero-PnL picks. Preserve original data and expose an append-only independently checked interpretation.

Record signal-available, order/fill, mark, exit, resolver and publication times separately. Include instrument identity, currency, quantity, cash flows, commissions, distributions, financing, venue and source version. Terminal lifecycle and financially measured outcome are separate states.

Classify every row as measured, precision-rounded flat, unpriced, stale, missing fields, disputed or ambiguous. An open exit price is not applicable; an absent closed fill is unknown. Unknown/null is not zero and cannot support financial admission.

### B. Portfolio NAV and common benchmarks

Build calendar-time account equity from actual or explicitly modeled fills, cash, outstanding positions and costs. Reconcile daily independently. Do not add trade percentages or compound simultaneous trades as full-account periods.

Compare funds/equities to the same-currency passive exposure, TAA to both SPY and an exposure/risk-matched multi-asset benchmark, and active timing to admissible matched-random entries. A low-risk portfolio should also report comparison with cash; SGOV is an investable proxy, not guaranteed risk-free.

### C. Pre-registered experiment registry

Freeze the universe, rule, signal cutoff, first executable event, exit/holding policy, cost cases, benchmark, decision statistic, trial family and stopping dates before testing.

Use chronological/nested validation; preserve serial and cross-asset dependence; account for all attempted variants and post-hoc filters. Reserve genuine unseen/forward data. Revisit a refuted strategy only after a specific changed premise, not a new report name.

The first family should contain a passive diversified baseline and **one** frozen TAA challenger. A diversified stock-selection challenger enters only with point-in-time/universe coverage. Intraday research enters only with sufficient executable-data resolution and a credible cost advantage.

### D. Risk and probability evaluation

Risk metrics: calendar CAGR, time-weighted NAV return, cash-relative Sharpe, appropriate Sortino/Calmar, drawdown and recovery duration, Expected Shortfall, turnover, look-through exposure and risk contribution. Report uncertainty and minimum tail support.

Simulate joint portfolio paths with shared dated blocks across assets and block-length sensitivity, plus explicit equity/rate/currency/liquidity shocks. Include spread/funding increases, delayed fills, provider failure and forced-liquidation/margin scenarios where relevant. Never present IID average win/loss ruin simulations as an account-level probability.

Define success before estimating it: **positive nominal return, positive real return, beating cash, beating a risk-matched benchmark, and staying inside the loss budget** are separate events. State horizon, currency, cost/tax scope, model, effective evidence and calibration error.

Historical rolling frequencies, bootstrap positivity, p-values, DSR scores and Bayesian-shrunk trade WR are not interchangeable with future portfolio-profit probability. Current personalized/prospective probability is **not estimable from this review**.

### E. Auditable admission and dashboard contracts

Proposed stages: **MEASUREMENT_BLOCKED -> RESEARCH -> SHADOW_FORWARD -> REVIEWABLE -> CAPITAL_ELIGIBLE**, with automatic backward transitions and explicit approval before financial risk. This is a proposed common vocabulary, not a replacement of existing gates without a versioned migration.

Before admission, require complete evidence-state coverage, exact executable clocks, NAV reconciliation, realistic net cost, dependence-aware uncertainty, risk stress and sufficient unseen forward exposure. Existing rules remain enforced until an approved type-specific mandate reconciles their conflicting sample floors and probability definitions.

For predictive trades, retain charter thresholds as necessary, not sufficient. For monthly/passive allocations, do not manufacture 100 independent trades by counting correlated fund holdings or daily marks. Use months, regime coverage, effective observations and benchmark-relative portfolio evidence. July's 6-12-month forward period is a minimum observation plan, not an automatic guarantee of statistical power.

Add a read-only Risk/Evidence view linked from Active/Closed Picks, showing validation state, event/reference prices, confidence scope, costs, benchmark, actual account-NAV risk and promotion permission. Publishing a page does not promote its contents.

## 10. Exact QA requirements and falsification

Extend [the existing QA plan](./QA_PLAN.md), rather than creating another incompatible validator.

| Test | Acceptance |
|---|---|
| Zero, null, nonzero and blank-field rows | All audited; no zero-only preselection or silent early return |
| Fresh equal prices | Independent timestamped reference required; age alone cannot verify flat |
| Legitimate intraday flat versus later daily close | No "fabricated" label merely because the close differs |
| Terminal row missing close time | Explicit anomaly, not reclassified OPEN |
| Signal versus fill versus current/exit clock | Comparisons use the respective executable event; no future quote leakage |
| Fund signal after NAV publication | Executes at a subsequent eligible NAV, unless an earlier valid order cutoff is demonstrated |
| Missing/stale ETF input | Deny valid target output; freshness per instrument/calendar, not global newest date |
| Negative momentum / missing universe / component overlap | Frozen-rule parity, explicit cash and sum of weights, look-through risk caps |
| Open positions, fees and distributions | Included in NAV and reconciliation; operating expenses not subtracted twice |
| Gaps, both-stop/target touch, trailing stops | Observed versus modeled versus ambiguous fill distinguished |
| Two simultaneous equal-weight +10% positions | Portfolio return **10%**, not sequentially compounded **21%** |
| Random timing null | Changes admissible entry times; a Sharpe-invariant permutation must fail null-validity QA |
| Live updater and UI | Current committed/deployed data hash, expected cadence, cohort parity and visible failure state |

**Potential falsifiers:** TAA improvement disappears after executable lag/costs/total-return corrections; forward performance fails the frozen risk/benchmark bar; concentration or missing data drives the result; a strategy's benefit is no better than risk-matched random exposure. In each case, demote/stop that research lane rather than tune until a pass appears.

## 11. Practical sequence and stopping discipline

1. **Measurement first:** reconcile uncapped open/recent terminal evidence and portfolio clocks. Deliver coverage and exception report; no history laundering.
2. **Reproduction:** independently rebuild passive NAV and one frozen TAA challenger on aligned, adjustment-verified data. Deliver reproducible artifacts, costs and risk stress.
3. **Forward driver:** persist immutable decisions, actual/model fills and daily NAV on a publication-aware cadence. Verify production caller, workflow results and deployed contract, not just helper imports.
4. **Challenger evaluation:** assess frozen benchmarks at scheduled checkpoints with adequate effective evidence. The first few weeks establish plumbing; they do not prove monthly allocation performance.
5. **Review decision:** retain, demote or retire based on the predeclared bars. Only after evidence and an approved mandate can a capital proposal be considered.

Weekly diagnostics use the master loop's H1 measurement, H2 replay/forward decay, H3 data/power, H4 source value and H5 coverage, with explicit **economic cost/capacity** and **portfolio-risk integrity** checks. After three null focus cycles, rotate research priority; do not repeat the same closed family or widen live risk to manufacture observations.

There is no honest date by which the framework guarantees a winning strategy. Success of this proposal is initially an **auditable decision process that can reject bad strategies**, followed by finding a candidate that actually survives it.

## 12. Public corroboration

- [FINRA mutual-fund mechanics](https://www.finra.org/investors/investing/investment-products/mutual-funds): daily NAV, underlying holdings, distributions, fees and loss risk.
- [FINRA ETF versus mutual fund](https://www.finra.org/investors/insights/etf-vs-mutual-fund), 2022-11-10: both wrappers can hold active/passive strategies; NAV and exchange execution differ; neither guarantees returns.
- [FINRA Rule 2270 day-trading risk disclosure](https://www.finra.org/rules-guidance/rulebooks/finra-rules/2270): execution/operational/cost risks and losses beyond initial investment with margin/shorting.

These sources support mechanisms and caution, not a personal success probability or a guarantee that passive/TAA will outperform.
