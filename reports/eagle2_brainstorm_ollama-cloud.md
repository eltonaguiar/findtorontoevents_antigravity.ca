# EAGLE2 brainstorm — ollama-cloud (ollama-cloud)

**1. Most‑promising back‑testable archetype per asset class (given the audit data)**  

- **Crypto:** *Liquidity‑wick‑reversal* – the only production‑ready crypto model with n ≥ 20 and PF > 1 (30 trades, WR 60 %, PF 1.55).  It isolates a single‑source signal, so the concentration risk is known and can be monitored.  
- **Equity:** *ATR‑percentile‑gate* – the only strategy that clears the PF > 1 threshold in production (29 trades, WR 58.6 %, PF 1.10).  Though originally built on crypto data, its volatility‑filter logic is asset‑agnostic and can be re‑trained on equities.  
- **Forex / Futures:** *ATR‑based trend filter* – the only logical extension of the ATR‑gate that can be applied to the thin samples (32 FX, 13 Futures).  It does not yet meet the “PF > 1 & n 