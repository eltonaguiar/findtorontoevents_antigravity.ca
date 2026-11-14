# BOND — Quick-Win Fix Proposals

Verified 2026-11-14 (live payload). Micro-audit for the BOND asset class.

## Class Verdict

**STALE** — seeds exist (15 OPEN ≈25h old) but are unbackfilled and undercooked: 9 null `current_price`, and the only settled bond trade closed Nov 10 with health `insufficient_data`.

## Evidence

- 15 OPEN seeds ≈25h old; 9 have `current_price` null.
- n=1 closed (settled Nov 10, ≈4d), health `insufficient_data`.
- `active_picks_bond.json` (`bond_scanner` source) confirms 6 SELL seeds with valid entry/tp/sl but no live price enrichment on load.
- Price path exists: `bond_data_fred.py` (FRED + yfinance data `fetch_bond_bundle`/`fetch_fred_series`).

---

## Quick Wins

### QW-B1 — Backfill null current_price for open seeds
- **Problem:** 9 of 15 open BOND seeds have `current_price` null, so live PnL cannot be computed/rendered.
- **Fix:** In the resolver/price path, backfill open BOND picks via `bond_data_fred.fetch_bond_bundle` (or yfinance) instead of leaving `current_price=None`; reuse the same failover as other non-crypto classes.
- **Impact:** High / **Effort:** Low–Medium / **Risk:** Low.
- **Target file(s):** `alpha_engine/bond_data_fred.py`; `audit_trail/universal_pick_resolver.py` (price resolution); `audit_trail/fetch_stock_prices.py` (existing non-crypto fetcher). Verified.

### QW-B2 — Don't surface statistics until a minimum closed sample
- **Problem:** n=1 closed with health `insufficient_data` still feeds BOND class-level stats/funnels.
- **Fix:** Suppress BOND aggregate stats and verdicts until closed n ≥ a configured floor (e.g. 10), consistent with the audit `insufficient_data` health flag.
- **Impact:** Medium / **Effort:** Low / **Risk:** Low.
- **Target file(s):** `audit_trail/dashboard_generator.py` (health/rollup path); `audit_trail/quality_gates.py`. Verified.

### QW-B3 — Age-gate stale seeds at emission
- **Problem:** Seeds are ≈25h old and not refreshed; a growing stale-open set skews class age.
- **Fix:** In `bond_scanner.py` / `bond_emitter_spike.py`, drop or re-scan seeds older than a max-hold window rather than carrying them as OPEN indefinitely.
- **Impact:** Medium / **Effort:** Low / **Risk:** Low.
- **Target file(s):** `alpha_engine/bond_scanner.py`; `tools/bond_emitter_spike.py`. Verified.

### QW-B4 — Verify bond price source wiring end-to-end
- **Problem:** Bonds have a FRED + yfinance path (`bond_data_fred.py`) but no evidence it feeds the open-pick resolver's price enrichment.
- **Fix:** Add/confirm a BOND entry in the resolver's price-enrichment source routing (like `forex`/`futures` already have), and smoke-test one symbol (e.g. HYG/TLT) to confirm `current_price` populates.
- **Impact:** Medium / **Effort:** Medium / **Risk:** Low.
- **Target file(s):** `alpha_engine/universal_price_enricher.py`; `audit_trail/universal_pick_resolver.py`. Verified.

---

## Notes
- All target files verified to exist in this worktree. BOND data source confirmed in `dashboard_generator.py` feed registry (line ~4079, `alpha_engine/data/active_picks_bond.json`).
- Settled-trade sample (n=1) too small for any verdict; flagged `insufficient_data`.
