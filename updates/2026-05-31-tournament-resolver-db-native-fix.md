# AI Tournament — DB-native resolver fix (INCIDENT_OVERALL #43)

**Date:** 2026-05-31 · **Author:** claude-opus-4.8 (`/money-maker-readyv2`) · **Status:** fix proposed (dry-run verified; not yet applied to production)

## What was broken
The AI-tournament resolution path is **JSON-bound**:
1. `tools/ai_tournament/price_tracker.py` resolves OPEN picks **only** if they are still in the recent `data/ai_tournament/submissions/*.json` glob, writing results to `ai_tournament_picks_latest.json`.
2. `tools/ai_tournament/ingest_to_db.py` propagates those resolutions back to MySQL via `ON DUPLICATE KEY UPDATE status=…`.

**Consequence:** any OPEN pick that ages out of the submissions glob window can **never** be resolved in the DB. There is no DB-native resolver. As of 2026-05-31 this stranded **2,693 OPEN rows** (1,479 aged >5d). DB resolution throughput collapsed: **1,725 resolved 2026-05-24 → 1 on 05-25 → 0 for six days.** This starves every model of resolved sample and blocks the top tournament models (deepseek_v4, cursor_agent, llama4_scout — each ≥57 resolved with ≥61 OPEN in backlog) from reaching the institutional n≥100 bar.

The two scheduled jobs (`mysql-stale-picks-resolver.yml`, `ai-tournament-price-tracker.yml`) report **success** daily but resolve nothing in the DB — `mysql_stale_picks_resolver.py` does not touch `tournament_picks`, and `price_tracker.py` only mutates JSON for picks still in the glob.

## What changed
New `tools/ai_tournament/resolve_db_picks.py` — reads OPEN `tournament_picks` **directly from the DB** (independent of the JSON glob), reuses the *exact* tested TP/SL/expiry logic and price-failover from `price_tracker.py` (`resolve_pick`, `fetch_price`), and writes resolutions straight back to the DB.
- **Dry-run by default**; `--apply` gates all DB writes.
- `--expired-only`, `--asset-class`, `--limit` for safe, staged rollout.
- UPDATE is guarded `WHERE id=%s AND status='OPEN'` (idempotent; won't clobber already-resolved rows).

## Live verification (dry-run, no writes)
```
$ python tools/ai_tournament/resolve_db_picks.py --limit 15
[resolve-db] 15 OPEN candidate picks loaded (all; DRY-RUN)
[resolve-db] would resolve: WIN=3 LOSS=4 | still_open=5 price_fail=3
  id=18627 -> WIN  pnl=19.94% (TP_HIT)
  id=18621 -> LOSS pnl=-3.84% (SL_HIT)
  ...
```
**7 of 15 overdue picks (47%) had already hit their TP/SL** and should have resolved days ago — confirming the backlog is full of resolvable picks the JSON pipeline silently dropped.

## Known limitation
3/15 `price_fail` were `GC` (gold futures): `price_tracker.fetch_price` passes the bare symbol to yfinance, which needs the `=F` suffix (`GC=F`) for futures/commodities. Commodity/futures coverage needs a symbol-normalization follow-up; equity/ETF/bond/crypto/penny resolve fine. Unresolved rows simply stay OPEN (no harm).

## Rollout (recommended)
1. `--apply --asset-class CRYPTO --limit 200` (largest, cleanest universe) → verify leaderboard.
2. Sweep remaining classes in batches.
3. Wire `resolve_db_picks.py --apply` into `ai-tournament-price-tracker.yml` (after `price_tracker.py`) so DB resolution becomes self-healing and never re-strands.
4. Fix the `=F` symbol normalization for commodity/futures.

**Acceptance:** short-TF OPEN picks aged >5d drop below 50; the 3 T1 models reach n_resolved ≥100; daily DB resolutions resume.

*Read-only investigation + dry-run only; no production rows mutated and no production strategy code changed in this PR.*
