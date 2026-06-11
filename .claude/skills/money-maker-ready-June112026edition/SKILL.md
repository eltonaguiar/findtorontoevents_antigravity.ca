---
name: money-maker-ready-June112026edition
description: The June-2026 EDITION of the money-ready program — executes the self-correcting MASTER LOOP (docs/MONEY_READY_MASTER_LOOP_2026-06.md) that converges toward 2-3 profitable asset classes even from 0/9. Use when the user says "/money-maker-ready-June112026edition", "run the master loop", "weekly money-ready cycle", or at the monthly edition review. Inherits data sources + hard rules from /money-maker-ready and /money-maker-readyv2. Aliases - mmr-june2026, master-loop, money-loop.
---

# /money-maker-ready-June112026edition — the Master Loop (June 2026 edition)

**Canonical plan:** `docs/MONEY_READY_MASTER_LOOP_2026-06.md` — READ IT FIRST; this skill is the executor.
**Edition discipline:** this is a DATED edition. On the 11th of each month, run the edition review (Section E below) and either re-stamp or supersede with a new edition skill. Editions never silently mutate — improvements are visible diffs.

## What this skill does (one weekly cycle)

1. **MEASURE** — refresh the honest ledger + coverage metrics; run the H1 structural audit:
   ```bash
   python3 tools/build_intrabar_truth_by_class.py --stdout       # per-class honest n/WR/PF
   python3 tools/stamp_entry_conditions.py --stdout              # forward lane state
   python3 tools/check_one_sided_resolution.py                   # coverage pathology
   # coverage: resolved/emitted ratio, terminal NULL-pnl count, dup-rate (SQL patterns in the master MD §3)
   # H1 stratified spot-replay: 10 random recent resolutions per focus class vs independent bars
   ```
2. **DIAGNOSE** — score H1-H5 per focus class (table in master MD §3). H1 red = halt everything else.
3. **ACT (parallel)** — for each focus class (currently CRYPTO + COMMODITY), run the top remedy:
   - Replay-variant batches via the proven harness (mirror `reports/strategy_bt_crypto_2026-06-11.json` methodology: entry-anchored first-touch, SL-wins-ties, pre-entry features only, per-symbol-day dedup, net of costs). **Pre-register the batch (hypothesis + falsification) BEFORE running; the batch is ONE FDR family; family closes after its registered comparisons.**
   - Plumbing/data fixes ship same-day with tests (the #129 discipline).
4. **FORWARD** — check the pre-registered checkpoint calendar (master MD §7); promote/kill ONLY at the bars (95% CI lower bound of net PF > 1.15 at n≥80 forward + time-split + concentration<35%).
5. **RATCHET** — commit the weekly scorecard to `reports/weekly_loop_scorecard_<date>.md`; file/resolve incidents via `tools/audit_pick_funnel/cli_track.py`; update the live pages.

## Data + credentials (for ANY agent, including brand-new ones)
- Read the orientation in master MD §0. DBs via `tools/db_env.py` ONLY; local agents get passwords from `/home/eaguiar2015/dbpasses.txt` (gitignored — NEVER commit/echo); remote agents ask the operator.
- **Backup to `ejaguiar1_backups` before ANY table mutation** (`tools/db_backup_to_backups.py`; ≤64-char table names; FK tables need CREATE-AS-SELECT copy).
- All source-of-truth pointers, tier definitions, mandatory data-integrity filters, and the reject-without-reverify list: inherit from `/money-maker-ready` + `/money-maker-readyv2` (do not duplicate here).

## Hard rules (non-negotiable, inherited + edition-specific)
- Every claim: `(asset_class | n | timeframe)`. Direct-SQL re-verify any number a subagent/peer/LLM produces.
- Pre-register before backtest (M-107). Tuning families close after their registered comparisons — no variant-fishing.
- Mutate-before-kill for strategies; do-not-relitigate list is binding (master MD §8).
- Promotion is FORWARD-lane only. Replay results select candidates; they never size anything.
- One focus-class slot rotates out after 3 consecutive null weekly cycles.

## E. Monthly edition review (run on the 11th)
1. Score the month: per focus class — did the CI lower bound improve? checkpoints hit/missed? incidents P0 aging?
2. What circled (3-null rotations, refuted batches) — add to do-not-relitigate.
3. What the next edition changes (one structural change max — editions evolve, not churn).
4. Write `reports/edition_review_<YYYY-MM>.md`, supersede or re-stamp the skill, update the master MD header.
5. Hand the operator the external-review task spec (master MD §9) if the edition made structural changes.

## Failure-hypothesis quick reference (full table: master MD §3)
H1 measurement → halt + fix · H2 backtest-only → shadow + close family · H3 data scarcity → free APIs (FRED/CFTC/EDGAR) + shadow-lane universe widening · H4 external signals → per-source scorecards keep/kill · H5 coverage → extend resolution before judging.

## Current state snapshot (2026-06-11 — RE-VERIFY, never trust this block after ~1 week)
0/9 classes pass. Focus: CRYPTO + COMMODITY. Live candidates: handoff-LONG (Jul-9 OOS gate), rsi5070×US (n≥150 gate ~Jun-25), COMMODITY n=100 verdict (~days), pead gate Jun-14. Honest chain self-sustains hourly. Walk-forward stale (#132 P1, blocks H2 scoring — fix early).
