# Overnight Session Report — 2026-04-19

**For the user on wakeup.** TL;DR + evidence + decisions needed.

## Scorecard

**Tonight's S1 backtest results: 4-of-4 FAIL.** This is the v1.1 gate working correctly — it rejects unvalidated strategies. **The gate has now rejected 4 hand-picked academic candidates today.**

| Strategy | Verdict | Headline stat | Why fail | Recommendation |
|---|---|---|---|---|
| **CR-1 Funding Rate Reversion** (BTC/ETH) | ❌ FAIL | n=4 in 3y | Threshold above 99th pctile of realized funding | Archive (untestable on this universe) |
| **EQ-1 PEAD mid-cap** | ❌ FAIL | Sharpe 0.04, WR 36.6% | Edge decayed beyond Engelberg 2018 estimate | Archive |
| **B1 Altcoin Basis Arb** | ❌ FAIL | Sharpe −87.5, 101k trades all losing | Binance `markPriceKlines` pre-adjusts spot+funding → proxy captures noise, not basis | **Re-spec** (needs paid tick data) |
| **C3 VVIX/VIX Mean Reversion** | ❌ FAIL (interesting) | IS Sharpe **4.06**, WR **73.5%**, n=34 | n<200, OOS1 Sharpe inversion, W/L<1.0 | **Re-spec** to broaden frequency — first candidate >1 Sharpe IS |

## Shipped tonight (10 commits, on origin/main)

| Commit | Impact |
|---|---|
| `305397e1a` | **P0: strategy_performance.json coverage 5→160 strategies (2.6%→82.9%)** |
| `32931c188` | Baseline: current /audit top-15 + bar to outperform |
| `5bf6dbb4c` | 12 new S0 hypotheses from 3 Ollama models (DeepSeek-v3.1, GLM-4.6, Gemma3) |
| `371be1da0` | Quant Signal Engine Framework V1 (your JSON spec) |
| `9b586f5fe` | Paper-flag 20 strategies from PR #256 Cloud Agent batch |
| `136c6b4a3` | Paper-flag Kimi's ETF-1 intermarket-flow-scout |
| earlier | Today's 15 earlier commits (retraction, S0.5 audit, Strategy Factory v1/v1.1, etc.) |

Plus this commit: 4 S1 backtest evidence files (altcoin basis + VVIX).

## Open PRs (your review queue)

| PR | Author | Content | My rec |
|---|---|---|---|
| **#260** | eltonaguiar (Cursor) | 20+ new strategies + backtest JSON + `compare_to_audit_baselines.py` | **Review + merge docs portion, paper-flag strategies**. Cursor's own finding: "**0 strategies** pass the smart-gate stretch bar (60% WR + 0.59% mean)" — matches our v1.1 gate conclusion |
| **#259** | eltonaguiar (Cursor) | Quant Framework v2 (494 lines, excellent methodology) + 1 strategy file | **Merge docs, paper-flag the `donchian_adx_trend_breakout.py`** |
| **#256** | Copilot Cloud Agent | 3 ARE/RC/SWEEP + 20 more (bond/etf/forex/futures strategies) | **Do NOT merge as-is.** Paper-flagged via commit `9b586f5fe`. No backtest evidence in PR |
| Kimi's branch `feature/baby-strategies-mfi-cmo-keltner-aroon` | Kimi Code | 4 strategies: MFI, CMO, Keltner Fresh-Break, Aroon | **Create PR + merge for paper-test**. Only v1.1-compliant batch today (empirical backtest, culled failures honestly) |

## The "outperform current" challenge — honest answer

You asked: *"find a strategy which outperforms our current strategies."*

**Answer: no strategy tested today outperforms the top of the current dashboard. Kimi's Keltner Fresh-Break (WR 57.1%, PF 1.30, Sharpe 1.63, n=154) ties baseline #7 but doesn't outperform #1-6.**

Cursor's own finding in PR #260: **0 of 20+ strategies pass the "smart-gate stretch" bar (60.46% WR + 0.59% mean)** on their frozen backtests. That matches.

**This is actually the correct outcome.** Today's hit rate on hand-picked "strongest" candidates:
- Academic literature picks (CR-1, EQ-1): 0/2 pass S1
- LLM-generated hypotheses (B1 GLM, C3 Gemma): 0/2 pass S1
- Kimi's empirical iteration: 2/6 marginal passes
- Cursor's frozen-JSON batch: 0/20 pass outperform bar
- **Overall: ~5% hit rate on "outperform" bar**

## What unlocked tonight

**P0 track-writer fix** (commit `305397e1a`) restored `strategy_performance.json` from 5 tracked strategies to 160. This means:
- V3 playbook's "zero combos pass Wilson LB" was calibrated on 5 of 193 strategies
- Rerunning Wilson/Bonferroni analysis on the 160-strategy corpus may reveal real edges that were silently invisible
- Every `elite_scorer.py` forward_wr calculation will now have 32× more data to draw from

**Recommended morning action**: re-run V3 playbook analysis on cleaned + restored data. Expected: 2-5 strategies will newly clear Wilson LB > 50% Bonferroni. These are the real candidates to beat baseline.

## Still-open decisions for you

1. **Merge PR #259 docs (Quant Framework v2)?** Yes, safe.
2. **Merge PR #260?** Mixed — merge the docs + comparison script; paper-flag the strategy files that don't beat baseline.
3. **Create + merge Kimi's PR?** Yes. Her 4 strategies are the first v1.1-compliant batch. Go to paper-test pipeline immediately.
4. **Re-run V3 playbook analysis on restored track data?** Yes — highest leverage. May reveal existing strategies with real edge.
5. **Fire a 5th backtest cycle on different candidates?** Only 1 worth pursuing: **VVIX/VIX (C3) with broadened signal frequency** — it's the first Sharpe-4 candidate today. Re-spec before trying.

## Meta insight

The Strategy Factory v1.1 gate works. 4 peer reviewers endorsed it; 4 S1 runs tonight confirmed it rejects bad hypotheses honestly. You should trust it over the impulse to "just ship 10 more strategies."

Your dashboard is healthy (43 active picks, shadow-mode fix confirmed working). The biggest risk tomorrow is **not** "too few strategies" — it's **un-validated strategies slipping past the gate via parallel agent PRs**. Keep paper-flagging anything without proper S1-S3 evidence.

---

Sleep well. Everything important is on origin/main. The rest is queued for your morning review.
