import json,datetime as dt,re
from collections import defaultdict,Counter
rows=json.load(open('raw/GA2_matrix.json'))
cron=json.load(open('raw/GA2_cron.json'))
now=dt.datetime(2026,11,14,17,50,0,tzinfo=dt.timezone.utc)
for r in rows:
    c=cron.get(r['path'],{})
    r['cron']='; '.join(c.get('crons',[]))
    r['has_cron']=bool(c.get('crons'))
    r['has_dispatch']=c.get('has_dispatch',False)
    r['has_push']=c.get('has_push',False)
    r['has_pr']=c.get('has_pr',False)
    r['yaml_present']=c.get('len',0)>0
    # age in days (all-branch effective last run)
    r['age_days']=round(r['age_hours_all']/24,1) if r['age_hours_all']!='' else None
    r['age_days_main']=round(r['age_hours_main']/24,1) if r['age_hours_main']!='' else None
    # bucket (mutually exclusive) using all-branch last run
    if (r['total_all'] or 0)==0 or r['age_days'] is None: b='never'
    elif r['age_days']>180: b='>180d'
    elif r['age_days']>90: b='>90d'
    elif r['age_days']>30: b='>30d'
    elif r['age_days']>7: b='>7d'
    else: b='<=7d'
    r['bucket']=b
    r['stale']= b in ('never','>7d','>30d','>90d','>180d')
    r['zombie']= r['state']=='active' and r['has_cron'] and (b=='never' or r['stale'])
json.dump(rows,open('raw/GA2_enriched.json','w'),indent=1)
def cnt(f): return sum(1 for r in rows if f(r))
print('BUCKETS',Counter(r['bucket'] for r in rows))
print('active',cnt(lambda r:r['state']=='active'),'disabled',cnt(lambda r:r['state']!='active'))
print('stale_total(any state)',cnt(lambda r:r['stale']),'active_stale',cnt(lambda r:r['stale'] and r['state']=='active'))
print('never active/disabled',cnt(lambda r:r['bucket']=='never' and r['state']=='active'),cnt(lambda r:r['bucket']=='never' and r['state']!='active'))
print('ZOMBIE active+cron+stale',cnt(lambda r:r['zombie']))
print('disabled with cron',cnt(lambda r:r['state']!='active' and r['has_cron']))
print('stale with cron',cnt(lambda r:r['stale'] and r['has_cron']))
print('-- non-cron stale (dispatch/push only) --',cnt(lambda r:r['stale'] and not r['has_cron']))
