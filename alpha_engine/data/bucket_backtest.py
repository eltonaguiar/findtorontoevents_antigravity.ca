import json, os, sys, ssl, urllib.request, math, statistics
from collections import defaultdict
from datetime import datetime, timezone

BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
]

def fetch_klines(symbol, interval='4h', limit=200):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    for mirror in BINANCE_MIRRORS:
        try:
            url = f"{mirror}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=10, context=ctx)
            return json.loads(resp.read())
        except: continue
    return []

# Test 3 simple strategies across 3 symbol buckets
BUCKETS = {
    'MAJORS': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT'],
    'MIDCAP': ['FETUSDT', 'RENDERUSDT', 'APTUSDT', 'SUIUSDT', 'ARBUSDT'],
    'ALTS': ['DOGEUSDT', 'ADAUSDT', 'AVAXUSDT', 'LINKUSDT', 'DOTUSDT'],
}

def backtest_rsi_mean_reversion(closes, period=14, oversold=30, overbought=70):
    """Simple RSI mean-reversion backtest"""
    if len(closes) < period + 5: return {'trades': 0}

    # Compute RSI
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))

    trades = []
    in_trade = False
    entry = 0
    direction = ''

    for i in range(period, len(closes)):
        avg_gain = sum(gains[i-period:i]) / period
        avg_loss = sum(losses[i-period:i]) / period
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        rsi = 100 - (100 / (1 + rs))

        if not in_trade:
            if rsi < oversold:
                in_trade = True; entry = closes[i]; direction = 'LONG'
            elif rsi > overbought:
                in_trade = True; entry = closes[i]; direction = 'SHORT'
        else:
            pnl = ((closes[i] - entry) / entry * 100) if direction == 'LONG' else ((entry - closes[i]) / entry * 100)
            # Exit: TP at 2%, SL at 1.5%, or RSI crosses 50
            if pnl >= 2.0 or pnl <= -1.5 or (direction == 'LONG' and rsi > 50) or (direction == 'SHORT' and rsi < 50):
                trades.append(pnl)
                in_trade = False

    if not trades: return {'trades': 0}
    wins = sum(1 for t in trades if t > 0)
    return {
        'trades': len(trades), 'wins': wins, 'wr': wins/len(trades)*100,
        'avg_pnl': sum(trades)/len(trades), 'total_pnl': sum(trades),
    }

def backtest_bollinger_bounce(closes, period=20, std_mult=2.5):
    """Bollinger Band bounce backtest"""
    if len(closes) < period + 5: return {'trades': 0}

    trades = []
    in_trade = False
    entry = 0
    direction = ''

    for i in range(period, len(closes)):
        window = closes[i-period:i]
        sma = sum(window) / period
        std = (sum((c - sma)**2 for c in window) / period) ** 0.5
        upper = sma + std_mult * std
        lower = sma - std_mult * std

        if not in_trade:
            if closes[i] <= lower * 1.005:
                in_trade = True; entry = closes[i]; direction = 'LONG'
            elif closes[i] >= upper * 0.995:
                in_trade = True; entry = closes[i]; direction = 'SHORT'
        else:
            pnl = ((closes[i] - entry) / entry * 100) if direction == 'LONG' else ((entry - closes[i]) / entry * 100)
            if pnl >= 1.5 or pnl <= -1.0 or abs(closes[i] - sma) / sma < 0.005:
                trades.append(pnl)
                in_trade = False

    if not trades: return {'trades': 0}
    wins = sum(1 for t in trades if t > 0)
    return {
        'trades': len(trades), 'wins': wins, 'wr': wins/len(trades)*100,
        'avg_pnl': sum(trades)/len(trades), 'total_pnl': sum(trades),
    }

def backtest_momentum_breakout(closes, lookback=20):
    """Simple momentum breakout: buy above highest high, sell below lowest low"""
    if len(closes) < lookback + 5: return {'trades': 0}

    trades = []
    in_trade = False
    entry = 0
    direction = ''

    for i in range(lookback, len(closes)):
        window = closes[i-lookback:i]
        highest = max(window)
        lowest = min(window)

        if not in_trade:
            if closes[i] > highest:
                in_trade = True; entry = closes[i]; direction = 'LONG'
            elif closes[i] < lowest:
                in_trade = True; entry = closes[i]; direction = 'SHORT'
        else:
            pnl = ((closes[i] - entry) / entry * 100) if direction == 'LONG' else ((entry - closes[i]) / entry * 100)
            if pnl >= 2.0 or pnl <= -1.5:
                trades.append(pnl)
                in_trade = False

    if not trades: return {'trades': 0}
    wins = sum(1 for t in trades if t > 0)
    return {
        'trades': len(trades), 'wins': wins, 'wr': wins/len(trades)*100,
        'avg_pnl': sum(trades)/len(trades), 'total_pnl': sum(trades),
    }

STRATEGIES = {
    'rsi_mean_reversion': backtest_rsi_mean_reversion,
    'bollinger_bounce_2.5': backtest_bollinger_bounce,
    'momentum_breakout': backtest_momentum_breakout,
}

print('='*80)
print('MULTI-SYMBOL BUCKET BACKTESTING')
print('='*80)

results = {}
for bucket_name, symbols in BUCKETS.items():
    print(f'\n--- {bucket_name} BUCKET ({", ".join(symbols)}) ---')
    for strat_name, strat_func in STRATEGIES.items():
        bucket_results = []
        for sym in symbols:
            klines = fetch_klines(sym, '4h', 500)
            if not klines: continue
            closes = [float(k[4]) for k in klines]
            r = strat_func(closes)
            if r['trades'] > 0:
                bucket_results.append(r)
                print(f'  {strat_name:<25} {sym:<12} trades={r["trades"]:>3} WR={r["wr"]:>5.0f}% avg={r["avg_pnl"]:>+6.2f}%')

        # Aggregate bucket results
        if bucket_results:
            total_trades = sum(r['trades'] for r in bucket_results)
            total_wins = sum(r['wins'] for r in bucket_results)
            total_pnl = sum(r['total_pnl'] for r in bucket_results)
            syms_profitable = sum(1 for r in bucket_results if r['total_pnl'] > 0)
            agg_wr = total_wins/total_trades*100 if total_trades > 0 else 0

            key = f'{strat_name}|{bucket_name}'
            results[key] = {
                'strat': strat_name, 'bucket': bucket_name,
                'trades': total_trades, 'wr': agg_wr,
                'avg_pnl': total_pnl/total_trades if total_trades > 0 else 0,
                'symbols_tested': len(bucket_results),
                'symbols_profitable': syms_profitable,
                'robustness': syms_profitable/len(bucket_results) if bucket_results else 0,
            }
            print(f'  >> AGGREGATE: trades={total_trades} WR={agg_wr:.0f}% profitable_syms={syms_profitable}/{len(bucket_results)}')

# Summary ranking
print(f'\n{"="*80}')
print('STRATEGY x BUCKET RANKING (by WR)')
print(f'{"="*80}')
ranked = sorted(results.values(), key=lambda x: (-x['wr'], -x['robustness']))
for r in ranked:
    robust = 'ROBUST' if r['robustness'] >= 0.6 else 'FRAGILE' if r['robustness'] >= 0.4 else 'WEAK'
    print(f'  {r["strat"]:<25} {r["bucket"]:<10} WR={r["wr"]:>5.0f}% trades={r["trades"]:>4} robust={r["robustness"]:.0%} ({robust})')

# Save results
with open('alpha_engine/data/bucket_backtest_results.json', 'w') as f:
    json.dump({'timestamp': datetime.now(timezone.utc).isoformat(), 'results': results}, f, indent=2, default=str)
print('\nSaved to alpha_engine/data/bucket_backtest_results.json')
