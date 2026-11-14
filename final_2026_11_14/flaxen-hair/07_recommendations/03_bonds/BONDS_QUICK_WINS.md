# Bonds / Treasury / Fixed Income Quick Wins — MERGED

**Scope:** Bonds / treasury / fixed income (ZN=F 10Y T-Note futures; TLT/IEF bond ETFs; SHY/LQD/AGG/BND/HYG/TIP/MUB)
**Merged sources:** My flaxen-hair audit + peer `finpredict-v4` audit + peer `childlike-airport` proposed fixes
**Date:** 2026-11-14

## Consolidated findings

| # | Finding | Severity | Effort | Files | Source |
|---|---|---|---|---|---|
| BO-1 | PnL unit normalization for ZN=F closed picks (ratio vs percent, up to 100× disagreement) | HIGH | LOW | `multi_asset_closed.json`, `quick_wins/shared/normalize_pnl_units.py` | My audit |
| BO-2 | Fix non-unique pick IDs — `vix_reversal::ZN=F::2026-03-11` appears 4× | HIGH | LOW | `multi_asset/scanner.py` (`_pick_id`), `multi_asset_closed.json`, `quick_wins/shared/validate_pick_ids.py` | My audit |
| BO-3 | Close/stale ZN=F open pick — `futures_mean_reversion::ZN=F::2026-04-03` still OPEN (7+ months) | MED | LOW | `institutional_picks.json` | My audit |
| BO-4 | Add BOND category mapping consistently (`category: "bond"` → `asset_class: "BOND"`) | MED | LOW | `commodity_futures_strategies.py` | My audit |
| BO-5 | Verify `bond_asset_class` migration applied on live MySQL (`ejaguiar1_stocks`) | MED | LOW | `tools/migrations/20260530_add_bond_asset_class.sql` | My audit |
| BO-6 | Add bond mutual fund / bond ETF data feed (currently only ZN=F futures + TLT/IEF ETFs) | MED | MEDIUM | `scanner.py` symbol universe, `commodity_futures_strategies.py` | My audit |
| BO-7 | Sync `active_picks_bond.json` (7 fresh picks, 2026-11-12) into `live_picks.db`; dedupe SHY ×3 across bond strategies | P0/High | Small | `alpha_engine/audit_sync.py`, `active_picks_bond.json`, `live_picks.db` | Peer childlike bonds §3.1 |
| BO-8 | Refresh price/PnL for 2 stale (~172d) bond rows in `live_picks.db` via `alpha_engine/fetch_stock_prices.py` | P0/High | Small | `live_picks.db`, `alpha_engine/fetch_stock_prices.py` | Peer childlike bonds |
| BO-9 | Emit TP/SL/time exit events via `audit_trail/universal_pick_resolver.py`; populate `symbol_strategy_stats` for all 7 bond strategies | P1/High | Small | `audit_trail/universal_pick_resolver.py`, `audit_trail/dashboard_generator.py` | Peer childlike bonds |

## Bond asset-class state
- ZN=F is the only bond future, categorized as `FUTURES` not `BOND` in `multi_asset_closed.json` / `institutional_picks.json`.
- TLT and IEF are the only picks with true `asset_class: "BOND"` / `category: "bond"` (2 OPEN picks, dated 2026-11-12).
- `active_picks_bond.json`: 7 fresh picks (2026-11-12, ~2 days); SHY ×3 across `bond_yield_momentum`/`bond_duration_rotation`/`bond_tlt_ief_v3`, LQD, MUB, TLT (peer childlike).
- `live_picks.db`: only 2 stale (~172d) bond rows (peer childlike).
- Only 3 closed bond picks ever; no exit events (peer childlike).
- `BOND_SYMBOLS` frozenset at `alpha_engine/asset_class.py:22–62`: TLT, IEF, SHY, LQD, AGG, BND, HYG, JNK, SJNK, BKLN, EMB, TIP, MUB, IGIB.
- 7 bond strategies in `alpha_engine/`.
- Honest intrabar: n=26, WR 7.7%, PF 0.391, avg -0.3342% (peer audits).
- Policy_clean n=1 (TLT only), WR 0%, PF 0.0 (peer audits).
- Money-ready: INSUFFICIENT_DATA (PF 0.0, WR 0.0), policy frozen, recency failed (last close 2026-11-10, 4.0 days) (peer audits).

## Verification (bonds)
1. **PnL unit check:** all `pnl_pct`/`realized_pnl_pct` values in consistent units; the 4 ZN=F `vix_reversal` rows currently show both `-0.3754` (percent) and `-0.0037536` (ratio) for the same logical pick.
2. **ID uniqueness:** `vix_reversal::ZN=F::2026-03-11` no longer repeats across the corpus.
3. **Staleness:** no OPEN pick with `entry_date` older than 30 days without `exit_price`/`closed_at` (ZN=F `futures_mean_reversion::ZN=F::2026-04-03` resolved).
4. **Migration:** `SHOW COLUMNS FROM at_raw_picks WHERE Field='asset_class'` → ENUM contains `BOND` across all 11 tables.
5. **Bond sync:** `active_picks_bond.json` → `live_picks.db` upsert by symbol+strategy, dedupe SHY ×3.

## Code snippets

**`_pick_id()` uniqueness (`scanner.py`):**
```python
_PICK_ID_COUNTER: dict[str, int] = {}

def _pick_id(strategy: str, symbol: str, dt: str) -> str:
    key = f"{strategy}::{symbol}::{dt}"
    _PICK_ID_COUNTER[key] = _PICK_ID_COUNTER.get(key, 0) + 1
    seq = _PICK_ID_COUNTER[key]
    return f"{key}#{seq:03d}" if seq > 1 else key
```

**Close stale ZN=F open pick (`institutional_picks.json`):**
```json
"status": "CLOSED",
"close_reason": "Stale open pick — exceeded max hold (22d > 10d), auto-closed",
"closed_at": "2026-04-25T00:00:00+00:00",
"realized_pnl_pct": 0.0
```

**Migration verification:**
```bash
mysql -h mysql.50webs.com -u ejaguiar1 -p ejaguiar1_stocks -e "SHOW COLUMNS FROM at_raw_picks WHERE Field='asset_class';"
# Confirm ENUM contains 'BOND'
```

**Bond sync upsert (`audit_sync.py`):**
```python
# Upsert active_picks_bond.json into live_picks.db, dedupe by (symbol, strategy)
columns = ["symbol", "entry_price", "take_profit", "stop_loss", "confidence", "risk_reward",
           "allocation", "category", "asset_class", "strategy", "updated_at"]
# category="bond", asset_class="BOND"; updated_at = feed timestamp
```

Per AGENTS.md: document each implemented fix in `updates/<date>-<description>.md` and commit fix + doc on a clean branch containing only your changes.
