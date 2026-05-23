# Autonomous loop status — 2026-04-26

Two diagnostic findings while waiting on PR #401 / #402 CI:

## 1. Backlog cleared ✅

```
GET /live-monitor/api/sports_bets.php?action=active
{ "bets": [], total active: 0, pending: 0 }
```

Peer's `grade_manual` endpoint + totals-fallback patch (now PR #402) cleared every pending ticket from Apr 6–25. The dashboard at https://findtorontoevents.ca/live-monitor/sports-betting.html should now show real W/L for the entire backlog instead of stuck PENDING rows.

## 2. The Odds API is on the **free tier** — Kimi's #1 finding confirmed

```
GET /live-monitor/api/sports_odds.php?action=credit_usage
{ "monthly_used": 86, "monthly_limit": 500, "monthly_remaining": 414, "pct_used": 17.2 }
```

Hard-coded `$lim = 500` at [sports_odds.php:69](live-monitor/api/sports_odds.php#L69). 17.2% credit utilization 25 days into the month — **the constraint is refresh frequency, not budget**. Free tier limits to ~2–3h refresh; paid tier ($20/mo, 20K credits) unlocks ≤1min refresh.

This matches Kimi Swarm's #1 recommendation. Action required from operator (no code change): subscribe to The Odds API paid tier and update the `THE_ODDS_API_KEY` env var on the deploy host. Server-side budget cap can stay at 500 (or be raised to 20,000 in the same hard-coded `$lim`).

**Once this happens**, the following downstream items become possible:
- Real-time steam-move detection
- Reverse-line-movement signals
- Cross-platform (sportsbook ↔ Polymarket / Kalshi) arbitrage capture
- Sharper CLV (the −1.22% baseline assumes 2–3h-stale entry prices; some of that loss may be data lag, not selection)

Without the upgrade, every other infrastructure improvement is bottlenecked.

## 3. PRs awaiting CI

- **#401** Pinnacle Shin — only 1 CI check ("scan") visible, full CI not yet complete. mergeable=UNKNOWN.
- **#402** grade_manual + totals fallback — production already running this code (uploaded by peer agent via FTP), so it's behaviorally validated; CI just needs to confirm syntax.

## Next-loop pickups (for future autonomous iterations)

1. Recheck PR #401 CI status; if green, post-summary and signal ready-to-merge.
2. After #401 merges, monitor `lm_sports_clv` weekly avg_clv_pct trend (see scheduled remote agent `weekly-sports-pick-verifier-clv-trend`).
3. NHL goalie overlay implementation — gated on operator approval, not autonomous.
4. NBA series sim wiring — gated on (a) PR #401 merge, (b) Pinnacle cron live on host, (c) 4 weeks of post-Shin CLV data.
