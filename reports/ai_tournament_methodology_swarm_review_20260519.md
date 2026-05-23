# AI Tournament Methodology — Swarm Review

**Date:** 2026-05-19  
**Engines:** OpenRouter (GPT-4o-mini), Cerebras (llama-4-scout), Ring-2.6-1T  
**Prompt:** `tools/swarm/prompts/ai_tournament_methodology_review_20260519.md`  
**Verdict:** ALL THREE → **NEEDS_WORK** (sound foundation, significant statistical and operational fixes required)

---

## Consensus Findings (2+ engines agree)

### 1. Statistical validity — n=5-20 is noise, not signal

All three engines flagged this independently:

- **Ring:** "At n=15, a 55% WR has 95% CI [33%, 76%]. You literally cannot reject randomness."
- **Cerebras:** "To detect 55% WR at 80% power, α=0.05 you need ~1,500 trades per model. For a rough directional signal (65% WR), ~200 trades."
- **GPT-4o-mini:** "Aim for minimum n≥30 per model per class. Use Wilson or Agresti-Coull CIs for WR; bootstrap CI for PF."

**Fix adopted:** Minimum n=30 completed trades per model per class before ranking. CIs reported on all metrics.

### 2. Selection bias — free-choice universe is the largest flaw

All three flagged this as the most critical design flaw:

- **Ring:** "This is the single largest methodological flaw. WR/PF are not comparable across models when the denominator (opportunity set) is different."
- **Cerebras:** "Model A could achieve PF=3.0 on easy trending crypto, Model B PF=1.2 on mean-reverting FX — but Model B might be the better strategist."
- **GPT-4o-mini:** "Standardize the symbol universe. Allow each model to rank internally but must submit top-k from the list."

**Fix adopted:** Pre-registered universe per class. Models rank within the universe; free picks OUTSIDE the universe are marked as bonus/unranked.

### 3. Hallucination check — ±5% is too coarse

- **Ring:** "Require trade-level logs. ±5% on aggregate WR won't catch look-ahead bias, which is the most common form of backtest fabrication."
- **Cerebras:** "Use exact binomial test for WR, bootstrap CI for PF. Require full trade-level P&L."
- **GPT-4o-mini:** "Reduce to ±2% or implement Chi-square test."

**Fix adopted:** Trade-level submission required. Exact binomial test for WR claims. Look-ahead bias detection added.

### 4. Resolution — mid-price at expiry is wrong

- **Ring:** "Use bid-price for sells, ask-price for buys. In crypto, bid-ask spreads can be 0.1–0.5% on majors, 1–5% on alts."
- **Cerebras:** "Use actual last-trade price, not synthetic mid-price."
- **GPT-4o-mini:** "Use closing price of asset on last day of window."

**Fix adopted:** Closing price at expiry (not mid). Conservative slippage: 5-10bps equity, 0.2% crypto.

### 5. Top operational risk

**Ring** identified the most critical: **data feed inconsistency + model versioning drift.** yfinance breaks frequently; OpenAI/Anthropic silently update models between cycles. Use cryptographic timestamping on all price pulls.

---

## Ring-Specific Insights (unique findings)

- **Model versioning drift:** API-based models are non-deterministic and silently updated. Pin model versions (e.g., `gpt-4o-2024-11-20`, not `gpt-4o`). This is critical for reproducibility.
- **Gap-through SL:** If BTC drops 10% in a candle and hits SL, fill at the candle low, not the SL price. Standard in real trading.
- **Short FOREX window (10d):** Many picks will expire unresolved. At n=5-10 picks per cycle, if 60% expire, you're scoring on 2-4 trades — meaningless. Consider extending FOREX to 21 days.

---

## Cerebras-Specific Insights (unique findings)

- **Multiple-testing bias:** Comparing dozens of models × 6 classes inflates false positives. Apply Bonferroni correction to p-values.
- **Minimum RR requirement:** Models with wide SL/TP ratios will artificially boost WR. Enforce SL ≤ 2×TP AND RR ≥ 1.5 at submission time.
- **Proposed scoring formula:** `Score = lower95(WR) × lower95(PF)` — only rewards statistically supported performance.

---

## Updated Design Decisions for Methodology v1.1

| Area | Original | Updated |
|---|---|---|
| Symbol universe | Model's free choice | Pre-registered universe per class; free picks = bonus/unranked |
| Min n for ranking | No minimum | 30+ completed trades per model per class |
| WR/PF ranking | Simple WR + PF | + confidence intervals; + Sharpe/Sortino/Calmar |
| Hallucination check | ±5% on aggregate WR | Exact binomial test; trade-level log required |
| Expiry resolution | Mid-price | Closing price (+ slippage adjustment) |
| Halluication tolerance | ±5% | ±10% aggregate; any trade-level fabrication = HALLUCINATION_CONFIRMED |
| FOREX window | 10 days | 21 days (else too many unresolved at small n) |
| Model version pinning | Not specified | Required; pin exact model version at tournament start |
| Min RR | Not specified | RR ≥ 1.5; SL ≤ 2×TP enforced |
| Scoring formula | WR + PF tier | `Score = lower95(WR) × lower95(PF)` (Cerebras rec.) |
| Data audit trail | GitHub Actions JSON | SHA-256 hash of each price pull; append-only |
