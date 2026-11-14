# FIX_PROPOSED.md — BONDS Asset Class

Target repo: `/home/eaguiar2015/findtorontoevents_antigravity.ca`
Worktree: `childlike-airport`

## 1. Bonds-specific findings

### Fresh bond_scanner feed vs stale live_picks.db sync gap

| Source | Asset class | Count | Age / staleness | Notes |
|--------|-------------|-------|-----------------|-------|
| `active_picks_bond.json` | BOND | 7 | FRESH — 2026-11-12 (~2d old) | bond_scanner output; SHY appears 3x across strategies |
| `live_picks.db` | BOND | 2 active | STALE — ~172 days old | DB not synced with active_picks_bond.json |
| Bond feed (SHY, LQD, MUB, TLT) | BOND | 4 symbols | FRESH (2d) | In bond_scanner output only; not persisted to DB |

SHY (×3 strategies: `bond_yield_momentum`, `bond_duration_rotation`, `bond_tlt_ief_v3`), LQD, MUB, TLT are present in the fresh bond feed with `entry_price`, `take_profit`, `stop_loss`, `confidence`, `risk_reward`, `allocation=2000`, `category=bond`, `asset_class=BOND`. Only 2 of these rows persist in `live_picks.db` and they are ~172 days stale — a sync gap is the core bug.

### Closed picks thinness

- Closed bond picks: only 3 rows across all time. No exit events (TP/SL/time) are emitted for bond strategies, so PnL and performance attribution are impossible to verify.

### Bond strategies present in `alpha_engine`

- `bond_duration_rotation.py`
- `bond_yield_curve_slope.py`
- `bond_yield_momentum.py`
- `bond_tlt_trend_vol_scaled.py`
- `bond_credit_spread.py`
- `bond_tips_breakeven.py`
- `yield_curve_nss.py`

### BOND_SYMBOLS coverage (`alpha_engine/asset_class.py`)

`BOND_SYMBOLS` frozenset: TLT, IEF, SHY, LQD, AGG, BND, HYG, JNK, SJNK, BKLN, EMB, TIP, MUB, IGIB — covers the fresh feed symbols.

## 2. Quick wins for bonds

- [ ] Sync `alpha_engine/data/active_picks_bond.json` (6 picks, fresh 2026-11-12 ~2d old) into `live_picks.db` so the live panel reflects the fresh bond feed instead of 172d stale rows.
- [ ] Refresh `current_price` and recompute PnL for the 2 stale bond picks currently in `live_picks.db` (fetch latest quote via `audit_trail/fetch_stock_prices.py` or market data provider).
- [ ] Emit exit events (TP hit / SL hit / time exit) for bond picks so closed-pick count grows from 3 and audit attribution works.
- [ ] Populate `audit_trail.symbol_strategy_stats` for bond strategies (`bond_duration_rotation`, `bond_yield_momentum`, `bond_tlt_ief_v3`, `bond_yield_curve_slope`, `bond_credit_spread`, `bond_tips_breakeven`, `yield_curve_nss`).

## 3. Proposed fixes for bonds

### Fix 3.1 — Sync `active_picks_bond.json` into `live_picks.db`

**Bug:** `active_picks_bond.json` is fresh (2d, 7 picks) but `live_picks.db` holds only 2 stale (~172d) bond rows. The bond feed never lands in the live-picks DB.

**Files to touch:**
- `alpha_engine/audit_sync.py` — portfolio data MySQL sync (likely writes live_picks rows)
- `alpha_engine/production_scanner.py` — production scan orchestrator (writes active picks)
- `live_picks.db` — SQLite live picks DB (target of sync)
- `active_picks_bond.json` — source of truth for fresh bond picks

**Proposed change:**
Add a bond-specific sync step (or extend the existing sync loop) that reads `active_picks_bond.json` and upserts each pick into `live_picks.db`:
- Columns: symbol, entry_price, take_profit, stop_loss, confidence, risk_reward, allocation, category=`bond`, asset_class=`BOND`, strategy, updated_at = feed timestamp (2026-11-12).
- Dedupe by (symbol, strategy) since SHY appears ×3 across strategies.
- Upsert on conflict: update price fields, keep `opened_at` unchanged, set `updated_at` to feed time.

**Verification:** Since `asset_class` lives in `metadata` JSON (not a top-level column), query via Python `asset_class_from_symbol()` or `metadata LIKE '%"asset_class":"BOND"%'`. Expect 6 bond rows (SHY ×3 strategies, LQD, MUB, TLT), and `MAX(updated_at)` ~2026-11-12.

### Fix 3.2 — Refresh current_price/PnL for stale bond picks

**Bug:** 2 bond picks in `live_picks.db` are ~172d stale with `pnl=0.0`, `current_price=None` (unresolved zombies).

**Files to touch:**
- `audit_trail/fetch_stock_prices.py` — server-side stock price fetcher
- `live_picks.db` — target rows
- `alpha_engine/forward_validator.py` — forward validation of picks (reuses price fetcher)

**Proposed change:**
Run a one-off refresh job (and add to the hourly `db-freshness-guardian` loop if not present):
- Query `live_picks` for bond rows where `updated_at < now - 7d` (or `current_price IS NULL`).
- Fetch latest close for each symbol via `fetch_stock_prices.py`.
- Update `current_price`, compute `pnl = (current_price - entry_price) / entry_price`, set `updated_at = now`.
- If `current_price >= take_profit` → emit TP exit event; if `<= stop_loss` → emit SL exit event; if past max hold → emit time exit.

**Verification:** 0 bond rows with `current_price IS NULL`; `pnl` non-zero for refreshed rows.

### Fix 3.3 — Emit exit events for bond picks

**Bug:** No TP/SL/time exit events emitted for bond strategies; closed bond picks = 3 (thin). Audit trail cannot attribute bond PnL.

**Files to touch:**
- `audit_trail/universal_pick_resolver.py` — active pick TP/SL/time exit resolver
- `audit_trail/dashboard_generator.py` — main dashboard payload + HTML generator
- `live_picks.db` / closed-picks table

**Proposed change:**
Extend `universal_pick_resolver.py` to resolve bond picks:
- For each active bond pick, compare `current_price` vs `take_profit` / `stop_loss`.
- On hit: insert closed-pick row with exit_reason ∈ {`tp`, `sl`, `time`}, exit_price, exit_pnl, exit_at.
- Move row from active to closed; keep audit trail entry with symbol, strategy, asset_class=`BOND`.

**Verification:** Closed bond picks count > 3; exit_reason distribution non-empty for BOND asset class.

### Fix 3.4 — Populate `audit_trail.symbol_strategy_stats` for bond strategies

**Bug:** `symbol_strategy_stats` lacks bond strategy rows, so per-symbol/strategy performance attribution for BOND is missing.

**Files to touch:**
- `audit_trail/dashboard_generator.py` — generates stats aggregation
- `alpha_engine/config.py` — strategy families / scoring config (confirm bond families registered)
- `audit_trail/symbol_strategy_stats` table (DB schema)

**Proposed change:**
After sync + exit resolution, aggregate per (symbol, strategy) for asset_class=`BOND`:
- picks_count, wins, losses, avg_pnl, win_rate, avg_rr, last_pick_at.
- Insert/upsert into `symbol_strategy_stats` with asset_class filter = `BOND`.

**Verification:** `SELECT COUNT(*) FROM symbol_strategy_stats` filtered by `asset_class='BOND'` in metadata (query via `asset_class_from_symbol()` or `metadata LIKE '%"asset_class":"BOND"%'`) returns ≥ 7 rows (one per active bond pick) and rows exist for all 7 bond strategies listed above.

## 4. Verification steps

1. Python check via `alpha_engine.asset_class.asset_class_from_symbol` on bond symbols (SHY, LQD, MUB, TLT) → all return `'bond'`; count of `live_picks` rows with bond-classified metadata → expect 6 active rows.
2. `sqlite3 live_picks.db "SELECT MAX(updated_at) FROM live_picks"` → expect ~2026-11-12 (2d old), not 172d.
3. `sqlite3 live_picks.db "SELECT COUNT(*) FROM live_picks WHERE current_price IS NULL"` → expect 0 for bond-classified rows after refresh.
4. Closed bond picks count > 3 after exit emission (query via `asset_class` in metadata).
5. `sqlite3 audit_trail.db "SELECT COUNT(*) FROM symbol_strategy_stats"` where asset_class filter = `'BOND'` → expect ≥ 7 rows covering all bond strategies.
6. Run `tools/db_freshness_check.py` — bond rows should no longer flag as stale.
7. Run `python3 -c "import py_compile; py_compile.compile('<edited_file>', doraise=True)"` on each edited Python file.

## 5. Repo paths touched

| Path | Role |
|------|------|
| `alpha_engine/audit_sync.py` | Portfolio/MySQL sync — add bond sync step |
| `alpha_engine/production_scanner.py` | Scan orchestrator — writes active bond picks |
| `alpha_engine/asset_class.py` | `BOND_SYMBOLS` frozenset (verify coverage — no change expected) |
| `alpha_engine/forward_validator.py` | Forward validation / price refresh reuse |
| `audit_trail/fetch_stock_prices.py` | Price fetcher for stale bond pick refresh || `tools/db_freshness_check.py` | DB freshness guardian — include bond staleness check |
| `audit_trail/universal_pick_resolver.py` | TP/SL/time exit resolver — add bond exit emission |
| `audit_trail/dashboard_generator.py` | Dashboard payload + `symbol_strategy_stats` aggregation |
| `live_picks.db` | Live picks DB — sync target (7 bond rows) |
| `alpha_engine/data/active_picks_bond.json` | Fresh bond feed source (2d old, 6 picks) |
| `updates/2026-11-14-ML-AUDIT-childlike-airport/proposed_fixes/bonds/FIX_PROPOSED.md` | This document |
