# deepseek - strategic fork

### 1. Are These Mutually Exclusive?

For a small team with modest budget, **options 1 and 3 are effectively mutually exclusive** in any given quarter. Both require dedicated research, data procurement, capital commitment, and ongoing monitoring. Splitting attention between new-input hunting and structural alpha production guarantees half-baked execution and higher failure probability.  

**Option 2 (research sandbox) is baseline compatibility**: it costs nothing and can run alongside either 1 or 3. But “sandbox” here means *zero capital at risk and zero new research hours* — it is a passive gate, not an active process. If you choose 1 or 3, you must explicitly pause all other edge hunts, including any new candidate generation.  

**Recommendation**: pick **one** of 1 or 3, run it hard for 90 days, with option 2 as the fallback posture if the selected path fails its kill criterion. Do not attempt both.

---

### 2. Sequencing — 90-Day Plan (Assuming Option 3 Is Selected; See Section 5)

**Week 1–2: Data & Infrastructure**  
- Acquire one clean, liquid structural alpha dataset: crypto perpetual swap funding rates from a single exchange (Binance or Bybit) via their API.  
- Build a minimal trading engine that can monitor funding rate, spot basis, and execute on the same exchange (paper trading initially).  
- **Kill criterion**: if after 2 weeks you cannot get reliable tick-level funding data with < 500 ms lag, abort — structural alpha dies on data quality.

**Week 3–6: Paper Execution & Backtesting**  
- Implement a pure funding-rate arbitrage strategy: short perpetual when funding > 0.01% per 8h, go flat when it drops below 0.005%; size ≤ 0.5 ETH notional.  
- Backtest over 2 years (2024–2026) using your existing harness (edge stability gate: eff ≥ 0.30, same sign, ≥3 of 5 windows).  
- **Kill criterion**: if paper returns after slippage and exchange fees do not exceed 1.5x the risk-free rate (2.5% annualized), or if the sign flips more than 1 window out of 5, stop.

**Week 7–12: Live Microlot**  
- Deploy $1,000 real capital on a single pair (ETH-USDT).  
- Daily monitoring: track realized PnL, slippage, funding payment lag, and liquidation risk.  
- **Kill criterion**: if max drawdown exceeds 5% or Sharpe ratio (realized) < 0.8 over any rolling 30-day window, shut down and return to research sandbox.

If option 1 is chosen instead, the timeline is similar but data acquisition (order flow or options) will take 4–6 weeks alone and cost $5k–$20k/month. A 90-day program for new inputs is almost certainly insufficient to reach a harness-passing result.

---

### 3. Base Rates (Probability of Harness-Passing Edge Within 6–12 Months)

Ranked from least to most likely:

1. **Option 2 (Research Sandbox)** — 0%. It produces no new candidates by design.  
2. **Option 1 (New Inputs)** — 3–8%. Order flow / options / alt-data from vendors is already sold to dozens of funds; edge persistence after costs is rare. Your own track record (7 straight kills) suggests you lack the data science depth to turn raw feeds into stable signals.  
3. **Option 3 (Structural Alpha)** — 10–15%. Better odds because it exploits mechanical inefficiencies (funding rate, basis, carry) that are not purely predictive. However, small teams often fail due to adverse selection, capital constraints, and exchange risk. The 15% number assumes you already have low-latency execution capability; if not, drop to 5%.

Honest summary: **No option has better than a 15% chance** of producing a real, cost-beating edge in 6–12 months. The most likely outcome for any choice is zero alpha after fees, slippage, and team time.

---

### 4. Structure Alpha — Genuinely Different or a Harder Trap?

It is **genuinely different** because you are not betting on direction but on capture of a contractual cash flow (funding, carry, spread). That removes the burden of predicting price.  

But it is **also a harder version of the same trap** if you lack the operational edge:  
- You need low-latency execution and continuous monitoring — a small team burns out fast.  
- Capacity is tiny: a $50k funding arb account can only scale to ~$200k before moving the market.  
- Jumps (e.g., exchange hacks, deleveraging events) can blow through stop-losses.

**One concrete structural strategy**: **Cross-exchange futures basis arb** (cash-and-carry on ES vs. SPY or BTC perpetual vs. spot).  
- **Data**: live Level-2 book from two exchanges + funding rate feed.  
- **Capital**: $100k minimum ($50k per leg) to survive margin calls.  
- **Risk**: exchange credit risk, liquidation engine latency, margin model differences. Expected Sharpe 1.2–1.8 before costs, but after fees and slippage it often drops below 0.5.  

Implementation demands dedicated DevOps — a small team should not attempt this without prior HFT experience.

---

### 5. The Single Highest-EV Move This Quarter

**Stop spending. Keep it a research sandbox.**  

Why: The edge hunt was thorough and honest. You have no reason to believe that a new data class or structural alpha will succeed given your resource constraints. Base rates are low, and the cost of distraction (time, money, morale) is high. The “highest EV” is not zero — it is **avoiding negative EV** from chasing low-probability strategies.

**Concrete acceptance test**:  
1. Freeze all candidate generation.  
2. Do not approve any budget for data or live trading through Q3 2026.  
3. Revisit only if a team member independently discovers a candidate that passes the harness *using existing data* — but given the 7-straight kill record, don’t hold your breath.

If the team cannot accept stopping, then the highest EV is **option 3 with < $10k live capital and a strict 90-day kill criterion** (as detailed in Section 2). But the odds of success are at best 10%, and the expected loss (including time) is almost certainly positive. The research sandbox preserves optionality for free. Use it.
