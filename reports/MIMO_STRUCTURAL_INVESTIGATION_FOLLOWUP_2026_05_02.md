# MIMO Structural Investigation Follow-Up — 2026-05-02

**Author:** Xiao Mi MIMO peer agent (relayed via orchestrator)
**Status:** Honest follow-up after MIMO's PR #646 was clarified to be roadmap-only
**Audience:** Future AI agents + operator deciding what to do if Phase 1 quality-gate fixes (Cursor PR #644 + correlated-penalty cap + ETF emitter wiring) don't move per-asset-class performance to Tier 2 / hedge-fund-grade.

---

## Premise

If Phase 1 fixes don't move the needle, the problem is **structural** — not in the gates, but in the strategies themselves.

The hedge-fund approach isn't *"many strategies, hope some work."* It's *"prove edge exists first, then scale."*

---

## Layer 1 — Are strategies actually trading real patterns?

**The uncomfortable question:** most quant strategies are curve-fit noise that happened to work in a specific regime.

### What to check

- **Walk-forward efficiency.** Does the strategy's backtest WR hold in the next 6 months of unseen data? If backtest WR is 65% but forward WR is 42%, the strategy is overfit. Period.
- **Regime dependency.** Does the strategy only work in bull markets? In low-volatility environments? Plot WR by VIX quartile or BTC trend state. If it only works in one regime, it's not an edge — it's a bet on regime persistence.
- **Decay rate.** How fast does alpha decay after signal emission? If WR drops from 60% at 1 day to 45% at 3 days, you have a latency problem, not a strategy problem.

### Concrete action

For each asset class, take the top 5 strategies by closed-pick WR and run:

```
For each strategy:
  1. Split closed picks into H1 (first half) and H2 (second half) chronologically
  2. If H2 WR < H1 WR by >10pp → the strategy is decaying
  3. If H2 WR < 45% → retire immediately
```

The repo already has `forward_degradation_tracker.py` — but is anyone looking at its output?

---

## Layer 2 — Signal source quality

The system has many emitters but most are low-quality sources stitched together. The real question: **where does alpha actually come from?**

| Signal Source | Likely Quality | Why |
|---|---|---|
| Copy-trading retail traders | LOW | Retail loses 70-80% of the time. You're copying losers. |
| ML on price data alone | LOW-MEDIUM | Price-only ML has weak signal-to-noise. Needs alternative data. |
| Technical indicators (RSI, MACD) | LOW | Every retail trader uses these. No edge left. |
| Funding rate / basis | MEDIUM-HIGH | Real structural edge in crypto. The `funding_rate_carry` with 8.19 Sharpe proves this. |
| Sentiment (fear/greed, social) | MEDIUM | Works at extremes only. The contrarian concept was right; implementation was wrong. |
| Cross-asset confluence | MEDIUM-HIGH | Multiple asset classes confirming = real signal. |

**The hard truth:** if the best strategies are just technical indicators with scoring wrappers, no amount of gate tuning will make them hedge-fund quality.

### What to do

1. Audit signal source distribution — what % of closed picks come from each source type?
2. Kill everything from low-quality sources — retail copy-trading and pure TA strategies should be paper-only by default.
3. Double down on structural edges — funding rate carry, cross-asset confluence, and sentiment extremes are the real alpha.

---

## Layer 3 — Execution edge (where most retail systems fail)

Even with a good signal, execution can destroy it.

### Slippage reality check

- `SLIPPAGE_PER_TRADE` is likely set too low.
- Crypto slippage on mid-cap alts: **0.3-0.5% per side** (not 0.1%).
- Forex: **0.02-0.05% per side** on majors, **0.1%+** on crosses.
- If the backtest assumes 0.1% but reality is 0.4%, a 55% WR strategy becomes a **47% WR strategy.**

### What to do

- Pull actual fill data from exchange APIs (Binance gives you average fill price vs signal price).
- Calculate **realized slippage** per symbol per strategy.
- Feed that back into backtests as a per-symbol cost model.

---

## Layer 4 — Portfolio construction (the invisible killer)

The system has **per-pick** sizing (Kelly, risk-based) but limited **portfolio-level** optimization.

### Problems

- `MAX_OPEN_PICKS = 100` is way too high. No hedge fund runs 100 concentrated positions. At that count you're basically an index with extra steps.
- `MAX_CORRELATED_EXPOSURE = 0.40` — 40% in one asset class is still dangerous. Crypto correlation goes to 1.0 in crashes.
- No **dynamic allocation** between asset classes based on regime.

### What to do

1. **Reduce to 15-25 max positions** — forces quality over quantity.
2. **Correlation-aware sizing** — if you have 3 crypto LONG picks, the 4th should be penalized heavily (correlation clustering).
3. **Regime-based allocation** — in high-VIX regimes, shift from crypto/equity to bonds/forex.

---

## Layer 5 — The nuclear option: rebuild from edge up

If nothing above works, the honest answer is: **strategies don't have edge.** At that point:

1. **Start with one asset class** — pick the one with the best recent performance (likely CRYPTO based on the data).
2. **Pick ONE strategy** with proven structural edge (funding rate carry is the best candidate).
3. **Run it for 90 days** with real money (small size, $1K).
4. If profitable at 90 days, expand. If not, you don't have edge and no amount of engineering will create it.

---

## Investigation priority — TL;DR

| Priority | Question | How to answer it |
|---|---|---|
| **P0** | Are strategies decaying? | H1/H2 chrono-split on top 20 strategies |
| **P0** | What's the real slippage? | Pull exchange fill data, compare to signal price |
| **P1** | Where does alpha actually come from? | Audit signal source distribution |
| **P1** | Are we overfit? | Walk-forward efficiency on all strategies |
| **P2** | Portfolio construction? | Reduce max positions, add correlation sizing |
| **P3** | Nuclear: do we have edge at all? | 90-day live test on single best strategy |

The gates and thresholds are the **last 10%** of quality. The first 90% is: do the strategies actually work? **If they don't, no gate tuning in the world will fix it.**

---

## Cross-references

- MIMO's PR #646 (`docs/HEDGE_FUND_UPLIFT_ROADMAP.md`) — the Phase 1 roadmap MIMO believes will move the needle if executed.
- Cursor's PR #644 (`docs/per-asset-quality-plan` branch) — Phase 1 implementation: per-class thresholds + penalty cap + CI gate.
- `reports/HEDGE_FUND_UPLIFT_ROADMAP_2026_05_02.md` — Claude Opus's PR-decomposition roadmap (different angle: transaction-cost overlay, DSR, statistical rigor).
- `reports/PER_ASSET_AUDIT_QUALITY_ENHANCEMENTS_2026_05_02.md` (cloud agent's branch `copilot/enhance-hedge-fund-picks`) — per-class SME/Quant/QA panel + near-miss register + 541-entry kill_list age-out finding.
- `audit_trail/forward_degradation_tracker.py` — already exists, MIMO's open question: is anyone looking at its output?
- `alpha_engine/etf_strategies.py` — exists but unwired (one of MIMO's Phase 1 quick wins, but rated 70% confidence due to never running live).

---

**Saved by:** Opus orchestrator, 2026-05-02
**Source:** MIMO peer agent (Xiao Mi) via operator chat relay
