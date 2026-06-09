# PLAN — DB Health Discrepancy: "DATA INTEGRITY FAILURE" vs "cleared 2026-05-31"

**Author:** Freebuff (Codebuff) · **Date:** 2026-06-08
**Status:** DRAFT — pending multi-AI cross-review (Grok + MiniMax + NVIDIA NIM)
**Target branch (worktree):** `fix/db-ghost-rows-and-freshness`

---

## 1. The contradiction (verbatim from /audit DB Health panel, 2026-06-08 22:07 EDT)

| Check | Value | Status |
|---|---|---|
| PnL Integrity (sampled) | 99.5% — 130 / 24,158 mismatch >1pp | greenish (under 1% drift) |
| Ghost Rows (constant pnl_pct) | **22,947** — 10 cohorts (n>1000, distinct_entries<5) | 🔴 RED |
| Forward Validator Freshness | **84h** — 2026-06-05 13:24:13 last WON/LOST | 🔴 RED |
| WON-vs-PnL contradiction | no — avg pnl per status OK | ✅ green |

The panel itself renders "⚠ DATA INTEGRITY FAILURE — DO NOT TRADE ON THESE NUMBERS".

The remediation footer on the same panel claims:
> "tools/cleanup_ghost_rows.py shipped (2026-05-31: 0 ghost rows confirmed). Ghost rows, status mismatch, non-canonical statuses, and _bak tables all cleared as of 2026-05-31 DB audit."

These two statements are mutually exclusive. One of the following must be true:

**H1 — The fix didn't hold.** Ghost rows re-accumulated between 2026-05-31 and 2026-06-08 (~8 days). Most likely mechanism: a system that re-emits / re-resolves picks writes the same constant `pnl_pct` for many rows. Examples: tick-based re-emission, duplicate resolution runs, or a re-snapshotted backfill.

**H2 — The metric is mis-counted.** The `db_health_check.py` "ghost cohort" heuristic (`n>1000 AND distinct_entries<5`) is too broad — it captures legitimate low-resolution cohorts (e.g. all the FOREX EXPIRED picks where the resolver returns the same pnl_pct=0 every time and the cohort genuinely has only a few distinct pnl values). The 22,947 figure is then noise, not a real bug.

**H3 — The remediation status is stale.** The "cleared 2026-05-31" line is hard-coded / cached and is no longer being updated by the audit pipeline, so it greenwashes an actually-broken state.

**H4 — Reading a _bak table.** The health check accidentally queries `at_pick_outcomes_bak` or similar; the live table is clean.

**H5 — forward_validator.py is the actual root cause, not the ghosts.** 84h since last WON/LOST means the resolver hasn't run in 3.5 days. While it's silent, every downstream panel (incl. WR/PF by class) is computing against an open-pick-bloated dataset, which inflates the denominator and can synthesize the "ghost cohort" pattern (an OPEN cohort with n growing but pnl_pct unchanged looks like a ghost).

**Prior:** My own read of `alpha_engine/data/closed_picks.json` earlier today showed `BOND n=2, FOREX n=157 (11.5% WR)`, `COMMODITY n=128 (21.1% WR)`, `CRYPTO n=74 (47.3% WR)`, `EQUITY n=49 (63.3% WR)`. The CRYPTO and FOREX cohorts in particular are exactly the shape that H2 / H5 would predict — many rows, few distinct PnL values, because most FX/Crypto picks EXPIRE rather than hit TP/SL.

## 2. Investigation plan (Phase 1, no code change)

1. Read `tools/db_health_check.py` end-to-end. Capture the exact SQL it runs for:
   - "PnL Integrity (sampled)"
   - "Ghost Rows (constant pnl_pct)" — the cohort filter `n>1000 AND distinct_entries<5`
   - "Forward Validator Freshness" — which timestamp column it reads
   - "WON-vs-PnL contradiction"
2. Read `tools/cleanup_ghost_rows.py` to learn what "ghost" means to the cleanup script (it may differ from the health-check definition; that gap would explain the contradiction by itself).
3. Read `audit_trail/forward_validator.py` (or wherever it lives) to see why it hasn't emitted in 84h.
4. **Query MySQL directly** (creds in `dbpasses.txt`, host `mysql.50webs.com`, db `ejaguiar1_stocks`):
   - `SELECT COUNT(*), COUNT(DISTINCT pnl_pct) FROM at_pick_outcomes;` — totals
   - `SELECT status, COUNT(*) FROM at_pick_outcomes GROUP BY status;` — status distribution
   - Top 10 cohorts with `n>1000` ordered by `distinct_pnl_pct` ascending
   - `SELECT MAX(resolved_at), MAX(timestamp) FROM at_pick_outcomes WHERE status IN ('WON','LOST');` — true freshness
   - `SHOW TABLES LIKE '%bak%'; SHOW TABLES LIKE 'at_pick_outcomes%';` — find _bak tables
5. Compare the 22,947 number to the SQL. Is the count real, is the cohort filter too loose, or is it reading a _bak table?

## 3. Proposed fix (Phase 2, on worktree)

Working branch: `fix/db-ghost-rows-and-freshness` (off main, per AGENTS.md "Only Push Your Own Changes").

### 3a. Tighten ghost-row definition in `db_health_check.py`
- Change the cohort filter from `n>1000 AND distinct_entries<5` to a stricter signal: `n>1000 AND COUNT(DISTINCT ABS(pnl_pct) > 0.01) < 5 AND same status='WON'`. A genuine ghost is "1000+ rows all WON with pnl_pct = exactly the same number like 1.234", not "1000+ FOREX EXPIRED rows that all show pnl_pct=0".
- Add the cohort's `status` distribution to the report so a reviewer can see at a glance whether the cohort is dominated by EXPIRED (noise) or WON (real ghost).

### 3b. Fix the forward-validator freshness regression
- Identify why `forward_validator.py` has not emitted in 84h. Likely causes: cron schedule, GHA workflow file, a stuck lock, or a missing dependency.
- Add a 24h staleness CI gate (`.github/workflows/db-freshness-guardian.yml` already exists per AGENTS.md) that **fails the build** instead of just warning.
- Add a watchdog: if `MAX(resolved_at)` is older than `now - 26h`, open an issue via `gh issue create --label data-staleness`.

### 3c. Make the remediation status honest
- Replace the hard-coded "cleared 2026-05-31" line with a live read: `db_health_check.json["last_cleanup_ghost_rows_at"]` and `db_health_check.json["last_cleanup_ghost_rows_remaining"]`.
- If those keys are missing/old, the panel should display the staleness instead of greenwashing.

### 3d. Add a per-asset-class freshness drilldown
- Today the panel shows one number. Add a small table: `asset_class | n_closed | last_resolved_at | freshness_hours`. That way a reader can see at a glance whether the staleness is uniform or concentrated in one class (e.g. CRYPTO, where most picks EXPIRE and the resolver may have a different cadence).

## 4. Verification plan

- Run the modified `db_health_check.py` against the live DB. Confirm:
  - The tightened ghost-row definition drops the 22,947 count to a sane number (target: < 500, ideally < 100).
  - The 84h freshness finding is preserved.
  - The remediation footer now reads from a live key, not hard-coded text.
- Open PR with: (a) the code diff, (b) before/after DB health panel screenshot, (c) one `updates/2026-06-08-db-ghost-rows-and-freshness.md` describing the root cause, the fix, and the verification.
- Per AGENTS.md safety: do NOT push the branch; ask the user to merge.

## 5. Out of scope (deferred to a follow-up PR)

- The broader "ZERO classes are money-ready" finding (per `audit_reports/ASSET_CLASS_EDGE_AUDIT_2026-05-25.md`). That requires n≥100 clean data per class, which the freshness fix unlocks but doesn't itself produce.
- The picks-now regeneration. That's a separate code path and is already on disk in `tools/picks_now_professional.py`; a future PR can wire a hardened retry.

## 6. Open questions for cross-review (the AI team)

1. Is the proposed tighter ghost-row definition (`n>1000 AND COUNT(DISTINCT ABS(pnl_pct) > 0.01) < 5 AND same status='WON'`) too aggressive? Should it allow a few distinct values to absorb legitimate signal?
2. Is the 26h watchdog threshold right? It must be larger than the worst legitimate forward-validator run gap, smaller than 84h.
3. Should the "no WON-vs-PnL contradiction" check be expanded to "no OPEN-vs-zero-PnL" — i.e. flag OPEN picks whose pnl_pct is exactly 0 because they haven't been resolved?
4. Is there a known data-quality incident (similar to H-101 / M-095 for the COT leakage) that explains why ghost rows keep re-appearing? If so, that incident needs a registered fix in `tools/hypothesis_registry.json` per M-107.
