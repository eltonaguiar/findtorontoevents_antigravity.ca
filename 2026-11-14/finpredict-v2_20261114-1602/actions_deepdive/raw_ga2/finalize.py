import json,re
rows=json.load(open('raw/GA2_enriched.json'))
cron=json.load(open('raw/GA2_cron.json'))
def cadence(crons):
    if not crons: return (None,None)
    c=crons[0].split()
    if len(c)!=5: return ('unknown',None)
    mi,ho,dom,mon,dow=c
    if mon!='*' and (mon.startswith('*/') or mon!='*'):
        # specific months
        if mon.startswith('*/'): return ('quarterly~',100)
        return ('annual/specific-month',380)
    if dow!='*': return ('weekly',8)
    if dom!='*': return ('monthly',40)
    if ho=='*' or '/' in ho or ',' in ho or mi=='*' or '/' in mi or ',' in mi:
        return ('intraday',1.5)
    return ('daily',2.5)
for r in rows:
    c=cron.get(r['path'],{})
    r['cron']='; '.join(c.get('crons',[]))
    r['has_cron']=bool(c.get('crons'))
    r['yaml_present']=c.get('len',0)>0
    cad,gap=cadence(c.get('crons',[]))
    r['cadence']=cad or ('none' if not c.get('crons') else 'unknown')
    r['max_gap_days']=gap
    if c.get('crons'):
        if r['age_days'] is None: overdue=True
        else: overdue = gap is not None and r['age_days']> (gap*1.5+2)
    else: overdue=False
    r['cadence_overdue']=bool(overdue and r['state']=='active')
    # zombie = active + cron + cadence overdue
    r['zombie']=r['cadence_overdue']
json.dump(rows,open('raw/GA2_final.json','w'),indent=1)
print('active+cron',sum(1 for r in rows if r['state']=='active' and r['has_cron']))
print('cadence_overdue(active)',sum(1 for r in rows if r['zombie']))
print('-- overdue list --')
for r in rows:
    if r['zombie']:
        print(f"{r['cadence']:22} gap={r['max_gap_days']} age={r['age_days']} {r['bucket']:7} {r['name'][:38]:38} cron=[{r['cron']}]")
from collections import Counter
print('cadence dist active',Counter(r['cadence'] for r in rows if r['state']=='active'))
