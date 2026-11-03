import requests, re, json, time, html, os
STORE="/tmp/jobrounds/accumulated.json"
H={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36","Accept-Language":"en-CA"}
BASE="https://ca.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
def load_known():
    rd=open('/home/eaguiar2015/findtorontoevents_antigravity.ca/bestiejob/README.md',encoding='utf-8').read()
    known=set(u.split('?')[0].rstrip('/') for u in re.findall(r'\]\((https?://[^)]+)\)',rd))
    kj=json.load(open('/home/eaguiar2015/findtorontoevents_antigravity.ca/bestiejob/jobs.json'))
    known|={j['url'].split('?')[0].rstrip('/') for j in kj['jobs'] if j.get('url')}
    ids=set(re.findall(r'linkedin\.com/jobs/view/(?:[^\s"\')]*?-)?(\d{8,})'," ".join(known)))
    return known, ids
def load_store():
    if os.path.exists(STORE): return json.load(open(STORE))
    return {"jobs":[], "seen_ids":[]}
def save_store(s): json.dump(s,open(STORE,"w"),indent=1)
def li_search(kw, loc, extra=None, pages=1):
    out=[]
    for start in range(0, 25*pages, 25):
        p={"keywords":kw,"location":loc,"start":start}; p.update(extra or {})
        for attempt in range(2):
            try:
                r=requests.get(BASE,params=p,headers=H,timeout=25)
                if r.status_code==429: time.sleep(9); continue
                if r.status_code!=200: return out
                lis=re.findall(r'<li>([\s\S]*?)</li>',r.text)
                if not lis: return out
                for li in lis:
                    mu=re.search(r'href="(https://ca\.linkedin\.com/jobs/view/[^"?]+)',li)
                    mt=re.search(r'base-search-card__title[^>]*>\s*([^<]+?)\s*<',li)
                    mc=re.search(r'base-search-card__subtitle[^>]*>\s*<a[^>]*>\s*([^<]+?)\s*<',li) or re.search(r'base-search-card__subtitle[^>]*>\s*([^<]+?)\s*<',li)
                    ml=re.search(r'job-search-card__location[^>]*>\s*([^<]+?)\s*<',li)
                    md=re.search(r'datetime="(\d{4}-\d{2}-\d{2})"',li)
                    if mu and mt:
                        out.append({"url":mu.group(1).rstrip('/'),"title":html.unescape(mt.group(1)),
                            "company":html.unescape(mc.group(1)) if mc else "?",
                            "loc":html.unescape(ml.group(1)) if ml else "?",
                            "posted":md.group(1) if md else "?","kw":kw})
                break
            except Exception as e: time.sleep(4)
        time.sleep(2.5)
    return out
def run_round(name, queries, pages=1):
    known, kids = load_known()
    store=load_store(); seen=set(store["seen_ids"]); added=0; raw=0
    for kw,loc,extra in queries:
        res=li_search(kw,loc,extra,pages); raw+=len(res)
        for j in res:
            jid=(re.search(r'-(\d{8,})$',j["url"]) or re.search(r'/(\d{8,})$',j["url"]))
            jid=jid.group(1) if jid else j["url"]
            if jid in seen or jid in kids or j["url"].split('?')[0] in known: continue
            seen.add(jid); j["round"]=name; store["jobs"].append(j); added+=1
        time.sleep(1.5)
    store["seen_ids"]=sorted(seen); save_store(store)
    print(f"[{name}] raw={raw} NEW={added} store={len(store['jobs'])}")
