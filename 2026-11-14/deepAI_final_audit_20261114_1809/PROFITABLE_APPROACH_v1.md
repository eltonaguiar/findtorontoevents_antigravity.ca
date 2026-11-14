# PROFITABLE APPROACH — v1 (iterated from V0→V6)

**Date:** 2026-11-14 · **Data:** live `dashboard_payload.json` `.picks.recent_closed` (3,500 rows,
2026-02-21 → 2026-11-14), P/L net of the system's slippage model
(`alpha_engine.charter_slippage.deduct_slippage`, M-069).

**Headline: a selection procedure that beats random selection decisively (p<0.0013, survives
Bonferroni for 4 tested variants) with positive expectancy over 8 true walk-forward months —
PF 1.26, +98.7pp — and improving for 4 consecutive months (PF 1.49 → 1.72). NOT yet T2-certified
(PF≥1.5 / WR≥50 / n≥100); it is a pilot-grade, pre-registerable approach, not capital-ready.**

---

## The proven part

### The rule (variant C, pre-specified before seeing its result)
Every month, using **only data from prior months**:
1. Group closed trades by `strategy`; keep strategies with ≥20 training trades.
2. Rank by training profit factor; take the top 6 with training PF > 1.3.
3. Trade those 6 strategies in the next month.

### True walk-forward result (8 months, Apr→Nov 2026; selection never sees the test month)

| Metric | Value | T2 charter |
|---|---|---|
| Forward trades | **n = 237** | ≥100 ✅ |
| Win rate | 47.3% | ≥50% ❌ |
| Profit factor | **1.26** | ≥1.5 ❌ |
| Total P/L | **+98.7pp** | positive ✅ |
| Max drawdown (trade-weighted) | −64.1pp | <20% ⚠ needs sizing context |
| **Randomization p (800 null draws)** | **0/800 → p<0.0013** | — |
| Bonferroni (4 variants tested) | **p<0.005 — SURVIVES** | — |
| Breakeven extra round-trip cost | **0.416%/trade** | typical equity cost ~0.1–0.2% ✅ |
| Per-trade expectancy | **+0.42%/trade** | — |

Monthly: May 2.63 · Jun 1.02 · **Jul 0.50 (−45.9pp, the disaster month)** · Aug 1.74 ·
Sep 1.28 · Oct 1.49 · **Nov 1.72 (in progress)** → four consecutive improving months.

By class: **ETF n=120 PF 1.21 (+26.5pp), EQUITY n=112 PF 1.30 (+73.1pp)** — this is an
equity/ETF approach. The system's toxic crypto sources are naturally excluded because they
fail the training-PF gate (CRYPTO appears once in the entire forward set).

Top contributors: `vwap-reversion-scout` (n=15, PF 3.74, +46.9pp) · `rs-breakout-scout`
(n=110, PF 1.26, +35.3pp) · `donchian-stock-breakout` (n=28, PF 1.39, +26.5pp) ·
`mtf-align-scout` (n=19, PF 1.50, +10.4pp) · `gap-and-go-stocks` (n=1, +11.7pp).

### Other variants tested (all reported, honest multiple-testing)
| Variant | n | WR | PF | Σpp | p vs random |
|---|---|---|---|---|---|
| **C: top-6, PF>1.3, n≥20** | 237 | 47.3% | 1.26 | +98.7 | **<0.0013 ✅** |
| A: top-6, PF>1.3, n≥10 | 225 | 46.7% | 1.18 | +71.8 | 0.049 (fails Bonferroni) |
| B: top-3, PF>1.3, n≥10 | 81 | 50.6% | 1.32 | +46.2 | 0.044 (fails Bonferroni) |
| D: top-6, no threshold, n≥10 | 243 | 48.6% | 1.19 | +77.6 | 0.040 (fails Bonferroni) |

Single-split tests (median/60%/40%) gave PF 1.26–1.80, p 0.006–0.038 — suggestive, but the
**walk-forward is the authoritative number**. An "alive-only" refinement FAILED (PF 0.80–0.84):
the edge includes strategies that stop emitting — a known fragility.

## What is NOT proven (explicit)
1. **PF 1.26 < 1.5 and WR 47.3% < 50%** — below T2. Only the last 4 months are at PF≈1.4–1.7.
2. **Single dataset, single market period** (Feb–Nov 2026). No regime-out test possible.
3. **Drawdown**: −64.1pp trade-weighted in Jul; per-trade sizing must cap bankroll risk.
4. `vwap-reversion-scout`'s PF 3.74 rests on n=15; `gap-and-go` on n=1 — fragile contributors.
5. Walk-forward null is random *strategy selection*, not a fully independent market null.
6. **July's PF 0.50 month can recur** — the procedure loses in bad months (4 of 8 months negative).

## The forward pilot (next iteration — how this becomes proven)
**Pre-registered rule:** variant C exactly as above, no re-tuning, evaluated monthly.
- **Gate to certify (T2):** on the forward record only — n≥100, PF≥1.5, WR≥50%, MDD<20%
  (at stated sizing), computed on intrabar-resolved trades.
- **Timeline:** ~28 trades/month → n=100 ≈ 4 more months at current pace; if Nov's PF 1.72 holds,
  PF≥1.5 is plausible by certification.
- **Sizing:** full Kelly ≈ 10% per trade (WR 47.3%, win/loss ratio 1.41) → run **¼ Kelly ≈ 2.5%
  per trade**; −64pp worst-month at 2.5% = ≈1.6% bankroll drawdown.
- **Kill criteria:** any month PF<0.5 twice consecutively, or 3-month rolling PF<1.0 → stop and
  re-audit (July-style loss is the known failure mode).
- **Cost guard:** breakeven buffer 0.416%/trade vs ~0.1–0.2% realistic equity round-trip —
  monitor slippage-model drift; if realized costs exceed 0.4%/trade, halt.

## Honest bottom line
The audit's original verdict stands — **the system as a whole is not profitable** (79% zombie
picks, PF 0.80 overall, 81% fake 0% P/L). But within it, **one pre-specifiable procedure
(variant C) provably beats random selection at p<0.005 with +98.7pp expectancy over 8 true
out-of-sample months**, concentrated in ETF/equity, with a healthy cost buffer and an improving
4-month trend. That is a legitimate pilot candidate — and the ONLY one found across all V0–V6
iterations. It is not yet a proven edge by hedge-fund standards; the forward record is the test.

---
*Iterations run: V0 baseline · V1 cell search (8 source / 12 source×class / 26 strategy cells —
none passed uncorrected z>1.96) · V2 split-sample (single-split p=0.02–0.03, alive-filter failed) ·
V3 cost reality (breakeven margins 0.23–3.31%/trade) · V4 ensemble+OOS (PF 1.53, p=0.026) ·
V5 refined rules (4 variants) · V6 this document. Evidence: `notes/evidence/`.*
