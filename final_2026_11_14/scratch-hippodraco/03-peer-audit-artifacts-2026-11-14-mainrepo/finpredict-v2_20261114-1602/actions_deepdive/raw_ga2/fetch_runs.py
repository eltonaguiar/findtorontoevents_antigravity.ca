import json, subprocess, sys, time, os
from concurrent.futures import ThreadPoolExecutor, as_completed

REPO="eltonaguiar/findtorontoevents_antigravity.ca"
wfs=json.load(open('raw/GA2_workflows.json'))['workflows']
os.makedirs('raw/runs',exist_ok=True)

def call(url):
    for attempt in range(4):
        p=subprocess.run(['gh','api',url],capture_output=True,text=True)
        if p.returncode==0:
            try: return json.loads(p.stdout)
            except Exception: pass
        err=p.stderr.strip()
        if 'rate limit' in err.lower() or '403' in err:
            time.sleep(30*(attempt+1)); continue
        if '404' in err or 'Not Found' in err:
            return {'__error__':'404','__msg__':err[:300]}
        time.sleep(2*(attempt+1))
    return {'__error__':'fail','__msg__':p.stderr.strip()[:300]}

def job(w):
    wid=w['id']
    res={}
    for tag,q in (('all','?per_page=1'),('main','?branch=main&per_page=1')):
        path=f'raw/runs/{wid}_{tag}.json'
        if os.path.exists(path):
            try:
                res[tag]=json.load(open(path)); continue
            except Exception: pass
        d=call(f'repos/{REPO}/actions/workflows/{wid}/runs{q}')
        res[tag]=d
        json.dump(d,open(path,'w'))
    return wid,res

# rate check
rl=call('rate_limit')
print('rate before', rl.get('rate'),flush=True)

out={}
done=0
with ThreadPoolExecutor(max_workers=8) as ex:
    futs={ex.submit(job,w):w for w in wfs}
    for f in as_completed(futs):
        w=futs[f]
        try:
            wid,res=f.result(); out[wid]=res
        except Exception as e:
            out[w['id']]={'__error__':str(e)}
        done+=1
        if done%50==0: print('done',done,flush=True)
json.dump(out,open('raw/GA2_runs_cache.json','w'))
print('TOTAL',len(out))
