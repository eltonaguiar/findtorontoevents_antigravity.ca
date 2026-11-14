# Equity / Stocks Quick Wins — MERGED

**Scope:** Stocks / equity (AAPL, MSFT, AMZN, META, JPM, V, NVDA, GOOGL, TSLA, HD, TMO)
**Merged sources:** My flaxen-hair audit + peer `finpredict-v4` audit + peer `childlike-airport` proposed fixes
**Date:** 2026-11-14

## Consolidated findings

| # | Finding | Severity | Effort | Files | Source |
|---|---|---|---|---|---|
| EQ-1 | Normalize equity `pnl_pct`/`realized_pnl_pct` to decimal ratio (mixed ratio/percent, up to 100× off) | HIGH | Small | `multi_asset_closed.json`, `institutional_closed.json`, `quick_wins/shared/normalize_pnl_units.py` | My audit |
| EQ-2 | Expire/stale the 2026-04-03 equity OPEN pick (META via `macd_divergence_tuned`, ~7 months old) | HIGH | Small | `institutional_picks.json` | My audit |
| EQ-3 | Fix non-unique equity pick IDs (`vix_reversal::AAPL::2026-03-11` ×5, `MSFT` ×4, etc.) | HIGH | Small | `multi_asset_closed.json`, `quick_wins/shared/validate_pick_ids.py` | My audit |
| EQ-4 | Decouple `ml_score` from `confidence` for equity picks (identical on every open pick) — ML code is SOUND; inversion is a DATA bug | MED | Small | `multi_asset_picks.json`, `equity_strategies.py`, `alpha_engine/scanner.py` | My audit + peer childlike |
| EQ-5 | Fix SPY/QQQ miscategorized as EQUITY (they are ETFs, tagged category=equity/asset_class=EQUITY) | MED | Small | `multi_asset_picks.json` | My audit |
| EQ-6 | Add data-freshness gate for equity price feeds in scanner (no staleness check on yfinance data) | MED | Medium | `alpha_engine/scanner.py`, `tools/db_freshness_check.py` | My audit |
| EQ-7 | Backfill `asset_class`='EQUITY' for UNK equity picks via `alpha_engine/asset_class.py:55` `EQUITY_SYMBOLS` frozenset | HIGH | Small | `live_picks.db`, `dashboard/live_picks.json`, `stocksunify2_active_picks.json`, `alpha_engine/asset_class.py` | Peer childlike stocks §3.2 |
| EQ-8 | Refresh `current_price`/`unrealized_pnl` for 5 stale active stock picks (~172 days, opened 2026-05-25) via `alpha_engine/fetch_stock_prices.py` | HIGH | Small | `live_picks.db`, `alpha_engine/fetch_stock_prices.py` | Peer childlike stocks §3.1 |
| EQ-9 | Emit `CLOSED/EXIT` events for aged-out equity picks (>30d, no TP/SL) via `audit_trail/universal_pick_resolver.py` | HIGH | Small | `live_picks.db`, `audit_trail/universal_pick_resolver.py`, `data/live_picks.db` (pick_history) | Peer childlike stocks §3.3 |
| EQ-10 | Re-run equity scanners via `alpha_engine/production_scanner.py` (Alpha Engine is DEAD — 9 cancelled + 1 failure, ~24h outage) | P0/Critical | Medium | `alpha_engine/production_scanner.py`, `.github/workflows/alpha-engine-live.yml` | Peer audits infra QW-1 |

## Verification (equity)

**Repro 1 — PnL unit mismatch:**
```python
import json
d = json.load(open("multi_asset/data/multi_asset_closed.json"))
for r in d:
    if r.get("asset_class") == "EQUITY":
        entry = r["entry_price"]; close = r.get("close_price") or r.get("exit_price")
        calc = (close / entry - 1)
        stored = r.get("realized_pnl_pct") or r.get("pnl_pct")
        print(r["symbol"], "stored=", stored, "calc_ratio=", round(calc,6))
```
Expected: AAPL stored `-0.1821` vs calc `-0.00182` (100× off); V stored `-1.7237` vs calc `-0.01724`.

**Repro 2 — Non-unique equity IDs:** `vix_reversal::AAPL::2026-03-11` ×5, `MSFT` ×4 → must be 0 duplicates after fix.

**Repro 3 — ml_score == confidence:** all four equity open picks (HD, TMO, SPY, QQQ) print `True` → must be decoupled. Note: ML code itself is sound (peer childlike); inversion is a data bug.

**Repro 4 — Stale META open pick:** `institutional_picks.json` META `macd_divergence_tuned`, entry 2026-04-03, status OPEN → change to `EXPIRED`.

**Repro 5 — Equity asset_class backfill:** `SELECT COUNT(*) FROM live_picks WHERE asset_class IS NULL OR asset_class='UNK'` → 0 after backfill using `alpha_engine.asset_class.EQUITY_SYMBOLS`.

**Repro 6 — Alpha Engine dead:** `gh run list -w alpha-engine-live.yml` → 9 cancelled + 1 failure in last 10 runs (peer audits).

## Code snippets

**PnL normalization helper** — see `quick_wins/shared/normalize_pnl_units.py`; apply to every EQUITY row.

**Unique equity pick ID (dedupe):**
```python
def dedupe_equity_ids(picks):
    seen = {}; out = []
    for r in picks:
        if r.get("asset_class") != "EQUITY":
            out.append(r); continue
        base = r["id"]
        if base in seen:
            seen[base] += 1
            r["id"] = f"{base}#{seen[base]}"
            r.setdefault("extra", {})["deduped_from"] = base
        else:
            seen[base] = 0
        out.append(r)
    return out
```

**Expire stale META open pick:**
```json
"status": "EXPIRED",
"closed_at": "2026-11-14T00:00:00+00:00",
"close_reason": "Stale open pick > 90 days (entry 2026-04-03), auto-expired",
"pnl_pct": null, "forward_test_only": true
```

**SPY/QQQ category fix:**
```json
"category": "etf", "asset_class": "ETF"
```

**Equity data-freshness gate** (in `scanner.py` after `fetch_market_data`): reject symbols whose latest bar is older than T-1 trading day (26h).

**Backfill asset_class via alpha_engine/asset_class.py:**
```python
from alpha_engine.asset_class import asset_class_from_symbol
# For each UNK equity pick:
pick["asset_class"] = asset_class_from_symbol(pick["symbol"])  # returns "EQUITY" for AAPL, MSFT, etc.
```

**Alpha Engine P0 fix:** Fix `.github/workflows/alpha-engine-live.yml` — remove `cancel-in-progress: true` on 2h cron that kills 45–60 min runs.

## Per-asset-class state (equity)
- 757 live picks, avg PnL -5.22%, 176 positive / 534 negative (peer audits)
- Honest intrabar: n=249, WR 59.0%, PF 0.934, avg -0.0806% (peer audits)
- Dashboard vs raw: PF 0.704 vs 5.555 (-7.9x — filter inverts performance, captures losers discards winners) (peer audits)
- `stocksunify2_active_picks.json`: 14 equity picks ~79 days stale (2026-08-26), all 'STRONG BUY'/BUY, scores 60-100, no price/PnL refresh (peer childlike)
- Only 1 closed stock pick vs 6,400 CRYPTO — stocks pipeline produces almost no resolved outcomes (peer childlike)

Per AGENTS.md: document each implemented fix in `updates/<date>-<description>.md` and commit fix + doc on a clean branch containing only your changes.
