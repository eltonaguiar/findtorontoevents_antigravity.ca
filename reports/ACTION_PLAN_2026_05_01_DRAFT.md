# Action Plan — 2026-05-01 Post-Mass-Merge Wave

## Context

12 PRs merged on 2026-05-01 between 21:17 and 21:25 UTC closing the
loop's main backlog (B1, B2 dupes closed, B4, B8, B11, B12, B15, B16,
B19→absent, B24, B28 + #585 escalation + #570 perf review). Two
merge-conflict PRs (#584 B2-grid + #586 B14-stress-test) closed for
the loop to recreate fresh. PR queue is currently **0**.

This plan identifies what's still pending after that wave and proposes
sequenced delivery for the next 7 days.

## Current state of /audit (verified 2026-05-01 ~21:30 UTC)

- Overall PF: **0.98** (stagnant; matches Cursor + Roocode 7-day reads)
- Recent 50 closed per class (after-cost net):
  - CRYPTO: WR 40%, **−24%**
  - EQUITY: WR 37%, **−26%** (PF degraded 1.43 → 1.29 over 7d)
  - ETF: WR 39%, **−37%**
  - FOREX: WR 29%, **−4%** (PF stuck at 0.27 — resolver noise)
  - COMMODITY: WR 36%, **+3%** (PF jumped 0.84 → 1.51 — PR #535 win)
  - BOND: WR 56%, **+2%** (n=20, noise-dominated)
- Active book: 23 picks (22 LONG, 1 SHORT)
- 30 fresh UEPS long-term picks emitted but not yet on /audit's main
  table (B28 fix #582 merged 21:22 UTC; surfaces on next dashboard
  rebuild).

**Million-dollar question for the recent window:** equal-weight on the
active book = **lose ~25% in 4 of 6 classes**. Only `st_fear_greed_contrarian
LONG CRYPTO` (n=55, WR 90.9%, Wilson lb 80.4%, +1.26%/trade after costs)
and `rs-breakout-scout LONG EQUITY` (n=18, WR 77.8%, +2.58%/trade) survive
both Wilson 95% lb AND realistic costs.

## Pending action items (post-2026-05-01-merge-wave)

### Wave 1 — Verify & propagate (next 24h, no new code)
**V1-V7 verification re-run after merges propagate.** Specifically:
- V1: confirm UEPS picks appear on /audit main table (post-#582)
- V2: EQUITY × POSITION lane non-empty (post-#545 + #582)
- V6: concept_family stamped on every pick (post-#566 Phase 2 registry)
- V7: BOND credit-spread emitting (was non-fail diagnostic; recheck)
- New V8: B16 daily readout artifact present at `reports/forward_edge_audit_<date>.md`

### Wave 2 — Recreate the 2 closed PRs (this week)
- **B2-redux:** Asset-Class × Timeframe grid panel (#584 closed for
  conflicts). Same scope: 4×N grid on /audit showing active-pick
  count per (asset_class, timeframe), with empty cells flagged.
- **B14-redux:** Liquidity / slippage stress test for CRYPTO sidecars
  (#586 closed for conflicts). 2×-volume-spike simulation on PR #525
  + #527 paper-traded picks.

### Wave 3 — Empirically-driven follow-ups from the 7-day perf review (this week)
- **EQUITY-REGRESS:** Diagnose the EQUITY PF 1.43 → 1.29 drop.
  Per-strategy breakdown: which equity strategy degraded? Likely candidates:
  `mtf-align-scout` (single-symbol concentration on AMD), `goldmine_stocks`
  zombies, or the post-PR-#539 HC-floor tune leaking weaker picks.
- **FOREX-RESOLVER-2:** Drop non-JPY threshold 5.0 → 1.5 (per the prior
  panel's renegotiation; PR #531 verdict was REJECT-on-broken-bar).
  Re-run A/B replay with the lower bar; ship if Sharpe lift ≥ 0.5.
- **HYRO-FRESHNESS:** `hyro_pick_performance.json` stale since Apr 19,
  `hyrotrader_short_term_entries.json` stale since Apr 14. Identify
  which workflow stopped emitting and revive OR formally retire.

### Wave 4 — Gate-soak items (delayed to mid-week)
- **B5 (Cursor Phase 3 scoring):** HIGH risk; gated on B4 (#566)
  soaking 48h post-merge. Earliest start: 2026-05-03 21:23 UTC.
- **B6 (Cursor Phase 5 UI filters):** LOW risk; gated on B4 only.
  Can ship as soon as concept_family field appears on every pick
  (V6 verification pass, expected within 1 dashboard cycle).
- **B13 (Per-class HMM):** HIGH risk; gated on B12 (#581) soaking 7d.
  Earliest start: 2026-05-08.

### Wave 5 — Ready items not yet PR'd
- **B7 (CFTC COT live-wire):** MED risk; V7 marked non-fail diagnostic
  on 2026-05-01 (0 BOND credit-spread picks but this is signal-availability,
  not a fail). Ready to ship.
- **B9 (TradingAgents wire-in shadow):** LOW risk; gated on V1 ✓.
  V1 expected to flip ✅ within next dashboard cycle (B28 fix took
  effect ~21:22 UTC). Ready to schedule for shadow-mode 14-day run
  in `long_term_pick_contract.py::emit_long_term_picks`.
- **B17 (HC button after-cost gating):** MED risk. Gated on B16 (just
  merged); can start once B16's daily artifact accrues 7+ days of data.
- **B18 (Shadow-mode auto-promotion):** MED risk; same B16 gate as B17.
- **B19 (Pair-level exception carve-out):** MED risk; standalone.
  Initial registry entry: `(atr_percentile_gate, BTCUSDT, LONG)` per
  the prior audit (n=25, WR 84%, Wilson lb 65%).

### Wave 6 — Operator-decision-blocked
- **B22 (Meme producer):** Decision required from operator: build new
  scanner (substantial), retire family, or status quo (recommended).
- **B25 (TradingAgents identical-metrics):** MED risk. Diagnostic
  needed first — log raw LLM responses per ticker; then fix prompt
  or adjudication averaging. Blocked behavior diagnosis, not code.

### Wave 7 — Bug-fix follow-ups
- **B23 (TradingAgents resolver SYSTEM_SOURCES):** This was claimed
  done by FreeBuff via the merged #550 + later code in main. **Verify
  on disk** that `audit_trail/universal_pick_resolver.py SYSTEM_SOURCES`
  contains `tradingagents` entry; if missing, ship the 1-line fix.
- **B26 (TradingAgents end-to-end smoke):** LOW risk; gated on
  B24 (#583 merged) + B25 (pending).

## Proposed sequence (impact-ranked, prerequisite-respecting)

| Order | Item | Wave | Risk | Why now |
|------:|---|---|---|---|
| 1 | Verify V1-V8 (next 24h, no code) | 1 | n/a | Confirms today's mass-merge actually delivered |
| 2 | EQUITY-REGRESS diagnostic (no PR; report only) | 3 | n/a | Most urgent — EQUITY is degrading week-over-week |
| 3 | B6 Cursor Phase 5 UI filters | 4 | LOW | Low-risk concept UI surfaces the B4 work |
| 4 | B23 verify (1-line fix only if needed) | 7 | LOW | Closes the TradingAgents loop |
| 5 | B19 pair-level carve-out (BTCUSDT initial) | 5 | MED | Surfaces a verified edge `(atr_percentile_gate, BTCUSDT, LONG)` |
| 6 | B2-redux grid panel | 2 | LOW | Re-create the closed #584 |
| 7 | B14-redux slippage stress test | 2 | LOW | Re-create the closed #586 |
| 8 | FOREX-RESOLVER-2 (drop non-JPY 5.0 → 1.5) | 3 | MED | Largest single edge gap (FOREX PF 0.27) |
| 9 | B7 CFTC COT live-wire | 5 | MED | Highest-leverage missing FOREX/COMMODITY signal |
| 10 | B9 TradingAgents wire-in (14d shadow) | 5 | LOW | Activates the adversarial-debate sidecar |
| 11 | HYRO-FRESHNESS audit | 3 | LOW | Restores hyrotrader telemetry |
| 12 | B5 Cursor Phase 3 scoring (after B4 48h soak) | 4 | HIGH | Gated; requires evidence accrual |
| 13 | B13 per-class HMM (after B12 7d soak) | 4 | HIGH | Gated; requires evidence accrual |
| 14 | B17 HC after-cost gating (after B16 7d data) | 5 | MED | Requires B16 artifact to have data |
| 15 | B18 shadow-mode auto-promotion | 5 | MED | Requires B16 artifact |
| 16 | B25 TradingAgents identical-metrics fix | 6 | MED | Diagnostic-blocked |

## Out of scope (deliberately deferred)
- B22 meme producer (operator decision required)
- B26 end-to-end smoke test (depends on B25)
- B10 UEPS KPI panel (needs n≥10 UEPS closes)
- Any further TradingAgents A/B Phases 4-6 (multi-model adjudication,
  variant-specific guardrails, per-variant dashboard metrics) — already
  in flight from Cursor's plan; let that run.

## Risk controls
- Each numbered item ships as its own PR with tests + per-PR doc.
- Anything HIGH-risk (B5, B13) lands behind shadow flag for ≥48h.
- All workflow auto-commits use `safe_push.sh`.
- Before any item with prerequisites, the loop verifies the prereq
  state on `main` (not on its branch).

## Acceptance criteria for the plan as a whole
- Within 7 days: items 1-11 complete; queue down to 5 gated items.
- Within 14 days: items 12-15 in shadow; B25 unblocked or formally
  parked.
- Overall PF target: 0.98 → ≥1.05 within 14 days, attributable via
  the per-class drift metric in B16's daily readout.

---

**This is the DRAFT v1.** Sending to 5 AIs for review. Will produce a
revised v2 incorporating consensus feedback, then 1 final review pass,
then implement.
