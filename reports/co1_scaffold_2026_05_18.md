# CO-1 Scaffold — Physical Commodity Inventory Surprise (H-027) — 2026-05-18

**Author:** Claude Opus 4.7 (1M ctx)
**Goal:** Goal #1 — find genuine statistical edge per asset class on `findtorontoevents.ca/audit`.
**Status:** UNTESTED scaffold. Opt-in research sidecar. No production code changed, no wiring.

---

## What was built

CO-1 is the #2-ranked of 14 proposals in
`reports/new_strategy_proposals_2026_05_18.md` — a strong physical causal
mechanism, free data, no banned/arbitrage flag. COMMODITY is the system's best
class, but every commodity strategy in the ledger is a *price/positioning
overlay* (seasonal momentum, gold safe-haven, metals mean-reversion,
DXY-inverse, COT). CO-1 reads the *physical-world primitive* instead.

This scaffold delivers the **research sidecar only** — it does NOT touch any
production pick path:

1. **`tools/co1_commodity_inventory_surprise_research.py`** — a runnable,
   standalone research module. It fetches free inventory + price data, computes
   the CO-1 signal, runs a FULL continuous-position cross-sectional backtest,
   gates the result through `edge_stability_harness` (imported UNMODIFIED),
   applies a post-cost gate, and writes a backtest-style report. It is an opt-in
   sidecar with **no caller in any pick-generation or scoring path**
   (`quality_gates.py`, `dashboard_generator.py`, `passes_active_gate`,
   `calculate_smart_score`, `production_scanner`, etc.).

2. **`reports/hypothesis_registry.json`** — CO-1 pre-registered as **H-027**
   (next free id; H-001..H-026 were taken — verified across every array in the
   registry), `status: UNTESTED`, under a new top-level
   `co1_commodity_inventory_surprise` array. Filed per M-107 BEFORE any data is
   touched.

3. **This doc** — `reports/co1_scaffold_2026_05_18.md`.

### The signal

Physical commodity prices are anchored to *inventory levels*. The published
EIA weekly petroleum/natgas stocks, USDA WASDE crop stocks, and LME/COMEX
warehouse stocks are scheduled reports whose **surprise vs expectation** moves
the curve. The ledger's `oil_inventory_momentum` strategy uses a
*price-momentum proxy* for inventory — CO-1 uses the **actual published
inventory number**.

- `inventory_surprise(W) = actual_stocks(W) - expected_stocks(W)`.
- `signal_z` = rolling 26-observation strictly-past z-score of the surprise.
- direction: a DRAW vs expectation (`z<0`, bullish supply news) -> LONG the
  commodity ETF proxy; a BUILD vs expectation (`z>0`, bearish) -> SHORT.
  `direction = -sign(z)`.
- harness score field = `|signal_z|` (conviction magnitude).

**Causal mechanism:** inventory is the single most direct supply/demand balance
indicator for a physical commodity (Deaton-Laroque storage / convenience-yield
theory). A draw vs an expected build is a genuine fundamental surprise. The
proposal flags one risk — the headline move is fast — mitigated here by trading
the slower-adjusting ETF proxy (USO/UNG/DBA) on the multi-day drift, not the
report-day spike.

### Consensus vs the trailing-seasonal proxy — honest disclosure

The "surprise" is `actual - consensus`. A real analyst-consensus inventory feed
(API/Reuters survey of forecasts) is **NOT free**. So CO-1 uses a **documented
`seasonal_proxy` expectation** — the trailing-seasonal blend of the same
calendar week ~52 weeks earlier (strictly-past seasonal anchor) and the recent
4-week trailing trend, built only from strictly-past published numbers.

This is **NOT a real consensus surprise**. It is labelled `seasonal_proxy`
everywhere it appears (module docstring, registry `consensus_mode` /
`consensus_disclosure`, report VERDICT section, cache file). A genuine consensus
feed would sharpen the signal and would constitute a *different test*. The
verdict layer says so explicitly.

### Data sources — free only

- **EIA open-data API** `api.eia.gov/v2` — weekly petroleum + natural-gas
  inventory series. EIA issues a free registration key; the module reads it
  from the `EIA_API_KEY` environment variable and never hard-codes it. The v2
  API also serves some series without a key as a fallback.
- **USDA NASS / WASDE** — free, no key (crop ending-stocks). Documented as the
  canonical free route for agricultural proxies (DBA).
- **LME / COMEX warehouse stock reports** — free public daily/weekly.
  Documented as the canonical free route for base-metals proxies (DBB).
- **yfinance** — free, no-key daily price series for the commodity ETF proxies.

No paid feed, no hard-coded key. If every free source fails the module degrades
to a clearly-labelled synthetic series and reports `UNTESTED-data-gap` — it
never fabricates a pass.

---

## How to run it

```bash
# full run (6 commodity ETF proxies) — writes the report
python tools/co1_commodity_inventory_surprise_research.py

# fast smoke (3 proxies: USO / UNG / UGA)
python tools/co1_commodity_inventory_surprise_research.py --quick

# machine-readable verdict only
python tools/co1_commodity_inventory_surprise_research.py --json

# re-fetch free data, ignoring the cache
python tools/co1_commodity_inventory_surprise_research.py --refresh-cache
```

Output report: `reports/co1_commodity_inventory_surprise_research_2026-05-18.md`.
Data cache: `tools/cache/co1_commodity_inventory_surprise_cache.json`.

The verdict is one of `ADMISSIBLE`, `REJECTED`, or `UNTESTED-data-gap`. A gaudy
in-sample WR is NOT a pass — only the harness + post-cost verdict counts.

**Known data caveats:**
- A free `EIA_API_KEY` is required for live EIA petroleum/natgas series — set
  it in the environment before a real run. Without it (or offline) the
  petroleum/natgas proxies fall back to a labelled synthetic series.
- The USDA WASDE and LME warehouse free parsers are **documented but not yet
  wired** — DBA/DBB therefore run as synthetic until those parsers are added,
  which forces `UNTESTED-data-gap` whenever they are in the universe.
- The expectation is the documented **trailing-seasonal proxy**, not a real
  analyst consensus. A real consensus feed is the first upgrade before any
  wire-up consideration.

---

## Wiring Plan

CO-1 is an **opt-in sidecar today** and stays that way until it clears the
harness gate. Per the CLAUDE.md Wire-Up Rule, here is the explicit wire-up path:

- **Target caller file:** `audit_trail/quality_gates.py`
- **Target function:** `passes_active_gate(...)` — the production pick gate.
  CO-1 would contribute an `inventory_surprise_zscore` feature read by the gate
  for `asset_class == "COMMODITY"` picks (and surface in
  `audit_trail/dashboard_generator.py::calculate_smart_score` as a scoring
  input).
- **Pre-wire-up harness-gate condition (HARD GATE — all must hold):**
  1. `tools/co1_commodity_inventory_surprise_research.py` must report
     `VERDICT: ADMISSIBLE` — `edge_stability_harness.is_admissible()` returns
     `True`: `|eff| >= 0.30`, **same sign**, in `>= 3 of 5` walk-forward 14-day
     windows, each window `>= 80` records.
  2. The post-cost gate must PASS — net edge retains `>= 60%` of gross after a
     12bps commodity-ETF round-trip.
  3. The run must NOT be on a synthetic/offline fallback series — it must use a
     live EIA inventory tape, with the USDA WASDE + LME warehouse free parsers
     wired so DBA/DBB are real, not synthetic.
  4. The expectation must be re-tested against a **real analyst-consensus
     inventory feed** (not the trailing-seasonal proxy) — the proxy run only
     pre-screens; a consensus-based run is the genuine test.
  5. A fresh **out-of-sample** re-test on data collected after the
     `data_sample_lock` must also clear (1)+(2).
  6. A deflated-Sharpe / SPA multiple-testing correction and operator sign-off.
- **If any condition fails:** archive the H-027 config, mark the registry row
  `REJECTED`, record the `next_step`, and **do NOT re-test the same
  construction on the same sample** (M-107). A real-consensus run is a distinct
  test and is permitted; a re-run of the seasonal-proxy construction is not.
  No wiring.

Until (1)-(6) all hold, CO-1 has **zero production callers** and changes **zero
production behaviour**.

---

## Current status

| Item | State |
|---|---|
| Hypothesis id | **H-027** |
| Registry status | `UNTESTED` (pre-registered, M-107 compliant) |
| Research module | built, standalone, opt-in sidecar |
| Consensus source | **trailing-seasonal proxy** (no free real consensus feed) |
| Production wiring | **none** — and none until the harness gate passes |
| Backtest verdict | not yet run / pending live EIA tape + real consensus feed |

This is an **UNTESTED scaffold**. The base rate is poor (8-11 prior harness
kills); CO-1 earns a production wire-up only by clearing the harness + post-cost
gates on real inventory data with a real consensus, never by a sound prior
alone.

---

*Generated 2026-05-18. Sidecar scaffold — no production code modified.
Sources: `reports/new_strategy_proposals_2026_05_18.md` (CO-1 section),
`tools/edge_stability_harness.py`, `reports/hypothesis_registry.json` (M-107),
`tools/et1_etf_creation_redemption_research.py` (sidecar pattern, H-026).*
