# 2026-11-23 — `/investments/` hub audited for portability into the audit surfaces

## What was asked

Check the "investment hub" reachable from the main site under "Other Stuff" and decide what is worth
building on, or translating toward `/audit`, `/audit2`, `/audit3`.

## What was read

`investments/index.html` (562 lines) and `investments/all-dashboards.html` — the pages the main
`index.html` links as "investment tools". Both are in-repo; several pages the hub links to are **not**
(`/investments/goldmines/`, `/investments/master_dashboard.html`, `/findmutualfunds/portfolio1/stats.html`,
all `/findstocks/portfolio2/*`), so they are deployed from elsewhere.

## What changed

- **`reports/investment_hub_portability_2026-11-23.md`** — inventory of the hub, a live HTTP status
  probe of its links, the ranked list of what to port, and the list of what to refuse to port.

## What was found

- **Worth porting:** (1) the **Graveyard** as a first-class strip, driven by `hypothesis_registry.json`
  REJECTED/REFUTED entries — the audit reports kills as table rows and never names retired systems;
  (2) the **SHA-256 pre-commitment** pattern applied to the registry + picks files on `/audit2`, which
  turns pre-registration into something a reader can verify instead of trust; (3) a **gainer-autopsy
  card** linking the live winners page to H-237/238 and the newly registered H-239/240; (4) surfacing
  `tools/db_freshness_check.py`'s verdict as a banner; (5) the VIX regime overlay — but only as a
  registered hypothesis, not a knob.
- **Refused:** the hub's self-reported win rates (27.3% on n=44, "2/2 wins", 28.6% forward WR) have no
  CI and no pre-registration; importing them next to gated cells would launder unproven numbers.
  The "Optimal Finder" grid search is the multiplicity machine the programme already measured at
  PBO 0.345 with 0 of 40 cells clearing every gate.
- **Two defects:** the hub states Questrade charges **1.75%** FX conversion while the verified tariff in
  `tools/equity_cost_hml.py` says **1.5%**; and two advertised tools
  (`/findstocks/portfolio2/learning-lab.html`, `/findstocks/portfolio2/daytrader-sim.html`) return **404**.

## Verification

- Live HTTP probes run for 7 hub links: 5× 200, 2× 404 (recorded in the report).
- No site file edited — this is an audit and a recommendation, not a deploy.
- No verdict moves: **0 of 10 classes investable**, unchanged.
