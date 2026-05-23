import json
comp = json.load(open('data/live_competition.json'))
losers = [(a['id'], a['name'], float(a.get('totalReturn',0)), len(a.get('activePicks',[]))) for a in comp['algorithms'] if float(a.get('totalReturn',0)) < -0.3]
losers.sort(key=lambda x: x[2])
for aid, name, ret, active in losers:
    print(f'{ret:>+.3f}%  active:{active}  {aid}')
