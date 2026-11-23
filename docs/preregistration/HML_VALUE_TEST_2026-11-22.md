# Pre-registration — HML (value) measurement test

**Written:** 2026-11-22
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

### B1 — There is no point-in-time universe, so §2 cannot be honoured

§2 requires a point-in-time universe with no survivorship filtering. That is currently
impossible here:

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

§3 promises measured costs. For EQUITY they do not exist:

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
and the borrow cost on the cheap-to-short names is not free. §4 accounts for committed
collateral but not for borrow. Either borrow cost is measured and charged, or §2 is
amended to a **long-only** value test with its benchmark restated — the current wording
silently assumes costless shorting.

---

## 1. Why this test, and why measure rather than import

The external literature disagrees roughly **2x** on the magnitude of the value premium:

- the low end puts gross HML at about **25–42 bp/month**;
- the high end at about **50–70 bp/month**.

Both ranges are gross of turnover costs, and both come from universes and sample periods
that are not ours. With a 2x disagreement, importing either number into the programme's
tally would be a guess dressed as evidence. The honest move is to **measure HML on our
own data**, with our own costs, and let the interval decide.

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
  two constants in use differ by 5x (5.0 bp vs 25.0 bp). That must be reported alongside
  every net number rather than hidden.
- Gross and net results are both reported; only the **net** figure feeds the kill rule.

## 4. Benchmark and capital base

- The benchmark is **committed capital including cash collateral**, not a raw T-bill
  yield. A long-short book ties up collateral, so comparing it against a bare risk-free
  rate would flatter the strategy.
- All returns are expressed as **net return on committed capital**.

## 5. Kill rule (fixed in advance)

The value family is **killed** if either condition holds on the out-of-sample period:

1. **OOS annualised net return on committed capital ≤ 4.3%**, or
2. **the one-sided 95% upper bound of that return ≤ 4.3%**.

Condition 2 is the stronger one: it says even the optimistic end of the interval fails to
clear the bar, so continuing to collect data cannot rescue the family.

**The bar is 4.32%, not a rounded 4.3%.** Its source is
`tools/capacity_model.py:HURDLE_TBILL_APR = 0.0432` — *"the programme hurdle,
docs/edge_research/07"*. The 4.3% rounding was fixed before the source was located, and
the two are not identical: a result of **4.31% would pass the written rule while
sitting 1 bp below the programme hurdle**. To remove that ambiguity, the binding test is
**≤ 4.32%**, and a result in the 4.30-4.32% band must be reported as *at the hurdle*, not
as a pass.

Passing the kill rule is **not** a promotion. A survivor goes to forward observation, not
to `INVESTABLE`.

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
- It does **not** yet specify a point-in-time universe, despite §2 requiring one — the
  data does not exist (B1). §2 states the requirement; it is not a statement of fact.
- It does not change any tally row. The programme tally stays `0 INVESTABLE / 10
  NOT_INVESTABLE / 4 UNKNOWN over 14 rows` until a measured result exists.
