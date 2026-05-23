# Predictions, Database, and Scoring Analysis

Date: 2026-04-06

## Executive Summary

The current prediction stack is really two systems:

1. `predictions/data/predictions.db` is a small SQLite ledger of scraped social calls.
2. `audit_trail/data/dashboard_payload.json` is the richer live scoring layer used by the audit dashboard.

Those systems are being talked about as if they are one thing, but they are not. The SQLite database does not store `score`, `trust_score`, or calibrated `confidence`; the dashboard layer adds those later. That mismatch is the main reason the existing analysis story feels blurry.

The database has useful directional signal coverage, but weak execution integrity. The scoring layer is materially more useful for ranking live picks, but its confidence values are explicitly uncalibrated and its thresholds have drifted across docs.

## Sources Reviewed

- `predictions/db.py`
- `predictions/validation/price_validator.py`
- `predictions/data/predictions.db`
- `predictions/data/leaderboard.json`
- `audit_trail/data/dashboard_payload.json`
- `audit_trail/quality_gates.py`
- `audit_dashboard/blueprint_generator.py`
- `docs/ACTIVE_PICKS_SCORING_REVIEW_2026-04-05.md`
- `docs/TP_CALIBRATION_2026-04-06.md`

## 1. Prediction Database Reality

### What the SQLite schema actually stores

`predictions.db` stores raw prediction records with:

- predictor identity
- platform
- symbol
- direction
- `entry_price`
- `take_profit`
- `stop_loss`
- `sentiment_score`
- source URL/text
- scrape timestamp
- status / resolved PnL

This is visible in [predictions/db.py](/e:/findtorontoevents_antigravity.ca/predictions/db.py#L23) through [predictions/db.py](/e:/findtorontoevents_antigravity.ca/predictions/db.py#L41).

Important absence: there is no database column for `score`, `elite_score`, `trust_score`, or a first-class `confidence` field. The closest native field is `sentiment_score`.

### Current database counts

From the live SQLite file on 2026-04-06:

- 367 predictions
- 246 predictors
- 276 LONG / 91 SHORT
- platform mix:
  - StockTwits: 194
  - Reddit: 87
  - Polymarket: 45
  - TradingView: 36
  - Twitter: 5

### Status distribution

- `EXPIRED_WIN`: 217
- `EXPIRED_LOSS`: 107
- `TP_HIT`: 34
- `SL_HIT`: 9

This means 324 of 367 rows were closed by time expiry, not by hitting TP/SL. The directional hit rate looks decent on the surface, but most outcomes are "price was higher/lower 48h later" rather than "targeting logic worked."

The 48-hour expiry rule is hard-coded in [price_validator.py](/e:/findtorontoevents_antigravity.ca/predictions/validation/price_validator.py#L19), and expired trades are resolved as `EXPIRED_WIN` / `EXPIRED_LOSS` in [price_validator.py](/e:/findtorontoevents_antigravity.ca/predictions/validation/price_validator.py#L163).

### Structural gaps

- `asset_class` exists in schema but all 367 rows are null, so cross-asset analysis is currently lost despite the column being present in [predictions/db.py](/e:/findtorontoevents_antigravity.ca/predictions/db.py#L77).
- `predictions/data/leaderboard.json` is stale and currently shows `active_count: 0` with last update `2026-03-26T16:14:40Z`.
- The social prediction DB is effectively a resolved archive right now, not a fresh live feed.

## 2. Data Integrity Problems

### TP/SL direction integrity is still dirty

Rows with invalid directional geometry still exist:

- LONG with TP at or below entry: 17
- LONG with SL at or above entry: 1
- SHORT with TP at or above entry: 16
- SHORT with SL at or below entry: 3

That is 37 broken TP/SL relationships in a 367-row database.

The validator does contain correction logic for this in [price_validator.py](/e:/findtorontoevents_antigravity.ca/predictions/validation/price_validator.py#L91), but the historical rows are still contaminated.

### PnL is not analytically trustworthy yet

The database-wide average PnL is unusable because of legacy garbage values:

- minimum `outcome_pnl_pct`: `-43019904.302`
- 11 rows are below `-100%`

Examples:

- DOGE short with `entry_price = 0.09298` and `take_profit = 40000.0` marked `TP_HIT`
- BTC short with `take_profit = 4000000000.0` marked `TP_HIT`
- XRP short with `take_profit = 600.0` marked `TP_HIT`

So the current predictor leaderboard can show absurd contradictions such as:

- very high win rate
- strongly negative average PnL

That is not an edge signal. It is a data hygiene problem.

The validator now caps recalculated PnL to `[-100, 500]` in [price_validator.py](/e:/findtorontoevents_antigravity.ca/predictions/validation/price_validator.py#L203), but those old outliers remain in the database and need a cleanup/backfill pass.

## 3. Scoring Layer Reality

### Live payload stats

From `audit_trail/data/dashboard_payload.json` generated on `2026-04-06T16:16:21Z`:

- 116 active picks
- average score: `29.46`
- average elite score: `34.43`
- average confidence: `0.772`
- average trust score: `4.52`
- zero-score picks: `17` (`14.66%`)

Score buckets:

- `70+`: 2
- `50-69`: 21
- `30-49`: 48
- `1-29`: 28
- `0`: 17

Top live names by score are currently led by `SUIUSDT`, `AAVEUSDT`, `TAOUSDT`, `SHIBUSDT`, `DOTUSDT`, `HBARUSDT`, `INJUSDT`, `ATOMUSDT`, `WUSDT`, and `XRPUSDT`.

### Threshold drift: docs vs code

The live code currently sets:

- `SMART_PICKS_MIN_SCORE = 60`
- `SMART_PICKS_MIN_CONFIDENCE = 0.60`

See [quality_gates.py](/e:/findtorontoevents_antigravity.ca/audit_trail/quality_gates.py#L292) and [quality_gates.py](/e:/findtorontoevents_antigravity.ca/audit_trail/quality_gates.py#L317).

Using the current live payload:

- at score floor `70`: 2 smart picks qualify
- at score floor `60`: 11 smart picks qualify
- at score floor `55`: 14 qualify
- at score floor `50`: 14 qualify

So any doc still saying "Smart Picks need 70" is stale relative to the code.

### Score appears useful; confidence does not yet mean probability

The scoring code comments claim:

- `elite_score IC = +0.26`
- score `50-60` band = `59.7% WR`
- score `0-30` band = `21.9% WR`

That is in [quality_gates.py](/e:/findtorontoevents_antigravity.ca/audit_trail/quality_gates.py#L326).

That suggests score is directionally predictive.

But confidence is explicitly described as uncalibrated in [blueprint_generator.py](/e:/findtorontoevents_antigravity.ca/audit_dashboard/blueprint_generator.py#L748): a `0.8` confidence value does not mean `80%` probability of profit. It is just a strategy-local strength number.

## 4. Where the Edge Probably Is

### 1. Use score for ranking, not the raw social DB

The social DB is still useful for source collection and contributor tracking, but not as the primary ranking layer. The audit scoring stack already carries:

- score
- elite score
- trust score
- agreement count
- forward metrics
- richer freshness logic

That is where selection edge currently lives.

### 2. Treat expiry win rate separately from TP/SL effectiveness

The database currently rewards "was right within 48 hours" much more than "produced executable TP/SL geometry." Those are different skills and should be split into separate metrics:

- directional accuracy
- TP hit rate
- SL avoidance rate
- expected value using actual exits

### 3. Preserve score, but recalibrate confidence

The score comments imply monotonic predictive power. Keep that.

The next quality step is calibration:

- bucket confidence into deciles
- compare predicted vs realized win rate
- compute Brier score / ECE
- remap each strategy's native confidence scale into a common probability scale

### 4. Finish TP/SL normalization and volatility adaptation

The newer TP calibration work is materially stronger than the old static TP rules. `docs/TP_CALIBRATION_2026-04-06.md` is pointing in the right direction:

- static TP was too blunt
- symbol/volatility tiers are better
- winners cluster around 2-3%

That logic should be pushed deeper into source ingestion and into any backfill/repair job so old rows stop poisoning evaluation.

## 5. Optimization Recommendations

### Database fixes

1. Add a cleanup migration for historical broken TP/SL rows.
2. Recompute `outcome_pnl_pct` for all rows using the capped validator logic.
3. Backfill `asset_class` for every prediction.
4. Mark legacy-corrupt rows with a boolean like `is_invalid_execution = 1` instead of silently mixing them into averages.
5. Split raw source storage from evaluation storage.

Suggested separation:

- `predictions_raw`: exactly what was scraped
- `predictions_normalized`: cleaned entry/TP/SL/direction values
- `prediction_outcomes`: exit logic and resolved PnL
- `prediction_scores`: dashboard-era score/trust/confidence snapshot

### Scoring fixes

1. Keep `score` as the main rank feature.
2. Stop describing `confidence` as if it were calibrated probability until calibration exists.
3. Store the score snapshot in a durable table if you want proper post-hoc analysis.
4. Freeze the Smart Picks threshold in one place and update docs automatically from code.

### Evaluation fixes

1. Report win rate three ways:
   - expiry win rate
   - TP/SL resolved win rate
   - PnL-weighted expectancy
2. Exclude corrupted rows from portfolio analytics.
3. Track per-platform data quality, not just per-platform win rate.

## 6. Recommended Redis Bus Messages

These are proposed coordination payloads only. They were not sent.

### A. Data hygiene request

```json
{
  "type": "analysis_request",
  "topic": "predictions_db_hygiene",
  "priority": "high",
  "timestamp": "2026-04-06T16:30:00Z",
  "from": "codex-analysis",
  "summary": "Clean historical TP/SL corruption and recalculate social prediction PnL",
  "findings": {
    "predictions": 367,
    "bad_tpsl_rows": 37,
    "pnl_below_minus_100": 11,
    "asset_class_null_rows": 367
  },
  "actions_requested": [
    "Backfill asset_class",
    "Repair invalid TP/SL direction rows",
    "Recompute outcome_pnl_pct with capped validator logic",
    "Flag legacy-corrupt rows for exclusion"
  ]
}
```

### B. Scoring calibration request

```json
{
  "type": "analysis_request",
  "topic": "score_confidence_calibration",
  "priority": "high",
  "timestamp": "2026-04-06T16:31:00Z",
  "from": "codex-analysis",
  "summary": "Score looks predictive but confidence is still strategy-local and uncalibrated",
  "findings": {
    "active_picks": 116,
    "avg_score": 29.46,
    "zero_score_pct": 14.66,
    "smart_picks_at_70": 2,
    "smart_picks_at_60": 11
  },
  "actions_requested": [
    "Run decile calibration on confidence",
    "Compute Brier score and ECE by strategy family",
    "Persist score/trust/confidence snapshots for closed-pick analysis",
    "Publish one canonical Smart Picks threshold"
  ]
}
```

### C. Portfolio/routing recommendation

```json
{
  "type": "portfolio_guidance",
  "topic": "selection_priority",
  "priority": "medium",
  "timestamp": "2026-04-06T16:32:00Z",
  "from": "codex-analysis",
  "summary": "Use audit score layer for ranking; use predictions.db as raw source intake only",
  "routing": {
    "primary_rank_source": "audit_trail/data/dashboard_payload.json",
    "raw_source_archive": "predictions/data/predictions.db",
    "avoid_using_for_pnl": "legacy social DB rows until hygiene pass completes"
  }
}
```

## 7. Bottom Line

The project already has the beginnings of an edge, but it is not in the raw social prediction database by itself. The edge is in:

- the audit score stack
- trust-weighted filtering
- forward metrics
- newer TP calibration work

The raw SQLite DB is still valuable, but only after it is treated as intake data first and execution-quality truth second.

## 8. Executed Follow-Through

The following next steps were implemented after this analysis:

- Added hygiene metadata columns in [db.py](/e:/findtorontoevents_antigravity.ca/predictions/db.py).
- Added [historical_hygiene.py](/e:/findtorontoevents_antigravity.ca/predictions/historical_hygiene.py) to backfill `asset_class`, repair obvious resolved-price/PnL damage, and flag invalid execution rows.
- Re-ran predictor backfill/export so [leaderboard.json](/e:/findtorontoevents_antigravity.ca/predictions/data/leaderboard.json) reflects valid-vs-invalid row separation.

Post-cleanup state:

- all 367 prediction rows now have `asset_class = crypto`
- 37 rows are flagged `is_invalid_execution = 1`
- no rows remain below `-100%` PnL
- predictor stats now track `valid_predictions` and `invalid_predictions`

This does not fully solve social prediction quality, but it removes the worst analytical corruption and makes leaderboard stats materially more trustworthy.
