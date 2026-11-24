# 2026-11-16 — MUTUAL_FUND asset class registered with a daily-NAV data path

**Request.** Add mutual funds as a real class on /audit with NAV data and an
honest empty-or-unproven verdict.

## What was missing

`MUTUAL_FUND` was not a registered class anywhere in the pipeline: 0 rows and
0 payload strings, class id -1 in the ML gate, and the separate
`ejaguiar1_mutual_funds` DB unreachable (1045). Even if a fund were emitted it
could not be priced — the resolver fetches `interval="1h"` OHLCV, which is
empty for a `MUTUALFUND` ticker.

## What changed

**Registration**
* `alpha_engine/mutual_fund_nav.py` (new) owns `MUTUAL_FUND_SYMBOLS` (28 no-load
  core funds across Vanguard/Fidelity/Schwab/TRP/PIMCO) and `is_mutual_fund()`.
* `alpha_engine/asset_class.py`: category map (`mutual_fund`, `mutual_funds`,
  `nav_fund`), `_LOWER_TO_UPPER`, symbol checks in `asset_class_from_symbol`
  and `normalize_asset_class` (before the equity fallback).
* `audit_trail/asset_classification.py`: `AssetClass.MUTUAL_FUND`, an
  `AssetConfig` (10% TP / 5% SL, 8% max SL distance, vol factor 0.3), a guard in
  `classify_asset()`, and `ASSET_CLASSES`.
* `alpha_engine/money_ready_verdict.py`: class added to
  `CANONICAL_ASSET_CLASSES`, `CLASS_WR_FLOORS` (0.45) and `SLIPPAGE_BPS` (8).
* `audit_trail/quality_gates.py`: `ASSET_CLASS_SMART_THRESHOLDS["MUTUAL_FUND"]`
  (`min_score 40`, `min_fwr 0.50`, `min_trades 0`).
* `audit_trail/dashboard_generator.py`: added to `_PER_ASSET_CLASSES` (so the
  class is emitted even with zero rows), both `_CANONICAL` sets, the non-crypto
  sets and the asset-class × timeframe grid.
* `audit_dashboard/template.html`: class filter lists, tile, `MF` mini-badge and
  non-crypto branches.

**NAV data path**
* `fetch_nav()` reads daily closes (the fund's NAV) via yfinance, computes
  latest/previous NAV and daily change, and caches to
  `alpha_engine/data/mutual_fund_nav_cache.json` with a 12 h TTL. It fails open
  (returns `None`) rather than fabricating a price.
* `audit_trail/universal_pick_resolver.py`: when a symbol has no spot price and
  is a fund, `current_price` comes from NAV, and the pick records
  `price_source="mutual_fund_nav"` + `nav_date`. Holdings get a 168 h
  (`MAX_HOLD_HOURS_BY_CLASS`) window because funds settle once a day.
* `fetch_navs()` + CLI refresh the whole universe.

**Honest verdict**
* `_build_per_asset_quality_summary` previously set `thresholdPass=true` for any
  class with `activeCount == 0` — the reason BOND showed a green pass on an
  empty book. Empty classes now report **false**: the class appears with
  `activeCount 0`, `smartCount 0`, `thresholdPass false`, and money-ready emits
  `INSUFFICIENT_DATA` / `sizing_allowed=false`.

## Verification

```
python -m py_compile  ... (7 modules)                                  # OK
python -m pytest -q tests/test_mutual_fund_nav.py tests/test_asset_class.py
```
* `asset_class_from_symbol("VFIAX") -> mutual_fund`; `FXAIX -> MUTUAL_FUND`;
  `SPY -> etf`, `TLT -> bond`, `AAPL -> equity`, `EURUSD=X -> forex`,
  `CL=F -> futures` unchanged.
* `_build_per_asset_quality_summary([], [], ...)` returns
  `MUTUAL_FUND: activeCount 0, smartCount 0, thresholdPass False`, and no empty
  class passes.
* All inline `<script>` blocks in `template.html` pass `node --check`.

## Limits

No picks are emitted for the class: this registers the universe, the NAV data
path and the honest verdict, nothing more. NAV comes from yfinance daily closes
(T+0 close published after the session), so a same-day mark may be one day
stale; the cache TTL is 12 h. No real-money claim is made for the class.
