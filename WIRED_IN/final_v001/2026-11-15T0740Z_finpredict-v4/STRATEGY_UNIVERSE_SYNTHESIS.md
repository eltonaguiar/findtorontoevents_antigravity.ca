# STRATEGY_UNIVERSE_SYNTHESIS — 700+ strategies, graveyard lessons, and what they imply

**Folder**: `WIRED_IN/final_v001/2026-11-15T0740Z_finpredict-v4/`
**Sources**: `docs/ALL_STRATEGIES.md` (700+ strategies across 15+ systems), `baby_strategies/STRATEGY_GRAVEYARD.md`, `BABY_STRATEGIES_AUDIT_INTEGRATION.md`, `baby_strategies/NEW_STRATEGY_VARIATIONS_V2.md`.

## 1. The scale of the problem (multiple-testing)

The repo contains **700+ individual strategies** plus thousands of meta-permutations (genetic/evolution engines, 600-variant library, 320+ incubator strategies). This is the textbook setting for multiple-testing inflation.

**Direct evidence of the pathology:**
- The DARWIN/GP evolution engine reports all-time records such as **Sharpe 95–97** and **WR 90.5%** on SOLUSDT SHORT (runs #25, #31, #32). These are **impossible after any honest multiplicity correction**. A Sharpe of 95 with look-ahead-free, cost-adjusted, corrected data is not a real feature of a tradeable market. These are overfit artifacts of evolutionary search.
- The project's own audit already showed **0/37 strategy×symbol combos passed all 7 gates** in independent simulation, and **0/23 hypotheses survived clean OOS** in the peer final plan.
- The `ALL_STRATEGIES.md` "statistically proven winners" table (Connors RSI-2 75.7% on SPY, etc.) are single-test, uncorrected claims; the clean OOS harness does NOT confirm them as money-ready.

**Conclusion**: the high-Sharpe / high-WR entries in the catalog are not evidence of edge; they are evidence of **selection bias**. They must never be used to justify live sizing.

## 2. Graveyard lessons (long-run empirical ground truth)

From `STRATEGY_GRAVEYARD.md` (72 graveyarded strategies, forward-Kelly audited):

1. **OHLCV proxies for microstructure do not work** — order flow, delta, liquidity signals approximated from candles have near-zero predictive power.
2. **Complex regime detection overfits** — HMM, GARCH, variance-ratio all failed; simple SMA/ADX regime filters outperform.
3. **More parameters = more overfitting** — graveyard is full of 5+ parameter strategies; survivors have 2–3 max.
4. **Variant proliferation is wasteful** — 10 near-identical variants don't improve odds; if the core signal is weak, no parameter set saves it.
5. **Mean reversion works; most other things don't** — 100% of surviving strategies were mean-reversion based (crypto retail overreaction).
6. **Kelly fraction from FORWARD trades is the ground truth** — backtest Sharpe/WR can be gamed; negative Kelly after 10+ real trades = dead.

**Implication for the final strategy**: prefer **simple, low-parameter, forward-validated** rules. Reject anything that requires many tuned parameters or exotic regime models to "work."

## 3. The baby-strategy integration (audit wiring)

`BABY_STRATEGIES_AUDIT_INTEGRATION.md` shows the audit DB (strategy registry, backtest runs, strategy stats) already exists and tracks baby strategies by WR/Sharpe/trades/fitness, with a **banned** tier for catastrophic strategies (e.g., `PriceRocMeanReversion` banned: WR 45%, Sharpe −4.20 on 573 trades). The **bundle** of low-correlation survivors reported combined Sharpe ≈ 4.0, avg WR ≈ 55%, max DD <15%.

**Caveat**: bundle "Sharpe 4.0" is a backtest figure, not a proof-gated forward result. It is a candidate for the forward clock, not a proven claim.

## 4. What this changes in the finalized strategy

| Prior decision | Updated by universe synthesis |
|---|---|
| BTC/GLD sma200 are the only wealth-beating candidates | Unchanged — but now strongly supported: they are **simple, low-parameter, benchmark-relative**, matching graveyard lesson 3/4/6. |
| vwap-reversion-scout is the equity forward-alpha candidate | Reinforced — it is a **mean-reversion** signal (graveyard lesson 5), low parameter count, and already has a pre-registered clock. |
| Reject TLT/BND, forex (data), prediction markets | Unchanged. |
| Do not chase high-Sharpe catalog entries | **NEW, explicit**: DARWIN/GP Sharpe-95 artifacts are rejected as overfit; no forward clock for them. |
| Bundle (low-correlation mean-reversion survivors) | **NEW**: add the baby-strategy **bundle** as a candidate for the forward clock only (not a proof claim). |

## 5. Final candidate set (post-synthesis)

| Candidate | Class | Type | Why it survives the universe screen |
|---|---|---|---|
| BTC sma200 | Crypto | trend/regime | simple, low-param, benchmark-relative wealth beat |
| GLD sma200 | Commodity | trend/regime | simple, low-param, wealth beat (1% margin gate) |
| vwap-reversion-scout | Equity | mean-reversion | graveyard lesson 5; forward clock running |
| Mixed Faber sleeve | Multi | tactical-beta | baseline benchmark; beats SPY on wealth+Sharpe |
| Baby mean-reversion bundle | Crypto | bundle | low pairwise corr, forward-clock candidate only |

**Explicitly NOT candidates**: any DARWIN/GP/evolution artifact, any >3-parameter rule, any OHLCV-microstructure proxy, any HMM/GARCH regime model, any uncorrected high-WR table entry.

---

## 6. Rule reminder
A claim from the universe (any of the 700+) is not a "strategy" until it has a clean OOS, cost-adjusted, benchmark-relative backtest **and** a pre-registered forward clock. The universe is a search space, not a results page.
