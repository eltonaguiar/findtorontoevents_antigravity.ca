# Zoo's Reverse-Split Scope Gap Closure — 2026-06-04

## Zoo's read-only discovery (trading_picks pipeline)
- LODE: 0 rows
- FFIE: 0 rows
- WKHS: 2 rows (1 at_raw_picks + 1 at_signal_outcomes)

**Verdict**: trading_picks (production live-pick pipeline) has near-zero exposure to the reverse_split_symbols registry. 2 WKHS rows is below ceremony threshold.

## Scope gap: `tournament_picks` not scanned (the table where LODE +1373% lived)

Scan results on `tournament_picks`:

| Symbol | OPEN | Closed | Entry-price range | Action |
|---|---:|---:|---|---|
| LODE | 33 | 1 WIN @ $3.52 (legit) | $0.12 - $3.52 | 32 pre-split → flagged MISPRICED |
| FFIE | 39 | 0 | $0.045 - $7.60 | 31 sub-$1 → flagged MISPRICED |
| WKHS | 0 | 0 | — | clean |

Current LODE market: $4.45. Anything below ~$3.20 is post-split impossible.
FFIE yfinance reports delisted; sub-$1 entries are clearly stale-quote artifacts.

**63 pre-split OPEN picks** would have resolved into inflated wins when the price-tracker hit them with current market prices — same as the original LODE +1373% pattern.

Cumulative MISPRICED tally: **3,902** across all 5 audit rounds + this scope-gap closure.

## Why hand-curated registry is the wrong approach

The `audit_trail/reverse_split_symbols.py` registry has 3 symbols. Real reverse-split exposure in tournament_picks is well beyond this — NFLX did a 10:1 forward split, GE did 1:8 reverse, FFIE has had multiple reverse splits, etc.

The drift-based detection already shipped (`tools/ai_tournament/price_tracker.py` per-class thresholds, commit `956498ca59`) auto-catches reverse splits + futures rolls + stale-AI-quotes without enumerating symbols. The 868 Round-5 catches and these 63 LODE/FFIE catches all use the same mechanic.

**Recommend deprecating the registry approach** in favor of:
1. Universal drift-based detection at resolution time (already shipped).
2. Drift-based detection at INGEST time for `at_raw_picks` (still TODO — peer agent could add this).
3. Periodic per-class threshold tuning based on the residual artifact rate.

## For zoo's session log

- The full gated sequence (backup → flag → MD doc) was overkill for 2 WKHS rows. Auto-approve threshold for surgical fixes should be n<10 with a 1-line audit log entry.
- The bash heredoc issue (`{tbl}` interpolated by outer shell) is a real footgun — always use `python3 <<'PYEOF' ... PYEOF` for multi-line python with f-strings inside backticks. Worth a shared coding-style note.
