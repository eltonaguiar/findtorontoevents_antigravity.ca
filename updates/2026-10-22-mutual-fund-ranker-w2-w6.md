# Mutual Fund Rating System — W2 Viewer + W3–W6 (2026-10-22)

## What this covers
Completes the §5.2 mutual-fund rating implementation for the Audit Dashboard:

- **W2** — `/audit/mutual-funds.html` viewer (new), consuming `audit_dashboard/data/mutut_fund_rankings.json`.
- **W3** — `sizing_grade` (A–D) illustrative capacity badge, emitted by the ranker and surfaced in the viewer.
- **W4** — freshness multiplier on the composite score (no penalty within 7 days of last NAV; linear decay to 0.5× after 90 days stale).
- **W5** — hard Tier-1/Tier-2 history gate: n_months ≥ 100 or the fund is demoted to T3 Reject.
- **W6** — provenance columns (`origin`, `resolve_method`) written at emit time.

## What was broken / why
The ranker (`alpha_engine/mutual_fund_ranker.py`) previously emitted only the composite score + tier with no capacity/freshness/provenance metadata. The viewer did not exist, so the ranking output was not browsable. Key earlier bugs already fixed this session (documented separately):

- `_fetch_nav()` returned an empty dict — yfinance v1.3.0 MultiIndex columns made `raw["Close"]` a DataFrame (not a Series), causing `AttributeError: 'DataFrame' object has no attribute 'dtype'` to be swallowed by a blanket `except`. Fixed with `raw[("Close", tk)]` + `xs()` fallback.
- AUM gate constant was 100.0 (interpreted as $100B) instead of 0.10 ($100M).
- `_pct_rank` could exceed 100; sortino was ranked against the sharpe distribution.
- Clone dedup was global (dropped distinct styles) and metadata-order-dependent (kept the wrong clone).

## What changed
### `alpha_engine/mutual_fund_ranker.py`
- Added `MIN_TIER2_MONTHS = 100`, `_sizing_grade()`, `_freshness_multiplier()`.
- In `compute_rankings()`:
  - Compute `nav_through_str` once per fund and a `freshness` multiplier.
  - `adjusted_score = score * freshness` gates tier assignment (T1 ≥ 80, T2 ≥ 65).
  - W5 demotion after tier decision for n_months < 100.
  - Emit new fields: `score` (adjusted), `composite_raw`, `freshness_multiplier`, `sizing_grade`, `origin`, `resolve_method`.

### `audit_dashboard/mutual-funds.html` (new viewer)
- Dark theme matching site tokens (`--bg/--card/--border/--text/--green/--red/--yellow/--cyan/--purple`, Segoe UI).
- Summary cards from `tier_counts`; tier/category/index filter bar; sortable sticky-header table.
- Columns: tier badge, ticker, name (+index chip), category, **Sizing grade badge**, composite score bar, factor breakdown, expense, AUM, months, NAV-thru, Sharpe, Sortino, max-DD, status/reject reason.
- Methodology footnote documents the composite weights, freshness multiplier, and provenance.
- JS escaping: the source must not contain literal `&`/`'` sequences (the write pipeline decodes HTML entities), so `esc()` concatenates entities via `'&' + 'amp;'` etc.

## Verification
- `python3 -m alpha_engine.mutual_fund_ranker` → `T1=1 T2=8 T3=28`; first fund now includes `sizing_grade="A"`, `origin`, `resolve_method`, `freshness_multiplier=1.0`, `composite_raw=87.1`, `score=87.1`.
- Playwright (local server, `tools/serve_local.py`, port 5173): page 200, JSON 200, `#fund-body` renders 37 rows, tier counts `{T1:1, T2:8, T3:28}`, 15 header cells, SWPPX row shows sizing badge `A`, methodology contains "Sizing grade" and "Provenance", **no console/page errors**.
- `py_compile` passes on the ranker. Temporary check scripts removed.

## Notes
- Freshness multiplier is currently 1.0 because NAV data is fresh; it only visibly penalizes when data goes stale (verified logic, not artificially reshuffling healthy data).
- W5 gate does not change current tier counts because all rated funds have 120 months of NAV.

*Not financial advice. Research/educational only. Past performance does not guarantee future results.*
