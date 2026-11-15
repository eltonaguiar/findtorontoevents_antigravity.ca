# 2026-11-15 · 12:33 AM · Winning-Strategies Package

**Worktree:** `buffy` · **Branch:** `main` · **Author:** Buffy (Codebuff)
**Predecessor:** `2026-11-15_1227AM_profitability/buffy/` (per-class plan, style matrix, SubQ run 1, industry cases)

This round answers three things the predecessor did not: **prompts for your parallel agents**, **why
prediction markets still have no winners**, and **the benchmark gap you caught** (beat the S&P 500 /
beat buy-and-hold).

---

## Bottom line, short

1. **No strategy in this repo currently beats buy-and-hold.** Not because it was tested and failed — because
   **it was never tested against a benchmark at all.** Zero of five classes has ever had an excess-return
   number computed. That is now documented as the top-priority gap.
2. **Prediction markets have no winners for six reasons**, the first of which is that *there is no
   prediction-market class* — their picks are filed as CRYPTO (32 rows), so no verdict has ever been
   computed. The rest: binary settlement has no TP/SL, the taker fee is **3.5% of stake at 50¢ / 6.3% at
   10¢** and peaks exactly where edge is claimed, copying pays that fee twice and arrives late,
   leaderboards rank lottery wins as skill, and no settlement data means no calibration measurement.
3. **You are right about funds, half-right about what wins.** A low-cost fund allocation has a measured
   **90.2%** chance of positive 10-year return. But **92.89% of active large-cap funds trailed the S&P 500
   over 20 years** (SPIVA YE2025). The wrapper wins; the average manager doesn't.

---

## The prompt pack (this round's main deliverable)

`01_agent_prompts/AGENT_PROMPTS.md` — 8 copy-paste prompts + a shared preamble:

| Agent | Assignment | Depends on |
|---|---|---|
| **A6** | **Ledger repair** — resolver mark-to-market, TP_HIT promotion, backfill 3,350 rows, CI gate | — (blocking) |
| **A0** | **Benchmark harness** — one reusable module: excess, IR, alpha t-stat, capture ratios | — |
| **A1** | EQUITY RSI-2 **vs SPY total return** | A0, A6 |
| **A2** | ETF 200-DMA trend **vs buy-and-hold** | A0, A6 |
| **A3** | CRYPTO funding carry **vs BTC hold and vs cash** | A0, A6 |
| **A4** | FOREX carry **vs T-bill cash** | A0, A6 |
| **A5** | Prediction markets — calibration + fee-inclusive breakeven, **maker vs taker** | A0, A6 |
| **A7** | **Red team** — tries to falsify every claimed WIN (double costs, 1-bar lag, drop best 5 trades, split by year) | A1–A5 |

**Quick start:** dispatch **A6 and A0 in parallel first**. Do not run A1–A5 until A0 exists, or five
agents will build five incompatible benchmarks.

Every prompt carries: the ten-gate definition of "REALLY works", a pre-written falsifier requirement,
one-hypothesis-per-agent, trial-count disclosure, and `results/<agent_id>/result.json` validated by
`results_schema.json`. The pack explicitly treats a well-evidenced **NO** as success.

---

## Where each of your six asks is answered

| Ask | Document |
|---|---|
| **1. Plan per asset class** | `2026-11-15_1227AM.../01_plan/PER_ASSET_CLASS_PLAN.md` (all 13 classes) + `03_benchmark_relative/BENCHMARK_GATES.md` (the missing benchmark half) |
| **2. Holding periods, styles, proven algorithms** | `2026-11-15_1227AM.../02_style_matrix/STYLE_MATRIX.md` — cost ladder, class×style matrix, World Cup audited winners (Unger 4×, Larry Williams +11,376%), Faber/TSMOM/RSI-2 literature; **no verified "Hoffman"** — flagged, not invented |
| **2b. SubQ + fact-check** | `07_subq/FACTCHECK.md` (run 2) and predecessor run 1 — real API, 40 decisions across 3 arms, sycophancy tested |
| **3. Answers to the Nov-14 plan** | `2026-11-15_1227AM.../03_nov14_answers/ANSWERS.md` — confirms the no-deploy call, corrects four numbers (ETF 566 marks not "zero picks"; COMMODITY/FUTURES unmeasurable not PF 1.78; three CRYPTO PFs; DSR at N=38 vs 361) |
| **4. Further essential questions** | `05_questions/QUESTIONS_ADDENDUM.md` (Q16–Q27) + predecessor's Q1–Q15. Repo answers **4 of 27** |
| **5. Industry turnarounds** | `2026-11-15_1227AM.../05_industry/INDUSTRY_TURNAROUNDS.md` — AQR quant winter, Man AHL (Sharpe **0.24**), Medallion capacity, GIPS/independent-admin trust machinery |
| **6. Metrics by perspective** | `06_metrics/METRICS_ADDENDUM.md` (benchmark-relative bars) + predecessor's absolute-metrics doc |

---

## New this round: the four benchmark numbers

Every strategy card should carry these, next to PF:

```
benchmark: SPY TR        excess: +1.9%/yr      IR: 0.62
up-capture: 104%         down-capture: 88%     capture ratio: 1.18
```

`excess ≤ 0` means **the strategy is an expensive index fund**. That single test is cheaper to run than
everything else in this repo and has never been run.

---

## SubQ run 2 (16 decisions)

| Finding | P |
|---|---|
| Prediction markets need their own class | **0.9995** |
| Copy trading cannot beat fees + delay | **0.0015** |
| Benchmarks must be a mandatory gate | **0.992** |
| Active fund beats index over 20y | **0.0016** |
| Low-cost fund allocation positive 10y+ | **0.9992** |
| Fee kills coin-flip edge | 0.996 |

**One disagreement, kept on the record:** with evidence, SubQ ranks **FOREX (0.303) above EQUITY (0.190)**
as next target; I rank EQUITY first (738 verified marks vs 158; 12% vs 56% contamination; 5–10 vs 10–20 bps
costs). That disagreement is now a scheduled head-to-head: A1 vs A4.

---

## What I did not do, and would not claim

- No strategy is recommended for capital. **0 of 15 gates pass.**
- The prompts are untested with your agents — they are written to be self-contained, but the first run
  will find gaps; expect to iterate once.
- Excess-return numbers remain **uncomputed**; the worked example in `BENCHMARK_GATES.md §4` is
  illustrative arithmetic, labelled as such.
- SubQ has no reasoning trace, so its agreement is not evidence about markets.

**Status: NO-GO for real capital. Dispatch A6 + A0 first.**
