-- ===========================================================================
-- 2026-04-25 sportsbet fixes
-- Apply via phpMyAdmin on mysql.50webs.com (database: ejaguiar1_sportsbet).
-- Run in order. Each section is independent — comment out any you want to skip.
-- See reports/SPORTSBET_DB_AUDIT_2026_04_25.md for findings these address.
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- §A2 — trim trailing/leading whitespace in lm_sports_bets.bet_type
-- ---------------------------------------------------------------------------
UPDATE lm_sports_bets
SET bet_type = TRIM(bet_type)
WHERE bet_type <> TRIM(bet_type);

-- Fix the one observed market typo (Smarkets exchange lay leaking into h2h):
UPDATE lm_sports_bets
SET market = 'h2h'
WHERE market = 'h2h_lay';


-- ---------------------------------------------------------------------------
-- §A5 — dedup lm_sports_daily_picks then add unique key
-- ---------------------------------------------------------------------------
-- Keep the lowest-id row in each duplicate group; delete the rest.
DELETE p1 FROM lm_sports_daily_picks p1
INNER JOIN lm_sports_daily_picks p2
  ON  p1.pick_date       = p2.pick_date
  AND p1.event_id        = p2.event_id
  AND p1.outcome_name    = p2.outcome_name
  AND p1.best_book_key   = p2.best_book_key
  AND p1.id              > p2.id;

ALTER TABLE lm_sports_daily_picks
  ADD UNIQUE KEY uniq_pick (pick_date, event_id, outcome_name, best_book_key);


-- ---------------------------------------------------------------------------
-- §A6 — prune lm_sports_value_bets > 30 days
-- ---------------------------------------------------------------------------
-- Snapshot row count first if you want a before/after; otherwise just run.
DELETE FROM lm_sports_value_bets
WHERE generated_at < NOW() - INTERVAL 30 DAY;


-- ---------------------------------------------------------------------------
-- §A1 — flag ungraded daily_picks for reprocessing
-- ---------------------------------------------------------------------------
-- Read-only diagnostic: list rows the settler skipped so we can fix them.
-- Export the result to CSV from phpMyAdmin and feed it into the next sweep.
SELECT id, pick_date, sport, event_id, home_team, away_team,
       commence_time, market, outcome_name, best_book_key
FROM lm_sports_daily_picks
WHERE result IS NULL
  AND commence_time < NOW() - INTERVAL 1 DAY
ORDER BY commence_time DESC;


-- ===========================================================================
-- §A4 — engine + charset conversion (InnoDB / utf8mb4)
-- ===========================================================================
-- DO NOT RUN with the rest of this file. Run off-peak; each ALTER rewrites
-- the whole table. Held back deliberately.
--
-- ALTER TABLE lm_sports_bets         ENGINE=InnoDB, CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- ALTER TABLE lm_sports_daily_picks  ENGINE=InnoDB, CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- ALTER TABLE lm_sports_bankroll     ENGINE=InnoDB, CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- ALTER TABLE lm_sports_clv          ENGINE=InnoDB, CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
