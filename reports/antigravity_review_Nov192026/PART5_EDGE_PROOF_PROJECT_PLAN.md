# PROJECT PLAN — Hedge-Fund-Grade Edge Discovery, Proof & Forward Testing

**Author:** GitHub Copilot / Mercury-3 AI (`githubcopilot-mercury3AI`)
**Date:** 2026-11-22 06:30 EST
**Mandate:** find and *prove* edge to a standard a quant desk would accept, then stand up forward testing. Report honestly; a negative result is a result.

---

## 0. Peer intel that changes the baseline (read first)

From COMS 2026-11-22 (`notes/freebuff-session-summary-crosscheck-20261122`, `notes/reply-freebuff-methodology-xreview-20261122`, `notes/freebuff-h151-net-issuance-refuted-20261122`):

| Finding | Consequence for us |
|---|---|
| freebuff **retracted CRYPTO "PROVEN"**: PF 1.313 → **0.2656 over 22,864 policy-clean picks, −0.0464%/trade GROSS**. Every class negative gross except ETF (n=32). | The 1.313 was **window selection**. Any claim we make must survive the *full population*, not a chosen window. |
| After **20bp** round trip: recent-window PF 1.184, EQUITY 1.229→1.175, **ETF edge only 7.8bp wide**. | Costs decide everything. Gate at **2× measured slippage**. |
| Only FDR survivors are **"payoff grids"**: `MomentumEMA` = exactly two outcomes (−2.00/+3.00); `mega_mutation_macd_rsi_m048` = 57 trades on 3 symbols. | Two-outcome grids are **synthetic artifacts, not edge** → auto-REJECT. |
| Honest Binance first-touch on 1,717 crypto picks: **54% of exits differ** from recorded, yet PF 1.367→1.479. | Daily inflation doesn't reproduce on crypto → **must re-resolve on real bars** for every claim. |
| `zoo-savant`: **PROMOTED shown at n=0**, BOND WR 100% at n=2, `/audit2` referenced 404 + a 22h-stale sidecar. | Badges must be **n-gated**; stale/404 payload = silent single point of failure. |
| H-150/H-151 **REFUTED** (net issuance +1bp, t=−0.63). | The hypothesis registry is extinguishing candidates — good; keep using it. |

**Implication:** our own Part 4 "equity momentum PF 2.94" is a **backtest hypothesis**, not evidence. Under the retraction lens it must be re-run on the full population, cost-stressed, and forward-tested before it can be called anything.

---

## 1. Doctrine — the desk's proof standard (all 8 must pass)

A candidate is "edge" only if **all** hold on the **full, policy-clean, honestly-resolved** population:

| # | Gate | Rule | Anti-pattern it kills |
|---|---|---|---|
| G0 | **Population integrity** | Full policy-clean set, no window choice, no lookahead; declare N up front | window selection (the 1.313 retraction) |
| G1 | **Honest resolution** | Real-bar first-touch (intrabar), not daily-close approximation | 54% exit mismatch |
| G2 | **Net expectancy** | Bootstrap 95% CI (2,000 seeded) lower bound **> 0** | "gross positive" claims |
| G3 | **2× cost stress** | CI-LB **> 0** at **2× measured slippage** | ETF's 7.8bp edge |
| G4 | **Multiplicity** | Benjamini–Hochberg q ≤ 0.1 **and** Deflated Sharpe ≥ 0.95 with n_trials = all tested cells | p-hacking across 362 cells |
| G5 | **Stability** | Chronological split-half: both halves net mean > 0 | regime-luck |
| G6 | **Concentration** | No symbol > 60% of a cell, no source > 90% of an aggregate | single-source 82% CANDIDATE |
| G7 | **Mechanism sanity** | ≥3 distinct outcomes, ≥3 symbols, ≥5 params-free; payoff must not be a 2-point grid | `MomentumEMA` −2/+3 grid |
| G8 | **Forward evidence** | Own pod, real forward rows closed *after* registration; n≥100 | PROMOTED-at-n=0 |

**Verdict tiers:** INSUFFICIENT_N (<20) · WEAK (fails any gate, keep observing) · **CANDIDATE** (G0–G7 pass, forward accruing) · **PROVEN_T2** (all 8, forward n≥100).

---

## 2. Candidate tracks (ranked by evidence quality, not by promise)

| Rank | Track | Why it could be real | Why it might be fake | First exact test |
|---|---|---|---|---|
| **1** | **EQUITY large-cap momentum** (12-1m or 6-2m, top-3/5) | Economic mechanism (cross-sectional momentum is a documented risk premium); my cost-adj backtest PF 2.94@20bp | Backtest window + survivorship of a fixed 30-name universe; my own numbers not forward-proven | Re-run on **full** US history incl. delisted, 2× cost, split-half, then forward pod |
| **2** | **CRYPTO SHORT mean-reversion confluence** (strong-consensus SHORT, macd_rsi_m048 SHORT) | DSR 0.9999 / 0.32 cells; short side of a KILL class | n=22–24 only; class aggregate is KILL; likely window | Full-population re-run + first-touch on real bars + 2× cost |
| **3** | **FOREX USDJPY momentum / rsi2** | Sharpe 2.02 lab; DSR 0.966 on rsi2 | `fx_prices` stale to 2026-02-09; n=25 | Backfill prices → re-run → forward |
| 4 | ETF tactical (dual-momentum) | Lab WF PASS | 7.8bp edge < cost | Fix slippage model first; likely REJECT |

**Explicitly rejected now:** `MomentumEMA` (2-outcome grid), `mega_mutation_macd_rsi_m048` (57 trades/3 symbols), any "PROVEN" resting on a recent window.

---

## 3. Phase plan (each phase has a hard acceptance gate)

### P0 — Freeze & clean the measurement (½ day)
- [ ] Freeze a **canonical population manifest**: sha256 of the resolved view, N, exclusion counts (integrity / auto-expired / resolver-anomaly), as freebuff/zoo did.
- [ ] Make **one** denominator (canonical resolved view) the only source for every surface.
- [ ] **Fix staleness/404**: single payload path; freshness badge (>48h = red); n-gate every badge (no PROMOTED at n=0).
- [ ] Acceptance: `/audit`, `/audit2`, `/audit3` all read the same sha256; no PROMOTED/PROVEN badge below n threshold.

### P1 — Honest re-resolution (1–2 days)
- [ ] Re-price every closed pick with **real bars / first-touch intrabar** (the 54%-mismatch finding).
- [ ] Emit `reports/resolved_canonical_<date>.jsonl` with provenance per row.
- [ ] Acceptance: 100% of rows carry `resolver_version`, `first_touch_source`; mismatch report published.

### P2 — Full-population, cost-true re-scoring (1 day)
- [ ] Run the tribunal over the **full** population (no window) with 2× cost per class.
- [ ] Report PF/WR/net with CIs; flag any cell whose sign flips vs a recent window (the retraction detector).
- [ ] Acceptance: a "window-selection report" table proving whether each prior claim survives full-population.

### P3 — Candidate deep-tests (2–3 days) — the actual edge hunt
For tracks 1–3, each:
- [ ] **Sensitivity grid** (lookbacks/n-longs/cost) with **Bonferroni/BH** and **expected false passes** reported (not just the best cell).
- [ ] **Survivorship test**: include delisted names; compare vs fixed universe.
- [ ] **Split-half + sub-period** (pre-2015 / post-2015).
- [ ] **Mechanism check (G7)**: outcome distribution, symbol count.
- [ ] Acceptance: a verdict per track with the number that would kill it stated *in advance*.

### P4 — Register & wire (½ day)
- [ ] Register surviving candidates as **pods** (pre-registered, M-107) with frozen decision rules.
- [ ] Create `POD-H119-FORWARD-ALPHA` so the 430 orphan rows count.
- [ ] Wire the kill-tribunal denylist into `production_scanner` (block emission of killed cells).
- [ ] Acceptance: every candidate has a pod; scanner reads the denylist.

### P5 — Forward testing harness (1 day) ← the deliverable that proves
- [ ] `PAPERTRADE` sleeve per surviving track (see `PAPERTRADE_EQUITY_MOMENTUM_SPEC.md`), auto-tracked:
  - daily bar ingest → signal → paper fills at 20bp (and 2× stress shadow) → append `reports/forward_observations.jsonl`.
- [ ] Dashboard: live paper equity curve, n, net-CI-so-far, gate progress (n/100, CI-LB).
- [ ] **Promotion rule:** only when G8 met (own forward n≥100, 2× cost CI-LB>0, IR≥0.5 vs benchmark).
- [ ] Acceptance: ledger accrues daily; page shows distance-to-gate; nothing auto-promotes.

---

## 4. Risk controls (non-negotiable)

- **Max one new pod promoted per month**; each needs independent re-derivation by a second agent/model.
- **No real capital** until PROVEN_T2 on forward rows; then a capped pilot (≤2% risk/idea, hard stop).
- **Kill rule:** a pod whose forward CI-LB < 0 at day 30 or 60 ends (pre-committed).
- **Every published number carries `[SRC: path:line]`.**

## 5. Deliverables & cadence

| When | Deliverable |
|---|---|
| Each phase | a `PART5_P<N>_<topic>.md` in this repo with the gate table |
| Weekly | `reports/edge_status_<date>.md`: per-pod n, CI, gate progress |
| Monthly | full re-run + retraction sweep (any claim that flips sign is retracted publicly) |

## 6. What I will NOT do

- I will **not** call anything "proven" off a backtest, a chosen window, or n<100.
- I will **not** present the best cell of a grid without its multiplicity correction.
- I will **not** promote a two-outcome "payoff grid" strategy.

---
*Not investment advice. Measurement-first, evidence-first. This plan's first job is to try to falsify our own Part 4 result.*
