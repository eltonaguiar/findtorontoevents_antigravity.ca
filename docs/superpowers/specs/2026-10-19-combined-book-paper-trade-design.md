# Design: Standalone Combined-Book Paper-Trade Sleeve (+ Backtest Harness)

- **Date:** 2026-10-19
- **Status:** Draft for user review
- **Owner:** Zoo (Inception Labs coding agent) per guidance from the external Grok pilot.

## 1. Purpose

Implement a self-contained, reproducible simulation of the "combined book" that Grok's
external backtest validated: a **trend-following** sleeve across asset classes, a
**quality/value** sleeve, and a **put-write** sleeve, combined by inverse volatility and
capped at a target book volatility. The module exists to (a) *reproduce* Grok's backtest
numbers on our own data, and (b) run an honest monthly **paper** simulation that reports
`NOT READY` / `READY` / `KILL` verdicts through the plan's go-live gates.

Scope constraints (explicit user guidance):

- **Standalone.** NOT wired into the live `paper_trading` `PortfolioManager` or Redis-bus
  fleet. Integration is deferred until the book passes its gates on live paper months.
- **Paper only.** No real money, no external trades placed anywhere.

## 2. Build order (per Grok guidance)

1. **Backtest harness first** (the "option 3" statistical harness). Reproduce close to
   Grok's published numbers before writing any paper-simulation code:
   - Reproduction targets (1988–2026, research proxies):
     - no overlay: CAGR **8.8%**, Sharpe **1.27**, max DD **−20.5%**
     - 5% overlay: CAGR **6.5%**, Sharpe **1.20**, max DD **−14.4%**
     - coin-flip control: PF ≈ **0.81**, rejected
   - Coin-flip control is **decisively rejected** by the gates.
   - If our numbers diverge materially, investigate and reconcile *first*.
2. **Freeze the rules** into `RULES.md`, record its SHA-256, verify on every run. Any rule
   change starts a new pilot with a reset record.
3. **Paper simulator** — month-end target weights, positions ledger, monthly returns,
   starting positions recorded as of the **2026-09-30 close**.
4. **Monthly gate check** on live paper months only → `NOT READY` / `READY` / `KILL`.

> Reference ledger: starting positions as of the **2026-09-30** close. The external pilot's
> reference rules hash is `d5bed907932009a96d45521c15102cba2092ec9307dfd8367aedf3f21c9fcfd5`;
> our `RULES.md` will hash differently — record our own hash and archive it.

## 3. Frozen rules (for this pilot)

These values are baked into the hashed `RULES.md`; changing any of them starts a new pilot.

| Parameter | Value |
|-----------|-------|
| Starting capital | **$100,000** (fixed; "$100,090" explicitly rejected as a typo) |
| Target book volatility cap | **5%** annualized, chosen by the pre-registered rule below |
| Rebalance cadence | **Monthly** (matches Grok's tests; quarterly would invalidate the numbers) |
| Per-sleeve weight cap | 40% |
| Sleeve combination | inverse-volatility weights |
| Trade cost | 10 bps per trade (trend sleeve) |

Volatility-cap selection rule (pre-registered; implemented in `combiner.py`, not a constant):

> Pick the **highest** target annualized volatility in the **5–10%** range whose
> **pre-2016** backtest maximum drawdown stays within the **−15% kill limit**.
> 6% already hit −16.5%, so **5% wins**. Run this rule on pre-2016 data only;
> do not re-tune on full history.

Go-live gate (all must pass on live paper months):

- ≥ 100 months of data,
- profit factor ≥ 1.5,
- ≥ 50% winning months,
- worst drawdown no deeper than 20%.

Reported alongside the gate: Wilson 95% CI + binomial p-value per win rate, bootstrapped
profit factor (seeded/reproducible), Sharpe vs SPY over identical dates, random-entry
percentile, and a **Deflated Sharpe** that counts every variant tried.

Kill criteria (either alone kills the pilot):

- live paper drawdown worse than **−15%**, or
- at **≥ 24 months**: profit factor < 1.0, OR win rate < 50%, OR Sharpe ≤ 0,
  OR bootstrap P(PF ≤ 1) > 0.5.

## 4. Sleeves (exact instrument universe)

- **Trend-following sleeve.** Liquid ETFs, price vs 1/3/12-month lookbacks blended, each
  position sized to ~10% volatility, monthly rebalance, 10 bps/trade.
  - Stocks: `SPY`, `EFA`, `EEM`, `IWM`
  - Bonds: `TLT`, `IEF`, `SHY`, `LQD`, `HYG`, `TIP`
  - Commodities: `GLD`, `DBC`, `USO`, `SLV`
  - Real estate: `VNQ`

  The trend sleeve may hold a **net short** bond stance on a given month (e.g., short
  TIP/SHY/IEF). Borrow cost on shorts is either modeled explicitly or flagged as
  **unmodeled** in the report. Uninvested cash earns **0%** unless stated otherwise.
- **Quality/value sleeve.** Equal-ish blend of `QUAL`, `VLUE`, `MTUM`, `USMV` (the
  backtest's Ken-French-style portfolios are not directly tradeable).
- **Put-write sleeve.** `PUTW` is delisted → use **`XYLD`** (S&P 500 covered-call ETF) as
  the tradeable proxy; keep the CBOE PUT index (`PUT`) as the backtest return series. If the
  proxy's history is too short, provide a documented simplified short-put approximation and
  tag it as a proxy in the report.

## 5. Architecture / components

New self-contained package at repo root: `combined_book/`.

| Module | Responsibility |
|--------|----------------|
| `rules.py` | Frozen constants, RULES.md generation, SHA-256 hash compute/verify. Refuses to run on hash mismatch (requires reset). |
| `fetch.py` | yfinance historical daily closes/returns for the ETF universe; caching; graceful handling of missing/limited history (document stand-ins). |
| `trend_sleeve.py` | 1/3/12-m lookback trend blend, ~10% vol sizing, monthly rebalance, 10 bps costs. |
| `quality_sleeve.py` | QUAL/VLUE/MTUM/USMV blend returns. |
| `put_sleeve.py` | XYLD tradeable proxy; CBOE PUT index for backtest series (or documented synthetic short-put fallback). |
| `combiner.py` | inverse-vol sleeve weights, 40% cap, book-level 5% volatility cap via the pre-registered selection rule (5–10% range; highest target whose pre-2016 max DD stays within −15%). |
| `simulator.py` | Month-end engine: compute target weights from rules, record positions to ledger, compute monthly returns, build equity curve. |
| `ledger.py` | JSON ledger of positions + monthly returns; records starting positions as of 2026-09-30 close; appends monthly rows. |
| `gates.py` | Go-live + kill gates; Wilson interval, binomial p-value, bootstrapped PF, Sharpe vs SPY, random-entry percentile, Deflated Sharpe. |
| `cli.py` | Commands: `init-ledger`, `run-month`, `backtest`, `gates`, `hash-check`, `report`. |
| `tests/` | Unit + reproduction tests. |

### Data flow

`fetch.py` → sleeves produce monthly return series → `combiner.py` weights → `simulator.py`
iterates month-end to produce equity curve + ledger → `gates.py` evaluates → `report`
(`NOT READY` / `READY` / `KILL`).

### Honesty rules (output always)

- A win rate / profit factor alone prove nothing (plain SPY clears both); the proof is
  risk-adjusted comparison vs SPY and the random-entry test.
- Cards remain `NOT MONEY-READY` until the gate passes; nothing says `ENTER` before then.
- Trend-following did not prove an edge after 2015 → treated as a crisis hedge, not a
  profit source.

## 6. Error handling

- **Fetch failure:** use local cache if fresh; otherwise abort with a clear error; if an
  ETF series is missing/too short, skip that sleeve and surface it in the report (never
  silently fabricate).
- **Hash mismatch:** refuse to run and instruct that a rule change starts a new pilot.
- **Data gaps / stand-ins:** documented explicitly in the report (e.g., older funds standing
  in for missing history).

## 7. Testing

- Unit: lookback blend, ~10% vol sizing, inverse-vol weighting, 40% cap, 5% book-cap
  selection rule, gate math (Wilson, binomial p-value, seedable bootstrap PF, Deflated
  Sharpe), ledger consistency, coin-flip rejection.
- Reproduction: `backtest` output should land near the targets — no overlay CAGR 8.8% /
  Sharpe 1.27 / DD −20.5%; 5% overlay CAGR 6.5% / Sharpe 1.20 / DD −14.4%; coin-flip
  control PF ≈ 0.81 rejected — each within a documented tolerance. Divergence beyond
  tolerance must be investigated before paper-sim code ships.

## 8. Out of scope (now)

- PortfolioManager / Redis-bus fleet integration (deferred until gates pass on live paper
  months).
- Real trading, brokerage hooks, or external order placement.
- Tuning the 5% cap or any rule on full-history data.
