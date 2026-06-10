# MASTER PROGRESS — Top-Notch Picks Per Asset Class (12h run, 2026-06-10)

Live log for the autonomous run. Plan: `~/.claude/plans/greedy-mixing-puppy.md`. Endorsed by Mercury, Mercury2, Grok ("execute as written") + DeepSeek (convergent root-cause). Cadence: progress every 5-15 min.

## ROOT CAUSE (why months of sub-coin-flip picks)
The project optimized for months against a **corrupted measurement layer** (inaccurate resolver → 23-24% inflated WR; backfill/label contamination; scale-corrupt PFs; over-emission + single-source concentration; promotion on raw not intrabar-true; no per-class entry criteria). Fix order: honest measurement → clean data → correct gates → grow honest n → THEN per-class edge.

## DONE (this session, committed to main)
- **PR1** entry-anchored intrabar resolver in `universal_pick_resolver.py` behind `RESOLVER_ENTRY_ANCHORED` (default OFF=byte-identical) + harness 15/15 green. (36cdfbfc04)
- **#559 MERGED** — geometry guard in the HOURLY `outcome_resolver.py` (the `outcome-resolver.yml` cron resolver) — complementary to PR1; closes the +5548%-fake-pnl class there. (reviewed correct; backfill-half redundant-but-harmless)
- **#557 CLOSED** — its backfill chk-guard was INVERTED (regression) + pillar-cols already identical on main.
- **#556** was merged by a peer; verified main is **clean of the money_ready_picks_generator password leak** (my scrub 104753d8ab survived). `.agents/skills/` (56 docs) came in — not a security issue.
- **Security scrub**: money_ready_picks_generator.py + sign_flip_purge.py cleaned (env/db_env). Scale-corrupt rows quarantined (CRYPTO raw PF 13.6→1.02). Concentration P0 fail-closed. Status GREEN.
- **Debate** (meta→adversarial rounds) on the PR2 plan → REVISE with 11 must-fixes (folded into v2 plan).

## KEY FINDING (picks-now "closest edge candidates")
- `stocks_rsi2_pullback` EQUITY: page shows 5/6 gates pass, RECENCY FAIL. **RECENCY FAIL is a STALE-DATA bug** — live DB has 351 equity picks in 8d (last TODAY); `picks_now.json` is stale (2026-06-09). BUT its 58.8% WR/PF2.68 is the **inflated pre-intrabar number**; honest (INCIDENT #96 dedup) = n140 WR 33.9% LOSING. → NOT a real money-ready; the apparent near-readiness is stale+inflated scoreboard. Confirms PR2 is the unlock.
- `GBPUSD=X` FOREX forex_rsi2 (n114/58.8%/recency✓, PF/DSR unknown, single-source) + `RENDERUSDT inverse_ml` CRYPTO (n15/80%/PF7.7, small-n, emitting) = the other two closest; both need honest PF + n.

## REMAINING SECURITY
- 2 root-level scratch leaks still on main: `investigate_tp_sl_bug.py`, `investigate_tp_sl_bug_v2.py`. → scrub/delete.
- **OPERATOR ACTION (only they can): ROTATE 50webs DB passwords** — already in git history (#556 branch + docs).
- The DB-password-leak-guard CI should be a REQUIRED check (it failed on #556 yet #556 merged).

## NEXT (prioritized)
1. WS-D: refresh stale data — `dashboard_data.json` (5d), `pick_funnel_today/90d.json` (12.8d), `picks_now.json` (1d+ + stale recency) → trigger regen workflows; add missing `generated_at` stamps. (Makes the picks-now recency gate accurate.)
2. WS-B: PR2 entry-anchored shadow-diff (clean snapshot, per-class before/after incl. high/low-conf split per Mercury) → if sane, default ON. Wire money_ready_verdict to the intrabar ledger.
3. WS-B: grow honest n (crypto_ohlcv 180d backfill, 709 NULL-pnl recovery, 82 blank asset_class) — each in a txn w/ row-count sanity + backup.
4. WS-A: scrub investigate_tp_sl_bug*.py; #553 rebase+gitignore picks_now.json+keep clean scripts; GHA fixes (CI Tests timeout, edge-stability push race).
5. WS-C: re-baseline per-class on the post-PR2 cohort; forward-track leads (shadow-only).
6. WS-E: updates/index.html card + FTP deploy; loop.

## RISKS (per peer reviews — mitigations adopted)
Bulk DB mutations → txn + row-count sanity + rollback + backup (Mercury #1). Keep per-class leads shadow-only until 30-60 forward-resolved post-cleanup. n≥100 + DSR + WFE before any T2 claim. Don't flip a class to money-ready on stale/inflated numbers (the stocks_rsi2_pullback trap).
