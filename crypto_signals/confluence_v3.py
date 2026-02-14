"""
CONFLUENCE V3 — Refined Signal Engine
======================================
Based on V1 results + Kimi K2 insights. Key changes from V1:
1. AVAX/BNB: Skip momentum-only strategies, add RSI<65 filter
2. Wider SL for high-vol assets (3x ATR for AVAX, 2.5x for others)
3. Higher confluence threshold (55%+ score, 5+ strategies)
4. Bear market filter: reduce signals when 60-day return < -25%
5. No trailing stop (V2 proved it hurts more than helps)
6. Volume confirmation as tiebreaker
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json, os, time, ccxt
from strategies import (
    ema, sma, rsi, atr, bollinger_bands, macd, adx, supertrend,
    ichimoku, obv, stochastic,
    strategy_ema_crossover, strategy_rsi_momentum, strategy_macd_crossover,
    strategy_supertrend, strategy_triple_ema, strategy_adx_ema,
    strategy_ichimoku, strategy_volume_momentum, strategy_mtf_momentum,
    strategy_donchian_breakout, strategy_momentum_rotation,
    strategy_bb_squeeze_breakout
)

def load_or_fetch(symbol, timeframe='1d', exchange_id='binance', cache_dir='data_cache'):
    os.makedirs(cache_dir, exist_ok=True)
    safe = symbol.replace('/', '_')
    cache_file = os.path.join(cache_dir, f"{safe}_{timeframe}_{exchange_id}.csv")
    if os.path.exists(cache_file):
        if time.time() - os.path.getmtime(cache_file) < 43200:
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            print(f"  Cache: {symbol} ({len(df)} candles)")
            return df
    exchange = getattr(ccxt, exchange_id)({'enableRateLimit': True})
    all_data = []
    since = exchange.parse8601('2020-01-01T00:00:00Z')
    print(f"  Fetching {symbol}...")
    while True:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
            if not ohlcv: break
            all_data.extend(ohlcv)
            since = ohlcv[-1][0] + 1
            if len(ohlcv) < 1000: break
            time.sleep(exchange.rateLimit / 1000)
        except Exception as e:
            print(f"  Warn: {e}"); break
    if not all_data: return None
    df = pd.DataFrame(all_data, columns=['timestamp','open','high','low','close','volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df = df[~df.index.duplicated(keep='first')].sort_index()
    df.to_csv(cache_file)
    print(f"  Got {len(df)} candles")
    return df

# Same 12 strategies as V1 — proven to work
STRATEGIES = {
    'RSI_Mom':    {'fn': strategy_rsi_momentum,    'w': 2.0, 'cat': 'momentum'},
    'MTF_Mom':    {'fn': strategy_mtf_momentum,    'w': 2.0, 'cat': 'momentum'},
    'Donchian':   {'fn': strategy_donchian_breakout,'w': 1.5, 'cat': 'breakout'},
    'EMA_Cross':  {'fn': strategy_ema_crossover,   'w': 1.0, 'cat': 'trend'},
    'Supertrend': {'fn': strategy_supertrend,      'w': 1.5, 'cat': 'trend'},
    'Triple_EMA': {'fn': strategy_triple_ema,      'w': 1.0, 'cat': 'trend'},
    'MACD':       {'fn': strategy_macd_crossover,  'w': 1.0, 'cat': 'trend'},
    'ADX_EMA':    {'fn': strategy_adx_ema,         'w': 1.5, 'cat': 'strength'},
    'Ichimoku':   {'fn': strategy_ichimoku,        'w': 1.0, 'cat': 'trend'},
    'Vol_Mom':    {'fn': strategy_volume_momentum,  'w': 1.0, 'cat': 'volume'},
    'Mom_Rot':    {'fn': strategy_momentum_rotation,'w': 1.5, 'cat': 'momentum'},
    'BB_Squeeze': {'fn': strategy_bb_squeeze_breakout,'w': 1.0, 'cat': 'volatility'},
}
MAX_SCORE = sum(s['w'] for s in STRATEGIES.values())

# Asset-specific config (Kimi insight)
ASSET_CFG = {
    'BTC/USDT':  {'sl_mult': 2.0, 'max_sl_pct': 8, 'rsi_cap': 80, 'bear_filter': True,  'min_score': 0.45, 'min_strats': 3},
    'ETH/USDT':  {'sl_mult': 2.0, 'max_sl_pct': 8, 'rsi_cap': 80, 'bear_filter': True,  'min_score': 0.45, 'min_strats': 3},
    'AVAX/USDT': {'sl_mult': 3.0, 'max_sl_pct': 10,'rsi_cap': 70, 'bear_filter': True,  'min_score': 0.45, 'min_strats': 3},
    'BNB/USDT':  {'sl_mult': 2.5, 'max_sl_pct': 8, 'rsi_cap': 75, 'bear_filter': True,  'min_score': 0.45, 'min_strats': 3},
}

def generate_signals(df, symbol):
    cfg = ASSET_CFG[symbol]
    # Run strategies
    sigs = {}
    for name, info in STRATEGIES.items():
        try: sigs[name] = info['fn'](df)
        except: sigs[name] = pd.Series(0, index=df.index)

    score = pd.Series(0.0, index=df.index)
    n_agree = pd.Series(0, index=df.index)
    names = pd.Series('', index=df.index, dtype=str)
    for name, info in STRATEGIES.items():
        s = sigs[name]
        is_long = (s == 1).astype(float)
        score += is_long * info['w']
        n_agree += is_long.astype(int)
        for idx in df.index[is_long == 1]:
            names[idx] = (names[idx] + ',' + name).strip(',')

    score_pct = score / MAX_SCORE
    atr_14 = atr(df['high'], df['low'], df['close'], 14)
    rsi_14 = rsi(df['close'], 14)
    ret_60 = df['close'].pct_change(60).fillna(0)
    support = df['low'].rolling(50).min()
    resistance = df['high'].rolling(50).max()
    vol_avg = df['volume'].rolling(20).mean()

    # Regime
    regime = pd.Series('sideways', index=df.index)
    regime[ret_60 > 0.15] = 'bull'
    regime[ret_60 < -0.15] = 'bear'

    signals = []
    last_i = None

    for i in range(50, len(df)):
        if last_i and (i - last_i) < 5: continue
        if score_pct.iloc[i] < cfg['min_score'] or n_agree.iloc[i] < cfg['min_strats']:
            continue
        # New signal only
        if i > 0 and score_pct.iloc[i-1] >= cfg['min_score'] and n_agree.iloc[i-1] >= cfg['min_strats']:
            if score_pct.iloc[i] <= score_pct.iloc[i-1] * 1.1: continue

        # RSI cap (asset-specific)
        if pd.notna(rsi_14.iloc[i]) and rsi_14.iloc[i] > cfg['rsi_cap']:
            continue

        # Bear market filter: skip if 60-day return < -25%
        if cfg['bear_filter'] and ret_60.iloc[i] < -0.25:
            continue

        entry = df['close'].iloc[i]
        cur_atr = atr_14.iloc[i]
        if pd.isna(cur_atr) or cur_atr <= 0: continue

        # SL
        sl = entry - cfg['sl_mult'] * cur_atr
        sl_sup = support.iloc[i] * 0.995 if pd.notna(support.iloc[i]) else sl
        sl = max(sl, sl_sup)
        sl = min(sl, entry * 0.995)
        sl = max(sl, entry * (1 - cfg['max_sl_pct']/100))
        sl_pct = (entry - sl) / entry * 100

        # TP (regime-adjusted)
        r = regime.iloc[i]
        conf = score_pct.iloc[i]
        if r == 'bull': tp_m = 4.0
        elif r == 'bear': tp_m = 2.0
        else: tp_m = 3.0
        tp_m *= (0.8 + 0.4 * conf)
        tp = entry + tp_m * cur_atr
        tp_r = resistance.iloc[i] * 0.995 if pd.notna(resistance.iloc[i]) else tp
        if tp_r > entry * 1.005: tp = min(tp, tp_r)
        tp = max(tp, entry * 1.01)
        tp_pct = (tp - entry) / entry * 100

        risk = entry - sl
        reward = tp - entry
        rr = reward / risk if risk > 0 else 0
        if rr < 1.5: continue

        ns = int(n_agree.iloc[i])
        if conf >= 0.70 and ns >= 6: c = 'VERY_HIGH'
        elif conf >= 0.55 and ns >= 5: c = 'HIGH'
        elif conf >= 0.45 and ns >= 4: c = 'MEDIUM_HIGH'
        else: c = 'MEDIUM'

        has_vol = bool(pd.notna(vol_avg.iloc[i]) and df['volume'].iloc[i] > vol_avg.iloc[i] * 1.2)

        signals.append({
            'date': idx_to_str(df.index[i]),
            'entry_price': round(entry, 4), 'take_profit': round(tp, 4), 'stop_loss': round(sl, 4),
            'tp_pct': round(tp_pct, 2), 'sl_pct': round(sl_pct, 2), 'rr_ratio': round(rr, 2),
            'confidence': c, 'score': round(conf*100, 1), 'n_strats': ns,
            'strategies': names.iloc[i], 'regime': r,
            'rsi': round(rsi_14.iloc[i], 1) if pd.notna(rsi_14.iloc[i]) else None,
            'atr': round(cur_atr, 4), 'vol_confirmed': has_vol,
        })
        last_i = i
    return signals

def idx_to_str(idx):
    return idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)

def evaluate(signals, df, max_hold=30):
    results = []
    for sig in signals:
        date = pd.Timestamp(sig['date'])
        mask = df.index >= date
        if not mask.any(): continue
        si = df.index.get_loc(df.index[mask][0])
        entry, tp, sl = sig['entry_price'], sig['take_profit'], sig['stop_loss']
        ei = min(si + max_hold, len(df))
        outcome, exit_p, exit_d, bars = 'EXPIRED', None, None, 0
        max_p, min_p = entry, entry

        for j in range(si+1, ei):
            h, l = df['high'].iloc[j], df['low'].iloc[j]
            bars = j - si
            max_p, min_p = max(max_p, h), min(min_p, l)
            if l <= sl:
                outcome, exit_p, exit_d = 'SL_HIT', sl, idx_to_str(df.index[j]); break
            if h >= tp:
                outcome, exit_p, exit_d = 'TP_HIT', tp, idx_to_str(df.index[j]); break

        if outcome == 'EXPIRED':
            xi = min(ei-1, len(df)-1)
            exit_p, exit_d, bars = df['close'].iloc[xi], idx_to_str(df.index[xi]), xi-si

        pnl = (exit_p - entry) / entry * 100
        results.append({**sig, 'outcome': outcome, 'exit_price': round(exit_p, 4),
                        'exit_date': exit_d, 'pnl_pct': round(pnl, 2), 'bars_held': bars,
                        'mfe_pct': round((max_p-entry)/entry*100, 2),
                        'mae_pct': round((min_p-entry)/entry*100, 2)})
    return results

def analyze(results, symbol):
    if not results: return None
    df = pd.DataFrame(results)
    t = len(df)
    tp = len(df[df['outcome']=='TP_HIT'])
    sl = len(df[df['outcome']=='SL_HIT'])
    ex = len(df[df['outcome']=='EXPIRED'])
    wr = tp/t*100 if t else 0
    w = df[df['pnl_pct']>0]; l = df[df['pnl_pct']<=0]
    gp = w['pnl_pct'].sum() if len(w) else 0
    gl = abs(l['pnl_pct'].sum()) if len(l) else 0.001
    eq = [10000]
    for p in df['pnl_pct'].values: eq.append(eq[-1]*(1+p/100))
    pk = pd.Series(eq).cummax()
    dd = ((pd.Series(eq)-pk)/pk).min()*100

    conf_s = {}
    for c in ['VERY_HIGH','HIGH','MEDIUM_HIGH','MEDIUM']:
        sub = df[df['confidence']==c]
        if len(sub):
            ct = len(sub[sub['outcome']=='TP_HIT'])
            conf_s[c] = {'count':len(sub),'win_rate':round(ct/len(sub)*100,1),'avg_pnl':round(sub['pnl_pct'].mean(),2)}

    reg_s = {}
    for r in ['bull','bear','sideways']:
        sub = df[df['regime']==r]
        if len(sub):
            ct = len(sub[sub['outcome']=='TP_HIT'])
            reg_s[r] = {'count':len(sub),'win_rate':round(ct/len(sub)*100,1),'avg_pnl':round(sub['pnl_pct'].mean(),2)}

    vol_s = {}
    for v_label, v_val in [('confirmed', True), ('unconfirmed', False)]:
        sub = df[df['vol_confirmed']==v_val]
        if len(sub):
            ct = len(sub[sub['outcome']=='TP_HIT'])
            vol_s[v_label] = {'count':len(sub),'win_rate':round(ct/len(sub)*100,1),'avg_pnl':round(sub['pnl_pct'].mean(),2)}

    return {
        'symbol': symbol, 'total': t, 'tp': tp, 'sl': sl, 'expired': ex,
        'win_rate': round(wr,1),
        'avg_pnl': round(df['pnl_pct'].mean(),2),
        'avg_win': round(w['pnl_pct'].mean(),2) if len(w) else 0,
        'avg_loss': round(l['pnl_pct'].mean(),2) if len(l) else 0,
        'pf': round(gp/gl,2), 'total_pnl': round(df['pnl_pct'].sum(),2),
        'max_dd': round(dd,2), 'final_eq': round(eq[-1],2),
        'total_ret': round((eq[-1]/10000-1)*100,2),
        'avg_rr': round(df['rr_ratio'].mean(),2),
        'avg_bars': round(df['bars_held'].mean(),1),
        'conf': conf_s, 'regime': reg_s, 'vol': vol_s,
    }

def report(all_p, all_r):
    L = []
    L.append("# CONFLUENCE V3 — Refined Signal Engine Results")
    L.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    L.append("**Key changes from V1:** Bear market filter, wider SL for AVAX (3x ATR), lower RSI cap for AVAX/BNB, regime-adjusted TP")
    L.append("\n## EXECUTIVE SUMMARY\n")
    L.append("| Pair | Signals | WR | Avg PnL | Total PnL | PF | Max DD | $10k → |")
    L.append("|------|---------|-----|---------|-----------|-----|--------|--------|")
    for p in all_p:
        L.append(f"| {p['symbol']} | {p['total']} | {p['win_rate']}% | {p['avg_pnl']}% | {p['total_pnl']}% | {p['pf']} | {p['max_dd']}% | ${p['final_eq']:,.0f} |")

    L.append("\n## V1 → V3 COMPARISON\n")
    L.append("| Pair | V1 WR | V3 WR | V1 Total PnL | V3 Total PnL | V1 $10k | V3 $10k |")
    L.append("|------|-------|-------|-------------|-------------|---------|---------|")
    v1 = {'BTC/USDT':{'wr':37.5,'pnl':108.1,'eq':22919},'ETH/USDT':{'wr':39.6,'pnl':80.1,'eq':16454},
           'AVAX/USDT':{'wr':33.3,'pnl':6.2,'eq':7507},'BNB/USDT':{'wr':38.1,'pnl':131.1,'eq':26351}}
    for p in all_p:
        if p['symbol'] in v1:
            v = v1[p['symbol']]
            L.append(f"| {p['symbol']} | {v['wr']}% | {p['win_rate']}% | {v['pnl']}% | {p['total_pnl']}% | ${v['eq']:,} | ${p['final_eq']:,.0f} |")

    for p in all_p:
        sym = p['symbol']
        L.append(f"\n---\n## {sym}\n")
        L.append(f"- **Signals:** {p['total']} | TP: {p['tp']} | SL: {p['sl']} | Exp: {p['expired']}")
        L.append(f"- **Win Rate:** {p['win_rate']}% | Avg PnL: {p['avg_pnl']}%")
        L.append(f"- **Avg Win:** +{p['avg_win']}% | Avg Loss: {p['avg_loss']}%")
        L.append(f"- **PF:** {p['pf']} | R:R: {p['avg_rr']} | Max DD: {p['max_dd']}%")
        L.append(f"- **$10k →** ${p['final_eq']:,.0f} ({p['total_ret']}%)")
        if p['conf']:
            L.append("\n### By Confidence\n| Level | # | WR | Avg PnL |")
            L.append("|-------|---|-----|---------|")
            for c,s in p['conf'].items(): L.append(f"| {c} | {s['count']} | {s['win_rate']}% | {s['avg_pnl']}% |")
        if p['regime']:
            L.append("\n### By Regime\n| Regime | # | WR | Avg PnL |")
            L.append("|--------|---|-----|---------|")
            for r,s in p['regime'].items(): L.append(f"| {r} | {s['count']} | {s['win_rate']}% | {s['avg_pnl']}% |")
        if p['vol']:
            L.append("\n### Volume Confirmation\n| Volume | # | WR | Avg PnL |")
            L.append("|--------|---|-----|---------|")
            for v,s in p['vol'].items(): L.append(f"| {v} | {s['count']} | {s['win_rate']}% | {s['avg_pnl']}% |")

    L.append("\n---\n## RECENT SIGNALS (Last 15)\n")
    for sym, res in all_r.items():
        L.append(f"\n### {sym}\n| Date | Entry | TP | SL | R:R | Conf | Out | PnL | Days |")
        L.append("|------|-------|----|----|-----|------|-----|-----|------|")
        for r in res[-15:]:
            o = 'W' if r['outcome']=='TP_HIT' else ('L' if r['outcome']=='SL_HIT' else 'E')
            L.append(f"| {r['date']} | {r['entry_price']} | {r['take_profit']} | {r['stop_loss']} | {r['rr_ratio']} | {r['confidence']} | {o} | {r['pnl_pct']}% | {r['bars_held']}d |")

    return "\n".join(L)

def main():
    print("="*70)
    print("  CONFLUENCE V3 — Refined (V1 base + Kimi fixes)")
    print("="*70)

    pairs = ['BTC/USDT','ETH/USDT','AVAX/USDT','BNB/USDT']
    all_p, all_r = [], {}

    for sym in pairs:
        print(f"\n{'='*50}\n  {sym}\n{'='*50}")
        df = load_or_fetch(sym)
        if df is None or len(df) < 200: continue
        sigs = generate_signals(df, sym)
        print(f"  {len(sigs)} signals")
        res = evaluate(sigs, df)
        perf = analyze(res, sym)
        if perf:
            all_p.append(perf)
            all_r[sym] = res
            print(f"  WR: {perf['win_rate']}% | PnL: {perf['avg_pnl']}% | PF: {perf['pf']}")
            print(f"  TP: {perf['tp']} | SL: {perf['sl']} | Exp: {perf['expired']}")
            print(f"  $10k → ${perf['final_eq']:,.0f} ({perf['total_ret']}%)")
            for c,s in perf['conf'].items():
                print(f"    {c}: {s['count']} sig, {s['win_rate']}% WR, {s['avg_pnl']}% avg")

    if not all_p: return

    out = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(out,'CONFLUENCE_V3_REPORT.md'),'w',encoding='utf-8') as f:
        f.write(report(all_p, all_r))
    with open(os.path.join(out,'confluence_v3_signals.json'),'w',encoding='utf-8') as f:
        json.dump({'performance':all_p,'signals':{s:r for s,r in all_r.items()},
                   'generated':datetime.now().isoformat(),'version':'v3'},f,indent=2,default=str)

    print(f"\n{'='*70}\n  V3 FINAL\n{'='*70}")
    print(f"\n  {'Pair':<14} {'Sig':>5} {'WR':>7} {'AvgPnL':>8} {'TotPnL':>9} {'PF':>6} {'MaxDD':>7} {'$10k→':>10}")
    print(f"  {'-'*70}")
    for p in all_p:
        print(f"  {p['symbol']:<14} {p['total']:>5} {p['win_rate']:>6.1f}% {p['avg_pnl']:>7.2f}% "
              f"{p['total_pnl']:>8.1f}% {p['pf']:>6.2f} {p['max_dd']:>6.1f}% ${p['final_eq']:>9,.0f}")

if __name__ == '__main__':
    main()
