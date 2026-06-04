#!/usr/bin/env python3
"""
Populate all 6 metric dimension tracking tables from active picks JSON.
Author: Claude Opus 4.7 | Date: 2026-05-29
"""
from __future__ import annotations
import json, os, sys, math, re
import pymysql
from datetime import datetime, timezone, timedelta
from collections import defaultdict, Counter

STOCKS_PW = os.environ.get('DB_PASS_STOCKS','') or os.environ.get('MYSQL_PASSWORD','')
REPO = "/home/eaguiar2015/findtorontoevents_antigravity.ca"

def get_conn():
    return pymysql.connect(
        host='mysql.50webs.com', port=3306,
        user='ejaguiar1_stocks', password=STOCKS_PW,
        database='ejaguiar1_stocks', charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def _f(v):
    """Safe float."""
    if v is None: return None
    try: return float(v)
    except: return None

def _i(v):
    """Safe int."""
    if v is None: return None
    try: return int(v)
    except: return None

def _dt(s):
    """Safe datetime parse, always UTC-aware."""
    if not s: return None
    try:
        s = str(s).replace('Z', '+00:00')
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except: return None

def _grade_num(s):
    """Parse C:60 or B into numeric."""
    if not s: return None
    s = str(s).strip().upper()
    m = re.search(r'(\d+)', s)
    if m: return int(m.group(1))
    return {'A':90,'B':70,'C':50,'D':30,'F':10}.get(s[0] if s else '', None)

def load_picks():
    """Load active picks JSON."""
    path = os.path.join(REPO, 'alpha_engine/data/active_picks.json')
    data = json.load(open(path))
    if isinstance(data, dict):
        first = list(data.values())[0]
        if isinstance(first, dict):
            data = list(data.values())
        else:
            data = [data]
    elif not isinstance(data, list):
        data = [data]
    return data

# ============================================================
# 1. metric_dimensions
# ============================================================
def populate_dimensions(cur):
    items = [
        ('score','A','Grade A',90,99), ('score','B','Grade B',70,79),
        ('score','C','Grade C',50,59), ('score','D','Grade D',30,39),
        ('score','F','Grade F',10,19),
        ('score','SURFER','Surfer badge',None,None),
        ('score','SAFE','Safe badge',None,None),
        ('composite_ref','C:50','Composite C:50',50,50),
        ('composite_ref','C:60','Composite C:60',60,60),
        ('composite_ref','C:72','Composite C:72',72,72),
        ('composite_ref','C:80','Composite C:80',80,80),
        ('composite_ref','B:70','Composite B:70',70,70),
        ('composite_ref','B:80','Composite B:80',80,80),
        ('composite_ref','A:90','Composite A:90',90,90),
        ('trust','PROVEN','Trust tier PROVEN',None,None),
        ('trust','DEVELOPING','Trust tier DEVELOPING',None,None),
        ('trust','WATCH','Trust tier WATCH',None,None),
        ('trust','SANDBOX','Trust tier SANDBOX',None,None),
        ('trust','PROBATION','Trust tier PROBATION',None,None),
        ('trust','UNK','Trust tier UNK',None,None),
        ('agv','A','AGV tier A',None,None),
        ('agv','B','AGV tier B',None,None),
        ('agv','C','AGV tier C',None,None),
        ('regime','BEAR','Bear regime',None,None),
        ('regime','BULL','Bull regime',None,None),
        ('regime','CHOP','Chop regime',None,None),
        ('regime','ACCUMULATION','Accumulation regime',None,None),
        ('regime','DISTRIBUTION','Distribution regime',None,None),
        ('edge','TRACK','Edge track tag',None,None),
        ('edge','GOLDEN','Edge golden tag',None,None),
        ('strategy_badge','FWD_VALIDATED','Forward Validated',None,None),
        ('strategy_badge','KIMI_SOLO','KIMI Solo',None,None),
        ('strategy_badge','MULTI_AGREE','Multi-Agree',None,None),
        ('strategy_badge','ELIMINATED','Eliminated',None,None),
        ('timeframe','INTRA','Intraday',None,None),
        ('timeframe','SWING','Swing',None,None),
        ('timeframe','POSITION','Position',None,None),
        ('timeframe','SCALP','Scalp',None,None),
        ('timeframe','DAY','Day',None,None),
        ('direction','LONG','Long direction',None,None),
        ('direction','SHORT','Short direction',None,None),
    ]
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    n = 0
    for g, v, d, f, c in items:
        try:
            cur.execute("INSERT IGNORE INTO metric_dimensions (dimension_group,dimension_value,description,numeric_floor,numeric_ceil,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s)", (g,v,d,f,c,now,now))
            n += cur.rowcount
        except: pass
    print(f"  metric_dimensions: {n} inserted")

# ============================================================
# 2. view_definition_catalog
# ============================================================
def populate_view_catalog(cur):
    views = [
        ('smart_picks_button','Smart Picks Button','button','Smart Picks',
         'Elite score >= per-class floor + confidence >= 0.60',
         json.dumps({"elite_score_min":"per-class floor","confidence_min":0.60}),
         'alpha_engine/data/active_picks.json','hourly',0,1),
        ('smart_picks_tab','Smart Picks Tab','tab','Smart Picks',
         'Same as button, tab rendering',
         json.dumps({"elite_score_min":"per-class floor","confidence_min":0.60}),
         'alpha_engine/data/active_picks.json','hourly',0,1),
        ('high_conviction','High Conviction','nav_surface','Smart Picks',
         'Elite>=80 + conf>=0.75 + trust>=60',
         json.dumps({"elite_score_min":80,"confidence_min":0.75,"trust_min":60}),
         'alpha_engine/data/active_picks.json','hourly',0,1),
        ('money_ready','Money Ready','nav_surface','Smart Picks',
         'Passes money_ready_verdict gates',
         json.dumps({"money_ready":True}),
         'audit_dashboard/data/money_ready_verdict.json','daily',0,1),
        ('verified_alpha','Verified Alpha','nav_surface','Smart Picks',
         'Elite>=70 from VA sources',
         json.dumps({"elite_score_min":70}),
         'audit_dashboard/data/dashboard_data.json','hourly',0,1),
        ('elite','ELITE','nav_surface','Smart Picks',
         'Top-tier picks across all filters',
         json.dumps({"elite":True}),
         'alpha_engine/data/active_picks.json','hourly',0,1),
        ('us_equity_tab','US Equity Tab','tab','US Equity',
         'EQUITY asset class',
         json.dumps({"asset_class":"EQUITY"}),
         'alpha_engine/data/active_picks.json','hourly',0,1),
        ('us_equity_ltv','US Equity: Long-Term Value','filter_preset','US Equity',
         'Long-term value EQUITY',
         json.dumps({"asset_class":"EQUITY","style":"value"}),
         'alpha_engine/data/active_picks.json','hourly',0,1),
        ('us_equity_swing','US Equity: Swing Plays','filter_preset','US Equity',
         'Swing trade EQUITY',
         json.dumps({"asset_class":"EQUITY","timeframe":"SWING"}),
         'alpha_engine/data/active_picks.json','hourly',0,1),
        ('us_equity_closed','US Equity: Closed Holds','filter_preset','US Equity',
         'Closed EQUITY picks',
         json.dumps({"asset_class":"EQUITY","status":"CLOSED"}),
         'trading_picks table','daily',1,1),
    ]
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    n = 0
    for vk,dn,vt,ps,desc,fj,ds,rs,rdb,il in views:
        try:
            cur.execute("INSERT IGNORE INTO view_definition_catalog (view_key,display_name,view_type,parent_section,description,filter_rules,data_source,refresh_schedule,requires_db,is_live,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (vk,dn,vt,ps,desc,fj,ds,rs,rdb,il,now,now))
            n += cur.rowcount
        except: pass
    print(f"  view_definition_catalog: {n} inserted")

# ============================================================
# 3. pick_dimension_snapshot
# ============================================================
def populate_snapshots(cur, picks):
    rows = []
    for p in picks:
        sym = p.get('symbol','')
        if not sym: continue
        ac = (p.get('asset_class') or p.get('category') or '').upper()
        grade = p.get('elite_grade','') or ''
        eb = p.get('elite_breakdown',{}) or {}
        if not isinstance(eb, dict): eb = {}
        reg = (p.get('regime_alignment_label') or p.get('regime_current') or '')
        htf = p.get('htf_confirmation','')
        
        row = (
            p.get('id'), p.get('id'), sym, ac,
            (p.get('direction') or '').upper(),
            p.get('strategy',''), p.get('source_system',''),
            p.get('timeframe','') or p.get('tf',''),
            _i(p.get('elite_score')), grade[0] if grade else None, _grade_num(grade),
            1 if eb.get('surfer') else 0, 1 if eb.get('safe') else 0, grade,
            1 if eb.get('declining') else 0, 1 if eb.get('rising') else 0,
            1 if eb.get('magnifier') else 0, _f(p.get('confidence')),
            _f(p.get('hf_quality_score') or p.get('trust_score')),
            p.get('trust_tier',''), '',
            _i(p.get('antigravity_score')),
            'A' if _i(p.get('antigravity_score')) and _i(p.get('antigravity_score'))>=80 else
            'B' if _i(p.get('antigravity_score')) and _i(p.get('antigravity_score'))>=60 else
            'C' if _i(p.get('antigravity_score')) else '',
            reg, 1 if 'BEAR' in reg.upper() or 'BULL' in reg.upper() else 0,
            1 if 'X' in str(p.get('regime_encoded','')) else 0,
            1 if 'DEMOD' in reg.upper() else 0,
            _f(p.get('strat_fwd_wr')), _f(p.get('strat_fwd_wr')),
            _i(p.get('strat_fwd_trades') or p.get('forward_trades')),
            'UP' if htf==1 or str(htf).upper() in ('UP','BULL') else
            'DOWN' if str(htf).upper() in ('DOWN','BEAR') else 'FLAT',
            1 if p.get('strong') else 0,
            1 if p.get('forward_validated') else 0,
            _f(p.get('viable_pct')), _f(p.get('probation_pct')),
            _f(p.get('recovery_pct')), _f(p.get('eliminated_pct')),
            1 if p.get('kimi_solo') else 0, 1 if p.get('multi_agree') else 0,
            (p.get('status') or p.get('forward_status') or 'OPEN').upper(),
            _f(p.get('pnl_pct') or p.get('unrealized_pnl_pct')),
            _f(p.get('pnl_usd')),
            _f(p.get('entry_price')), _f(p.get('current_price')),
            _f(p.get('take_profit')), _f(p.get('stop_loss')),
            _f(p.get('unrealized_pnl_pct')),
            _dt(p.get('resolved_at')), _dt(p.get('created_at') or p.get('entry_time')),
            datetime.now(timezone.utc), 'v1-2026-05-29'
        )
        rows.append(row)
    
    if rows:
        cur.execute("DELETE FROM pick_dimension_snapshot WHERE captured_at >= DATE_SUB(NOW(), INTERVAL 2 HOUR)")
        inserted = 0
        sql = """INSERT INTO pick_dimension_snapshot
            (pick_id,pick_uuid,symbol,asset_class,direction,strategy,source_system,timeframe,
             elite_score,score_grade,score_grade_numeric,score_surfer,score_safe,score_composite_ref,
             score_declining,score_rising,score_magnifier,score_confidence,
             trust_score,trust_tier,trust_color,agv_score,agv_tier,
             regime_label,regime_check,regime_x,regime_demoted,
             edge_track_pct,fwd_wr_pct,fwd_n,htf_trend,strong_signal,
             strat_fwd_validated,strat_viable_pct,strat_probation_pct,strat_recovery_pct,
             strat_eliminated_pct,strat_kimi_solo,strat_multi_agree,
             status,pnl_pct,pnl_usd,entry_price,current_price,tp_price,sl_price,
             unrealized_pnl_pct,resolved_at,submitted_at,captured_at,snapshot_version)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
        for row in rows:
            try:
                cur.execute(sql, row)
                inserted += 1
            except Exception as e:
                if 'Duplicate' not in str(e) and 'duplicate' not in str(e).lower():
                    pass  # silent skip
        print(f"  pick_dimension_snapshot: {inserted} rows inserted")
    else:
        print("  pick_dimension_snapshot: 0 rows")

# ============================================================
# 4. strategy_summary (with traceability)
# ============================================================
def populate_strategy_summary(cur, picks):
    # Group by strategy
    groups = defaultdict(list)
    for p in picks:
        s = p.get('strategy','')
        if s: groups[s].append(p)
    
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    
    for sname, spicks in groups.items():
        if not spicks: continue
        p0 = spicks[0]
        ac = (p0.get('asset_class') or p0.get('category') or 'UNKNOWN').upper()
        src = p0.get('source_system','')
        tf = p0.get('timeframe','') or p0.get('tf','')
        scores = [p.get('elite_score') for p in spicks if p.get('elite_score') is not None]
        avg_sc = sum(scores)/len(scores) if scores else None
        
        # Viability badges
        has_fwd = any(p.get('forward_validated') for p in spicks)
        vp = [p.get('viable_pct') for p in spicks if p.get('viable_pct') is not None]
        pp = [p.get('probation_pct') for p in spicks if p.get('probation_pct') is not None]
        rp = [p.get('recovery_pct') for p in spicks if p.get('recovery_pct') is not None]
        ep = [p.get('eliminated_pct') for p in spicks if p.get('eliminated_pct') is not None]
        ks = any(p.get('kimi_solo') for p in spicks)
        ma = any(p.get('multi_agree') for p in spicks)
        
        resolved = [p for p in spicks if (p.get('status') or '').upper() in ('WON','LOST','TP_HIT','SL_HIT','CLOSED')]
        active = [p for p in spicks if (p.get('status') or '').upper() in ('OPEN','ACTIVE')]
        wins = [p for p in resolved if (p.get('status') or '').upper() in ('WON','TP_HIT')]
        losses = [p for p in resolved if (p.get('status') or '').upper() in ('LOST','SL_HIT')]
        
        n_total = len(spicks)
        n_res = len(resolved)
        wr = len(wins)/n_res if n_res else None
        gross = sum(abs(p.get('pnl_pct') or 0) for p in wins)
        lsum = sum(abs(p.get('pnl_pct') or 0) for p in losses)
        pf = gross/lsum if lsum > 0 else None
        
        # Pick count by window
        now_dt = datetime.now(timezone.utc)
        picks_7d = [p for p in spicks if _dt(p.get('created_at')) and (now_dt - _dt(p.get('created_at'))).days <= 7]
        picks_30d = [p for p in spicks if _dt(p.get('created_at')) and (now_dt - _dt(p.get('created_at'))).days <= 30]
        
        # Sample pick IDs
        sample_ids = [p.get('id') for p in spicks[:5] if p.get('id')]
        
        # Strategy file path inference
        file_path = f"alpha_engine/new_strategies/{sname}.py" if sname else ""
        
        # Check if blacklisted
        blacklisted = sname in ['binance_smart_money','hl_funding_fade','quan_engine_scalp','claude_gainer_st','kimi_signal_tracking']
        
        d = {
            'strategy_name': sname, 'display_name': sname, 'asset_class': ac,
            'source_module': src, 'timeframes': json.dumps([tf]) if tf else None,
            'fwd_validated': 1 if has_fwd else 0, 'viable_pct': max(vp) if vp else None,
            'probation_pct': max(pp) if pp else None, 'recovery_pct': max(rp) if rp else None,
            'eliminated_pct': max(ep) if ep else None,
            'kimi_solo': 1 if ks else 0, 'multi_agree': 1 if ma else 0,
            'avg_elite_score': avg_sc,
            'n_total': n_total, 'n_resolved': n_res, 'n_active': len(active),
            'sizing_status': 'killed' if blacklisted else 'shadow',
            'is_enabled': 0 if blacklisted else 1,
            'is_disabled_reason': 'blacklisted -2026-05-01' if blacklisted else None,
            'pick_count_all_time': n_total, 'pick_count_7d': len(picks_7d),
            'pick_count_30d': len(picks_30d),
            'wr_all_time': wr, 'pf_all_time': pf,
            'file_path': file_path,
            'sample_pick_ids': json.dumps(sample_ids) if sample_ids else None,
            'created_at': now, 'updated_at': now, 'last_verified_at': now,
        }
        cols = ', '.join(d.keys())
        placeholders = ', '.join([f'%({k})s' for k in d.keys()])
        updates = ', '.join([f'{k}=VALUES({k})' for k in ['n_total','n_resolved','n_active','fwd_validated','viable_pct','probation_pct','recovery_pct','eliminated_pct','kimi_solo','multi_agree','avg_elite_score','wr_all_time','pf_all_time','pick_count_all_time','pick_count_7d','pick_count_30d','is_enabled','updated_at']])
        sql = f"INSERT INTO strategy_summary ({cols}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {updates}"
        cur.execute(sql, d)
    
    print(f"  strategy_summary: populated {len(groups)} strategies")

# ============================================================
# 5. pick_funnel_views
# ============================================================
def populate_funnel_views(cur, picks):
    views = {
        'smart_picks_button': lambda p: (_i(p.get('elite_score')) or 0) >= 60 and (_f(p.get('confidence')) or 0) >= 0.60,
        'high_conviction': lambda p: (_i(p.get('elite_score')) or 0) >= 80 and (_f(p.get('confidence')) or 0) >= 0.75 and (_f(p.get('hf_quality_score')) or 0) >= 60,
        'verified_alpha': lambda p: p.get('is_verified_alpha') or (_i(p.get('elite_score')) or 0) >= 70,
        'elite_all': lambda p: True,
    }
    classes = ['CRYPTO','EQUITY','FOREX','ETF','COMMODITY','FUTURES','BOND','UNKNOWN']
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    
    for vk, filt in views.items():
        for ac in classes:
            filtered = [p for p in picks if filt(p) and (p.get('asset_class') or p.get('category') or '').upper() == ac]
            if not filtered: continue
            n_t = len(filtered)
            res = [p for p in filtered if (p.get('status') or '').upper() in ('WON','LOST','TP_HIT','SL_HIT','CLOSED')]
            act = [p for p in filtered if (p.get('status') or '').upper() in ('OPEN','ACTIVE')]
            w = [p for p in res if (p.get('status') or '').upper() in ('WON','TP_HIT')]
            l = [p for p in res if (p.get('status') or '').upper() in ('LOST','SL_HIT')]
            wr = len(w)/len(res) if res else None
            g = sum(abs(p.get('pnl_pct') or 0) for p in w)
            ls = sum(abs(p.get('pnl_pct') or 0) for p in l)
            pf = g/ls if ls > 0 else None
            ap = sum(p.get('pnl_pct') or 0 for p in res)/len(res) if res else None
            
            try:
                cur.execute("""INSERT INTO pick_funnel_views
                    (view_key,display_name,view_type,view_group,asset_class,time_window,
                     filter_json,min_elite_score,min_confidence,
                     n_total,n_resolved,n_active,n_wins,n_losses,win_rate,profit_factor,avg_pnl_pct,
                     source_file,source_table,generated_at,created_at,updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE
                        n_total=VALUES(n_total),n_resolved=VALUES(n_resolved),n_active=VALUES(n_active),
                        n_wins=VALUES(n_wins),n_losses=VALUES(n_losses),win_rate=VALUES(win_rate),
                        profit_factor=VALUES(profit_factor),avg_pnl_pct=VALUES(avg_pnl_pct),
                        updated_at=VALUES(updated_at)
                """, (
                    vk, vk.replace('_',' ').title(),
                    'button' if 'button' in vk else 'nav_surface',
                    'Smart Picks', ac, 'all',
                    json.dumps({"view":vk,"asset_class":ac}),
                    60 if vk=='smart_picks_button' else 80 if vk=='high_conviction' else None,
                    0.60 if vk=='smart_picks_button' else 0.75 if vk=='high_conviction' else None,
                    n_t, len(res), len(act), len(w), len(l), wr, pf, ap,
                    'alpha_engine/data/active_picks.json','pick_dimension_snapshot',now,now,now
                ))
            except: pass
    print(f"  pick_funnel_views: populated")

# ============================================================
# 6. edge_discovery
# ============================================================
def populate_edge_discovery(cur, picks):
    combos = defaultdict(list)
    for p in picks:
        ac = (p.get('asset_class') or p.get('category') or 'UNKNOWN').upper()
        sb = 'gte60' if (_i(p.get('elite_score')) or 0) >= 60 else 'gte70' if (_i(p.get('elite_score')) or 0) >= 70 else 'gte80' if (_i(p.get('elite_score')) or 0) >= 80 else 'lt60'
        tb = 'gte5' if (_f(p.get('hf_quality_score')) or 0) >= 5 else 'lt5'
        fv = 'fwd_valid' if p.get('forward_validated') else 'not_fwd'
        combos[(ac, f"score_{sb}+trust_{tb}+{fv}")].append(p)
    
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    n_combos = 0
    for (ac, ck), cpicks in combos.items():
        res = [p for p in cpicks if (p.get('status') or '').upper() in ('WON','LOST','TP_HIT','SL_HIT','CLOSED')]
        if len(res) < 5: continue
        w = [p for p in res if (p.get('status') or '').upper() in ('WON','TP_HIT')]
        l = [p for p in res if (p.get('status') or '').upper() in ('LOST','SL_HIT')]
        nr = len(res)
        wr = len(w)/nr
        g = sum(abs(p.get('pnl_pct') or 0) for p in w)
        ls = sum(abs(p.get('pnl_pct') or 0) for p in l)
        pf = g/ls if ls > 0 else None
        ap = sum(p.get('pnl_pct') or 0 for p in res)/nr
        
        se = math.sqrt(0.25/nr) if nr > 0 else 1
        z = (wr - 0.5)/se if se > 0 else 0
        pv = 2*(1 - 0.5*(1+math.erf(abs(z)/math.sqrt(2)))) if abs(z)<6 else 0.000001
        bv = pv * len(combos)
        
        verdict = 'STRONG' if wr>=0.65 and nr>=30 else 'MODERATE' if wr>=0.58 and nr>=20 else 'WEAK' if wr>=0.52 else 'NONE'
        if wr < 0.45: verdict = 'INVERTED'
        
        detail = json.dumps({"score":ck.split('+')[0].split('_')[1],"trust":ck.split('+')[1].split('_')[1],"fwd":ck.split('+')[2]})
        
        try:
            cur.execute("""INSERT INTO edge_discovery
                (edge_key,edge_label,dimension_detail,asset_class,time_window,
                 n_total,n_resolved,n_active,min_n_threshold,
                 win_rate,profit_factor,avg_pnl_pct,
                 z_score,p_value,bonferroni_adjusted_p,survived_bonferroni,
                 edge_verdict,recommendation,
                 generated_at,updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                    n_total=VALUES(n_total),n_resolved=VALUES(n_resolved),win_rate=VALUES(win_rate),
                    profit_factor=VALUES(profit_factor),z_score=VALUES(z_score),p_value=VALUES(p_value),
                    edge_verdict=VALUES(edge_verdict),updated_at=VALUES(updated_at)
            """, (
                ck, f"{ck} in {ac}", detail, ac, 'all',
                len(cpicks), nr, len(cpicks)-nr, 30,
                wr, pf, ap, z, pv, bv, 1 if bv<0.05 else 0,
                verdict, 'SIZABLE' if verdict=='STRONG' else 'WATCH' if verdict=='MODERATE' else 'AVOID',
                now, now
            ))
            n_combos += 1
        except: pass
    print(f"  edge_discovery: {n_combos} combos")

# ============================================================
# MAIN
# ============================================================
def main():
    print("=== Building metric dimension tracking ===")
    conn = get_conn()
    cur = conn.cursor()
    
    print("\n--- Loading active picks ---")
    picks = load_picks()
    print(f"  {len(picks)} picks loaded")
    
    print("\n--- 1. metric_dimensions ---")
    populate_dimensions(cur)
    conn.commit()
    
    print("\n--- 2. view_definition_catalog ---")
    populate_view_catalog(cur)
    conn.commit()
    
    print("\n--- 3. pick_dimension_snapshot ---")
    populate_snapshots(cur, picks)
    conn.commit()
    
    print("\n--- 4. strategy_summary ---")
    populate_strategy_summary(cur, picks)
    conn.commit()
    
    print("\n--- 5. pick_funnel_views ---")
    populate_funnel_views(cur, picks)
    conn.commit()
    
    print("\n--- 6. edge_discovery ---")
    populate_edge_discovery(cur, picks)
    conn.commit()
    
    print("\n=== SUMMARY ===")
    for t in ['strategy_summary','metric_dimensions','pick_dimension_snapshot','pick_funnel_views','edge_discovery','view_definition_catalog']:
        cur.execute(f"SELECT COUNT(*) as cnt FROM {t}")
        print(f"  {t}: {cur.fetchone()['cnt']} rows")
    
    conn.close()
    print("\nDone.")

if __name__ == '__main__':
    main()
