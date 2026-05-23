# Open Items Gameplan — CX2 Post-Session (2026-05-19)

You are a senior quantitative researcher at a hedge fund. Below are the confirmed open items from session CX2 (2026-05-19). For each item, provide: (1) recommended action, (2) sequencing/priority, (3) any risks or prerequisites, (4) acceptance criteria (how we know it's done).

Be direct. This is for real capital deployment. No hand-waving.

---

## System Context

- Repo: findtorontoevents_antigravity.ca (multi-agent quant trading system)
- Asset classes: EQUITY, CRYPTO, COMMODITY, ETF, FOREX, BOND, FUTURES
- Quality gate: PF≥1.5, WR≥50%, MDD≤20% for live capital (Tier 2 minimum)
- Hypothesis registry: `reports/hypothesis_registry.json` — all hypotheses pre-registered (M-107 gate)
- Statistical validation: `alpha_engine/validation/statistical_gates.py` — correct DSR (Bailey & LdP 2014), Newey-West t-stat
- Database: MySQL on mysql.50webs.com, DB=ejaguiar1_stocks, table=trading_picks (73,555 rows; 32,195 duplicates confirmed by dry-run)
- IP restriction: RESOLVED — desktop can now connect (password confirmed working)

---

## Open Item 1: MySQL Dedup — Apply Now

**Status:** Dry-run confirmed. 32,195 duplicate rows across 6,086 groups. 984 confidence rows > 1.0 (need /10 fix).
**Script:** `tools/mysql_dedup_fix.py --apply`
**Risk:** Deletes 32,195 rows from production DB. Irreversible without backup.
**Question:** Should we take a backup first? Or is the dry-run confidence sufficient to apply directly? What's the right sequencing?

---

## Open Item 2: EQUITY n≥100 — Extend Backtest Window to 3Y

**Status:** Current: n=69 resolved EQUITY picks (from 1Y window). NW t-stat FAIL (p=0.563). DSR PASS.
**Ring-2.6-1T recommendation:** Extend to 3Y window → expected ~207 picks at similar pick rate.
**Script:** `alpha_engine/validation/run_equity_edge_test.py` (reads from `closed_picks.json` or MySQL)
**Question:** Does extending the lookback window for a validation test introduce survivor bias? What's the right methodology — extend the closed_picks query window, or run a proper point-in-time backtest on historical price data?

---

## Open Item 3: H-021 COT Small-Spec Re-run (~2026-05-26)

**Status:** 2/3 walk-forward windows pass eff≥1.2 on the COT small-speculator positioning signal. Window 3 (most recent) not yet populated. Re-run scheduled for 2026-05-26.
**Hypothesis:** H-021 in `reports/hypothesis_registry.json`
**Question:** Is waiting for window 3 the right call? Or should we run a conservative partial-pass test (2/3 windows = 67% pass rate) and register it as NEAR_ADMISSIBLE with a 30-day monitoring period?

---

## Open Item 4: H-027 DBA/DBB Parsers — Commodity Proxies

**Status:** H-027 (CO-1 commodity inventory surprise) — 4/6 proxies use real EIA data. Two remaining:
- DBA (agriculture ETF proxy): USDA FAS PSD API returned empty response
- DBB (base metals ETF proxy): LME warehouse data parser not wired (using synthetic data)
**Question:** Is DBA/DBB inventory data actually necessary for H-027 to have edge, or can the 4/6 real-data proxies form the basis of a valid partial test? What's the minimum viable data set for H-027 admission?

---

## Open Item 5: Ban Protocol Rec 5 — Overdue Symbol Reviews

**Status:** TRXUSDT, CVX, XOM all 11 days past review_date (2026-05-08 review date, not 2026-05-30 as previously logged).
**Current stage:**
- TRXUSDT: PENDING_UNBLOCK_REVIEW (SHADOW stage)
- CVX: Both EQUITY_BLOCKED_SYMBOLS AND PROBATION_STATUS (inconsistency)
- XOM: PENDING_UNBLOCK_REVIEW (SHADOW stage)
**Criteria to promote to PROBATION:** n≥20, WR≥52%, PF≥1.3 on closed picks
**Question:** For a symbol review, do we need a full backtest or just query current closed_picks.json stats? What's the correct audit procedure to be defensible?

---

## Open Item 6: Ban Protocol Infrastructure (Rec 1-3)

**Rec 1 (HIGH):** Create `audit_trail/blocked_registry.json` — unified schema with review_date, stage, unblock_criteria per blocked entity.
**Rec 2 (HIGH):** Create `tools/blocked_symbol_review_monitor.py` — daily scan for overdue reviews, write to `audit_trail/alerts/overdue_unblock_reviews.json`.
**Rec 3 (MEDIUM):** Fix UNBLOCK_THRESHOLDS logic bug: FULL unblock currently requires PF≥1.2, but PROBATION requires PF≥1.3 (backwards). Fix: FULL → PF≥1.5.

**Question:** Should Rec 1 (registry JSON) be built before Rec 5 (overdue reviews) or after? Is there a risk that migrating from hardcoded dict to JSON introduces inconsistencies? What's the right order?

---

## Questions for You

1. What is the correct sequencing of these 6 items by risk-adjusted priority?
2. For Item 1 (MySQL dedup): backup first or apply directly? What's the backup procedure for a hosted MySQL at 50webs?
3. For Item 2 (EQUITY 3Y): what's the right methodology — extend closed_picks query, or point-in-time backtest?
4. For Item 3 (H-021): wait for window 3, or admit as NEAR_ADMISSIBLE at 2/3?
5. For Items 5+6 (ban protocol): should overdue reviews use closed_picks stats or require full backtest?

Please respond with a structured gameplan: ordered task list with risk flags and acceptance criteria per item. Be specific — this will be executed autonomously.
