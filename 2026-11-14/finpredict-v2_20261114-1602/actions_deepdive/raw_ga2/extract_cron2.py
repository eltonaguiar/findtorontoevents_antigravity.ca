import json,subprocess,re,os
rows=json.load(open('raw/GA2_matrix.json'))
ROOT='/home/eaguiar2015/findtorontoevents_antigravity.ca/.kilo/worktrees/finpredict-v2'
def show(p): return subprocess.run(['git','show',f'origin/main:{p}'],capture_output=True,text=True,cwd=ROOT).stdout
def crons_of(txt):
    crons=[]; in_sched=False; sched_indent=None
    for line in txt.splitlines():
        s=line.rstrip('\n')
        if not s.strip() or s.lstrip().startswith('#'): continue
        m=re.match(r'^(\s*)schedule:\s*$',s)
        if m: in_sched=True; sched_indent=len(m.group(1)); continue
        if in_sched:
            ind=len(s)-len(s.lstrip())
            if ind<=sched_indent and s.strip():
                in_sched=False
            else:
                cm=re.match(r"^\s*-?\s*cron:\s*(.+)$",s)
                if cm:
                    v=cm.group(1).strip().split('#')[0].strip().strip('"\'')
                    if re.match(r'^[\d*/,%\-]+( [\d*/,%\-]+){4}$',v): crons.append(v)
    return crons
out={}
for r in rows:
    p=r['path']; txt=show(p) if not p.startswith('dynamic/') else ''
    out[p]=dict(crons=crons_of(txt),has_schedule='schedule:' in txt and bool(crons_of(txt)) or bool(re.search(r'(?m)^\s*schedule:\s*$',txt)),
                has_dispatch=bool(re.search(r'(?m)^\s*workflow_dispatch:',txt)),
                has_push=bool(re.search(r'(?m)^\s*push:',txt)),has_pr=bool(re.search(r'(?m)^\s*pull_request:',txt)),len=len(txt))
json.dump(out,open('raw/GA2_cron.json','w'),indent=1)
print('with_cron',sum(bool(v['crons']) for v in out.values()))
print('schedule_block',sum(v['has_schedule'] for v in out.values()))
print('dispatch_only',sum(v['has_dispatch'] and not v['crons'] for v in out.values()))
for p in ['.github/workflows/walkforward-gate.yml','.github/workflows/secret-rotation-reminder.yml','.github/workflows/poc-picks-checkpoint.yml','.github/workflows/db-freshness-check.yml']:
    print(p,out[p]['crons'])
