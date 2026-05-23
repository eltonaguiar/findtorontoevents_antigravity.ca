# Correction — the "cost-model bug" P0 is already fixed (stale-input convergence trap)

**Date:** 2026-05-17 · **Author:** claude-desktop (Claude Opus 4.7)

## What happened

An external arena.ai repo audit, then a 3-engine swarm (deepseek + xai + kilo),
then a swarm idea-generation pass — **all four independently named "fix the
cost-model bug (fees subtracted every bar)" as the #1 P0 action.**

That is a textbook multi-AI convergence trap: every engine read the same stale
source — `CRYPTO_ML_WORLDCLASS_RESEARCH/FINAL_SYNTHESIS_REPORT.md` and
`MASTER_SYNTHESIS_REPORT.md` — which still describe R006 as an open bug.

## The verified facts (checked on disk 2026-05-17)

1. **The cost-model bug is already fixed.** `crypto_ml_edge/validation.py`:
   - `cost_adjusted_sharpe` (line ~447): `cost_array = np.where(returns != 0, cost_per_trade_bar, 0.0)` — cost on trade bars only.
   - `validate_model` (line ~580): identical trade-bar-only logic.
   - In-code comment: *"The old formula subtracted cost_per_bar from ALL bars including zero-signal bars, creating massive phantom drag."*
   - Fixed in commit **`fcce5f9268b`** ("fix(ml): 4 critical bugs from 28-agent research audit"), dated **2026-02-24** — the *same commit* that created the synthesis reports, so the reports' checklists were never updated to "done."
   - `alpha_engine/risk_metrics.py` and `ml_crypto_predictor/enhanced_models/advanced_validation.py` also use per-trade / trade-bar-masked cost — no per-bar bug anywhere.

2. **The −0.91 backtest-forward correlation is NOT a cost-model artifact.**
   deepseek's theory ("phantom fees depress backtest PnL → negative correlation;
   fixing the cost bug flips it positive") is **false**:
   - `EDGE_ADDENDUM.md` (dated 2026-04-06, i.e. *after* the 2026-02-24 cost fix)
     measures the −0.91 and diagnoses the real cause: `comprehensive_backtest.py`
     grid-searches 635+ strategies on **synthetic price data (`seed=42`)** — a toy
     regime-switching model with zero correlation to real market dynamics. The
     strategies memorise random noise; backtest WR is therefore *anti*-correlated
     with forward WR.
   - Because the −0.91 was measured post-cost-fix, it is real, not phantom-fee drag.

## Consequences — two swarm action items are now invalid

- **"Fix the cost-model bug" (unanimous P0)** — already done. No action.
- **"Invert all signals" (swarm idea #2)** — premise was that −0.91 = anti-edge.
  The −0.91 is synthetic-data overfitting, not a sign-flipped real edge. Inverting
  a noise-memorising signal yields noise. Do **not** invert.

## The actual P0 (from EDGE_ADDENDUM's own correct diagnosis)

Replace the synthetic `seed=42` price data in `comprehensive_backtest.py` (and the
strategy-generation path that feeds it) with **real historical market data**, then
re-run strategy selection. The −0.91 is a data-provenance bug in the backtester's
input, not a cost-accounting bug and not a signal-polarity bug.

## Process note

Reports under `CRYPTO_ML_WORLDCLASS_RESEARCH/` are point-in-time research
snapshots whose action checklists were never reconciled against later commits.
Future agents (and external tools like arena.ai) should treat their open-item
lists as **unverified** — confirm against the codebase + `git log` before acting.
R006 status in both synthesis reports has been corrected in this commit.
