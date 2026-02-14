import urllib.request, json, ssl
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "UpdateCheck/1.0"})
    return json.loads(urllib.request.urlopen(req, context=ctx, timeout=15).read().decode())

# Pump Watch
print("=" * 80)
print("PUMP WATCH - Forensics Engine")
print("=" * 80)
d = fetch("https://findtorontoevents.ca/findcryptopairs/api/pump_forensics.php?action=watchlist&min_score=45")
picks = d.get('picks', [])
print(f"Total HIGH+ picks: {len(picks)}")
for p in picks[:25]:
    pnl = float(p.get('pnl_pct') or 0)
    print(f"  {p['pair']:<18} Score:{float(p['pump_score']):>3.0f}  {p['pump_grade']:<12} PnL:{pnl:>+7.2f}%  {p['status']}")

# Algo battle
print("\n" + "=" * 80)
print("ALGO BATTLE ROYALE - Leaderboard")
print("=" * 80)
try:
    d2 = fetch("https://findtorontoevents.ca/findcryptopairs/api/algo_battle.php?action=leaderboard")
    for a in d2.get('leaderboard', [])[:12]:
        print(f"  {a['algo_name']:<30} W:{a['wins']} L:{a['losses']} WR:{a['win_rate']}% PnL:{a['total_pnl']}%")
except Exception as e:
    print(f"  Error: {e}")

# Backtest arena
print("\n" + "=" * 80)
print("BACKTEST ARENA - Top Picks")
print("=" * 80)
try:
    d3 = fetch("https://findtorontoevents.ca/findcryptopairs/api/backtest100.php?action=top_picks")
    for p in d3.get('picks', [])[:10]:
        print(f"  {p['pair']:<16} {p['direction']}  Certainty:{p['certainty_score']}  WR:{p.get('avg_win_rate','?')}%  Strategies:{p.get('strategy_count','?')}")
except Exception as e:
    print(f"  Error: {e}")
