# FORWARD CANDIDATE SCOREBOARD — honest CI-lower-bound vs the sizing bar (2026-06-13)

Method: per-strategy honest intrabar ledger (at_signal_outcomes TP/SL) → cluster-bootstrap PF CI lower bound (symbol-day clusters, tools/pf_ci_lower.py) + effective-n. **Sizing bar = CI-LB > 1.15 AND n_eff ≥ 80.** Point-estimate PF is NOT a promotion signal — the CI-LB is. Ranked by CI-LB.

| candidate | n | WR% | PF (pt) | **CI-LB** | n_eff | verdict |
|---|---|---|---|---|---|---|
| **luxalgo_confluence × SHORT** | 47 | 66.0 | 1.89 | **1.09** | 44.6 | **REAL EDGE, sub-bar** — front-runner; needs ~2× n |
| forex_rsi2_mean_reversion | 20 | 60.0 | 2.15 | **1.01** | 17.8 | real edge barely; DNR+HARD_KILL at this n — needs forward n, not relitigation |
| macd_rsi_confluence | 117 | 41.9 | 1.09 | **0.80** | 112.4 | **NO EDGE** — has the n (n_eff 112) but CI-LB<1; point PF is noise |
| futures_momentum | 62 | 50.0 | **1.53** | **0.43** | 21.4 | **MIRAGE** — point PF 1.53 looks Tier-2 but CI-LB 0.43; the "COMMODITY lead" cited across docs is NOT real under the referee (corroborates the DNR dedup-artifact flag) |

## The two findings that matter

1. **luxalgo SHORT is the ONLY candidate with a real, defensible edge approaching the bar** (CI-LB 1.09). It converts to a sizable winner iff forward n reaches ~80 with the CI holding. This is THE thing to grow (P0C #570 keeps it emitting). Re-run this exact CI-LB at n_eff≈80.

2. **The CI-LB referee just killed two "leads":** `macd_rsi_confluence` (PF 1.09 at a full n_eff 112 — but CI-LB 0.80, so the sample size is real and the edge is not) and especially **`futures_momentum` (point PF 1.53 → CI-LB 0.43)** — the COMMODITY "lead" repeatedly cited by agents/docs is a small-n/concentration mirage. Do not size or promote it; this is exactly why point-estimate PF is banned as a promotion signal.

## Implication for "getting to winners"
We do not have a sizable winner today, and the honest pipeline is THIN: one real sub-bar edge (luxalgo SHORT), one tiny one (forex_rsi2, DNR), and the rest are point-estimate mirages the CI-LB rejects. The path is unchanged and now precise: **grow luxalgo SHORT's forward n to the bar** (weeks, fed by the LONG-block) and let the pre-registered gates (pead, H-114, rsi5070) add candidates. Promotion is CI-LB-gated, never headline-PF.
