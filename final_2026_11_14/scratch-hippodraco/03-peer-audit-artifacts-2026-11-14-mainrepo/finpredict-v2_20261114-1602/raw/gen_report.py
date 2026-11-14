import json,datetime as dt,collections,csv,os
now=dt.datetime(2026,11,14,16,5,tzinfo=dt.timezone.utc)
rows=json.load(open('raw/A_rows.json'))
all7=json.load(open('raw/A_all7d_runs.json'))
f48=json.load(open('raw/A_fail48.json'))
def p(s): return dt.datetime.fromisoformat(s.replace('Z','+00:00'))
def age_h(s): return (now-p(s)).total_seconds()/3600
def g(c,k): return c.get(k,0)
# --- CSV matrix ---
with open('sub/A_workflow_matrix.csv','w',newline='') as fh:
    w=csv.writer(fh)
    w.writerow(['workflow','path','state','last_run_utc','age_h','last_status','last_conclusion','last_event','runs24','success24','failure24','cancelled24','runs7','success7','failure7','cancelled7'])
    for r in sorted(rows,key=lambda x:(-sum(x['c7'].values()),x['name'])):
        last=r['last']
        w.writerow([r['name'],r['path'],r['state'],last['created_at'] if last else '',r['age_h'] if last else '',last['status'] if last else '',last['conclusion'] if last else '',last['event'] if last else '',
                    sum(r['c24'].values()),g(r['c24'],'success'),g(r['c24'],'failure'),g(r['c24'],'cancelled'),
                    sum(r['c7'].values()),g(r['c7'],'success'),g(r['c7'],'failure'),g(r['c7'],'cancelled')])
# --- aggregates ---
c24={k:sum(r['c24'].get(k,0) for r in rows) for k in ['success','failure','cancelled','skipped','running','neutral']}
c7={k:sum(r['c7'].get(k,0) for r in rows) for k in ['success','failure','cancelled','skipped','running','neutral']}
tot24=sum(c24.values()); tot7=sum(c7.values())
never=[r for r in rows if r['last'] is None]
stale=[r for r in rows if r['last'] and r['age_h']>168]
failwf24=collections.Counter(x['wf'] for x in all7 if x['conclusion']=='failure' and age_h(x['created_at'])<=24)
failwf48=collections.Counter(x['wf'] for x in f48)
latest={}
for x in all7:
    if x['conclusion']=='failure' and age_h(x['created_at'])<=24:
        if x['wf'] not in latest or x['created_at']>latest[x['wf']]['created_at']: latest[x['wf']]=x
def badstep(rid):
    try: d=json.load(open(f'raw/jobs/{rid}.json'))
    except: return 'UNVERIFIED (no job data)'
    for j in d['jobs']:
        if j['conclusion'] not in ('success','skipped',None):
            bad=[s['name'] for s in j['steps'] if s['conclusion'] not in ('success','skipped',None)]
            return f"`{j['name']}` / {bad[0] if bad else '?'}"
    return '_run retrying (no completed failed job now)_'
root={
 '43609547717':'`KeyError: \'LONG\'` after data-source failures: Binance HTTP 451, CoinMetrics 400/403, `No module named xgboost`, `\'high\'`/`\'close\'` KeyErrors',
 '43608586741':'same `KeyError: \'LONG\'`; 508 error-ish lines in log',
 '43609430834':'UNVERIFIED — run retrying (attempt 3 in progress at snapshot)',
 '43605861085':'UNVERIFIED — run retrying (attempt 4, jobs test(3.11)/test(3.12) still running)',
 '43603128044':'UNVERIFIED — run retrying (attempt 5 in progress)',
 '43602685216':'pandas 2.1.4 source build under Python 3.14: `_PyLong_AsByteArray` expected 6 args, have 5',
 '43593382356':'same pandas/Python-3.14 build failure',
 '43593223780':'same pandas/Python-3.14 build failure',
 '43593359756':'same pandas/Python-3.14 build failure',
 '43593366467':'same pandas/Python-3.14 build failure',
 '43592761629':'same pandas/Python-3.14 build failure',
 '43575056444':'`OSError: [Errno 24] Too many open files` in `alpha_engine/__init__.py`',
 '43593034946':'same pandas/Python-3.14 build failure',
 '43592941157':'same pandas/Python-3.14 build failure',
 '43593541152':'`The action \'Download from findtorontoevents.ca (50webs FTP)\' has timed out after 30 minutes`',
 '43544373994':'`fetch_prices.php returned HTTP 404` (expected 200) — daily_prices ingest broken',
 '43596188828':'UNVERIFIED — run retrying (attempt 8 at snapshot)',
 '43603342689':'UNVERIFIED — run retrying (attempt 3 in progress)',
 '43521235051':'`ModuleNotFoundError: No module named \'tools\'`',
 '43559740169':'`No artifacts named "github-pages" were found for this workflow run`',
 '43546586116':'`ERROR: All 8 push attempts failed`',
 '43520036730':'`ERROR: All 10 push attempts failed — next cycle will self-heal.`',
 '43502887476':'`##[error]Process completed with exit code 28` (curl timeout in deploy verification)',
 '43566181363':'exit code 1; no error line in job log (UNVERIFIED detail)',
}
# --- md ---
L=[]
A=L.append
A('FAIL')
A('')
A('# Subagent A — GitHub Actions health audit')
A('')
A(f'Repo: `eltonaguiar/findtorontoevents_antigravity.ca`  |  Snapshot: **2026-11-14T16:05Z**  |  Auditor: Subagent A')
A('')
A('> All counts below are derived from GitHub API output captured 16:03–16:08Z. Run statuses move; a handful of runs captured as `failure` were later auto-retried (attempts 2–8) and were `in_progress` again when logs were requested. That is called out where it applies.')
A('')
A('## 1. Summary counts')
A('')
A('| Metric | Value |')
A('|---|---|')
A(f'| Total workflows in repo | **365** (361 active, 4 `disabled_manually`) |')
A(f'| Workflows that ran in last 24h | **269** |')
A(f'| Workflows that ran in last 7d | **309** |')
A(f'| Workflows that never ran (all-time) | **20** |')
A(f'| Workflows stale >7d (last run older than 7d) | **36** |')
A(f'| Zero-run in 7d (never + stale) | **56** |')
A(f'| Runs in 24h (reconstructed) | **{tot24:,}** ({c24["success"]:,} success, {c24["failure"]:,} failure, {c24["cancelled"]:,} cancelled, {c24["skipped"]:,} skipped, {c24["running"]} running) |')
A(f'| Runs in 7d (reconstructed) | **{tot7:,}** ({c7["success"]:,} success, {c7["failure"]:,} failure, {c7["cancelled"]:,} cancelled, {c7["skipped"]:,} skipped, {c7["running"]} in progress) |')
A(f'| Failing workflows | **24** in 24h (214 failed runs) / **88** in 7d (1,207 failed runs) |')
A(f'| Cancelled runs | **82** in 24h; **642** in 7d |')
A(f'| Cancelled with zero jobs executed | **15** in 24h (all 82 checked); 7d not exhaustively checked |')
A(f'| Timed-out runs (`timed_out`) | **0** in 24h and 7d |')
A(f'| Last run failed | **25 workflows** |')
A(f'| Last run cancelled | **11 workflows** |')
A(f'| Last run in progress | **18 workflows** |')
A('')
A('Definition note: "24h/7d" windows end at 2026-11-14T16:05Z (same clock as the run list capture). Per-workflow totals come from `total_count`; run-level breakdowns come from fully paginated run arrays (all 96 workflows with >100 runs in 7d were paginated to completion).')
A('')
A('## 2. Failure clusters (last 24h, with 48h totals)')
A('')
A('| Workflow | Fail 24h | Fail 48h | Latest failing run | Created (UTC) | Failing job / step | Root error |')
A('|---|---:|---:|---|---|---|---|')
for wf in sorted(latest,key=lambda w:-failwf24[w]):
    x=latest[wf]; rid=str(x['id'])
    A(f'| {wf} | {failwf24[wf]} | {failwf48[wf]} | [{rid}](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/{rid}) | {x["created_at"]} | {badstep(rid)} | {root.get(rid,"not inspected")} |')
A('')
A('### Dominant root causes')
A('')
A('1. **Python 3.14 vs pandas 2.1.4 (largest cluster, at least 9 workflows).** Workflows pin `python-version: \'3.11\'` with `actions/setup-python@v6` but also pass invalid input `update-environment: false`; the job then resolves the system interpreter (`/usr/include/python3.14`, pip from `/usr/lib/python3/dist-packages`), and `pandas==2.1.4` compiles from source and dies with `too few arguments to function ‘_PyLong_AsByteArray’; expected 6, have 5`.')
A('2. **Alpha Engine fatal `KeyError: \'LONG\'`** in 2 workflows (93 failed runs/24h combined), preceded by data-source failures: Binance HTTP 451 (geo), CoinMetrics 400/403 circuit breaker, `No module named \'xgboost\'`, and per-strategy `KeyError: \'high\'/\'close\'`.')
A('3. **Git push contention**: Live Spike and H-002 PEAD exhaust 8 and 10 retry attempts (`All N push attempts failed`) — consistent with the known high-commit-frequency main branch.')
A('4. **FTP/dashboard ops**: Mirror timed out at the 30-min step cap; `fetch_prices.php` returns HTTP 404; Pages deploy fails because no `github-pages` artifact was uploaded.')
A('5. **Python import style**: `ModuleNotFoundError: No module named \'tools\'` in `refresh_daily_prices_yf.py` (the documented relative-vs-direct-script gotcha in AGENTS.md).')
A('')
A('## 3. Stale and never-run workflows')
A('')
A('### Never run (20)')
A('')
A('| Workflow | Path | State |')
A('|---|---|---|')
for r in sorted(never,key=lambda x:x['name']): A(f'| {r["name"]} | `{r["path"]}` | {r["state"]} |')
A('')
A('### Stale >7d (36)')
A('')
A('| Workflow | Last run (UTC) | Age | Last conclusion | 7d runs |')
A('|---|---|---:|---|---:|')
for r in sorted(stale,key=lambda x:-x['age_h']):
    A(f'| {r["name"]} | {r["last"]["created_at"]} | {r["age_h"]/24:.1f}d | {r["last"]["conclusion"]} | {sum(r["c7"].values())} |')
A('')
A('Note: some stale entries are legitimately low-frequency schedules (monthly workflows last run 2026-11-01, e.g. ML Monthly Full Retrain, Monthly DNA Tournament) or intentionally disabled (`Forex Agent`, `Forex Smart Picks`, `AI Tournament Pipeline`, `Real-Time Battle Test`). The rest (last run May–October) appear abandoned.')
A('')
A('## 4. Dashboard-pipeline health (`audit-dashboard.yml`, id 281988696)')
A('')
A('| Metric | 24h | 7d |')
A('|---|---:|---:|')
A('| Runs | 24 | 168 |')
A('| Success | 13 | 106 |')
A('| Cancelled | 10 | 61 |')
A('| In progress at snapshot | 1 | 1 |')
A('| Success rate | 54.2% | 63.1% |')
A('')
A('- Cron is `10 * * * *`; concurrency group `dashboard-publish`, `cancel-in-progress: false`, job `timeout-minutes: 115`.')
A('- **Runtime has grown far past the documented 30–35 min.** Five sampled successful jobs ran **79.6, 81.9, 84.5, 86.7 and 104.2 minutes** (job `started_at`→`completed_at`; median 84.5 min for n=5). Run created→updated median was 121.0 min including queueing.')
A('- With an hourly schedule and ~80–105 min jobs, GitHub keeps only the newest pending run per concurrency group and cancels older queued ones: **9 of the 24h cancellations were zero-job, queued audit-dashboard runs** (43470794969, 43500038928, 43517634445, 43535071245, 43545655088, 43560599415, 43570175588, 43589060993, 43603788378). 61/168 (36%) of 7d runs cancelled.')
A('- Effect: the dashboard refreshes roughly every ~1.5–2h, not hourly — consistent with the peer finding that live payloads were ~1.4–1.6h old at 15:45Z.')
A('- `push:` trigger remains absent as documented (2026-05-19 removal rationale intact in the workflow comments).')
A('')
A('### Related pipeline workflows (last run snapshot)')
A('')
A('| Workflow | Last run (UTC) | Age | Last conclusion | 24h runs | 24h fail |')
A('|---|---|---:|---|---:|---:|')
pipeline=['281988696','281990568','281981504','281983928','282049698','281989712','283086441','282205657','282205659','281981993','282667220','282050973','282048478','281989494','282048946','281978514']
byid={r['id']:r for r in rows}
for wid in pipeline:
    r=byid.get(wid)
    if not r: continue
    if r['last']:
        A(f'| {r["name"]} | {r["last"]["created_at"]} | {r["age_h"]/24:.1f}d | {r["last"]["conclusion"]} | {sum(r["c24"].values())} | {g(r["c24"],"failure")} |')
    else:
        A(f'| {r["name"]} | never | — | — | 0 | 0 |')
A('')
A('## 5. In-progress / retry-loop risk')
A('')
A('- At capture, 17 runs were `in_progress`; most were fresh (<10 min). Two exceeded 3.5h: `Discord Bot  Persistent` (43593989922, started 12:16Z) and `DNA Strategy Pipeline` (43594177096, attempt 5).')
A('- Several 48h failure records were re-running with high attempt counts at log time (`run_attempt` 3–8), indicating automated rerun/failure-guardian flapping: Sports smoke (a3), CI Tests (a4), Market Beating (a5), ALPHA Live (a3), robust-edge-miner (a8), DNA Strategy (a5), Daily Price Refresh (a8), Daily Prices yfinance (a8), H-002 PEAD (a8), Verified pilot daily (a8).')
A('')
A('## 6. Warnings / deprecations')
A('')
A('- GitHub annotations: **3** `##[warning]` lines, all `Node.js 20 is deprecated ... forced to run on Node.js 24` (`actions/checkout@v4`, `actions/setup-python@v5`, `actions/download-artifact@v5`).')
A('- No `::warning::` annotations were emitted; the 2 literal occurrences are echoed script text inside H-002 PEAD.')
A('- Runtime `WARN` lines in the 19 sampled non-empty logs: **722**, dominated by Alpha Engine (`Kill switch: WARNING -- Dead features: 30/32 (94%) -- health_score=0.06`, Binance HTTP 451 fallbacks, anomaly alerts) and mirror retry notices.')
A('- `DeprecationWarning`: 75 occurrences in sampled logs, chiefly Node `punycode` (`[DEP0040]`) in retry loops and Python `datetime.utcnow()` in `genome/generate_picks.py:447`.')
A('- These counts are for sampled failure logs only; a repo-wide warning census would require downloading all 1,207 failed-run logs. See UNVERIFIED.')
A('')
A('## 7. Evidence commands')
A('')
A('```bash')
A('gh api repos/eltonaguiar/findtorontoevents_antigravity.ca/actions/workflows --paginate \\')
A('  --jq \'.workflows[] | {id,name,path,state}\'          # 365 rows -> raw/A_workflows.json')
A('gh run list --repo eltonaguiar/findtorontoevents_antigravity.ca --limit 500 \\')
A('  --json databaseId,name,workflowName,event,status,conclusion,createdAt,updatedAt,headBranch,number,url')
A('gh api repos/.../actions/workflows/<id>/runs?per_page=10')
A('gh api repos/.../actions/workflows/<id>/runs?per_page=100&created=%3E%3D2026-11-13T16:05:00Z   # 24h')
A('gh api repos/.../actions/workflows/<id>/runs?per_page=100&created=%3E%3D2026-11-07T16:05:00Z   # 7d')
A('# paginated to completion for 96 workflows with >100 runs/7d (raw/wf7d_full/*.jsonl)')
A('gh api repos/.../actions/runs/<id>/jobs?per_page=100')
A('gh run view <id> --repo ... --log-failed        # 19 sampled logs in raw/logs/')
A('gh api repos/.../actions/jobs/<job_id>/logs     # fallback when --log-failed refused an in-progress run')
A('```')
A('')
A(f'Exact reconstructed totals (summed across all 365 workflows): 24h = **{tot24:,}** runs; 7d = **{tot7:,}** runs. Repo-level `actions/runs?created=>=...` returns `total_count=2500` for both windows (API cap), so repo-level `total_count` was **not** used for any window aggregate.')
A('')
A('## 8. UNVERIFIED')
A('')
A('- Root errors for runs that were mid-retry when logs were requested: Sports endpoint smoke + Playwright (43609430834), CI Tests (43605861085), Market Beating (43603128044), robust-edge-miner (43596188828), ALPHA ENGINE - Live Autonomous Scanner (43603342689).')
A('- 7d count of zero-job cancelled runs (only the 82 runs in 24h were job-checked; 15 had zero jobs).')
A('- Repo-wide warning/deprecation census (only 19 failed logs sampled).')
A('- Whether the `update-environment: false` failure is specific to a self-hosted runner label (`vars.ACTIONS_RUNNER_LABEL`) or applies to cloud `ubuntu-latest`; logs show Python 3.14 and `/usr/include/python3.14`, but the runner label per job was not captured.')
A('')
A('## Appendix — per-workflow last-run matrix (365 rows)')
A('')
A('Also written as CSV: `sub/A_workflow_matrix.csv`. Legend: r24/r7 = total runs; s/f/c = success/failure/cancelled.')
A('')
A('| Workflow | Last run UTC | Age | Last state | Last event | r24 | s24 | f24 | c24 | r7 | s7 | f7 | c7 |')
A('|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|')
for r in sorted(rows,key=lambda x:(-sum(x['c7'].values()),x['name'])):
    last=r['last']; st=(last['conclusion'] or last['status']) if last else 'never'
    A(f'| {r["name"]} | {last["created_at"] if last else "—"} | {(str(round(r["age_h"]/24,1))+"d") if last else "—"} | {st} | {last["event"] if last else "—"} | {sum(r["c24"].values())} | {g(r["c24"],"success")} | {g(r["c24"],"failure")} | {g(r["c24"],"cancelled")} | {sum(r["c7"].values())} | {g(r["c7"],"success")} | {g(r["c7"],"failure")} | {g(r["c7"],"cancelled")} |')
A('')
open('sub/A_actions_health.md','w').write('\n'.join(L)+'\n')
print('wrote',len(L),'lines, md bytes',os.path.getsize('sub/A_actions_health.md'),'csv bytes',os.path.getsize('sub/A_workflow_matrix.csv'))
