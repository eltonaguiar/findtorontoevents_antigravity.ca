# Sportsbet DB Audit — 2026-04-25

**Source:** local dump `C:\Users\zerou\Downloads\ejaguiar1_sportsbet.sql` (29 MB, 83 592 lines)
**DB:** `ejaguiar1_sportsbet` on `mysql.50webs.com`
**Reviewed by:** Claude (auto-audit)

## Headline numbers

| Table | Rows (approx) | Notes |
|---|---|---|
| `lm_sports_bets` | 41 (`AUTO_INCREMENT=42`) | All settled. Mix of pre- and post-guardrail cohorts. |
| `lm_sports_daily_picks` | ~1 200 | At least 2 spot-checked rows ungraded after >70 days (see A1). |
| `lm_sports_value_bets` | ~22 000 | Largest table — no TTL/prune (see A6). |
| `lm_sports_ml_predictions` | 1 260 | Populated, but **not** wired into bet writes (see A3). |
| `lm_sports_clv` | ~10 000 | OK. |

## Findings

### A1. Ungraded picks past commence_time (`lm_sports_daily_picks`)
Spot-checked rows where `commence_time + 70 days < NOW()` still have `result IS NULL`:
- id 17 — `Santa Clara Broncos vs Seattle Redhawks`, 2026-02-12 03:00 — `result=NULL`, `pnl=NULL`
- id 19 — `Washington Huskies vs Penn State`, 2026-02-12 03:30 — `result=NULL`, `pnl=NULL`

These are picks the grader couldn't map (missing scoreboard match or bet-type the settler doesn't understand). Systemic — the daily settle loop silently skips them.

**Fix:** see `2026_04_25_sportsbet_fixes.sql` §A1 — flags rows for reprocessing and emits a CSV of unmappable picks for manual review.

### A2. Inconsistent `bet_type` strings (`lm_sports_bets`)
Values seen in the dump are not normalized:
- `'moneyline'`, `'total'`, `'spread'` (snake-case)
- `'Over 6.50'`, `'Vancouver Canucks ML'`, `'Minnesota Timberwolves ML'` (free-form labels)
- `'Detroit Red Wings '` (trailing space — id 25)
- `market='h2h_lay'` (Smarkets exchange lay leaked into the H2H bucket — id 25)

**Fix:** `2026_04_25_sportsbet_fixes.sql` §A2 trims trailing whitespace and folds free-form labels into the canonical set. Application-side fix to follow in `sports_bets.php` writer.

### A3. Dead ML columns (`lm_sports_bets.ml_*`)
All 41 rows show baseline defaults: `ml_win_prob=0.5000`, `ml_prediction='lean'`, `ml_confidence='low'`, `ml_should_bet=0`, `ml_model_type='baseline'`, `ml_predicted_at=NULL`.

Meanwhile `lm_sports_ml_predictions` has 1 260 rows with real probabilities — they are never copied into `lm_sports_bets` at write time. Dashboards that surface `ml_*` from `lm_sports_bets` show meaningless data.

**Fix (deferred):** wire the ML predictions table into the bet-writer (lookup by `event_id + market + outcome_name`). Out of scope for this PR — flagged here for tracking.

### A4. Storage engine + charset
Every sports table is `ENGINE=MyISAM DEFAULT CHARSET=utf8mb3`.
- MyISAM has no transactions and no row-level locks — concurrent settlement updates table-lock the whole table.
- utf8mb3 cannot store 4-byte UTF-8 (no emoji, no historic CJK). Today the only collateral risk is sportsbook names with emoji marketing, but the cost to fix is low.

**Fix:** convert to `InnoDB / utf8mb4` off-peak (held back from `2026_04_25_sportsbet_fixes.sql` because it rewrites every row — schedule separately).

### A5. Missing uniqueness on `lm_sports_daily_picks`
No unique key on `(pick_date, event_id, outcome_name, best_book_key)`. Re-running the picks generator on the same day double-inserts.

**Fix:** `2026_04_25_sportsbet_fixes.sql` §A5 — dedup keep-first, then add unique index.

### A6. `lm_sports_value_bets` unbounded growth
Largest single table; no TTL. Today's UI never reads rows older than 48 h, so old rows are pure storage tax.

**Fix:** `2026_04_25_sportsbet_fixes.sql` §A6 — one-time prune of rows older than 30 days. Add a nightly cron later (separate task).

### A7. Mass-void event 2026-04-04 18:50:00
12+ rows show `status='settled', result='void', settled_at='2026-04-04 18:50:00'` for Feb 2026 games never graded. This is a deliberate **policy reset** — the `value_bet_gr202604` algorithm and `cohort='post_guardrail_20260404'` started here. Pre-guardrail rows have `cohort=NULL`.

**Not a bug.** Performance reports must filter by `cohort = 'post_guardrail_20260404'` to avoid mixing voided pre-guardrail history. Documented for future analysts.

## Verification (after applying `2026_04_25_sportsbet_fixes.sql`)

```sql
-- A1: no daily picks older than 1 day still ungraded that have a known event_id
SELECT COUNT(*) FROM lm_sports_daily_picks
WHERE result IS NULL AND commence_time < NOW() - INTERVAL 1 DAY;
-- expect: shrinks toward 0 over the next backfill run

-- A2: no trailing whitespace
SELECT COUNT(*) FROM lm_sports_bets WHERE bet_type LIKE '% ' OR bet_type LIKE ' %';
-- expect: 0

-- A5: unique key in place
SHOW INDEX FROM lm_sports_daily_picks WHERE Key_name = 'uniq_pick';
-- expect: 1 row

-- A6: no old value_bets rows
SELECT COUNT(*) FROM lm_sports_value_bets WHERE generated_at < NOW() - INTERVAL 30 DAY;
-- expect: 0
```
