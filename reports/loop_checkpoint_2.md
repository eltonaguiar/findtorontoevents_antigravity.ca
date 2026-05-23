# Loop Checkpoint 2 — T+~60m (2026-05-08 19:15 UTC)

## Major reality update — 2 prior claims REJECTED

### 1. ❌ "35-day forward-validator freeze" — FALSE

Live `db_health_check.py` `open_bloat` returns **`hours_since_last_close=1`** as of 18:55 UTC. WON/LOST writes are happening hourly.

Possible reasons earlier claim was wrong:
- Earlier `MAX(imported_at)` query may have run on a stale connection
- Earlier query may have hit a different DB (backtests vs stocks)
- Resolver was likely never actually frozen — earlier swarm hypothesis based on partial evidence

### 2. ❌ "Cascade hypothesis: 5 pipelines fail from one stale config" — REJECTED

Grep evidence across resolver chain:

| file | circuit_breaker refs |
|---|---|
| `alpha_engine/production_scanner.py` | YES (lines 274, 276-7, 3490, 3501, 3513, 3533) — gates pick generation only |
| `alpha_engine/forward_validator.py` | **NONE** |
| `alpha_engine/outcome_resolver.py` | **NONE** |

Confirms kilo's earlier swarm-second-opinion carveout. Only **pick generation** is gated by `circuit_breaker_state.json`. Forward-validator + outcome-resolver run independently and continue resolving existing picks.

So even if `circuit_breaker_state.json` IS stale (file content checked earlier — it is), the cascade to all 5 pipelines was a wrong synthesis. Real impact = **only halts NEW pick creation; existing picks still resolve normally**.

## Confirmed findings (from live full health run 18:55)

| check | tier | data |
|---|---|---|
| pnl_integrity (after fix) | red | **43.22% mismatch** (3,698 / 8,556 sampled rows have stored pnl_pct disagree with recomputed (exit-entry)/entry by >1pp) |
| ghost_rows | yellow | 29,856 rows in 11 cohorts (sampled view; full count higher) |
| open_bloat | green | 27.0M OPEN, last terminal write 1h ago |
| index_health | yellow | 5 missing composite indexes |
| outcome_coverage | yellow | raw 12.27% (NOT 0.09% — Kimi's denom was wrong) |
| signal_tier_writer | red | 100% NULL on last 7d (4,940 rows) |
| lm_signals_resolver | red | 96.21% no-resolve |
| won_pnl_contradiction | red | confirmed — WON avg pnl=-40.72 |
| ml_feature_store | red (failed) | column `target_direction` doesn't exist on this table version |
| phantom_expired | (re-run) | needed Decimal*float fix |

## What changed in the action plan

### Demoted (no longer P0)

- ~~Delete `circuit_breaker_state.json` + add 6h TTL guard~~ — **lower urgency**. File IS stale, but its only effect is gating pick-generation, not resolver. If the breaker did silently halt picks for 35 days, that's still a loss but it's not the cascade we feared.
- ~~"5 pipelines broken since 2026-04-02"~~ — only signal_tier_writer + lm_signals_resolver writers are confirmed broken. Forward-validator + algorithm_rolling_perf + at_consensus_picks resolver are independently broken or independently fine — needs separate investigation per pipeline.

### Promoted (still P0)

| # | item | evidence |
|---|---|---|
| P0-NEW | **PnL recompute integrity** | 43.22% mismatch on 8,556 sampled rows. Stored pnl_pct disagrees with computed (exit-entry)/entry. This is the **biggest data-quality bug** that survived all earlier audits. |
| P0-Kimi#1 | trading_picks WON-with-negative-PnL | -40.72 avg pnl on 2,555 WON rows |
| P0-Freebuff#1.2 | 1.6M+ ghost rows from meta_strategy template | confirmed in earlier ghost sweep |
| P0-Ghost#1 | rapid_signals 100% synthetic | 35,352 / 35,352 rows; 6 strategies fire same CVX@$185 same second |
| P0-Ghost#2 | lm_signals 95% NULL pnl | 31,996 / 33,732; resolver never wrote |
| P0-Ghost#3 | at_discord_notifications 100% NULL pnl | 40,242 / 40,242; notification log mistaken as trade source |

### New investigation queue

1. Why is `signal_tier_writer` 100% NULL on 7d? Find writer, fix column setting.
2. Why is `lm_signals_resolver` 96% no-resolve? expire-cron skips outcome resolution.
3. Why is the WON status getting written with negative PnL? Find writer that maps SL_HIT to WON or similar mislabel.
4. Why does `ml_feature_store` not have `target_direction`? Schema drift; check current cols.
5. Why is `pnl_integrity` mismatch 43%? Storage layer != arithmetic; either entry_price/exit_price was updated post-PnL or the pnl_pct calculation uses different formula.

## Done since checkpoint 1

- ✅ Ghost-sweep agent landed 5 new patterns (`reports/ghost_sweep_full_2026-05-08.md`)
- ✅ Doc-reorg safety audit done (`reports/doc_reorg_safety_2026-05-08.md`)
- ✅ Full live db_health_check ran (882s); fixed 2 broken checks (Decimal*float TypeError)
- ✅ Cascade hypothesis investigated via grep; rejected for resolver chain

## Up next

- 2nd full health run finishing in bg (pid 3257); will update db_health.json with all 10 checks fixed
- Investigate penny_picks cron stoppage (highest-leverage Goal #1 win)
- Schedule next wakeup at T+20m

## Files

- `reports/loop_checkpoint_2.md` (this)
- `tools/db_health_check.py` (Decimal*float fix)
- `audit_dashboard/data/db_health.json` (will refresh on bg completion)
