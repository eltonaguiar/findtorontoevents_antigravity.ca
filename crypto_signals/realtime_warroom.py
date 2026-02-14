"""
REAL-TIME WAR ROOM — Live Forward-Test Validator
=================================================
Refreshes data from Binance, runs the V1 confluence engine,
identifies OPEN signals (not yet resolved), fetches live prices,
and scores our system's real-time performance.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json, os, time, sys
import ccxt

from strategies import (
    ema, sma, rsi, atr, bollinger_bands, macd, adx, supertrend,
    ichimoku, obv, stochastic,
    strategy_ema_crossover, strategy_rsi_momentum, strategy_macd_crossover,
    strategy_supertrend, strategy_triple_ema, strategy_adx_ema,
    strategy_ichimoku, strategy_volume_momentum, strategy_mtf_momentum,
    strategy_donchian_breakout, strategy_momentum_rotation,
    strategy_bb_squeeze_breakout
)

STRATEGIES = {
    'RSI_Momentum':    {'fn': strategy_rsi_momentum,    'w': 2.0},
    'MTF_Momentum':    {'fn': strategy_mtf_momentum,    'w': 2.0},
    'Donchian':        {'fn': strategy_donchian_breakout,'w': 1.5},
    'EMA_Cross':       {'fn': strategy_ema_crossover,   'w': 1.0},
    'Supertrend':      {'fn': strategy_supertrend,      'w': 1.5},
    'Triple_EMA':      {'fn': strategy_triple_ema,      'w': 1.0},
    'MACD_Cross':      {'fn': strategy_macd_crossover,  'w': 1.0},
    'ADX_EMA':         {'fn': strategy_adx_ema,         'w': 1.5},
    'Ichimoku':        {'fn': strategy_ichimoku,        'w': 1.0},
    'Vol_Momentum':    {'fn': strategy_volume_momentum,  'w': 1.0},
    'Mom_Rotation':    {'fn': strategy_momentum_rotation,'w': 1.5},
    'BB_Squeeze':      {'fn': strategy_bb_squeeze_breakout,'w': 1.0},
}
MAX_SCORE = sum(s['w'] for s in STRATEGIES.values())

PAIRS = ['BTC/USDT', 'ETH/USDT', 'AVAX/USDT', 'BNB/USDT']


def banner(text, char='=', width=80):
    print(f"\n{char*width}")
    print(f"  {text}")
    print(f"{char*width}")


def fetch_fresh(symbol, exchange, timeframe='1d', days=400):
    """Fetch fresh OHLCV data — NO CACHE. Live from Binance."""
    since = exchange.parse8601((datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%dT00:00:00Z'))
    all_data = []
    while True:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
            if not ohlcv: break
            all_data.extend(ohlcv)
            since = ohlcv[-1][0] + 1
            if len(ohlcv) < 1000: break
            time.sleep(exchange.rateLimit / 1000)
        except Exception as e:
            print(f"  [!] Fetch error: {e}"); break
    if not all_data: return None
    df = pd.DataFrame(all_data, columns=['timestamp','open','high','low','close','volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df = df[~df.index.duplicated(keep='first')].sort_index()
    return df


def fetch_live_price(symbol, exchange):
    """Get the current live ticker price."""
    try:
        ticker = exchange.fetch_ticker(symbol)
        return {
            'price': ticker['last'],
            'bid': ticker.get('bid'),
            'ask': ticker.get('ask'),
            'high_24h': ticker.get('high'),
            'low_24h': ticker.get('low'),
            'volume_24h': ticker.get('quoteVolume'),
            'change_24h': ticker.get('percentage'),
            'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
        }
    except Exception as e:
        print(f"  [!] Ticker error for {symbol}: {e}")
        return None


def compute_live_signals(df, symbol):
    """Run all 12 strategies on fresh data and compute current confluence state."""
    sigs = {}
    for name, info in STRATEGIES.items():
        try:
            sigs[name] = info['fn'](df)
        except:
            sigs[name] = pd.Series(0, index=df.index)

    # Current state (last bar)
    active = []
    total_score = 0.0
    for name, info in STRATEGIES.items():
        val = sigs[name].iloc[-1] if len(sigs[name]) > 0 else 0
        is_buy = int(val == 1)
        if is_buy:
            active.append(name)
            total_score += info['w']

    score_pct = total_score / MAX_SCORE * 100
    n = len(active)

    # Recent history — last 5 bars
    recent = []
    for i in range(-5, 0):
        if abs(i) > len(df): continue
        bar_active = []
        bar_score = 0.0
        for name, info in STRATEGIES.items():
            val = sigs[name].iloc[i] if len(sigs[name]) > abs(i) else 0
            if int(val == 1):
                bar_active.append(name)
                bar_score += info['w']
        recent.append({
            'date': df.index[i].strftime('%Y-%m-%d'),
            'close': round(df['close'].iloc[i], 2),
            'n_strategies': len(bar_active),
            'score_pct': round(bar_score / MAX_SCORE * 100, 1),
            'strategies': bar_active,
        })

    # Indicators
    rsi_14 = rsi(df['close'], 14)
    atr_14 = atr(df['high'], df['low'], df['close'], 14)
    ema_9 = ema(df['close'], 9)
    ema_21 = ema(df['close'], 21)
    ema_50 = ema(df['close'], 50)
    ema_200 = ema(df['close'], 200)
    bb_upper, bb_mid, bb_lower = bollinger_bands(df['close'], 20, 2)
    macd_line, signal_line, hist = macd(df['close'])
    adx_val, _, _ = adx(df['high'], df['low'], df['close'], 14)

    ret_7d = (df['close'].iloc[-1] / df['close'].iloc[-8] - 1) * 100 if len(df) > 8 else 0
    ret_30d = (df['close'].iloc[-1] / df['close'].iloc[-31] - 1) * 100 if len(df) > 31 else 0
    ret_90d = (df['close'].iloc[-1] / df['close'].iloc[-91] - 1) * 100 if len(df) > 91 else 0

    # Regime
    ret_60 = df['close'].pct_change(60).iloc[-1] if len(df) > 60 else 0
    if ret_60 > 0.15: regime = 'BULL'
    elif ret_60 < -0.15: regime = 'BEAR'
    else: regime = 'SIDEWAYS'

    # Support/Resistance
    support = df['low'].rolling(50).min().iloc[-1]
    resistance = df['high'].rolling(50).max().iloc[-1]

    # Signal verdict
    if score_pct >= 70 and n >= 6:
        verdict = 'STRONG BUY'
        color = '\033[92m'  # green
    elif score_pct >= 45 and n >= 3:
        verdict = 'BUY SIGNAL'
        color = '\033[93m'  # yellow
    elif score_pct >= 30 and n >= 2:
        verdict = 'WEAK BUY'
        color = '\033[33m'
    else:
        verdict = 'NO SIGNAL'
        color = '\033[90m'  # gray

    return {
        'symbol': symbol,
        'verdict': verdict,
        'color': color,
        'n_strategies': n,
        'score_pct': round(score_pct, 1),
        'active_strategies': active,
        'regime': regime,
        'indicators': {
            'rsi_14': round(rsi_14.iloc[-1], 1) if pd.notna(rsi_14.iloc[-1]) else None,
            'atr_14': round(atr_14.iloc[-1], 4) if pd.notna(atr_14.iloc[-1]) else None,
            'ema_9': round(ema_9.iloc[-1], 2) if pd.notna(ema_9.iloc[-1]) else None,
            'ema_21': round(ema_21.iloc[-1], 2) if pd.notna(ema_21.iloc[-1]) else None,
            'ema_50': round(ema_50.iloc[-1], 2) if pd.notna(ema_50.iloc[-1]) else None,
            'ema_200': round(ema_200.iloc[-1], 2) if pd.notna(ema_200.iloc[-1]) else None,
            'bb_upper': round(bb_upper.iloc[-1], 2) if pd.notna(bb_upper.iloc[-1]) else None,
            'bb_lower': round(bb_lower.iloc[-1], 2) if pd.notna(bb_lower.iloc[-1]) else None,
            'macd_hist': round(hist.iloc[-1], 4) if pd.notna(hist.iloc[-1]) else None,
            'adx': round(adx_val.iloc[-1], 1) if pd.notna(adx_val.iloc[-1]) else None,
            'support_50d': round(support, 2) if pd.notna(support) else None,
            'resistance_50d': round(resistance, 2) if pd.notna(resistance) else None,
        },
        'returns': {
            '7d': round(ret_7d, 2),
            '30d': round(ret_30d, 2),
            '90d': round(ret_90d, 2),
        },
        'recent_bars': recent,
    }


def check_open_signals(symbol, df, live_price):
    """Check if any recent signals from the saved JSON are still OPEN (within 30-day window)."""
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'confluence_signals.json')
    if not os.path.exists(json_path):
        return []

    with open(json_path) as f:
        data = json.load(f)

    signals = data.get('signals', {}).get(symbol, [])
    if not signals:
        return []

    now = datetime.utcnow()
    open_signals = []

    for sig in signals:
        sig_date = datetime.strptime(sig['date'], '%Y-%m-%d')
        days_since = (now - sig_date).days

        # Check signals from last 30 days that haven't been fully resolved yet
        # (or recent ones we can validate)
        if days_since <= 45:
            entry = sig['entry_price']
            tp = sig['take_profit']
            sl = sig['stop_loss']
            price = live_price

            # Distance to TP and SL
            dist_tp = (tp - price) / price * 100
            dist_sl = (price - sl) / price * 100
            unrealized = (price - entry) / entry * 100

            if price >= tp:
                status = 'TP_HIT_LIVE'
            elif price <= sl:
                status = 'SL_HIT_LIVE'
            elif days_since > 30:
                status = 'EXPIRED_LIVE'
            else:
                status = 'OPEN'

            open_signals.append({
                **sig,
                'live_price': round(price, 4),
                'unrealized_pnl': round(unrealized, 2),
                'dist_to_tp': round(dist_tp, 2),
                'dist_to_sl': round(dist_sl, 2),
                'days_since': days_since,
                'live_status': status,
            })

    return open_signals


def validate_recent_signals(symbol):
    """Pull all 2025-2026 signals and check their historical outcomes."""
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'confluence_signals.json')
    if not os.path.exists(json_path):
        return []

    with open(json_path) as f:
        data = json.load(f)

    signals = data.get('signals', {}).get(symbol, [])
    recent = [s for s in signals if s['date'] >= '2025-01-01']
    return recent


def main():
    banner("REAL-TIME WAR ROOM — Live Forward-Test Validator", '█')
    print(f"  Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"  Pairs: {', '.join(PAIRS)}")
    print(f"  Engine: V1 Confluence (12 strategies)")
    print(f"  Data: FRESH from Binance (no cache)")

    exchange = ccxt.binance({'enableRateLimit': True})

    # ═══════════════════════════════════════════════════════════════
    # PHASE 1: LIVE PRICES
    # ═══════════════════════════════════════════════════════════════
    banner("PHASE 1: LIVE MARKET PRICES", '─')
    live_prices = {}
    for symbol in PAIRS:
        ticker = fetch_live_price(symbol, exchange)
        if ticker:
            live_prices[symbol] = ticker
            chg = ticker['change_24h'] or 0
            chg_str = f"+{chg:.2f}%" if chg >= 0 else f"{chg:.2f}%"
            vol = ticker['volume_24h'] or 0
            print(f"  {symbol:<12} ${ticker['price']:>12,.2f}  24h: {chg_str:>8}  "
                  f"H: ${ticker['high_24h']:>10,.2f}  L: ${ticker['low_24h']:>10,.2f}  "
                  f"Vol: ${vol:>14,.0f}")

    # ═══════════════════════════════════════════════════════════════
    # PHASE 2: FRESH DATA + LIVE SIGNAL STATE
    # ═══════════════════════════════════════════════════════════════
    banner("PHASE 2: LIVE SIGNAL STATE (Fresh Data)", '─')
    all_states = {}
    for symbol in PAIRS:
        print(f"\n  Fetching {symbol} fresh data...")
        df = fetch_fresh(symbol, exchange, '1d', 400)
        if df is None or len(df) < 100:
            print(f"  [!] Insufficient data for {symbol}"); continue

        print(f"  Got {len(df)} candles ({df.index[0].strftime('%Y-%m-%d')} → {df.index[-1].strftime('%Y-%m-%d')})")

        state = compute_live_signals(df, symbol)
        all_states[symbol] = state

        reset = '\033[0m'
        v = state['verdict']
        c = state['color']
        ind = state['indicators']

        print(f"\n  ┌─ {symbol} ─────────────────────────────────────────────")
        print(f"  │ VERDICT: {c}{v}{reset}  ({state['n_strategies']}/12 strategies, {state['score_pct']}% score)")
        print(f"  │ Regime:  {state['regime']}  |  RSI: {ind['rsi_14']}  |  ADX: {ind['adx']}")
        print(f"  │ EMA:     9={ind['ema_9']}  21={ind['ema_21']}  50={ind['ema_50']}  200={ind['ema_200']}")
        print(f"  │ BB:      Upper={ind['bb_upper']}  Lower={ind['bb_lower']}")
        print(f"  │ MACD:    Hist={ind['macd_hist']}  |  ATR(14)={ind['atr_14']}")
        print(f"  │ S/R:     Support={ind['support_50d']}  Resistance={ind['resistance_50d']}")
        print(f"  │ Returns: 7d={state['returns']['7d']}%  30d={state['returns']['30d']}%  90d={state['returns']['90d']}%")

        if state['active_strategies']:
            print(f"  │ Active:  {', '.join(state['active_strategies'])}")
        else:
            print(f"  │ Active:  (none)")

        print(f"  │")
        print(f"  │ Recent 5 bars:")
        for bar in state['recent_bars']:
            bar_strats = ', '.join(bar['strategies'][:4])
            if len(bar['strategies']) > 4:
                bar_strats += f" +{len(bar['strategies'])-4} more"
            print(f"  │   {bar['date']}  ${bar['close']:>10,.2f}  {bar['n_strategies']}/12 ({bar['score_pct']}%)  {bar_strats}")
        print(f"  └──────────────────────────────────────────────────────")

    # ═══════════════════════════════════════════════════════════════
    # PHASE 3: OPEN SIGNAL TRACKING
    # ═══════════════════════════════════════════════════════════════
    banner("PHASE 3: OPEN / RECENT SIGNAL TRACKING", '─')
    all_open = {}
    for symbol in PAIRS:
        if symbol not in live_prices: continue
        price = live_prices[symbol]['price']
        open_sigs = check_open_signals(symbol, None, price)
        if open_sigs:
            all_open[symbol] = open_sigs
            print(f"\n  {symbol} — {len(open_sigs)} signal(s) in last 45 days:")
            for s in open_sigs:
                status = s['live_status']
                if status == 'OPEN':
                    status_str = f"\033[93mOPEN\033[0m"
                elif 'TP_HIT' in status:
                    status_str = f"\033[92mTP HIT ✓\033[0m"
                elif 'SL_HIT' in status:
                    status_str = f"\033[91mSL HIT ✗\033[0m"
                else:
                    status_str = f"\033[90mEXPIRED\033[0m"

                pnl = s['unrealized_pnl']
                pnl_str = f"\033[92m+{pnl:.2f}%\033[0m" if pnl >= 0 else f"\033[91m{pnl:.2f}%\033[0m"

                print(f"    {s['date']}  Entry=${s['entry_price']:>10,.2f}  "
                      f"Now=${s['live_price']:>10,.2f}  {pnl_str}  "
                      f"TP=${s['take_profit']:>10,.2f} ({s['dist_to_tp']:+.1f}%)  "
                      f"SL=${s['stop_loss']:>10,.2f} ({s['dist_to_sl']:+.1f}%)  "
                      f"{status_str}  [{s['confidence']}] {s['days_since']}d ago")
        else:
            print(f"\n  {symbol} — No signals in last 45 days")

    # ═══════════════════════════════════════════════════════════════
    # PHASE 4: 2025-2026 SIGNAL SCORECARD
    # ═══════════════════════════════════════════════════════════════
    banner("PHASE 4: 2025-2026 SIGNAL SCORECARD (Real Performance)", '─')
    total_signals = 0
    total_wins = 0
    total_pnl = 0
    pair_scores = {}

    for symbol in PAIRS:
        recent = validate_recent_signals(symbol)
        if not recent:
            print(f"\n  {symbol}: No 2025+ signals")
            continue

        wins = [s for s in recent if s['outcome'] == 'TP_HIT']
        losses = [s for s in recent if s['outcome'] == 'SL_HIT']
        expired = [s for s in recent if s['outcome'] == 'EXPIRED']
        wr = len(wins) / len(recent) * 100 if recent else 0
        pnl_sum = sum(s['pnl_pct'] for s in recent)
        avg_pnl = pnl_sum / len(recent) if recent else 0

        total_signals += len(recent)
        total_wins += len(wins)
        total_pnl += pnl_sum

        pair_scores[symbol] = {
            'total': len(recent), 'wins': len(wins), 'losses': len(losses),
            'expired': len(expired), 'wr': wr, 'pnl': pnl_sum, 'avg_pnl': avg_pnl,
        }

        wr_color = '\033[92m' if wr >= 40 else ('\033[93m' if wr >= 30 else '\033[91m')
        pnl_color = '\033[92m' if pnl_sum > 0 else '\033[91m'
        reset = '\033[0m'

        print(f"\n  {symbol}:")
        print(f"    Signals: {len(recent)}  |  W: {len(wins)}  L: {len(losses)}  E: {len(expired)}")
        print(f"    Win Rate: {wr_color}{wr:.1f}%{reset}  |  Total PnL: {pnl_color}{pnl_sum:+.2f}%{reset}  |  Avg: {avg_pnl:+.2f}%")

        for s in recent:
            o = '✓' if s['outcome'] == 'TP_HIT' else ('✗' if s['outcome'] == 'SL_HIT' else '○')
            o_color = '\033[92m' if s['outcome'] == 'TP_HIT' else ('\033[91m' if s['outcome'] == 'SL_HIT' else '\033[90m')
            print(f"    {o_color}{o}{reset} {s['date']}  Entry=${s['entry_price']:>10,.2f}  "
                  f"Exit=${s.get('exit_price',0):>10,.2f}  PnL={s['pnl_pct']:+6.2f}%  "
                  f"[{s['confidence']}]  {s.get('bars_held',0)}d  "
                  f"R:R={s['rr_ratio']}  {s['regime']}")

    # ═══════════════════════════════════════════════════════════════
    # PHASE 5: OVERALL SCORECARD
    # ═══════════════════════════════════════════════════════════════
    banner("PHASE 5: OVERALL SYSTEM SCORECARD", '█')

    overall_wr = total_wins / total_signals * 100 if total_signals else 0
    avg_overall = total_pnl / total_signals if total_signals else 0

    print(f"\n  ┌─────────────────────────────────────────────────────────────┐")
    print(f"  │  SYSTEM: V1 Confluence Engine (12 strategies)              │")
    print(f"  │  PERIOD: 2025-01-01 → {datetime.utcnow().strftime('%Y-%m-%d')} (REAL-TIME)         │")
    print(f"  ├─────────────────────────────────────────────────────────────┤")
    print(f"  │  Total Signals:     {total_signals:>5}                                  │")
    print(f"  │  Wins:              {total_wins:>5}                                  │")
    print(f"  │  Overall Win Rate:  {overall_wr:>5.1f}%                                │")
    print(f"  │  Total PnL:         {total_pnl:>+8.2f}%                             │")
    print(f"  │  Avg PnL/Trade:     {avg_overall:>+8.2f}%                             │")
    print(f"  ├─────────────────────────────────────────────────────────────┤")

    for sym, sc in pair_scores.items():
        wr_icon = '🟢' if sc['wr'] >= 40 else ('🟡' if sc['wr'] >= 30 else '🔴')
        pnl_icon = '🟢' if sc['pnl'] > 0 else '🔴'
        print(f"  │  {sym:<12} {wr_icon} WR={sc['wr']:>5.1f}%  {pnl_icon} PnL={sc['pnl']:>+8.2f}%  ({sc['total']} sig) │")

    print(f"  └─────────────────────────────────────────────────────────────┘")

    # Current live signals
    print(f"\n  CURRENT LIVE SIGNAL STATUS:")
    for sym, state in all_states.items():
        v = state['verdict']
        if 'BUY' in v:
            print(f"    {state['color']}⚡ {sym}: {v} — {state['n_strategies']}/12 strategies ({state['score_pct']}%)\033[0m")
            print(f"       Active: {', '.join(state['active_strategies'])}")
        else:
            print(f"    \033[90m○ {sym}: {v}\033[0m")

    # ═══════════════════════════════════════════════════════════════
    # SAVE REPORT
    # ═══════════════════════════════════════════════════════════════
    out_dir = os.path.dirname(os.path.abspath(__file__))
    report = {
        'timestamp': datetime.utcnow().isoformat(),
        'live_prices': live_prices,
        'signal_states': {k: {kk: vv for kk, vv in v.items() if kk != 'color'} for k, v in all_states.items()},
        'open_signals': {k: v for k, v in all_open.items()},
        'scorecard_2025': pair_scores,
        'overall': {
            'total_signals': total_signals,
            'total_wins': total_wins,
            'win_rate': round(overall_wr, 1),
            'total_pnl': round(total_pnl, 2),
            'avg_pnl': round(avg_overall, 2),
        }
    }
    with open(os.path.join(out_dir, 'WARROOM_LIVE.json'), 'w') as f:
        json.dump(report, f, indent=2, default=str)

    # Markdown report
    md = []
    md.append(f"# WAR ROOM — Real-Time System Validation")
    md.append(f"\n**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    md.append(f"**Engine:** V1 Confluence (12 strategies)")

    md.append(f"\n## Live Prices\n")
    md.append(f"| Pair | Price | 24h Change | 24h High | 24h Low | Volume |")
    md.append(f"|------|-------|-----------|----------|---------|--------|")
    for sym, t in live_prices.items():
        chg = t['change_24h'] or 0
        md.append(f"| {sym} | ${t['price']:,.2f} | {chg:+.2f}% | ${t['high_24h']:,.2f} | ${t['low_24h']:,.2f} | ${(t['volume_24h'] or 0):,.0f} |")

    md.append(f"\n## Current Signal State\n")
    md.append(f"| Pair | Verdict | Score | Strategies | Regime | RSI | ADX |")
    md.append(f"|------|---------|-------|------------|--------|-----|-----|")
    for sym, s in all_states.items():
        md.append(f"| {sym} | **{s['verdict']}** | {s['score_pct']}% | {s['n_strategies']}/12 | {s['regime']} | {s['indicators']['rsi_14']} | {s['indicators']['adx']} |")

    md.append(f"\n## 2025-2026 Scorecard\n")
    md.append(f"| Pair | Signals | Wins | Losses | WR | Total PnL | Avg PnL |")
    md.append(f"|------|---------|------|--------|-----|-----------|---------|")
    for sym, sc in pair_scores.items():
        md.append(f"| {sym} | {sc['total']} | {sc['wins']} | {sc['losses']} | {sc['wr']:.1f}% | {sc['pnl']:+.2f}% | {sc['avg_pnl']:+.2f}% |")
    md.append(f"| **TOTAL** | **{total_signals}** | **{total_wins}** | | **{overall_wr:.1f}%** | **{total_pnl:+.2f}%** | **{avg_overall:+.2f}%** |")

    if all_open:
        md.append(f"\n## Open / Recent Signals\n")
        for sym, sigs in all_open.items():
            md.append(f"\n### {sym}\n")
            md.append(f"| Date | Entry | Live | PnL | TP | SL | Status | Conf | Days |")
            md.append(f"|------|-------|------|-----|----|----|--------|------|------|")
            for s in sigs:
                md.append(f"| {s['date']} | ${s['entry_price']:,.2f} | ${s['live_price']:,.2f} | {s['unrealized_pnl']:+.2f}% | ${s['take_profit']:,.2f} | ${s['stop_loss']:,.2f} | {s['live_status']} | {s['confidence']} | {s['days_since']}d |")

    with open(os.path.join(out_dir, 'WARROOM_REPORT.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(md))

    print(f"\n  Reports saved: WARROOM_LIVE.json, WARROOM_REPORT.md")
    banner("WAR ROOM COMPLETE", '█')


if __name__ == '__main__':
    main()
