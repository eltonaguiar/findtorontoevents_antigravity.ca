# FIX_PROPOSED.md — CRYPTO asset class

**Target:** CRYPTO (largest asset class) of the ML/pick-trading system.
**Status:** Proposed fixes (not yet applied).
**Date:** 2026-11-14

## 1. Crypto-specific findings

**Stale active picks (highest severity)**
- `live_picks.db` crypto: 101 active crypto picks, largest asset class.
- All 101 are stale ~172 days (last activity 2026-05-25). No `current_price`, `last_checked`, or exit events refreshed since then.
- PnL errors concentrated here: 8 sign contradictions + 15 calc mismatches across crypto rows.

**PnL sign / calc bugs (representative examples)**
- NEARUSDT: entry 2.42, current 2.733 → `unrealized_pnl_pct=-0.129` (wrong sign) vs `pnl_pct=+0.128` (correct). Expected `(2.733-2.42)/2.42 = +0.129`.
- ZECUSDT: entry 674.39, current 665.24 → `unrealized=+0.013` (wrong sign). Expected `(665.24-674.39)/674.39 = -0.0136`.
- Additional affected symbols per audit: ATOMUSDT, INJUSDT, WUSDT, HBARUSDT etc.

**Closed-pick coverage (strong — not broken)**
- CRYPTO closed: 6,400 rows + 1,348 `crypto` (case-duplicated class label) rows.
- 16,176 closed rows carry a `pnl` field. Closed coverage is adequate; the defect is active-pick PnL staleness and sign/calc corruption, not closed data.

**Model surface**
- `ml_gatekeeper/gatekeeper.py:73`: `ASSET_CLASS_MAP = {"CRYPTO": 0, ...}` (CRYPTO = 0). Trained on 3,500+ real closed picks.
- Crypto strategy files: `alpha_engine/crypto_edge_strategies.py`, `alpha_engine/crypto_strategies.py`, `alpha_engine/crypto_strategy_harness.py` (and related `crypto_*` strategy modules).
- Databases: `crypto_data.db`, `coinglass_strategies/data/coinglass.db`.

## 2. Quick wins for crypto (do first — highest impact)

Fix these before any model/strategy retraining:

1. Recompute `unrealized_pnl_pct` for all 101 stale crypto active picks using `(current_price - entry_price) / entry_price`.
2. Fix the 8 sign contradictions (e.g. NEARUSDT, ZECUSDT) so sign matches direction of price move vs entry.
3. Fix the 15 calc mismatches so `unrealized_pnl_pct` == `pnl_pct` where both exist and are comparable.
4. Refresh `current_price` and `last_checked` for all crypto active rows.
5. Emit exit events / close stale picks that have no price update in ~172 days (or mark them `STALE` / `EXPIRED`).
6. Dedupe case-duplicated symbols (`CRYPTO` vs `crypto` class labels) so closed-pick aggregates are not double counted.

## 3. Proposed fixes for crypto

### 3.1 Recompute unrealized PnL (all crypto active rows)
```python
# Recompute for every crypto active row (asset_class lives in metadata JSON,
# not a top-level column — classify via asset_class_from_symbol() first).
expected = (current_price - entry_price) / entry_price
UPDATE live_picks
SET unrealized_pnl_pct = ?,
    pnl_pct = ?,
    last_checked = ?
WHERE id = ?
```
Apply to every crypto active row, not just the 23 flagged examples. Guard against `entry_price = 0` (skip/NULL).

### 3.2 Refresh prices and last_checked
- Re-fetch `current_price` from market data source for all 101 crypto active picks.
- Set `last_checked` to fetch timestamp. Rows still failing after refresh → flag `DATA_MISSING` for manual review.

### 3.3 Emit exit events for stale picks
- Picks with no price update ≥ ~172 days (2026-05-25) and no exit event → emit `EXIT_STALE` / close at last known price, or mark `EXPIRED`.
- Prevents zombie rows (`pnl=0.0`, `current_price=None`) from polluting the active panel.

### 3.4 Dedupe case-duplicated symbols
- Normalize `asset_class` / symbol casing at ingest: `CRYPTO` and `crypto` → single canonical class.
- Re-aggregate closed-pick counts (6,400 + 1,348) so class-level metrics (win rate, PF, median age) are not inflated by duplication.

### 3.5 Populate audit_trail.feature_edge_snapshots
- For each crypto pick evaluated by the ML gatekeeper, write a `feature_edge_snapshot` row (features used, model version, edge score, asset_class=CRYPTO) so PnL discrepancies can be traced back to the signal that produced the pick.

## 4. Verification steps

1. **Recompute expected PnL per row** and compare to stored `unrealized_pnl_pct`:
   - Expected = `(current_price - entry_price) / entry_price`
   - Assert `|stored - expected| < 1e-6` for all crypto active rows.
2. **Confirm sign consistency**:
   - `sign(unrealized_pnl_pct) == sign(current_price - entry_price)` for every crypto row. NEARUSDT must flip from `-0.129` → `+0.129`; ZECUSDT from `+0.013` → `-0.014`.
3. **Confirm no stale rows remain**:
   - Count crypto `ACTIVE` rows with `last_updated` (top-level) / `last_checked` (metadata) older than 30 days → must be 0 after fix (or all flagged `DATA_MISSING`/`EXPIRED`).
4. **Confirm dedupe**:
   - Query closed picks by canonical asset_class; `CRYPTO` count must equal the merged total, no separate `crypto` class rows.
5. **Re-run gatekeeper smoke test**:
   - `python3 -c "from ml_gatekeeper.gatekeeper import ASSET_CLASS_MAP; print(ASSET_CLASS_MAP['CRYPTO'])"` → `0`; ensure CRYPTO picks still route through the trained model (3,500+ closed picks) unchanged.

## 5. Repo paths touched

| Path | Reason |
|------|--------|
| `ml_gatekeeper/gatekeeper.py` | `ASSET_CLASS_MAP` CRYPTO=0 routing; verify unchanged |
| `alpha_engine/crypto_edge_strategies.py` | Crypto strategy surface consuming fixed picks |
| `alpha_engine/crypto_strategies.py` | Crypto strategy surface |
| `alpha_engine/crypto_strategy_harness.py` | Crypto strategy surface |
| `alpha_engine/mysql_trading_sync.py` | References ASSET_CLASS_MAP_MEME_TO_CRYPTO gating |
| `audit_trail/dashboard_generator.py` | Meme→CRYPTO class mapping (`_MEME_TO_CRYPTO`) |
| `audit_trail/trade_geometry.py` | `_ASSET_CLASS_MAP` / `AssetClass` enum |
| `live_picks.db` | 101 stale crypto active rows to recompute |
| `crypto_data.db` | Crypto market data source for price refresh |
| `coinglass_strategies/data/coinglass.db` | Crypto derivatives data source |

**Data files (`*.db`) are not committed to the repo** — apply fixes against the live/local DB copies, then document results in `updates/`.
