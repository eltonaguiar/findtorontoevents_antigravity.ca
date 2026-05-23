# Archive Dedup Audit (2026-04-22)

## Summary

Audited `alpha_engine/data/closed_picks.archive.jsonl` for duplicate pick IDs
that accumulated before the dedup guard was added in `save_closed_picks()`
(PR #313).

## Before Cleanup

| Metric | Value |
|--------|-------|
| Total lines | 44,011 |
| Parseable JSON lines | 44,010 |
| Malformed lines | 1 |
| Picks with `id` field | 44,009 |
| Unique pick IDs | 5,610 |
| **Duplicate entries** | **38,399** |
| **Dedup ratio** | **87.2%** |

### Duplication Pattern

The duplication was **scattered** (not sequential blocks), consistent with
the root cause: every validator cycle re-archived picks already in the
archive when the process restarted or the hot file was re-read after a
crash between archive-write and hot-file-trim.

Distribution of copies per ID:

| Copies | IDs |
|--------|-----|
| 1 | 727 |
| 2 | 1,261 |
| 3 | 1,641 |
| 4 | 1,358 |
| 5–8 | 574 |
| 9+ | 49 |

Some IDs appeared up to 8+ times. The scattered pattern (not contiguous
blocks) confirms re-archiving happened across multiple independent
validator cycles rather than a single bulk re-write.

## Root Cause

`save_closed_picks()` in `alpha_engine/forward_validator.py` had no
deduplication guard before PR #313. When the process crashed between
writing a pick to the archive JSONL and trimming the hot file, the next
validator cycle would re-archive the same picks (still in the hot file)
alongside their existing entries in the archive.

## Fix (PR #313)

Added a dedup guard in `save_closed_picks()` that:

1. Reads the last `ARCHIVE_DEDUP_TAIL_LINES` (1,000) lines of the archive
   using `deque(_rf, maxlen=ARCHIVE_DEDUP_TAIL_LINES)` for bounded parsing.
2. Builds a set of already-archived pick IDs.
3. Skips any pick whose `id` is already in the archive set.
4. Wrapped in `try/except` so a malformed or missing archive does not
   block the validator.

## Cleanup

Ran `tools/dedup_archive.py` to remove accumulated duplicates:

| Metric | Before | After |
|--------|--------|-------|
| Total lines | 44,011 | 5,612 |
| Unique pick IDs | 5,610 | 5,610 |
| Duplicates | 38,399 | 0 |
| Malformed lines | 1 | 0 |

All 5,610 unique pick IDs preserved. 38,399 redundant entries removed.
1 malformed JSON line dropped.

## Impact of Duplicates on Metrics

Before cleanup, the 38,399 duplicate entries would have inflated:

- **Historical trade counts** — each duplicate counted as an additional trade
- **Win rate (WR)** — duplicated winners counted multiple times
- **Profit factor (PF)** — PnL from duplicated entries skewed the ratio
- **Strategy performance summaries** — any aggregate stats computed from
  the archive were distorted

The cleanup restores accurate historical metrics. Any dashboard or report
that previously consumed the archive should now reflect true pick counts.

## Tool

`tools/dedup_archive.py` — one-time cleanup script (also useful if
dedup guard is ever bypassed). Supports `--dry-run` for safe preview.
