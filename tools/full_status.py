import json, os

def load(f):
    if not os.path.exists(f): return {}
    with open(f) as fh: return json.load(fh)

# Pump Watch
pw = load('_pump_wl.json')
picks = pw.get('picks', [])
watching = [p for p in picks if p.get('status') == 'WATCHING']
resolved = [p for p in picks if p.get('status') == 'RESOLVED']

print("=" * 90)
print("PUMP WATCH — Live Status")
print("=" * 90)
print(f"  Active picks: {len(watching)}  |  Resolved: {len(resolved)}")
print()

# Show top 15 active by score
print("  Top Active Picks (sorted by score):")
for i, p in enumerate(watching[:20]):
    pnl = float(p.get('pnl_pct') or 0)
    pair = p['pair'].replace('ZUSD','/USD').replace('USD','/USD')
    score = float(p.get('pump_score', 0))
    grade = p.get('pump_grade', '?')
    color_marker = '***' if score >= 55 else '**' if score >= 45 else '*'
    print(f"    {i+1:>2}. {p['pair']:<18} Score:{score:>3.0f} [{grade:<10}] PnL:{pnl:>+7.2f}%")

# Show resolved with outcomes
if resolved:
    print(f"\n  Resolved Picks:")
    wins = losses = 0
    for p in resolved:
        pnl = float(p.get('pnl_pct') or 0)
        reason = p.get('exit_reason', '?')
        if 'TP' in reason: wins += 1
        elif 'SL' in reason: losses += 1
        print(f"    {p['pair']:<18} PnL:{pnl:>+7.2f}%  Exit:{reason}")
    print(f"    --> W:{wins} L:{losses} = {wins/(wins+losses)*100:.0f}% WR" if wins+losses>0 else "")

# Algo Battle
print("\n" + "=" * 90)
print("ALGO BATTLE ROYALE — Leaderboard")
print("=" * 90)
ab = load('_algo_lb.json')
for a in ab.get('leaderboard', []):
    total = int(a.get('total_picks', 0))
    opn = int(a.get('open_picks', 0))
    w = int(a.get('wins', 0))
    l = int(a.get('losses', 0))
    wr = a.get('win_rate', 0)
    avg = a.get('avg_pnl') or '--'
    print(f"  {a['algo_name']:<28} Picks:{total:>3} Open:{opn:>3} W:{w} L:{l} WR:{wr}% AvgPnL:{avg}")

# AI Predictions
print("\n" + "=" * 90)
print("AI PREDICTIONS — Current Status")
print("=" * 90)
ai = load('_ai_mon.json')
if ai.get('ok'):
    for p in ai.get('open_predictions', []):
        sym = p.get('symbol', '?')
        dir = p.get('direction', '?')
        live_pnl = p.get('live_pnl_pct', 0)
        hrs = p.get('hours_open', 0)
        conf = p.get('confidence', '?')
        tp_dist = p.get('dist_to_tp_pct', 0)
        sl_dist = p.get('dist_to_sl_pct', 0)
        print(f"  {sym:<6} {dir:<6} PnL:{live_pnl:>+6.2f}%  {hrs:.0f}h open  Conf:{conf:<7} TP:{tp_dist:.1f}% away  SL:{sl_dist:.1f}% away")

# GitHub Actions status
print("\n" + "=" * 90)
print("GITHUB ACTIONS — Recent Runs")
print("=" * 90)
print("  (Check gh run list output separately)")
