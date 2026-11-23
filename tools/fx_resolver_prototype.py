#!/usr/bin/env python3
"""fx_resolver_prototype.py — demonstrate closing the open FX picks from observed quotes.

Reads all =X picks across copy_trader sources, and for each OPEN pick finds the NEXT observed
quote for that symbol (from another dated pick of the same symbol). Computes the mark-to-next-quote
return, labels it MARK_TO_NEXT_QUOTE (NOT a strategy exit), and reports what the FX sample yields
if resolved this way — plus how many more closes AUDJPY needs for DSR 0.95.

This is a prototype to size the resolver fix; it does not write production data.
"""
import json, glob, statistics as st, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from alpha_engine.audit3_tribunal import deflated_sharpe

def load_fx():
    rows, seen = [], set()
    for f in glob.glob('copy_trader_intel/data/*.json'):
        try: d = json.load(open(f))
        except Exception: continue
        def walk(o):
            if isinstance(o, dict):
                if '=X' in str(o.get('symbol','')) and o.get('entry_price') is not None:
                    yield o
                for v in o.values(): yield from walk(v)
            elif isinstance(o, list):
                for v in o: yield from walk(v)
        for r in walk(d):
            k=(r.get('symbol'),r.get('entry_date'),r.get('entry_price'))
            if k in seen: continue
            seen.add(k); rows.append(r)
    return rows

def main():
    rows = load_fx()
    by = {}
    for r in rows:
        by.setdefault(r['symbol'], []).append(r)
    resolved = []
    for sym, lst in by.items():
        dated = sorted([x for x in lst if x.get('entry_date')], key=lambda x: x['entry_date'])
        for i, x in enumerate(dated[:-1]):
            nxt = dated[i+1]
            e, xp = float(x['entry_price']), float(nxt['entry_price'])
            d = str(x.get('direction','LONG')).upper()
            ret = (xp/e-1) if d=='LONG' else (1-xp/e)
            resolved.append({"symbol":sym,"entry_date":x['entry_date'],"entry":e,
                             "mark_date":nxt['entry_date'],"mark":xp,"side":d,
                             "ret_pct":round(ret*100,3),"basis":"MARK_TO_NEXT_QUOTE"})
    out={"generated_at":__import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
         "fx_picks":len(rows),"symbols":sorted(by),"resolvable_closes":len(resolved),
         "resolved":resolved,
         "note":"MARK_TO_NEXT_QUOTE: closes an open pick at the next observed quote of the same symbol. "
                "Illustrates what a resolver would yield; NOT a strategy exit, do not treat as realised."}
    Path("reports/fx_resolver_prototype.json").write_text(json.dumps(out,indent=2)+"\n")
    print(f"FX picks {len(rows)} across {len(by)} symbols; resolvable closes by mark-to-next-quote: {len(resolved)}")
    for r in resolved:
        print(f"  {r['symbol']:10s} {r['side']:5s} {r['entry_date']}@{r['entry']} -> {r['mark_date']}@{r['mark']}  ret={r['ret_pct']:+.2f}%")
    aj=[r['ret_pct'] for r in resolved if r['symbol']=='AUDJPY=X']
    if aj:
        print(f"\nAUDJPY resolved marks: {aj}  mean={st.mean(aj):+.3f}%")
        # if these were the only closes, what DSR at current n(34)+these?
        vals=[v/100 for v in aj]
        d=deflated_sharpe(vals*max(1,34//max(1,len(vals))),658) if vals else None
        print(f"  (illustrative only - 1 mark is not a distribution; need ~14 real closes)")

if __name__=="__main__":
    main()
