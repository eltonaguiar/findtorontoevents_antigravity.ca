# CRYPTO — quick wins + proposed fix (deepAI, 2026-11-14)

Worktree base f54efb3b4a (re-verify anchors on rebase). Evidence: `evidence_live_audit.json`,
`cross_check_and_merge.md`, peer `reports/zero_pnl_data_pipeline_audit_2026-06-05.md`,
`reports/wr_scrutiny_honest_2026-06-05.md`, `reports/2026-06-05-PER-CLASS-T2-INVENTORY-POST-FILTER.md`.

## Quick win 1 — PASS (data verified): rely on `mega_mutation` as the only real crypto edge
- **Evidence:** n=18 in Nov recent_closed window: WR 72.2%, PF 3.20, avg +3.31%; last-30d n=7
  WR 57.1% PF 1.58. Peer T2 inventory: n=295, WR 64.1%, PF 3.16, PASS_ALL_AXES 5/5 — the ONLY T1.
- **Change:** stop headline-highlighting `prediction_market_consensus` (WR 86% = resolver artifact;
  peer: `prediction_market_agents` overall WR 1.3%, 96.5% null close). Promote `mega_mutation` into
  the forward pilot and label everything else "research". Frontend + smart-picks feed only.
- **Effect:** the one honest edge becomes visible; the artifact stops leading the page.
- **Risk:** low (display/selection only).

## Quick win 2 — PASS (anchor verified): enforce the June source bans that were never applied
- **Evidence:** peer `wr_scrutiny_honest_2026-06-05.md` specified bans; my Nov live check finds
  `luxalgo_filter` (16 rows) and `prediction_market*` (3 rows) STILL EMITTING in active_raw.
- **Anchor:** `audit_trail/quality_gates.py::BLOCKED_SOURCE_SYSTEMS` (and mirrored
  `audit_dashboard/template.html::BLOCKED_SYSTEMS`) — verify on rebase, then add:
  `prediction_market_agents`, `polymarket_whale_tracker`, `short_dominant_engine`,
  `polymarket_momentum`, `copy_trader_polymarket`.
- **Caveat:** `luxalgo_filters` now shows PF 1.11 n=1,277 in Nov data — do NOT blind-ban; re-scope
  (exclude null-close rows) first. Log the decision.
- **Effect:** removes the class of source that emitted the XRPUSDT entry=0.0 garbage row.

## Quick win 3 — PASS (data verified): drop EXPIRED rows from the active arrays
- 79% of `.picks.active_raw` (3,272/4,148) are EXPIRED pnl=0. Filter them out of the "active"
  payload entirely (they belong in recent_closed). Generator-side, shared with all classes —
  see `fixspecs/fixspec_zombie_purge_and_reemission_guard.md`.
- **Risk:** low; reverts to a stricter definition of "active".

## Quick win 4 — PASS (data verified): never emit entry_price <= 0
- Live: `prediction_market_consensus` emitted XRPUSDT entry=0.0 at 2026-11-14T13:54 (fitched 90 min
  later); BTCUSDT entry 0.3322/1.334 rows exist. Refuse to emit; quarantine bad rows.
  See `fixspecs/fixspec_garbage_price_ingest_guard.md`.

## Quick win 5 — FAIL (shared generator): zombie purge of inverse_mutations
- 2,262 EXPIRED pnl-0 rows from `inverse_mutations` alone. No crypto-only fix; needs the shared
  generator filter + a one-time purge migration. Spec in fixspec_zombie_purge_and_reemission_guard.md.

## Quick win 6 — PASS (data verified): show 'awaiting price' not 0%
- OPEN rows with `current_price=None` render as 0% P/L. Render "awaiting price" + age instead.
  Frontend (`template.html` pick-card renderer).

---

# Proposed fix (deeper) — crypto single-source concentration breaker

**Problem:** registry CRYPTO is 97.9% single-source; the class stat is really one source's stat.
`prediction_market*` and `luxalgo_*` dominate volume (peer: prediction_market_agents n=2,731 with
96.5% null close).

**Spec:**
1. In the ledger build (`fixspec_single_canonical_ledger.md`), compute per-class **source mix** and
   per-source WR/PF, and publish `source_mix` + `hhi` in the class card.
2. Gate: a class card may only show a headline PF if the top source is <70% of resolved n AND the
   binomial p-value vs 50% is < 0.05 (peer `per_class_scrutiny` already computes these axes —
   reuse `reports/per_class_scrutiny_20260605.json` methodology).
3. Emit an explicit `DOMINATED_BY_SOURCE` verdict when HHI > 0.5 so the page never implies a class
   edge that is one source.
4. Apply the `DATE(closed_at) != '2026-06-04'` backfill filter everywhere (peer-specified).

**Acceptance test:** no CRYPTO headline PF shown while top-source share >70% or binomial p ≥ 0.05;
`mega_mutation` promoted to pilot with its own n counter and forward gate n≥100.
