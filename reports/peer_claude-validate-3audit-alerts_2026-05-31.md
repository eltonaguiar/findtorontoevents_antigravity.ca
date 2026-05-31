# Peer Validation — /audit 3-Alert Drift Check

**Reviewer:** claude-validate-3audit-alerts
**Run (EST 2026-05-31 17:10) / (UTC 2026-05-31 21:10)**
**Mode:** READ-ONLY (DB + repo); no /audit edits.
**Scope:** the 3 alerts the user surfaced:
  1. HIGH `volume_spike_breakout` 7d WR 37% vs baseline 51% (>20% drop) — REDUCE
  2. MEDIUM `fc_crypto_pro` silent 144h — MONITOR
  3. MEDIUM `copy_trader_highscore` silent 167h — MONITOR

---

## Alert generator (source-of-truth code)

`cross_aggregation/performance_alerts.py:161` — STRATEGY_DEGRADATION format string:
```
f"{strat}: rolling 7d WR {r_wr:.0f}% vs baseline {base:.0f}% (>20% drop)"
```
`cross_aggregation/performance_alerts.py:248` — DATA_STALE format string:
```
f"{sys} hasn't produced a pick in {gap:.0f}h"
```
DATA_STALE iterates `by_sys` keyed on `p.get("source_system","unknown")` (line 223), gap measured against `_ts(p.get("timestamp"))`.

Live snapshot the alerts are computed against: `audit_dashboard/data/dashboard_data.json`, mtime `2026-05-28 21:43:47Z` (71.4h stale).

---

## Alert 1 — volume_spike_breakout (STRATEGY_DEGRADATION)

### PRE-EXPECTATION
Claim: 7d WR 37%, baseline 51%, drop 14pp absolute / ~27% relative.

### Query A — `ejaguiar1_stocks.trading_picks`
```sql
SELECT
  SUM(CASE WHEN created_at >= NOW()-INTERVAL 7 DAY  AND status IN ('WON','LOST','CLOSED','EXPIRED') THEN 1 ELSE 0 END) AS n_7d,
  SUM(CASE WHEN created_at >= NOW()-INTERVAL 7 DAY  AND status='WON' THEN 1 ELSE 0 END) AS w_7d,
  SUM(CASE WHEN created_at >= NOW()-INTERVAL 30 DAY AND status IN ('WON','LOST','CLOSED','EXPIRED') THEN 1 ELSE 0 END) AS n_30d,
  SUM(CASE WHEN created_at >= NOW()-INTERVAL 30 DAY AND status='WON' THEN 1 ELSE 0 END) AS w_30d,
  SUM(CASE WHEN status IN ('WON','LOST','CLOSED','EXPIRED') THEN 1 ELSE 0 END) AS n_all,
  SUM(CASE WHEN status='WON' THEN 1 ELSE 0 END) AS w_all
FROM trading_picks WHERE strategy='volume_spike_breakout';
```
**RAW RESULT:** `(n_7d=1, w_7d=0, n_30d=2, w_30d=0, n_all=5, w_all=0)` — 5 picks ever, 0 wins.

Cross-check by `source_system='volume_spike_breakout'`: **0 rows** (column doesn't carry that string). Cross-check by `strategy='Volume Spike Scout'`: also 0 closed picks.

### Query B — `rapid_fire_data/closed_picks.json` (where this strategy actually lives)
194 closed picks for `source_system=='volume_spike_breakout'`. Wins = `status in {WON,TP,TP_HIT}` OR `pnl_pct > 0`. Bucketed by `closed_at` vs now:
- **7d window:** 18 closed, 2 wins → **WR 11.1%**
- **prior (>7d):** 176 closed, 30 wins → **WR 17.0%**
- **all-time:** 194 closed, 32 wins → WR 16.5%
- latest `closed_at`: `2026-05-31 19:14:21Z` (1.9h ago — strategy IS actively producing)

### VERDICT — REFUTES (numbers wrong, direction right)
- The alert's "37% vs 51%" figures are **not reproducible** against either trading_picks DB (n=5 total) or rapid_fire_data (actual 11% vs 17%).
- The strategy IS underperforming, but the **baseline 51%** is fictional — actual baseline is 17%. This is a **dead strategy with a noisy 6pp dip**, not a 14pp acute degradation.
- Likely cause: alert was computed from a stale `enhanced_system_stats.json` (`generated_at = None`, snapshot containing `copy_trader_highscore 88.9%/9` and `fc_crypto_pro 0%/1`) whose baseline figures don't match current data.
- Recommended action: **DOWNGRADE alert to "stale baseline — strategy already underperforming long-term"**, do not treat as new degradation event.

---

## Alert 2 — fc_crypto_pro (DATA_STALE)

### PRE-EXPECTATION
Claim: 144h since last pick.

### Query — `ejaguiar1_stocks.trading_picks`
```sql
SELECT MAX(created_at), COUNT(*) FROM trading_picks WHERE strategy='fc_crypto_pro';
SELECT MAX(created_at), COUNT(*) FROM trading_picks WHERE source_system='fc_crypto_pro';
```
**RAW RESULT:** both `(NULL, 0)` — fc_crypto_pro has NEVER written to the canonical trading_picks DB.

### Cross-check — `audit_dashboard/data/dashboard_data.json`
6 entries with `source_system='fc_crypto_pro'`. Latest timestamp: `2026-05-25 20:38:02Z`.
- At snapshot time (`2026-05-28 21:43Z`): gap = **73.1h** (NOT 144h).
- At wall-clock now (`2026-05-31 21:10Z`): gap = **144.5h**.

### VERDICT — MATCHES (against live-recomputed gap; REFUTES if reading the static snapshot)
The 144h claim **matches reality NOW** because the alert is being re-computed at page load against the static dashboard_data.json (whose freshest fc_crypto_pro entry is 2026-05-25 20:38Z). The 73h figure embedded in the snapshot itself is what the alert WOULD say if computed at snapshot generation time.

**(EST 2026-05-31 17:10) gap = 144.5h ✓**

---

## Alert 3 — copy_trader_highscore (DATA_STALE)

### PRE-EXPECTATION
Claim: 167h since last pick.

### Query — `ejaguiar1_stocks.trading_picks`
```sql
SELECT MAX(created_at), COUNT(*) FROM trading_picks WHERE strategy='copy_trader_highscore';
SELECT MAX(created_at), COUNT(*) FROM trading_picks WHERE source_system='copy_trader_highscore';
```
**RAW RESULT:** both `(NULL, 0)` — no canonical DB rows ever.

### Cross-check — `audit_dashboard/data/dashboard_data.json`
20 entries with `source_system='copy_trader_highscore'`. Latest timestamp: **`2026-03-19 11:50:50Z`** (73 days old).
- At snapshot time: gap = **1689.9h**.
- At wall-clock now: gap = **1761.3h**.

### VERDICT — REFUTES (off by 10x — under-reported)
**Claimed 167h vs actual 1761h.** The alert generator's gap calculation is clamping or capped somewhere; the source_system has been completely dead since **2026-03-19** (74 days ago, not 7 days).

Hypothesis: `_ts()` parser silently fails on whatever timestamp format these 20 entries carry, and falls back to a recent default. Worth a follow-up bug ticket — alerts of this class are unreliable.

**(EST 2026-05-31 17:10) actual gap = 1761h, not 167h. Alert understates staleness 10x.**

---

## UN-FLAGGED alerts the dashboard missed

### Silent source_systems >144h, total ≥20 picks (canonical DB)
```sql
SELECT source_system, MAX(created_at), COUNT(*),
       TIMESTAMPDIFF(HOUR, MAX(created_at), NOW()) AS hours
FROM trading_picks WHERE source_system IS NOT NULL AND source_system<>''
GROUP BY source_system HAVING hours>144 AND COUNT(*)>=20
ORDER BY hours ASC;
```
**RAW RESULT — 13 source_systems silent >144h, NONE in current alert set:**
| source_system | last_pick | total | hours_silent |
|---|---|---|---|
| forex_copy_trader | 2026-05-25 00:49Z | 229 | 164 |
| polymarket_momentum | 2026-05-22 18:56Z | 402 | 218 |
| prediction_market_consensus | 2026-05-04 23:46Z | 316 | 645 |
| auto_dna_mutation | 2026-04-25 04:25Z | 48 | 880 |
| institutional_picks_engine | 2026-04-03 00:06Z | 42 | 1413 |
| ml_crypto_pred | 2026-03-29 00:33Z | 69 | 1532 |
| dna_winner_picks | 2026-03-29 00:53Z | 22 | 1532 |
| kimi_signal_tracking | 2026-03-29 00:06Z | 176 | 1533 |
| battleground | 2026-03-28 23:40Z | 152 | 1533 |
| mercury2 | 2026-03-28 23:51Z | 89 | 1533 |
| paper_trading | 2026-03-28 23:51Z | 35 | 1533 |
| breakout_b_ml | 2026-03-27 13:38Z | 20 | 1567 |
| multi_asset_scanner | 2026-03-13 08:19Z | 44 | 1908 |

### Silent strategies >144h, total ≥10 picks
Returned 70 rows. Highlights agents should at minimum see:
- `myfxbook_retail_contrarian` (n=3078, silent 152h)
- `ig_contrarian_sentiment` (n=4276, silent 152h)
- `forex_rsi2_mean_reversion` (n=2554, silent 152h)
- `forex_carry_momentum` (n=1182, silent 231h)
- `futures_ema_stack_momentum` (n=344, silent 1415h)
- 13× `ml_enhanced_*` strategies silent 147–167h

### >20pp WR drop 7d vs 30d
Query ran against both `strategy` and `source_system` with thresholds n_7d≥10 / n_30d≥30:
```sql
... HAVING n7>=10 AND n30>=30 ... drop = wr30-wr7 > 0.20
```
**RAW RESULT: 0 rows.** No clean ≥20pp WR drop reproducible from canonical DB. This means the volume_spike_breakout HIGH alert has **no companion** — either no other strategy is collapsing in the DB, or all strategies with that pattern are below the n=10 floor and being filtered out.

---

## Summary

| # | Alert | Claim | Reality | Verdict |
|---|---|---|---|---|
| 1 | volume_spike_breakout 7d 37% vs 51% | drop 14pp | rapid_fire actual 11% vs 17% (drop 6pp); DB has only n=5 ever | **REFUTES** (baseline 51% is fictional) |
| 2 | fc_crypto_pro silent 144h | 144h | 144.5h vs now (TRUE); 73h at snapshot time | **MATCHES** (live-recomputed) |
| 3 | copy_trader_highscore silent 167h | 167h | **1761h** (74 days dead since 2026-03-19) | **REFUTES** (10× under-reported) |

**Drift count:** 2/3 alerts have wrong numbers. Alert 1 has a wrong baseline. Alert 3 is off by ~1600h.
**New alerts missed:** ≥13 silent source_systems, ≥70 silent strategies. None of these surface on `/audit` today.
**EST timestamp added:** YES — every verdict block is stamped (EST 2026-05-31 17:10).

### Recommended follow-ups (no edits this window — peer-collision freeze until 21:30Z)
1. **Bug ticket** for `cross_aggregation/performance_alerts.py:_data_staleness` — gap calc returned 167h for a 1761h gap; suggests timestamp parser fallback hiding dead sources.
2. **Baseline-source audit** for STRATEGY_DEGRADATION — `_strategy_baseline_wr_from_stats` is pulling 51% baseline for a strategy whose actual all-time WR is 17%. Either `enhanced_system_stats.json` is stale or the strategy-name join is leaking from a different family.
3. **Stale-snapshot guard** — `audit_dashboard/data/dashboard_data.json` is 71h stale; any alert sourced from it should display its `generated_at` and refuse to fire if older than N hours.
4. **Add the 13 missed silent source_systems** to the alert feed (they pass the same DATA_STALE threshold the current 2 alerts pass).
