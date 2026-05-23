# One Strong Strategy Per Asset Class — Curated Proposal

**Date:** 2026-04-20
**Source:** Synthesis of (a) cycle 1-4 perf-review findings (PRs #257/#258/#261/#272), (b) KIMI_STRATS.MD review, (c) ANTIGRAVITY_STRATS.MD P0 list, (d) CHATGPT_STRATS.MD §161-200 protocol-grade picks
**Filter:** strategy must have (1) implementable today using existing repo data, (2) high mechanical trigger rate, (3) clear edge supported by ≥2 of the 4 strategy docs, (4) addresses a diagnosed cycle 1-4 bottleneck

---

## Why these 6 (not 600)

Cycles 1-4 of the recurring 8h perf-review (cron `870f36b0`) converged on three diagnostic findings:

1. **Strategy trigger rate is the bottleneck** for non-crypto. Commodities Agent fired 24 symbols × 6 strategies → 1 raw pick. Adding 600 templated strategies that fire <1% won't help.
2. **Broad alt-coin regime drain** (cycle 4): 8 symbols simultaneously losing across 7-10 strategies each. Suggests strategies aren't regime-aware.
3. **High-conviction picks just got their first symbol-quality flags** (DOGEUSDT, cycle 4). Active gate needs symbol-WR check.

**The 6 picks below are chosen for HIGH MECHANICAL TRIGGER RATE + asset-class fit + regime-awareness.** They directly attack the bottleneck rather than padding the catalog.

---

## 1. CRYPTO — Funding-Rate Mean Reversion with Regime Gate

**Source:** repo already has funding data; concept appears in KIMI §4.6 + CHATGPT #186 + ANTIGRAVITY DeFi-Native section
**File:** new `alpha_engine/strategies/crypto_funding_mean_reversion.py` (or fold into `funding_rate_arb.py`)
**Edge:** When perpetual funding rate is in extreme decile, retail leverage is over-positioned; a 4-12h reversion is mechanical.

**Signal:**
```python
def signal(symbol, funding_history_30d, btc_4h_trend):
    fr = current_funding_rate(symbol)
    fr_pct = percentile_rank(fr, funding_history_30d)
    
    # REGIME GATE — directly addresses cycle 4 alt drain finding
    if btc_4h_trend == "RED" and fr_pct < 95:
        return None  # only counter-trend SHORTs in red regime
    
    if fr_pct >= 95:
        return {"direction": "SHORT", "confidence": 0.7, "horizon_h": 8}
    if fr_pct <= 5 and btc_4h_trend != "RED":
        return {"direction": "LONG", "confidence": 0.7, "horizon_h": 8}
    return None
```

**Parameters:** funding history window 30d; extreme decile = 95th/5th pct; horizon 8h
**Risk:** TP +1.5%, SL -1%, time exit 12h
**Trigger rate estimate:** ~5-10% of crypto symbols/day (mechanical thresholds, not waiting for confluence)
**Why this over alternatives:** the **regime gate** specifically addresses cycle 4's alt-drain pattern (LONG-only sources lost massively on AVAXUSDT/ADAUSDT/SUIUSDT during BTC weakness)

---

## 2. EQUITY — Overnight vs Intraday Return Decomposition

**Source:** KIMI §5.12 (most-cited cross-asset risk premium); academic ref: Lou, Polk & Skouras (2019)
**File:** new `alpha_engine/strategies/equity_overnight_intraday_decomp.py`
**Edge:** US equity overnight returns are persistently MOMENTUM (positive autocorrelation), intraday returns are persistently REVERSAL (negative autocorrelation). Two distinct alphas in the same OHLC.

**Signal:**
```python
def signal(symbol, ohlc_30d):
    last = ohlc_30d.iloc[-1]
    prev = ohlc_30d.iloc[-2]
    overnight = (last["open"] - prev["close"]) / prev["close"]
    intraday = (last["close"] - last["open"]) / last["open"]
    
    # Overnight momentum: positive ON return → LONG next day
    if overnight > 0.005:  # 50bps
        return {"direction": "LONG", "confidence": 0.65, "horizon_h": 18}
    # Intraday reversal: large negative intraday → LONG next day (gap up bounce)
    if intraday < -0.02:  # -2%
        return {"direction": "LONG", "confidence": 0.6, "horizon_h": 6}
    return None
```

**Parameters:** thresholds 50bps overnight / -2% intraday
**Risk:** TP +1.5%, SL -1.5%, time exit at next day's close
**Trigger rate estimate:** 30-50% of EQUITY_SYMBOLS daily (will FIX equity's current 0/40 active picks problem from cycle 3 diagnostic)
**Data:** pure OHLC — no new feed. Already in `audit_trail/data/stock_prices.json`.
**Why this over alternatives:** unique convergent signal (KIMI tier-A, ChatGPT high-volume, well-studied academic anomaly), HIGH trigger rate (the actual non-crypto bottleneck), no ambiguity in implementation.

---

## 3. FOREX — Currency Carry with DXY-Regime Filter

**Source:** KIMI §5.3 + CHATGPT carry, regime filter from ANTIGRAVITY P0 Cu/Au-style ratio thinking
**File:** new `alpha_engine/strategies/forex_carry_dxy_filter.py`
**Edge:** Long high-rate currencies + short low-rate currencies works — UNLESS USD is strengthening sharply (carry trades unwind first in USD-up regimes). Add the DXY filter and you avoid the catastrophic unwinds.

**Signal:**
```python
def signal(forex_universe, rate_table, dxy_20d):
    # DXY trend filter — kills the worst carry-unwind period
    dxy_slope = linear_regression_slope(dxy_20d)
    if dxy_slope > 0.001:  # USD strengthening sharply
        return None  # skip carry trades
    
    # Sort by interest rate differential
    pairs = sorted(forex_universe, key=lambda p: rate_diff(p, rate_table))
    long_pair = pairs[-1]   # highest rate diff
    short_pair = pairs[0]   # lowest rate diff
    
    return [
        {"symbol": long_pair, "direction": "LONG", "confidence": 0.65, "horizon_d": 7},
        {"symbol": short_pair, "direction": "SHORT", "confidence": 0.65, "horizon_d": 7},
    ]
```

**Parameters:** weekly rebalance; DXY slope window 20d, threshold 0.1%/d
**Risk:** TP +1%, SL -0.5%, weekly exit
**Trigger rate estimate:** weekly emission, 100% trigger when DXY filter passes
**Data:** existing `FOREX_SYMBOLS` + central-bank rates (already pulled by `kalshi_signals.py`)
**Why this over alternatives:** FX is currently losing money in repo. The DXY filter is the SINGLE addition that flips most carry-trade catastrophes into break-even.

---

## 4. COMMODITY — Roll Yield Harvesting

**Source:** KIMI §2.6 — **the #1 quick win across all reviews**
**File:** new `alpha_engine/strategies/commodity_roll_yield.py` (or fold into `commodities_strategies.py`)
**Edge:** Backwardated commodity futures earn positive carry as front-month rolls toward spot; contangoed earn negative. Monthly cross-sectional rank → long top quintile backwardation, short top quintile contango.

**Signal:**
```python
def signal(commodity_universe):
    rolls = []
    for sym in commodity_universe:
        f1 = front_month_price(sym)
        f2 = next_month_price(sym)
        if f1 is None or f2 is None:
            continue
        days = days_to_expiry(sym, contract=2) - days_to_expiry(sym, contract=1)
        roll_yield = ((f1 - f2) / f2) * (365 / days)
        rolls.append((sym, roll_yield))
    
    rolls.sort(key=lambda x: x[1], reverse=True)
    n = len(rolls)
    quintile = max(1, n // 5)
    
    longs = [{"symbol": s, "direction": "LONG", "confidence": 0.7, "horizon_d": 30}
             for s, _ in rolls[:quintile]]
    shorts = [{"symbol": s, "direction": "SHORT", "confidence": 0.7, "horizon_d": 30}
              for s, _ in rolls[-quintile:]]
    return longs + shorts
```

**Parameters:** quintile rank, monthly rebalance, 30d horizon
**Risk:** TP +5%, SL -3%, monthly exit
**Trigger rate estimate:** **fires on every roll cycle = monthly emission across full commodity universe** — directly fixes cycle 1's "1 raw pick from 24 symbols" Commodities Agent starvation
**Data:** existing yfinance multi-contract fetch (already used by commodity-agent.yml). Need front + next-month series.
**Why this over alternatives:** **Ships the only profitable non-crypto class.** Commodities is at 55.6% WR / PF 1.06 today; roll yield is the textbook commodity alpha and will roughly double the trigger rate. Multiple reviews converge on this.

---

## 5. BOND — Yield Curve Steepener (2s10s)

**Source:** KIMI §2.1 + ANTIGRAVITY P0 (already partially wired per their notes) + repo already has TLT/IEF/ZN/ZT in `BOND_SYMBOLS`
**File:** new `alpha_engine/strategies/bond_yield_curve_steepener.py` (or fold into `bond_strategies.py`)
**Edge:** When 2s10s spread is in extreme tight decile AND Fed-funds-futures price cuts, yield curve historically steepens over 30-90d.

**Signal:**
```python
def signal(rates_history_5y, fed_funds_futures):
    spread = current_2s10s_spread(rates_history_5y)
    spread_pct = percentile_rank(spread, rates_history_5y["spread"])
    
    # Fed-funds-futures direction: are markets pricing cuts?
    ffr_direction = fed_funds_curve_slope(fed_funds_futures)
    
    if spread_pct <= 10 and ffr_direction < 0:  # extreme tight + cuts pricing
        # Steepener trade: long ZT (2y), short ZN (10y) via TLT proxy
        return [
            {"symbol": "TLT", "direction": "SHORT", "confidence": 0.7, "horizon_d": 60},
            {"symbol": "IEF", "direction": "LONG", "confidence": 0.7, "horizon_d": 60},
        ]
    if spread_pct >= 90 and ffr_direction > 0:  # extreme wide + hikes
        return [
            {"symbol": "TLT", "direction": "LONG", "confidence": 0.7, "horizon_d": 60},
            {"symbol": "IEF", "direction": "SHORT", "confidence": 0.7, "horizon_d": 60},
        ]
    return None
```

**Parameters:** 5y history window for percentile, decile thresholds, 60d horizon
**Risk:** TP +3%, SL -2%, time exit at 60d
**Trigger rate estimate:** ~10-15 trades/year (binary on extreme deciles + Fed direction)
**Data:** TLT/IEF already in `BOND_SYMBOLS`; Fed-funds-futures via Kalshi (existing) or yfinance
**Why this over alternatives:** Bond is currently 0 active picks. The steepener is the single most-cited bond strategy across ALL 4 reviews. Even a low trigger rate (10-15/yr) goes from 0 to nonzero.

---

## 6. ETF — Creation/Redemption Flow Momentum

**Source:** ChatGPT #190 + KIMI §7.1 — **one of only 2 ChatGPT picks rated TIER A** (ship-ready)
**File:** new `alpha_engine/strategies/etf_create_redeem_flow.py`
**Edge:** Daily ETF shares-outstanding changes reveal authorized-participant flow. Sustained creates → momentum continuation; sustained redemptions → reversal. Pure structural-flow signal.

**Signal:**
```python
def signal(etf_universe, shares_outstanding_30d):
    signals = []
    for sym in etf_universe:
        sho = shares_outstanding_30d[sym]
        if len(sho) < 30:
            continue
        # 5-day cumulative change relative to 30-day average
        recent_change = (sho.iloc[-1] - sho.iloc[-6]) / sho.iloc[-30:].mean()
        
        if recent_change > 0.02:  # 2% net creation in last 5d
            signals.append({"symbol": sym, "direction": "LONG", "confidence": 0.65, "horizon_d": 10})
        elif recent_change < -0.02:  # 2% net redemption
            signals.append({"symbol": sym, "direction": "SHORT", "confidence": 0.65, "horizon_d": 10})
    return signals
```

**Parameters:** 5d change vs 30d average, ±2% threshold, 10d horizon
**Risk:** TP +2%, SL -1.5%, time exit 10d
**Trigger rate estimate:** ~3-8 signals/day across the 50+ ETF universe (high-volume mechanical signal)
**Data:** **Free daily data** — yfinance has shares-outstanding for all major ETFs via `Ticker.info["sharesOutstanding"]`. Need to add a daily snapshot job.
**Why this over alternatives:** ETF is currently 1-3 active picks per cycle. ChatGPT and KIMI both flagged this as ship-ready with concrete data sources. High mechanical trigger rate = direct attack on the trigger-rate bottleneck.

---

## Implementation order (recommended)

| # | Strategy | Effort | Estimated active picks/day added | Why first |
|---|---|---|---|---|
| 1 | Commodity Roll Yield | 4-6h | 5-10 | Fixes #1 diagnosed bottleneck (commodities 1/144 starvation) — the ONLY profitable non-crypto class |
| 2 | Equity Overnight/Intraday Decomp | 3-4h | 15-25 | Equity has 0/40 active right now; pure OHLC = zero data dependency |
| 3 | ETF Create/Redeem Flow | 2-4h | 3-8 | One-time job to snapshot SO daily, then mechanical signal |
| 4 | Crypto Funding + Regime Gate | 4-6h | 3-5 | Addresses cycle-4 alt-drain regime issue; we already have funding data |
| 5 | Bond Yield Curve Steepener | 4-6h | 0-1/wk | Low volume but goes from 0 → nonzero on bonds |
| 6 | FX Carry + DXY Filter | 3-5h | 0-1/wk | FX losing money; DXY filter is the single change that flips it |

Total estimated: ~26-31 hours of focused work to **roughly double active-pick volume** AND make the engine regime-aware.

---

## What this proposal does NOT do

- Does NOT modify production strategy files
- Does NOT register in `STRATEGY_FAMILIES` (per earlier discussion — registration is safe but is a separate categorization step)
- Does NOT auto-emit picks until the engineer reviews + ships each file
- Does NOT replace anything; these are 6 NEW strategies added to the existing ~367

Per `CLAUDE.md` mutation-before-kill rule: this proposal also does NOT recommend killing any existing strategies. The cycle 1-4 perf-review PRs (#257/258/261/272) already cover that side of the equation.
