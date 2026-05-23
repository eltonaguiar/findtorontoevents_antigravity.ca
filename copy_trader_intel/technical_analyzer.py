"""Multi-timeframe technical analysis for all active crypto picks."""
import sys, os, json, time
sys.stdout.reconfigure(encoding='utf-8')
if os.name == 'nt':
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

import urllib.request
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

BINANCE_URLS = [
    'https://data-api.binance.vision',
    'https://api.binance.com',
    'https://api1.binance.com',
]

def fetch_klines(symbol, interval, limit=200):
    for base in BINANCE_URLS:
        try:
            url = f'{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}'
            r = urllib.request.urlopen(url, timeout=10)
            return json.loads(r.read())
        except:
            continue
    return []

def sma(data, period):
    if len(data) < period: return None
    return sum(data[-period:]) / period

def ema(data, period):
    if len(data) < period: return None
    k = 2 / (period + 1)
    e = sum(data[:period]) / period
    for p in data[period:]:
        e = p * k + e * (1 - k)
    return e

def calc_rsi(closes, period=14):
    if len(closes) < period + 1: return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i-1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0: return 100
    return 100 - (100 / (1 + avg_gain / avg_loss))

def calc_macd(closes):
    e12 = ema(closes, 12)
    e26 = ema(closes, 26)
    if e12 is None or e26 is None: return None, None
    ml = e12 - e26
    macd_vals = []
    for i in range(26, len(closes)):
        a = ema(closes[:i+1], 12)
        b = ema(closes[:i+1], 26)
        if a and b: macd_vals.append(a - b)
    ms = ema(macd_vals, 9) if len(macd_vals) >= 9 else None
    return ml, ms

def classify(r, ml, ms, price, s20, s50, s200, e9, e21):
    buys = sells = neutrals = 0
    if r is not None:
        if r < 30: buys += 1
        elif r > 70: sells += 1
        else: neutrals += 1
    if ml is not None and ms is not None:
        if ml > ms: buys += 1
        else: sells += 1
    for ma in [s20, s50, s200, e9, e21]:
        if ma is not None:
            if price > ma: buys += 1
            else: sells += 1
    if buys > sells + 2: return 'STRONG BUY', buys, sells
    elif buys > sells: return 'BUY', buys, sells
    elif sells > buys + 2: return 'STRONG SELL', buys, sells
    elif sells > buys: return 'SELL', buys, sells
    return 'NEUTRAL', buys, sells

def analyze_symbol(sym):
    results = {}
    for interval in ['1h', '4h', '1d']:
        try:
            klines = fetch_klines(sym, interval, 200)
            if not klines: continue
            closes = [float(k[4]) for k in klines]
            vols = [float(k[5]) for k in klines]
            price = closes[-1]
            r = calc_rsi(closes)
            ml, ms = calc_macd(closes)
            s20, s50, s200 = sma(closes, 20), sma(closes, 50), sma(closes, 200)
            e9, e21 = ema(closes, 9), ema(closes, 21)
            avg_vol = sum(vols[-20:-1]) / 19 if len(vols) >= 20 else sum(vols) / max(len(vols), 1)
            vol_ratio = vols[-1] / avg_vol if avg_vol > 0 else 1
            verdict, b, s = classify(r, ml, ms, price, s20, s50, s200, e9, e21)
            results[interval] = {
                'verdict': verdict, 'rsi': r, 'buys': b, 'sells': s,
                'vol_ratio': vol_ratio, 'price': price
            }
        except:
            continue
    return results


def run():
    # Load active picks
    payload_path = os.path.join(os.path.dirname(__file__), '..', 'audit_trail', 'data', 'dashboard_payload.json')
    if not os.path.exists(payload_path):
        print('[TECH] No dashboard payload found')
        return

    with open(payload_path, encoding='utf-8') as f:
        d = json.load(f)

    ap = d.get('picks', {}).get('active', [])
    crypto = [p for p in ap if (p.get('asset_class', '') or '').upper() == 'CRYPTO'
              and (p.get('symbol', '') or '').endswith('USDT')]

    # Deduplicate by symbol (take highest scored)
    sym_best = {}
    for p in crypto:
        sym = p.get('symbol', '')
        score = p.get('score', 0) or 0
        if sym not in sym_best or score > (sym_best[sym].get('score', 0) or 0):
            sym_best[sym] = p

    unique_syms = sorted(sym_best.keys(), key=lambda s: -(sym_best[s].get('score', 0) or 0))
    print(f'[TECH] Analyzing {len(unique_syms)} unique crypto symbols...')

    # --- GITHUB_ACTIONS connectivity check: skip if Binance unreachable ---
    if os.environ.get('GITHUB_ACTIONS'):
        reachable = False
        for base in BINANCE_URLS:
            try:
                urllib.request.urlopen(f'{base}/api/v3/ping', timeout=5)
                reachable = True
                break
            except Exception:
                continue
        if not reachable:
            print('[TECH] Binance unreachable (geo-block?) — skipping technical analysis')
            return

    # --- Parallel fetch: 10 workers, circuit breaker on first 3 failures ---
    ta_results = {}  # sym -> analyze_symbol result
    early_failures = []

    def _worker(sym):
        return sym, analyze_symbol(sym)

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(_worker, sym): sym for sym in unique_syms}
        circuit_broken = False
        for fut in as_completed(futures):
            sym = futures[fut]
            try:
                _, ta = fut.result()
                ta_results[sym] = ta
                # Circuit breaker: track first 3 symbols submitted (by order)
                if len(ta_results) + len(early_failures) <= 3:
                    if not ta:
                        early_failures.append(sym)
                    if len(early_failures) >= 3:
                        circuit_broken = True
                        print('[TECH] Circuit breaker: first 3 symbols all failed — Binance likely blocked')
                        pool.shutdown(wait=False, cancel_futures=True)
                        break
            except Exception:
                if len(ta_results) + len(early_failures) <= 3:
                    early_failures.append(sym)
                    if len(early_failures) >= 3:
                        circuit_broken = True
                        print('[TECH] Circuit breaker: first 3 symbols all failed — Binance likely blocked')
                        pool.shutdown(wait=False, cancel_futures=True)
                        break

    if circuit_broken:
        return

    elapsed = time.time() - t0
    print(f'[TECH] Fetched {len(ta_results)} symbols in {elapsed:.1f}s (parallel)')

    # --- Build results from parallel data ---
    results_all = []
    for sym in unique_syms:
        ta = ta_results.get(sym, {})
        if not ta:
            continue
        p = sym_best[sym]
        try:
            if not ta.get('1h') and not ta.get('4h'):
                continue

            direction = (p.get('direction', '') or '').upper()
            score = p.get('score', 0) or 0
            pnl = p.get('pnl_pct')
            pnl_str = f'{float(pnl):+.2f}%' if pnl is not None else 'N/A'
            strategy = (p.get('strategy', '') or '')[:25]

            verdicts = [ta[tf]['verdict'] for tf in ['1h', '4h', '1d'] if ta.get(tf)]
            buy_tfs = sum(1 for v in verdicts if 'BUY' in v)
            sell_tfs = sum(1 for v in verdicts if 'SELL' in v)

            if direction in ('LONG', 'BUY'):
                aligned = buy_tfs >= 2
                alignment = f'{buy_tfs}/3 BUY'
            elif direction in ('SHORT', 'SELL'):
                aligned = sell_tfs >= 2
                alignment = f'{sell_tfs}/3 SELL'
            else:
                aligned = True
                alignment = '?'

            rsi_1h = ta['1h']['rsi'] if ta.get('1h') and ta['1h'].get('rsi') else None
            rsi_4h = ta['4h']['rsi'] if ta.get('4h') and ta['4h'].get('rsi') else None
            vol_4h = ta['4h']['vol_ratio'] if ta.get('4h') else None

            results_all.append({
                'sym': sym, 'dir': direction, 'score': score, 'pnl': pnl_str,
                'strategy': strategy, 'aligned': aligned, 'alignment': alignment,
                'rsi_1h': rsi_1h, 'rsi_4h': rsi_4h, 'vol_4h': vol_4h,
                'v_1h': ta.get('1h', {}).get('verdict', '?') if ta.get('1h') else '?',
                'v_4h': ta.get('4h', {}).get('verdict', '?') if ta.get('4h') else '?',
                'v_1d': ta.get('1d', {}).get('verdict', '?') if ta.get('1d') else '?',
                'buy_tfs': buy_tfs, 'sell_tfs': sell_tfs,
            })
        except Exception:
            continue

    results_all.sort(key=lambda x: (-x['aligned'], -x['score']))

    aligned_picks = [r for r in results_all if r['aligned']]
    misaligned = [r for r in results_all if not r['aligned']]

    print(f'[TECH] Analyzed {len(results_all)} symbols')
    print()

    print(f'TECHNICALLY ALIGNED ({len(aligned_picks)} picks):')
    print(f'{"SYM":<14} {"DIR":<6} {"SCORE":>5} {"PnL":>8} {"RSI4H":>6} {"VOL":>5} {"1H":<12} {"4H":<12} {"1D":<12} {"AGREE":<8}')
    print('-' * 100)
    for r in aligned_picks[:40]:
        rsi_s = f'{r["rsi_4h"]:.0f}' if r['rsi_4h'] else '?'
        vol_s = f'{r["vol_4h"]:.1f}x' if r['vol_4h'] else '?'
        print(f'{r["sym"]:<14} {r["dir"]:<6} {r["score"]:>5.0f} {r["pnl"]:>8} {rsi_s:>6} {vol_s:>5} {r["v_1h"]:<12} {r["v_4h"]:<12} {r["v_1d"]:<12} {r["alignment"]:<8}')

    print()
    print(f'TECHNICALLY MISALIGNED ({len(misaligned)} picks):')
    print(f'{"SYM":<14} {"DIR":<6} {"SCORE":>5} {"PnL":>8} {"RSI4H":>6} {"VOL":>5} {"1H":<12} {"4H":<12} {"1D":<12} {"AGREE":<8}')
    print('-' * 100)
    for r in misaligned[:40]:
        rsi_s = f'{r["rsi_4h"]:.0f}' if r['rsi_4h'] else '?'
        vol_s = f'{r["vol_4h"]:.1f}x' if r['vol_4h'] else '?'
        print(f'{r["sym"]:<14} {r["dir"]:<6} {r["score"]:>5.0f} {r["pnl"]:>8} {rsi_s:>6} {vol_s:>5} {r["v_1h"]:<12} {r["v_4h"]:<12} {r["v_1d"]:<12} {r["alignment"]:<8}')

    # Performance comparison
    a_pnls = [float(r['pnl'].replace('%', '')) for r in aligned_picks if r['pnl'] != 'N/A']
    m_pnls = [float(r['pnl'].replace('%', '')) for r in misaligned if r['pnl'] != 'N/A']
    a_wr = sum(1 for x in a_pnls if x > 0) / len(a_pnls) * 100 if a_pnls else 0
    m_wr = sum(1 for x in m_pnls if x > 0) / len(m_pnls) * 100 if m_pnls else 0
    a_avg = sum(a_pnls) / len(a_pnls) if a_pnls else 0
    m_avg = sum(m_pnls) / len(m_pnls) if m_pnls else 0

    print()
    print('=' * 60)
    print(f'ALIGNED:    {len(aligned_picks)} picks, WR={a_wr:.0f}%, avg PnL={a_avg:+.2f}%')
    print(f'MISALIGNED: {len(misaligned)} picks, WR={m_wr:.0f}%, avg PnL={m_avg:+.2f}%')
    print(f'EDGE:       {a_wr - m_wr:+.1f}% WR advantage for aligned picks')

    # Save results
    out_path = os.path.join(os.path.dirname(__file__), 'data', 'technical_analysis.json')
    output = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'total_analyzed': len(results_all),
        'aligned_count': len(aligned_picks),
        'misaligned_count': len(misaligned),
        'aligned_wr': round(a_wr, 1),
        'misaligned_wr': round(m_wr, 1),
        'aligned_avg_pnl': round(a_avg, 2),
        'misaligned_avg_pnl': round(m_avg, 2),
        'edge_wr': round(a_wr - m_wr, 1),
        'picks': results_all,
    }
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)
    print(f'\n[TECH] Saved to {out_path}')


if __name__ == '__main__':
    run()
