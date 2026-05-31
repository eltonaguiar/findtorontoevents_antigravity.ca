# Cerebras Deep Critique — Strategy Pipeline End-to-End (2026-05-31)

**Model:** gpt-oss-120b (Cerebras hosted) — llama-3.3-70b unavailable on this account.
**Source doc:** `docs/STRATEGY_PIPELINE_END_TO_END_2026-05-31.md`
**Prior critique:** `reports/peer_claude-multi_ai_critique_cerebras_2026-05-31.md`
**System prompt:** senior quant, hostile reviewer mode.

## Parsed JSON

```json
{
  "critical_missing": "A real\u2011time execution\u2011cost & capacity model (slippage, market impact, fee schedule, and Kelly\u2011type sizing) is completely absent.  No file such as `alpha_engine/execution_costs.py` or a config in `docs/EXECUTION_COST_MODEL.md` exists, and the back\u2011test engine never subtracts transaction costs (see the lack of any reference to a cost model in `alpha_engine/outcome_resolver.py` or `alpha_engine/score_booster.py`).  Without this the P&L numbers are materially overstated and the system cannot enforce realistic position limits.",
  "most_important_gates": [
    {
      "gate": "n>=500",
      "reason": "Provides a minimum sample size to make any statistical inference credible; all fresh\u2011strategy PRs #307\u2011#322 were correctly rejected because n was far below this floor (Section\u202fB.2).",
      "citation": "Section B.2 / PR #307\u2011#322"
    },
    {
      "gate": "Wilson lower\u2011bound (LB)",
      "reason": "Gives a conservative confidence interval for binomial win\u2011rate estimates, protecting against small\u2011sample noise; implemented in `alpha_engine/smart_picks_engine.py` (line\u202f84\u201192).",
      "citation": "Section C.1 / `alpha_engine/smart_picks_engine.py`"
    }
  ],
  "over_engineered_gates": [
    {
      "gate": "Bonferroni correction",
      "reason": "PF, Sharpe and WR are highly correlated; applying a strict family\u2011wise error correction (Section\u202fC.2) throws away many viable signals and inflates Type\u2011II error.",
      "citation": "Section C.2"
    },
    {
      "gate": "Hard\u2011drop concentration cap (HHI>0.30 \u2192 drop)",
      "reason": "PR #344 shows that a hard\u2011drop turned a healthy EQUITY edge (251\u219243 emits) into a near\u2011zero signal, while a down\u2011weight would preserve diversification without killing the edge.",
      "citation": "Section C.4 / PR #344"
    }
  ],
  "bigger_money_loss": "data_quality",
  "methodology_ranking": [
    {
      "rank": 1,
      "methodology": "claude\u2011opus\u20114\u20117 (Cursor\u2011framework gates + verbatim verification)",
      "failure_mode": "None observed \u2013 correctly rejected all 8 fresh strategies at n=1\u20115."
    },
    {
      "rank": 2,
      "methodology": "Freebuff 10K MC bootstrap (PF 95% CI lower\u2011bound)",
      "failure_mode": "Occasional over\u2011optimism when bootstrap samples miss tail events, but still robust."
    },
    {
      "rank": 3,
      "methodology": "Qwen cohort analysis (raw vs policy\u2011clean)",
      "failure_mode": "Mismatched magnitude estimates; still identifies divergence patterns."
    },
    {
      "rank": 4,
      "methodology": "Zoo cursor\u2011framework on fresh strategies",
      "failure_mode": "Relies on the same n>=500 gate; no new bugs discovered."
    },
    {
      "rank": 5,
      "methodology": "Kilo forced_resolution (filter TIME_EXIT)",
      "failure_mode": "Survivorship bias \u2013 discarding TIME_EXIT removes the majority of trades and inflates apparent edge."
    },
    {
      "rank": 6,
      "methodology": "Grok pipeline\u2011corruption (stale DB + resolver bugs)",
      "failure_mode": "Partial verification; many claims fail to reproduce because of stale `signal_outcomes` rows (PR #361)."
    },
    {
      "rank": 7,
      "methodology": "claude\u2011parallel MC capping (winsorize pnl_pct to [SL,TP])",
      "failure_mode": "Systematically inflates PF (2\u20116\u00d7) as shown in PR #347 and #343; deprecated in PR #358."
    }
  ],
  "next_move": "fix_pipeline_first",
  "top_3_predicted_failures": [
    {
      "failure": "Resolver mis\u2011labeling (TIME_EXIT vs SL_HIT) inflates PF and mis\u2011classifies PnL",
      "evidence": "PR #353 \u2013 11,596 TIME_EXIT vs 4 SL_HIT in FOREX; also PR #158 for CRYPTO WON\u2011on\u2011negative\u2011PnL."
    },
    {
      "failure": "Stale `signal_outcomes` table causing missed exits and phantom OPEN positions",
      "evidence": "PR #361 \u2013 forward_validator frozen 270h; PR #339 \u2013 backtest trades table 25\u2011day lag."
    },
    {
      "failure": "Hard\u2011drop concentration cap hiding profitable EQUITY edge",
      "evidence": "PR #344 \u2013 EQUITY edge reduced from 251 to 43 emits; PR #351 \u2013 ETF verdict hidden."
    }
  ],
  "most_urgent_missing_topic": "execution cost & capacity modeling (slippage, market impact, fee schedule, and Kelly\u2011type sizing)",
  "paper_pilot_horizon": "with_caveats"
}
```

## Full response

```json
{
  "critical_missing": "A real‑time execution‑cost & capacity model (slippage, market impact, fee schedule, and Kelly‑type sizing) is completely absent.  No file such as `alpha_engine/execution_costs.py` or a config in `docs/EXECUTION_COST_MODEL.md` exists, and the back‑test engine never subtracts transaction costs (see the lack of any reference to a cost model in `alpha_engine/outcome_resolver.py` or `alpha_engine/score_booster.py`).  Without this the P&L numbers are materially overstated and the system cannot enforce realistic position limits.",
  "most_important_gates": [
    {
      "gate": "n>=500",
      "reason": "Provides a minimum sample size to make any statistical inference credible; all fresh‑strategy PRs #307‑#322 were correctly rejected because n was far below this floor (Section B.2).",
      "citation": "Section B.2 / PR #307‑#322"
    },
    {
      "gate": "Wilson lower‑bound (LB)",
      "reason": "Gives a conservative confidence interval for binomial win‑rate estimates, protecting against small‑sample noise; implemented in `alpha_engine/smart_picks_engine.py` (line 84‑92).",
      "citation": "Section C.1 / `alpha_engine/smart_picks_engine.py`"
    }
  ],
  "over_engineered_gates": [
    {
      "gate": "Bonferroni correction",
      "reason": "PF, Sharpe and WR are highly correlated; applying a strict family‑wise error correction (Section C.2) throws away many viable signals and inflates Type‑II error.",
      "citation": "Section C.2"
    },
    {
      "gate": "Hard‑drop concentration cap (HHI>0.30 → drop)",
      "reason": "PR #344 shows that a hard‑drop turned a healthy EQUITY edge (251→43 emits) into a near‑zero signal, while a down‑weight would preserve diversification without killing the edge.",
      "citation": "Section C.4 / PR #344"
    }
  ],
  "bigger_money_loss": "data_quality",
  "methodology_ranking": [
    {
      "rank": 1,
      "methodology": "claude‑opus‑4‑7 (Cursor‑framework gates + verbatim verification)",
      "failure_mode": "None observed – correctly rejected all 8 fresh strategies at n=1‑5."
    },
    {
      "rank": 2,
      "methodology": "Freebuff 10K MC bootstrap (PF 95% CI lower‑bound)",
      "failure_mode": "Occasional over‑optimism when bootstrap samples miss tail events, but still robust."
    },
    {
      "rank": 3,
      "methodology": "Qwen cohort analysis (raw vs policy‑clean)",
      "failure_mode": "Mismatched magnitude estimates; still identifies divergence patterns."
    },
    {
      "rank": 4,
      "methodology": "Zoo cursor‑framework on fresh strategies",
      "failure_mode": "Relies on the same n>=500 gate; no new bugs discovered."
    },
    {
      "rank": 5,
      "methodology": "Kilo forced_resolution (filter TIME_EXIT)",
      "failure_mode": "Survivorship bias – discarding TIME_EXIT removes the majority of trades and inflates apparent edge."
    },
    {
      "rank": 6,
      "methodology": "Grok pipeline‑corruption (stale DB + resolver bugs)",
      "failure_mode": "Partial verification; many claims fail to reproduce because of stale `signal_outcomes` rows (PR #361)."
    },
    {
      "rank": 7,
      "methodology": "claude‑parallel MC capping (winsorize pnl_pct to [SL,TP])",
      "failure_mode": "Systematically inflates PF (2‑6×) as shown in PR #347 and #343; deprecated in PR #358."
    }
  ],
  "next_move": "fix_pipeline_first",
  "top_3_predicted_failures": [
    {
      "failure": "Resolver mis‑labeling (TIME_EXIT vs SL_HIT) inflates PF and mis‑classifies PnL",
      "evidence": "PR #353 – 11,596 TIME_EXIT vs 4 SL_HIT in FOREX; also PR #158 for CRYPTO WON‑on‑negative‑PnL."
    },
    {
      "failure": "Stale `signal_outcomes` table causing missed exits and phantom OPEN positions",
      "evidence": "PR #361 – forward_validator frozen 270h; PR #339 – backtest trades table 25‑day lag."
    },
    {
      "failure": "Hard‑drop concentration cap hiding profitable EQUITY edge",
      "evidence": "PR #344 – EQUITY edge reduced from 251 to 43 emits; PR #351 – ETF verdict hidden."
    }
  ],
  "most_urgent_missing_topic": "execution cost & capacity modeling (slippage, market impact, fee schedule, and Kelly‑type sizing)",
  "paper_pilot_horizon": "with_caveats"
}
```
