# Topic Deep-Dive: Execution Costs (DeepSeek-Chat) — 2026-05-31

**Topic:** Slippage / market impact / fees for 24-strategy paper-pilot across 8 asset classes
**AI:** DeepSeek (`deepseek-chat`) via api.deepseek.com
**Operator:** zerounderscore@gmail.com
**Context:** 24-strategy paper-pilot harness starts emission 13:30 UTC tomorrow (mine 8 + kilo 8 + zoo 8). 8 asset classes: CRYPTO, EQUITY, FOREX, COMMODITY, ETF, BOND, FUTURES, PREDICTION_MARKETS.

---

## 3-line operator summary

1. **Use one-way cost model** = `spread/2 + commission_bps + impact_bps(notional)`; deduct from raw PnL before any gate check.
2. **bps numbers calibrated to retail (IBKR Pro / Binance VIP0)** — CRYPTO_MAJOR ~12 bps round-trip, CRYPTO_ALTCOIN ~25 bps, EQUITY_SP500 ~2 bps, FOREX_MAJOR ~1 bps, PREDICTION_MARKETS ~120 bps (Polymarket fee dominates).
3. **Market impact is negligible (<0.1 bps) below $10k notional** for liquid assets; only altcoins/small-cap/bonds need the Almgren-Chriss `sqrt(notional/ADV)` term for our $1k–$100k range.

---

## Distilled bullet spec (wire into `docs/PAPER_PILOT_HARNESS.md`)

### Per-side slippage bps (paper-pilot floor)

| Class                | Slippage bps | Notes                       |
|----------------------|--------------|-----------------------------|
| CRYPTO_MAJOR         | 3–5          | Binance/Kraken L2           |
| CRYPTO_ALTCOIN       | 10–20        | Wider spreads               |
| EQUITY_SP500         | 1–2          | Almgren-Chriss              |
| EQUITY_SMALLCAP      | 5–10         | Kissell 2013                |
| FOREX_MAJOR          | 0.5–1        | BIS triennial               |
| FOREX_CROSS          | 2–4          | Retail FX                   |
| COMMODITY_FUTURES    | 2–5          | CME data                    |
| ETF_SPY              | 1–2          | IBKR exec reports           |
| BOND                 | 5–15         | TRACE, illiquid             |
| FUTURES_ES           | 0.5–1        | CME depth                   |
| FUTURES_NQ           | 0.5–1        | CME depth                   |
| PREDICTION_MARKETS   | 10–30        | Polymarket/Kalshi           |

### Fee tiers (use retail Tier-1)

- EQUITY/ETF: $0.0035/share IBKR tiered (~0.5 bps for typical $100 prints)
- CRYPTO: 0.1% maker, 0.1% taker (Binance VIP0) = 10 bps each side
- FOREX: 0.2–0.5 pips (IBKR) = ~0.2 bps notional
- FUTURES: $0.85/contract ES, $2.00 NQ
- BOND: $1 per $1k face = ~10 bps round-trip
- PREDICTION_MARKETS: 1–2% (Polymarket)

### Spread vs commission

**Bundle** for paper pilot. Total one-way = `spread/2 + commission_bps + impact_bps`.

### Market-impact model

Almgren-Chriss (2001) with Kissell (2013) modifications. Impact only kicks in above $10k notional. For our $1k–$100k range, impact is materially zero on liquid assets but matters on altcoins/small-cap/bonds.

`impact_bps = coeff * sqrt(notional_usd / 1e6)`

### Validation rule

Compare modeled cost against IBKR TWS execution reports for first 100 live trades; recalibrate if realized deviates >20%.

---

## Python pseudo-code (drop into harness)

```python
def apply_execution_costs(raw_pnl_bps, asset_class, notional_usd, side):
    """
    Deduct one-way execution costs from raw PnL (bps).
    References:
      - Almgren & Chriss (2001) "Optimal Execution of Portfolio Transactions"
      - Kissell (2013) "The Science of Algorithmic Trading"
      - Cont & Wagalath (2016) "Fire Sales in a Model of Complex Interconnectedness"
    """
    cost_params = {
        'CRYPTO_MAJOR':     {'spread': 4,  'commission': 10,  'impact_coeff': 0.1},
        'CRYPTO_ALTCOIN':   {'spread': 15, 'commission': 10,  'impact_coeff': 0.5},
        'EQUITY_SP500':     {'spread': 1.5,'commission': 0.5, 'impact_coeff': 0.01},
        'EQUITY_SMALLCAP':  {'spread': 7,  'commission': 0.5, 'impact_coeff': 0.1},
        'FOREX_MAJOR':      {'spread': 0.8,'commission': 0.2, 'impact_coeff': 0.005},
        'FOREX_CROSS':      {'spread': 3,  'commission': 0.2, 'impact_coeff': 0.02},
        'COMMODITY_FUTURES':{'spread': 3,  'commission': 1,   'impact_coeff': 0.05},
        'ETF_SPY':          {'spread': 1.5,'commission': 0.5, 'impact_coeff': 0.01},
        'BOND':             {'spread': 10, 'commission': 2,   'impact_coeff': 0.2},
        'FUTURES_ES':       {'spread': 0.8,'commission': 0.3, 'impact_coeff': 0.005},
        'FUTURES_NQ':       {'spread': 1,  'commission': 0.5, 'impact_coeff': 0.008},
        'PREDICTION_MARKET':{'spread': 20, 'commission': 100, 'impact_coeff': 1.0},
    }
    p = cost_params[asset_class]
    spread_cost = p['spread'] / 2
    commission_bps = p['commission']
    impact_bps = 0.0
    if notional_usd > 10_000:
        impact_bps = p['impact_coeff'] * (notional_usd / 1e6) ** 0.5
    total_cost = spread_cost + commission_bps + impact_bps
    return raw_pnl_bps - total_cost
```

**Example:** `apply_execution_costs(50, 'CRYPTO_ALTCOIN', 50_000, 'BUY')` ≈ 50 − (7.5 + 10 + 0.1) ≈ **32 bps net**.

---

## Paper citations (4)

1. Almgren, R. & Chriss, N. (2001) — *Optimal Execution of Portfolio Transactions* — Journal of Risk
2. Kissell, R. (2013) — *The Science of Algorithmic Trading and Portfolio Management* — Academic Press
3. Cont, R. & Wagalath, L. (2016) — *Fire Sales in a Model of Complex Interconnectedness* — Mathematical Finance
4. BIS Triennial Central Bank Survey (FX turnover / spreads benchmarks)

---

## Raw API response

(verbatim from DeepSeek; formatting preserved)

```
## Execution Cost Model for Multi-Asset Paper Pilot

### 1) Slippage Assumptions (bps per side)

| Asset Class | Slippage (bps) | Source |
|---|---|---|
| CRYPTO (major) | 3-5 | Binance/Kraken L2 data |
| CRYPTO (altcoin) | 10-20 | Low liquidity, wider spreads |
| EQUITY (SP500) | 1-2 | Almgren-Chriss (2001) |
| EQUITY (small-cap) | 5-10 | Kissell (2013) |
| FOREX (major) | 0.5-1 | BIS triennial survey |
| FOREX (cross) | 2-4 | Retail FX spreads |
| COMMODITY (futures) | 2-5 | CME data |
| ETF (SPY-grade) | 1-2 | IBKR execution reports |
| BOND | 5-15 | TRACE data, illiquid |
| FUTURES (ES/NQ) | 0.5-1 | CME depth |
| PREDICTION_MARKETS | 10-30 | Polymarket/Kalshi |

### 2) Market Impact Model
Use Almgren-Chriss (2001) with Kissell (2013) modifications for small sizes.
For $1k-100k trades, impact is negligible (<0.1 bps) for liquid assets. Use only for altcoins/small-cap/bonds.

### 3) Fee Tiers
Use retail Tier-1 (IBKR Pro / Binance VIP0):
- EQUITY/ETF: $0.0035/share (IBKR tiered)
- CRYPTO: 0.1% maker, 0.1% taker (Binance)
- FOREX: 0.2-0.5 pips (IBKR)
- FUTURES: $0.85/contract (ES), $2.00 (NQ)
- BOND: $1 per $1,000 face (retail)
- PREDICTION_MARKETS: 1-2% (Polymarket)

### 4) Spread vs Commission
Bundle for simplicity in paper pilot:
- Total cost = Spread/2 + Commission + Impact
- Spread dominates for illiquid assets, commission for liquid

### 5) Production Spec
(See python pseudo-code above.)

Key assumptions for paper pilot:
- All costs are one-way (per trade)
- No slippage from order book imbalance (paper trading)
- Impact only materializes above $10k notional
- Prediction markets use worst-case (Polymarket 2% fee)
- Bond costs reflect retail TRACE execution

Validation: Compare against IBKR TWS execution reports for first 100 trades. Adjust parameters if realized costs deviate >20% from model.
```

---

*Generated 2026-05-31 by Claude Opus 4.7 peer agent. AI source: DeepSeek `deepseek-chat`. Cost: ~$0.002.*
