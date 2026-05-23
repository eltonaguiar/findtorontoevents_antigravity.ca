# HyroTrader position sizes — reference

**Use with:** [`HYROTRADER_CHALLENGE_STRATEGY.md`](./HYROTRADER_CHALLENGE_STRATEGY.md)

All dollar amounts below are **USDT**. **Recalculate** size whenever entry price, stop %, or equity changes.

---

## Universal formula

```
Risk$        = Account × risk_per_trade_pct        (e.g. 5000 × 0.0075 = 37.50)
Position     = Risk$ / (EntryPrice × StopFraction)   (StopFraction = 0.02 for 2% stop)
Notional     = Position × EntryPrice
```

**Trailing drawdown:** equity peaks ratchet your loss allowance. Size so one stop-out does not consume the whole daily or max trail budget.

---

## 1-step vs 2-step (typical Hyro-style framing)

| | **1-step** | **2-step** (your program) |
|---|------------|---------------------------|
| Profit target | Often **10%** single phase | **10%** phase 1, then **5%** phase 2 |
| Daily DD | Often **tighter** (e.g. 4%) | Often **5%** |
| Max DD | Often **tighter** (e.g. 6%) | Often **10%** |
| Suggested risk/trade | **0.50%** (less room) | **0.75%** |

Confirm percentages on your Hyro contract — firms change labels.

---

## Active profile: **5,000 USDT · FREE TRIAL · futures · trailing** (Hyro UI)

| Line item | USDT | Notes |
|-----------|------|--------|
| **Risk per trade (0.75%)** | **37.50** | Hard cap risk at stop |
| **Profit target** | **+250** | **+5%** — Hyro “Profit” meter |
| **Drawdown limit** | **−250** | **5%** trail — same magnitude as profit goal |
| **Max loss** | **−500** | **10%** trail from peak |
| **Min trading days** | **5** | T-Days on dashboard |
| **Soft daily stop** | **−125** | −2.5% → no new trades |
| **Hard daily** | **−250** | Match Hyro DD meter — flat for the day |

**Discipline (5K trial):**

- Max **2–3** trades/day; after **2** losses, done for the day.
- After **+75 USDT** (~+1.5%), consider standing down — trailing DD eats give-back.
- **SL before entry.** Flat before sleep if overnight volatility threatens trailing peak.

**Paid “two-step” later:** profit steps may differ from this trial — re-read meters.

---

## Illustrative crypto sizes (5,000 USDT, 0.75% risk = **37.50 USDT**)

Plug **your** live `Entry` and `Stop%`. Examples use round numbers only for arithmetic — **not** live quotes.

| Instrument | Example entry | Stop % | Stop $ per unit | **Contracts** (= 37.50 / stop$) |
|------------|---------------|--------|-----------------|-----------------------------------|
| BTCUSDT | 68,000 | 2.0% | 1,360 | **0.0276** BTC |
| BTCUSDT | 68,000 | 2.2% | 1,496 | **0.0250** BTC |
| ETHUSDT | 2,000 | 2.0% | 40 | **0.9375** ETH |
| ETHUSDT | 2,000 | 5.8% | 116 | **0.323** ETH |
| SOLUSDT | 90 | 6.7% | 6.03 | **6.22** SOL |
| XRPUSDT | 2.00 | 5.6% | 0.112 | **335** XRP |

Higher **stop %** ⇒ **smaller** position for the same **37.50** risk.

---

## Quick copy block ($5K FREE TRIAL, Hyro UI)

```
Account:     5,000 USDT
Type:        FREE TRIAL · futures · trailing
Risk/trade:  37.50 USDT (0.75%)
Profit:      +250 USDT (+5%)
DD limit:    -250 USDT (trail)
Max loss:    -500 USDT (trail)
T-days:      min 5
Daily soft:  -125 USDT → no new trades
```

---

## Next phase (if Hyro adds a second funded step)

Re-read meters; many traders drop to **~0.50%** (**25 USDT**/trade) until targets are clear.

---

*Not financial advice. Confirm all thresholds with HyroTrader’s current rule PDF / dashboard.*
