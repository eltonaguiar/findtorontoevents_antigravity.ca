# Prediction Market Copy Trading — Why Kalshi / Polymarket Still Has No Winners
**Date:** 2026-11-15  
**Purpose:** Explain why, despite prediction markets (Kalshi, Polymarket) and "copy trading" attempts, the system still has no consistent winners.  
**Core insight:** Prediction markets are not a magic alpha source. Copy trading them inherits all the same failure modes (multiple testing, cost, latency, adverse selection, stale data) plus new ones (event resolution risk, binary payout structure, regulatory constraint). The root cause is the same as everywhere else in this system: **information coefficient ≈ 0, no clean out-of-sample edge, all classes `sizing_allowed: false`**.

---

## 1. Why prediction markets don't automatically produce winners

### 1.1 Binary payout structure distorts incentives
Kalshi/Polymarket contracts are binary (Yes/No, $0/$100). The payout is capped. This means:
- **Edge must be in probability calibration, not magnitude.** A strategy that is "right 60% of the time" on 50/50 events still loses after fees if it overbets or underprices risk.
- **No trend-following alpha.** You can't "ride a winner" — the contract expires at $0 or $100. This eliminates an entire class of equity-style trend strategies.
- **Kelly sizing is different.** Optimal bet size on binary contracts is much smaller than on continuous-return assets; most copy-traders overbet relative to their edge.

### 1.2 Adverse selection — who is on the other side?
When you copy-trade a prediction-market signal, you are trading against:
- **Informed participants** with private or faster information (political insiders, industry experts, pollsters).
- **Market makers** who adjust prices in real time as new information arrives.
- **Other copy-traders** all executing the same signal, moving the price against them.

If the signal is public (a Discord alert, a Twitter post, a dashboard tile), the edge is already arbitraged away by the time you see it. **Copy trading public signals = buying liquidity, not alpha.**

### 1.3 Latency and resolution risk
- Prediction markets resolve on real-world events (elections, Fed decisions, regulatory rulings) with **long, uncertain resolution timelines**.
- A "winning" pick may sit unresolved for weeks or months, tying up capital with no mark-to-market.
- Resolution can be disputed, delayed, or overturned (e.g., contested elections), introducing event risk that price models don't capture.

### 1.4 The same root causes as the rest of the system
Copy trading prediction markets fails for the **exact same reasons** the internal scanners fail:
- **Multiple testing:** Thousands of event contracts, dozens of copy strategies, no `nb_trials` correction → false discoveries galore.
- **Costs:** Exchange fees + spread + slippage on binary contracts erode thin edges.
- **Stale data:** Copying a signal after it's already priced in.
- **No intrabar truth:** You don't know if the contract was tradable at the signal price when you receive it.
- **EXPIRED/non-win mishandling:** Unresolved or voided contracts mishandled in WR calculation.

### 1.5 "Copy trading" ≠ systematic edge
Copy trading is discretionary delegation, not a repeatable, pre-registered, costed, out-of-sample procedure. It fails every gate in `07-key-metrics/KEY_METRICS.md`:
- No `(asset_class \| n \| timeframe)` on copy results
- No DSR/SPA/PBO correction
- No cost model
- No benchmark comparison (vs what? vs holding cash? vs SPY?)
- No kill criteria

---

## 2. What would it take for prediction markets to work here?

If you want to use Kalshi/Polymarket as a **data source** (not a copy-trading target), the bar is:

| Requirement | Why |
|-------------|-----|
| Treat contract prices as **probability forecasts**, not trade signals | Binary payouts need calibration, not directional bets |
| Model **resolution timing** and **event risk** explicitly | Capital is tied up; resolution can be delayed/disputed |
| Apply the same **mandatory data-integrity filters** (no backfill labels, banned sources, sane-pnl, EXPIRED=non-win, intrabar validation) | Same failure modes as internal scanners |
| Require **clean OOS** vs a prediction-market benchmark (e.g., aggregated consensus, Metaculus, or flat 50/50) | Edge must exceed the wisdom of the crowd |
| Size at **¼ Kelly or lower** for binary contracts | Binary bets have different Kelly geometry |
| **Pre-register** the event-class strategy (e.g., "Fed rate decision direction") | Avoid multiple-testing across thousands of contracts |

Even then, the honest assessment is: **prediction markets are a data source, not an edge generator.** The edge (if any) comes from better probability calibration, which this system has not demonstrated (IC ≈ 0).

---

## 3. Why "copy trading" attempts have failed here

| Attempted approach | Why it failed |
|-------------------|---------------|
| Copy Kalshi/Polymarket contracts into `trading_picks` | Binary contracts mapped poorly to continuous PnL; resolution delays; no fill realism |
| Mirror Polymarket trader portfolios | Adverse selection; public signals already priced; fees |
| Use prediction-market sentiment as a feature for internal scanners | IC ≈ 0; sentiment didn't predict direction better than random |
| Auto-execute copy trades via API | Latency; slippage; adverse selection; no kill gate on consecutive losses |

**Bottom line:** Copy trading prediction markets is not a substitute for the hard work of measurement integrity, cost-adjusted OOS validation, and multiple-testing correction. Until the system has **one** strategy that clears the T2 gate (n≥100, PF≥1.5, WR≥50%, MDD<20% on clean OOS, beats benchmark), copying prediction markets will just copy losses faster.

---
