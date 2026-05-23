#!/usr/bin/env python3
"""
copytrader_quality_backtest.py
================================
Phase A: Pull real trade history from OKX API
Phase B: Verify trade quality (consistency, risk metrics, fraud detection)
Phase C: Reverse-engineer strategy parameters from verified trades
Phase D: Backtest reverse-engineered strategies against historical price data

Run: python copy_trader_intel/copytrader_quality_backtest.py
"""

import json, sys, os, time, math
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

import requests

try:
    import yfinance as yf
    HAS_YFINANCE = True
except Exception:
    HAS_YFINANCE = False
    print("[WARN] yfinance not available, backtesting without live price data")

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


# ============================================================
# PHASE A: Pull real trades from OKX
# ============================================================

def pull_okx_trades(unique_codes, max_per_trader=100):
    """Pull trade history from OKX Copy Trading API."""
    print("=" * 70)
    print("  PHASE A: PULL REAL TRADES FROM OKX API")
    print("=" * 70)

    all_trades = {}
    for code in unique_codes:
        print(f"\n  [{code[:8]}] Fetching trades...")
        try:
            r = requests.get(
                "https://www.okx.com/api/v5/copytrading/public-subpositions-history",
                params={"uniqueCode": code, "limit": max_per_trader},
                headers=HEADERS, timeout=15
            )
            data = r.json()
            raw = data.get("data", [])
            if not raw:
                print(f"    [EMPTY] code={data.get('code')}, msg={data.get('msg','')}")
                all_trades[code] = []
                continue

            trades = []
            for t in raw:
                open_ts = int(t.get("openTime", 0))
                close_ts = int(t.get("closeTime", 0))
                hold_ms = close_ts - open_ts
                hold_hours = hold_ms / 3_600_000 if hold_ms > 0 else 0
                entry = float(t.get("openAvgPx", 0))
                exit_px = float(t.get("closeAvgPx", 0))
                pnl = float(t.get("pnl", 0))
                pnl_pct = float(t.get("pnlRatio", 0)) * 100
                lever = float(t.get("lever", 1))

                trades.append({
                    "inst": t.get("instId", ""),
                    "side": t.get("posSide", ""),
                    "leverage": lever,
                    "entry_price": entry,
                    "exit_price": exit_px,
                    "open_time": open_ts,
                    "close_time": close_ts,
                    "hold_hours": round(hold_hours, 2),
                    "pnl_usd": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 4),
                    "size": float(t.get("subPos", 0)),
                })

            all_trades[code] = trades
            print(f"    [OK] {len(trades)} trades")
            time.sleep(0.4)
        except Exception as e:
            print(f"    [ERROR] {e}")
            all_trades[code] = []

    total = sum(len(v) for v in all_trades.values())
    print(f"\n  [TOTAL] {total} trades from {len([v for v in all_trades.values() if v])} traders")
    return all_trades


# ============================================================
# PHASE B: Verify trade quality
# ============================================================

def verify_trade_quality(trader_id, trades):
    """Comprehensive quality verification of a trader's history."""
    n = len(trades)
    if n < 3:
        return {"trader_id": trader_id, "quality_grade": "F", "reason": "Too few trades", "total_trades": n}

    pnls = [t["pnl_usd"] for t in trades]
    pnl_pcts = [t["pnl_pct"] for t in trades]
    holds = [t["hold_hours"] for t in trades if t["hold_hours"] > 0]
    leverages = [t["leverage"] for t in trades if t["leverage"] > 0]

    # Basic stats
    wins = sum(1 for p in pnls if p > 0)
    losses = sum(1 for p in pnls if p < 0)
    breakeven = sum(1 for p in pnls if p == 0)
    win_rate = wins / n if n > 0 else 0
    total_pnl = sum(pnls)
    avg_win = sum(p for p in pnls if p > 0) / wins if wins > 0 else 0
    avg_loss = abs(sum(p for p in pnls if p < 0) / losses) if losses > 0 else 0
    risk_reward = avg_win / avg_loss if avg_loss > 0 else 99
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p < 0))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 99

    # Drawdown analysis
    equity_curve = []
    running = 0
    peak = 0
    max_dd = 0
    max_dd_pct = 0
    for pnl in pnls:
        running += pnl
        equity_curve.append(running)
        if running > peak:
            peak = running
        dd = peak - running
        if dd > max_dd:
            max_dd = dd
        dd_pct = dd / peak * 100 if peak > 0 else 0
        if dd_pct > max_dd_pct:
            max_dd_pct = dd_pct

    # Consistency metrics
    # Win rate stability (rolling windows)
    window = min(10, n // 2)
    if window >= 3:
        rolling_wrs = []
        for i in range(n - window + 1):
            chunk = pnls[i:i+window]
            wr = sum(1 for p in chunk if p > 0) / len(chunk)
            rolling_wrs.append(wr)
        wr_std = (sum((wr - win_rate)**2 for wr in rolling_wrs) / len(rolling_wrs)) ** 0.5
        wr_consistency = max(0, 1 - wr_std * 2)
    else:
        wr_consistency = 0.5

    # Streak analysis
    max_win_streak = 0
    max_loss_streak = 0
    current_streak = 0
    for pnl in pnls:
        if pnl > 0:
            if current_streak > 0:
                current_streak += 1
            else:
                current_streak = 1
            max_win_streak = max(max_win_streak, current_streak)
        elif pnl < 0:
            if current_streak < 0:
                current_streak -= 1
            else:
                current_streak = -1
            max_loss_streak = max(max_loss_streak, abs(current_streak))
        else:
            current_streak = 0

    # Sharpe ratio approximation (using trade returns)
    if len(pnl_pcts) > 1:
        mean_ret = sum(pnl_pcts) / len(pnl_pcts)
        std_ret = (sum((r - mean_ret)**2 for r in pnl_pcts) / (len(pnl_pcts)-1)) ** 0.5
        sharpe = mean_ret / std_ret if std_ret > 0 else 0
    else:
        sharpe = 0

    # Time distribution (regularity)
    if len(holds) > 1:
        avg_hold = sum(holds) / len(holds)
        hold_cv = ((sum((h - avg_hold)**2 for h in holds) / len(holds)) ** 0.5) / avg_hold if avg_hold > 0 else 99
    else:
        avg_hold = holds[0] if holds else 0
        hold_cv = 0

    # Fraud / manipulation detection
    red_flags = []
    if win_rate > 0.95 and n > 10:
        red_flags.append("WIN_RATE_TOO_HIGH")
    if max_dd_pct > 80:
        red_flags.append("EXTREME_DRAWDOWN")
    if any(abs(p) > total_pnl * 0.5 for p in pnls) and n > 5:
        red_flags.append("SINGLE_TRADE_DOMINANCE")
    if avg_loss > avg_win * 5:
        red_flags.append("ASYMMETRIC_RISK")
    if hold_cv > 5:
        red_flags.append("INCONSISTENT_HOLD_TIME")
    if all(t["leverage"] > 50 for t in trades if t["leverage"] > 0):
        red_flags.append("EXTREME_LEVERAGE")

    # Instrument diversity
    instruments = [t["inst"] for t in trades]
    unique_inst = len(set(instruments))
    inst_concentration = max(instruments.count(i) for i in set(instruments)) / n if instruments else 0

    # Quality grading
    score = 0
    if win_rate >= 0.40: score += 15
    if win_rate >= 0.50: score += 10
    if profit_factor >= 1.2: score += 15
    if profit_factor >= 2.0: score += 10
    if risk_reward >= 1.0: score += 10
    if risk_reward >= 1.5: score += 5
    if sharpe > 0.5: score += 10
    if sharpe > 1.0: score += 5
    if max_dd_pct < 30: score += 10
    if wr_consistency > 0.6: score += 5
    if n >= 20: score += 5
    if not red_flags: score += 10
    score -= len(red_flags) * 5

    if score >= 80: grade = "A"
    elif score >= 65: grade = "B"
    elif score >= 50: grade = "C"
    elif score >= 35: grade = "D"
    else: grade = "F"

    return {
        "trader_id": trader_id,
        "quality_grade": grade,
        "quality_score": score,
        "total_trades": n,
        "metrics": {
            "win_rate": round(win_rate * 100, 2),
            "wins": wins,
            "losses": losses,
            "breakeven": breakeven,
            "profit_factor": round(profit_factor, 2),
            "risk_reward": round(risk_reward, 2),
            "sharpe_ratio": round(sharpe, 3),
            "total_pnl_usd": round(total_pnl, 2),
            "avg_win_usd": round(avg_win, 2),
            "avg_loss_usd": round(avg_loss, 2),
            "max_drawdown_usd": round(max_dd, 2),
            "max_drawdown_pct": round(max_dd_pct, 2),
        },
        "consistency": {
            "win_rate_consistency": round(wr_consistency, 3),
            "max_win_streak": max_win_streak,
            "max_loss_streak": max_loss_streak,
            "hold_time_cv": round(hold_cv, 2),
        },
        "style": {
            "avg_hold_hours": round(avg_hold, 2),
            "avg_leverage": round(sum(leverages)/len(leverages), 1) if leverages else 0,
            "unique_instruments": unique_inst,
            "instrument_concentration": round(inst_concentration * 100, 1),
        },
        "red_flags": red_flags,
    }


# ============================================================
# PHASE C: Reverse-engineer strategy parameters
# ============================================================

def extract_strategy_params(trader_id, trades, quality):
    """Extract actionable strategy parameters from verified trades."""
    if quality["quality_grade"] == "F":
        return None

    n = len(trades)
    holds = [t["hold_hours"] for t in trades if t["hold_hours"] > 0]
    leverages = [t["leverage"] for t in trades if t["leverage"] > 0]

    # Direction bias
    longs = sum(1 for t in trades if t["side"].lower() in ("long", "buy"))
    shorts = sum(1 for t in trades if t["side"].lower() in ("short", "sell"))
    long_pct = longs / n if n > 0 else 0.5

    # Instrument preferences
    inst_counts = defaultdict(int)
    for t in trades:
        inst_counts[t["inst"]] += 1
    top_instruments = sorted(inst_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    # TP/SL estimation from actual trade outcomes
    winning_pcts = [t["pnl_pct"] for t in trades if t["pnl_pct"] > 0]
    losing_pcts = [abs(t["pnl_pct"]) for t in trades if t["pnl_pct"] < 0]

    avg_tp_pct = sum(winning_pcts) / len(winning_pcts) if winning_pcts else 2.0
    avg_sl_pct = sum(losing_pcts) / len(losing_pcts) if losing_pcts else 2.0
    median_tp = sorted(winning_pcts)[len(winning_pcts)//2] if winning_pcts else 2.0
    median_sl = sorted(losing_pcts)[len(losing_pcts)//2] if losing_pcts else 2.0

    # Session timing
    hours = []
    for t in trades:
        ts = t["open_time"]
        if ts > 1e12: ts /= 1000
        if ts > 0:
            try:
                h = datetime.fromtimestamp(ts, tz=timezone.utc).hour
                hours.append(h)
            except: pass
    hour_dist = defaultdict(int)
    for h in hours:
        hour_dist[h] += 1
    peak_hour = max(hour_dist, key=hour_dist.get) if hour_dist else 12

    # Day of week distribution
    dow_dist = defaultdict(int)
    for t in trades:
        ts = t["open_time"]
        if ts > 1e12: ts /= 1000
        if ts > 0:
            try:
                d = datetime.fromtimestamp(ts, tz=timezone.utc).weekday()
                dow_dist[d] += 1
            except: pass

    # Archetype
    avg_hold = sum(holds) / len(holds) if holds else 0
    if avg_hold < 1: archetype = "SCALPER"
    elif avg_hold < 8: archetype = "DAY_TRADER"
    elif avg_hold < 72: archetype = "SWING_TRADER"
    else: archetype = "POSITION_TRADER"

    avg_lev = sum(leverages) / len(leverages) if leverages else 1

    return {
        "trader_id": trader_id,
        "archetype": archetype,
        "quality_grade": quality["quality_grade"],
        "quality_score": quality["quality_score"],
        "direction": {
            "bias": "LONG" if long_pct > 0.65 else ("SHORT" if long_pct < 0.35 else "NEUTRAL"),
            "long_pct": round(long_pct * 100, 1),
        },
        "tp_sl": {
            "avg_tp_pct": round(avg_tp_pct, 4),
            "avg_sl_pct": round(avg_sl_pct, 4),
            "median_tp_pct": round(median_tp, 4),
            "median_sl_pct": round(median_sl, 4),
            "rr_ratio": round(avg_tp_pct / avg_sl_pct, 2) if avg_sl_pct > 0 else 99,
        },
        "position_sizing": {
            "avg_leverage": round(avg_lev, 1),
            "min_leverage": round(min(leverages), 1) if leverages else 1,
            "max_leverage": round(max(leverages), 1) if leverages else 1,
        },
        "timing": {
            "avg_hold_hours": round(avg_hold, 2),
            "peak_hour_utc": peak_hour,
            "active_days": sorted(dow_dist, key=dow_dist.get, reverse=True)[:3] if dow_dist else [],
        },
        "instruments": {
            "top": [{"name": k, "trades": v, "pct": round(v/n*100, 1)} for k, v in top_instruments],
        },
    }


# ============================================================
# PHASE D: Backtest reverse-engineered strategies
# ============================================================

def backtest_strategy(strategy_params, trades, price_data=None):
    """Backtest a reverse-engineered strategy using actual trade data
    and optionally against historical price data."""

    trader_id = strategy_params["trader_id"]
    tp_pct = strategy_params["tp_sl"]["median_tp_pct"]
    sl_pct = strategy_params["tp_sl"]["median_sl_pct"]
    direction_bias = strategy_params["direction"]["bias"]
    avg_leverage = strategy_params["position_sizing"]["avg_leverage"]

    n = len(trades)
    if n < 5:
        return None

    # --- Walk-Forward Backtest ---
    # Split trades: 70% in-sample, 30% out-of-sample
    split = int(n * 0.7)
    in_sample = trades[:split]
    out_sample = trades[split:]

    def eval_trades(trade_list, label):
        """Evaluate a set of trades."""
        if not trade_list:
            return None
        pnls = [t["pnl_usd"] for t in trade_list]
        pnl_pcts = [t["pnl_pct"] for t in trade_list]
        wins = sum(1 for p in pnls if p > 0)
        nt = len(trade_list)
        wr = wins / nt if nt > 0 else 0
        total_pnl = sum(pnls)
        gross_profit = sum(p for p in pnls if p > 0)
        gross_loss = abs(sum(p for p in pnls if p < 0))
        pf = gross_profit / gross_loss if gross_loss > 0 else 99

        # Equity curve & drawdown
        equity = []
        running = 0
        peak = 0
        max_dd_pct = 0
        for pnl in pnls:
            running += pnl
            equity.append(running)
            if running > peak: peak = running
            dd = peak - running
            dd_pct = dd / peak * 100 if peak > 0 else 0
            max_dd_pct = max(max_dd_pct, dd_pct)

        # Sharpe
        if len(pnl_pcts) > 1:
            mean_r = sum(pnl_pcts) / len(pnl_pcts)
            std_r = (sum((r - mean_r)**2 for r in pnl_pcts) / (len(pnl_pcts)-1)) ** 0.5
            sharpe = mean_r / std_r if std_r > 0 else 0
        else:
            sharpe = 0

        # Calmar ratio
        calmar = total_pnl / max_dd_pct if max_dd_pct > 0 else 99

        return {
            "label": label,
            "trades": nt,
            "win_rate": round(wr * 100, 2),
            "profit_factor": round(pf, 2),
            "total_pnl_usd": round(total_pnl, 2),
            "total_return_pct": round(sum(pnl_pcts), 4),
            "max_drawdown_pct": round(max_dd_pct, 2),
            "sharpe": round(sharpe, 3),
            "calmar": round(calmar, 3),
        }

    in_result = eval_trades(in_sample, "IN_SAMPLE")
    out_result = eval_trades(out_sample, "OUT_OF_SAMPLE")
    full_result = eval_trades(trades, "FULL")

    # --- TP/SL Variation Grid Backtest ---
    # Test how the strategy would perform with different TP/SL multiples
    tp_multipliers = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
    sl_multipliers = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
    grid_results = []

    for tp_mult in tp_multipliers:
        for sl_mult in sl_multipliers:
            test_tp = tp_pct * tp_mult
            test_sl = sl_pct * sl_mult

            # Simulate: for each trade, check if it would hit TP or SL first
            sim_pnl = 0
            sim_wins = 0
            sim_n = 0
            for t in trades:
                actual_pnl_pct = t["pnl_pct"]
                # If actual move exceeded our TP, count as TP hit
                if actual_pnl_pct >= test_tp:
                    sim_pnl += test_tp * avg_leverage / 100  # Simplified
                    sim_wins += 1
                # If actual move exceeded our SL (negative), count as SL hit
                elif actual_pnl_pct <= -test_sl:
                    sim_pnl -= test_sl * avg_leverage / 100
                else:
                    # Neither hit, use actual outcome
                    sim_pnl += actual_pnl_pct * avg_leverage / 100
                    if actual_pnl_pct > 0: sim_wins += 1
                sim_n += 1

            sim_wr = sim_wins / sim_n if sim_n > 0 else 0
            grid_results.append({
                "tp_mult": tp_mult,
                "sl_mult": sl_mult,
                "tp_pct": round(test_tp, 4),
                "sl_pct": round(test_sl, 4),
                "sim_win_rate": round(sim_wr * 100, 2),
                "sim_total_return": round(sim_pnl, 4),
            })

    # Find best TP/SL combination
    best_grid = max(grid_results, key=lambda x: x["sim_total_return"])

    # --- Historical Price Backtest (if yfinance available) ---
    hist_backtest = None
    if HAS_YFINANCE and strategy_params["instruments"]["top"]:
        top_inst = strategy_params["instruments"]["top"][0]["name"]
        # Convert OKX instrument ID to yfinance symbol
        yf_symbol = top_inst.replace("-USDT-SWAP", "").replace("-SWAP", "")
        yf_symbol = yf_symbol.replace("-", "") + "-USD"
        # Common crypto mappings
        symbol_map = {
            "BTCUSDT-USD": "BTC-USD", "ETHUSDT-USD": "ETH-USD",
            "SOLUSDT-USD": "SOL-USD", "AVAXUSDT-USD": "AVAX-USD",
            "DOGEUSDT-USD": "DOGE-USD", "XRPUSDT-USD": "XRP-USD",
            "BTC-USD-USD": "BTC-USD", "ETH-USD-USD": "ETH-USD",
        }
        yf_symbol = symbol_map.get(yf_symbol, yf_symbol)

        try:
            ticker = yf.Ticker(yf_symbol)
            hist = ticker.history(period="90d", interval="1d")
            if len(hist) > 20:
                closes = hist["Close"].tolist()
                # Simple backtest: apply strategy rules to daily price data
                sim_trades = 0
                sim_wins = 0
                sim_pnl = 0
                for i in range(1, len(closes)):
                    daily_ret = (closes[i] - closes[i-1]) / closes[i-1] * 100
                    # Apply direction bias
                    if direction_bias == "LONG":
                        trade_ret = daily_ret
                    elif direction_bias == "SHORT":
                        trade_ret = -daily_ret
                    else:
                        trade_ret = daily_ret  # Default long

                    # Apply TP/SL
                    if trade_ret >= tp_pct:
                        trade_ret = tp_pct
                    elif trade_ret <= -sl_pct:
                        trade_ret = -sl_pct

                    leveraged_ret = trade_ret * avg_leverage / 100
                    sim_pnl += leveraged_ret
                    sim_trades += 1
                    if leveraged_ret > 0:
                        sim_wins += 1

                hist_backtest = {
                    "symbol": yf_symbol,
                    "period": "90d",
                    "daily_trades": sim_trades,
                    "win_rate": round(sim_wins / sim_trades * 100, 2) if sim_trades else 0,
                    "total_return_pct": round(sim_pnl, 4),
                    "note": "Simplified daily backtest with TP/SL applied",
                }
                print(f"    [HIST] {yf_symbol}: {sim_trades} days, WR {hist_backtest['win_rate']}%, Return {sim_pnl:.2f}%")
        except Exception as e:
            print(f"    [HIST WARN] {yf_symbol}: {e}")

    return {
        "trader_id": trader_id,
        "strategy": strategy_params,
        "walk_forward": {
            "in_sample": in_result,
            "out_of_sample": out_result,
            "full": full_result,
        },
        "tp_sl_grid": {
            "best_combination": best_grid,
            "grid_size": len(grid_results),
            "all_results": sorted(grid_results, key=lambda x: x["sim_total_return"], reverse=True)[:10],
        },
        "historical_backtest": hist_backtest,
    }


# ============================================================
# Main
# ============================================================

def main():
    print("=" * 70)
    print("  COPYTRADER QUALITY VERIFICATION & BACKTESTING")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    # Our verified OKX traders
    known_traders = {
        "1173EC858F15E04F": "Expert-Ethash-Camel",
        "849CAD818B573125": "nightraid-",
        "0C053614746975C0": "Fair-Hash-Maverick",
        "99FB5ECCC0C27A8A": "CrowleyZhou",
        "AD2B6E949E5E91EC": "FJ Investment",
        "D442CF34E4AEEAF1": "Trader KS",
    }

    # Also try to pull from OKX leaderboard
    try:
        r = requests.get(
            "https://www.okx.com/api/v5/copytrading/public-lead-traders",
            headers=HEADERS, timeout=15
        )
        data = r.json()
        for t in data.get("data", []):
            code = t.get("uniqueCode", "")
            name = t.get("nickName", f"OKX-{code[:8]}")
            if code and code not in known_traders:
                known_traders[code] = name
        print(f"  [OK] {len(known_traders)} traders to analyze")
    except Exception as e:
        print(f"  [WARN] Leaderboard fetch: {e}")

    # PHASE A: Pull trades
    all_trades = pull_okx_trades(list(known_traders.keys()))

    # PHASE B: Verify quality
    print("\n" + "=" * 70)
    print("  PHASE B: VERIFY TRADE QUALITY")
    print("=" * 70)

    quality_reports = {}
    for code, trades in all_trades.items():
        if not trades:
            continue
        name = known_traders.get(code, code[:8])
        q = verify_trade_quality(code, trades)
        quality_reports[code] = q
        flags = ", ".join(q["red_flags"]) if q["red_flags"] else "none"
        print(f"\n  [{q['quality_grade']}] {name} (score: {q['quality_score']})")
        print(f"      WR: {q['metrics']['win_rate']}% | PF: {q['metrics']['profit_factor']} | Sharpe: {q['metrics']['sharpe_ratio']}")
        print(f"      PnL: ${q['metrics']['total_pnl_usd']:,.2f} | MaxDD: {q['metrics']['max_drawdown_pct']:.1f}%")
        print(f"      Trades: {q['total_trades']} | Flags: {flags}")

    # PHASE C: Extract strategy parameters
    print("\n" + "=" * 70)
    print("  PHASE C: REVERSE-ENGINEER STRATEGY PARAMETERS")
    print("=" * 70)

    strategies = {}
    for code, trades in all_trades.items():
        if not trades or code not in quality_reports:
            continue
        q = quality_reports[code]
        params = extract_strategy_params(code, trades, q)
        if params:
            strategies[code] = params
            name = known_traders.get(code, code[:8])
            print(f"\n  {name} [{params['archetype']}]")
            print(f"    TP: {params['tp_sl']['median_tp_pct']:.2f}% | SL: {params['tp_sl']['median_sl_pct']:.2f}% | R:R: {params['tp_sl']['rr_ratio']}")
            print(f"    Bias: {params['direction']['bias']} ({params['direction']['long_pct']:.0f}%) | Lev: {params['position_sizing']['avg_leverage']}x")
            print(f"    Hold: {params['timing']['avg_hold_hours']:.1f}h | Top: {params['instruments']['top'][0]['name'] if params['instruments']['top'] else '?'}")

    # PHASE D: Backtest
    print("\n" + "=" * 70)
    print("  PHASE D: BACKTEST REVERSE-ENGINEERED STRATEGIES")
    print("=" * 70)

    backtest_results = {}
    for code, params in strategies.items():
        trades = all_trades[code]
        name = known_traders.get(code, code[:8])
        print(f"\n  Backtesting {name}...")

        result = backtest_strategy(params, trades)
        if result:
            backtest_results[code] = result
            wf = result["walk_forward"]
            is_r = wf["in_sample"]
            os_r = wf["out_of_sample"]

            print(f"    IN-SAMPLE:  {is_r['trades']} trades | WR: {is_r['win_rate']}% | PF: {is_r['profit_factor']} | PnL: ${is_r['total_pnl_usd']:,.2f}" if is_r else "    IN-SAMPLE: N/A")
            print(f"    OUT-SAMPLE: {os_r['trades']} trades | WR: {os_r['win_rate']}% | PF: {os_r['profit_factor']} | PnL: ${os_r['total_pnl_usd']:,.2f}" if os_r else "    OUT-SAMPLE: N/A")
            print(f"    BEST TP/SL: TP×{result['tp_sl_grid']['best_combination']['tp_mult']} / SL×{result['tp_sl_grid']['best_combination']['sl_mult']} → {result['tp_sl_grid']['best_combination']['sim_total_return']:.2f}%")

    # Save all results
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_traders_analyzed": len(quality_reports),
        "quality_reports": quality_reports,
        "strategies": strategies,
        "backtest_results": {k: {
            "trader_name": known_traders.get(k, k[:8]),
            **v
        } for k, v in backtest_results.items()},
    }

    path = DATA_DIR / "quality_backtest_results.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)

    # FINAL SUMMARY
    print("\n" + "=" * 70)
    print("  FINAL RESULTS SUMMARY")
    print("=" * 70)

    # Quality grades
    grades = defaultdict(list)
    for code, q in quality_reports.items():
        grades[q["quality_grade"]].append(known_traders.get(code, code[:8]))
    for g in ["A", "B", "C", "D", "F"]:
        if grades[g]:
            print(f"  Grade {g}: {', '.join(grades[g])}")

    # Top strategies by out-of-sample performance
    print("\n  STRATEGY LEADERBOARD (by out-of-sample PnL):")
    print(f"  {'Trader':25s} {'Grade':>5s} {'WR(OS)':>7s} {'PF(OS)':>7s} {'PnL(OS)':>10s} {'Sharpe':>7s}")
    print("  " + "-" * 65)

    ranked = []
    for code, bt in backtest_results.items():
        os_r = bt["walk_forward"].get("out_of_sample")
        if os_r:
            ranked.append((code, os_r))
    ranked.sort(key=lambda x: x[1]["total_pnl_usd"], reverse=True)

    for code, os_r in ranked:
        name = known_traders.get(code, code[:8])
        grade = quality_reports[code]["quality_grade"]
        print(f"  {name:25s} {grade:>5s} {os_r['win_rate']:6.1f}% {os_r['profit_factor']:6.2f} {os_r['total_pnl_usd']:+9.2f} {os_r['sharpe']:6.3f}")

    print(f"\n  [OK] Results saved -> {path}")
    print("=" * 70)

    return output


if __name__ == "__main__":
    main()
