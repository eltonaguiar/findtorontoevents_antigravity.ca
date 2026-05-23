# Master Plan — Multi-AI Vetting Debate (2026-05-18)

Plan vetted: `reports/MASTER_ENHANCEMENT_PLAN_2026_05_18.md`. Briefing given to
reviewers: `reports/PLAN_VET_PREREQ_2026_05_18.md` (self-contained — no DB access).
Reviewers: **Grok (xAI)**, **opencode/DeepSeek**, **kilo**. Phase 1 = 3 independent
critiques; Phase 2 = reconciliation synthesis (below).

## Convergence — all 3 reviewers agree

1. **Measurement-first (Phase 0 as hard blocker) is CORRECT** — not a deferral
   tactic. You cannot run the harness / DSR / per-class floors on placeholder PnL.
2. **"No edge in the current set" is the honest verdict.** Grok + kilo: the harness
   is *permissive*, not strict — eff≥0.30 / 3-of-5-same-sign kills genuine noise.
3. **Funding-rate/basis arbitrage is OVERSTATED as "the" bet.** All 3 flag it:
   heavily arbitraged since 2022-24 (Grok); "not directional" vs a harness that
   needs consistent direction is contradictory framing (kilo); execution-risky —
   negative funding, counterparty risk, basis convergence, capacity erosion, and a
   data-availability red flag ("Day 1: confirm the data" = you don't have it yet)
   (opencode).
4. **The plan is MISSING a cost model** — Grok + opencode, strongly. `pf_registry`,
   the harness, and resolved outcomes appear to run on gross/placeholder PnL.
   Net-of-cost expectancy + per-class slippage is higher-leverage than the edge hunt.
5. **Biggest risk: Phase 0 may not actually fix outcomes.** kilo — if the resolver
   *logic* is broken (not just `closed_at` unfilled), phases are wasted. opencode —
   Phase 0 is a dependency black hole (yfinance unreliable, market-hours, per-class
   TP/SL).

## Divergence

- **More strategies?** Grok: new *families* probably needed. kilo: don't conflate
  "no measurable edge" with "no edge exists". opencode: "cut ruthlessly, then probe
  with exactly 1-2 structurally-different families." → Reconciled: cut first, then
  1-2 genuinely-new-input families — never more variants.
- **Harness:** Grok says fine, attack the walk-forward *window construction*
  (regime diversity). kilo says permissive. opencode notes the CRYPTO 33% figure is
  a *recent window*, not the full policy-clean set.

## Briefing factual corrections (from reviewers)

- CRYPTO "WR ~33%, PF 0.17-0.41" is the **recent resolved window**, not the
  full policy-clean set (~WR 46%, PF ~1.26, n≈2028). Label it "recent window."
- `money_ready_verdict` gate (n≥50 / WR≥0.55) vs Phase-4 promotion (n≥100 /
  WR≥0.52) are **inconsistent thresholds** — reconcile.
- COMMODITY policy-clean is ~PF 2.30 at n≈47 — the issue is **sample size**, not
  only COT inflation.
- `pf_registry` "verdict-grade" vs COMMODITY-inflation note is contradictory —
  state explicitly what cost/dedup `pf_registry` does and does not apply.

## Plan amendments adopted (Phase-2 reconciliation outcome)

| # | Amendment | Source | Priority |
|---|-----------|--------|----------|
| A1 | Add a **cost model** — net-of-cost expectancy + per-class slippage feeding every gate AND the harness. Funding-arb needs a *continuous*-funding cost model, not round-trip. | Grok, opencode | **P0** |
| A2 | Add **timeboxes + go/no-go dates** to every phase, and a terminal **"no edge → archive / shut down"** state. A sandbox without a deadline becomes permanent. | Grok, opencode | P0 |
| A3 | **Phase 0b parallel track** — don't let Phase 0 block everything. Wire a paid data API (Polygon / Alpha Vantage) for EQUITY (2nd-largest class). Verify the resolver *logic*, not just `closed_at`. | opencode, kilo | P0 |
| A4 | Add a **kill-or-archive clause** — if Phase 0 shows a class has only stub emitters, delete it, do not "gather n". | Grok | P1 |
| A5 | **Downgrade funding-arb** — Day-1 data-availability check + a pre-registered kill criterion (e.g. net expectancy after cost < 0.5%/cycle → abandon) BEFORE committing the 90-day sprint. Treat as one of several orthogonal probes, not the savior. | all 3 | P1 |
| A6 | Add **external benchmark validation** (coin-toss / spot-hold baseline) + audit walk-forward **window construction** for genuine regime diversity. | kilo, Grok | P1 |
| A7 | Codify a **position-sizing protocol** as a gate — harness-admissible ≠ size-at-will. | opencode | P2 |
| A8 | **Briefing fixes** — relabel CRYPTO recent-window; reconcile the n/WR threshold inconsistency; document `pf_registry` cost methodology. | all 3 | P1 |

## Verdict

The master plan **survives vetting** — its core thesis (measurement-first, cut
volume not add strategies, harness-gated edge only, paper-only until proven) is
endorsed by all 3 reviewers. But it ships with **3 real gaps**: no cost model
(A1), no timeboxes / terminal state (A2), and an over-confident single funding-arb
bet (A5). Amendments A1-A3 are P0 and should fold into
`MASTER_ENHANCEMENT_PLAN_2026_05_18.md` before execution. Funding-arb is demoted
from "the Phase-3 bet" to "one gated probe among several, behind a data check."
