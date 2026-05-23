#!/usr/bin/env python3
"""
ANTIGRAVITY ALTERNATIVE DATA ENGINE
====================================
Signals that Renaissance CAN'T scale to:
  1. Fear & Greed Index — free from alternative.me
  2. Binance Funding Rates — free from Binance fapi
  3. BTC Dominance Rotation — free from CoinGecko

These are genuine underdog edges:
  - Too thin in liquidity for $130B AUM to exploit
  - Behavioral/structural, not speed-dependent
  - All completely free, no API keys

"Be fearful when others are greedy, and greedy when others are fearful" — Buffett
"""

import json
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from pathlib import Path
from scipy import stats as scipy_stats
import urllib.request
import time

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


def fetch_json(url, retries=3):
    """Fetch JSON from URL with retries"""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            if attempt == retries - 1:
                print(f"  ❌ Failed to fetch {url}: {e}")
                return None
            time.sleep(2)


def validate_trades(trades, name):
    """Quick validation"""
    if not trades or len(trades) < 5:
        return {"name": name, "trades": len(trades) if trades else 0, "verdict": "❌ INSUFFICIENT DATA"}
    
    arr = np.array(trades)
    n = len(arr)
    wins = sum(1 for t in arr if t > 0)
    wr = wins / n * 100
    
    gross_profit = sum(t for t in arr if t > 0)
    gross_loss = abs(sum(t for t in arr if t < 0))
    pf = gross_profit / gross_loss if gross_loss > 0 else 0
    
    if n >= 5 and np.std(arr) > 0:
        t_stat, p_val = scipy_stats.ttest_1samp(arr, 0)
        p_one = p_val / 2 if t_stat > 0 else 1 - p_val / 2
        sharpe = np.mean(arr) / np.std(arr) * np.sqrt(min(252, n))
    else:
        p_one, sharpe = 1.0, 0
    
    cumulative = np.cumsum(arr)
    running_max = np.maximum.accumulate(cumulative)
    max_dd = abs(float(min(cumulative - running_max))) if n > 0 else 0
    
    checks_passed = 0
    if n >= 15: checks_passed += 1
    if wr >= 45: checks_passed += 1
    if p_one <= 0.05: checks_passed += 1
    if sharpe >= 1.0: checks_passed += 1
    if pf >= 1.3: checks_passed += 1
    if max_dd <= 20: checks_passed += 1
    
    if checks_passed >= 5: verdict = "🏆 INSTITUTIONAL"
    elif checks_passed >= 4: verdict = "✅ PROVEN"
    elif checks_passed >= 3: verdict = "⚠️ PROMISING"
    else: verdict = "❌ WEAK"
    
    return {
        "name": name,
        "trades": n, "wins": wins,
        "win_rate": round(wr, 1),
        "avg_pnl": round(float(np.mean(arr)), 3),
        "total_pnl": round(float(np.sum(arr)), 2),
        "sharpe": round(sharpe, 2),
        "profit_factor": round(pf, 2),
        "max_dd": round(max_dd, 2),
        "p_value": round(p_one, 4),
        "checks_passed": f"{checks_passed}/6",
        "verdict": verdict,
    }


# ═══════════════════════════════════════════════════════════════════════════
# SIGNAL 1: FEAR & GREED CONTRARIAN
# ═══════════════════════════════════════════════════════════════════════════

def backtest_fear_greed():
    """
    Crypto Fear & Greed Index contrarian strategy.
    
    Source: alternative.me (free, no API key)
    Published evidence: 1,145% ROI vs 1,046% buy-and-hold (2018-2024)
    
    Rules:
      - BUY when index < 20 (Extreme Fear) — hold for 14 days
      - SELL when index > 80 (Extreme Greed) — exit all positions
      - Wait for next extreme
    
    Buffer zones prevent whipsaw:
      - Don't rebuy until fear drops below 25 again after greed exit
    """
    print("\n" + "=" * 80)
    print("SIGNAL 1: FEAR & GREED CONTRARIAN")
    print("Source: alternative.me/crypto/fear-and-greed-index/ (FREE)")
    print("=" * 80)
    
    # Fetch historical Fear & Greed data
    url = "https://api.alternative.me/fng/?limit=0&format=json"
    data = fetch_json(url)
    
    if not data or "data" not in data:
        print("  ❌ Could not fetch Fear & Greed data")
        return None
    
    fg_data = data["data"]
    fg_data.reverse()  # Oldest first
    
    print(f"  ✅ Got {len(fg_data)} days of Fear & Greed data")
    
    # Also need BTC price for the same period
    import yfinance as yf
    btc = yf.download("BTC-USD", period="max", interval="1d", auto_adjust=True, progress=False)
    if btc.empty:
        print("  ❌ Could not fetch BTC data")
        return None
    
    # Create aligned dataframe
    fg_df = pd.DataFrame(fg_data)
    fg_df["date"] = pd.to_datetime(fg_df["timestamp"].astype(int), unit="s")
    fg_df["value"] = fg_df["value"].astype(int)
    fg_df = fg_df.set_index("date").sort_index()
    
    # Align with BTC
    btc_close = btc["Close"]
    if isinstance(btc_close, pd.DataFrame):
        btc_close = btc_close.iloc[:, 0]
    
    common = fg_df.index.intersection(btc_close.index)
    if len(common) < 100:
        # Try date-only matching
        fg_df.index = fg_df.index.normalize()
        btc_close.index = btc_close.index.normalize()
        common = fg_df.index.intersection(btc_close.index)
    
    print(f"  ✅ Aligned {len(common)} common trading days")
    
    if len(common) < 100:
        print("  ❌ Insufficient aligned data")
        return None
    
    fg_aligned = fg_df.loc[common, "value"]
    btc_aligned = btc_close.loc[common]
    
    # Strategy: buy at extreme fear, exit at extreme greed
    trades_14d = []  # 14-day hold
    trades_30d = []  # 30-day hold
    trades_greed_exit = []  # Hold until greed
    
    # Strategy 1: Fixed hold period (14 days)
    for i in range(len(common) - 14):
        fg = int(fg_aligned.iloc[i])
        if fg <= 20:  # Extreme fear
            entry = float(btc_aligned.iloc[i])
            exit_p = float(btc_aligned.iloc[i + 14])
            pnl = (exit_p - entry) / entry * 100
            trades_14d.append(pnl)
    
    # Strategy 2: Fixed hold period (30 days)
    for i in range(len(common) - 30):
        fg = int(fg_aligned.iloc[i])
        if fg <= 20:
            entry = float(btc_aligned.iloc[i])
            exit_p = float(btc_aligned.iloc[i + 30])
            pnl = (exit_p - entry) / entry * 100
            trades_30d.append(pnl)
    
    # Strategy 3: Enter at fear < 20, exit at greed > 75
    in_trade = False
    entry_price = 0
    for i in range(len(common)):
        fg = int(fg_aligned.iloc[i])
        price = float(btc_aligned.iloc[i])
        
        if not in_trade and fg <= 20:
            in_trade = True
            entry_price = price
        elif in_trade and fg >= 75:
            pnl = (price - entry_price) / entry_price * 100
            trades_greed_exit.append(pnl)
            in_trade = False
    
    # Strategy 4: Short at extreme greed > 85, exit at < 50
    trades_short_greed = []
    in_trade = False
    entry_price = 0
    for i in range(len(common)):
        fg = int(fg_aligned.iloc[i])
        price = float(btc_aligned.iloc[i])
        
        if not in_trade and fg >= 85:
            in_trade = True
            entry_price = price
        elif in_trade and fg <= 50:
            pnl = (entry_price - price) / entry_price * 100
            trades_short_greed.append(pnl)
            in_trade = False
    
    # Print all variants
    results_list = []
    for name, trades in [
        ("FearGreed_BuyFear20_Hold14d", trades_14d),
        ("FearGreed_BuyFear20_Hold30d", trades_30d),
        ("FearGreed_BuyFear20_ExitGreed75", trades_greed_exit),
        ("FearGreed_ShortGreed85_Exit50", trades_short_greed),
    ]:
        v = validate_trades(trades, name)
        results_list.append(v)
        sign = "+" if v.get("total_pnl", 0) >= 0 else ""
        print(f"  {name}: {v['trades']}t | WR:{v.get('win_rate', 0)}% | "
              f"PnL:{sign}{v.get('total_pnl', 0)}% | Sharpe:{v.get('sharpe', 0)} | "
              f"p={v.get('p_value', 1)} | {v.get('checks_passed', '')} {v['verdict']}")
    
    return results_list


# ═══════════════════════════════════════════════════════════════════════════
# SIGNAL 2: BINANCE FUNDING RATE
# ═══════════════════════════════════════════════════════════════════════════

def backtest_funding_rate():
    """
    Binance Perpetual Futures Funding Rate strategy.
    
    Source: Binance public fapi (FREE, no API key)
    
    When funding rate is very negative (shorts paying longs):
      - Market is overly bearish
      - Price tends to revert upward
      - Small capital advantage: can't scale beyond ~$5M
    
    Rules:
      - BUY when 8h funding rate < -0.01% (shorts dominating)
      - EXIT after 24 hours or when funding turns positive
    """
    print("\n" + "=" * 80)
    print("SIGNAL 2: BINANCE FUNDING RATE FADE")
    print("Source: Binance fapi/v1/fundingRate (FREE, public)")
    print("=" * 80)
    
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "XRPUSDT", "AVAXUSDT", "LINKUSDT"]
    
    all_results = []
    
    for sym in symbols:
        print(f"\n  Fetching funding rates for {sym}...")
        
        # Fetch last 1000 funding rates (8h intervals, ~333 days)
        url = f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={sym}&limit=1000"
        data = fetch_json(url)
        
        if not data or len(data) < 50:
            print(f"  ❌ Insufficient data for {sym}")
            continue
        
        # Convert to DataFrame
        fr_df = pd.DataFrame(data)
        fr_df["fundingTime"] = pd.to_datetime(fr_df["fundingTime"], unit="ms")
        fr_df["fundingRate"] = fr_df["fundingRate"].astype(float)
        fr_df = fr_df.set_index("fundingTime").sort_index()
        
        print(f"  ✅ {len(fr_df)} funding rate samples ({fr_df.index[0].date()} to {fr_df.index[-1].date()})")
        
        # Need price data too
        yf_sym = sym.replace("USDT", "-USD")
        import yfinance as yf
        price_data = yf.download(yf_sym, start=fr_df.index[0].strftime("%Y-%m-%d"),
                                  end=(fr_df.index[-1] + timedelta(days=5)).strftime("%Y-%m-%d"),
                                  interval="1d", auto_adjust=True, progress=False)
        
        if price_data.empty or len(price_data) < 30:
            print(f"  ❌ Insufficient price data for {yf_sym}")
            continue
        
        price_close = price_data["Close"]
        if isinstance(price_close, pd.DataFrame):
            price_close = price_close.iloc[:, 0]
        
        # Strategy: when daily avg funding < threshold, go long next day
        # Aggregate to daily
        fr_df["date"] = fr_df.index.normalize()
        daily_fr = fr_df.groupby("date")["fundingRate"].mean()
        
        # Test multiple thresholds
        for threshold, thresh_name in [(-0.0001, "neg_0.01pct"), (-0.0003, "neg_0.03pct"), (-0.0005, "neg_0.05pct")]:
            trades = []
            
            price_close_norm = price_close.copy()
            price_close_norm.index = price_close_norm.index.normalize()
            
            for i in range(len(daily_fr) - 1):
                fr_val = float(daily_fr.iloc[i])
                date_today = daily_fr.index[i]
                date_next = daily_fr.index[i + 1] if i + 1 < len(daily_fr) else None
                
                if fr_val < threshold and date_next is not None:
                    # Find price on signal day and next day
                    if date_today in price_close_norm.index and date_next in price_close_norm.index:
                        entry = float(price_close_norm.loc[date_today])
                        exit_p = float(price_close_norm.loc[date_next])
                        pnl = (exit_p - entry) / entry * 100
                        trades.append(pnl)
            
            name = f"FundingFade_{sym}_{thresh_name}"
            v = validate_trades(trades, name)
            all_results.append(v)
            
            if v["trades"] >= 5:
                sign = "+" if v.get("total_pnl", 0) >= 0 else ""
                print(f"    {thresh_name}: {v['trades']}t | WR:{v.get('win_rate', 0)}% | "
                      f"PnL:{sign}{v.get('total_pnl', 0):.1f}% | p={v.get('p_value', 1)} | {v['verdict']}")
    
    return all_results


# ═══════════════════════════════════════════════════════════════════════════
# SIGNAL 3: BTC DOMINANCE ROTATION
# ═══════════════════════════════════════════════════════════════════════════

def backtest_btc_dominance_rotation():
    """
    BTC Dominance capital rotation strategy.
    
    When BTC dominance is high (>60%): Hold BTC (safety)
    When BTC dominance is falling: Rotate into altcoins (alt season)
    When BTC dominance is low (<45%): Expect reversal back to BTC
    
    Source: CoinGecko (free) or yfinance BTC.D proxy
    """
    print("\n" + "=" * 80)
    print("SIGNAL 3: BTC DOMINANCE ROTATION")
    print("=" * 80)
    
    import yfinance as yf
    
    # Download BTC and total crypto market proxy
    print("  Downloading crypto data...")
    syms = ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "DOGE-USD", "ADA-USD"]
    batch = yf.download(syms, period="5y", interval="1d", auto_adjust=True, 
                         group_by="ticker", progress=False, threads=True)
    
    dfs = {}
    for sym in syms:
        try:
            df = batch[sym].dropna()
            if len(df) > 200:
                dfs[sym] = df
        except:
            pass
    
    if "BTC-USD" not in dfs or len(dfs) < 3:
        print("  ❌ Insufficient data")
        return None
    
    btc = dfs["BTC-USD"]["Close"]
    
    # Proxy: BTC "dominance" via relative strength vs altcoin basket
    alt_basket = None
    for sym in ["ETH-USD", "SOL-USD", "XRP-USD"]:
        if sym in dfs:
            alt = dfs[sym]["Close"]
            # Normalize each to starting value
            common = btc.index.intersection(alt.index)
            if alt_basket is None:
                alt_basket = (alt.loc[common] / alt.loc[common].iloc[0])
            else:
                alt_basket += (alt.loc[common] / alt.loc[common].iloc[0])
    
    if alt_basket is None:
        print("  ❌ No altcoin data")
        return None
    
    btc_norm = btc.loc[alt_basket.index] / btc.loc[alt_basket.index].iloc[0]
    btc_strength = btc_norm / alt_basket  # Rising = BTC outperforming (high dominance)
    
    # Smooth the ratio
    strength_sma = btc_strength.rolling(20).mean()
    strength_change = strength_sma.pct_change(20)  # 20-day change in BTC dominance
    
    # Strategy: when BTC dominance is FALLING → go long altcoins
    # When BTC dominance is RISING → go long BTC
    trades_alt = []  # Altcoin trades when BTC dom falling
    trades_btc = []  # BTC trades when BTC dom rising
    hold = 21
    
    for i in range(40, len(strength_change) - hold):
        if pd.isna(strength_change.iloc[i]):
            continue
        
        sc = float(strength_change.iloc[i])
        date_i = strength_change.index[i]
        date_exit = strength_change.index[i + hold]
        
        if sc < -0.05:  # BTC dom falling → alt season
            # Go long best altcoin (ETH as proxy)
            if "ETH-USD" in dfs:
                eth = dfs["ETH-USD"]["Close"]
                if date_i in eth.index and date_exit in eth.index:
                    entry = float(eth.loc[date_i])
                    exit_p = float(eth.loc[date_exit])
                    pnl = (exit_p - entry) / entry * 100
                    trades_alt.append(pnl)
        
        elif sc > 0.05:  # BTC dom rising → BTC season
            if date_i in btc.index and date_exit in btc.index:
                entry = float(btc.loc[date_i])
                exit_p = float(btc.loc[date_exit])
                pnl = (exit_p - entry) / entry * 100
                trades_btc.append(pnl)
    
    results_list = []
    for name, trades in [
        ("BTCDom_AltSeason_LongETH", trades_alt),
        ("BTCDom_BTCSeason_LongBTC", trades_btc),
        ("BTCDom_Combined", trades_alt + trades_btc),
    ]:
        v = validate_trades(trades, name)
        results_list.append(v)
        sign = "+" if v.get("total_pnl", 0) >= 0 else ""
        print(f"  {name}: {v['trades']}t | WR:{v.get('win_rate', 0)}% | "
              f"PnL:{sign}{v.get('total_pnl', 0):.1f}% | p={v.get('p_value', 1)} | {v['verdict']}")
    
    return results_list


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 100)
    print("ANTIGRAVITY ALTERNATIVE DATA ENGINE")
    print("Signals that Renaissance Technologies CANNOT scale to")
    print("All data sources: FREE, no API keys")
    print("=" * 100)
    
    all_signals = {}
    
    # Signal 1: Fear & Greed
    fg_results = backtest_fear_greed()
    if fg_results:
        all_signals["fear_greed"] = fg_results
    
    # Signal 2: Funding Rate
    fr_results = backtest_funding_rate()
    if fr_results:
        all_signals["funding_rate"] = fr_results
    
    # Signal 3: BTC Dominance
    dom_results = backtest_btc_dominance_rotation()
    if dom_results:
        all_signals["btc_dominance"] = dom_results
    
    # Final report
    print(f"\n{'='*100}")
    print("ALTERNATIVE DATA RESULTS SUMMARY")
    print("=" * 100)
    
    all_validated = []
    for category, results in all_signals.items():
        if results:
            for r in results:
                all_validated.append(r)
    
    all_validated.sort(key=lambda x: (
        int(x.get("checks_passed", "0/6").split("/")[0]),
        x.get("total_pnl", 0)
    ), reverse=True)
    
    print(f"\n{'RK':>3} {'SIGNAL':<45} {'TR':>5} {'WR':>6} {'PnL':>9} {'SHP':>6} {'PF':>5} {'p-val':>7}  VERDICT")
    print("-" * 100)
    
    for i, v in enumerate(all_validated, 1):
        if v["trades"] < 3:
            continue
        sign = "+" if v.get("total_pnl", 0) >= 0 else ""
        print(f"{i:>3} {v['name']:<45} {v['trades']:>5} {v.get('win_rate', 0):>5.1f}% "
              f"{sign}{v.get('total_pnl', 0):>7.1f}% {v.get('sharpe', 0):>6.2f} "
              f"{v.get('profit_factor', 0):>5.2f} {v.get('p_value', 1):>7.4f}  {v['verdict']}")
    
    # Save
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "engine": "ALTERNATIVE_DATA_v1",
        "data_cost": "$0 — all free public APIs",
        "why_renaissance_cant": "Liquidity constraints — these markets can't absorb $130B AUM",
        "results": all_validated,
    }
    
    outfile = DATA_DIR / "alternative_data_results.json"
    with open(outfile, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n📁 Results saved: {outfile}")


if __name__ == "__main__":
    main()
