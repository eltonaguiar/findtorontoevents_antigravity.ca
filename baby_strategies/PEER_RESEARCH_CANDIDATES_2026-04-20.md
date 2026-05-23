# Baby-tier candidates from peer research (2026-04-20)

Seeded during cycle-6 perf-review. Goal: stage high-conviction peer-proposed
strategies in the baby tier so any rockstar alpha gets forward-tested before
being lost.

## Duplicate audit — DO NOT re-implement

Peer proposal | Existing baby file(s) | Status
---|---|---
Antigravity §17.1 BB Squeeze Breakout | `bb_squeeze_breakout.py`, `bollinger_squeeze_stochastic_breakout.py`, `carter_squeeze_breakout.py`, `keltner_momentum_squeeze.py`, `prop_scalper_bb_squeeze.py`, `rsi2_bb_squeeze.py` | Saturated (6 variants)
Antigravity §17.2 Connors RSI(2) | `connors_rsi2.py`, `connors_rsi2_mean_reversion.py` | Saturated (2 variants)
Antigravity §17.7 VIX Spike MR | `equity_vix_regime_momentum.py` | Partial overlap — different mechanism (regime vs panic spike); SKIP for now, equity data path unclear
Kimi V3 Funding Term-Structure Divergence (single-name) | `funding_rate_mean_reversion_v1.py`, `mercury_funding_enhanced.py` | Covered in single-name variant

## Added this PR

- [x] **`cross_sectional_crypto_carry.py`** — quintile spread carry (long bottom-funding, short top-funding). ChatGPT §206 + Kimi V3. Distinct from existing single-name funding strategies (cross-sectional ≠ mean-reversion).

## Candidates NOT added (data-path dependencies flagged)

Order within each bucket: simplest to implement first.

### Crypto-only (data available, safe to add next)

- **Protocol Revenue Yield Discounting** (Kimi V3 DeFi) — requires per-protocol revenue feed (DefiLlama API). Sharpe 1.5 claimed. Blocked on: adding revenue scraper.
- **Gas Fee Momentum** (Kimi V3) — if gas spikes persist 3+ blocks, buy BTC/ETH. Blocked on: Ethereum RPC feed.
- **Dark Pool Midpoint Peg Capture** (Kimi V3 microstructure) — HFT-tier, Sharpe 3.5 claimed but requires order-book depth and sub-minute rebalance. Out of scope for current 4h-8h pipeline.

### Equity / ETF / bond (blocked on data scoping)

- **QMJ — Quality Minus Junk** (ChatGPT §201, AQR) — needs balance-sheet fundamentals (ROE, debt, accruals). Blocked on: fundamentals feed.
- **Cochrane-Piazzesi bond risk premia** (ChatGPT §202) — needs 1-5yr Treasury yield curve. Blocked on: FRED API wiring.
- **TLT Momentum + Seasonality** (Antigravity §17.6) — needs TLT daily OHLCV + seasonality table. Blocked on: bond ETF data path.
- **Adaptive Asset Allocation** (Antigravity §17.5) — multi-ETF momentum + min-variance weights. Blocked on: multi-ETF feed + solver dependency.
- **Corporate Bond Value** (ChatGPT §205) — corporate bond yield spread cross-section. Blocked on: bond index data.
- **Opportunistic Insider Cluster Alpha** (Kimi V3) — needs SEC Form 4 feed. Blocked on: EDGAR parser.
- **Factor Crowding Rotation** (Kimi V3) — needs Fama-French factor data. Blocked on: French library data path.
- **MBS Prepayment Speed Momentum** (Kimi V3) — needs MBS yield data. Blocked on: exotic data feed.

### FX / commodity (blocked on TradFi data)

- **London Breakout 7-8** (Antigravity §17.3) — FX range breakout. Blocked on: FX tick or 1m OHLCV feed.
- **Currency Momentum 12-month** (ChatGPT §203, BIS) — FX cross-sectional 12m return. Blocked on: FX daily feed.
- **Tokyo Fix Squeeze** (Kimi V3) — JPY crosses 9:55-10:00 Tokyo. Blocked on: FX tick data.
- **Oil Inventory Surprise** (Antigravity §17.4) — EIA weekly inventory vs consensus. Blocked on: EIA + forecast consensus feed.
- **Commodity Momentum + Term Structure** (ChatGPT §204) — futures cross-section. Blocked on: commodity futures feed.
- **Gold Lease Squeeze Capture** (Kimi V3) — gold lease rate spike. Blocked on: LBMA data.

### Rate / volatility

- **SOFR Futures Term Structure Carry** (Kimi V3) — SOFR curve slope. Blocked on: CME SOFR feed.
- **Systematic Call Overwrite Harvester** (Kimi V3 options) — index options write. Blocked on: options chain feed.

## Recommendation

1. **Prioritize crypto-native strategies first** — data is already plumbed. Next candidates: Protocol Revenue (needs DefiLlama scraper, moderate effort) and any other Kimi V3 on-chain idea with existing data.
2. **For equity/bond/FX**, scope a shared "TradFi data feed" workstream rather than per-strategy scrambling. One yfinance/FRED/EDGAR bundle unlocks ~8 candidates at once.
3. **Graduation criteria** (agreed protocol): min 60 days paper, Sharpe > 0.6, max DD < 12%. Any baby that hits these moves to the main pipeline. Any that underperforms after 90 days gets archived to `STRATEGY_GRAVEYARD.md`.
