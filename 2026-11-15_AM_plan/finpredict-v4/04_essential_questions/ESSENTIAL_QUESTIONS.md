# Essential Questions Every Candidate Strategy Must Answer

**Date:** 2026-11-15 (AM)
**Purpose:** A hard checklist to vet any proposed "winning" strategy before it earns capital.

---

## The 12 Gates

1. **What is the economic mechanism?** Why should this persist? (Risk premium, behavioral bias, structural flow — or is it pattern-mining?)
2. **Does it beat the buy-and-hold benchmark after costs?** Not "positive" — beats SPY (equity) / BTC-hold (crypto) / 60-40 (allocation) net of fees.
3. **Is it validated out-of-sample?** Walk-forward, purged CV, untouched OOS. Never in-sample.
4. **What is the effective N?** Not raw rows — correlation-adjusted independent trades. n_eff ≥100 to even look.
5. **What is the DSR / PBO?** If DSR <0.95 or PBO >0.10, it is a multiple-testing artifact.
6. **What are ALL costs?** Spread, slippage, commission, financing/swap. Rerun after costs.
7. **What is the max drawdown and CVaR?** Can the account survive the worst 5%? Is there a stop?
8. **Does it survive regime change?** Test in the worst sub-period (2008, 2020, 2022). If it dies in one regime, it is not robust.
9. **Is there capacity?** Does the edge survive at the size you'd actually trade?
10. **Is the signal truly independent?** Or is it a rehash of an already-dead strategy?
11. **Can it be paper-traded for 90 days?** No exceptions.
12. **What is the kill condition?** Pre-state exactly when you'll stop (PF <1.0 at n=100, breach of DD cap, etc.). If you can't write it, don't deploy.

---

## Prediction-Market Specific (Kalshi/Polymarket)

- Why is copy-trading there consistently failing? (See PREDICTION_MARKETS_WHY_NO_WINNERS)
- What is the adverse-selection / bot fraction in the market you're copying?
- Are you paying fees + spread that exceed the copied edge?
- Is your size comparable to the copied trader's (edge may not scale)?

---

## The "Trust" Questions (from institutional research)

- Can an independent auditor reproduce your track record from raw data?
- Do you publish benchmark-relative attribution (alpha vs beta)?
- Are your incentives aligned (skin in the game, high-water marks)?
- Do you explain drawdowns in process terms instead of hiding them?

---

*If a strategy cannot pass these 12 + trust questions, it is research, not deployable.*
