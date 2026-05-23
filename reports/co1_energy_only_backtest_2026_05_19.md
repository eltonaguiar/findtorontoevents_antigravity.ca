# CO-1 Physical Commodity Inventory Surprise (H-027) — 2026-05-18

_Generated 2026-05-19T03:48:39+00:00 by `tools/co1_commodity_inventory_surprise_research.py`._

## VERDICT: **UNTESTED-data-gap**

**Status: OPT-IN RESEARCH SIDECAR. No production wiring.** No caller in `quality_gates.py`, `dashboard_generator.py`, `passes_active_gate`, `calculate_smart_score`, or any pick-generation / scoring path. Fetches free public inventory + price data, writes this report — nothing else.

## The signal

Physical commodity inventory surprise — the published EIA/USDA/LME inventory number vs expectation, NOT the price-momentum proxy that `oil_inventory_momentum` currently uses:

- `inventory_surprise(W) = actual_stocks(W) - expected_stocks(W)` — the published weekly inventory level minus the expectation.
- `signal_z` = rolling 26-observation strictly-past z-score of the inventory surprise.
- direction: a DRAW vs expectation (`z<0`, bullish supply news) -> LONG; a BUILD vs expectation (`z>0`, bearish) -> SHORT. `direction = -sign(z)`.
- harness score field = `|signal_z|` (conviction magnitude).

**Consensus / expectation — honest proxy disclosure:** the surprise is `actual - consensus`. A real analyst-consensus feed (API/Reuters poll) is NOT free, so CO-1 uses a DOCUMENTED `seasonal_proxy` expectation — a trailing-seasonal blend (same calendar week ~52 weeks earlier + recent trailing-trend), built only from strictly-past published numbers. This is NOT a real consensus surprise; a genuine consensus feed would sharpen the signal. The proxy is labelled as such everywhere it appears.

**Causal mechanism:** inventory is the single most direct supply/demand balance indicator for a physical commodity. A draw vs an expected build is a genuine fundamental surprise. The proposal flags one risk — the headline move is fast — mitigated here by trading the slower-adjusting ETF proxy (USO/UNG/DBA) and the multi-day drift, not the report-day spike.

## Construction (legitimate density pattern from H-008/H-019/H-020/H-026)

- **FULL continuous-position cross-sectional book** — one resolved record per proxy per day, NO `|z|` self-selection, NO sparse event filter. This is the H-008 density pattern, not threshold relaxation.
- **Strict no-look-ahead** — weekly inventory carries a known publication lag (~5 days). Each value is stamped at its PUBLICATION date; a position on day D may see only surprises PUBLISHED strictly before D; entry D+1; return realized over price close(D)->close(D+1). Weekly publications are forward-filled (strictly-past) onto the daily grid.

## Data (free sources only)

- **EIA open-data API** `api.eia.gov/v2` — weekly petroleum + natural-gas inventory series (free registration key, read from the `EIA_API_KEY` env var; never hard-coded).
- **USDA NASS / WASDE** — free, no key (crop ending-stocks; documented route for agricultural proxies).
- **LME / COMEX warehouse stock reports** — free public daily/weekly (documented route for base-metals proxies).
- **yfinance** — free, no-key daily price series for the ETF proxies.
- **Sample:** 13377 proxy-day resolved records.
- All proxies sourced from live free data.

| Proxy | records | wins | gross WR | surprise obs |
|---|---|---|---|---|
| USO | 5057 | 2531 | 50.0% | 2224 |
| UNG | 3737 | 1873 | 50.1% | 802 |
| UGA | 4583 | 2208 | 48.2% | 1845 |

## Harness verdict (THE gate — `edge_stability_harness`, UNMODIFIED)

- per-window eff (new->old): ``
- windows scored: 0  (strong 0: +0/-0)
- `is_admissible()`: False
- harness reason: REJECTED — only 0/0 windows reach eff>=0.3

## Post-cost gate (12bps round-trip; net must keep >= 60% of gross)

- gross edge: **-0.3989 bps/trade**
- net edge (after 12.0bps round-trip): **-12.3989 bps/trade**
- cost-survival: **0.0%** (floor 60%)
- post-cost gate: **FAIL**

- pooled gross WR: 49.4%
- pooled net WR: 47.3%

## Honest conclusion

**CO-1 is UNTESTED — data-gap, explicitly NOT a pass.** The harness scored only 0 fourteen-day window(s); it needs >= 3. This is an honest non-verdict — not a pass and not a clean fail. A real CO-1 verdict needs live EIA weekly stocks (free key in `EIA_API_KEY`), the USDA WASDE + LME warehouse free parsers wired, and ideally a real analyst-consensus feed in place of the trailing-seasonal proxy.

## next_step

Provision a free EIA_API_KEY and wire the USDA WASDE + LME warehouse free parsers so DBA/DBB are real, not synthetic. Re-run only with the live inventory tape.
