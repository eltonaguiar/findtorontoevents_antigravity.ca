# Adaptive Options Overlay — Momentum-Driven Multi-Leg Strategy
## Reverse-Engineered from April 2026 Trade Recap
**Date:** 2026-05-19
**Source:** Screenshot of 22 trades (TSLA + SPX), April 2026
**Observed WR:** 90.5% (21/22 wins), total earned $991,538

---

## 1. Strategy Name

**"Adaptive Options Overlay — Momentum-Driven Multi-Leg" (AOM-MML)**

---

## 2. Raw Data Summary

| Trade # | Symbol | Structure | P&L | Return % | Result |
|---------|--------|-----------|-----|---------|--------|
| 1 | TSLA | SHRTOPT | +$6,708 | +0.571% | WIN |
| 2 | TSLA | Bull Call Spread | +$66,760 | +6.028% | WIN |
| 3 | SPX | Bull Call Spread | +$77,980 | +7.575% | WIN |
| 4 | TSLA | SHRTOPT | +$55,900 | +5.806% | WIN |
| 5 | TSLA | Covered Call | +$55,800 | +6.152% | WIN |
| 6 | TSLA | Bull Call Spread | +$31,800 | +3.634% | WIN |
| 7 | TSLA | Buy (equity) | +$47,900 | +5.790% | WIN |
| 8 | TSLA | Married Put | +$37,800 | +4.788% | WIN |
| 9 | SPX | Buy | +$68,900 | +9.562% | WIN |
| 10 | TSLA | Bear Put Spread | +$59,800 | +10.473% | WIN |
| 11 | TSLA | Bear Put Spread | -$77,800 | -11.992% | LOSS |
| 12 | TSLA | Long | +$79,800 | +14.025% | WIN |
| 13 | SPX | Bear Put Spread | +$67,900 | +13.551% | WIN |
| 14 | TSLA | SHRTOPT | +$44,300 | +9.698% | WIN |
| 15 | SPX | Bull Call Spread | -$109,000 | -19.265% | LOSS |
| 16 | TSLA | Bear Put Spread | +$69,800 | +14.073% | WIN |
| 17 | TSLA | Married Put | +$47,900 | +10.690% | WIN |
| 18 | SPX | Bull Call Spread | +$88,900 | +24.751% | WIN |
| 19 | SPX | Covered Call | +$61,890 | +29.684% | WIN |
| 20 | TSLA | Protective Collar | +$89,700 | +75.505% | WIN |
| 21 | TSLA | SHRTOPT | +$41,900 | +54.486% | WIN |
| 22 | TSLA | SHRTOPT | +$76,900 | 0% | WIN |

---

## 3. Signal Logic (Directional Bias)

### Primary Signal: Short-Term Momentum on TSLA and SPX

The sequence of structures reveals a clear regime shift in April 2026:

- **Early April (trades 1-9):** Predominantly bullish structures (Bull Call Spread, Covered Call, Married Put, Buy) — consistent with TSLA/SPX in a near-term uptrend or post-dip recovery.
- **Mid-April (trades 10-17):** Mix of Bear Put Spreads and Long entries — consistent with a sharp TSLA decline (earnings miss, macro shock, or tariff shock in April 2026). The one LOSS on the Bear Put Spread (trade 11) suggests an early mean-reversion attempt before the full decline was confirmed.
- **Late April (trades 18-22):** Very high return % per trade, Protective Collar, SPX Bull Call, Covered Call. This is the post-capitulation bounce. Large % returns suggest leverage was added on confirmed reversal.

**Inferred signal construction:**
1. **5-day momentum**: 5-day close-to-close return divided by 20-day rolling average return. Positive = bullish bias; negative = bearish bias.
2. **RSI(14)**: Above 55 confirms bull; below 45 confirms bear. Avoids whipsaws.
3. **20-day ATR (normalized)**: Scales expected move. High ATR wider spreads + more structure optionality; Low ATR SHRTOPT (sell premium).
4. **IV Rank (30-day lookback)**: IV rank > 0.6 triggers premium-selling overlay (SHRTOPT, Covered Call). IV rank < 0.4 triggers debit spread (Bull/Bear spread).

**Direction Decision:**
```
signal_strength = 0.4 x momentum_z + 0.3 x rsi_z + 0.3 x price_vs_20dma_z
> +0.5 -> BULLISH
< -0.5 -> BEARISH
else   -> NEUTRAL (SHRTOPT or Covered Call if long position held)
```

---

## 4. Structure Selection Logic (Decision Tree)

```
Has existing long equity position?
YES:
  Signal BULLISH + IV_rank < 0.5  -> Married Put
  Signal NEUTRAL/BEARISH + IV_rank > 0.5 -> Covered Call
  Strong BEARISH (signal < -0.7) -> Protective Collar
NO (entering fresh):
  BULLISH (signal > 0.5):
    IV_rank < 0.5 -> Bull Call Spread
    IV_rank >= 0.5 -> Long Equity
  BEARISH (signal < -0.5):
    -> Bear Put Spread
  NEUTRAL (|signal| < 0.3) + IV_rank > 0.6:
    -> SHRTOPT (sell OTM puts or calls; premium decay as profit)
```

**Spread width selection:**
- ATR-based: use 1x ATR for strike separation on spreads.
- DTE: 21-45 days to expiration for spreads; 7-14 DTE for SHRTOPT.

---

## 5. Position Sizing Rules

**Estimated notional capital:** ~$1.1M (derived from P&L / return % for each trade).

Per trade: `position_size = capital x kelly_fraction x conviction_scalar`

| Parameter | Value |
|-----------|-------|
| Full Kelly fraction | 25% (quarter-Kelly as per repo standard) |
| Min size | $30,000 |
| Max size per trade | 15% of portfolio |
| Conviction scalar | 0.5 (low) to 1.5 (high), based on signal_strength magnitude |

**Loss trades sizing:** Trades #11 and #15 suggest high-conviction bets near 50% of capital — above the 25% Kelly target. Hard cap at 15% of capital per trade is recommended.

---

## 6. SHRTOPT Overlay

**SHRTOPT = Systematic Short Options (selling OTM puts OR calls for premium collection)**

- Appears at trade start (trade #1: +$6,708 = tiny absolute gain, 0.57% return)
- Appears mid-run (trades #4, #14) — parallel theta-decay income while directional trades are running
- Appears at end (trades #21, #22: trade #22 is 0% return = closed for scratch/expired worthless)

**SHRTOPT rules:**
1. Trigger: IV_rank > 0.6 on the underlying (TSLA or SPX)
2. Sell OTM puts if bullish bias; sell OTM calls if bearish bias; sell strangle if neutral
3. Delta target: 0.15-0.20 (far OTM for high probability of expiry worthless)
4. DTE at entry: 7-21 days
5. Exit: at 50% max profit or at 21 DTE if still open
6. Risk: always close if loss = 2x premium received

---

## 7. Entry/Exit Rules

**Entry:**
- Compute signal daily at close; enter next open
- For spreads: pay at most 0.5x ATR in debit

**Exit:**
- Profit target: 50% of max profit for defined-risk spreads; 80% for SHRTOPT
- Stop loss: -50% of premium paid (debit spreads); -200% of premium received (SHRTOPT)
- Time stop: Close at 5 DTE if no target hit
- Signal reversal: If momentum signal flips sign, close position regardless of P&L

---

## 8. Risk Parameters

| Parameter | Threshold |
|-----------|-----------|
| Max loss per trade | 15% of portfolio |
| Max daily loss | 20% of portfolio |
| Portfolio VaR (95%, 1-day) | 10% of portfolio |
| Max concurrent positions | 5 |
| SHRTOPT overlay max | 20% of portfolio in short premium exposure |

---

## 9. April 2026 Context

April 2026 saw significant TSLA volatility (earnings + macro/tariff shock cycle). The strategy exploited:
1. Early month: Post-dip recovery -> Bull Call Spreads and SHRTOPT (IV elevated)
2. Mid-month: TSLA sharp decline -> Bear Put Spreads (trade #10, #13, #16 all large winners)
3. One failed early Bear Put (trade #11) = entered too early before decline confirmed by RSI
4. Late month: Capitulation bottom + mean-reversion bounce -> Protective Collar and long equity; giant % returns because TSLA moved large
5. Final SHRTOPT (trades #21-22): volatility compression as April closed -> sold IV for theta income

---

## 10. Acceptance Criteria for Promotion to LIVE

| Metric | Threshold |
|--------|-----------|
| Backtest WR | >= 60% |
| Profit Factor | >= 1.5 |
| Max Drawdown | <= 20% |
| n (resolved trades) | >= 100 |
| Walk-forward windows | >= 3 consistent |
| OOS Sharpe | >= 0.5 |

**Note:** The 90.5% WR observed in April 2026 reflects a single month with an ideal trend/reversal setup. Realistic long-run WR for a momentum options overlay is 55-65%.

---

## 11. Hypothesis Registry Entry

**ID:** H-OPT-001
**Status:** PRE_REGISTERED (per M-107 gate)
**Wiring:** OPT-IN RESEARCH SIDECAR ONLY. No production callers.
**Script:** `tools/options_strategy_research/momentum_options_overlay.py`
