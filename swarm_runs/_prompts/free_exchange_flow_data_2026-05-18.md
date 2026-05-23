# Research: FREE alternatives to CryptoQuant exchange net-flow data

## Goal
The C-2 / H-018 strategy needs exchange net-flow data — coin/stablecoin transfers
INTO vs OUT OF centralized spot exchanges, per major coin, daily. CryptoQuant
sells this (~$30-200/mo). The operator wants a FREE alternative that is good
enough to backtest and run H-018 (the net-flow cross-sectional spread).

## What the strategy needs (minimum viable feed)
- Per-coin daily exchange inflow and outflow (or just net-flow), for ~10 majors
  (BTC ETH SOL BNB XRP ADA AVAX LINK DOGE LTC).
- At least ~12-18 months of history for a walk-forward backtest.
- Look-ahead-free: each day's value must be knowable at that day's close.
- Exchange-wallet attribution is the hard part — the value is knowing WHICH
  addresses belong to exchanges.

## Questions to answer
1. What FREE sources expose exchange inflow/outflow or exchange-balance change?
   Consider: Glassnode free tier, CryptoQuant free tier, Coinglass API,
   DefiLlama, Dune Analytics (free queries on labeled exchange wallets),
   Arkham Intelligence, Nansen free, Whale Alert, blockchain.com,
   Etherscan/BscScan labeled addresses, Velo, Amberdata free, Santiment free,
   IntoTheBlock, Messari free, Token Terminal, exchange proof-of-reserves feeds.
2. For each candidate: is it truly free? Rate limits? History depth? Does it
   give per-coin exchange flow or only aggregate? API or scrape-only?
3. Is a self-built Dune query on publicly-labeled exchange deposit/withdrawal
   wallets viable and free? What is the effort?
4. Cheapest near-free fallback if nothing is fully free.
5. A concrete recommendation: which free source (or combination) to wire into
   H-018, and the exact data-fetch plan.

## Rules
- Be concrete and current. Name endpoints, rate limits, tiers.
- Distinguish "exchange-attributed net-flow" (what we need) from generic
  on-chain volume (not enough — H-014 already killed that).
- Honest: if no free source truly replaces CryptoQuant, say so and give the
  cheapest path.
