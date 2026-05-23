# Orphan Systems Quarantine — 2026-04-04

**Author:** `antigrav-dash-integrity` (Claude Opus 4.6) after hidden-goldmine hunt
**Status:** DO NOT WIRE these endpoints into `audit_trail/dashboard_generator.py` or the main `/audit/` dashboard.

## Context

A hidden-goldmine hunt starting from `live-monitor/live-monitor.html` identified 5+ sub-dashboards on findtorontoevents.ca that appeared to host high-performance trading strategies orphaned from the main audit page. Spot-checks of the data-quality showed **all of them are unusable or actively misleading**.

## Quarantined endpoints & reasons

### 1. `findstocks/portfolio2/api/advanced_stats.php?action=leaderboard`
**Claim:** 25 algorithms, top ones 60-100% WR with +1,289% (Cursor Genius) / +699% (ETF Masters) total PnL.
**Reality:** These numbers are **parameter-optimized backtest projections**, NOT live trading results. The real-trade endpoint `data.php?type=algo_performance` shows every single one of the 25 algorithms is losing money in live trading:

| Algorithm | Leaderboard (fantasy) | algo_performance (real) |
|---|---|---|
| Cursor Genius | 60.87% WR, +1289.51% | **25.34% WR, −2.64% avg** |
| ETF Masters | 64.47% WR, +699.63% | **6.02% WR, −5.87% avg** |
| Sector Rotation | 63.64% WR, +372.14% | **7.27% WR, −4.52% avg** |
| 13F Hedge Fund Clone | 51.52% WR, +333.74% | **29.41% WR, −2.84% avg** |
| Risk Parity HRP | 63.45% WR, +402.06% | (missing from perf endpoint) |
| PEAD Earnings Drift | 48.12% WR, +309.33% | **30.61% WR, −2.98% avg** |

**Smoking gun:** Cursor Genius metadata includes `"best_for": "Profitable with TP:50% SL:15% Hold:30d"` and `"worst_for": "Current default: -46.4428% return"`. The leaderboard uses the optimized params; live trading uses defaults.

**Also:** individual pick records at `data.php?type=picks` have NO `exit_price`, NO `pnl_pct`, NO `status` — the leaderboard cannot be derived from realized trades.

### 2. `findforex2/portfolio/api/advanced_stats.php`
**Reality:** Returns HTML 404 (endpoint does not exist). `data.php?type=algo_performance` has 8 FX algos with tiny samples (1-3 picks each). Corrupt values like `FX Carry Trade avg=999999.9999` confirm the data is unreliable.

### 3. `findcryptopairs/portfolio/api/advanced_stats.php`
**Reality:** HTML 404. `data.php?type=algo_performance` has 8 CR algos with 1-4 picks each. Corrupt `CR Mean Reversion avg=7403.9846` and single-pick 0% WR rows for all others.

### 4. `findmutualfunds2/portfolio2/api/advanced_stats.php`
**Reality:** Endpoint does not exist. `data.php?type=algo_performance` has 10 MF algos with 1-2 picks each, showing `win_rate=97.50` on single-pick samples — suspicious scaling (likely % of positive days, not pick WR).

### 5. `live-monitor/api/goldmine_tracker.php` — `consolidated` + `live_signal` sub-systems
**Reality:** `consolidated` 9.5% WR / -83%. `live_signal` 1,656 closed / 44.8% WR / -356%. Both bleeding. The "edge" sub-system does show 75% WR on 4 closed picks — too small a sample to trust.

### 6. `investments/goldmines/antigravity/` (Cursor Genius goldmine) — STALE / SYNTHETIC
**Claim:** 49 trades, 67.3% WR, +$117 total, avg $2.39/trade (via `api/unified_predictions.php`).
**Reality:**
- Data is **stale since 2026-02-05** (58+ days at time of audit).
- All 185 system-wide PnL values are integer-dollar ($2.47, $1.80, -$0.82) — synthetic signature, inconsistent with real market execution.
- Round-number aggregates ($47, $117, $18, $23, $53, -$9) suggest backtest-generated test fixtures.
- `recent` endpoint caps at 168h and returns 0 records — dead system.
- No raw-trade endpoint: stats cannot be independently verified per-trade.

### 7. `STOCKS/competition/competition-slim.json` (backtest leaderboard)
**Claim:** Classic Momentum penny_stocks = +1487% return, Sharpe 2.66 (on only 21.4% WR).
**Reality:**
- Low-WR + fat-tail-return combo is a classic curve-fit signature.
- Live forward picks confirm: penny_stocks ML Ranker = **−43.95% total (26.7% WR)**.
- Backtest leaderboard diverges materially from forward performance (already flagged in `audit_trail/quality_gates.py:293`).
- Only the live `forward_picks.json` is trustworthy — it's already integrated as `stocks_competition` (line 5166 of dashboard_generator.py).

**Guidance:** the backtest view of this competition is parameter-curve-fit and should never be wired as a picks source. The live forward tracker is already in the main audit dashboard.

## Guidance for future agents

- **DO NOT** add any `findstocks` / `findforex2` / `findcryptopairs` / `findmutualfunds2` endpoint to `JSON_PICK_SOURCES` in `audit_trail/dashboard_generator.py`.
- **DO NOT** use `advanced_stats.php?action=leaderboard` as a source of truth anywhere — the numbers are walk-forward parameter projections, not trades.
- **If** you need to reconsider any of these systems in the future: cross-check `data.php?type=algo_performance` AND validate a sample of individual picks against real market data before wiring.
- The real audit dashboard (`/audit/`) already covers the legitimately-performing systems: `quan_engine`, `copy_trader_intel`, `alpha_engine`, etc.

## Spot-check methodology (reproducible)

```bash
# 1. Fetch leaderboard
curl -s "https://findtorontoevents.ca/<DOMAIN>/<PATH>/api/advanced_stats.php?action=leaderboard" | jq '.leaderboard'
# 2. Fetch real performance
curl -s "https://findtorontoevents.ca/<DOMAIN>/<PATH>/api/data.php?type=algo_performance" | jq '.performance'
# 3. Compare algorithm-by-algorithm. If numbers diverge significantly → leaderboard is fantasy.
# 4. Fetch individual picks, verify they have exit_price+pnl_pct populated.
# 5. Spot-check a few closed picks against Binance/CoinGecko/Yahoo real market data.
```

## Related
- Main audit: `audit_trail/dashboard_generator.py` (systems: `JSON_PICK_SOURCES` ~L2773)
- User's north-star goal: "hedge-fund-level trusted performance picks" on /audit/
- Commit context: this doc added after the hidden-goldmine hunt spawned by user instruction 2026-04-04.
