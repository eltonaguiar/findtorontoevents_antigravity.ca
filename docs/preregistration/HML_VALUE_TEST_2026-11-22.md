# Pre-registration — HML (value) measurement test

**Written:** 2026-11-22
**Amended:** 2026-11-23T00:25Z (operator-authorised: the collateral treatment is now stated explicitly in the benchmark section; the kill-rule threshold is unchanged)
**Status:** PRE-REGISTERED, NOT YET RUN. No result is claimed in this document.
**Scope:** read-only measurement on this programme's own data. Not investment advice.

A pre-registration exists so the test cannot be redefined after the numbers are in. The
kill rule, the cost treatment, the benchmark and the expected-null reasoning below are
fixed **before** any data is touched. If the test is later run and the result is
disappointing, that is a result to report, not a reason to change the rule.

---

## 0. BLOCKERS — the test may NOT be run until these are cleared

Both were verified against the repo on 2026-11-22, **after** the sections below were
written. They are recorded here rather than resolved quietly, because either one
defeats the point of pre-registering.

### B1 — There is no point-in-time universe, so the definition section cannot be honoured

The definition section requires a point-in-time universe with no survivorship filtering
[SRC: this document §2]. That is currently impossible here:

| what exists | what it actually is |
|---|---|
| `data/universe/sp500_tickers.txt` | 502 names, header says **"static snapshot ~2026-06"** — current constituents only |
| `STOCKS/scanners/delisted_symbols.py` | a filter that **REMOVES** delisted/renamed tickers so yfinance batches don't break — the opposite of what a PIT universe needs |
| `tools/point_in_time_audit.py` | a static **code** scanner for look-ahead patterns, not a universe builder |
| historical index membership | **does not exist** in this repo |

**Why this is not a technicality.** Value stocks are disproportionately the ones that
delist, go bankrupt, or get acquired. A 2026-06 snapshot of surviving large-caps drops
the losers from the cheap leg, so measured HML would be biased **toward a positive
result** — manufacturing the very outcome the test exists to detect honestly. Running on
the static snapshot would produce a number, and the number would be wrong in a known
direction.

**Cleared when:** a rebalance-date-by-rebalance-date membership list (with its own
provenance) exists, and the count of names dropped for missing book-to-market is reported
per rebalance.

### B2 — EQUITY execution cost is UNMEASURED, so "net of measured costs" cannot be met

The cost section promises measured costs [SRC: this document §3]. For EQUITY they do not exist:

- `tools/measured_cost_recost.py` → `UNMEASURED = {"BOND", "COMMODITY", "EQUITY", "ETF", "FUTURES"}`. Only FOREX (7.53 bp, upper bound) and CRYPTO (12.60 bp) are measured.
- The assumed EQUITY cost is **5.0 bp** in `tools/measured_cost_recost.py:ASSUMED` and `alpha_engine/cost_model.py`.
- A second tool, `tools/pod_equity_breakout_backtest.py:COST_BP_PRIMARY`, assumes
  **25.0 bp** — a **5x disagreement between two constants in the same repo**.

With a 5x spread between the two constants in use, "net of cost" is a choice of
constant, not a measurement. Per the programme's standing rule, an unmeasured cost may
gate a **rejection** but may never support a **promotion** — so even a clean pass cannot
be promoted until this is measured.

**Cleared when:** EQUITY round-trip cost is measured with provenance (in flight as
`tools/equity_cost_measure.py`, M1). Note that tool already documents that the equity
breakout verdict rested on the 25.0 bp constant.

### B3 — The short leg is assumed, not established

A monthly HML book shorts the expensive leg. Large-cap shorting requires locate/borrow,
and the borrow cost on the cheap-to-short names is not free. The benchmark section
accounts for committed collateral but not for borrow [SRC: this document §4]. Either
borrow cost is measured and charged, or the definition is amended to a **long-only** value
test with its benchmark restated [SRC: this document §2] — the current wording silently
assumes costless shorting.

---

## 1. Why this test, and why measure rather than import

The external literature disagrees by roughly a factor of two on the magnitude of the value
premium:

- the low end puts gross HML at about **25–42 bp/month** UNMEASURED: no citation present in this repo;
- the high end at about **50–70 bp/month** UNMEASURED: no citation present in this repo.

Both ranges are gross of turnover costs, and both come from universes and sample periods
that are not ours. With that factor-of-two disagreement, importing either number into the
programme's tally would be a guess dressed as evidence. The honest move is to **measure
HML on our own data**, with our own costs, and let the interval decide. UNMEASURED: the
two literature ranges have no citation in this repo, so they are recorded here but used as
no input anywhere in this document.

## 2. Definition under test

- **Signal:** HML (high-minus-low book-to-market), i.e. long cheap, short expensive.
- **Rebalance:** **monthly**.
- **Holding:** long-short, equal treatment of both legs as defined by the HML construction.
- **Universe:** a **point-in-time** universe. A name enters only if it was actually
  available and had a valid book-to-market at the rebalance date. No survivorship
  filtering, no look-ahead into delisted or later-listed names.
- **Data:** our own stored price and fundamental data. Where a field is unavailable the
  row is dropped and counted, never imputed silently.

## 3. Cost treatment

- **Turnover costs are counted exactly once.** No double-charging at both entry and exit;
  cost is applied per unit of turnover, not per trade leg.
- Costs are the programme's measured cost estimates where they exist (per asset class),
  not a round-number assumption. **For EQUITY no measured cost exists yet — see B2.**
  Until B2 clears, any net figure in this test is net of an *assumed* constant, and the
  two constants in use differ by 5x (5.0 bp vs 25.0 bp) [SRC: tools/measured_cost_recost.py; tools/pod_equity_breakout_backtest.py]. That must be reported alongside
  every net number rather than hidden.
- Gross and net results are both reported; only the **net** figure feeds the kill rule.

## 4. Benchmark and capital base

- The benchmark is **committed capital including cash collateral**, not a raw T-bill
  yield. A long-short book ties up collateral, so comparing it against a bare risk-free
  rate would flatter the strategy.
- All returns are expressed as **net return on committed capital**.
- **Collateral interest is now stated explicitly, in two named cases.** The policy rate is
  **4.32% annualised** [SRC: tools/capacity_model.py:49] (`HURDLE_TBILL_APR = 0.0432`); the
  hurdle Sharpe is **1.114** [SRC: tools/equity_cost_measure.py:482].

### COLLATERAL_BASE

Cash collateral posted against the short leg **earns the policy rate, 4.32% annualised** [SRC: tools/capacity_model.py:49].
The benchmark return is therefore the sum of the
long-leg return, the short-leg return, and the collateral interest:

```
collateral_interest = 0.0432 × collateral_notional × (days / 365)
benchmark_base      = r_long + r_short + collateral_interest / committed_capital
```

### COLLATERAL_CONSERVATIVE

Collateral earns **0%** in this case by assumption, deliberately ignoring the 4.32% policy rate [SRC: tools/capacity_model.py:49]. Because a zero-yield benchmark *under-credits* cash, the
conservative case may not simply leave that cash out: the forgone interest is booked as an
**explicit cost charged to the strategy**, so the hurdle is never flattered by pretending
the collateral was unproductive.

In words: the strategy's net return is its gross return, minus turnover cost, minus the
interest the collateral would have earned had that cash been left at the policy rate.

Algebraically:

```
forgone_collateral_interest = 0.0432 × collateral_notional × (days / 365)
net_conservative            = gross_strategy − turnover_cost − forgone_collateral_interest
```

The benchmark in this case is `r_long + r_short + 0`, and the cost line above is what keeps
the comparison honest. The policy rate `0.0432` is sourced [SRC: tools/capacity_model.py:49].

### Which case is the headline, and why

**COLLATERAL_CONSERVATIVE is the headline for the go/no-go decision.** It is the only case
that cannot flatter the strategy: crediting collateral at the policy rate raises the
benchmark the strategy must beat by exactly the interest that cash earns for free, whereas
charging that interest to the strategy when it is *not* credited asks the strategy to beat
the bar it would face if the collateral were merely idle cash. A pass that exists only
because collateral interest was credited (COLLATERAL_BASE) is a pass against a weaker bar,
not a pass. If the result clears the kill rule in COLLATERAL_BASE but not in
COLLATERAL_CONSERVATIVE, the family has **not** passed.

### 4.1 Worked example (ARITHMETIC, NOT A MEASURED RESULT)

Round numbers only, to show how the two cases differ. **No backtest has been run, and none
of these figures is a result.** Take a representative nominal size:

- committed capital `C = $100,000`;
- collateral posted against the short leg = `50%` of committed capital, so `collateral_notional = $50,000`;
- holding period `days = 30`;
- illustrative gross strategy return `g = 1.00%` on committed capital and turnover cost
  `t = 0.10%` on committed capital (assumptions chosen only to exercise the formula).

Collateral interest for the period:

```
0.0432 × 50,000 × 30 / 365 = 177.53 dollars
```

- Under COLLATERAL_BASE that `$177.53` is added to the benchmark: the strategy must beat
  an extra `0.178%` of committed capital for the month.
- Under COLLATERAL_CONSERVATIVE the same `$177.53` is subtracted from the strategy:
  `net_conservative = 1.00% − 0.10% − 0.178% = 0.722%` for the month.

The two cases therefore differ by `2 × 0.178% = 0.355%` per month in this example: the
collateral interest is counted once on each side, which is exactly why the conservative
case cannot flatter the result. These figures are arithmetic only and carry no evidential
weight.

## 5. Kill rule (fixed in advance)

The value family is **killed** if either condition holds on the out-of-sample period:

1. **OOS annualised net return on committed capital ≤ 4.3%**, or
2. **the one-sided 95% upper bound of that return ≤ 4.3%**.

The second condition is the stronger one: it says even the optimistic end of the interval fails to
clear the bar, so continuing to collect data cannot rescue the family [SRC: this document §5].

**The bar is 4.32%, not a rounded 4.3%.** Its source is
`tools/capacity_model.py:HURDLE_TBILL_APR = 0.0432` [SRC: tools/capacity_model.py:49] — *"the
programme hurdle, docs/edge_research/07"*. The 4.3% rounding was fixed before the source was
located, and the two are not identical: a result of **4.31% would pass the written rule while
sitting 1 bp below the programme hurdle**. To remove that ambiguity, the binding test is
**≤ 4.32%**, and a result in the 4.30-4.32% band must be reported as *at the hurdle*, not
as a pass.

**The kill rule is applied to BOTH collateral cases** (see the benchmark section): a result
must clear it under `COLLATERAL_CONSERVATIVE` as well as under `COLLATERAL_BASE`, and a pass
that holds in only one of the two cases is **not** a pass.

Passing the kill rule is **not** a promotion. A survivor goes to forward observation, not
to `INVESTABLE`.

> **Provenance gap (recorded 2026-11-23).** This document cites `tools/capacity_model.py:49` for the 4.32% policy rate, but that file is absent from `origin/main` (verified with `git ls-tree origin/main -- tools/capacity_model.py`, which returns nothing; `tests/test_capacity_model.py` is absent too). The 4.32% hurdle is therefore not reproducible from the repository as of that date. This changes neither the binding test (at most 4.32% at the gross-signal level) nor the KILL verdict, which is driven by the gross signal, not by the cost model. See `docs/edge_research/29_NEXT_STEPS_2026-11-23.md` item 2 and `updates/2026-11-23-peer-claim-verification.md` (B11).
> Update 2026-11-23: `tools/capacity_model.py` and `tests/test_capacity_model.py` have since been ported to main from `origin/push/phase2-round-2026-11-22` (commit `1c15c5d7d07`), so the cited constant is now reproducible from a clean clone of main; see `updates/2026-11-23-capacity-model-ported.md`.

## 6. Expected result, recorded before running

**PEAD has decayed since 2005/06** according to three independent sources. The same
post-publication decay logic applies to the value premium, which has been widely known
and traded for decades.

**Status of that claim: OPERATOR-SUPPLIED PREMISE, sources not yet named.** As written,
"three independent sources" is unfalsifiable — a reader cannot tell whether the decay
holds, and a null result could always be explained away by the premise. Before this
document is treated as complete, the three sources must be **named and read**, and the
claim restated with what each one actually measures (sample period, universe, anomaly
definition). Until then the reasoning below is a prior, not evidence.

Therefore: **a null result on a large-cap universe after 2006 is the expected outcome,
not a failure of the test.** It would corroborate the decay story rather than contradict
it. The interesting outcomes are (a) a positive result surviving costs, or (b) a clean
null with a tight interval, which is a real answer rather than an absence of one.

## 7. What this document does not do

- It does not claim a number. Every quantitative field is UNKNOWN until the test runs.
- It does not import a magnitude from the literature.
- It does **not** yet specify a point-in-time universe, despite the definition section
  requiring one [SRC: this document §2] — the data does not exist (B1). The definition
  section states the requirement; it is not a statement of fact.
- It does not change any tally row. As of 2026-11-23 the programme tally is
  `0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN` over 14 rows [SRC: docs/edge_research/23_DEFINITIVE_ANSWER_2026-11-22.md:195];
  this pre-registration changes no row and adds no verdict.

---

# Appendix A. Dossier-shape contract (required by `tools/doc_source_lint.py`)

The programme's doc linter requires every published document to carry eight fixed headings
and a Provenance footer. This pre-registration is not an audit-review dossier, so the
appendix supplies the required shape from this document's own content. It adds no claim
that is not already in the body above.

## 1 Identity

- **Document:** `docs/preregistration/HML_VALUE_TEST_2026-11-22.md` — pre-registered 2026-11-22, amended 2026-11-23 by operator instruction.
- **Family:** VALUE (Fama-French HML, high-minus-low book-to-market), EQUITY asset class.
- **Status:** PRE-REGISTERED, NOT YET RUN. No result is claimed anywhere in this document.
- **Scope:** read-only measurement on this programme's own data. Not investment advice.
- **Policy constants:** the policy rate is 4.32% [SRC: tools/capacity_model.py:49]; the hurdle Sharpe is 1.114 [SRC: tools/equity_cost_measure.py:482].

## 2 What the class is

An HML book is long the cheap (high book-to-market) leg and short the expensive (low
book-to-market) leg, rebalanced monthly, with the spread measured net of turnover cost and
against committed capital that includes the collateral the short leg ties up. The asset
class is EQUITY, and the short leg is what makes borrow and collateral real costs rather
than accounting details (blocker B3).

## 3 Measured state

UNMEASURED. No return, cost, or confidence interval has been computed for this family. The
blockers recorded at the top of this document are open, and every quantitative field is
UNKNOWN until the test runs.

## 4 Contradictions

- The EQUITY cost constant in the repo disagrees with itself five-fold: 5.0 bp [SRC: tools/measured_cost_recost.py] versus 25.0 bp [SRC: tools/pod_equity_breakout_backtest.py].
- The kill rule was written with 4.3% and the programme hurdle is 4.32% [SRC: tools/capacity_model.py:49]; the kill-rule section makes 4.32% binding.
- Collateral interest was unstated in the first version of the benchmark section; this amendment states both cases explicitly.

## 5 Data integrity

- **No point-in-time universe.** The only equity membership list is a static snapshot [SRC: data/universe/sp500_tickers.txt], and the delisted-name filter removes exactly the names a PIT universe must keep [SRC: STOCKS/scanners/delisted_symbols.py]. Survivorship bias here pushes HML toward a positive result.
- **No borrow cost.** The short leg's locate/borrow is not measured.
- **No measured EQUITY cost.** It is an assumption, not a measurement.

## 6 Cost reality

Costs are counted once per unit of turnover. For EQUITY the cost is an assumption, not a
measurement, and the two constants in use differ five-fold [SRC: tools/measured_cost_recost.py], so
any net figure must be reported with the constant that produced it. Collateral is priced in
two cases: at the 4.32% policy rate [SRC: tools/capacity_model.py:49], or at zero with the
forgone interest charged back to the strategy.

## 7 What would change the verdict

- A cleared blocker set plus a measured out-of-sample interval whose full lower bound
  clears 4.32% [SRC: tools/capacity_model.py:49] in **both** collateral cases would move the
  family from "not yet run" toward forward observation.
- The kill rule firing in either case closes the family.
- A pass in one case only changes nothing: the conservative case governs.

## 8 Blunt answer

Least survivable number: the assumed EQUITY round-trip cost. It is not measured, the two
constants in the repo disagree five-fold, and every net figure this test will produce is a
linear function of it [SRC: tools/measured_cost_recost.py]. Next least survivable is the
4.32% policy rate itself [SRC: tools/capacity_model.py:49]: it is sourced, but it is a
policy constant rather than a measured return, so if it moves the whole hurdle moves with it.

## Provenance
- model: `subq-savant-1.4` (Zoo agent, code mode)
- prompt: operator instruction for the collateral amendment, quoted verbatim in the benchmark section
- snapshot: `docs/preregistration/HML_VALUE_TEST_2026-11-22.md` at prereg branch tip `8df189f317c`; policy rate `tools/capacity_model.py:49`; hurdle Sharpe `tools/equity_cost_measure.py:482`
- amendment: operator-authorised 2026-11-23T00:25Z. The collateral treatment is stated for both cases in the benchmark section. The kill-rule threshold is UNCHANGED: 4.3% as written, 4.32% binding [SRC: tools/capacity_model.py:49]. No result was added, removed, or reinterpreted.
