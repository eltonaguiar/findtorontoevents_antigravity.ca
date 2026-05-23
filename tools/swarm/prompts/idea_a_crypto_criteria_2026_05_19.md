# IDEA-A: Proven CRYPTO Criteria Research — Academic + Practitioner

## Context

We run a multi-asset algorithmic trading system. CRYPTO asset class is currently sub-Tier-2:
- WR=44.6%, PF=1.25, n=8067
- Key drag: `quan_engine` 18% volume @ PF=0.70 and `unknown` 7% @ PF=0.35
- Elite strategies show PF=2.34–3.97 but are diluted by high-volume underperformers
- Target: WR>50%, PF>1.5 (Tier-2), PF>2.0/WR>55% (Tier-1, Renaissance target)
- Hold period: 5–30 days forward returns

We need to enumerate **proven, academically-grounded criteria** for CRYPTO that can be wired
into `calculate_smart_score()`, used as pick gates, or applied as signal filters.

## Existing criteria to EXCLUDE (already implemented)

Do NOT suggest any of the following — they are already wired:
- Funding rate directional signals (already gated)
- On-chain transaction counts / active address counts
- Exchange net-flow (inflow/outflow) signals
- COT (Commitment of Traders) — not applicable to crypto
- Roll yield (futures-specific, not in scope)
- Price/volume momentum (already in multiple strategies)
- Confidence threshold gates (M-034, M-035 live)
- ML gradient boost score (already in pipeline)

## Research Task

Enumerate the **top 10 proven criteria** from academic literature and practitioner research
that predict 5–30 day forward returns for CRYPTO assets, where:

1. Data is available via FREE public sources:
   - Binance public REST API (no auth required): klines, ticker, depth, trades
   - CoinGecko free tier: market cap, volume, developer stats, social stats
   - yfinance: BTC/ETH index proxies, cross-asset correlations
   - On-chain free tiers: Glassnode free, CryptoQuant free, Dune Analytics free queries
   - Alternative.me Fear & Greed Index (free API)

2. NOT already in our system (see exclusion list above)

3. Ranked by: (expected WR lift × data availability × implementation simplicity)
   - Top 3 MUST be immediately implementable with free APIs, complexity ≤ 3

For each criterion provide:

### Criterion Format

**Name**: [criterion name]
**Mechanism**: [1–2 sentence explanation of why this predicts returns]
**Academic Reference**: [paper/author/year — if none, cite practitioner source]
**Data Source**: [exact API endpoint or free data source]
**Implementation Complexity**: [1=trivial, 2=easy, 3=moderate, 4=hard, 5=research-grade]
**Expected WR Lift**: [estimate in percentage points vs baseline, cite source if known]
**Wire-In Point**: [smart_score boost | gate | filter | signal source | new strategy]
**Free API Feasibility**: [yes/partial/no — explain if partial]

## Wire-In Architecture (for reference)

Our system's pick scoring pipeline (most relevant hooks):
- `alpha_engine/quality_gates.py` → `passes_active_gate()` / `passes_smart_gate()` — binary gates
- `alpha_engine/smart_picks_engine.py` → `calculate_smart_score()` — composite score 0–1
- `alpha_engine/production_scanner.py` — upstream signal generation
- `audit_trail/quality_gates.py` → gate registry with shadow mode support
- New hypothesis slots: H-009 through H-018 available in hypothesis registry

## Focus Areas (prioritized)

Research especially these underexplored CRYPTO-specific factors:

1. **Market microstructure**: bid-ask spread dynamics, order book imbalance persistence
2. **Cross-asset momentum spillover**: BTC dominance changes → altcoin return predictability
3. **Social sentiment**: Reddit/Twitter sentiment scores → next-week drift (not raw counts)
4. **Miner behavior proxies**: hash rate momentum, difficulty adjustment cycle effects
5. **Liquidity premium**: illiquidity-adjusted returns (Amihud ratio adapted for crypto)
6. **Weekend effect / calendar anomaly**: day-of-week patterns in crypto that survive 2020+
7. **Volatility regime**: realized vol percentile → mean reversion vs trend continuation
8. **Stablecoin market cap growth**: USDC/USDT supply expansion as risk-on proxy
9. **Derivatives market structure**: open interest trend (not funding rate direction)
10. **Cross-exchange price divergence**: arbitrage gap persistence as leading indicator

## Output Format

Rank all 10 by (expected edge × data availability × implementation simplicity).
Top 3 must be immediately free-API implementable (complexity ≤ 3).
For criteria 4–7: acceptable if complexity ≤ 4.
For criteria 8–10: may require moderate engineering (complexity ≤ 5).

After the ranked list, provide a **consensus recommendation**: if you had to pick ONE
criterion to implement first for maximum WR lift with minimum implementation cost, which
would it be and why?
