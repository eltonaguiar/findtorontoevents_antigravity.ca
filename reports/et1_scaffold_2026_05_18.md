# ET-1 Scaffold — ETF Creation/Redemption Share-Count Flow (H-026) — 2026-05-18

**Author:** Claude Opus 4.7 (1M ctx)
**Goal:** Goal #1 — find genuine statistical edge per asset class on `findtorontoevents.ca/audit`.
**Status:** UNTESTED scaffold. Opt-in research sidecar. No production code changed, no wiring.

---

## What was built

ET-1 is the #1-ranked of 14 proposals in
`reports/new_strategy_proposals_2026_05_18.md` — the cleanest mechanism,
genuinely-new primary-market input, lowest effort, no banned/arbitrage flag.

This scaffold delivers the **research sidecar only** — it does NOT touch any
production pick path:

1. **`tools/et1_etf_creation_redemption_research.py`** — a runnable, standalone
   research module. It fetches free ETF data, computes the ET-1 signal, runs a
   FULL continuous-position cross-sectional backtest, gates the result through
   `edge_stability_harness` (imported UNMODIFIED), applies a post-cost gate, and
   writes a backtest-style report. It is an opt-in sidecar with **no caller in
   any pick-generation or scoring path** (`quality_gates.py`,
   `dashboard_generator.py`, `passes_active_gate`, `calculate_smart_score`,
   `production_scanner`, etc.).

2. **`reports/hypothesis_registry.json`** — ET-1 pre-registered as **H-026**
   (next free id; H-001..H-025 were taken), `status: UNTESTED`, under a new
   top-level `et1_etf_creation_redemption` array. Filed per M-107 BEFORE any
   data is touched.

3. **This doc** — `reports/et1_scaffold_2026_05_18.md`.

### The signal

When an ETF's **shares outstanding** rises, an Authorized Participant created
new units — committed primary-market capital flowing into the basket. A falling
share count = redemption = outflow.

- `net_creation_flow(D) = (shares_out(D) - shares_out(D-10)) / shares_out(D-10)`
  — the 10-day AP creation/redemption share-count delta.
- `signal_z` = rolling 30-observation strictly-past z-score of the net creation
  flow.
- direction (momentum): `z>0` (persistent net creation = institutional inflow)
  -> LONG; `z<0` (persistent net redemption = outflow) -> SHORT.
- harness score field = `|signal_z|` (conviction magnitude).

**Causal mechanism:** creation/redemption is executed by APs and large
allocators — a revealed institutional-flow signal with no behavioural noise.
Persistent net creation into a sector/thematic ETF is a momentum-of-capital
signal that may lead the basket. The data is free but scattered across issuer
sites / N-PORT filings — assembly cost is the only moat. Mega broad-market funds
are excluded because their creation/redemption is mechanical index rebalancing,
not a view.

### Data sources — free only

- **yfinance** — daily ETF close series + `sharesOutstanding` scalar (no key).
- **SEC EDGAR `data.sec.gov`** — N-PORT-derived shares-outstanding facts per
  fund registrant (no key, SEC-UA required).
- **Issuer fund pages** (SPDR / iShares / Vanguard / Invesco) — publish daily
  shares-outstanding; documented as the manual-fetch fallback for a denser
  tape.

No paid feed, no API key. If every free source fails the module degrades to a
clearly-labelled synthetic series and reports `UNTESTED-data-gap` — it never
fabricates a pass.

---

## How to run it

```bash
# full run (~20 thematic/sector ETFs) — writes the report
python tools/et1_etf_creation_redemption_research.py

# fast smoke (5 ETFs)
python tools/et1_etf_creation_redemption_research.py --quick

# machine-readable verdict only
python tools/et1_etf_creation_redemption_research.py --json

# re-fetch free data, ignoring the cache
python tools/et1_etf_creation_redemption_research.py --refresh-cache
```

Output report: `reports/et1_etf_creation_redemption_research_2026-05-18.md`.
Data cache: `tools/cache/et1_etf_creation_redemption_cache.json`.

The verdict is one of `ADMISSIBLE`, `REJECTED`, or `UNTESTED-data-gap`. A gaudy
in-sample WR is NOT a pass — only the harness + post-cost verdict counts.

**Known data caveat:** N-PORT shares-outstanding is filed *monthly*. The module
forward-fills it onto the daily grid (strictly-past, no look-ahead). A true
ET-1 verdict needs a *daily* issuer share-count tape; until that is sourced the
honest verdict is likely `UNTESTED-data-gap`. yfinance exposes only a current
`sharesOutstanding` scalar, not the historical tape.

---

## Wiring Plan

ET-1 is an **opt-in sidecar today** and stays that way until it clears the
harness gate. Per the CLAUDE.md Wire-Up Rule, here is the explicit wire-up path:

- **Target caller file:** `audit_trail/quality_gates.py`
- **Target function:** `passes_active_gate(...)` — the production pick gate.
  ET-1 would contribute an `etf_creation_flow_10d_zscore` feature read by the
  gate for `asset_class == "ETF"` picks (and surface in
  `audit_trail/dashboard_generator.py::calculate_smart_score` as a scoring
  input).
- **Pre-wire-up harness-gate condition (HARD GATE — all must hold):**
  1. `tools/et1_etf_creation_redemption_research.py` must report
     `VERDICT: ADMISSIBLE` — `edge_stability_harness.is_admissible()` returns
     `True`: `|eff| >= 0.30`, **same sign**, in `>= 3 of 5` walk-forward 14-day
     windows, each window `>= 80` records.
  2. The post-cost gate must PASS — net edge retains `>= 60%` of gross after a
     10bps ETF round-trip.
  3. The run must NOT be on a synthetic/offline fallback series — it must use a
     dense daily issuer shares-outstanding tape.
  4. A fresh **out-of-sample** re-test on data collected after the
     `data_sample_lock` must also clear (1)+(2).
  5. A deflated-Sharpe / SPA multiple-testing correction and operator sign-off.
- **If any condition fails:** archive the H-026 config, mark the registry row
  `REJECTED`, record the `next_step`, and **do NOT re-test the same construction
  on the same sample** (M-107). No wiring.

Until (1)-(5) all hold, ET-1 has **zero production callers** and changes **zero
production behaviour**.

---

## Current status

| Item | State |
|---|---|
| Hypothesis id | **H-026** |
| Registry status | `UNTESTED` (pre-registered, M-107 compliant) |
| Research module | built, standalone, opt-in sidecar |
| Production wiring | **none** — and none until the harness gate passes |
| Backtest verdict | not yet run / pending dense daily share-count tape |

This is an **UNTESTED scaffold**. The base rate is poor (8-11 prior harness
kills); ET-1 earns a production wire-up only by clearing the harness + post-cost
gates on real data, never by a sound prior alone.

---

*Generated 2026-05-18. Sidecar scaffold — no production code modified.
Sources: `reports/new_strategy_proposals_2026_05_18.md` (ET-1 section),
`tools/edge_stability_harness.py`, `reports/hypothesis_registry.json` (M-107),
`tools/h020_cross_exchange_premium_research.py` (sidecar pattern).*
