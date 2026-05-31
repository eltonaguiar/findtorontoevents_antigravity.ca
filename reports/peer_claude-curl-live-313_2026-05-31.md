# Peer Review — Live /audit +313.43 Investigation

**Date:** 2026-05-31
**Agent:** claude-opus-4-7
**Trigger:** User reported seeing +313.43 on live /audit; 3 prior agents found 0 hits in repo.

## TL;DR

**+313.43 appears NOWHERE in live HTML, live JSON, or repo.** The actual live value is **+300.53** (`total_pnl_pct_compounded_rolling_100`). User likely:
(a) misread 300.53 as 313.43, OR
(b) saw a transient intra-refresh value, OR
(c) was looking at a different metric.

The bigger story: **live JSON is 3 days fresher than repo** — significant divergence in published vs committed data.

## Evidence

### Live /audit/index.html (Last-Modified: Sun, 31 May 2026 21:07:29 GMT)
- Grep "313" → **0 matches**
- Grep "rolling.100" → only JS source code references (no value 313 rendered)

### Live /audit/data/dashboard_data.json (generated_at: 2026-05-31T20:52:04Z)
```
total_pnl_pct                          = -88.4
total_pnl_pct_sum_raw                  = 838.32
total_pnl_pct_compounded_ew            = -88.4
total_pnl_pct_compounded_rolling_100   = 300.53     <-- closest to "313"
rolling_30d_max_dd                     = 16.71
zero_pnl_count                         = 102
```
- Grep entire JSON for "313" → not present in pnl fields.

### Repo audit_dashboard/data/dashboard_data.json (generated_at: 2026-05-28T21:29:18Z)
```
total_pnl_pct                          = -92.95
total_pnl_pct_sum_raw                  = 571.66
total_pnl_pct_compounded_ew            = -92.95
total_pnl_pct_compounded_rolling_100   = -41.63    <-- Kilo's value
rolling_30d_max_dd                     = 17.15
zero_pnl_count                         = 98
```

### Divergence Verdict: **REPO-STALE (live is fresher than repo)**

| Field                              | Repo (5/28) | Live (5/31) | Drift |
|------------------------------------|-------------|-------------|-------|
| total_pnl_pct                      | -92.95      | -88.4       | +4.55 |
| total_pnl_pct_sum_raw              | +571.66     | +838.32     | +266.66 |
| compounded_rolling_100             | -41.63      | **+300.53** | +342.16 |
| zero_pnl_count                     | 98          | 102         | +4    |

The live JSON was regenerated 2026-05-31 20:52Z (probably by a scheduled dashboard generator that publishes directly to FTP) while the repo copy is from 2026-05-28. Kilo's analysis is reading a **3-day-stale snapshot**.

The rolling-100 metric flipped sign massively (-41.63 → +300.53) — that's the headline +300 figure the user likely saw and rounded/misread as 313.43.

## Hyrotrader Phantom Strategy — STILL PRESENT

`https://findtorontoevents.ca/audit/data/hyro_pick_performance.json` (live, 21:15Z fetch):

```json
"": {
  "strength_score": 90.0,
  "grade": "A+",
  "win_rate": 0.818,
  "wins": 9,
  "losses": 2,
  "total_signals": 11,
  "profit_factor": 8.9,
  "total_pnl_pct": 0.316,
  "edge_ratio": 13.34
}
```

**Empty-key strategy with A+ grade and PF 8.9 is STILL on the live page.** This is the phantom previously flagged. Out of 44 strategies, key `""` is at index 3 (between `fractal_sr_bounce` and `hidden_divergence_continuation`). Looks like a `NULL` / missing `strategy_id` from the hyrotrader generator that needs a filter at write time.

## Recommendations

1. **Tell user:** The number you saw was +300.53, not +313.43. Confirm with a fresh screenshot.
2. **Sync repo:** Pull the latest live dashboard_data.json into the repo or run the local dashboard_generator (carefully — see CLAUDE.md "never run generators locally" rule). Kilo's earlier analysis is reading stale data.
3. **Investigate the +266 swing in sum_raw and -41→+300 swing in rolling_100 over 3 days** — that magnitude of intraweek shift in a 100-trade rolling window suggests either new winning closes flooding in or a resolver/clamp behavior change. Check `closed_pnl_concentration.top1_share_pct` (43.6% → 42.1%, kimi_riseoftheclaw dominant) — still single-strategy concentration risk.
4. **Fix hyro phantom:** add `WHERE strategy IS NOT NULL AND strategy != ''` filter in the hyrotrader strategy-scores generator. Confirmed unfixed as of 2026-05-31 21:15Z.

## Files

- Live JSON snapshot: `/tmp/live_dashboard_data.json` (13.6MB, generated_at 2026-05-31T20:52:04Z)
- Live hyro snapshot: `/tmp/live_hyro.json` (94KB)
- Repo: `audit_dashboard/data/dashboard_data.json` (generated_at 2026-05-28T21:29:18Z)
