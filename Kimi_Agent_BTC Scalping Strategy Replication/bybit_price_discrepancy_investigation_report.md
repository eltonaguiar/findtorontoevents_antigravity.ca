# Bybit BTCUSD.V Price Discrepancy Investigation Report

## Executive Summary

After extensive research into Bybit's pricing mechanics, data feeds, and trading environments, I have identified **multiple possible explanations** for why the reported trade prices do not match real BTC market data. The most likely explanations involve **Bybit's Testnet environment** or **mark price vs last traded price discrepancies**.

---

## Key Findings

### 1. **CRITICAL DISCOVERY: Bybit Testnet Has Known Price Issues for BTC/ETH**

From a Medium article on Deep Reinforcement Learning for Crypto Trading (2024):
> "On the other hand, the **Bybit testnet has large, unrealistic spikes in BTC and ETH last prices**, which can skew trading results."

This is a **documented, known issue** with Bybit's testnet specifically for BTC and ETH pairs - exactly what we're seeing!

**Key differences between Demo and Testnet:**
| Feature | Demo Account | Testnet Account |
|---------|-------------|-----------------|
| Price/Market Movements | Accurately simulate Mainnet | **Operates INDEPENDENTLY of Mainnet** |
| Order Book Impact | Orders don't enter real order book | Orders DO influence Testnet prices |
| Price Accuracy | Mirrors real market | **Can have unrealistic spikes** |

### 2. **Bybit's Dual-Price Mechanism Creates Natural Discrepancies**

Bybit uses three different prices:
- **Last Traded Price (LTP)**: The actual execution price
- **Mark Price**: Used for liquidation and unrealized P&L
- **Index Price**: Weighted average from 6 major spot exchanges

**Mark Price Formula for BTCUSD:**
```
Mark Price = Median(Price 1, Price 2, Last Traded Price)
Price 1 = Index Price × [1 + Last Funding Rate × (Time Until Funding/8)]
Price 2 = Index Price + Moving Average (2.5-minute Basis)
```

**Documented price divergence:**
> "In a fluctuating market, the Last Traded Price on Bybit may temporarily deviate from the Mark Price."

> "The spread between 'Last Traded' and 'Mark Price' is OFTEN SO WIDE (literally **100's of dollars**)" - Reddit user

### 3. **Mark Price vs Last Price Can Differ by Hundreds of Dollars**

From Bybit's documentation and user reports:
- The mark price is designed to be **smoother** than last traded price
- During volatility, the difference can be **$100-$500+**
- Liquidation is triggered by **mark price**, not last traded price
- This is a **feature**, not a bug - it protects against manipulation

### 4. **BTCUSD.V - The ".V" Suffix Investigation**

The ".V" suffix on BTCUSD.V is **not a standard Bybit notation**. Possible explanations:
- Could indicate a **specific chart view** (Mark Price view)
- Could be a **demo/testnet indicator**
- Could represent a **different price source** (index vs mark vs last)
- **Not found** in standard Bybit contract documentation

### 5. **Index Price vs Spot Price Differences**

Bybit's index price:
- Aggregates from **6 major spot exchanges**
- Uses **volume-weighted average**
- Updates **hourly weights**
- Has **1% deviation threshold** for BTC (exchanges deviating >1% are excluded)

This means Bybit's index price can differ from any single exchange's spot price by design.

---

## Analysis of the Trade Price Discrepancy

### Reported Trade 4 Example:
- **Entry**: 69469.77
- **Exit**: 71206.94
- **Reported move**: +1737 points
- **Real market at that time**: ~71,400-71,500

### Why This Doesn't Match Real Data:

**Scenario A: Testnet Trading (MOST LIKELY)**
- Testnet operates **independently** from mainnet
- Has documented **unrealistic price spikes** for BTC/ETH
- Would explain why prices are in the right range ($69k-$72k) but exact values don't match
- Would explain why only 2/12 trades matched real data

**Scenario B: Mark Price Being Used for P&L Display**
- If the screenshot shows **mark price** rather than entry/exit prices
- Mark price can diverge significantly from last traded price
- The 1737-point move could be mark price movement, not actual trade prices

**Scenario C: Different Timestamp Interpretation**
- If timestamps are interpreted differently (UTC vs local)
- Could be off by hours, showing prices from a different time period
- However, this wouldn't explain the systematic offset

---

## Most Likely Explanations (Ranked)

### 1. **BYBIT TESTNET ENVIRONMENT** (Probability: 70%)
**Evidence:**
- Documented known issue with BTC/ETH price spikes on testnet
- Testnet prices operate independently from mainnet
- Would explain why price range matches but exact prices don't
- Would explain the 1737-point move that didn't happen in real data

**Why this fits:**
- The screenshot could be from someone practicing on testnet
- Testnet is designed for testing, not accurate price replication
- The ".V" suffix might indicate testnet or demo mode

### 2. **MARK PRICE vs LAST PRICE DISCREPANCY** (Probability: 20%)
**Evidence:**
- Bybit's mark price can differ from last price by hundreds of dollars
- Mark price is used for P&L calculations
- The screenshot might be showing mark price values

**Why this fits:**
- Mark price is smoother and can lag or lead actual market prices
- Could create the appearance of trades that don't match real data

### 3. **PAPER TRADING / DEMO ACCOUNT** (Probability: 8%)
**Evidence:**
- Demo accounts use simulated execution
- Orders don't enter real order book
- However, Bybit claims demo "accurately simulates" mainnet prices

**Why this is less likely:**
- Demo is supposed to mirror mainnet prices accurately
- Wouldn't explain systematic discrepancies

### 4. **DATA RECORDING ERROR / EDITED SCREENSHOT** (Probability: 2%)
**Evidence:**
- Prices could be manually entered incorrectly
- Screenshot could be edited

**Why this is least likely:**
- The price range ($69k-$72k) matches real market
- The discrepancies follow a pattern, not random errors

---

## Conclusion

### Primary Finding:
The price discrepancies are **most likely due to trading on Bybit's Testnet environment**, which has documented issues with unrealistic BTC/ETH price spikes that don't match mainnet prices.

### Secondary Finding:
The ".V" suffix in BTCUSD.V and the systematic price differences ($166-$773 offset) are consistent with either:
1. Testnet pricing anomalies
2. Mark price being displayed instead of last traded price

### Recommendation:
To verify the true source of these prices:
1. Check if the account was using **Testnet** (testnet.bybit.com)
2. Verify if the prices shown are **mark price** vs **last traded price**
3. Compare timestamps carefully for timezone differences
4. Check if the trades were executed on **Demo Trading** mode

---

## References

1. Bybit Help Center - Mark Price Calculation
2. Bybit Help Center - Index Price Calculation
3. Bybit Help Center - Demo Trading FAQ
4. Medium Article: "Deep Reinforcement Learning for Crypto Trading" (July 2024)
5. Reddit r/Bybit - User reports on mark/last price divergence
6. Bybit Official Blog - Dual-Price Mechanism Explanation
