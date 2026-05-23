# Audit what-if: yesterday vs today, HIGH CONVICTION, and asset-class edge (2026-04-23)

## Scope: what “picks” means

**All analysis below refers to the Antigravity audit dashboard only:**  
[https://findtorontoevents.ca/audit](https://findtorontoevents.ca/audit)

That page is built from the same pipeline as `audit_trail/dashboard_generator.py`, which writes `audit_trail/data/dashboard_payload.json`. The browser loads active rows from `picks.active` and closed rows (with a cap) from `picks.recent_closed`. It does **not** refer to the main Toronto events site, FavCreators, or ad-hoc JSON outside this pipeline.

## Data flow (audit)

```
Many system JSONs → collect_all_picks() → quality gates + dedup
  → payload["picks"]["active"] + resolved closed → _build_recent_closed_picks (cap 3500)
  → dashboard_payload.json (deployed with / audit bundle)
  → audit index.html fetches/loads JSON → Active / Smart / Closed / HIGH CONVICTION views
```

**HIGH CONVICTION hero button** (`applyHighConvictionPreset` in `audit_dashboard/template.html`):

- Sets `_convictionOnlyFilter = true` and **`_hcEdgeStrict = true`**.
- Renders the Active tab and applies **`filterHcStrict`**:  
  `filterHighConvictionOrdered` (shared gates in `audit_dashboard/hc_filter.js`) **then** `passesValidatedEdgePerClass` (MERCURYPROMPT 2026-04-14 “validated edge” by asset class).

**Bonds / ETFs / futures / dead commodity in the explainer:**  
`hcEdgeManifest()` and `passesValidatedEdgePerClass` mark BOND (nodata), ETF (dead), FUTURES (dead), and only allow CRYPTO / EQUITY / FOREX through the **strict** second stage. So even if `hc_filter.js` allows an ETF through the shared gates, **`filterHcStrict` removes it** from the list the user sees. That matches the product intent: *review edge by asset class only where a validated filter exists*.

**Doc reference:** [docs/HIGH_CONVICTION_FILTER.md](../docs/HIGH_CONVICTION_FILTER.md) (historical criteria narrative); **authoritative for live UI** is `hc_filter.js` + the two-stage filter in `template.html` above.

## Methodology

1. **Cohort definition:** We attribute each **closed** pick to the **calendar day of its entry timestamp** (`timestamp` at signal time, UTC date prefix), matching how users would have “taken the table as of that day” after resolutions came in.
2. **Data used:** The committed `audit_trail/data/dashboard_payload.json` snapshot (generated at `2026-04-23T19:02:32Z` in the repo at analysis time). `recent_closed` is **capped** at 3500 rows (`MAX_CLOSED_PICKS` in `dashboard_generator.py`) but still includes full coverage for the two days of interest (2026-04-22 and 2026-04-23).
3. **Filters compared:**
   - **All closed** that day (no HC filter) — *not* “ideal”, baseline.
   - **HC (`hc_filter.js` only):** `filterHighConvictionOrdered` — can still include **ETF** (and in principle other non-edge classes) if they pass shared gates.
   - **HC strict (default hero button):** `filterHcStrict` — same as live HIGH CONVICTION with `_hcEdgeStrict`.
4. **Repro:** From repo root:
   ```bash
   node tools/audit_what_if_entry_day.js
   npm run audit:whatif
   ```
   Optional: `--dates 2026-04-22,2026-04-23` or `--payload <path>`.

**Not in scope:** Hindsight oracle (“only take winners”), intraday order of execution, slippage/commissions, or re-running `dashboard_generator.py` on MySQL. Those would change absolute numbers, not the relative ranking of **filter tiers** in this report.

## Results (as of the analyzed payload)

Calendar days (UTC entry date on the `timestamp` field):

| Day | Cohort | Picks (n) | Sum PnL % (arithmetic) | Note |
|-----|--------|-----------|-------------------------|------|
| 2026-04-22 | All closed | 202 | +13.64% | Unfiltered; mixed asset classes. |
| 2026-04-22 | HC only | 17 | +27.61% | Stronger, fewer rows. |
| 2026-04-22 | HC strict (live hero) | 17 | +27.61% | Same 17 as HC only on this day — no ETF in HC set, strict = HC. |
| 2026-04-23 | All closed | 109 | -19.64% | Hard day: crypto and commodity both negative in aggregate. |
| 2026-04-23 | HC only | 16 | -8.55% | 11 crypto + 5 ETF. |
| 2026-04-23 | HC strict (live hero) | 11 | -8.98% | **ETF rows dropped**; only crypto + validated-edge math. |

### Which asset class “won” (by sum `pnl_pct` that day, unfiltered closed)

- **2026-04-22:** **Crypto** had the largest positive contribution (+10.0% across 129 picks); **equity** +3.6% on a single name; **forex** and **commodity** roughly flat in aggregate.
- **2026-04-23:** **Forex** (+0.15%, n=9) and **ETF** (+0.43%, n=5) were the only small positive groups; **crypto** and **commodity** were both negative in aggregate. So “all picks that closed from entries that day” would *not* have been saved by a single-asset focus without filtering — **magnitude was in crypto/commodity losses**.

### Ideal vs UI-feasible

- **Truly “ideal” (not in UI):** ex-post keep only positive-PnL picks — *not* a tradable filter; included only to separate **signal** from **luck**.
- **Best supported workflow on /audit (feasible):** use **HIGH CONVICTION (hero)** so `_hcEdgeStrict` runs → you only see **CRYPTO / EQUITY / FOREX** with MERCURY-validated gates; then optional **asset** dropdown to read each class. **ETF and BOND** do not pass `passesValidatedEdgePerClass` until research upgrades their status in `hcEdgeManifest()` / MERCURY — consistent with the **“No validated filter”** labels in the explainer.
- **Observed quirk (2026-04-23):** Shared HC gates can still let **5 ETFs** into “HC only”; **strict** strips them, leaving **only crypto** and exposing that day as **losing in aggregate** in both modes for that cohort. This shows **tightening from loose HC to strict** can change *composition*, not just size.

## Areas for improvement (by area)

| Area | Current state | Improvement |
|------|----------------|------------|
| **BOND** | `nodata` in explainer, strict rejects | Wait for n≥30+ forward-traded BOND after symbol pipeline fix; add forward metrics to payload row when sample allows. |
| **ETF** | Marked `dead` in explainer; strict rejects; HC-only can still show some | Re-validate in harness (MIMO v2+); if still dead, keep strict rejection and consider down-ranking in **non-strict** path so users aren’t nudged toward PF&lt;1 cohorts. |
| **FOREX** | Validated edge, auto-relax when fwd N&lt;20 | Show **fwdN** in tooltip when relax applies (already in logic in template). |
| **COMMODITY** | `weak` / not in strict | Treat as “monitor only” until CI straddles &gt; 1.0 with confidence. |
| **Data / strategy** | What-if is snapshot + capped `recent_closed` | Add optional `tools/audit_what_if_entry_day.js --full` that loads generator output for full history when run in CI, or a second artifact `recent_closed_all.json` (size tradeoff). |

## Verification

- `node tools/audit_what_if_entry_day.js` exit 0; output matches the tables in this file for the same `dashboard_payload.json` SHA.
- `node tests/test_hc_filter.js` should still pass (unchanged contract).

## Files added

- `tools/audit_what_if_entry_day.js` — reproducible audit-only what-if.
- `package.json` — script alias `npm run audit:whatif`.
