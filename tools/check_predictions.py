"""Check live prediction status from the tracker API."""
import urllib.request
import json

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
API = 'https://findtorontoevents.ca/findcryptopairs/api/prediction_tracker.php'

def fetch(action):
    url = API + '?action=' + action
    req = urllib.request.Request(url, headers=HEADERS)
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())

def main():
    data = fetch('monitor')
    stats = fetch('stats')

    print("=" * 70)
    print("  AI PREDICTION TRACKER - LIVE STATUS")
    print("  " + data.get('timestamp', ''))
    print("=" * 70)
    print()

    s = stats.get('overall', {})
    print("  SCOREBOARD: %d total | %d open | %d resolved | W:%s L:%s | Win rate: %s%%" % (
        s.get('total_predictions', 0), s.get('open', 0), s.get('resolved', 0),
        s.get('wins', 0), s.get('losses', 0), s.get('win_rate', 0)
    ))
    if s.get('avg_pnl') is not None:
        print("  Avg P&L: %.2f%% | Best: %s%% | Worst: %s%%" % (
            float(s['avg_pnl']), s.get('best_trade', '--'), s.get('worst_trade', '--')
        ))
    print()

    # Open predictions
    open_preds = data.get('open_predictions', [])
    if open_preds:
        print("  OPEN PREDICTIONS (%d)" % len(open_preds))
        print("  " + "-" * 66)
        for p in open_preds:
            pnl = float(p.get('live_pnl_pct') or p.get('pnl_pct') or 0)
            peak = float(p.get('peak_pnl_pct') or 0)
            trough = float(p.get('trough_pnl_pct') or 0)
            dist_tp = p.get('dist_to_tp_pct', '?')
            dist_sl = p.get('dist_to_sl_pct', '?')
            hours = p.get('hours_open', '?')
            conf = p.get('confidence', '?')

            arrow = "+" if pnl >= 0 else ""
            status = "OK" if pnl >= 0 else "!!"
            emoji = "G" if pnl >= 0 else "R"

            print()
            print("  [%s] %s  (%s / %s)" % (emoji, p['symbol'], conf, p.get('direction', 'LONG')))
            print("      Current P&L: %s%.2f%%  |  Peak: %+.2f%%  |  Trough: %+.2f%%" % (arrow, pnl, peak, trough))
            print("      Entry: %s  |  Live: %s" % (p.get('entry_price', '?'), p.get('live_price', '?')))
            print("      TP in: %s%%  |  SL in: %s%%  |  Open: %sh" % (dist_tp, dist_sl, hours))
    else:
        print("  No open predictions.")

    # Resolved
    resolved = data.get('just_resolved', []) + data.get('recent_resolved', [])
    seen = set()
    unique = []
    for r in resolved:
        rid = r.get('id')
        if rid not in seen:
            seen.add(rid)
            unique.append(r)

    if unique:
        print()
        print("  RESOLVED (%d)" % len(unique))
        print("  " + "-" * 66)
        for p in unique:
            pnl = float(p.get('pnl_pct') or 0)
            reason = p.get('exit_reason', '?')
            tag = "WIN" if reason == 'TP_HIT' else ("LOSS" if reason == 'SL_HIT' else "EXPIRED")
            print("  [%s] %s  P&L: %+.2f%%  (%s)" % (tag, p['symbol'], pnl, reason))

    print()
    print("=" * 70)

if __name__ == '__main__':
    main()
