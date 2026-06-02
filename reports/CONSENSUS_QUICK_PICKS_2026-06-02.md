# Consensus Quick Picks (CQP) — 2026-06-02

**Author:** Claude Opus 4.8 orchestrating a 6-model AI panel via the local LiteLLM proxy.
**Type:** opinion-aggregation, **NOT** backtested edge. Use as a stability-tilted "park it" basket,
not as a proven /audit signal.

> **Honesty label (CLAUDE.md rule):** these are *AI-model consensus opinions* drawn from each model's
> training knowledge of analyst ratings / 13F ownership / moat & quality — **not a live data pull**.
> No model fetched anything. Treat as a sentiment prior to verify against live TipRanks/Zacks/Morningstar
> before sizing. This deliberately skips backtesting per the request for a "quick, pure-consensus" pick.

## Methodology (CQP v1)

No backtest. Each model scores candidates 0–100 on five consensus signals, then we aggregate:

1. **Analyst consensus** — Strong-Buy→Sell rating, # analysts, mean price-target upside (TipRanks/Zacks).
2. **Famous-investor / institutional ownership** — 13F whales (Berkshire, big funds), conviction holds.
3. **Stock-site consensus** — Morningstar moat + star rating, Seeking Alpha quant, Motley Fool coverage.
4. **Stability / quality** — durable moat, balance-sheet strength, low beta, dividend reliability.
5. **Trend sanity** — above 200-DMA, not in a structural drawdown.

**Asset-class stability tiers (default tilt):** BOND/T-bill ballast > broad ETF > mega-cap quality > single semi.

**Aggregation rule:** rank by (# of models that picked it) then by (average conviction). Any name with
more AVOID flags than picks is excluded regardless of score.

**Panel (6 valid voters):** cloudflare-llama, deepseek-chat-direct, hybrid-model-large,
nvidia-deepseek-v4-pro, ollama-cloud-local, paid-mode-large. (claude-haiku-direct / ollama-cloud /
openrouter-ring-1t / free-mode-large failed or returned empty this run.)

## Consensus result

| Rank | Ticker | Tier | Votes | Avg conviction | Avoids | Read |
|---:|---|---|---:|---:|---:|---|
| 1 | **MSFT** | Mega-cap | 6/6 | 90 | 0 | **Unanimous.** Moat + balance sheet + universal buy ratings. |
| 2 | **BRK.B** | Mega-cap | 5/6 | 89 | 0 | Fortress/Buffett diversification, the "sleep-well" equity. |
| 3 | **SGOV** | Bond/cash | 4/6 | 95 | 0 | Highest conviction overall — near-riskless T-bill yield anchor. |
| 4 | **VOO** | Broad ETF | 4/6 | 94 | 0 | Core S&P 500, low cost, the default equity ballast. |
| 5 | **VTI** | Broad ETF | 3/6 | 92 | 0 | Total-market breadth, self-cleansing index. |
| 6 | **COST** | Mega-cap | 3/6 | 89 | 0 | Membership moat, defensive, steady compounder. |
| 7 | **AGG** | Bond | 2/6 | 92 | 0 | Core investment-grade bond ballast. |
| — | GOOGL / SCHD / JPM | mixed | 2/6 | 86–89 | 0 | Honorable mentions. |

### On the names you named
- **MSFT** → **consensus #1, unanimous.** Strongest stability-with-upside pick on the board.
- **AAPL** → thin coverage this run (1 vote @ 95). Quality is undisputed but the panel preferred MSFT/BRKB for the same slot.
- **NVDA** → **divisive / net-negative:** 2 picks (avg 84) vs **3 AVOID**. Great company, but the panel says it's too cyclical/valuation-sensitive for a *stability* basket. Hold only if you accept volatility.
- **INTC** → **consensus AVOID:** 0 picks, **3 AVOID** ("fading moat, execution risk"). Do not put in a quick-pick safe basket.

### Suggested stability-tilted starter basket (illustrative, equal-ish weight)
`SGOV` + `AGG` (ballast) · `VOO`/`VTI` (broad equity) · `MSFT` + `BRK.B` + `COST` (quality mega-cap).
Most stable asset classes per request → **T-bills/bonds (SGOV/AGG)** and **broad ETFs (VOO/VTI)** dominate the top.

### Avoid consensus
INTC (3), NVDA (3, divisive), TSLA (2), ARKK/AMC/QQQ/TLT (1 each — TLT flagged for long-duration rate risk).

## Caveats
- Single-run snapshot; models have knowledge cutoffs and can be stale on ratings.
- Reproduce live: verify each top pick against TipRanks Smart Score + Morningstar star/moat before sizing.
- This is analysis, not financial advice. Per-pick raw votes: `reports/cqp_vote_*.txt`.
