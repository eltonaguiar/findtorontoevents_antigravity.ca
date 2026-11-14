# Crypto Quick Wins — MERGED

**Scope:** Crypto (BTC, ETH, altcoins via coinglass_strategies, ml_crypto_predictor, quantum_fusion_crypto_engine)
**Merged sources:** My flaxen-hair audit + peer `finpredict-v4` audit + peer `childlike-airport` proposed fixes
**Date:** 2026-11-14

## Consolidated findings

| # | Finding | Severity | Effort | Files | Source |
|---|---|---|---|---|---|
| CR-1 | Resolve/expire stale coinglass positions (max opened 2026-11-06, ~8 days old, exceeds MAX_HOLD_HOURS=48) | HIGH | LOW | `coinglass_strategies/ratio_store.py`, `coinglass_strategies/scanner.py` | My audit |
| CR-2 | PnL unit normalization (ratio vs percent, up to 100× disagreement) | HIGH | LOW | `coinglass_strategies/ratio_store.py`, `coinglass_strategies/paper_portfolio.py`, `quick_wins/shared/normalize_pnl_units.py` | My audit |
| CR-3 | Fix non-unique pick IDs (second/minute precision collisions; `INSERT OR IGNORE` silently drops dupes) | MED | LOW | `coinglass_strategies/strategies/base.py`, `coinglass_strategies/crypto_enhancement_pack.py`, `ml_crypto_predictor/enhanced_models/live_picks_tracker.py`, `quick_wins/shared/validate_pick_ids.py` | My audit |
| CR-4 | Decouple `ml_score` from `confidence` — ML code sound; inversion is DATA bug (conf≥0.90 → 14.4% WR; conf 0.50–0.60 → 60.3% WR) | MED | LOW | `copy_trader_intel/gmx_scraper.py:555`, `copy_trader_intel/asset_class_analysis_forex.py:1061`, `score_audit.py:6`, `live_picks_tracker.py`, `live_predictor.py` | My audit + peer childlike + peer audits |
| CR-5 | Verify/backfill `pnl_dollar`/`pnl_pct` populated & consistent for closed positions | MED | LOW | `coinglass_strategies/data/coinglass.db` | My audit |
| CR-6 | Fix crypto price fetcher so PnL stops freezing at `entry_price` (Binance/CoinGecko/CCXT reachability, fallback source, `last_price_update`) | P0/Critical | Small | `audit_trail/fetch_stock_prices.py` (crypto path), `coinglass_strategies/data_fetcher.py` | Peer audits crypto QW-1 |
| CR-7 | Kill 5× PF inflation (dashboard PF 1.80 vs raw DB PF 0.37) via `source_tag` filter + `COUNT(DISTINCT pick_id)` | P0/Critical | Small | `alpha_engine/smart_picks_engine.py`, `audit_trail/dashboard_generator.py` | Peer audits crypto QW-2 |
| CR-8 | Purge 8-month zombie AI Challenge picks (`created_at < '2026-09-01'`, `track_level='none'`) | P0/Critical | Small | `multi_asset/data/multi_asset_closed.json`, `live_picks.db` | Peer audits crypto QW-3 |
| CR-9 | Invert ML confidence calibration (`effective_conf = 1.0 - raw_conf` + `CRYPTO_CONF_FLIP`) | P2/Medium | Small | `ml_gatekeeper/gatekeeper.py`, `ml_gatekeeper/crypto_calibration.json` (new) | Peer audits crypto LF-2 |
| CR-10 | Smart Picks min sample gate n>=20 (PF 9.69 driven by `claude_gainer_st` on n=3 rows) | P2/Medium | Small | `alpha_engine/smart_picks_engine.py`, `tools/ml_metrics_ci_summary.py` | Peer audits crypto MF-3 |

## Key observations
- `coinglass.db` `positions` table: 13 OPEN positions, max `opened_at` 2026-11-06 (~8 days stale), far exceeding `MAX_HOLD_HOURS = 48` (`config.py:69`). `monitor_positions()` closes via TIMEOUT but only invoked from `cmd_portfolio()` (`scanner.py:38`), not every scan.
- `fetch_current_price()` (`data_fetcher.py:462`) returns `None` when Binance geo-blocked (HTTP 451) → TP/SL/TIMEOUT checks skipped → positions never resolve.
- `ratio_store.py:close_position()` stores `pnl_pct` in **percent** (`* 100`); other systems (ml_crypto_predictor, alpha_engine) may store **ratio** (0.05 = 5%) → win-rate/profit-factor off by up to 100×.
- `positions.signal_id TEXT UNIQUE` + `INSERT OR IGNORE` silently drops duplicates.
- `signal_id` second/minute precision → collisions if same strategy+symbol fires within same second/minute.
- `crypto_enhancement_pack.py:_make_pick()` has **no `signal_id` field**.
- `ml_score` set equal to `confidence` in `gmx_scraper.py:555`, `asset_class_analysis_forex.py:1061`; `score_audit.py:6` falls back `ml_score` to `confidence`.
- `quantum_fusion_crypto_engine.py` is mock/simulated (random performance metrics, no live data, no DB writes) — not a quick-win target; flag for documentation only.
- Live cross-check (peer audits): NEARUSDT SHORT claimed +2.74% but live +3.46%; XRPUSDT SHORT claimed 0.0% but live +1.46%; BTCUSDT SHORT claimed 0.0% but live +0.97%.
- 101 active crypto picks, all ~172 days stale (last activity 2026-05-25), no `current_price`/`last_checked`/exit events (peer childlike).
- Closed coverage strong (6,400 CRYPTO + 1,348 `crypto` case-dup; 16,176 closed rows carry `pnl`) (peer childlike).
- Raw DB: n=46,324 total / 2,001 decisive, WR 39.4%, PF 0.371 (peer audits).
- Dashboard recent-closed CRYPTO: PF 1.80 vs raw DB PF 0.37 (**5x inflation**) (peer audits).
- Smart Picks CRYPTO: PF 9.69, WR 78.9% — **91.7% from single source `claude_gainer_st`** with only **3 closed rows** in raw DB (peer audits).
- All 3 active crypto picks: `forward_trades=0`, `forward_validated=false`, `forward_status="NO_DATA"`, `_backfilled: true` (reconstructed, not live-emitted), `_emitter_registry_would_block: true` (peer audits).
- Crowded consensus: BTC pick has 13 contributing systems; "crowded_consensus_unproven" correlates with lower edge (peer audits).
- Money-ready: NOT_READY (PF 0.92, WR 35.87%, MDD ~100%, expectancy -0.059, bootstrap CI excludes zero) (peer audits).

## Verification (crypto)
**SQL (read-only, safe against `coinglass_strategies/data/coinglass.db`):**
```sql
-- Open positions + max age
SELECT COUNT(*) AS open_count, MAX(opened_at) AS oldest_opened FROM positions WHERE status='OPEN';
-- All open positions detail
SELECT signal_id, symbol, direction, opened_at, status, pnl_pct, pnl_dollar FROM positions WHERE status='OPEN' ORDER BY opened_at DESC;
-- Duplicate signal_ids in positions
SELECT signal_id, COUNT(*) AS cnt FROM positions GROUP BY signal_id HAVING cnt > 1;
-- Duplicate signal_ids in signals
SELECT signal_id, COUNT(*) AS cnt FROM signals GROUP BY signal_id HAVING cnt > 1;
-- Closed positions missing pnl
SELECT COUNT(*) AS missing_pnl FROM positions WHERE status='CLOSED' AND (pnl_pct IS NULL OR pnl_dollar IS NULL);
-- Open positions that incorrectly have pnl populated
SELECT COUNT(*) AS open_with_pnl FROM positions WHERE status='OPEN' AND (pnl_pct IS NOT NULL OR pnl_dollar IS NOT NULL);
-- Consistency: pnl_dollar vs quantity * pnl_pct / 100 (tolerance $0.01)
SELECT signal_id, symbol, pnl_pct, pnl_dollar, quantity,
       ABS(pnl_dollar - (quantity * pnl_pct / 100.0)) AS diff
FROM positions WHERE status='CLOSED' AND pnl_pct IS NOT NULL AND pnl_dollar IS NOT NULL
HAVING diff > 0.01;
-- Ratio-suspect pnl_pct values (|v| <= 1.0 likely stored as ratio not percent)
SELECT COUNT(*) AS ratio_suspects FROM positions WHERE status='CLOSED' AND pnl_pct IS NOT NULL AND abs(pnl_pct) <= 1.0;
```

**Python (decoupling check):**
```python
bad = [p for p in picks
       if p.get('ml_score') is not None and p.get('confidence') is not None
       and abs(float(p['ml_score']) - float(p['confidence'])) < 1e-9]
print(f"Coupled ml_score==confidence: {len(bad)} picks")  # should be 0
```

## Code snippets

**QW-1 `expire_stale_positions()` (add to `ratio_store.py`):**
```python
from datetime import datetime, timezone, timedelta
def expire_stale_positions(max_hold_hours=None):
    if max_hold_hours is None:
        from coinglass_strategies import config
        max_hold_hours = config.MAX_HOLD_HOURS
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=max_hold_hours)).isoformat()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT signal_id FROM positions WHERE status='OPEN' AND opened_at < ?", (cutoff,)
        ).fetchall()
        for r in rows:
            conn.execute("""
                UPDATE positions SET status='CLOSED', closed_at=?,
                exit_price=entry_price, exit_reason='STALE_TIMEOUT',
                pnl_pct=0, pnl_dollar=0 WHERE signal_id=?
            """, (datetime.now(timezone.utc).isoformat(), r["signal_id"]))
        return len(rows)
```
Call from `scanner.py` `main()`/`cmd_scan()` every run, not just `--portfolio`.

**QW-2 `normalize_pnl_pct()` (add to `ratio_store.py`):**
```python
def normalize_pnl_pct(value):
    if value is None: return None
    v = float(value)
    if abs(v) <= 1.0:  # looks like ratio, not percent
        return round(v * 100, 4)
    return round(v, 4)
```
Wrap every `p.get("pnl_pct")` read with `normalize_pnl_pct(...)`; enforce percent-only writes in `close_position()`.

**QW-3 Unique signal_id (`strategies/base.py`):**
```python
import uuid
def __post_init__(self):
    if not self.generated_at:
        self.generated_at = datetime.now(timezone.utc).isoformat()
    if not self.signal_id:
        self.signal_id = f"{self.strategy}::{self.symbol}::{self.generated_at[:19]}:{uuid.uuid4().hex[:8]}"
```
Add `signal_id` to `_make_pick()` in `crypto_enhancement_pack.py` and to prediction dicts in `live_picks_tracker.py`/`live_predictor.py`. Log warning when `INSERT OR IGNORE` skips a duplicate (currently silent).

**QW-4 Decouple ml_score from confidence (`live_picks_tracker.py`):**
```python
prediction = {
    ...
    "confidence": confidence,              # calibrated label: HIGH/MEDIUM/LOW
    "probability": round(directional_confidence, 4),  # calibrated probability 0-1
    "ml_score": round(best_prob, 4),       # raw model output, independent of confidence
    ...
}
# NEVER: "ml_score": confidence
```

**QW-5 Backfill pnl for closed positions:**
```sql
UPDATE positions SET pnl_pct = ROUND((exit_price - entry_price) / entry_price * 100, 4),
                     pnl_dollar = ROUND(quantity * ((exit_price - entry_price) / entry_price * 100) / 100, 2)
WHERE status='CLOSED' AND (pnl_pct IS NULL OR pnl_dollar IS NULL) AND exit_price IS NOT NULL;
```

**QW-6 PF inflation fix (`smart_picks_engine.py`):**
```python
# Filter by source_tag and dedupe pick_id before PF computation
df = df[df["source_tag"].isin(ALLOWED_SOURCE_TAGS)]
pf = df.groupby("pick_id")["pnl"].sum()  # COUNT(DISTINCT pick_id) guard
```

## Recommended execution order
1. **CR-6** (fix crypto price fetcher) — stops PnL freezing at entry_price
2. **CR-7** (PF inflation fix) — dashboard PF 1.80 vs raw 0.37
3. **CR-8** (purge zombie AI Challenge picks) — 8-month-old picks still OPEN
4. **CR-1** (expire stale positions) — stops carrying 8-day-old zombie exposure
5. **CR-5** (verify/backfill pnl columns)
6. **CR-2** (normalize pnl units)
7. **CR-3** (unique pick IDs)
8. **CR-4** (decouple ml_score from confidence)
9. **CR-9** (invert ML confidence calibration)
10. **CR-10** (Smart Picks min sample gate)

Per AGENTS.md: document each implemented fix in `updates/<date>-<description>.md` and commit fix + doc on a clean branch containing only your changes.
