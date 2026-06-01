# Deep Hostile Critique — Mimo (xiaomi mimo-v2.5-pro) on End-to-End Strategy Pipeline

**Date:** 2026-05-31
**Reviewer:** mimo-v2.5-pro (xiaomi, via token-plan-sgp.xiaomimimo.com)
**Doc reviewed:** `docs/STRATEGY_PIPELINE_END_TO_END_2026-05-31.md` (15.5KB)
**Prior critique (shorter):** `reports/peer_claude-multi_ai_critique_mimo_2026-05-31.md`
**Posture:** Hostile reviewer (instructed not to agree)
**System prompt:** "Senior quant who has built production trading systems at hedge funds. Be specific and concrete. Reference research papers / known pitfalls. Use bullet points."

---

## Parsed JSON Verdict

```json
{
  "next_move": "fix_pipeline_first",
  "bigger_money_loss": "data_quality",
  "most_urgent_missing_topic": "execution_costs_slippage",
  "paper_pilot_horizon": "fantasy",
  "most_important_gates": ["intrabar_OHLC_replay", "DSR_with_PBO"],
  "over_engineered_gates": ["Bonferroni", "Wilson_LB"]
}
```

Full parsed JSON at: `/tmp/mimo_parsed.json` (saved during run).

---

## Full Mimo Response

```json
{
  "critical_missing": "Portfolio-level risk management and position sizing layer. The pipeline is entirely signal-centric: generate signals → score → gate → resolve → verdict. NOWHERE does it construct an actual portfolio, size positions, set aggregate exposure limits, or define drawdown circuit-breakers. This is not polish — this is the thing that makes you blow up. Specifically: (1) No portfolio construction means all 24 strategies operate independently with no coordination — if tsmom + donchian + ema_pullback all fire long crypto simultaneously in a momentum regime, you get 3x concentrated directional exposure with no one stopping it. The source-system HHI cap (0.30) measures which STRATEGY is concentrated, not which DIRECTION, FACTOR, or ASIT is concentrated. (2) No max-drawdown circuit breaker at portfolio level — BLOCKED_SOURCE_SYSTEMS is a manual post-mortem tool, not a real-time kill switch. A single correlated selloff (FTX-style, March 2020-style) across CRYPTO+EQUITY+FUTURES could destroy 30-50% of capital in hours with zero automatic intervention. (3) No position sizing — Kelly, risk-parity, or even equal-risk is absent. The smart_score/confidence system RANKS picks but doesn't SIZE them. Without sizing, a high-confidence 0.1bp-edge CRYPTO pick and a high-confidence 50bp-edge EQUITY pick get the same allocation, which is insane. Reference: DeMiguel et al. (2009) 'Optimal Versus Naive Diversification' — even 1/N equal-weight outperforms concentrated approaches without proper risk budgeting. The system has a scoring engine but no risk engine. This will cause spectacular, correlated, unhedged losses in the first real drawdown.",

  "most_important_gates": [
    "Intrabar OHLC replay — This is the single gate that determines whether your GROUND TRUTH is correct. Everything downstream (PF, WR, Sharpe, DSR, PBO, all verdicts) flows from whether a trade hit TP or SL first. PRs #347/#343 proved that winsorization inflates PF 2-6×, meaning your current resolution is systematically producing false-positive edges. Bailey & López de Prado (2014) 'The Deflated Sharpe Ratio' — the DSR gate assumes Sharpe inputs are unbiased; if your resolution is wrong by 2-6×, your DSR is computing the deflated version of a LIE. Fix resolution first; every other gate is garbage-in-garbage-out until you do.",
    "n>=500 sample size floor — This is the bedrock statistical requirement. At n<30, the Wilson lower bound on win rate has ±15-20% width even at 55% observed WR (Agresti & Coull 1998 approximation). At n=500, it tightens to ±4%. More importantly, n>=500 is the minimum where Bootstrap PF confidence intervals become stable enough to trust — below that, the bootstrap distribution itself is noisy (Efron & Tibshirani 1993, Ch. 12). The n=1-5 strategies are correctly rejected; the real danger is the n=50-150 strategies that PASS Wilson LB but have unstable PF estimates."
  ],

  "over_engineered_gates": [
    "PBO (Probability of Backtest Overfitting) — Conceptually misapplied. PBO (Bailey, Borwein, López de Prado 2014) measures the probability that the BEST strategy from K trials on a common dataset is overfit due to selection. It requires knowing K (the number of configurations tried). Applied to live signal_outcomes where there IS no multiple-testing problem — you're evaluating a fixed strategy on forward data, not selecting the best from backtests — PBO loses its theoretical foundation. If K is unknowable (and it is, because mutation strategies and darwin_engine generate configurations continuously), PBO becomes a number you compute but can't interpret. Drop it from money-ready gates; replace with a simpler out-of-sample RATIO (in-sample PF / out-of-sample PF < 1.5x degradation).",
    "Bonferroni correction — Applied to PF + Sharpe + WR simultaneously, but these three metrics are >0.85 correlated (all are monotone transforms of the same return vector). Bonferroni assumes INDEPENDENT tests and divides alpha by the number of tests. With 3 correlated tests, the effective number of independent tests is ~1.3-1.5 (Li & Ji 2005, 'Adjusted chi-square test for degree-of-freedom adjustment'). You're rejecting at α/3 when you should reject at α/1.4 — roughly 2x too punitive. This systematically kills low-n strategies that have real edge but insufficient data to survive 3x over-correction. Replace with Holm-Bonferroni (free improvement, still controls FWER) or a multivariate Hotelling T² on the return vector."
  ],

  "bigger_money_loss": "data_quality. Aggregation bugs (PR #351 ETF fallthrough, PR #346 BOND mis-tag, PR #344 EQUITY hard-drop) hide REAL edge — cost is opportunity cost (money not made). Data-quality bugs (PR #353 FOREX resolver mislabel with 11,596:4 TIME_EXIT:SL_HIT, PR #352 COMMODITY zero curve data with 8-symbol effective universe, PR #345 CRYPTO per-strategy hidden winners masking class aggregate) produce FALSE edge — cost is real capital deployed to strategies that don't work. Concretely: PR #353 means FOREX positions are being held until TIME_EXIT while suffering full SL-equivalent adverse moves that the resolver doesn't record as SL_HIT. Your FOREX PF is computed from mostly-zero-pnl time exits (median=0) plus a handful of TP/SL outcomes — this is a biased estimator that understates true loss rate. If you deploy real capital to FOREX based on this PF, you will lose money proportional to the mislabel rate × average adverse excursion. PR #352 is worse: trading 23 commodity futures with no term-structure data means you cannot distinguish contango (negative roll yield destroying 5-10% annually for crude, nat gas) from backwardation (positive carry). Commodity futures strategies without roll-yield awareness are not commodity strategies — they're random walks with transaction costs. Ref: Gorton & Rouwenhorst (2006) 'Facts and Fantasies about Commodity Futures' — the entire commodity futures premium is concentrated in the roll yield.",

  "methodology_ranking": [
    {
      "rank": 1,
      "method": "Zoo cursor-framework-on-fresh-strategies",
      "reason": "Correctly applied n>=500 + Wilson LB + Bonferroni to 8 fresh strategies at n=1-5. All 8 correctly rejected. Methodology is simple, falsifiable, and produces correct outcomes regardless of who implements it. No failure modes identified. Robust because the gates are conservative by design and the test data (n=1-5) is unambiguously below threshold."
    },
    {
      "rank": 2,
      "method": "claude-opus-4-7 (cursor framework + verbatim red-team)",
      "reason": "Comprehensive application across all peer methodologies caught 20+ fabrications. The verbatim verification step is the key robustness feature — it forces claims to match file/PR references, eliminating hallucination. Slightly less robust than #1 because it relies on human judgment in the red-team step (could miss subtle fabrications)."
    },
    {
      "rank": 3,
      "method": "Freebuff 10K MC bootstrap",
      "reason": "Bootstrap PF 95% CI lower-bound is a well-understood, theoretically sound technique (Efron 1979). The methodology is correct; the failure was in EXECUTION (83% artifact rate: 2 RETIRED_ALREADY, 2 DOESNT_REPRODUCE, 1 CONCENTRATION). If implemented with proper data validation, this would be the best methodology for live-edge assessment. Failure mode: implementation bugs in data sourcing (analyzing stale/incorrect data), not methodology."
    },
    {
      "rank": 4,
      "method": "Grok pipeline-corruption thesis",
      "reason": "2/5 claims verified (resolver bugs are real, forward_validator frozen 270h). 3/5 DOESNT_REPRODUCE. The core thesis ('everything is corrupt') is unfalsifiable — you can always claim more corruption than what's been found. Failure mode: unfalsifiable framing leads to false certainty about systemic failure. Specific bug finds (PR #361) are valuable but the methodology doesn't produce calibrated confidence — it's binary (corrupt/not-corrupt) with no probability estimate."
    },
    {
      "rank": 5,
      "method": "Qwen cohort analysis",
      "reason": "Correctly identified raw-vs-policy-clean divergence. Wrong on magnitudes (FOREX PF reversal DOESNT_REPRODUCE per PR #361, EQUITY magnitudes wrong per PR #329). Failure mode: cohort comparison logic introduced errors — likely off-by-one in time windows or incorrect join between raw and policy-clean tables. The natural experiment approach is sound but implementation-specific bugs made conclusions unreliable."
    },
    {
      "rank": 6,
      "method": "Kilo forced_resolution",
      "reason": "Fundamentally flawed. Filtering OUT TIME_EXIT to analyze only TP_HIT+SL_HIT creates classical survivorship bias (Hendry 1980, 'Econometrics — Alchemy or Science?'). The most damning failure: OWN permutation test returned p=1.000 (no edge) and this was IGNORED. Publishing 'PROMISING' despite a self-generated p=1.000 result is not a methodology — it's confirmation bias with extra steps. Failure mode: survivorship by selection + ignoring self-generated falsification evidence."
    },
    {
      "rank": 7,
      "method": "claude-parallel MC capping (winsorize pnl_pct)",
      "reason": "Anti-robust — introduces systematic upward bias in PF by 2-6× (PR #347: FOREX 3.16×, PR #343: COMMODITY 6.46×). This is not a random error; it's a structural bias that makes EVERY strategy look better than it is. Winsorizing realized PnL to the [SL, TP] window assumes you would have exited at SL/TP if the path crossed it — but the whole point of intrabar replay is that you DON'T KNOW which was hit first without tick data. Capping is a bias-amplifier, not a bias-corrector. Deprecated (PR #358) for good reason."
    }
  ],

  "next_move": "fix_pipeline_first",

  "next_move_defense": "Your own thesis is correct: 'money-ready bottleneck is PLUMBING, not strategies/MC.' Here's the specific argument with numbers: (1) You have 6 architectural bugs that collectively distort ALL asset-class verdicts. Fixing PR #353 (FOREX resolver), PR #346 (BOND mis-tag), PR #344 (EQUITY hard-drop), PR #351 (ETF fallthrough), PR #345 (CRYPTO hidden winners), and PR #352 (COMMODITY no curve data) would give you CORRECT verdicts for all 6 classes for the first time. (2) 74/87 copytrader sources are silent — 85% signal attrition means your production signal pipeline has massive connectivity rot. (3) You have ZERO strategies at T2 money-ready as of 2026-05-24, but 3 of the 6 bugs are hiding real edge (PR #344 masks 251→43 emits, PR #351 hides n=153/PF=1.44 ETF strategy, PR #345 hides 4 T2-floor CRYPTO winners inside class aggregate). It's entirely possible that fixing the pipeline surfaces T2-class strategies you ALREADY HAVE. (4) Adding new strategies to a broken pipeline means new signals go through the same broken resolver, same misclassified asset classes, same inflated PF estimates — you'll make the same allocation errors with more instruments. Prioritize: Fix 6 bugs → Fix resolver OHLC replay → Add execution cost model → THEN evaluate whether you need more strategies. Expected timeline: 2-3 days for bug fixes, 1 week for execution cost model, then assess.",

  "top_3_predicted_failures": [
    "TIME_EXIT saturation will make all PF/WR/Sharpe meaningless across most asset classes. The resolver defaults to TIME_EXIT when intrabar OHLC can't determine TP-vs-SL first-touch (the fundamental issue documented in PRs #347/#343/#358). Expect >80% TIME_EXIT in FOREX (already 11,596:4 per PR #353), >70% in EQUITY, >50% in COMMODITY. With median PnL near zero for TIME_EXITs, PF will collapse toward 1.0 for most strategies, making it impossible to distinguish edge from noise. The harness will produce 'INSUFFICIENT' or 'FAIL' verdicts across the board — not because strategies lack edge, but because resolution is broken.",
    "At least 2-3 of the 8 fresh academic strategies (tsmom, connors_rsi2, triple_rsi, donchian_breakout, ema_pullback_trend) will emit correlated same-direction signals in the same asset class during a trending regime. With no portfolio-level correlation gate (Section G-Q5 is still open), these will appear as 3-5 independent 'high-conviction' picks that are actually a single factor bet. If the regime reverses, all stop-losses hit within the same hour. This is the #1 real-money blow-up scenario for tomorrow's harness.",
    "Forward-validator / signal_outcomes staleness will cause data gaps. PR #361 found forward_validator frozen 270h; PR #339 found bt_backtest_trades 25 days stale. The harness will encounter strategies where the last 10-20 resolved trades are missing from signal_outcomes, causing n-counts to be artificially low. Strategies that SHOULD pass n>=100 will show n=30-50 and be incorrectly rejected by the money-ready gate. This is a false-negative failure mode: real strategies killed by data pipeline staleness."
  ],

  "most_urgent_missing_topic": "execution_costs_slippage",

  "most_urgent_missing_topic_reasoning": "Execution costs are the MOST urgent because they determine whether you have edge AT ALL — every other missing topic (capacity, Kelly, regime-change, correlation) is conditional on edge existing post-costs. Specific argument: (1) Your academic strategies (Connors RSI2, Piotroski, momentum) have historically thin edges — backtest PF 1.2-1.5. After costs, most academic anomaly strategies lose edge entirely (Novy-Marx & Velikov 2016, 'Assessing the Costs of Factor Investing' — after transaction costs, 6 of 12 anomaly long-short portfolios have PF <1.0). (2) CRYPTO (your largest universe at ~9,648 symbols) has realistic round-trip costs of 20-50bps (10-25bps slippage + 10bps taker fees on Binance). A strategy with backtest PF 1.3 and zero-cost assumption may have live PF 0.7-0.9 after costs. (3) FOREX with 1-2 pip spreads: for a strategy targeting 10-20 pip TPs, costs eat 10-20% of gross profit per trade. (4) You have NO execution cost model anywhere in the pipeline — the backtests assume zero slippage, the gates evaluate raw (cost-free) PF/Sharpe, and the resolution records gross PnL. Until you add a cost model (recommend square-root impact model per Almgren 2003 'Optimal Execution with Nonlinear Impact Functions' for crypto, and spread-based model for FX/equities), you cannot distinguish 'edge exists' from 'backtest artifact.' This is the single highest-ROI infrastructure investment right now.",

  "paper_pilot_horizon": "fantasy",

  "paper_pilot_horizon_reasoning": "n>=500 in 30 days requires ~16.7 picks/day per strategy uniformly across all 24 strategies. This is fantasy for all classes except CRYPTO intraday. Specific math: (1) CRYPTO gainer scanner + momentum strategies: POSSIBLE. If scanner refreshes hourly across 9,648 symbols and emits 3-5 signals per scan, you could generate 50-100 signals/day. At this rate, n=500 in 5-10 days. This is the ONE class where 30 days works. (2) EQUITY PEAD: fires only around earnings (~3-4 weeks per quarter peak season). At 2-3 signals/day during peak and 0 otherwise, you'd need 200+ days for n=500. (3) EQUITY Piotroski/Magic Formula: quarterly rebalance signals. n=500 in 30 days is IMPOSSIBLE — you'd need 12+ years. (4) COMMODITY seasonal: 23 symbols with monthly/quarterly seasonal patterns. At 1-2 signals per month, n=500 requires 250+ months (20+ years). (5) FOREX carry: monthly rebalance on 10-18 pairs. n=500 in 30 days is impossible. (6) ETF Faber tactical: 6 symbols with monthly momentum signals. n=500 requires 83+ months. (7) Polymarket: hourly binary contracts — if actively scanning, n=500 is achievable in 2-4 weeks. (8) BOND: 4 symbols, static. n=500 is fantasy at any horizon under 5 years. CONCLUSION: For CRYPTO and Polymarket, 30 days is achievable. For everything else, you need either (a) lower the n floor to something Wilson LB can support (n=50-100 with wider CI), (b) accept that non-crypto strategies will take 6-24 months to reach n=500, or (c) fundamentally redesign your strategy emission to be more frequent (e.g., intrabar EQUITY instead of daily). The 'uniform n>=500 across all classes in 30 days' framing is a fantasy that will cause you to prematurely kill valid long-horizon strategies."
}
```
