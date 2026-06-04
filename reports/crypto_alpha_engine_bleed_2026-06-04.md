# CRYPTO alpha_engine bleed 2026-06-04

## Pattern (at_signal_outcomes, asset_class=crypto, decisive only)

| Window | n | WR | w/l ratio |
|---|---:|---:|---:|
| 30d+ baseline | 100,793 | 37.4% | 0.60 |
| 30d total | 9,313 | 25.5% | 0.34 |
| 14d total | 3,399 | 18.6% | 0.23 |
| 7d total | 6,848 | 37.2% | 0.59 |
| **48h** | **92** | **41.3%** | **0.70** |

## Source attribution

7-30d bleed window:
- `alpha_engine`: **12,617 picks @ 23.5% WR** — the entire drag
- `mercury2`: 95 picks @ 41.1% WR (small-n, neutral)

48h recovery (alpha_engine only):
- 92 picks @ 41.3% WR — sample-size limited but trend reversed

## Interpretation

alpha_engine had ~3 weeks of CRYPTO 23.5% WR (May 5 - May 21 roughly), which dragged the rolling /audit money-ready verdict to CRYPTO NOT_READY (38.2% WR / PF 0.97). The last 48h shows a recovery but on too-small n (92) to be statistically confident.

The bleed coincides with crypto market regime change in May — possible that alpha_engine signals are momentum-following and got chopped in a sideways/down regime, then signals improved as the regime stabilized.

## Action

- Do NOT size up CRYPTO based on the 41.3% 48h figure (n too small).
- Monitor 7d window: if it stays >40% over the next week, may indicate genuine regime adaptation.
- If 7d drops back below 35%, suggests bleed wasn't regime-driven and alpha_engine CRYPTO logic needs review.

Generated 2026-06-04 by claude during /loop session.

## CRITICAL — duplicate-row inflation in at_signal_outcomes (added 08:50 UTC)

Sample query revealed `at_signal_outcomes` has massive row-duplication for alpha_engine picks. Dedup by `(symbol, opened_at|closed_at, strategy, entry_price)`:

| Class | raw_n | unique_n | dup_ratio |
|---|---:|---:|---:|
| CRYPTO | 12,617 | 291 | **43.36x** |
| EQUITY | 567 | 36 | 15.75x |
| FOREX | 100 | 12 | 8.33x |
| MEMECOIN | 68 | 9 | 7.56x |

### Implications
- The bleed-window CRYPTO "12,617 picks" is really **~291 unique picks** at 23.5% WR — still confirms a real bleed but on much smaller n than appeared.
- Dashboard `money_ready_verdict` n_resolved figures already dedup (ETF n=8 / 100% WR / INSUFFICIENT_DATA), so user-facing surfaces are protected.
- Raw `at_signal_outcomes` rows are NOT safe for ad-hoc analysis without dedup.

### Same pattern as the LODE/AI-tournament cleanup
This is the third manifestation of the duplicate-pick leakage signal:
1. AI tournament (now cleaned): mispriced entries — 2,987 fixed
2. CLAUDE.md note (May): "1864 duplicate signal-ts groups" in pick_funnel CRYPTO Smart Picks
3. **Today (alpha_engine `at_signal_outcomes`)**: 7-43x duplication across all live asset classes

### Action
- Open INCIDENT_OVERALL P0: alpha_engine bot writes same row 8-43x to `at_signal_outcomes`. Need either UNIQUE constraint on `(symbol,opened_at,strategy,direction)` or fix the bot's write logic.
- Until fixed, every analytic against `at_signal_outcomes` must dedup or it will inflate `n` and mask real edge.

## Apparent ETF/FOREX 100%/94% WR was duplication artifact

Earlier extreme reads (alpha_engine ETF 100% / n=142 @ 48h; FOREX 94% / n=100 @ bleed-window) are **NOT real edges** — they collapsed to ~15-25 unique picks after dedup. The raw row counts were duplicated wins of the same SPY/QQQ/USDCAD pick.

## Root cause confirmed — INCIDENT_OVERALL.id=91

- `at_signal_outcomes` has UNIQUE INDEX `idx_dedup` on `(symbol, direction, source_system, opened_at)`.
- **98.2% of alpha_engine rows write `opened_at=NULL`** (40,016 of 40,743). MySQL treats NULL as distinct from itself, so the unique constraint never fires.
- Top duplicate group (last 24h): **PLTR regime_accumulation @ entry=156.54 closed 2026-06-03 14:05:08 = 11 duplicate rows.**

### Writers identified (need fix)
- `audit_trail/backfill_local_sources.py:194` (INSERT IGNORE INTO at_signal_outcomes — IGNORE doesn't help when unique-index can't match due to NULL)
- `audit_trail/backfill_local_sources.py:295,380` (also insert closed picks)
- `tools/repair_data_integrity.py:278`

### Recommended fix (operator approval needed before DDL)
Add a SECOND unique index that dedupes at close-time regardless of opened_at:
```sql
CREATE UNIQUE INDEX idx_dedup_close
  ON at_signal_outcomes (symbol, strategy, entry_price, closed_at, source_system);
```
This is additive (no writer changes), catches the actual duplicate pattern (same close-time = same fill), and won't break existing flows because the current 8-43x duplicates would all collapse to 1 row apiece via the writer's `INSERT IGNORE`.

**DO NOT RUN this DDL without operator approval** — it will fail mid-creation if duplicates already exist (which they do). Sequence: dedup existing dups → add index → done. That's a maintenance window operation.
