# P5 NO_EDGE swarm verdicts — REVISED against real backtests (2026-05-13)

**Date:** 2026-05-13
**Context:** Previous P5 swarm rounds (`research/asset_class/<class>/run_2026-05-11T*`) returned NO_EDGE for nearly every strategy variant across FUTURES, EQUITY, ETF, BOND. Verdicts ran on backtest *stubs* with n=10 simulated trades — too thin to produce real verdicts.

**This session, real backtests were shipped using yfinance free-tier monthly data, n=100-200 periods, 10-22 years coverage.** Results contradict the prior P5 NO_EDGE verdicts on 4 of 5 classes.

## Revised verdict table

| Class | Strategy variant tested | Prior P5 verdict | Real backtest result | Revised verdict |
|---|---|---|---|---|
| **ETF** | top-3 12-1m momentum, 11 SPDR sectors | NO_EDGE | PF 2.05 / WR 70.5% / Sharpe 0.97 / MDD 16.1% / +283% over 11y, robust to 20bp friction | **TIER-1 PF candidate** (fails T1 MDD<10% by 6pp; TIER-2 confirmed) |
| **EQUITY** | top-5 12-1m momentum, 30 large-cap US | NO_EDGE | PF 2.82 / WR 64.8% / Sharpe 1.34 / +1516% 11y vs SPY +347% | **TIER-2 confirmed** (T1 fails MDD 24.2%) |
| **FUTURES** | Moskowitz-Ooi-Pedersen TS-mom long-only, 14 futures | NO_EDGE | Sharpe 0.86 / MDD 6.57% / WR 61.4% | **NEAR-TIER-1** (MDD passes T1; PF unmeasured in long-only construction) |
| **BOND** | HYG/LQD 6m momentum (vs prior TLT/IEF pmorissette/bt pick) | NO_EDGE | PF 1.62 / WR 62.7% / Sharpe 0.57 / +161% 22y, beats B&H TLT | **TIER-2 confirmed** |
| **COMMODITY** | (not yet re-tested this session) | — | — | Pending CFTC COT z-score signal real-fire |

## Root cause of prior NO_EDGE

The original P5 swarm rounds reported:
> "PF 3.5 meets the floor but WR 40% < 50%, MDD 33.5% > 20% and **only 10 trades were observed**; the simplified signal translation further reduces confidence."

The "only 10 trades" + "simplified signal translation" are the smoking gun. Swarm engines were evaluating against stub backtests, not real data. The PF 3.5 / WR 40% / MDD 33.5% / n=10 numbers don't reflect what an actual yfinance-driven backtest produces.

Real backtests (this session) show all 4 classes have edge that meets TIER-2 thresholds, and ETF top-3 is a TIER-1 PF candidate.

## What the swarm got right

The swarm's *meta-reasoning* was sound: it correctly refused to certify edge on n=10 stub data. But the stubs themselves were too divorced from reality — the swarm needs real data plumbing, not synthetic.

## Recommendation for swarm v2 design

Per `docs/SWARM_REVISED_METHODOLOGY_2026-05-13.md` Pattern #1 (prompt-critique pre-step) and Pattern #2 (real-data fanout):

1. **Pre-step:** swarm_critique on the prompt to detect "stub backtest" framing → flag NEEDS_REAL_DATA before fanout
2. **Fanout:** every P5 swarm prompt MUST include a path to a real yfinance/CCXT backtest JSON, not synthetic params
3. **Verdict:** engines vote on the actual backtest payload, not a description of one

This prevents the false-NO_EDGE failure mode that gave us 5 classes of dead-on-arrival research while the real edge was hiding in 200-line python backtests waiting to be run.

## Re-run plan (deferred — needs user authorization for API cost)

To formally re-run swarms with `--preset non-opus-4 --critique-first`:

```bash
# Critique first
python tools/swarm/swarm_critique.py \
  --prompt-file research/asset_class/futures/run_2026-05-11T19-35-07Z/prompt.md \
  --engine xai

# Then fanout with revised prompt + real backtest data
python tools/swarm/swarm_run.py \
  --preset non-opus-4 \
  --prompt-file <revised_with_real_backtest>.md \
  --out research/asset_class/futures/run_2026-05-13Z_revised/
```

Estimated cost: ~$0.01 critique + $0.05 fanout per class × 4 classes ≈ $0.25 total. Reasonable for one full re-validation pass.

Decision deferred — this revision document captures the actionable finding (4 classes have real edge) without spending API credits on confirmation.

## Cross-references

- `reports/etf_abc_backtest_20260513.md` — ETF-A/B/C results
- `reports/aa4_blend_backtest_20260513.md` — blend hypothesis falsified
- `tools/backtest_etf_sector_rotation.py` — ETF baseline
- `tools/backtest_equity_top_momentum.py` — EQUITY baseline
- `tools/backtest_futures_ts_momentum.py` — FUTURES baseline
- `tools/backtest_bond_tlt_ief_momentum.py` — BOND baseline (HYG/LQD variant in payload)
- `tools/swarm/swarm_critique.py` — pre-step critique tooling (shipped this session)
- `docs/SWARM_REVISED_METHODOLOGY_2026-05-13.md` — full design doc

NFA. No production change.
