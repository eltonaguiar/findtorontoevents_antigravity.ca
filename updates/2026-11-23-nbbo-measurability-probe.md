# 2026-11-23 — NBBO measurability probe: BOND, COMMODITY_FUTURES, PENNY_STOCK

**Type:** feasibility probe, not a measurement. No cost constant was added, no artifact
regenerated, no code changed. One new file (this document).

## The question

Can this repository measure the BOND, COMMODITY_FUTURES and PENNY_STOCK round-trip
execution cost at true NBBO (national best bid/offer), instead of the 1-minute
bar-range **upper bound** currently on the record? The bar-range number is
`median(high-low)/close` per 1-min bar, which bounds the round-trip quoted spread from
above because both the bid and the ask lie inside `[low, high]` at any instant. It is
conservative for a kill decision but says nothing about how much headroom exists. This
probe answers only *whether* a quoted-spread path exists in the repo, per class, and
cites where it would be or what is missing. It does not run it.

## The three numbers, and their exact provenance

The artifact the numbers come from is **`reports/cost_measurement_new_classes/class_cost_new_20261123.json`**.
It is **not on `origin/main`**: `reports/` is git-ignored (`.gitignore:20-21` whitelists only
two specific reports), so the artifact is committed only on branch
**`cost/new-classes-2026-11-23` @ `7379044708046852583ea24b0131f380152718d6`** (confirmed via
`git ls-remote origin 'refs/heads/cost/*'`). Everything below was read from that ref with
`git show`, never from the shared working tree.

The artifact's own `basis_note` reads verbatim:

> Every bp figure is the median 1-min bar range = a rigorous UPPER bound on the round-trip
> quoted spread (bid and ask both lie inside [low, high]); it is NOT the NBBO.

| Class | Median RT (bp) | Status recorded in artifact | Freshness | Names | Range |
|---|---|---|---|---|---|
| BOND | **1.2124854** | `MEASURED_FROM_LAST_SESSION` | LAST_SESSION | 10/10 | JNK 0.5442 → TLT 2.5126 |
| COMMODITY_FUTURES | **6.3182320** | `MEASURED_UPPER_BOUND` | LIVE_SESSION | 7/7 | ZS=F 2.0572 → SI=F 9.6041 |
| PENNY_STOCK | **21.2973651** | `MEASURED_FROM_LAST_SESSION` | LAST_SESSION | 7/8 (TELL `empty`) | SIRI 6.2697 → PLUG 92.6440 |

Each class also carries `measurement_kind: UPPER_BOUND_ON_RT_QUOTED_SPREAD`. Same figures are
restated at `updates/2026-11-23-stale-cost-status-corrections.md:10-13` and
`docs/edge_research/22_FINAL_SYNTHESIS_2026-11-22.md:36-37,83`.

**Material discrepancy to record (not resolved here):** the artifact is the `range_upper_bound_rt_bp`
median, but it also stores a `corwin_schultz_rt_bp_median` of **0.0724** bp for BOND,
**0.0** bp for COMMODITY_FUTURES and **8.7933** bp for PENNY_STOCK. Those do not reproduce the
headline figures above. The probe does not attempt to explain it; it only flags that the
headline number is the bar-range bound, not the Corwin-Schultz estimate (see the next section).

## Where the "upper bound" characterisation comes from

This is **sourced**, not merely asserted:

- **Proof (mathematical, in the tool):** [`tools/equity_cost_measure.py:15`](tools/equity_cost_measure.py:15)
  and `:236-239` state that at any instant bid and ask both lie inside the bar's `[low, high]`,
  so the round-trip quoted spread cannot exceed `high-low`. That is the justification, and it is
  a valid one for an upper bound.
- **Estimation caveat (in the tool and in the field):** [`corwin_schultz()`](tools/equity_cost_measure.py:147)
  is documented only as "Corwin & Schultz (2012) on consecutive bar pairs. Floors negatives at 0."
  The tool does **not** formally derive the upward bias of the estimator on 1-min bars; the task
  brief's claim that it is "biased upward" is an interpretation of the estimator's assumptions,
  not a proof stored in the repo. `roll_estimator()` at `:177` is similarly labelled "Upward biased
  by volatility" in its docstring.
- **Deliberate status labels:** `_measure_new_class()` sets `MEASURED_UPPER_BOUND` when the sample
  is a live session and `MEASURED_FROM_LAST_SESSION` otherwise
  ([`tools/equity_cost_measure.py:720-729`](tools/equity_cost_measure.py:720)). So the difference
  between the BOND/PENNY tag and the COMMODITY tag is **freshness** (Friday's bars vs a live
  `=F` sample), not a difference in the estimator. All three are upper bounds.
- **One thing the repo asserts without a citation:** the BOND and PENNY caveats say "the true NBBO
  is tighter" ([`tools/equity_cost_measure.py:754`](tools/equity_cost_measure.py:754)) and "not a
  live NBBO". The second is accurate. The first is a monotonic consequence of the bound
  (the true value is ≤ the bound), not an independently established measurement of the gap.

## The measurement tool, read from `origin/main`

Blob `b3ef58b76b53a566582b7e6c2d2c810d0bd085a0`, 966 lines. The line numbers in the task brief are
about 32 lines low against this blob; the values verified here are:

- **Input:** 1-minute OHLCV bars. Primary source is yfinance `period=5d, interval=1m` (Yahoo);
  Tiingo IEX 1-min is the documented fallback ([`measure_spread()`](tools/equity_cost_measure.py:191)).
- **Spread estimators:** `corwin_schultz()` `:147` (high-low), `roll_estimator()` `:177`
  (return autocovariance), and the per-bar range upper bound `:236-239`.
- **Alternate estimators:** no quoted-spread, effective-spread-from-trades, Kyle-lambda or
  trade-and-quote estimator exists in this file. Elsewhere the repo has Amihud illiquidity
  (`alpha_engine/features/volume.py:53`) and an `alpha_engine/execution_cost.py` that *derives*
  a spread from ATR or a default constant (`:102-116`) rather than measuring one.
- **CLI:** `--offline` `:819`, `--classes-measure` `:820`, `--classes-measure-new` `:823`.
- **The only quoted-spread code path:** [`top_of_book()`](tools/equity_cost_measure.py:260) calls
  `https://api.tiingo.com/iex/?tickers=<universe>` and reads `bidPrice`/`askPrice`/sizes. On null
  quotes it records `BLOCKED_NO_LIVE_NBBO` (`:278`), never zero. **It is wired only into the M1/M3
  paths for the equity universes, not into `--classes-measure-new`** (which writes
  `"top_of_book": "Tiingo IEX (needs key; not attempted here)"` at `:797`).

## Per-class verdicts

### BOND (10 bond ETFs: TLT, IEF, SHY, TLH, AGG, BND, LQD, TIP, JNK, HYG)

**Verdict: MEASURABLE, for these 10 ETFs only.**

- Evidence path: `top_of_book()` ([`tools/equity_cost_measure.py:260`](tools/equity_cost_measure.py:260))
  → Tiingo IEX `bidPrice`/`askPrice` for US-listed ETFs, using the existing `TIINGO_API_KEY`
  (`:831`). The alternate adapter `_adapter_tiingo_quote()`
  ([`alpha_engine/equity_price_failover.py:306`](alpha_engine/equity_price_failover.py:306))
  hits the same endpoint.
- Bonds are not a special case: these are ordinary NYSE-listed ETFs, so an equity quote endpoint covers them.
- Limitations: Tiingo IEX is a **single exchange's** top of book, not the consolidated NBBO, and it is a
  live-only snapshot (500/day on the free tier), not a historical quote series. The repo has **no**
  TAQ/consolidated tape, no L2 history and no order-by-order data for US equities. FRED
  (`alpha_engine/bond_data_fred.py`) carries macro yields, not ETF quotes.
- Minimum acquisition to get *true* NBBO: a consolidated-quote feed (SIP/CTA or a vendor offering historical NBBO), plus a historical store.

### COMMODITY_FUTURES (CL=F, GC=F, HG=F, NG=F, SI=F, ZC=F, ZS=F)

**Verdict: BLOCKED_MISSING_DATA.**

- No futures quote source exists. The wired commodity path,
  [`alpha_engine/commodity_price_failover.py`](alpha_engine/commodity_price_failover.py), returns
  only `{"price", "symbol", "currency", "asof", "source"}` from Yahoo v8 chart, Stooq, FMP
  `/quote`, Finnhub `/quote` and FRED spot. **No bid/ask anywhere.** The CME Globex order book is
  not wired (no `CME`/`Globex`/`DATABENTO` key among the secrets).
- The IEX quote path is US-equity/ETF only; IEX does not quote futures.
- Missing exactly: a futures top-of-book feed for `=F` symbols (e.g. a Databento/CME market-data
  subscription, or a broker quote API), and a historical contract-level quote store. The repo also
  lacks a roll-adjusted continuous series (`docs/edge_research/24_EXECUTION_PLAN_2026-11-23.md:216-255`).

### PENNY_STOCK (SIRI, F, NIO, LCID, PLUG, RIG, TELL, GPRO)

**Verdict: MEASURABLE in principle (same IEX path, since these are US-listed equities), but currently BLOCKED_MISSING_DATA for a usable sample.**

- No penny quote source is wired. The artifact's universe is a convenience list constructed by the task
  (`PENNY_UNIVERSE_CONSTRUCTED`); the tool's earlier comment "no penny-name series exists" is
  contradicted by `data/penny_universe_seed.json` existing on main (59 symbols), though that is a
  static universe list, not quote data. No penny price cache exists on main.
- The tick-truncation problem is the real blocker: on cheap names the quote grid is coarser than the
  price move, so a 0.00 bar-range is truncation, not a free spread ([`measure_spread()`](tools/equity_cost_measure.py:191),
  `tick_truncation`). The 21.3 bp median survived that filter (7/8 clean, TELL `empty`), but it is a survivor-biased convenience sample.
- Minimum unblock: historical NBBO (or at least per-venue quotes) for a point-in-time penny universe.
  Same acquisition as BOND's true-NBBO path.

## Secrets inventory (names only)

From `git grep -o "secrets\.[A-Za-z0-9_]*" origin/main -- .github/workflows`. Quote-relevant names:
`TIINGO_API_KEY`, `POLYGON_API_KEY`, `FINNHUB_API_KEY`, `ALPHAVANTAGE_API_KEY`, `ALPHA_VANTAGE_API_KEY`,
`ALPHA_VANTAGE_KEY`, `TWELVE_DATA_API_KEY`, `FMP_API_KEY`, `MASSIVE_API_KEY`, `FRED_API_KEY`,
`EIA_API_KEY`, `COINBASE_API_KEY`, `KRAKEN_API_KEY`, `KUCOIN_API_KEY`, `BINANCE_API_KEY`,
`PAPER_BROKER_API_KEY`, `REAL_BROKER_API_KEY`. Infrastructure names (`GH_PAT`, `MYSQL_PASSWORD`,
`DB_PASS_STOCKS`, `FTP_PASS`, `DISCORD_WEBHOOK_URL`, …) are omitted. No key value was read or printed.
**No NBBO/SIP/consolidated-tape/Databento/CME secret exists.**

## Does further cost refinement change any verdict? (blunt)

**For BOND and COMMODITY_FUTURES: no. Cheaper measurement cannot flip either.**
Both bond momentum (B1/B2/B3) and commodity momentum (V1/V2/V3) have break-even cost
**≤ 0 bp/side** ([`docs/edge_research/22_FINAL_SYNTHESIS_2026-11-22.md:36-37,142-143`](docs/edge_research/22_FINAL_SYNTHESIS_2026-11-22.md:142)).
With `c* ≤ 0` and any positive cost `cost > 0 ≥ c*`, net return is negative at *every* positive
cost, so a tighter NBBO estimate (smaller cost) moves the number toward zero but never past a
non-positive break-even. The BOND measured 1.2125 bp and COMMODITY measured 6.3182 bp are already
irrelevant to the kill. Even a hypothetical 0 bp NBBO leaves them at break-even or worse.

**For PENNY_STOCK: no, not with any number this repo could produce.** PENNY has no strategy and no
backtest, hence no break-even: `docs/edge_research/24_EXECUTION_PLAN_2026-11-23.md:370-388` records
`N = 0`, `aggregate: null`, and a frozen kill rule that fires while 0 penny instruments have a
measured spread. A better spread estimate would finally give the class a measured cost, but with
`N = 0` there is nothing to evaluate against it. Refining 21.3 bp to, say, 8 bp cannot change a verdict
that does not exist yet. It could only matter *after* a penny strategy and its break-even are
pre-registered and backtested, which is a separate, larger piece of work.

## Deliverables and process notes

- Base: clean detached worktree at `origin/main` = `f67840d1ebe09febaaa7d83ce656f4fcbc1a9805`.
- Branch: `research/nbbo-measurability-2026-11-23`, one file (this document), unmerged.
