# ETFs Quick Wins — MERGED

**Scope:** ETFs (TLT, SPY, QQQ, XLF, GLD, XLK, XLY, XLE, XLV, XLP, SOXX, KWEB, EFA, XLC)
**Merged sources:** My flaxen-hair audit + peer `finpredict-v4` audit + peer `childlike-airport` proposed fixes
**Date:** 2026-11-14

## Consolidated findings

| # | Finding | Severity | Effort | Files | Source |
|---|---|---|---|---|---|
| ET-1 | Normalize ETF closed-pick `pnl_pct` to single unit (ratio) + single field | HIGH | Medium | `multi_asset_closed.json`, `institutional_closed.json`, `quick_wins/shared/normalize_pnl_units.py` | My audit |
| ET-2 | Dedupe duplicate ETF picks (XLE ×2, XLY ×2) — keep highest confidence | MED | LOW | `institutional_picks.json` | My audit |
| ET-3 | Make ETF pick IDs globally unique (timestamp + sequence, never date-only) | MED | LOW | `institutional_picks_engine.py:1455`, `equity_strategies.py`, `quick_wins/shared/validate_pick_ids.py` | My audit |
| ET-4 | Resolve stale ETF OPEN picks from 2026-04-03 (close/purge with reason) | HIGH | LOW | `institutional_picks.json`, `multi_asset_picks.json` | My audit |
| ET-5 | Decouple `ml_score` from `confidence` (set null, never copy) — ML code sound; inversion is data bug | MED | Medium | `institutional_picks_engine.py`, `equity_strategies.py`, `multi_asset_picks.json` | My audit + peer childlike |
| ET-6 | Add KWEB, VLUE to `ETF_SYMBOLS` frozenset (currently missing → mislabeled as EQUITY) | P0/High | Small | `alpha_engine/asset_class.py:37–53` | Peer childlike etfs |
| ET-7 | Sync `active_picks_etf.json` (16 fresh picks, 2026-11-12T18:17:06Z) into `live_picks.db` (store class in `metadata` since no `asset_class` column) | P0/High | Small | `alpha_engine/etf_scanner.py`, `alpha_engine/data/active_picks_etf.json`, `data/live_picks.db` | Peer childlike etfs |
| ET-8 | 48h freshness guard for ETF picks | P1/Med | Small | `alpha_engine/etf_scanner.py` | Peer childlike etfs |
| ET-9 | Surface ETF tile in per-class dashboard; populate `strategy_stats` for `etf_*` strategies | P1/Med | Small | `audit_trail/dashboard_generator.py`, `alpha_engine/` | Peer childlike etfs |

## Key observations
- `multi_asset_closed.json` TLT: `pnl_pct: 0.0` though entry 88.28 ≠ exit 88.3956 (recompute ≈ +0.00131 ratio).
- `multi_asset_closed.json` XLF: `unrealized_pnl_pct: -0.01178` (ratio) vs `realized_pnl_pct: -1.1786` (percent) — 100× apart, both labeled `_pct`.
- `institutional_closed.json` ETF closes use PERCENT units (e.g. SPY `-2.9191` = -2.9191%); `multi_asset_closed.json` mixes units — inconsistent across files.
- `institutional_picks_engine.py:1455` ID gen is date-only (`{strat}::{sym}::{today}`) → non-unique on re-run.
- `equity_strategies.py:594` sector_rotation pick sets `confidence` only, no `ml_score`, no `id`.
- `active_picks_etf.json`: 16 fresh picks (2026-11-12T18:17:06Z); `etf_dual_momentum`, `etf_sector_momentum`, `etf_faber_tactical`, `etf_rsi2_pullback`, `etf_sector_dual_momentum`, `etf_cross_sectional_momentum`; SOXX, KWEB, XLV, XLF, XLE, SPY, QQQ, EFA, XLC (peer childlike).
- `live_picks` table has **no `asset_class` column** — class derived at query time (peer childlike).
- `ETF_SYMBOLS` missing KWEB and VLUE → mislabeled as EQUITY (peer childlike).
- 12 ETF strategy modules present (peer childlike).
- Honest intrabar: n=45, WR 2.3%, PF 0.022, avg -2.3321% — worst intrabar-verified class (peer audits).
- All top picks have `db_n=0`, `intrabar_fwd_n=null`, `intrabar_gate=NO_DATA` (peer audits).
- BITO/IBIT are Bitcoin ETFs (crypto proxies) (peer audits).
- Money-ready: INSUFFICIENT_DATA (PF 0.02, WR 2.22%) (peer audits).

## Verification (ETFs)
1. **PnL unit consistency:** every closed ETF record has exactly one `pnl_pct` as ratio (`-1 <= x <= 1`), and `pnl_pct ≈ (exit_price - entry_price) / entry_price` (direction-adjusted). No coexistence of `realized_pnl_pct` + `unrealized_pnl_pct`; no value magnitude > 1.
2. **Duplicate ETF picks:** group open ETF picks by `(symbol, entry_date, direction)` → count == 1 per group (XLE once, XLY once).
3. **Unique IDs:** collect all `id` values across `multi_asset_picks.json` + `institutional_picks.json` → no duplicates; IDs contain a time component (not date-only).
4. **Stale picks:** no OPEN ETF pick with `entry_date` older than 30 days without `exit_price`/`closed_at`.
5. **ml_score decouple:** no pick has `ml_score == confidence` unless both from an actual model; prefer `ml_score: null` where no model exists.
6. **ETF_SYMBOLS:** KWEB and VLUE present in `alpha_engine/asset_class.py:37–53`.
7. **ETF sync:** `active_picks_etf.json` rows present in `live_picks.db` with class in `metadata`.

## Code snippets

**PnL normalization (canonical converter — apply to both closed JSON files):**
```python
def normalize_pnl(pick):
    pnl = None
    for key in ("realized_pnl_pct", "unrealized_pnl_pct", "pnl_pct"):
        if pick.get(key) is not None:
            pnl = float(pick[key]); break
    if pnl is None: return pick
    if abs(pnl) > 1.0:  # percent leaked in
        pnl = pnl / 100.0
    pnl = max(-1.0, min(1.0, pnl))
    out = dict(pick); out["pnl_pct"] = round(pnl, 6)
    out.pop("realized_pnl_pct", None); out.pop("unrealized_pnl_pct", None)
    return out
```

**Dedupe duplicate ETF picks (`institutional_picks.json`):**
```python
from collections import defaultdict
best = {}
for p in picks:
    if p.get("asset_class") != "ETF" or p.get("status") != "OPEN": continue
    key = (p["symbol"], p.get("entry_date", p["timestamp"][:10]), p["direction"])
    if key not in best or p.get("confidence", 0) > best[key].get("confidence", 0):
        best[key] = p
keep_ids = {id(v) for v in best.values()}
picks = [p for p in picks if not (p.get("asset_class")=="ETF" and p.get("status")=="OPEN" and id(p) not in keep_ids)] or list(best.values())
```
Result: XLE kept once (sector_rotation_enhanced, conf 0.85), XLY kept once (sector_rotation, conf 0.638).

**Unique pick IDs (`institutional_picks_engine.py` ~line 1455):**
```python
import uuid, datetime
"id": f"{strat_name}::{sym}::{today}_{datetime.now(timezone.utc).strftime('%H%M%S')}:{uuid.uuid4().hex[:6]}",
```

**Resolve stale 2026-04-03 ETF opens:**
```python
from datetime import datetime, timezone
STALE_DAYS = 30; now = datetime.now(timezone.utc)
for p in picks:
    if p.get("status") == "OPEN" and p.get("asset_class") == "ETF":
        entry = datetime.fromisoformat(p["entry_date"])
        if (now - entry).days > STALE_DAYS:
            p["status"] = "CLOSED"; p["exit_price"] = p.get("current_price", p["entry_price"])
            p["closed_at"] = now.isoformat(); p["close_reason"] = "stale_open_purge"
            p["pnl_pct"] = (p["exit_price"] / p["entry_price"] - 1.0) * (1 if p["direction"]=="LONG" else -1)
```

**Decouple `ml_score` from `confidence`:**
```python
"confidence": result["confidence"],
"ml_score": None,  # real model must populate this; null = not scored (never copy confidence)
```

Note: `test_etf_verify.py` is a live-dashboard Playwright smoke test — confirms ETF category renders but does NOT validate pnl units/dedupe/ID uniqueness; verify against JSON files directly.

Per AGENTS.md: document each implemented fix in `updates/<date>-<description>.md` and commit fix + doc on a clean branch containing only your changes.
