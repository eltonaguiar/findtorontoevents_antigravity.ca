# Agent Prompts — Parallel Coding Agents (finpredict-v4)

**Date:** 2026-11-15 (AM)
**Purpose:** Ready-to-paste prompts for agents in parallel worktrees / different machines, each trying to find a *real* winning strategy per asset class.

**Universal requirements (paste into every prompt):**
- Must beat the **buy-and-hold benchmark** (SPY for equity, BTC-hold for crypto, 60/40 for allocation) **after all costs** (spread, slippage, commission, financing).
- Must be validated **out-of-sample / forward**, not in-sample. Pre-register the hypothesis.
- Must report **effective N, DSR, PBO, max drawdown, and net expectancy**.
- Must be **paper-traded 90 days** before any deployment.
- Must **fact-check any "proven"/contest claim with SubQ** (endpoint `https://api.subq.ai/v1/systemone`, model `subq-snap-1.2`, keys in `~/dbpasses.txt`, do not commit them) against primary sources. Default-reject TradingView/contest leaderboard claims.
- Must show the **risk-management overlay** (sizing, caps, kill-switch).

---

## Master Prompt (generic, per class)

> You are tasked with finding a genuinely profitable, deployable strategy for the **{ASSET_CLASS}** class in this repo. The system has struggled for years; do NOT trust existing claims. Follow the protocol:
> 1. Identify the buy-and-hold benchmark and state it explicitly.
> 2. Enumerate candidate strategy families with a *standing economic mechanism* (risk premium, behavioral bias, structural flow). Reject pattern-mining.
> 3. For each candidate: backtest on clean data, apply full costs, run walk-forward OOS, compute Sharpe/Sortino/Calmar/DSR/PBO/effective-N/drawdown.
> 4. Compare to the benchmark AND to buy-and-hold. It must WIN net of costs.
> 5. Pre-register the best candidate; specify the kill condition.
> 6. Fact-check any "proven"/contest claim via SubQ against primary sources.
> 7. Produce a paper-trading plan (90 days) and a risk overlay.
> Output: a single markdown report with the chosen strategy, its evidence table, benchmark comparison, and kill condition. Be honest if nothing passes.

---

## Per-Class Prompts

### EQUITY
> Target: long-term trend / momentum / factor strategies on US equities. Strongly prefer the Faber 200-day MA and AQR-style momentum (vol-managed). Reject intraday RSI-2/scalping. Benchmark: SPY total return. Must beat it after costs and OOS.

### Mutual Funds / ETFs
> Target: the ALLOCATION core (VTI/BND/SGOV or FXAIX/FXNAX/FZROX) + a tactical Faber 200-day MA sleeve. This is beta capture; prove it beats 60/40 after costs over 12 months with max DD <20%. Do NOT overclaim alpha.

### CRYPTO
> Target: swing momentum (POSITION horizon) on liquid pairs. Must beat BTC-hold after costs and OOS with n_eff ≥100. Fix measurement (gap-aware fill, no forged TIME_EXIT) first. Reject scalping.

### COMMODITY / FUTURES
> Target: CTA trend (TSMOM, 200-day MA) on real futures with a real data feed. Must beat an equal-weight commodity benchmark after costs, OOS, n≥100. Account for roll/contango.

### FOREX
> Target: low-frequency carry + trend. Must beat a carry-benchmark after swap costs, OOS. Reject intraday session scalping. Hard-disable until data is clean.

### Prediction Markets (Kalshi/Polymarket)
> Target: this is zero-sum + fees. Only pursue if you have a *grounded information edge* (not copy-trading). Pre-register; price in fees+spread; run 90-day paper. Be honest: most attempts will fail structurally.

---

## The "Truth Serum" add-on (force honesty)

> At the end of your report, add a section "What would falsify this strategy?" — state the exact test/data/event that, if it happened, would prove your strategy has no edge. If you cannot write this, the strategy is not ready.

---

## Coordination notes

- Each agent works in its own worktree; push only your own changes.
- Results land under `2026-11-15_AM_plan/finpredict-v4/`.
- Convergence check: compare the chosen strategies across agents; only strategies that survive independent OOS + benchmark + SubQ fact-check are candidates for deployment.
