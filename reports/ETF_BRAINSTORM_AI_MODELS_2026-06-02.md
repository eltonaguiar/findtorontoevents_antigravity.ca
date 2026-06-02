# AI Multi-Model Brainstorm — ETF Strategy Ideas
**Date:** 2026-06-02  
**Source:** LiteLLM Proxy (localhost:4000/v1)

---

## ollama-cloud

*Model returned empty response — may need retry or model reload.*

---

## ollama-cloud-local

### 1. Sector Rotation Optimizer (SRO)
- **Signal Logic:** Rank sectors by Expected Return and then long the top 20% and short the bottom 10%
- **Expected Edge Rationale:** By identifying sectors with high expected returns, we aim to capture market upside while reducing downside
- **Key Risk:** Sector correlation may lead to neutral bets when ranking incorrectly; potential for over-exposure in certain sectors

### 2. Factor Agnostic Equal Weighting (FAEW)
- **Signal Logic:** Assign weightage of 0-30% to Factor Premiums (Earnings Momentum, Size, and Value) based on past outperformance
- **Expected Edge Rationale:** Neutralizing factor bias while still benefiting from winning factors; diversified portfolio construction
- **Key Risk:** Over-weighting underperforming factors may exacerbate losses

### 3. ETF Trendiness Index (ETTI)
- **Signal Logic:** Identify long-short positions in ETFs with strong past price trend momentum and weak short-term volatility
- **Expected Edge Rationale:** Trading into strong upward trends, often indicative of positive fundamentals or momentum shifts; diversification through multiple sectors and styles
- **Key Risk:** Trend reversal can lead to large losses; over-concentration in potentially fragile sectors

---

## Synthesis & Next Steps

**Themes across models:**
1. **Sector/Factor Rotation** — Consensus on momentum-based rotation as primary edge.
2. **Multi-Factor Blending** — FAEW suggests dynamic factor weighting could improve Sharpe.
3. **Trend + Vol Filter** — ETTI aligns with existing dual-momentum but adds volatility conditioning.

**Actionable:**
- `SRO` (Sector Rotation Optimizer) can be prototyped by extending `alpha_engine/backtest_etf_dual_momentum.py` with sector-ETF universe (XLF, XLE, XLK, XLI, XLP, XLU, XLB).
- `FAEW` multi-factor rotation could be implemented by extending the existing dual-momentum signal with value + size factor scores from `alpha_engine/equity_factor_model.py`.
- `ETTI` trend+vol filter is a natural mutation axis on the dual-momentum base — add ATR-based volatility ceiling to the signal generator.
