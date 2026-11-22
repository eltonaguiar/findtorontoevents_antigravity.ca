# H-033 EQUITY Industry/Sector Cross-Sectional Momentum — 2026-05-19

_Generated 2026-11-22T08:33:02+00:00 by `tools/h033_equity_sector_momentum_research.py`._

## VERDICT: **UNTESTED-data-gap**

**Status: OPT-IN RESEARCH SIDECAR. No production wiring.** No caller in `quality_gates.py`, `dashboard_generator.py`, `passes_active_gate`, `calculate_smart_score`, or any pick-generation / scoring path. Fetches free public sector-ETF data, writes this report — nothing else.

## The signal

EQUITY industry/sector cross-sectional momentum (Moskowitz-Grinblatt 1999). Universe: the 11 SPDR sector ETFs (XLB / XLE / XLF / XLI / XLK / XLP / XLU / XLV / XLY / XLRE / XLC) — the GICS sector partition of the US large-cap market:

- `momentum_i(D) = close_i(D)/close_i(D-21) - 1` — trailing 21-day return per sector.
- Rank cross-sectionally at the monthly rebalance date; LONG the top-2, SHORT the bottom-2. Equal-weight long-short, held until the next rebalance.
- Optional trend filter (pre-registered): the book is FLAT unless SPY is above its 252-day moving average at the rebalance date. Trend filter THIS RUN: **ON**.
- harness score field = `|cross-sectional momentum z-score|` of the picked sector vs the 11-sector cross-section on the rebalance date (conviction magnitude).

**Causal mechanism:** Moskowitz-Grinblatt (1999) documented industry momentum as a separable risk-premium distinct from individual-stock momentum: industries that have outperformed over 1-12 months continue to outperform over the next 1-3 months. The mechanism is slow information diffusion across the supply chain plus persistent factor exposure shifts (rates, energy prices, credit) that benefit some sectors over multi-month horizons. The optional SPY 12-month trend filter is the documented regime guard — cross-sectional dispersion narrows and the momentum spread inverts in bear markets.

## Construction (legitimate density pattern from H-008/H-019/H-026/H-027)

- **FULL continuous-position long-short book** — top-2 LONG / bottom-2 SHORT every rebalance (subject to the optional trend filter); every (picked_sector, held_day) with a next bar is one resolved record. NO selection of 'big' momentum moves, NO post-hoc threshold — density comes from holding daily, the H-008 pattern, not threshold relaxation.
- **Strict no-look-ahead** — the 21-day momentum used to rank on rebalance date D uses closes strictly through D; positions enter on the bar AFTER D; the 252-day SPY MA is end-anchored at D over its trailing window — no future bars.
- **Turnover-aware cost** — a single 15bps round-trip is charged on the FIRST held day of each rebalance period (in + out across the period), not per-day. Pooled mean reflects the per-bar average.

## Data (free sources only)

- **yfinance** — daily close series for the 11 SPDR sector ETFs and the SPY trend benchmark (free, no key).
- **Sample:** 5828 sector-day resolved records across 73 active rebalances (16 flat by trend filter / data gap).
- All sectors sourced from live free data.

| Sector | records | wins | gross WR | longs | shorts |
|---|---|---|---|---|---|
| XLB | 260 | 135 | 51.9% | 100 | 160 |
| XLE | 1137 | 585 | 51.4% | 577 | 560 |
| XLF | 400 | 204 | 51.0% | 300 | 100 |
| XLI | 320 | 167 | 52.2% | 200 | 120 |
| XLK | 797 | 409 | 51.3% | 480 | 317 |
| XLP | 240 | 108 | 45.0% | 60 | 180 |
| XLU | 637 | 300 | 47.1% | 317 | 320 |
| XLV | 420 | 216 | 51.4% | 160 | 260 |
| XLY | 660 | 337 | 51.1% | 340 | 320 |
| XLRE | 540 | 268 | 49.6% | 200 | 340 |
| XLC | 417 | 225 | 54.0% | 180 | 237 |

## Harness verdict (THE gate — `edge_stability_harness`, UNMODIFIED)

- per-window eff (new->old): ``
- windows scored: 0  (strong 0: +0/-0)
- `is_admissible()`: False
- harness reason: REJECTED — only 0/0 windows reach eff>=0.3

## Post-cost gate (15bps round-trip; net must keep >= 60% of gross)

- gross edge: **2.244 bps/trade**
- net edge (after 15.0bps round-trip): **1.4924 bps/trade**
- cost-survival: **66.51%** (floor 60%)
- post-cost gate: **PASS**

- pooled gross WR: 50.7%
- pooled net WR: 50.4%

## Honest conclusion

**H-033 is UNTESTED — data-gap, explicitly NOT a pass.** The harness scored only 0 fourteen-day window(s); it needs >= 3. This is an honest non-verdict — not a pass and not a clean fail. A real H-033 verdict needs the full yfinance daily close history for all 11 SPDR sector ETFs + SPY.

## next_step

Re-fetch the yfinance daily close history for all 11 SPDR sector ETFs + SPY so the harness has the full ~7-15 year cross-section. Re-run only with the dense tape.
