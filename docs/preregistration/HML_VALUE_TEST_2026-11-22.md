# Pre-registration — HML (value) measurement test

**Written:** 2026-11-22
**Status:** PRE-REGISTERED, NOT YET RUN. No result is claimed in this document.
**Scope:** read-only measurement on this programme's own data. Not investment advice.

A pre-registration exists so the test cannot be redefined after the numbers are in. The
kill rule, the cost treatment, the benchmark and the expected-null reasoning below are
fixed **before** any data is touched. If the test is later run and the result is
disappointing, that is a result to report, not a reason to change the rule.

---

## 0. BLOCKERS — status as of the single run

Two were verified against the repo on 2026-11-22, **after** the sections below were
written. They were recorded rather than resolved quietly, because either one defeats
the point of pre-registering. They were then worked, and the test was run once.

| # | Blocker | Status | How it was settled |
|---|---|---|---|
| B1 | no point-in-time universe | **PARTIALLY CLEARED** | Fundamentals are now PIT (90-day reporting lag). The *universe* is still survivor-conditioned. Both halves documented in B1 below. |
| B2 | EQUITY cost unmeasured | **CLEARED** | Measured: n=191 names, 238,810 daily + 356,271 minute bars. ~1–5 bp round trip. See B2 below and `reports/equity_cost_hml.json`. |
| B3 | short leg assumed costless | **DECLARED** | Borrow is not publicly posted for this account, so it is declared as an unknown with a quantified sensitivity. See B3 below. |

**Verdict: KILL** — see §8. Because the family is killed on the *gross* signal being
absent (+0.11%/yr), neither the residual survivorship bias nor any plausible borrow
rate can rescue it: both push in the same direction or are too small to matter.


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

**PEAD has decayed since 2005/06**, and the same post-publication decay logic is expected
to apply to the value premium, which has been widely known and traded for decades.

The three sources below were **located and read on 2026-11-22** rather than assumed. They
are listed with what each one actually measures, because only the first is PEAD-specific
— the other two support the decay mechanism, not the PEAD-specific date.

| # | Source | What it actually measures | Relevance |
|---|---|---|---|
| 1 | **Martineau, C. (2022)**, "Rest in Peace Post-Earnings Announcement Drift", *Critical Finance Review* **11(3-4), 613-646** | PEAD directly. Abstract: *"For large stocks, PEAD have been non-existent since 2006"* | **Direct.** The only source that names 2006, and it names it for **large caps** — exactly our universe |
| 2 | **Chordia, T., Subrahmanyam, A. & Tong, Q. (2014)**, "Have capital market anomalies attenuated in the recent era of high liquidity and trading activity?", *Journal of Accounting and Economics* **58, 41-58** | Anomalies broadly, not PEAD. *"the majority of the anomalies have attenuated… approximately halved after decimalization"* | Supports the decay **mechanism** post-~2001. Not PEAD-specific |
| 3 | **Richardson, S., Tuna, I. & Wysocki, C. (2010)**, "Accounting anomalies and fundamental analysis: A review of recent research advances", *Journal of Accounting and Economics* **50(2-3), 410-454** | A review of accounting anomalies incl. PEAD, documenting post-publication attenuation | Supports decay of **this family** pre-2010. A review, not new empirics |

**One caveat taken from source 1, and worth keeping:** Martineau finds PEAD *non-existent
for large stocks since 2006* but **still present in microcaps** (disappearing there only
more recently). The expected null therefore applies to a **large-cap** test. A microcap
extension would be a different test with a different prior, and must not inherit this
one.

Therefore: **a null result on a large-cap universe after 2006 is the expected outcome,
not a failure of the test.** It would corroborate the decay story rather than contradict
it. The interesting outcomes are (a) a positive result surviving costs, or (b) a clean
null with a tight interval, which is a real answer rather than an absence of one.

## 7. What this document does not do

- It does not claim a number. Every quantitative field is UNKNOWN until the test runs.
- It does not import a magnitude from the literature.
- It does **not** yet specify a point-in-time universe, despite §2 requiring one — the
  data does not exist (B1). §2 states the requirement; it is not a statement of fact.
- It does not change any tally row. The programme tally stays `0 INVESTABLE / 11
  NOT_INVESTABLE / 3 UNKNOWN over 14 rows` — HML moved from UNKNOWN to
  NOT_INVESTABLE on the run recorded in §8.

---

## 8. RESULT — the single run (2026-11-23)

Run **once**, with the rule in §5 applied unchanged. Runner:
`tools/hml_pit_backtest.py`; artifact: `reports/hml_result.json`.

### Configuration actually used

| Setting | Value |
|---|---|
| Universe | 200 requested from today's S&P 500 list → **186 usable** (had both prices and fundamentals) |
| Signal | annual `Stockholders Equity / Ordinary Shares Number` ÷ price = B/M |
| Point-in-time rule | fundamental usable only if `period_end + 90d <= rebalance date` |
| Rebalances | **44 monthly**, 2021-11 → 2026-11 |
| Portfolio | quintiles, equal weight, k ≈ 29–30 per leg |
| Cost in | **4.97 bp** round trip (conservative max of CS/Roll + SEC) |
| Turnover | 14.8%/month average |

### Numbers

| | |
|---|---|
| Gross annual | **+0.11%** |
| Net annual (after cost) | **+0.02%** |
| SE of annual net | 6.65% |
| One-sided 95% upper bound | **+10.96%** |
| Hurdle | 4.32% |
| Kill arm 1 (point ≤ hurdle) | **TRUE** |
| Kill arm 2 (UB ≤ hurdle) | false |
| **Verdict** | **KILL** |

### The kill is driven by the GROSS signal, not by cost

Cost drag is `14.8%/month × 4.97 bp × 12 ≈ 0.09%/yr`. Gross is `+0.11%/yr`, so net is
`+0.02%/yr`. **Even at zero cost the family fails the 4.32% hurdle by over four
percentage points.** This is not a cost-driven rejection, and no argument about the
cost constant can reopen it.

### The ranking works — this is a real null, not a broken test

The legs are economically coherent, which is the check that the B/M sort is not
garbage:

- **LONG (cheap, high B/M):** banks and insurers (`BAC`, `C`, `COF`, `CFG`, `FITB`,
  `ALL`, `CB`, `AIZ`, `CINF`), utilities (`DUK`, `ED`, `EXC`, `EVRG`, `ES`, `ETR`),
  plus `F`, `CVS`, `BRK-B`.
- **SHORT (expensive, low B/M):** high-multiple growth (`ADBE`, `AVGO`, `AMAT`,
  `ANET`, `CDNS`, `ADSK`, `CRWD`), consumer growth (`AMZN`, `CMG`, `BKNG`, `ABNB`,
  `DXCM`).

A textbook HML portfolio. The sort is correct; the premium is absent over this
window. 20 of 44 months positive, mean monthly gross `+0.009%`, sd `3.67%`.

### This is the outcome §6 predicted

§6 recorded, before the run, that a large-cap post-2006 null is the **expected**
result rather than a failure. That is what happened: the result corroborates the
decay premise in §6 (Martineau 2022, large caps specifically) rather than
contradicting it.

### B1 — how far it was actually cleared

**Cleared:** the fundamentals are genuinely point-in-time. The 90-day reporting lag
means a 10-K is never traded before it could have been filed.

**Not cleared:** the *universe*. The ticker list is today's S&P 500, so delisted names
are missing from the cheap leg. Observed live, not assumed: `EA`, `DFS` and `EQR` are
in the list but returned *"possibly delisted, no price data found"* and were dropped.
Bias direction is **upward** (survivors are the winners), so true PIT HML would be
**worse** than +0.11%. The residual bias therefore cannot rescue the verdict.

### B2 — cleared, with the number that was used

Measured on 191 names over 238,810 daily and 356,271 minute bars: Corwin-Schultz
median **0.77 bp**, Roll median **4.77 bp**, SEC **0.206 bp**, impact **0.008% of
ADV** at $20k/name. Round trip **≈1–5 bp**; the tool takes the conservative maximum
(4.97 bp). The repo's 5.0 bp constant was about right; its 25.0 bp constant overstated
by ~5x. Detail: `updates/2026-11-23-equity-cost-measured-questrade.md`.

### B3 — borrow, declared rather than assumed

**Declaration:** Questrade does not publish short borrow rates; they are security- and
account-specific. **The borrow rate for this book is UNKNOWN and is carried at 0 bp in
the numbers above — an explicit limitation, not a finding.**

**Sensitivity:** the short leg is 50% of committed capital. General-collateral
large-cap borrow at 0.5%/yr costs `0.5 × 50% = 25 bp/yr` of committed capital; at
2%/yr it is 100 bp/yr. The short leg here is large liquid growth, normally easy to
borrow, so the low end is more plausible.

**Why it does not change the verdict:** net is `+0.02%` against a `4.32%` hurdle.
Borrow can only make net *lower*. Even at a 0 bp borrow assumption the family fails by
over four points. B3 is immaterial **to this verdict** — it would matter for a family
that passed.

Zero capital sanctioned. Not investment advice.

