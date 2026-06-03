# Category-Taxonomy Fix — Operator Runbook (INCIDENT_OVERALL #88, ENHANCEMENT_OVERALL #109)

**Date:** 2026-06-03
**Author:** claude-opus-4-7 (this session)
**Refs:**
- `INCIDENT_OVERALL #88` (P1/OPEN) — case-mess + ~394 NULL/UNKNOWN auto-taggable rows
- `ENHANCEMENT_OVERALL #109` (BACKLOG, effort=S, target=this sprint) — normalization plan
- `EAGLE4_2026-06-03_CLAUDE_OPUS_4_7.MD` — root-cause analysis linked from #88

## Why this runbook

The incident + enhancement rows are already filed (good). What they lack is a **single
self-contained sequence** an operator can run on 50webs without re-deriving the plan.
This doc provides: (1) exact pre-check, (2) exact SQL, (3) post-check, (4) rollback,
(5) verify-on-deploy (so the 6f2.7 / money_ready / pick_funnel panels all reflect the
new taxonomy). It is a **complement** to the DB rows, not a replacement.

## Pre-check (read-only, mandatory)

```sql
-- 1. Confirm the mess still exists at time of run (counts may have shifted since 2026-06-03 01:50Z)
SELECT category, COUNT(*) AS n
FROM trading_picks
GROUP BY category
ORDER BY n DESC;

-- 2. Confirm the UNKNOWN/NULL rows map cleanly to source_system (no surprises since the rows were filed)
SELECT
  source_system,
  COUNT(*) AS n_unknown
FROM trading_picks
WHERE category = '' OR category IS NULL
GROUP BY source_system
ORDER BY n_unknown DESC;

-- 3. Snapshot the 3 highest-risk reassignments (auto-tag candidates) before mutating
SELECT id, symbol, source_system, category, created_at
FROM trading_picks
WHERE category = '' OR category IS NULL
  AND source_system IN ('ml_bg_system_f', 'signal_validation', 'alpha_engine', 'etf_all_strategies')
ORDER BY source_system, symbol
LIMIT 500;
```

Expected from this session's query (2026-06-02 / 2026-06-03):

| category | n |
|---|---:|
| crypto | 17,067 |
| forex | 14,890 |
| commodity | 7,309 |
| equity | 2,703 |
| stocks | 578 |
| index | 450 |
| futures | 438 |
| '' / NULL (UNKNOWN) | 380 |
| etf | 335 |
| bond | 183 |
| meme | 87 |
| stock | 23 |
| penny | 4 |
| pennystock | 4 |

(Re-run if your numbers differ; that's fine — schema may have grown overnight.)

## The fix (single transaction, no autocommit)

```sql
START TRANSACTION;

-- A. Collapse the case-mess (low-risk: LOWER-only match, 609 rows)
UPDATE trading_picks
SET category = 'equity'
WHERE LOWER(category) IN ('stock', 'stocks', 'penny', 'pennystock');

-- B. Auto-tag UNKNOWN/NULL by source_system pattern (EAGLE4 doc + my session verification)

-- B.1 ml_bg_system_f is a crypto source. Every row with this source_system + non-crypto symbol pattern = crypto
UPDATE trading_picks
SET category = 'crypto'
WHERE (category = '' OR category IS NULL)
  AND source_system = 'ml_bg_system_f';

-- B.2 signal_validation emits FOREX (USD-* / EUR-* / JPY-* / CHF-* symbols)
UPDATE trading_picks
SET category = 'forex'
WHERE (category = '' OR category IS NULL)
  AND source_system = 'signal_validation';

-- B.3 alpha_engine emits a mix of EQUITY + ETF; default to EQUITY for blue-chips, ETF for known ETF tickers
UPDATE trading_picks t
LEFT JOIN (
  SELECT 'SPY'   AS sym UNION ALL SELECT 'QQQ'   UNION ALL SELECT 'IWM'
  UNION ALL SELECT 'XLK' UNION ALL SELECT 'XLF'   UNION ALL SELECT 'XLE'
  UNION ALL SELECT 'XLV' UNION ALL SELECT 'XLI'   UNION ALL SELECT 'XLP'
  UNION ALL SELECT 'XLY' UNION ALL SELECT 'XLU'   UNION ALL SELECT 'XLB'
  UNION ALL SELECT 'VNQ' UNION ALL SELECT 'GLD'   UNION ALL SELECT 'SLV'
  UNION ALL SELECT 'TLT' UNION ALL SELECT 'IEF'   UNION ALL SELECT 'HYG'
  UNION ALL SELECT 'FINX' UNION ALL SELECT 'VLUE'
) AS etf_list ON t.symbol = etf_list.sym
SET t.category = IF(etf_list.sym IS NOT NULL, 'etf', 'equity')
WHERE (t.category = '' OR t.category IS NULL)
  AND t.source_system = 'alpha_engine';

-- B.4 etf_all_strategies — every row is by definition an ETF pick
UPDATE trading_picks
SET category = 'etf'
WHERE (category = '' OR category IS NULL)
  AND source_system = 'etf_all_strategies';

-- Verify before commit (read-only, but inside the same tx so a rollback restores state)
SELECT category, COUNT(*) AS n
FROM trading_picks
GROUP BY category
ORDER BY n DESC;

-- If numbers look right:
COMMIT;
-- If not:
ROLLBACK;
```

**Target state after commit:**

| category | n | change |
|---|---:|---:|
| crypto | 17,267+ | +~200 from ml_bg_system_f |
| forex | 14,920+ | +~30 from signal_validation |
| equity | 2,703 + 601 + ~50 (alpha_engine blue-chips) | +~651 |
| etf | 335 + ~20 (etf_all_strategies) + ~20 (alpha_engine ETFs) | +~40 |
| '' / NULL | 0 | -380 |

## Rollback

The whole thing is one transaction. **If you haven't committed yet: `ROLLBACK;`** That's it.

**If you already committed** and need to revert (within reason — the rows above are
fairly stable labels), the inverse is:

```sql
-- Inverse of A: introduce back the case-mess (revert the rename only)
UPDATE trading_picks
SET category = 'stocks'
WHERE LOWER(category) = 'equity'
  AND id IN (
    -- The 601 rows you just re-tagged — capture them BEFORE the forward update
    -- or use a marker column added in the forward update (recommended)
  );
```

**To make rollback possible, add a marker BEFORE the forward update:**

```sql
-- Before running the main block, add a marker column
ALTER TABLE trading_picks
  ADD COLUMN category_pre_2026_06_03_fix VARCHAR(32) DEFAULT NULL;

-- Populate the marker for every row that will be touched
UPDATE trading_picks
SET category_pre_2026_06_03_fix = category
WHERE LOWER(category) IN ('stock','stocks','penny','pennystock')
   OR category = '' OR category IS NULL;

-- Now run the main block. To rollback:
UPDATE trading_picks
SET category = category_pre_2026_06_03_fix
WHERE category_pre_2026_06_03_fix IS NOT NULL;

ALTER TABLE trading_picks DROP COLUMN category_pre_2026_06_03_fix;
```

This is the **safe** pattern. Adds 2 ALTERs to the run, but rollback is one UPDATE.

## Post-deploy verify (mandatory)

After `COMMIT`, re-verify the surfaces that read from `trading_picks.category`:

1. **`/audit`** — the asset_class_health panel should now show 0/6 classes with "Unknown"
   rows. (Pre-fix, EQUITY + ETF + CRYPTO + FOREX each had 30-200 UNKNOWN rows inflating
   the "Other" bucket.)
2. **`/audit/pick_funnel.html`** — the "78.9% CRYPTO Smart-Picks" cell (DISPUTED) should
   not be affected (that one is signal-quality, not category). The 30d pick-volume bars
   per class WILL shift: equity up, etf up, crypto up, '' / null down to 0.
3. **`/audit/money_ready_verdict.json`** — auto-regenerates on next cron. Run manually
   if you want immediate: `python3 tools/money_ready_verdict.py` (or whatever the
   current generation script is — verify before running).
4. **`/audit/incidents.html`** — `INCIDENT #88` should transition to `RESOLVED` once
   an operator confirms the deploy. Add a closing note:
   ```sql
   UPDATE INCIDENT_OVERALL
   SET status = 'RESOLVED', updated_at = NOW(),
       recommended_fix = CONCAT(recommended_fix, '\n\n[2026-06-03 DEPLOYED per docs/CATEGORY_TAXONOMY_FIX_RUNBOOK_2026-06-03.md — pre-check + main + verify all green]')
   WHERE incident_id = 88;
   UPDATE ENHANCEMENT_OVERALL
   SET status = 'DONE', updated_at = NOW()
   WHERE enhancement_id = 109;
   ```

## Risk

- **Low.** The reassignments are 1-way (from a mess to a clean label), idempotent if
  re-run (the WHERE clauses match the *pre-fix* state), and the marker-column pattern
  makes rollback one UPDATE.
- **Edge cases I did NOT cover:**
  - `category = 'meme'` (87 rows) — could be crypto (meme coins) or equity (meme stocks
    like GME/AMC). **Don't touch in this fix.** File a follow-up.
  - `category = 'index'` (450 rows) — could be ETF (SPY/QQQ/IWM) or FUTURES (ES/NQ)
    depending on the underlying. **Don't touch.** File a follow-up.
  - Rows where `category = 'equity'` but `symbol LIKE '%USDT'` (USDT-quoted crypto on
    an equity-coded source). Sample-size is small but real. **Don't touch.**

## Wiring plan (if you want to keep this from regressing)

Add a CHECK constraint or a post-emit trigger that rejects inserts with a non-canonical
category. Canonical list: `equity, etf, crypto, forex, commodity, futures, bond, index,
meme` (lowercase, single-word). Reject empty string / NULL at the DB layer.

```sql
-- Pre-check before adding: scan for any non-canonical that we'd block
SELECT DISTINCT category FROM trading_picks
WHERE category NOT IN ('equity','etf','crypto','forex','commodity','futures','bond','index','meme')
  AND category != '';
-- Should return 0 rows after the main fix above.

-- Then:
ALTER TABLE trading_picks
  ADD CONSTRAINT chk_category_canonical
  CHECK (category IN ('equity','etf','crypto','forex','commodity','futures','bond','index','meme') OR category = '');
-- Note: allowing '' for the moment (post-emit filler) — tighten after a 7-day grace period.
```

Caveat: any legacy inserts that violate the CHECK will fail. Run the main fix first,
add the CHECK second.

## Files referenced

- `tools/audit_pick_funnel/seed_incidents_enhancements.py` — DB schema for incident/enhancement rows
- `EAGLE4_2026-06-03_CLAUDE_OPUS_4_7.MD` — root-cause analysis (this session's previous opus-4-7)
- `docs/EAGLE_PLAN_CROSS_REFERENCE_2026-06-02.md` — index of the 11+ EAGLE plans
- `INCIDENT_OVERALL #88`, `ENHANCEMENT_OVERALL #109` — DB rows this runbook operationalizes

## Status

**Ready for operator greenlight.** Not auto-running — this touches live `trading_picks`
data that the audit dashboard reads from, and per CLAUDE.md the agent does not run
schema mutations against the live DB without operator approval.
