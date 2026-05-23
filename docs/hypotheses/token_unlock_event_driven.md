# S0 Hypothesis — Token Unlock Event-Driven Strategy

**Status:** S0 (hypothesis only). No live emission until S4.
**Tier:** 1, Rank #1 (Strategy Factory v1.1)
**Owner:** alpha_engine/strategies/token_unlock_event_driven.py
**Date:** 2026-04-18

## 1. The Inefficiency

Crypto token unlocks mechanically increase circulating supply on a pre-announced
schedule. Vesting recipients (early investors, team, foundation) have a cost
basis near zero and a documented tendency to sell at or shortly after cliff /
linear-release events. The supply shock is:
- **Scheduled** (known months in advance)
- **Quantifiable** (exact token count, recipient class)
- **Mechanically unavoidable** (on-chain contract releases are not discretionary)

Despite being public information, empirical studies (Keyrock 2023, Glassnode
2024, and the source claim in `GITHUB_CLOUDAGENT_STRATS.MD` C5: ~-4% CAR in
pre-unlock window) suggest the effect is not fully priced in at retail scale,
particularly for mid-cap tokens with thin perp markets.

## 2. Why Now

- `tokenunlocks.app` exposes a free, machine-readable calendar (post-2023).
- Perp liquidity on Binance/Bybit for top-100 alts is sufficient to trade
  $10k-$100k clips without slippage dominating signal.
- Retail flow is concentrated in narrative/meme trades, not structural supply
  events — the edge is not saturated.
- On-chain vesting contracts (most use standard OZ `VestingWallet` or
  Sablier/Hedgey) are programmatically classifiable.

## 3. What Beats Random — Concrete Predictions

The hypothesis makes three falsifiable predictions:

1. **Large-unlock short (>5% of circulating float):** SHORT entry T-72h,
   exit T+24h, produces negative CAR (target: ≤ -3%) with bootstrap
   p < 0.05 across n≥30 events.
2. **Investor-tier vs team-tier asymmetry:** Unlocks flagged `investor`
   produce deeper negative CAR than `team`-tier (team often has off-market
   OTC agreements; investors sell on-market).
3. **Small investor-tier unlock reversal (<2% of float):** post-event
   relief bounce — LONG T+0h to T+48h — positive CAR (target: +1.5%).

## 4. Null Hypotheses To Rule Out

- **H0a — Efficient Markets:** price fully impounds the scheduled release
  by T-7d; residual CAR is noise.
- **H0b — Front-run already priced:** smart money sells at T-7d to T-72h;
  by T-72h the move is done, retail has no remaining edge.
  **This is the riskiest null** — if pre-emption > 30% of total CAR, strategy dies.
- **H0c — Effect too heterogeneous:** CAR variance is so wide across token
  categories (L1 vs DeFi vs gaming vs meme) that position sizing cannot
  compensate; Sharpe on unscaled portfolio < 0.5.
- **H0d — Liquidity illusion:** edge exists only on sub-$500M mcap names
  where execution cost eats the alpha.

## 5. Data Sources

- **Primary:** tokenunlocks.app public JSON calendar (free tier).
- **Secondary:** CryptoRank vesting API (free, rate-limited).
- **On-chain truth:** Etherscan / Arbiscan contract reads on known
  vesting addresses (Sablier, Hedgey, OZ VestingWallet).
- **Price data:** Binance spot + perp OHLCV via existing
  `alpha_engine/data/` ingestion (failover chain mandated by CLAUDE.md).
- **Benchmark:** BTC 1h returns as market-neutral benchmark for CAR.

## 6. Universe

- Top 100 tokens by market cap with:
  - listed Binance perp (for shorting)
  - ≥ $20M 24h perp volume (30d median)
  - public vesting schedule on tokenunlocks.app
- Excluded: stablecoins, wrapped assets, LSDs, tokens with < 180d trading history.
- Estimated eligible universe: 40-60 names.

## 7. Holding Period & Risk

- **Entry:** T-72h before unlock block-time.
- **Exit:** T+24h or tightened stop, whichever first.
- **Risk per trade:** 0.5% of account equity (hard cap).
- **Stop-loss:** 1.5× ATR(24h) from entry.
- **Pyramiding:** none.
- **Concurrency cap:** 3 concurrent event positions (diversification; most
  weeks have 5-15 eligible unlocks).
- **Correlation filter:** skip new signal if already holding a position in
  an asset with 30d return-correlation > 0.7 vs the candidate.

## 8. S1 Gate Criteria

Event-study calibration (see `docs/event_studies/token_unlock_calibration_plan.md`)
must produce:
- n ≥ 30 historical events per tested cohort
- bootstrap 95% CI on mean CAR excludes zero
- pre-emption share of total CAR < 30%
- liquidity-filtered subset still passes (no survivorship via illiquid tail)

If any gate fails → back to S0 or archive.
