# AI Prediction Tournament — Methodology Review Request

You are a senior quantitative researcher / ML engineer reviewing a proposed methodology for an "AI Model Prediction Tournament."

The full methodology is below. Your job is to:
1. Identify any **critical flaws** in the design (statistical, operational, or practical)
2. Suggest **specific improvements** with reasoning
3. Rate the methodology: SOUND / NEEDS_WORK / FLAWED and justify

Be blunt. This will be executed on live markets with real AI model picks.

---

## The Methodology

**Goal:** Pit multiple AI model families (GPT-4o, Grok-3, Claude Opus, Gemini, DeepSeek, Cerebras, Ring, Mercury, etc.) against live financial markets. Each model:
1. Chooses its own symbol universe and justifies it
2. Generates a production-grade trading strategy per asset class
3. Produces specific forward-test picks (entry, TP, SL, confidence)

Performance is tracked live via GitHub Actions daily price pulls (failover: Binance→CoinGecko→KuCoin for CRYPTO; yfinance→Alpha Vantage for EQUITY). Picks resolve at TP/SL hit or at window expiry (14-60 days depending on class).

**Scoring:** WR (win rate), PF (profit factor). Tiers: T1 PF≥2.0/WR≥55%, T2 PF≥1.5/WR≥50%, T3 PF≥1.3/WR≥45%.

**Hallucination check:** Any backtest claim is independently reproduced using real OHLC data. ±5% tolerance. Outside tolerance → BACKTEST_DISPUTED. Fabricated data → HALLUCINATION_CONFIRMED + -1 pick penalty.

**No shortcuts prompt (applied to all models):**
> Act as a senior quant researcher at a top hedge fund. We need production-grade, mathematically rigorous, and thoroughly verified strategies. Think step by step. Cite sources. No fabricated data. No partial answers.

**Pick schema:** symbol | direction | entry_price | take_profit | stop_loss | confidence | asset_class | strategy_name | rationale

**Resolution windows:** EQUITY=30d, CRYPTO=14d, COMMODITY=28d, FOREX=10d, ETF=30d, BOND=60d

**Comparison:** At cycle end, compare best AI model strategy vs our own validated strategies per asset class.

---

## Questions for your review:

1. **Statistical validity:** Is WR + PF sufficient for ranking with n=5-20 picks per model per class? What's the minimum n for statistical significance? Should we use confidence intervals?

2. **Selection bias:** Models choosing their own symbol universe — does this introduce selection bias that makes comparison unfair? How would you control for this?

3. **Hallucination verification:** Is ±5% tolerance on WR claims reasonable? What's a better approach for verifying AI backtest claims?

4. **Resolution methodology:** Is "TP or SL hit, or mid-price at expiry" a sound resolution rule? What biases does it introduce?

5. **Practical execution:** What are the top 3 operational risks that would cause this tournament to produce invalid results?

6. **Improvements:** What one structural change would most improve the statistical validity of this tournament?

Give your answer in structured sections matching the 6 questions. Be specific and cite where relevant.
