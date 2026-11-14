import json,csv,datetime as dt
wfs=json.load(open('raw/GA2_workflows.json'))['workflows']
cache=json.load(open('raw/GA2_runs_cache.json'))
now=dt.datetime(2026,11,14,17,50,0,tzinfo=dt.timezone.utc)
def parse(t):
    if not t: return None
    return dt.datetime.fromisoformat(t.replace('Z','+00:00'))
rows=[]
for w in wfs:
    wid=str(w['id']); c=cache.get(wid,{})
    def get(tag,k):
        d=c.get(tag) or {}
        return d.get(k)
    allr=(c.get('all') or {}).get('workflow_runs') or []
    mainr=(c.get('main') or {}).get('workflow_runs') or []
    ta=(c.get('all') or {}).get('total_count')
    tm=(c.get('main') or {}).get('total_count')
    lr_all=allr[0] if allr else {}
    lr_main=mainr[0] if mainr else {}
    la=parse(lr_all.get('run_started_at') or lr_all.get('created_at'))
    lm=parse(lr_main.get('run_started_at') or lr_main.get('created_at'))
    age_m=(now-lm).total_seconds()/3600 if lm else None
    age_a=(now-la).total_seconds()/3600 if la else None
    rows.append(dict(
        id=w['id'],name=w['name'],path=w['path'],state=w['state'],
        created=w.get('created_at'),updated=w.get('updated_at'),
        total_all=ta,total_main=tm,
        last_run_all=la.isoformat() if la else '',
        conclusion_all=lr_all.get('conclusion') or '',
        status_all=lr_all.get('status') or '',
        event_all=lr_all.get('event') or '',
        last_run_main=lm.isoformat() if lm else '',
        conclusion_main=lr_main.get('conclusion') or '',
        status_main=lr_main.get('status') or '',
        event_main=lr_main.get('event') or '',
        age_hours_main=round(age_m,1) if age_m is not None else '',
        age_hours_all=round(age_a,1) if age_a is not None else '',
        err_all=('__error__' in (c.get('all') or {})),
        err_main=('__error__' in (c.get('main') or {})),
    ))
rows.sort(key=lambda r:(r['state'],r['path']))
json.dump(rows,open('raw/GA2_matrix.json','w'),indent=1)
# summary
def bucket(r):
    if (r['total_all'] or 0)==0: return 'never'
    a=r['age_hours_all']
    if a=='': return 'never'
    d=a/24
    if d>180: return '>180d'
    if d>90: return '>90d'
    if d>30: return '>30d'
    if d>7: return '>7d'
    return 'active<=7d'
from collections import Counter
print('states',Counter(r['state'] for r in rows))
print('total_count_issue',[(r['id'],r['name'],r['total_all'],r['total_main']) for r in rows if r['total_all'] is None][:5])
print('errors_all',sum(r['err_all'] for r in rows),'errors_main',sum(r['err_main'] for r in rows))
print('bucket(all-branch last run):',Counter(bucket(r) for r in rows))
print('never total_all==0:',sum((r['total_all'] or 0)==0 for r in rows))
print('main never but all>0:',sum((r['total_main'] or 0)==0 and (r['total_all'] or 0)>0 for r in rows))
print('disabled:',[(r['name'],r['path']) for r in rows if r['state']!='active'])
