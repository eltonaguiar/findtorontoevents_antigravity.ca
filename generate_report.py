#!/usr/bin/env python3
"""Generate interactive HTML performance report from live system data."""
import json, os
from collections import defaultdict
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(ROOT, 'audit_trail/data/universal_resolved_picks.json')) as f:
    all_picks_data = json.load(f)

with open(os.path.join(ROOT, 'audit_trail/data/dashboard_payload.json')) as f:
    payload = json.load(f)

recent = [p for p in all_picks_data if any(p.get('resolved_at','').startswith(d) for d in
    ['2026-05-16','2026-05-17','2026-05-18','2026-05-19','2026-05-20','2026-05-21'])]

# Compute all picks detail for filtering
allPicks = []
for p in sorted(recent, key=lambda x:-(x.get('pnl_pct',0) or 0)):
    allPicks.append({
        'day': p['resolved_at'][:10],
        'symbol': p['symbol'],
        'ac': (p.get('asset_class') or 'UNKNOWN').upper(),
        'dir': p['direction'],
        'entry': p.get('entry_price',0),
        'exit': p.get('exit_price',0),
        'pnl': p.get('pnl_pct',0) or 0,
        'reason': p.get('exit_reason',''),
        'src': p.get('source_system',''),
        'strat': p.get('strategy','')
    })

# Pre-aggregate for each view
day_ac = defaultdict(lambda: defaultdict(lambda: {'n':0,'wins':0,'losses':0,'be':0,'pnl':0.0,'tp':0,'sl':0,'te':0}))
src_day = defaultdict(lambda: defaultdict(lambda: {'n':0,'wins':0,'losses':0,'pnl':0.0}))
sym_day = defaultdict(lambda: defaultdict(lambda: {'n':0,'wins':0,'losses':0,'pnl':0.0}))
dir_day = defaultdict(lambda: {'n':0,'wins':0,'losses':0})

for p in recent:
    day = p['resolved_at'][:10]
    ac = (p.get('asset_class') or 'UNKNOWN').upper()
    s = p.get('source_system','?')
    sym = p['symbol']
    d = p['direction']
    pnl = p.get('pnl_pct',0) or 0

    dd = day_ac[day][ac]
    dd['n']+=1
    if pnl>0: dd['wins']+=1
    elif pnl<0: dd['losses']+=1
    else: dd['be']+=1
    dd['pnl']+=pnl
    dd['tp']+=1 if p.get('exit_reason')=='TP_HIT' else 0
    dd['sl']+=1 if p.get('exit_reason')=='SL_HIT' else 0
    dd['te']+=1 if p.get('exit_reason')=='TIME_EXIT' else 0

    sd = src_day[day][s]
    sd['n']+=1
    if pnl>0: sd['wins']+=1
    elif pnl<0: sd['losses']+=1
    sd['pnl']+=pnl

    sd2 = sym_day[day][sym]
    sd2['n']+=1
    if pnl>0: sd2['wins']+=1
    elif pnl<0: sd2['losses']+=1
    sd2['pnl']+=pnl

    dd2 = dir_day[day+'|'+d]
    dd2['n']+=1
    dd2['dir']=d
    dd2['day']=day
    if pnl>0: dd2['wins']+=1
    elif pnl<0: dd2['losses']+=1

# Source summary across all days
src_all = defaultdict(lambda: {'n':0,'wins':0,'losses':0,'pnl':0.0,'days':set()})
for p in recent:
    s = p.get('source_system','?')
    d = src_all[s]
    d['n']+=1
    pnl = p.get('pnl_pct',0) or 0
    if pnl>0: d['wins']+=1
    elif pnl<0: d['losses']+=1
    d['pnl']+=pnl
    d['days'].add(p['resolved_at'][:10])

# Sym summary across all days
sym_all = defaultdict(lambda: {'n':0,'wins':0,'losses':0,'be':0,'pnl':0.0,'tp':0,'sl':0,'te':0,
    'long_w':0,'long_l':0,'short_w':0,'short_l':0,'sources':defaultdict(int),'ac':'?'})
for p in recent:
    s = p['symbol']
    d = sym_all[s]
    d['n']+=1
    d['ac'] = (p.get('asset_class') or 'UNKNOWN').upper()
    pnl = p.get('pnl_pct',0) or 0
    if pnl>0: d['wins']+=1
    elif pnl<0: d['losses']+=1
    else: d['be']+=1
    d['pnl']+=pnl
    d['tp']+=1 if p.get('exit_reason')=='TP_HIT' else 0
    d['sl']+=1 if p.get('exit_reason')=='SL_HIT' else 0
    d['te']+=1 if p.get('exit_reason')=='TIME_EXIT' else 0
    if p['direction']=='LONG':
        if pnl>0: d['long_w']+=1
        elif pnl<0: d['long_l']+=1
    else:
        if pnl>0: d['short_w']+=1
        elif pnl<0: d['short_l']+=1
    d['sources'][p.get('source_system','?')]+=1

# AC health
ac_health_list = []
for ac_name, ac_data in (payload.get('asset_class_summary') or {}).items():
    pf = ac_data.get('pf',0)
    wr = ac_data.get('forwardWR',0)*100
    n = ac_data.get('activeCount',0)
    thresholds = ac_data.get('thresholds',{})
    if pf>=2.0 and wr>=55: status='T1 Renaissance'
    elif pf>=1.5 and wr>=50: status='T2 Institutional'
    elif pf>=1.2 and wr>=48: status='T3 Retail-OK'
    elif pf<1.0: status='Sub-floor'
    else: status='Below T3'
    ac_health_list.append({'ac':ac_name,'status':status,'active':n,'smart':ac_data.get('smartCount',0),
        'avgScore':round(ac_data.get('avgScore',0),1),'fwdWR':round(wr,1),'pass':ac_data.get('thresholdPass',False),
        'minScore':thresholds.get('minScore',0),'minWR':round(thresholds.get('minForwardWR',0)*100,1),'pf':round(pf,2)})

# JSON embeds
day_ac_json = json.dumps({d:{ac:day_ac[d][ac] for ac in day_ac[d]} for d in day_ac})
src_all_json = json.dumps(sorted([{'src':s,'n':d['n'],'wins':d['wins'],'losses':d['losses'],
    'wr':round(d['wins']/(d['wins']+d['losses'])*100,1) if d['wins']+d['losses'] else 0,
    'pnl':round(d['pnl'],2),'avgPnl':round(d['pnl']/d['n'],2) if d['n'] else 0,
    'days':len(d['days'])} for s,d in src_all.items()],key=lambda x:-x['n']))
sym_json = json.dumps(sorted([{'symbol':s,'ac':d['ac'],'count':d['n'],'wins':d['wins'],'losses':d['losses'],'be':d['be'],
    'wr':round(d['wins']/d['n']*100,1) if d['n'] else 0,'totalPnl':round(d['pnl'],2),'avgPnl':round(d['pnl']/d['n'],2) if d['n'] else 0,
    'tp':d['tp'],'sl':d['sl'],'te':d['te'],
    'longW':d['long_w'],'longL':d['long_l'],'shortW':d['short_w'],'shortL':d['short_l'],
    'topSrc':max(d['sources'].items(),key=lambda x:x[1])[0] if d['sources'] else '?',
    'topStrat':max(d['strats'].items(),key=lambda x:x[1])[0] if d['strats'] else '?'}
    for s,d in sym_all.items()],key=lambda x:-x['count']))
picks_json = json.dumps(allPicks)
dir_json = json.dumps([{'day':k.split('|')[0],'dir':v['dir'],'n':v['n'],'wins':v['wins'],'losses':v['losses'],
    'wr':round(v['wins']/v['n']*100,1) if v['n'] else 0} for k,v in dir_day.items()])
exit_json = json.dumps({'TP_HIT':sum(1 for p in recent if p.get('exit_reason')=='TP_HIT'),
    'SL_HIT':sum(1 for p in recent if p.get('exit_reason')=='SL_HIT'),
    'TIME_EXIT':sum(1 for p in recent if p.get('exit_reason')=='TIME_EXIT')})
ac_health_json = json.dumps(ac_health_list)

gen_date = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')

HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pick Performance Report — findtorontoevents.ca/audit</title>
<style>
:root{--bg:#0a0e17;--card:#111827;--bdr:#1e293b;--text:#e2e8f0;--muted:#94a3b8;--acc:#3b82f6;--grn:#22c55e;--red:#ef4444;--amb:#f59e0b;--cyn:#06b6d4;--pur:#a855f7;--rd:8px;--sh:0 4px 6px rgba(0,0,0,.3)}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'SF Mono','Fira Code','Consolas',monospace;background:var(--bg);color:var(--text);padding:20px;line-height:1.5}
h1{font-size:1.6em;color:var(--acc);margin-bottom:4px}h2{font-size:1.1em;color:var(--muted);margin:24px 0 12px;border-bottom:1px solid var(--bdr);padding-bottom:6px}
.hdr{display:flex;align-items:baseline;gap:16px;margin-bottom:16px;flex-wrap:wrap}
.hdr .dt{color:var(--muted);font-size:.85em}.hdr .bdg{background:var(--acc);color:#fff;padding:2px 10px;border-radius:12px;font-size:.75em;font-weight:700}
.tabs{display:flex;gap:4px;margin-bottom:16px;flex-wrap:wrap}
.tab{padding:6px 16px;border:1px solid var(--bdr);background:var(--card);color:var(--muted);border-radius:var(--rd) var(--rd) 0 0;cursor:pointer;font-size:.8em;font-family:inherit}
.tab:hover{border-color:var(--acc);color:var(--acc)}.tab.on{background:var(--acc);color:#fff;border-color:var(--acc)}
.tc{display:none}.tc.on{display:block}
.flt{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px;align-items:center}
.fg{display:flex;gap:4px;flex-wrap:wrap;align-items:center}
.fg label{font-size:.72em;color:var(--muted);margin-right:4px;text-transform:uppercase;letter-spacing:.5px}
.btn{padding:5px 14px;border:1px solid var(--bdr);background:var(--card);color:var(--text);border-radius:var(--rd);cursor:pointer;font-size:.8em;font-family:inherit;white-space:nowrap}
.btn:hover{border-color:var(--acc);color:var(--acc)}.btn.on{background:var(--acc);color:#fff;border-color:var(--acc)}
sel{padding:5px 10px;border:1px solid var(--bdr);background:var(--card);color:var(--text);border-radius:var(--rd);font-size:.8em;font-family:inherit}
.sr{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:20px}
.sc{background:var(--card);border:1px solid var(--bdr);border-radius:var(--rd);padding:14px;box-shadow:var(--sh)}
.sc .lb{font-size:.7em;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
.sc .vl{font-size:1.4em;font-weight:700;margin-top:2px}
.sc .sb{font-size:.72em;color:var(--muted);margin-top:2px}
.sc.grn .vl{color:var(--grn)}.sc.red .vl{color:var(--red)}.sc.amb .vl{color:var(--amb)}.sc.cyn .vl{color:var(--cyn)}.sc.pur .vl{color:var(--pur)}
.tw{overflow-x:auto;margin-bottom:16px}table{width:100%;border-collapse:collapse;font-size:.78em}
th{background:var(--card);color:var(--muted);text-transform:uppercase;font-size:.68em;letter-spacing:.5px;padding:8px;text-align:left;position:sticky;top:0;border-bottom:2px solid var(--bdr)}
td{padding:6px 8px;border-bottom:1px solid var(--bdr);white-space:nowrap}
tr:hover td{background:rgba(59,130,246,.05)}.pos{color:var(--grn)}.neg{color:var(--red)}.neu{color:var(--amb)}
.tag{display:inline-block;padding:2px 7px;border-radius:4px;font-size:.72em;font-weight:600}
.t-c{background:rgba(6,182,212,.15);color:var(--cyn)}
.t-e{background:rgba(139,92,246,.15);color:var(--pur)}
.t-f{background:rgba(236,72,153,.15);color:var(--pink)}
.t-t{background:rgba(34,197,94,.15);color:var(--grn)}
.t-cm{background:rgba(245,158,11,.15);color:var(--amb)}
.t-fu{background:rgba(239,68,68,.15);color:var(--red)}
@media(max-width:768px){.sr{grid-template-columns:repeat(2,1fr)}.flt{flex-direction:column;align-items:flex-start}}
</style>
</head>
<body>
<div class="hdr">
  <h1>&#x1F4CA; Pick Performance Report</h1>
  <span class="dt">Generated: GENDATE UTC</span>
  <span class="bdg">findtorontoevents.ca/audit</span>
</div>
<div class="tabs">
  <div class="tab on" onclick="sw('overview')">Overview</div>
  <div class="tab" onclick="sw('daybreakdown')">Day-by-Day</div>
  <div class="tab" onclick="sw('sources')">Source Systems</div>
  <div class="tab" onclick="sw('symbols')">Top Symbols</div>
  <div class="tab" onclick="sw('direction')">Direction</div>
  <div class="tab" onclick="sw('exits')">Exit Reasons</div>
  <div class="tab" onclick="sw('health')">Asset Health</div>
  <div class="tab" onclick="sw('detail')">All Picks Detail</div>
</div>
<div class="flt" id="fbar">
  <div class="fg">
    <label>Period</label>
    <button class="btn on" data-p="5d" onclick="sp('5d',this)">5D</button>
    <button class="btn" data-p="3d" onclick="sp('3d',this)">3D</button>
    <button class="btn" data-p="today" onclick="sp('today',this)">Today</button>
    <button class="btn" data-p="7d" onclick="sp('7d',this)">7D</button>
    <button class="btn" data-p="14d" onclick="sp('14d',this)">14D</button>
    <button class="btn" data-p="all" onclick="sp('all',this)">All</button>
  </div>
  <div class="fg">
    <label>Asset</label>
    <button class="btn on" data-a="ALL" onclick="sf('asset','ALL',this)">All</button>
    <button class="btn" data-a="CRYPTO" onclick="sf('asset','CRYPTO',this)">&#x1F48E; CRYPTO</button>
    <button class="btn" data-a="EQUITY" onclick="sf('asset','EQUITY',this)">&#x1F4C8; EQUITY</button>
    <button class="btn" data-a="FOREX" onclick="sf('asset','FOREX',this)">&#x1F4B1; FOREX</button>
    <button class="btn" data-a="ETF" onclick="sf('asset','ETF',this)">&#x1F4CA; ETF</button>
    <button class="btn" data-a="MEME" onclick="sf('asset','MEME',this)">&#x1F0CF; MEME</button>
  </div>
  <div class="fg">
    <label>Direction</label>
    <button class="btn on" data-d="ALL" onclick="sf('dir','ALL',this)">All</button>
    <button class="btn" data-d="LONG" onclick="sf('dir','LONG',this)">&#x1F4C8; LONG</button>
    <button class="btn" data-d="SHORT" onclick="sf('dir','SHORT',this)">&#x1F4C9; SHORT</button>
  </div>
  <div class="fg">
    <label>Source</label>
    <select class="sel" id="srcSel" onchange="sf('source',this.value,this)"><option value="ALL">All Sources</option></select>
  </div>
  <div class="fg">
    <label>Sort</label>
    <select class="sel" id="sortSel" onchange="run()">
      <option value="pnl-d">PnL Best</option>
      <option value="pnl-a">PnL Worst</option>
      <option value="wr">Win Rate</option>
      <option value="cnt">Frequency</option>
      <option value="sym">Symbol A-Z</option>
    </select>
  </div>
</div>
<div id="overview" class="tc on"></div>
<div id="daybreakdown" class="tc"></div>
<div id="sources" class="tc"></div>
<div id="symbols" class="tc"></div>
<div id="direction" class="tc"></div>
<div id="exits" class="tc"></div>
<div id="health" class="tc"></div>
<div id="detail" class="tc"></div>
<script>
const dayAC = ''' + day_ac_json + ''';
const srcAll = ''' + src_all_json + ''';
const symData = ''' + sym_json + ''';
const dirData = ''' + dir_json + ''';
const exitData = ''' + exit_json + ''';
const acHealth = ''' + ac_health_json + ''';
const allPicks = ''' + picks_json + ''';

const fmt = (n,d=2) => n==null?'—':n.toFixed(d);
const pnlC = v => v>0?'pos':v<0?'neg':'';
const tc = ac => ({'CRYPTO':'t-c','EQUITY':'t-e','FOREX':'t-f','ETF':'t-t','COMMODITY':'t-cm','FUTURES':'t-fu','MEME':'t-cm'}||{})[ac]||'t-c';

let fs = {period:'5d',asset:'ALL',dir:'ALL',source:'ALL',sort:'pnl-d'};

function sw(id) {
  document.querySelectorAll('.tab').forEach((t,i)=>t.classList.toggle('on',
    ['overview','daybreakdown','sources','symbols','direction','exits','health','detail'][i]===id));
  document.querySelectorAll('.tc').forEach(c=>c.classList.remove('on'));
  document.getElementById(id).classList.add('on');
}
function sp(p,el) {
  fs.period=p;
  document.querySelectorAll('[data-p]').forEach(b=>b.classList.toggle('on',b.dataset.p===p));
  run();
}
function sf(type,val,el) {
  fs[type]=val;
  const a=type==='asset'?'a':type==='dir'?'d':'x';
  if(type==='asset'||type==='dir') document.querySelectorAll('[data-'+a+']').forEach(b=>b.classList.toggle('on',b.dataset[a]===val));
  run();
}

const periodDays = {
  '5d':['2026-05-16','2026-05-17','2026-05-18','2026-05-19','2026-05-20','2026-05-21'],
  '3d':['2026-05-19','2026-05-20','2026-05-21'],
  'today':['2026-05-21'],
  '7d':null, '14d':null, 'all':null
};

function inPeriod(day) {
  const p = fs.period;
  if(p==='all') return true;
  if(periodDays[p]) return periodDays[p].includes(day);
  if(p==='7d') return new Date(day)>=new Date('2026-05-14');
  if(p==='14d') return new Date(day)>=new Date('2026-05-07');
  return true;
}

function filterPicks(arr) {
  let f = arr.filter(p=>inPeriod(p.day));
  if(fs.asset!=='ALL') f=f.filter(p=>p.ac===fs.asset);
  if(fs.dir!=='ALL') f=f.filter(p=>p.dir===fs.dir);
  if(fs.source!=='ALL') f=f.filter(p=>p.src===fs.source);
  switch(fs.sort){
    case 'pnl-d': f.sort((a,b)=>b.pnl-a.pnl); break;
    case 'pnl-a': f.sort((a,b)=>a.pnl-b.pnl); break;
    case 'wr': f.sort((a,b)=>a.pnl>0?-1:1); break;
    case 'cnt': f.sort((a,b)=>b.pnl-a.pnl); break;
    case 'sym': f.sort((a,b)=>a.symbol.localeCompare(b.symbol)); break;
  }
  return f;
}

/* ── RENDER FUNCTIONS ── */
function ro() {
  const f = filterPicks(allPicks);
  const n = f.length;
  const w = f.filter(p=>p.pnl>0).length;
  const l = f.filter(p=>p.pnl<0).length;
  const be = f.filter(p=>p.pnl===0).length;
  const pnl = f.reduce((s,p)=>s+p.pnl,0);
  const avg = n>0?pnl/n:0;
  const wr = w+l>0? w/(w+l)*100:0;
  const tp = f.filter(p=>p.reason==='TP_HIT').length;
  const sl = f.filter(p=>p.reason==='SL_HIT').length;
  const te = f.filter(p=>p.reason==='TIME_EXIT').length;
  const gp = f.filter(p=>p.pnl>0).reduce((s,p)=>s+p.pnl,0);
  const gl = Math.abs(f.filter(p=>p.pnl<0).reduce((s,p)=>s+p.pnl,0));
  const pf = gl>0? Math.abs(gp/gl):(gp>0?999:0);
  const el=document.getElementById('overview');
  el.innerHTML=`<h2>&#x1F4CA; Performance Summary — ${fs.period.toUpperCase()}</h2>
  <div class="tw"><table>
  <tr><td style="color:var(--muted);padding:6px 10px">Total Resolved Trades</td><td style="padding:6px 10px;font-weight:700">${n}</td></tr>
  <tr><td style="color:var(--muted);padding:6px 10px">Winners</td><td style="padding:6px 10px;font-weight:700" class="pos">${w} (${fmt(wr)}% WR)</td></tr>
  <tr><td style="color:var(--muted);padding:6px 10px">Losers</td><td style="padding:6px 10px;font-weight:700" class="neg">${l}</td></tr>
  <tr><td style="color:var(--muted);padding:6px 10px">Breakeven</td><td style="padding:6px 10px;font-weight:700">${be}</td></tr>
  <tr><td style="color:var(--muted);padding:6px 10px">Total PnL</td><td style="padding:6px 10px;font-weight:700" class="${pnlC(pnl)}">${pnl>=0?'+':''}${fmt(pnl)}%</td></tr>
  <tr><td style="color:var(--muted);padding:6px 10px">Avg PnL/Trade</td><td style="padding:6px 10px;font-weight:700" class="${pnlC(avg)}">${avg>=0?'+':''}${fmt(avg)}%</td></tr>
  <tr><td style="color:var(--muted);padding:6px 10px">TP / SL / Time Exit</td><td style="padding:6px 10px;font-weight:700">${tp} / ${sl} / ${te}</td></tr>
  <tr><td style="color:var(--muted);padding:6px 10px">Profit Factor</td><td style="padding:6px 10px;font-weight:700" class="${pf>=1.5?'pos':pf<1?'neg':''}">${fmt(pf,2)}</td></tr>
  <tr><td style="color:var(--muted);padding:6px 10px">Trades/Day</td><td style="padding:6px 10px;font-weight:700">${n>0?fmt(n/5,1):0}</td></tr>
  </table></div>`;
}

function rdb() {
  const f = filterPicks(allPicks);
  const el=document.getElementById('daybreakdown');
  let h='<h2>&#x1F4C5; Day-by-Day × Asset Class</h2><div class="tw"><table><tr><th>Date</th><th>Asset</th><th>Trades</th><th>W</th><th>L</th><th>BE</th><th>WR</th><th>Total PnL</th><th>Avg PnL</th><th>TP</th><th>SL</th><th>TE</th></tr>';
  const days=[...new Set(f.map(p=>p.day))].sort();
  days.forEach(day=>{
    const acs={};
    f.filter(p=>p.day===day).forEach(p=>{
      if(!acs[p.ac]) acs[p.ac]={n:0,wins:0,losses:0,be:0,pnl:0,tp:0,sl:0,te:0};
      const d=acs[p.ac];
      d.n++;
      if(p.pnl>0)d.wins++; else if(p.pnl<0)d.losses++; else d.be++;
      d.pnl+=p.pnl;
      d.tp+=p.reason==='TP_HIT'?1:0;
      d.sl+=p.reason==='SL_HIT'?1:0;
      d.te+=p.reason==='TIME_EXIT'?1:0;
    });
    const dayN=f.filter(p=>p.day===day).length;
    const dayPnl=f.filter(p=>p.day===day).reduce((s,p)=>s+p.pnl,0);
    const dayPct=dayN>0?fmt(dayPnl/dayN):'—';
    let first=true;
    Object.keys(acs).sort().forEach((ac,ai)=>{
      const d=acs[ac];
      const wr=d.n>0?fmt(d.wins/d.n*100):'—';
      if(first) h+=`<tr><td rowspan="${Object.keys(acs).length}" style="font-weight:700;vertical-align:top">${day}<br><span style="font-size:.7em;color:var(--muted)">avg ${dayPct}%</span></td>`;
      first=false;
      h+=`<td><span class="tag ${tc(ac)}">${ac}</span></td><td>${d.n}</td><td class="pos">${d.wins}</td><td class="neg">${d.losses}</td><td>${d.be}</td><td>${wr}%</td>`;
      h+=`<td class="${pnlC(d.pnl)}">${d.pnl>=0?'+':''}${fmt(d.pnl)}%</td>`;
      h+=`<td class="${pnlC(d.pnl/d.n)}">${fmt(d.pnl/d.n)}%</td>`;
      h+=`<td>${d.tp}</td><td class="neg">${d.sl}</td><td class="neu">${d.te}</td></tr>`;
    });
  });
  h+='</table></div>';
  el.innerHTML=h;
}

function rs() {
  const f = filterPicks(allPicks);
  const el=document.getElementById('sources');
  const srcCalc={};
  f.forEach(p=>{
    if(!srcCalc[p.src]) srcCalc[p.src]={n:0,wins:0,losses:0,pnl:0,days:new Set()};
    srcCalc[p.src].n++;
    if(p.pnl>0)srcCalc[p.src].wins++; else if(p.pnl<0)srcCalc[p.src].losses++;
    srcCalc[p.src].pnl+=p.pnl;
    srcCalc[p.src].days.add(p.day);
  });
  const sd=Object.entries(srcCalc).map(([s,d])=>({src:s,n:d.n,wins:d.wins,losses:d.losses,
    wr:d.wins/(d.wins+d.losses)*100,pnl:d.pnl,avgPnl:d.n>0?d.pnl/d.n:0,days:d.days.size}));
  sd.sort((a,b)=>b.n-a.n);

  let c='<h2>&#x1F3ED; Source System Performance</h2><div class="sr">';
  sd.slice(0,12).forEach(s=>{
    const cc=s.avgPnl>=0?'grn':'red';
    c+=`<div class="sc ${cc}"><div class="lb" style="font-size:.62em;word-break:break-all">${s.src}</div><div class="vl">${s.avgPnl>=0?'+':''}${fmt(s.avgPnl)}%</div><div class="sb">${s.n} trades · ${fmt(s.wr)}% WR · ${s.pnl>=0?'+':''}${fmt(s.pnl)}% PnL · ${s.days}d</div></div>`;
  });
  c+='</div><div class="tw"><table><tr><th>Source</th><th>Trades</th><th>W</th><th>L</th><th>WR</th><th>Total PnL</th><th>Avg PnL</th><th>Days</th></tr>';
  sd.forEach(s=>{
    c+=`<tr><td>${s.src}</td><td>${s.n}</td><td class="pos">${s.wins}</td><td class="neg">${s.losses}</td><td>${fmt(s.wr)}%</td>`;
    c+=`<td class="${pnlC(s.pnl)}">${s.pnl>=0?'+':''}${fmt(s.pnl)}%</td>`;
    c+=`<td class="${pnlC(s.avgPnl)}">${s.avgPnl>=0?'+':''}${fmt(s.avgPnl)}</td><td>${s.days}</td></tr>`;
  });
  c+='</table></div>';
  el.innerHTML=c;
}

function rsy() {
  const f = filterPicks(allPicks);
  const el=document.getElementById('symbols');
  const sc={};
  f.forEach(p=>{
    if(!sc[p.symbol]) sc[p.symbol]={n:0,wins:0,losses:0,pnl:0,tp:0,sl:0,te:0,longW:0,longL:0,shortW:0,shortL:0,ac:p.ac,src:p.src};
    const d=sc[p.symbol];
    d.n++;
    if(p.pnl>0)d.wins++; else if(p.pnl<0)d.losses++;
    d.pnl+=p.pnl;
    d.tp+=p.reason==='TP_HIT'?1:0;
    d.sl+=p.reason==='SL_HIT'?1:0;
    d.te+=p.reason==='TIME_EXIT'?1:0;
    if(p.dir==='LONG'){if(p.pnl>0)d.longW++;else if(p.pnl<0)d.longL++;}
    else{if(p.pnl>0)d.shortW++;else if(p.pnl<0)d.shortL++;}
  });
  const sy=Object.entries(sc).map(([s,d])=>({symbol:s,...d,wr:d.wins/d.n*100,avgPnl:d.n>0?d.pnl/d.n:0,
    topSrc:d.src,topStrat:''}));
  sy.sort((a,b)=>b.n-a.n);

  let h='<h2>&#x1F3AF; Top Symbols by Frequency</h2><div class="tw"><table><tr>';
  h+='<th>#</th><th>Symbol</th><th>Class</th><th>Trades</th><th>W</th><th>L</th><th>WR</th><th>Total PnL</th><th>Avg PnL</th><th>TP</th><th>SL</th><th>TE</th><th>Long WR</th><th>Short WR</th><th>Top Source</th></tr>';
  sy.slice(0,25).forEach((s,i)=>{
    const lwr=(s.longW+s.longL)>0?fmt(s.longW/(s.longW+s.longL)*100):'—';
    const swr=(s.shortW+s.shortL)>0?fmt(s.shortW/(s.shortW+s.shortL)*100):'—';
    h+=`<tr><td>${i+1}</td><td><strong>${s.symbol}</strong></td><td><span class="tag ${tc(s.ac)}">${s.ac}</span></td>`;
    h+=`<td>${s.n}</td><td class="pos">${s.wins}</td><td class="neg">${s.losses}</td>`;
    h+=`<td class="${pnlC(s.wr-50)}">${fmt(s.wr)}%</td>`;
    h+=`<td class="${pnlC(s.totalPnl)}">${s.totalPnl>=0?'+':''}${fmt(s.totalPnl)}%</td>`;
    h+=`<td class="${pnlC(s.avgPnl)}">${s.avgPnl>=0?'+':''}${fmt(s.avgPnl)}</td>`;
    h+=`<td>${s.tp}</td><td class="neg">${s.sl}</td><td class="neu">${s.te}</td>`;
    h+=`<td>${lwr}%</td><td>${swr}%</td><td>${s.topSrc}</td></tr>`;
  });
  h+='</table></div>';
  el.innerHTML=h;
}

function rd() {
  const f = filterPicks(allPicks);
  const el=document.getElementById('direction');
  const calc=(dir)=>{const x=f.filter(p=>p.dir===dir);const w=x.filter(p=>p.pnl>0).length;const l=x.filter(p=>p.pnl<0).length;return{n:x.length,wins:w,losses:l,wr:(w+l)>0?w/(w+l)*100:0};};
  const lo=calc('LONG'), sh=calc('SHORT');
  const delta=(lo.n>0&&sh.n>0)?fmt(lo.wr-sh.wr,1):'—';
  let c='<h2>&#x2195; Direction Analysis</h2><div class="sr">';
  c+=`<div class="sc grn"><div class="lb">LONG Win Rate</div><div class="vl">${fmt(lo.wr)}%</div><div class="sb">${lo.wins}/${lo.n} trades</div></div>`;
  c+=`<div class="sc red"><div class="lb">SHORT Win Rate</div><div class="vl">${fmt(sh.wr)}%</div><div class="sb">${sh.wins}/${sh.n} trades</div></div>`;
  c+=`<div class="sc amb"><div class="lb">L/S Split</div><div class="vl">${lo.n}/${sh.n}</div><div class="sb">trade count</div></div>`;
  c+=`<div class="sc pur"><div class="lb">Edge Delta</div><div class="vl">${delta}pp</div><div class="sb">LONG vs SHORT</div></div></div>`;
  let tbl='<div class="tw"><table><tr><th>Date</th><th>Direction</th><th>Trades</th><th>W</th><th>L</th><th>WR</th></tr>';
  const dy={};
  f.forEach(p=>{if(!dy[p.day])dy[p.day]={};if(!dy[p.day][p.dir])dy[p.day][p.dir]={n:0,wins:0};dy[p.day][p.dir].n++;if(p.pnl>0)dy[p.day][p.dir].wins++;});
  Object.keys(dy).sort().forEach(day=>{
    ['LONG','SHORT'].forEach(dir=>{if(dy[day][dir]){const d=dy[day][dir];const cc=dir==='LONG'?'pos':'neg';tbl+=`<tr><td>${day}</td><td class="${cc}">${dir}</td><td>${d.n}</td><td class="pos">${d.wins}</td><td class="neg">${d.n-d.wins}</td><td class="${pnlC(d.wins/d.n*100-50)}">${fmt(d.wins/d.n*100)}%</td></tr>`;}});
  });
  tbl+='</table></div>';
  el.innerHTML=c+tbl;
}

function rex() {
  const f = filterPicks(allPicks);
  const el=document.getElementById('exits');
  const total=f.length;
  const rc={TP_HIT:0,SL_HIT:0,TIME_EXIT:0};
  const rp={TP_HIT:0,SL_HIT:0,TIME_EXIT:0};
  f.forEach(p=>{rc[p.reason]++;rp[p.reason]+=p.pnl;});
  let c='<h2>&#x1F51A; Exit Reasons</h2><div class="sr">';
  [{k:'TP_HIT',l:'TP Hit',cc:'grn'},{k:'SL_HIT',l:'SL Hit',cc:'red'},{k:'TIME_EXIT',l:'Time Exit',cc:'cyn'}].forEach(r=>{
    const v=rc[r.k];const pnl=rp[r.k];const avg=v>0?pnl/v:0;
    c+=`<div class="sc ${r.cc}"><div class="lb">${r.l}</div><div class="vl">${v}</div><div class="sb">${total>0?fmt(v/total*100):0}% of exits</div></div>`;
  });
  c+='</div><h3>PnL by Exit Reason</h3><div class="tw"><table><tr><th>Reason</th><th>Count</th><th>%</th><th>Total PnL</th><th>Avg PnL</th></tr>';
  [{k:'TP_HIT',l:'TP Hit'},{k:'SL_HIT',l:'SL Hit'},{k:'TIME_EXIT',l:'Time Exit'}].forEach(r=>{
    const v=rc[r.k];const pnl=rp[r.k];const avg=v>0?pnl/v:0;
    c+=`<tr><td>${r.l}</td><td>${v}</td><td>${fmt(v/total*100)}%</td><td class="${pnlC(pnl)}">${pnl>=0?'+':''}${fmt(pnl)}%</td><td class="${pnlC(avg)}">${avg>=0?'+':''}${fmt(avg)}%</td></tr>`;
  });
  c+='</table></div>';
  el.innerHTML=c;
}

function rh() {
  const el=document.getElementById('health');
  let h='<h2>&#x1F3E5; Asset Class Health</h2><div class="tw"><table><tr>';
  h+='<th>Asset Class</th><th>Status</th><th>Active</th><th>Smart</th><th>Avg Score</th><th>Fwd WR</th><th>P/F</th><th>Min Score</th><th>Min WR</th><th>Pass</th></tr>';
  acHealth.forEach(hh=>{
    const sc=hh.status.includes('T1')||hh.status.includes('T2')?'pos':hh.status.includes('Dead')||hh.status.includes('Sub')?'neg':'';
    h+=`<tr><td><span class="tag ${tc(hh.ac)}">${hh.ac}</span></td><td class="${sc}">${hh.status}</td><td>${hh.active}</td><td>${hh.smart}</td>`;
    h+=`<td>${fmt(hh.avgScore)}</td><td>${fmt(hh.fwdWR)}%</td><td>${fmt(hh.pf,2)}</td>`;
    h+=`<td>${hh.minScore}</td><td>${fmt(hh.minWR)}%</td><td>${hh.pass?'&#x2705;':'&#x274C;'}</td></tr>`;
  });
  h+='</table></div>';
  el.innerHTML=h;
}

function rdet() {
  const f=filterPicks(allPicks);
  const el=document.getElementById('detail');
  let h=`<h2>&#x1F4DC; Resolved Picks <span id="dc">(${f.length} trades)</span></h2><div class="tw"><table><tr>`;
  h+='<th>Date</th><th>Symbol</th><th>Class</th><th>Dir</th><th>Entry</th><th>Exit</th><th>PnL %</th><th>Reason</th><th>Source</th></tr>';
  f.slice(0,500).forEach(p=>{
    h+=`<tr><td>${p.day}</td><td><strong>${p.symbol}</strong></td><td><span class="tag ${tc(p.ac)}">${p.ac}</span></td>`;
    h+=`<td>${p.dir}</td><td>${fmt(p.entry,4)}</td><td>${fmt(p.exit,4)}</td>`;
    h+=`<td class="${pnlC(p.pnl)}">${p.pnl>=0?'+':''}${fmt(p.pnl,2)}%</td>`;
    h+=`<td>${p.reason}</td><td>${p.src}</td></tr>`;
  });
  h+='</table></div>';
  el.innerHTML=h;
}

function run(){ro();rdb();rs();rsy();rd();rex();rh();rdet();}
function popSrc(){
  const sel=document.getElementById('srcSel');
  const srcs=[...new Set(allPicks.map(p=>p.src))].sort();
  srcs.forEach(s=>{const o=document.createElement('option');o.value=s;o.textContent=s;sel.appendChild(o);});
}

document.addEventListener('DOMContentLoaded',()=>{
  document.querySelector('.dt').textContent='Generated: GENDATE UTC';
  popSrc();
  run();
});
</script>
</body>
</html>'''

HTML = HTML.replace('GENDATE', gen_date)
output_path = os.path.join(ROOT, 'audit_performance_report.html')
with open(output_path, 'w') as f:
    f.write(HTML)

print(f"Report: {output_path} ({len(HTML):,} bytes)")
print(f"Picks: {len(recent)} recent, {len(allPicks)} total")
print(f"Profit factor properly computed from individual picks via JS")