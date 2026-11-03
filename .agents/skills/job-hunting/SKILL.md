# Job Hunting Skill — LinkedIn Guest API Harvester + Pattern Miner

**Purpose:** Reusable, deterministic harvesting of ServiceNow/Salesforce/Platform jobs from the public LinkedIn guest jobs API (`/jobs-guest/jobs/api/seeMoreJobPostings/search`). No login, no rate-limit key, 14-day recency filter via `f_TPR=r1209600`.

**Location:** `.agents/skills/job-hunting/SKILL.md`

---

## Core Library

**File:** `/tmp/jobs/harvest_lib.py` (copy to repo if needed)

```python
import json, subprocess, time, re, html, urllib.parse, sys

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

def fetch(url):
    r = subprocess.run(["curl","-sSL","-m","35","-A",UA,"-H","Accept-Language: en-CA,en;q=0.9",url], capture_output=True, text=True, errors="replace")
    return r.stdout

def strip(s):
    s = re.sub(r"<[^>]+>"," ",s or ""); s = html.unescape(s); return re.sub(r"\s+"," ",s).strip()

def harvest(qs, location, pages=3, sleep=1.15, tag=""):
    """
    qs: list of query strings (e.g. ["ServiceNow ITOM Toronto", "Salesforce CPQ remote Canada"])
    location: "Canada" (or city for tighter results)
    pages: number of LinkedIn result pages (10 jobs per page)
    sleep: polite delay between requests
    tag: round label for traceability
    Returns: list of dicts with keys: round, query, title, company, location, posted, url
    """
    rows = []
    loc = urllib.parse.quote(location)
    for q in qs:
        for p in range(pages):
            kw = urllib.parse.quote(q)
            url = (f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
                   f"?keywords={kw}&location={loc}&f_TPR=r1209600&start={p*10}")
            body = fetch(url)
            cards = re.findall(r'<li>(.*?)</li>', body, re.S)
            got = 0
            for c in cards:
                t = re.search(r'class="base-search-card__title"[^>]*>(.*?)</h3>', c, re.S)
                co = re.search(r'class="base-search-card__subtitle"[^>]*>\s*<a[^>]*>(.*?)</a>', c, re.S)
                lo = re.search(r'class="job-search-card__location"[^>]*>(.*?)</span>', c, re.S)
                dt = re.search(r'<time[^>]*datetime="([^"]+)"', c)
                lk = re.search(r'class="base-card__full-link[^"]*"\s+href="([^"?]+)', c)
                if not t: continue
                rows.append({"round":tag,"query":q,"title":strip(t.group(1)),
                    "company":strip(co.group(1)) if co else "",
                    "location":strip(lo.group(1)) if lo else "",
                    "posted":dt.group(1)[:10] if dt else "",
                    "url":lk.group(1) if lk else ""})
                got += 1
            print(f"  [{q[:40]:40s}] p{p} -> {got}", file=sys.stderr)
            time.sleep(sleep)
    return rows
```

**Usage (one-liner):**
```bash
python3 -c '
import sys; sys.path.insert(0,"/tmp/jobs")
from harvest_lib import harvest
rows = harvest(["ServiceNow ITOM Toronto","Salesforce CPQ remote Canada"], "Canada", pages=2, tag="R21")
import json; json.dump(rows, open("/tmp/round21.json","w"), indent=2)
'
```

---

## Pattern Mining Workflow

1. **Harvest baseline** (Rounds 0-20) — broad city + remote + partner + staffing sweeps.
2. **Aggregate + dedupe** by `url` (see `aggregate.py` in prior session).
3. **Title tokenization** — unigram/bigram counts on `title` field only (LinkedIn guest cards expose no JD body).
4. **Identify weak signals** — modules (ITOM, GRC, IRM, HRSD, CSDM, LWC, CPQ, MuleSoft, Marketing Cloud), seniority (Senior/Lead/Architect/Principal), bilingual (French), sector (banks, public, hospitals), boutiques.
5. **Pattern-driven rounds** (21-27) — targeted queries for each weak signal.
6. **Re-aggregate** — merge new rows, re-bucket, re-rank.
7. **Output** — master JSON + human MD report + keyword bank.

---

## Classification Rules (title-based only)

**Category:**
- `ServiceNow` if title contains: ServiceNow, ITSM, CMDB, ITOM, GRC, IRM, HRSD, CSDM, Discovery, Flow Designer, IntegrationHub, Virtual Agent, Service Portal
- `Salesforce` if title contains: Salesforce, Apex, Lightning, LWC, CPQ, Pardot, MuleSoft, Marketing Cloud, Sales Cloud, Service Cloud, Experience Cloud, SFDC
- `Adjacent` otherwise (resume-aligned but not platform-specific)

**Region (LinkedIn guest API never emits workplace type):**
- `GTA` if location contains any of: Toronto, Etobicoke, North York, Scarborough, York, Markham, Vaughan, Richmond Hill, Thornhill, Woodbridge, Mississauga, Brampton, Oakville, Burlington, Milton, Ajax, Pickering, Whitby, Oshawa, Clarington, Bowmanville, Newmarket, Aurora, King City, Stouffville, Uxbridge, Greater Toronto Area, GTA, Hamilton, Stoney Creek, Ancaster
- `SW-Ontario` if location contains: Waterloo, Kitchener, Cambridge, Guelph, London, Windsor, Brantford, Stratford, Woodstock, Sarnia, Chatham
- `Ontario-Other` if location contains: Ottawa, Kingston, Barrie, Sudbury, Thunder Bay, Peterborough, Sault Ste. Marie, Belleville, Niagara Falls, St. Catharines, Welland, Orillia, Timmins, North Bay
- `Other-Province` if location contains any major city outside Ontario (Montreal, Vancouver, Calgary, Edmonton, Winnipeg, Saskatoon, Halifax, etc.)
- `Province-Level` if location is exactly: Canada, Ontario Canada, Quebec Canada, British Columbia Canada, Alberta Canada, etc.
- `Unknown` otherwise

**Remote inference (weak, never asserted):**
- If query contains `remote|teletravail|wfh|anywhere` AND region is `Province-Level|Unknown|GTA` → `remote_likely = true`

**Fit score (heuristic for ranking):**
- +3 if title contains cert token (CSA, CAD, CIS-*, PD1, JS1, Platform App Builder, ITIL, Alteryx, Databricks, Tableau)
- +2 if platform named in title (ServiceNow/Salesforce + module)
- +1 if Senior/Lead/Principal/Architect/Staff/Head
- -2 if Junior/Intern/Co-op/New Grad
- +2 if region == GTA
- +1 if remote_likely

---

## Reusable Round Templates

**Round 21 (SN modules):** ITOM, GRC, IRM, HRSD, CSDM, Flow Designer, IntegrationHub, Virtual Agent — Toronto + Mississauga + Markham + remote Canada

**Round 22 (SF modules):** LWC, CPQ, Experience Cloud, MuleSoft, Marketing Cloud, Sales Cloud, Service Cloud — Toronto + Mississauga + Markham + remote Canada

**Round 23 (Bilingual):** French queries (`développeur`, `administrateur`, `conseiller`, `bilingue`) — Montreal + Québec + Toronto bilingue

**Round 24 (Senior tier):** Senior/Lead/Principal/Architect/Solution Architect — Toronto + remote Canada

**Round 25 (Banks/Telcos/Insurers):** CIBC, BMO, RBC, TD, Scotiabank, Bell, Rogers, Telus, Manulife, Sun Life

**Round 26 (Public sector):** Government of Ontario, City of Toronto, TTC, Metrolinx, OPG, Hydro One, UHN, SickKids, hospital Toronto, public sector Canada

**Round 27 (Boutiques + staffing):** Mindlance, OnX, Alimentiv, acroynon, BULL-IT, Tamanna, J&M, Astra-North, LTM, Alldus, Chapman Tate, Zaelab, Benevity, McKesson, Co-operators, Ateko, boutique consultancy Toronto, staffing agency Toronto

---

## Output Artifacts

- `job_search_pattern_rounds_<ts>.json` — master payload with `jobs[]`, `stats`, `new_from_rounds_21_27`
- `job_search_pattern_report_<ts>.md` — human-readable summary with top-N freshest + sectioned lists
- `job_search_cert_keyword_bank_<date>.md` — title-signal keyword bank (weak because guest cards expose titles only)

---

## Git Safety (MANDATORY)

- Always create a new branch for each harvest session
- Stage **only** files you authored (`git add job_search_* updates/2026-*-job-search*`)
- Never stage or commit files modified by other authors (Cursor, CI, teammates)
- Never force-push
- Document every session in `updates/`

---

## Limitations (documented for honesty)

1. LinkedIn guest API returns **no workplace-type field** — remote is inferred, never asserted.
2. Guest cards expose **title/company/location/posted/url only** — no JD body, no cert requirements, no salary, no visa sponsorship.
3. French queries are **title-only** — `développeur` in title does not guarantee bilingual workplace.
4. Dedupe is **URL-based** — same job posted on multiple LinkedIn slugs will appear as duplicates.
5. 14-day recency filter (`f_TPR=r1209600`) is hard-coded — older jobs are invisible to this harvester.

---

## When to Use This Skill

- Quarterly refresh of ServiceNow/Salesforce job landscape in Canada
- Targeted module hunting (ITOM, GRC, LWC, CPQ, MuleSoft, etc.)
- Sector sweeps (banks, public sector, hospitals, boutiques)
- Bilingual (French) market analysis
- Seniority-tier analysis (Architect/Principal/Lead)

**Do NOT use for:** full JD scraping (requires authenticated session or ATS board crawling), salary benchmarking, visa sponsorship detection, or real-time alerts (LinkedIn blocks aggressive polling).

---

**Author:** Zoo (pattern-driven extension of original LinkedIn guest API harvester)  
**Last updated:** 2026-11-03  
**License:** Same as repo (internal tooling)