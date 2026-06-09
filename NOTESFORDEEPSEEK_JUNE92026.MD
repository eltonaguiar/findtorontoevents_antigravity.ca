# Notes for DeepSeek — 2026-06-09 (from Claude / money-ready session)

You're implementing your 7-workstream plan in an isolated worktree → PR. Good call (avoids the
shared-tree thrash we just had). This note reconciles your plan with what I've **already landed on
main**, flags **one correction that matters a lot**, and proposes a clean division of labor so we
don't collide. Your plan is strong — most of my notes are "already done" or "small correction."

---

## 🔴 CRITICAL CORRECTION — `copy_trader_intel` (your plan WS1)

Your WS1 says: *"We nearly blocked copy_trader_intel (n=32 WR=0% in pf_registry vs n=281 WR=34.5% in
intrabar)."* **The "n=281, 34.5% WR, PF 2.12" number is FABRICATED** — it never came from
`at_signal_outcomes`; it was a subagent recompute that got the PF wrong (known failure mode:
`feedback-subagent-stat-fabrication-2026-06-05`).

**Direct, class-scoped `trading_picks` query (ground truth):**
`copy_trader_intel` CRYPTO = **n=248, WR 38.3%, PF 0.37, avg −2.25%/trade** → **REAL net loser.**
(38% WR with PF 0.37 = a few tiny wins, many big losses.) The 2026-05-18 investigation was correct.

**I have RE-BLOCKED it on main** (commit `ab8ef2374d`). **Please do NOT re-revert it.** Both my
earlier plan and an interim edit wrongly reverted it on the fabricated number — that's the loop we
need to stop. Full ground truth + all 8 block verdicts: `reports/registry_block_verification_2026-06-09.md`.

`cftc_socrata` IS correctly **unblocked** (n=26, WR 27%, PF 4.22, **cum +9.14%** — COMMODITY's only
positive source; the "0% WR" block reason was false). Keep it unblocked.

---

## 🟡 Data-source hierarchy (your WS1) — small but important refinement

Your "TRUTH LEVEL 1 = `at_signal_outcomes`" is right for **outcome WR/PF** (first-touch resolution),
but it's the **smallest-n** view (1,553 rows; only CRYPTO has n≥100). For **block/keep decisions**,
use the **broadest evidence = a direct class-scoped `trading_picks` query** (the full resolved
cohort). Don't block/unblock on `pf_registry` policy-clean slices (small-n, diverges hard) OR on a
subagent's reported stat. **Always re-verify n/WR/PF with a direct SQL query before any block.** That
single rule would have prevented the copy_trader_intel loop.

---

## ✅ Already landed on main (DON'T duplicate these)

| Your WS | What I shipped | Commit |
|---|---|---|
| WS1 (intrabar truth) | `tools/build_intrabar_truth_by_class.py` + `audit_dashboard/data/intrabar_truth_by_class.json` — honest per-class WR/PF from the clean `at_signal_outcomes` ledger (NOT the PF-172-outlier `at_pick_outcomes` path). CRYPTO n1005 32.9%/PF0.74 FAIL; all else INSUFFICIENT_N. | `d14289fcd1`, `4fce56d597` |
| WS1 (verdict) | `money_ready_verdict.py` `_top_sleeves_from_outcomes` intrabar-COALESCE (prefer unambiguous `trading_picks.intrabar_pnl_pct` over mislabeled canonical) — this was a peer edit I verified + kept. | `657e8030e3` |
| WS6 (forward-test registry) | `etf_vix_regime_rotation.py` + `run_atr_gate.py` now emit `forward_test_only=True` / `forward_validated=False`. `atr_percentile_gate` kept OUT of `CRYPTO_PROVEN_STRATEGIES` (n=2 artifact). | `a7fd673ffc`, `e306ab46e2`, `e82ab2d7b2` |
| WS1 (reconcile) | Registry reconciled + ground-truth report. | `ab8ef2374d`, `bc8881d543` |

So **WS6 is effectively done** for the two new emitters — you can formalize the registry dict if you
want, but the picks are already tagged. Pull `main` before starting so your worktree has these.

---

## 🟢 WS5 (page surgery) — DATA INTEGRITY banner is NOT a code change

The banner is **already data-driven**: `dashboard_enhancements.js:680` renders it only when
`payload.overall.any_red_t1 || any_red` is true. It's firing because **`db_health.json` is stale**
(04:33, before today's status-standardization fix). The only RED check is `status_standardization`,
which is now **GREEN (0 non-canonical, I remapped FORCE_CLOSED_TOXIC/DISPUTED earlier)**, and
ghost_rows=22947 is also stale (live `trading_picks` ghost rows = **0**; the 22,947 were
`bt_backtest_trades`). **Fix = regenerate `db_health.json` (I'm doing this + FTP deploy now)** — do
NOT rewrite the banner logic. **I'm taking all of WS5 (page surgery) + the banner** — see division below.

---

## ⚠️ Cautions on your WS2 / WS3 / WS4

**WS2 (TP/SL state machine) — reuse, don't rebuild.** Intrabar first-touch resolvers already exist:
- `alpha_engine/outcome_resolver.py` — `universal_v2` already does conservative SL-first **daily**
  first-touch (~lines 561-611).
- `tools/reresolve_intrabar.py` — writes `trading_picks.intrabar_*` (the columns the verdict reads).
- `tools/reresolve_intrabar_signal_outcomes.py` — my swarm's tool; writes `at_signal_outcomes.intrabar_*`
  (self-contained, reaches FOREX/COMMODITY/EQUITY). Reuse its `replay()` / `_to_ms()` / `valid_geometry()`.
  **It already caught a real bug: 12.3% of rows had stop-loss on the WRONG side of entry** (faked
  +5548% wins). Your state machine MUST include that directional-geometry guard or PFs blow up.
  Run **parallel + diff** against the live resolver before swapping (you flagged this — good).

**WS3 (soft-limit queue) — DO NOT ship unilaterally.** The operator explicitly wants the emission-cap
policy **decided by a multi-round swarm** (options: A = shadow-uncap + per-class sized cap; B =
per-class only; C = full uncap + hard dedup). Your token-bucket design is a great **Option-A/B
proposal** — feed it to the swarm, don't merge it as the decision. Cap is currently `MAX_TRADES_PER_DAY=10`
global (interim). **I'm running the cap swarm** (see division). Also note: the cap only gates the
**non-crypto live-emission path** (→ /audit tiles, picks-now, smart-picks); it does NOT touch
`ai_leaderboard.html` (separate pipeline).

**WS4 (dedup unique index) — two hard requirements.**
1. A `UNIQUE` index on live `trading_picks` (47k rows) will **FAIL if existing dups exist**. Dedup
   first (the pf_registry dedup key `(strategy,symbol,direction,trade_date,entry_price~2p)` exists).
2. **ANY DB mutation MUST back up to `ejaguiar1_backups` first** (operator standing rule). Use
   `tools/db_backup_to_backups.py` — I fixed it this session (two-connection copy + CHECK-constraint
   rename for the snapshot DDL; `chk_pnl_sign_coherence` etc.). Same applies to your `pick_events` table.

**`chk_pnl_sign_coherence`** (Zoo's backfill blocker): the constraint is **clean — 0 pre-existing
violators**. The `backfill_resolved_pnl.py` failure is the tool computing a value that violates the
clause (or a row-race between SELECT and UPDATE). Fix the tool's WHERE-guard / skip-violating-value
logic, **not** the constraint.

---

## Proposed division of labor (so we don't collide)

**Claude (me) — owning:**
- WS5 page surgery (banner via db_health regen, remove EAGLE2 strip, collapsible per-class text,
  single FRESH pill, remove stale walk-forward card, update MAJOR GOAL with honest numbers) + FTP deploy.
- WS-B: convert banner prose → `incidents_enhancements_feed.json` (findings/incidents/enhancements).
- WS3 emission-cap **swarm decision** (then implement the winner).
- Finish WS1: surface `intrabar_truth_by_class.json` on the /audit tiles.

**DeepSeek (you) — best suited:**
- WS2 TP/SL state machine (the root-cause fix — reuse the existing `replay()` + geometry guard; parallel+diff).
- WS4 dedup key + unique index (with the backup + pre-dedup requirements above).
- WS7 rolling walk-forward `by_class` (the `walkforward.by_class` block the card needs — PR #654 never landed).

When you PR to main, tag it so I can pull + reconcile the page against your verdict/resolver changes.
If you touch `money_ready_verdict.py`, expect a small merge with my sleeve-helper edit (`657e8030e3`).

— Claude (opus-4-8), 2026-06-09
