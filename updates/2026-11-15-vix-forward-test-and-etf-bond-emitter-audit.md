# 2026-11-15 — VIX>25 + breakout forward test, ETF/BOND emitter audit

Follow-up to `2026-11-15-forex-gate-live-read-vix-combos-and-freshness.md`. Branch
`fix/etf-short-gate-vix-combos-2026-11-15` published to origin (2 commits, 19 files, built from
`origin/main` and cherry-picked so no bot cron commits were carried along).

## 1. Does the 1.80x VIX>25 + breakout lift hold out of sample? No — it hasn't fired.

`tools/vix_breakout_forward_test.py` re-measures the rule on slices of **time** instead of the
harness's train/test split, because "out of sample" is a question about the future and a split over
one window cannot answer it. Same feature pipeline as the discovery harness; 265,991 pooled hourly
bars with VIX coverage (the harness's 324,653 includes pre-VIX history), newest bar 2026-11-14 00:00Z.

| window | bars | signals | base rate | precision | lift | avg fwd |
|---|---|---|---|---|---|---|
| all bars | 265,991 | 246 | 14.65% | 19.92% | 1.36x | +0.582% |
| discovery (before last 90d) | ~ | 245 | 14.84% | 19.59% | 1.32x | +0.546% |
| last 90d | ~ | **1** | — | — | 7.72x | +9.368% |
| last 30d | ~ | **1** | — | — | 8.32x | +9.368% |
| last 14d | ~ | **1** | — | — | 8.55x | +9.368% |
| last 7d | ~ | **0** | — | — | — | — |

**245 of the 246 signals are older than 90 days.** The rule has essentially not fired in the last
quarter, because it requires `VIX > 25` and VIX has been ~19.7 for the whole recent window. There is
therefore **no forward n at all** — the 1.80x can be neither confirmed nor refuted by this test. What
the numbers do say:

- The edge, such as it is, is a **stressed-regime** rule and is dormant in calm tape. Treating the
  discovery figure as a standing expectation would be wrong.
- The two measurements disagree for a mundane reason worth writing down: the harness's 24.14% /
  1.80x is computed against a base rate of 14.52% over all 324,653 bars (including rows where the
  rule is structurally `False` because VIX is NaN), while this test conditions on VIX-covered bars
  only, raising the base to 14.65% and lowering the lift to 1.36x. **The lift number moves with the
  denominator.** The signal count (246) is identical in both, which is the reassuring part.
- Honest status: candidate rule, no forward evidence, not sizeable. The JSON snapshot written by the
  script is the baseline a later run must be compared against — that later run is the real
  out-of-sample test.

## 2. Why ETF `active` and BOND `recent_closed` looked dead — nothing had stopped

The report was "no new picks in >72h". Both are **weekday-only** feeds and the page was read on a
**Sunday**:

| workflow | cron | last run |
|---|---|---|
| `etf-bond-scanner.yml` (ETF) | `35 13 * * 1-5` (Fri 13:35 UTC) | Sat 2026-11-13 13:37Z ✅ |
| `etf-bond-scanner.yml` (Bond) | `0 14 * * 1-5` (Fri 14:00 UTC) | Sat 2026-11-13 14:05Z ✅ |
| `bond-agent.yml` | `32 14 * * 1-5` | 2026-11-13 14:33Z ✅ |

BOND is healthy: `alpha_engine/data/active_picks_bond.json` was committed every weekday at
13:39 and 14:08 UTC on Nov 10, 11, 12 and 13 (`chore: Bond scanner picks merge [skip ci]`). Next run
was due Monday. **Nothing to restart.**

**ETF did have real defects**, just not schedule ones:

1. `alpha_engine/etf_scanner.py` tagged signals with `signal_type` (BUY/SELL) but never set
   `direction` outside `_merge_into_active_picks()`. A non-merge run (the one `etf-bond-scanner.yml`
   performs for its saved artifact) wrote **12 of 15 signals with `direction=None`** and no `id`.
   Direction-aware gates — including the new ETF SHORT class block — could not classify them, and the
   dashboard cannot tell a SELL from a LONG.
   **Fix:** derive `direction`/`id`/`status` at emission, keyed strictly on an explicit
   BUY/LONG/SELL/SHORT `signal_type` (a signal with no `signal_type` stays undirected rather than
   silently defaulting to SHORT). Verified by re-running the scanner: **n=15, `no_direction=0`,
   `no_id=0`, 13 LONG / 2 SHORT**.
2. The 6-hourly `alpha-engine-etf.yml` job is **not an ETF feed**. It runs
   `tools/etf_emitter_spike.py`, whose own payload says `is_draft: true`,
   `ingested_by_dashboard: false`, and publishes the result to
   `alpha_engine/data/active_picks_etf.json`. Grepping every consumer: `dashboard_generator.py` never
   references that path, and `outcome_resolver.py` reads
   `alpha_engine/data/scanner_output/active_picks_etf.json` — the *other* file. So four commits a day
   of "Add ETF picks from emitter" have been landing in a file nothing ingests. That is why the repo
   history looks like ETF is emitting while /audit shows one aged ETF pick.
   **Not "fixed" by wiring it up, deliberately:** those picks carry **no score at all**
   (`no_score=15`), so ingesting them into the audited ledger would admit unscored picks past the
   class floor (`MIN_ELITE_SCORE_BY_CLASS["ETF"] = 35`) and pollute every downstream metric. Recorded
   as the remaining gap instead.

**Remaining gap (needs a decision, not a patch):** ETF needs a scored emitter. Either promote
`etf_emitter_spike` to compute an elite score and merge (a feature with real design choices), or
retire the 6-hourly job so the dead-end file stops implying a live feed. Until then ETF pick supply
is weekday-only via `etf_scanner.py`, and the honest reading of an ETF `active` row is "last weekday
run", not "live".

## 3. Staleness panel no longer false-alarms every weekend

`audit_dashboard/dashboard_freshness.js` judged per-class staleness in wall-clock time, so every
weekend manufactured "⚠ STALE — check that class's scanner" for classes that were never due to run:
Friday 14:00 UTC + 72h lands exactly on Monday 14:00 UTC.

**Fix:** for market-hours classes (ETF, BOND, EQUITY, COMMODITY, FUTURES, INDEX_STOCK, STOCKS,
PENNY_STOCK) the age excludes Sat/Sun, so the 72h budget measures *trading* silence. CRYPTO and
anything unlisted keep wall-clock ageing. Whole weekend days are subtracted rather than exact hours —
slightly generous on purpose, because the failure being guarded against is a false alarm.

Effect: the ETF `active` row read at Sunday 22:00Z for a Thursday pick was 76h wall-clock (STALE) and
is 28h market-aware (AGING); the BOND Friday-14:00Z case goes 56h → 9h. The header text now says
"over 72h of *open-market* silence".

## Verification performed

- `node --check audit_dashboard/dashboard_freshness.js` → OK; the weekend-aware age function was
  exercised in node against the Friday-pick case (56h wall-clock → 9h market-aware).
- `python -m alpha_engine.etf_scanner` (no `--merge`) → 15 signals, `no_direction=0`, `no_id=0`,
  13 LONG / 2 SHORT, `no_score=15`; generated file restored afterwards so no data churn is committed.
- `python3 tools/vix_breakout_forward_test.py` → wrote the 40-line report + JSON snapshot,
  `n=246` all-bars / `n=1` last 90d / `n=0` last 7d.
- `py_compile` on `etf_scanner.py`; `git ls-remote --heads origin fix/etf-short-gate-vix-combos-2026-11-15`
  matches local `d5259137541` before these commits.

Not done: no forward logging harness for the VIX rule (it needs a daily runner to accumulate n), and
the ETF scoring decision above.
