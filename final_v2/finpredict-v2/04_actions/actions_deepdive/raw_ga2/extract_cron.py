import json,subprocess,re
rows=json.load(open('raw/GA2_matrix.json'))
out={}
for r in rows:
    p=r['path']
    try:
        txt=subprocess.run(['git','show',f'origin/main:{p}'],capture_output=True,text=True,cwd='/home/eaguiar2015/findtorontoevents_antigravity.ca/.kilo/worktrees/finpredict-v2').stdout
    except Exception as e:
        txt=''
    crons=re.findall(r'cron:\s*["\']?([^"\'\n#]+)',txt)
    crons=[c.strip() for c in crons]
    has_schedule=bool(re.search(r'(?m)^\s*schedule:\s*$',txt))
    has_dispatch=bool(re.search(r'(?m)^\s*workflow_dispatch:',txt))
    has_push=bool(re.search(r'(?m)^\s*push:',txt))
    has_pr=bool(re.search(r'(?m)^\s*pull_request:',txt))
    out[p]=dict(crons=crons,has_schedule=has_schedule,has_dispatch=has_dispatch,has_push=has_push,has_pr=has_pr,len=len(txt))
json.dump(out,open('raw/GA2_cron.json','w'),indent=1)
missing=[p for p,v in out.items() if v['len']==0]
print('paths',len(out),'missing_from_origin_main',len(missing))
print('with_schedule',sum(v['has_schedule'] for v in out.values()))
print('with_cron_lines',sum(bool(v['crons']) for v in out.values()))
print('dispatch_only_no_cron',sum((v['has_dispatch'] and not v['crons']) for v in out.values()))
print('push_or_pr_no_cron',sum(((v['has_push'] or v['has_pr']) and not v['crons']) for v in out.values()))
print('missing sample',missing[:10])
