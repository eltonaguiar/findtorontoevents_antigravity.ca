# VALUE (HML) pre-registration — completed, and it found two blockers that stop the test

**Date:** 2026-11-22
**Document:** `docs/preregistration/HML_VALUE_TEST_2026-11-22.md`
**Status:** pre-registered, **not runnable yet** — see B1/B2/B3

---

## What was asked

Pre-register a VALUE test before any backtest: monthly **HML long-short on our own
universe, net of MEASURED costs**; kill if either the OOS annualised net return on
committed capital **≤ 4.3%**, or the one-sided **95% upper bound ≤ 4.3%**. Record that
PEAD decayed post-2005/06 across three independent sources, so a large-cap post-2006 null
is the **expected** result. Do not import a literature magnitude — models disagree 2x
(25–42 vs 50–70 bp/month gross).

A pre-registration already existed in the tree covering the headline requirements. Rather
than rewrite it, I verified its claims against the repo. Three did not hold.

## B1 — the point-in-time universe does not exist (blocking)

§2 requires "a point-in-time universe… no survivorship filtering". That cannot currently
be satisfied:

| what exists | what it actually is |
|---|---|
| `data/universe/sp500_tickers.txt` | 502 names; the file's own header says **"static snapshot ~2026-06"** |
| `STOCKS/scanners/delisted_symbols.py` | a filter that **removes** delisted/renamed tickers so yfinance batches don't break |
| `tools/point_in_time_audit.py` | a static **code** scanner for look-ahead patterns — not a universe builder |
| historical index membership | **absent from the repo** |

**Why it matters beyond hygiene:** value stocks are disproportionately the ones that
delist or go bankrupt. A 2026-06 survivor snapshot drops the losers from the cheap leg, so
measured HML is biased **toward a positive result** — manufacturing exactly the outcome
the test exists to detect honestly. Running on the static snapshot would yield a number
that is wrong in a known direction.

## B2 — EQUITY cost is unmeasured, so "net of measured costs" cannot be met (blocking)

- `tools/measured_cost_recost.py` → `UNMEASURED = {"BOND","COMMODITY","EQUITY","ETF","FUTURES"}`. Only FOREX (7.53 bp, upper bound) and CRYPTO (12.60 bp) are measured.
- Assumed EQUITY cost is **5.0 bp** (`measured_cost_recost.ASSUMED`, `alpha_engine/cost_model.py`).
- `tools/pod_equity_breakout_backtest.py:COST_BP_PRIMARY` assumes **25.0 bp**.

**Two constants in the same repo differ by 5x.** "Net of cost" there is a choice of
constant, not a measurement. Per the standing rule an unmeasured cost may gate a
**rejection** but never support a **promotion** — so even a clean pass cannot promote.
M1 (`tools/equity_cost_measure.py`) is measuring this in parallel.

## B3 — the short leg is assumed costless

Monthly HML shorts the expensive leg. Large-cap shorting needs locate/borrow, and borrow
on the names one wants to short is not free. §4 charges committed collateral but not
borrow. Either borrow is measured and charged, or §2 becomes a long-only test with a
restated benchmark.

## The 4.3% hurdle was rounded, and the rounding is load-bearing

The real constant is `tools/capacity_model.py:HURDLE_TBILL_APR = 0.0432` — *"the
programme hurdle, docs/edge_research/07"*. The pre-registration said 4.3%.

A result of **4.31% would pass the written rule while sitting 1 bp below the programme
hurdle.** The document now binds on **≤ 4.32%** and requires a result in the 4.30–4.32%
band to be reported as *at the hurdle*, not as a pass.

## "Three independent sources" was unfalsifiable as written

The PEAD-decay premise is recorded, but it names no sources — so a reader cannot tell
whether the decay holds, and a null could always be explained away after the fact. The
document now marks it **OPERATOR-SUPPLIED PREMISE, sources not yet named**, and requires
the three to be named and read (with sample period, universe, anomaly definition) before
the document is treated as complete.

**I did not invent three citations to fill the count.** The premise is the operator's;
dressing it in unread references would be the same error as importing a magnitude.

## Q4 honoured

No literature magnitude is an input. §1 prints the full **2x disagreement** (25–42 vs
50–70 bp/month gross) rather than a point estimate, and notes both ranges come from
universes and periods that are not ours.

## What this means

The test is **pre-registered and blocked**, which is the honest state. The kill rule, the
cost treatment and the expected-null reasoning are fixed in advance — that is what the
pre-registration was for. But two of the three inputs it depends on (a PIT universe and a
measured EQUITY cost) do not exist yet, and running without them would produce a biased
number.

Order of work when unblocked: **measure EQUITY cost (B2) → build a PIT universe (B1) →
decide borrow (B3) → run exactly once against the frozen rule.**

Zero capital sanctioned. Not investment advice.
