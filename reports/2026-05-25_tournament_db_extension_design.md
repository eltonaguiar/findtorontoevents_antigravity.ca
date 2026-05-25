# Tournament DB Extension — Prompts, Research Basis, Provider Denormalization

**Date:** 2026-05-25
**Target DB:** `ejaguiar1_stocks` @ `mysql.50webs.com`
**Migration file:** `tools/ai_tournament/migrations/202605250300_pick_research_and_prompts.sql`
**Scope:** Add prompt provenance + per-pick research metadata without breaking existing ingest.

## Problem

Today `tournament_picks` (3,161 rows) captures the model's *output* (thesis, entry/TP/SL, rationale) but **not the input**:
- No record of the exact prompt sent to the model for a given submission run.
- No record of how much research the model claims to have done (symbols screened, sources cited).
- No self-audit flag separating informed picks from speculation / random guesses.
- `provider` lives only on `tournament_model_stats`, forcing a JOIN on every dashboard query.

## Design

### 1. `tournament_prompts` — one row per submission run

A "submission" = one model invocation that produced 1..N picks (typically 5–20). Adding
`prompt_text` directly to `tournament_picks` would duplicate the same 4–8 KB prompt across
every pick in that batch (3,161 picks × ~6 KB ≈ 19 MB of redundant text; growing fast).
Normalizing into `tournament_prompts` keeps `tournament_picks` lean and lets us version
prompts independently (A/B prompt experiments become a `prompt_version` filter).

```
tournament_prompts(
  submission_id INT PK AUTO_INCREMENT,
  model_id, provider, prompt_version,
  system_prompt TEXT, user_prompt TEXT,
  ideal_trading_style_by_class JSON,   -- per-asset-class style hints fed to the model
  generated_at DATETIME
)
```

`tournament_picks.prompt_submission_id INT NULL` is the FK back. NULL = legacy pick from
before this migration; ingest after phase 2 must populate it.

### 2. `tournament_pick_research` — one row per pick

Per-pick because the self-audit flag and the screened-symbol count are pick-specific (one
prompt → 10 picks where 7 are `informed` and 3 are `speculation`).

```
tournament_pick_research(
  pick_id INT PK,                       -- FK 1:1 to tournament_picks.id
  symbols_screened INT,                 -- "I looked at 47 names, chose this one"
  sources_jsonl JSON,                   -- [{"url":..., "title":..., "type":"news|filing|chart"}]
  research_basis ENUM('informed','partial','speculation','random_guess'),
  self_audit_response TEXT,             -- raw model answer to the self-audit prompt
  recorded_at DATETIME
)
```

JSON (not JSONL — MySQL 5.7+ has a JSON type) avoids creating a third `tournament_pick_sources`
table. We pay one document parse per render but sources are display-only.

### 3. Denormalize `provider` onto `tournament_picks`

Add `provider VARCHAR(100) NULL`. Yes, it duplicates `tournament_model_stats.provider`, but:
- Dashboards filter by provider on nearly every query (anthropic vs openai vs cerebras).
- `model_id` → provider mapping is stable (we never change a model's provider mid-run).
- Saves a JOIN on the hot path; backfill once, populate on insert thereafter.

## Backwards compatibility

All new columns and tables are additive:
- `tournament_picks.prompt_submission_id` — NULL default. Existing INSERT in
  `tools/ai_tournament/ingest_to_db.py:173-183` (27-column tuple) keeps working unchanged.
- `tournament_picks.provider` — NULL default. Ingest populates when known; backfill SQL
  in the migration sets it from `tournament_model_stats` for historical rows.
- `tournament_prompts` / `tournament_pick_research` — new tables; no impact on legacy reads.
- The `ON DUPLICATE KEY UPDATE` clause (`ingest_to_db.py:184-195`) does NOT touch the new
  columns, so re-ingestion of an old pick won't clobber a later-added prompt link.

## Rollout plan

**Phase 1 — schema (this PR).** Apply migration during a low-traffic window. Idempotent
DDL means re-running is safe. No code changes ship with it.

**Phase 2 — ingest pipeline writes the new fields.** Update `ingest_to_db.py`:
- Before the `tournament_picks` batch, INSERT one `tournament_prompts` row per submission
  file, capture `LAST_INSERT_ID()` as `submission_id`.
- Extend the picks tuple to include `prompt_submission_id` and `provider` (29 cols).
- After picks INSERT, batch-INSERT `tournament_pick_research` rows keyed by
  `(model_id, symbol, submitted_at)` → resolved `pick_id`.
- Source the `research_basis` flag from a new self-audit step in `generate_super_secure_picks.py`
  (model is re-prompted: "Mark each pick as informed | partial | speculation | random_guess").

**Phase 3 — dashboard reads them.** `audit_dashboard/dashboard_generator.py` adds two
columns to the per-pick table: research_basis badge + a "View prompt" expander that pulls
`tournament_prompts.user_prompt`. `provider` filter becomes a top-level facet.

## Risks

- **50webs DDL limits.** Shared MySQL; no superuser. `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`
  is **MySQL 8.0.29+** only; 50webs runs MySQL 5.7 / MariaDB 10.x so we use the
  `information_schema` guard pattern in a stored procedure (see migration). `CREATE TABLE
  IF NOT EXISTS` is universally supported and safe.
- **FK cascade.** `tournament_pick_research.pick_id` FK has `ON DELETE CASCADE` — if we ever
  hard-delete a pick, research vanishes with it. We don't currently hard-delete picks
  (status flips only), so this is acceptable. `tournament_picks.prompt_submission_id` FK
  uses `ON DELETE SET NULL` so dropping a prompt row leaves picks intact.
- **`dedup_key` collisions.** Existing dedup_key = `model_id|symbol|submitted_at`
  (`ingest_to_db.py:121`). The new tables don't touch this. But if Phase 2 ingest writes
  the prompt row *after* the picks (current ordering), the FK back-fill needs a second pass.
  Mitigation: write prompts first within the same transaction.
- **JSON column size.** MySQL JSON cap is ~1 GB but row size is ~64 KB. Sources arrays
  capped at 50 entries (~10 KB) in ingest validation; oversize gets truncated with a flag.
- **Stored procedure DROP.** The migration's guard procedure is dropped at the end so
  re-running the file doesn't accumulate procs. Wrapped in `DELIMITER` blocks; ensure
  the SQL client (50webs phpMyAdmin or pymysql `multi=True`) handles them.

## Acceptance

- Migration applies cleanly on a staging copy (export `tournament_picks` schema, apply
  locally first).
- `ingest_to_db.py` runs unchanged post-migration (regression test: `--dry-run` against the
  current picks file should still produce 27-column tuples that match the existing INSERT).
- New tables visible in `information_schema.tables` with expected indexes.
