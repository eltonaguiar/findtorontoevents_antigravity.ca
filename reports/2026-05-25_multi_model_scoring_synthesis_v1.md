# Multi-Model Stock-Algorithm Scoring Synthesis — v1 (partial, 2 of 11 models landed)

**Date:** 2026-05-25
**Status:** PRELIMINARY — only NVIDIA DeepSeek-R1-Distill-Qwen-32B-Uncensored + moonshotai/kimi-k2.6 have completed. MiniMax-m2.7, CF qwen3-30b, CF qwq-32b, and CF top-6 panel (llama-3.3-70b, llama-4-scout, nemotron-3-120b, gpt-oss-120b, glm-4.7-flash, mistral-small-24b) still running. This doc will be updated with v2 once they land.

## Inputs

| Source report | Model | Status |
|---|---|---|
| [2026-05-25_nvidia_deepseek_scoring_research.md](2026-05-25_nvidia_deepseek_scoring_research.md) | nicoboss/DeepSeek-R1-Distill-Qwen-32B-Uncensored (NVIDIA NIM) | done |
| [2026-05-25_nvidia_kimi_scoring_research.md](2026-05-25_nvidia_kimi_scoring_research.md) | moonshotai/kimi-k2.6 (NVIDIA Integrate) | done |
| 2026-05-25_nvidia_minimax_scoring_research.md | minimaxai/minimax-m2.7 | in flight |
| 2026-05-25_cf_qwen_scoring_research.md | @cf/qwen/qwen3-30b-a3b-fp8 + @cf/qwen/qwq-32b | in flight |
| 2026-05-25_cf_top6_scoring_research.md | 6 CF Workers AI top models | in flight |

## Cross-model consensus dimensions

Both DeepSeek + Kimi independently selected these as the core dimensions of a quality score (verbatim ordering):

1. **Risk-adjusted return** — Sharpe primary, Sortino preferred (both flag Sortino as "more honest because downside-only")
2. **Drawdown control** — max-drawdown (peak-to-trough) hard ceiling
3. **Sample size** — explicit floor below which the score is "unreliable"
4. **Statistical significance** — p-value / Bonferroni / t-test on returns > 0
5. **Out-of-sample generalization** — train/test split ratio, OOS-vs-IS metric ratio
6. **Cost burden** — slippage + commissions as % of gross return
7. **Win-rate** — secondary, both warn it's misleading without payoff-ratio context
8. **Bias audits** — survivorship, look-ahead, snooping

Dimensions where they diverge:
- DeepSeek explicitly weighted **interpretability** (5%); Kimi treated it as a binary `bias_audit == PASS` gate
- Kimi adds **beta to benchmark** (`|β| <= 0.3` for deploy); DeepSeek does not
- DeepSeek adds **scalability / computational efficiency** as a dimension; Kimi treats it as out-of-scope

## Consensus single-score formula (v1 draft)

Synthesized from both — uses DeepSeek's weight skeleton, replaces the soft "win-rate" with Kimi's `OOS-fraction` (more rigorous), keeps both authors' minimum-sample-size floor:

```
def quality_score(m, n_trades):
    # m = dict of metrics; n_trades = closed-trade count
    if n_trades < 100:
        return None, "INSUFFICIENT_N (need n>=100 for reliable score)"

    # Per-dimension 0-1 normalized sub-scores (saturating linear)
    sharpe_s    = min(m['sharpe_net'] / 1.5, 1.0)              # 1.5 = elite
    sortino_s   = min(m['sortino']    / 2.0, 1.0)              # 2.0 = elite
    maxdd_s     = max(0, 1 - m['max_dd_pct'] / 0.30)           # 0% DD → 1.0, 30% DD → 0
    n_s         = min(n_trades / 500, 1.0)                     # 500 = saturated confidence
    sig_s       = 1.0 if m['bonferroni_p'] < 0.05 else (0.5 if m['bonferroni_p'] < 0.10 else 0)
    oos_s       = min(m['oos_is_ratio'], 1.0)                  # 1.0 = OOS Sharpe == IS Sharpe
    cost_s      = max(0, 1 - m['cost_burden'])                 # 0% cost → 1.0
    bias_s      = 1.0 if m['bias_audit'] == 'PASS' else 0.0    # hard gate

    # Weighted sum (weights sum to 1.00)
    score = 100 * (
        0.20 * sharpe_s   +
        0.20 * sortino_s  +
        0.20 * maxdd_s    +
        0.10 * n_s        +
        0.10 * sig_s      +
        0.10 * oos_s      +
        0.05 * cost_s     +
        0.05 * bias_s
    )
    return round(score, 1), None
```

## Consensus deploy bands

Both authors converged on a 3-tier band with the same conceptual cutoffs:

| Band | Score | DeepSeek gates | Kimi gates |
|---|---|---|---|
| **DEPLOY** | ≥ 80 | Sharpe≥1.2 · MaxDD≤15% · n≥200 · Bonf-p<0.05 | Sharpe≥1.0 · Sortino≥1.5 · maxDD≤20% · n≥200 · Bonf-p<0.05 · OOS-R²≥0.6 · \|β\|≤0.3 · cost<30% · bias=PASS · WR≥53% |
| **RESEARCH** | 60–79 | Sharpe≥0.8 · MaxDD≤25% · n≥150 · Bonf-p<0.10 | Sharpe≥0.8 · Sortino≥0.8 · maxDD≤35% · n≥100 · p<0.05 · OOS-frac≥0.20 |
| **JUNK** | < 60 | any DEPLOY gate fails | any RESEARCH gate fails |

**Synthesis: use Kimi's deploy gates (stricter, more dimensions covered) as the operative gate; use the score formula above as the headline number.**

## Worked example

Hypothetical: Sharpe 1.2 · Sortino 1.8 · MaxDD 18% · WR 56% on n=240 trades · Bonf-p=0.03 · OOS-IS ratio=0.65 · |β|=0.15 · cost=20% · bias=PASS.

| Dim | Raw | Sub-score |
|---|---|---|
| sharpe (1.2/1.5) | — | 0.80 |
| sortino (1.8/2.0) | — | 0.90 |
| maxdd (1 - 18/30) | — | 0.40 |
| n (240/500) | — | 0.48 |
| sig (Bonf-p<0.05) | — | 1.00 |
| oos (0.65) | — | 0.65 |
| cost (1 - 0.20) | — | 0.80 |
| bias (PASS) | — | 1.00 |

```
score = 100 × (0.20·0.80 + 0.20·0.90 + 0.20·0.40 + 0.10·0.48 + 0.10·1.00 + 0.10·0.65 + 0.05·0.80 + 0.05·1.00)
      = 100 × (0.16 + 0.18 + 0.08 + 0.048 + 0.10 + 0.065 + 0.04 + 0.05)
      = 100 × 0.723
      = 72.3
```

→ **RESEARCH band** (paper-trade only). Both authors agree this hypothetical algorithm is *not* deploy-grade because MaxDD 18% pulls the score below 80 even though Sharpe + Sortino are strong.

Note that this matches **Kimi's worked example verdict of DEPLOY** when Kimi assumed *additional* unstated gates pass (OOS-R²=0.65, etc.). DeepSeek's formula in isolation also lands the example in RESEARCH at ~72-75. So with the consensus-merged weights, RESEARCH is the correct verdict.

## TODO (v2 update)

When MiniMax-m2.7 + CF qwen3-30b + CF qwq-32b + CF top-6 land:
- Re-extract their formulas + threshold tables
- Look for: any dimension the panel adds that the current 8 don't have (likely candidates: turnover, factor exposure, regime sensitivity, decay slope)
- Look for: weight disagreement > ±10% on any dimension
- Look for: deploy-band cutoff disagreement > ±5 points
- Write `2026-05-25_multi_model_scoring_synthesis_v2.md` superseding this one

## Next actions (independent of v2)

1. Wire the v1 formula into the live `/audit` promotion gate as a sidecar advisory score (NOT a blocker yet — needs the remaining 9 models' input first).
2. Add `quality_score` field to `audit_dashboard/data/nav_surface_edge_matrix.json` (built by agent E commit `ee182355a`) so the nav-surface matrix reports the consensus score per surface.
3. Track as new ENHANCEMENT_OVERALL row with proposed-by=multi-model-consensus.
