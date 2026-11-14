# FIX_PROPOSED.md — Mutual Funds Asset Class Gap

**Asset class:** MUTUAL_FUNDS  
**Status:** ZERO coverage — complete absence  
**Target:** Add mutual funds as a first-class asset class in the ML/pick-trading pipeline

---

## 1. Mutual Funds Finding — No Active Pipeline

Audit confirms mutual funds have **no active pick pipeline** anywhere in the system:

- `live_picks.db` asset classes present: STOCKS 5, CRYPTO 101, FOREX 4, BOND 2, EQUITY 6, COMMODITY 5, UNKNOWN 6 — **no mutual fund class**, no mutual fund rows.
- Closed picks (16,771 deduped): **no mutual fund class** anywhere.
- `alpha_engine/asset_class.py`: no `MUTUAL_FUND_SYMBOLS` frozenset; `asset_class_from_symbol()` / `normalize_asset_class()` return `"unknown"` or fall back to `"equity"` for fund tickers (e.g. `VFIAX`, `VTSAX`, `FXAIX`).
- Related but non-emitting files exist: `alpha_engine/mutual_fund_ranker.py` (564 lines) and `alpha_engine/data/mutual_fund_metadata.csv` — neither emits picks nor registers a `MUTUAL_FUND` class, so they do not close the gap.
- `ml_gatekeeper/gatekeeper.py:73` `ASSET_CLASS_MAP = {"CRYPTO": 0, "FOREX": 1, "EQUITY": 2, "COMMODITY": 3, "ETF": 4, "BOND": 5, "FUTURES": 6}` — **no mutual fund entry**. Any mutual fund pick gets `-1` (unknown class) in feature extraction at line 134.
- `alpha_engine/` strategy inventory: `bond_*`, `etf_*`, `equity_*`, `forex_*`, `crypto_*`, `commodities_*`, `futures_*` scanners/strategies exist; **no `mutual_fund_*` scanner or strategy** that emits picks.
- Dashboard grouping (`audit_trail/dashboard_generator.py`) — **no mutual fund tile/bucket** (`_PER_ASSET_CLASSES`, `_CANONICAL`, `_AC_TF_GRID_ASSET_CLASSES`).

**Impact:** Mutual fund picks (if ever emitted) are misclassified as EQUITY/UNKNOWN, dropped by the ML gate (class id -1), and invisible in per-class dashboards. User explicitly requested mutual funds — this is a gap to close.

---

## 2. Quick Wins / Minimal Viable Additions

Minimal, low-risk changes to establish mutual fund support:

1. Add `MUTUAL_FUND_SYMBOLS` frozenset to `alpha_engine/asset_class.py` with a starter universe of common index/active fund tickers (e.g. `VFIAX`, `VTSAX`, `FXAIX`, `VWINX`, `VFSTX`, `PRBLX`, `PIMIX`, `VWELX`, `VANGUARD`/`FIDELITY`/`SCHWAB` share classes).
2. Add `"mutual_fund": "mutual_fund"` to `_CAT_MAP` and `"mutual_fund": "MUTUAL_FUND"` to `_LOWER_TO_UPPER` in `alpha_engine/asset_class.py`.
3. Add mutual fund handling to `asset_class_from_symbol()` and `normalize_asset_class()` so fund symbols classify as `"mutual_fund"` before falling back to equity.
4. Add `"MUTUAL_FUND": 7` to `ASSET_CLASS_MAP` in `ml_gatekeeper/gatekeeper.py:73`.
5. Add `"MUTUAL_FUND"` to `_PER_ASSET_CLASSES` in `audit_trail/dashboard_generator.py:6763` and to `_CANONICAL` / `_AC_TF_GRID_ASSET_CLASSES` so the dashboard renders a mutual fund tile.

These are additive only — no existing class is re-mapped, no existing picks change class.

---

## 3. Proposed Fixes for Mutual Funds

### 3.1 `alpha_engine/asset_class.py`
- Add `MUTUAL_FUND_SYMBOLS: frozenset[str]` (starter universe, extensible).
- Register `"mutual_fund"` in `_CAT_MAP` and `_LOWER_TO_UPPER`.
- In `asset_class_from_symbol()`: check `sym_core in MUTUAL_FUND_SYMBOLS` → return `"mutual_fund"` (place after ETF/commodity/equity or before equity, before the `"unknown"` fallback).
- In `normalize_asset_class()`: same frozenset check in the known-symbol block; also treat `raw_cat == "mutual_fund"` via `_CAT_MAP`.
- Add `MUTUAL_FUND_STRATEGY_HINTS` tuple (`"mutual_fund"`, `"fund_"`, `"index_fund"`, `"vanguard"`, `"fidelity"`) and consult it in `_strategy_hint_class()`.
- Update module docstring / Usage import list and the Returns docstring of `normalize_asset_class` (`crypto | equity | forex | etf | bond | futures | commodity | unknown` → add `mutual_fund`).
- Add `is_mutual_fund(pick)` helper mirroring `is_crypto`/`is_non_crypto`.

### 3.2 `ml_gatekeeper/gatekeeper.py`
- `ASSET_CLASS_MAP`: add `"MUTUAL_FUND": 7` (line 73).
- Feature extraction uses `ASSET_CLASS_MAP.get(..., -1)` at line 134 — mutual fund picks now encode to `7` instead of `-1`.
- Lines 722/958 (CRYPTO gate) and 1084/1172 (STOCK→EQUITY mapping) use string `.upper()` comparison, not `ASSET_CLASS_MAP`, so they are unaffected by the map change but should be audited for mutual fund inclusion separately.

### 3.3 New mutual fund scanner/strategy stub
Create `alpha_engine/mutual_fund_scanner.py` (mirror `alpha_engine/bond_scanner.py` structure):
- CLI: `python -m alpha_engine.mutual_fund_scanner` (signals only) / `--merge` (merge into `active_picks.json`).
- Starter strategies: `mutual_fund_index_core`, `mutual_fund_sector_rotation`, `mutual_fund_mean_reversion` — each returns empty/placeholder signal lists until backfilled with real fund data.
- Data source placeholder: yfinance fund OHLCV + expense-ratio/NAV metadata (stubbed, fail-open).
- Emits picks to `active_picks_mutual_fund.json` with `asset_class="mutual_fund"`, `source_system="mutual_fund_scanner"`.
- Import `MUTUAL_FUND_SYMBOLS` from `alpha_engine.asset_class`.

Also create `alpha_engine/mutual_fund_strategies.py` with the stub strategy functions (mirror `bond_strategies.py` naming convention).

### 3.4 `live_picks.db` metadata
- No schema change strictly required (asset class is a text column), but confirm the DB accepts `"MUTUAL_FUND"` / `"mutual_fund"` as a valid `asset_class` value and that `active_picks_sync.py` / pick-insert paths do not whitelist classes.
- Add `"mutual_fund"` to any class-validation/enum lists in DB write paths if they exist (search for hardcoded class lists in DB insert code).

### 3.5 Dashboard summary grouping (`audit_trail/dashboard_generator.py`)
- `_PER_ASSET_CLASSES` (line 6763): add `"MUTUAL_FUND"`.
- `_CANONICAL` (line 6027) and `_AC_TF_GRID_ASSET_CLASSES` (line 14201): add `"MUTUAL_FUND"`.
- `_normalize_per_asset_class` (line 6766): add alias `"MUTUAL_FUNDS": "MUTUAL_FUND"`.
- `_build_per_asset_quality_summary` (line 6781): picks up the new class automatically via `_PER_ASSET_CLASSES`.
- `market_asset_classes` (line 1628): add `"MUTUAL_FUND"` if fund price fetching is added later; otherwise leave out to avoid price-fetch failures on non-ticker fund symbols.

---

## 4. Verification Steps

1. **Unit check — symbol classification:**
   ```python
   from alpha_engine.asset_class import asset_class_from_symbol, normalize_asset_class, classify_pick_asset_class_upper
   assert asset_class_from_symbol("VFIAX") == "mutual_fund"
   assert asset_class_from_symbol("VTSAX") == "mutual_fund"
   assert asset_class_from_symbol("AAPL") == "equity"   # regression: equity unchanged
   assert normalize_asset_class({"symbol": "VFIAX", "category": ""}) == "mutual_fund"
   assert classify_pick_asset_class_upper({"symbol": "VFIAX"}) == "MUTUAL_FUND"
   ```
2. **Unit check — category metadata wins:**
   ```python
   assert normalize_asset_class({"symbol": "AAPL", "category": "mutual_fund"}) == "mutual_fund"
   ```
3. **Gatekeeper encoding:**
   ```python
   from ml_gatekeeper.gatekeeper import ASSET_CLASS_MAP, extract_features
   assert ASSET_CLASS_MAP["MUTUAL_FUND"] == 7
   f = extract_features({"asset_class": "mutual_fund", ...})
   assert f asset-class index == 7  # not -1
   ```
4. **Dashboard grouping:** confirm `_PER_ASSET_CLASSES` contains `"MUTUAL_FUND"` and a dashboard payload render produces a `MUTUAL_FUND` tile (empty is fine — no crash).
5. **Scanner smoke test:** `python -m alpha_engine.mutual_fund_scanner` runs without error and emits an empty/placeholder `active_picks_mutual_fund.json`.
6. **DB check:** query `live_picks.db` for distinct `asset_class` values — confirm `"MUTUAL_FUND"` is an acceptable insert value (no enum constraint rejection).
7. **Regression:** run existing asset-class test suite (`tests/` if present) to confirm no existing class changed behavior.

---

## 5. Repo Paths Touched

| Path | Change |
|------|--------|
| `alpha_engine/asset_class.py` | Add `MUTUAL_FUND_SYMBOLS`, `_CAT_MAP`/`_LOWER_TO_UPPER` entries, classification logic, `is_mutual_fund()`, strategy hints |
| `ml_gatekeeper/gatekeeper.py:73` | `ASSET_CLASS_MAP` add `"MUTUAL_FUND": 7` |
| `alpha_engine/mutual_fund_scanner.py` | New — mutual fund signal scanner stub |
| `alpha_engine/mutual_fund_strategies.py` | New — stub strategy functions |
| `audit_trail/dashboard_generator.py:6763` | `_PER_ASSET_CLASSES` add `"MUTUAL_FUND"` |
| `audit_trail/dashboard_generator.py:6027` | `_CANONICAL` add `"MUTUAL_FUND"` |
| `audit_trail/dashboard_generator.py:6766` | `_normalize_per_asset_class` alias `"MUTUAL_FUNDS"` |
| `audit_trail/dashboard_generator.py:14201` | `_AC_TF_GRID_ASSET_CLASSES` add `"MUTUAL_FUND"` |
| `live_picks.db` | Confirm `asset_class` text column accepts `"mutual_fund"`; no schema change expected |
| `alpha_engine/active_picks_sync.py` | Verify no class whitelist blocks mutual fund inserts |

**File written:** `updates/2026-11-14-ML-AUDIT-childlike-airport/proposed_fixes/mutual_funds/FIX_PROPOSED.md`
