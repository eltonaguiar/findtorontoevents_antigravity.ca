#!/usr/bin/env python3
"""Analyze multi-engine consensus per crypto pair."""
import json, urllib.request

BASE = 'https://findtorontoevents.ca/findcryptopairs/api'
pairs = {}

def fetch(url):
    try:
        r = urllib.request.urlopen(url, timeout=15)
        return json.loads(r.read())
    except:
        return None

def add_signal(pair, engine, direction, pnl, conf, reason, created):
    if pair not in pairs:
        pairs[pair] = {'engines': [], 'directions': [], 'pnls': [], 'confs': [], 'reasons': [], 'freshest': ''}
    pairs[pair]['engines'].append(engine)
    pairs[pair]['directions'].append(direction)
    pairs[pair]['pnls'].append(pnl)
    pairs[pair]['confs'].append(conf)
    pairs[pair]['reasons'].append(reason)
    if created > pairs[pair]['freshest']:
        pairs[pair]['freshest'] = created

# Proven Picks
d = fetch(BASE + '/proven_picks.php?action=picks')
if d:
    for s in d.get('active', []):
        add_signal(s.get('pair',''), 'Proven Picks', s.get('direction',''),
                   float(s.get('pnl_pct') or 0), float(s.get('confidence') or 0),
                   s.get('engines_agreeing',''), s.get('created_at',''))

# Kimi Enhanced
d = fetch(BASE + '/kimi_enhanced.php?action=signals')
if d:
    for s in d.get('active', []):
        add_signal(s.get('pair',''), 'Kimi Enhanced', s.get('direction',''),
                   float(s.get('pnl_pct') or 0), float(s.get('confidence') or 0),
                   s.get('signal_weights',''), s.get('created_at',''))

# Hybrid Engine
d = fetch(BASE + '/hybrid_engine.php?action=signals')
if d:
    for s in d.get('active', []):
        add_signal(s.get('pair',''), 'Hybrid Engine', s.get('direction',''),
                   float(s.get('pnl_pct') or 0), float(s.get('confidence') or 0),
                   s.get('model_votes',''), s.get('created_at',''))

# Expert Consensus
d = fetch(BASE + '/expert_consensus.php?action=signals')
if d:
    for s in d.get('active', []):
        add_signal(s.get('pair',''), 'Expert Consensus', s.get('direction',''),
                   float(s.get('pnl_pct') or 0), float(s.get('confidence') or 0),
                   s.get('rationale',''), s.get('created_at',''))

# Summary
print("Total unique pairs across all engines:", len(pairs))
print()

ranked = sorted(pairs.items(), key=lambda x: (-len(x[1]['engines']), -sum(x[1]['confs'])/max(1,len(x[1]['confs']))))
for p, info in ranked[:25]:
    dirs = set(info['directions'])
    agree = len(dirs) == 1
    avg_conf = sum(info['confs']) / max(1, len(info['confs']))
    avg_pnl = sum(info['pnls']) / max(1, len(info['pnls']))
    dir_str = list(dirs)[0] if agree else 'MIXED'
    eng_count = len(info['engines'])
    print("%-14s engines:%d dir:%-5s agree:%s avg_conf:%.1f%% avg_pnl:%+.2f%% freshest:%s" % (
        p, eng_count, dir_str, agree, avg_conf, avg_pnl, info['freshest']))
    for i, eng in enumerate(info['engines']):
        print("  -> %s: %s pnl:%+.2f%% conf:%.0f%%" % (eng, info['directions'][i], info['pnls'][i], info['confs'][i]))
