# 05 — QA Plan: 0% PnL Validation & Blank-Field Checks

**Goal:** Determine whether picks showing **0% (or null-equivalent) P/L** and/or **blank/missing fields** are valid, explainable, or suspect — for **open picks** and **recently closed picks (last 30 days, and any pick closed ≤7 days flagged high-priority)**.

## 1. Scope & cohorts
- **Cohort A (open):** `status/state in {ACTIVE, OPEN}` or no terminal exit.
- **Cohort B (recently closed):** exit/close/resolved timestamp within last 30 days (sub-cohort B7: ≤7 days).
- **Signals of concern:** `pnl_pct`/`pnl`/`unrealized_pnl_pct` in {0, 0.0, "0", "0%", null, blank} OR abs(pnl) below rounding epsilon with flat prices; any blank/null in critical fields.

## 2. Critical fields (must not be blank for auditable state)
| Field group | Fields (canonical/examples) | Open required | Recently closed required |
|---|---|---|---|
| Identity | `id/pick_id`, `symbol/ticker`, `asset_class`, `strategy/source_system` | Yes | Yes |
| Direction/sizing | `side/direction`, `quantity/notional` (if applicable) | Yes | Yes |
| Timing | `entry_time/opened_at`, `as_of/mark_time` | Yes | Yes |
| Prices | `entry_price`, `current_price/mark_price` (open), `exit_price` (closed) | entry+mark | entry+exit |
| Risk | `stop_loss`, `take_profit` (if strategy-defined) | expected | record-as-defined |
| Outcome | `status`, `pnl`, `pnl_pct`, `pnl_unit`, `fees/costs`, `resolution_method` | pnl fields may be provisional but must be labeled | Yes, final+labeled |
| Provenance | `price_source/quote_status`, `data_timestamp/freshness` | Yes | Yes |

**Blank =** null, empty string, whitespace, sentinel (`N/A` where value required), or missing key.

## 3. 0% PnL market-data reasonableness validation
For each 0%/null-pnl pick, compute/obtain an **independent expected return** over the relevant window and compare:

1. **Resolve window:** open → `t0 = entry_time`, `t1 = now/mark_time` (must be fresh); closed → `t0 = entry_time`, `t1 = exit_time`.
2. **Fetch reference marks:** primary market data (vendor/API) for `symbol` at/near `t0`,`t1` (adjusted as appropriate: splits/dividends for equities/ETFs/MFs NAV; FX convention; crypto pair). Record `ref_entry`, `ref_exit/current`, `ref_source`, `ref_timestamp`.
3. **Compute expected move:** `exp_ret = side_sign * (ref_1 - ref_0) / ref_0` (net-of-known-costs variant where available). Apply instrument-specific handling (MF = NAV-to-NAV/next-NAV; futures = contract/roll-aware).
4. **Compare to reported:** `delta = |reported_ret - exp_ret|` (treat % vs ratio units explicitly).
5. **Assign disposition (per pick):**
   - `VALIDATED_ZERO` — marks/prices essentially unchanged within tolerance **and** fresh quotes **and** window plausible (e.g. same-bar/NAV, halted/flat) with evidence.
   - `VALIDATED_NONZERO` — reported matches independent calc (non-zero) after unit normalization.
   - `SUSPECT_ZERO_FLAT_BUG` — independent move != 0 beyond tolerance but reported 0% (coercion/unit/stale-mark bug).
   - `SUSPECT_STALE_OR_UNQUOTED` — mark/quote stale (> SLA), missing, or `current_price==entry_price` without market justification.
   - `SUSPECT_BAD_REFERENCE` — entry/exit/side/timestamps inconsistent (e.g. exit before entry, impossible price).
   - `INSUFFICIENT_DATA` — cannot fetch/align reliable reference (must log reason).

**Suggested tolerances (tune per class/liquidity):** crypto ±0.30% or 1.5× half-spread; liquid equity/ETF ±0.20%; FX ±0.10%; MF ±0.05% NAV + fee timing; else mark insufficient if wider unexplained. Always report absolute & relative delta.

## 4. Blank-field validation
- Run schema/required-field checks per cohort; severity: **P0** if identity/side/entry_price/entry_time missing; **P1** if mark/exit/provenance missing; **P2** if optional risk/metadata missing.
- For open picks: blank `current_price/mark_time/quote_status` ⇒ cannot validate PnL → disposition ≥ `SUSPECT_STALE_OR_UNQUOTED`.
- For recently closed: blank `exit_price/exit_time/resolution_method/pnl` ⇒ unresolved/incomplete close → disposition `INSUFFICIENT_DATA` or `SUSPECT_BAD_REFERENCE`.
- Cross-check: timestamps parseable & ordered, prices > 0 (where applicable), asset_class/symbol consistent, status aligns with presence of exit.

## 5. Procedure & outputs
1. **Extract** cohorts A/B from canonical/reconciled sources (DB + dashboard JSON) with source path/row id.
2. **Normalize units** (ratio↔percent) before comparison; record original.
3. **Fetch** independent marks (with caching & provenance); compute expected returns.
4. **Classify** each pick (disposition + reasons + fields missing + severity).
5. **Aggregate:** counts/rates by asset_class/strategy/source/cohort/disposition; list top systemic causes (e.g. stale marks, coercion, missing exit).
6. **Repro:** emit machine-readable report (CSV/JSON) + human summary; include run timestamp, data hashes/snapshots, tolerance config.

**Acceptance:** 100% of open and recently-closed picks have (a) 0%/PnL disposition or non-zero validation result and (b) blank-field audit result; no pick silently labeled “flat/valid” without fresh evidence.

## 6. Immediate red flags (auto-escalate)
- `current_price == entry_price` across many symbols with stale timestamps.
- Large `ref` move but reported 0% (systemic coercion).
- Closed picks with blank `exit_price` or `pnl` yet marked resolved/won/lost.
- Negative/positive PnL sign inconsistent with side & price move.
