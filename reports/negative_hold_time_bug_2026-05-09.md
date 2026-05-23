# Negative-hold-time bug forensic — 2026-05-09

## TL;DR

**1,025 closed picks** in `trading_picks` have `closed_at < created_at` (negative hold time). PR #862 Q4 noted KC=F (n=55) as ONE symbol affected. Cross-symbol scan found this is a **system-wide data corruption affecting 12+ symbols and 11 source systems**, with `multi_asset_copytrader` driving 45% of cases (n=463).

## Verified state (2026-05-09T21:30Z)

```sql
SELECT COUNT(*) FROM trading_picks 
WHERE TIMESTAMPDIFF(MINUTE, created_at, closed_at) < 0
  AND status NOT IN ('OPEN','active','ACTIVE','SIGNAL');
-- 1,025 rows
```

### Top affected symbols

| symbol | n |
|--------|---|
| DOGEUSDT | 64 |
| EURGBP=X | 58 |
| GBPJPY=X | 57 |
| USDCAD=X | 55 |
| SI=F | 54 |
| HG=F | 39 |
| AUDJPY=X | 34 |
| DYDXUSDT | 33 |
| STRKUSDT | 31 |
| INJUSDT | 29 |
| CADJPY=X | 28 |
| AUDUSD=X | 26 |

Spans CRYPTO + FOREX + FUTURES — not a single-class artifact.

### Top affected sources

| source_system | n |
|---------------|---|
| **multi_asset_copytrader** | **463** (45%) |
| alpha_engine | 194 |
| alpha_engine_fast | 110 |
| prediction_market_agents | 65 |
| cta_replicator | 62 |
| ml_crypto_predictor | 61 |
| non_crypto_consensus | 31 |
| prediction_market_consensus | 16 |
| copy_trader_binance | 10 |
| short_dominant_engine | 2 |

## Sample row pattern

```
id=multi_asset_cftc_cot... WON LONG pnl=+0.065
  src=multi_asset_copytrader strat=cftc_cot_commercial_signal
  created_at=2026-04-19 18:23:31
  closed_at =2026-04-19 00:00:00   ← midnight, BEFORE created
  diff      =-1103 min
```

```
id=multi_asset_cftc_cot... WON LONG pnl=+0.065
  src=multi_asset_copytrader strat=cftc_cot_commercial_signal
  created_at=2026-04-19 13:34:55
  closed_at =2026-04-19 00:00:00   ← same midnight
  diff      =-814 min
```

## Root cause hypothesis

The `closed_at` column gets set to **start-of-day midnight** (00:00:00) instead of actual close time, while `created_at` correctly preserves the intra-day timestamp. Cause is most likely:

1. CFTC COT report scraper reads only the report DATE (not time) from CFTC.
2. `multi_asset_copytrader` ingest does `closed_at = parse_date(report.date)` → returns `2026-04-19 00:00:00`.
3. `created_at` is correctly set from the run timestamp at ingest time (e.g., 13:34).
4. Result: closed_at predates created_at by hours.

The bug is concentrated in cftc_cot_commercial_signal strategy because COT reports ARE date-stamped, not time-stamped — but the resolver should at minimum set `closed_at = max(report_date_midnight, created_at + 1m)`.

## Impact analysis

**Bad analytics outputs** (downstream of `TIMESTAMPDIFF(closed_at, created_at)`):

| Analytics path | Damage |
|----------------|--------|
| Q8 hold-time capital efficiency (PR #862) | Negative hold buckets contaminate ALL buckets |
| Q3 time-of-day WR | Picks attributed to wrong hour |
| forward_validator hold-time gates | Picks pre-resolved before they "started" |
| `at_signal_outcomes.opened_at`/`closed_at` aggregations | Same midnight rollback artifact |
| `MAX_HOLD_HOURS_BY_CLASS` violation detection | Falsely triggers TIME_EXIT |

## Fix (proposed)

### Path A — Writer-side clamp (mysql_trading_sync.py)

```python
# In pick_to_row, AFTER closed_at parsing:
if closed_at and parsed_created_at:
    if datetime.fromisoformat(closed_at) < datetime.fromisoformat(parsed_created_at):
        # Negative hold time → clamp to created_at + estimated hold
        # For cftc_cot daily strategies, default to created_at + 24h
        # For all others, created_at + 1min (avoids divide-by-zero in hold metrics)
        clamp_minutes = 60*24 if 'cftc' in (pick.get('strategy') or '').lower() else 1
        closed_at = (datetime.fromisoformat(parsed_created_at) +
                     timedelta(minutes=clamp_minutes)).strftime("%Y-%m-%d %H:%M:%S")
```

### Path B — DB migration (one-shot fix existing 1,025 rows)

```sql
UPDATE trading_picks
SET closed_at = DATE_ADD(created_at, INTERVAL 1 MINUTE)
WHERE TIMESTAMPDIFF(MINUTE, created_at, closed_at) < 0
  AND status NOT IN ('OPEN','active','ACTIVE','SIGNAL');
```

### Path C — Source-side fix (recommended; requires multi_asset_copytrader access)

Fix at the source: ensure `closed_at` reflects the actual report-publication time (CFTC publishes Tuesday 3:30PM ET), not midnight rollback.

## Recommended sequence

1. **Path A** (writer clamp) — ship this PR. Prevents future damage.
2. **Path B** (one-shot UPDATE) — coordinated with operator. Fixes historical.
3. **Path C** (source fix) — only when multi_asset_copytrader maintainer can be reached.

## NOT IN SCOPE this PR

- Code fix is queued for next session — same file (`mysql_trading_sync.py`) is in PR #876 / #877 / #884 stack; need those to merge first to avoid 4-way conflict.
- DB migration requires user approval (1,025 rows is significant).
- Source-system fix (Path C) is upstream of this repo.

## Refs

- PR #862 FINDINGS.md Q4 — original KC=F flag
- swarm_runs/next_steps_perf_2026-05-09/ — confirmation that this corruption pollutes 30d perf data
- docs/MUTATION_THREE_AXIS_PROTOCOL.md — affected by negative hold (TIMESTAMPDIFF)
- alpha_engine/mysql_trading_sync.py:198-203 — current closed_at parsing path
