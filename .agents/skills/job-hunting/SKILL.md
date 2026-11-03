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

## Stage 3 — JD Extraction (verified working 2026-11-03)

**Purpose:** Fetch full job descriptions from LinkedIn guest job-view pages (`/jobs/view/<slug>-<id>`), parse requirements, and score against resume.

**Key Discovery:** The guest job-view page returns HTTP 200 (no login required) and embeds a `<script type="application/ld+json">` block with `@type: JobPosting` containing:
- `title`, `datePosted` (full ISO timestamp), `employmentType` (CONTRACTOR/FULL_TIME)
- `hiringOrganization.name`
- `jobLocation.address` → `addressCountry`, `addressLocality`, `addressRegion`
- `experienceRequirements.monthsOfExperience` (structured years!)
- `educationRequirements.credentialCategory` (bachelor degree, etc.)
- `description` (full HTML, ~4KB per posting)

**Fallback:** If JSON-LD missing, parse `class="show-more-less-html__markup"` div.

**Extractor:** `/tmp/jobs/jd_extractor.py`

```python
import json, re, html, subprocess, sys
from datetime import datetime, timezone

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

RESUME = {
    "certs": {"CSA","CAD","CIS-PA","CIS-RC","CIS-HAM","CIS-SAM","CIS-DISCO","CIS-SPM","CIS-HR",
              "CIS-ITSM","CIS-EM","CSDM","ITIL","PD1","JS1","Platform App Builder",
              "Alteryx","Databricks","Tableau"},
    "modules_sn": {"ITSM","ITOM","GRC","IRM","HRSD","CSDM","Discovery","Flow Designer",
                   "IntegrationHub","Virtual Agent","Service Portal","HAM","SAM","SPM","CSM","FSM","TSOM"},
    "modules_sf": {"Apex","Lightning","LWC","CPQ","Pardot","MuleSoft","Marketing Cloud",
                   "Sales Cloud","Service Cloud","Experience Cloud","Data Cloud"},
    "years": 6,
    "employers": {"CIBC","BMO","Metrolinx","RBC"},
    "bilingual": False,
}

def fetch(url):
    r = subprocess.run(["curl","-sSL","-m","35","-A",UA,"-H","Accept-Language: en-CA,en;q=0.9",url],
                       capture_output=True, text=True, errors="replace")
    return r.stdout

def strip_html(s):
    s = re.sub(r"<[^>]+>"," ",s or "")
    s = html.unescape(s)
    return re.sub(r"\s+"," ",s).strip()

def extract_jd(url):
    body = fetch(url)
    # JSON-LD primary
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', body, re.S):
        try:
            data = json.loads(m.group(1))
            if isinstance(data, dict) and data.get("@type") == "JobPosting":
                loc = data.get("jobLocation",{}).get("address",{}) if isinstance(data.get("jobLocation"),dict) else {}
                exp = data.get("experienceRequirements",{}) if isinstance(data.get("experienceRequirements"),dict) else {}
                edu = data.get("educationRequirements",{}) if isinstance(data.get("educationRequirements"),dict) else {}
                desc_html = data.get("description","")
                return {
                    "url": url,
                    "title": data.get("title",""),
                    "company": data.get("hiringOrganization",{}).get("name","") if isinstance(data.get("hiringOrganization"),dict) else "",
                    "posted": (data.get("datePosted") or "")[:10],
                    "employment_type": data.get("employmentType",""),
                    "location_city": loc.get("addressLocality",""),
                    "location_region": loc.get("addressRegion",""),
                    "location_country": loc.get("addressCountry",""),
                    "years_min": exp.get("monthsOfExperience",0)//12 if exp.get("monthsOfExperience") else None,
                    "education": edu.get("credentialCategory",""),
                    "description": strip_html(desc_html),
                    "source": "json-ld",
                }
        except Exception:
            pass
    # Markup fallback
    m = re.search(r'class="show-more-less-html__markup[^"]*"[^>]*>(.*?)</div>', body, re.S)
    if m:
        return {"url":url, "description":strip_html(m.group(1)), "source":"markup"}
    return None

def parse_signals(desc):
    certs = re.findall(r"\b(CSA|CAD|CIS[- ]?(?:PA|RC|HAM|SAM|DISCO|SPM|HR|ITSM|EM|CSDM)|"
                       r"Platform Developer|JavaScript Developer|Platform App Builder|"
                       r"Platform Admin(?:istrator)?|PD1|PD2|JS1|ITIL|Alteryx|Databricks|Tableau)\b", desc, re.I)
    modules = re.findall(r"\b(ITSM|ITOM|GRC|IRM|HRSD|CSDM|Discovery|Flow Designer|"
                         r"IntegrationHub|Virtual Agent|Service Portal|HAM|SAM|SPM|CSM|FSM|TSOM|"
                         r"Apex|Lightning|LWC|CPQ|Pardot|MuleSoft|Marketing Cloud|"
                         r"Sales Cloud|Service Cloud|Experience Cloud|Data Cloud)\b", desc, re.I)
    years = re.search(r"(\d+)\s*(?:\+|or more)?\s*(?:years?|yrs?)", desc, re.I)
    onsite = bool(re.search(r"\bonsite\b|\bon-site\b|office", desc, re.I))
    hybrid = bool(re.search(r"\bhybrid\b|2 days|3 days", desc, re.I))
    remote = bool(re.search(r"\bremote\b|work from home|wfh", desc, re.I))
    bilingual = bool(re.search(r"\bbilingual\b|fran[cç]ais|French", desc, re.I))
    clearance = bool(re.search(r"\bclearance\b|\bsecret\b|top secret|reliability", desc, re.I))
    return {
        "certs_required": [c.upper() for c in certs],
        "modules": [m.upper() for m in modules],
        "years_min": int(years.group(1)) if years else None,
        "onsite": onsite, "hybrid": hybrid, "remote": remote,
        "bilingual": bilingual, "clearance": clearance,
    }

def score_job(job, resume=RESUME):
    score = 0
    reasons = []
    sig = job.get("signals",{})
    # Certs
    certs_have = set(c.upper() for c in sig.get("certs_required",[]))
    certs_resume = resume["certs"]
    overlap = certs_have & certs_resume
    missing = certs_have - certs_resume
    if overlap:
        score += 3; reasons.append(f"+3 certs {overlap}")
    if missing:
        score -= 1; reasons.append(f"-1 missing {missing}")
    # Years
    y = sig.get("years_min")
    if y is not None:
        if y <= resume["years"]:
            score += 2; reasons.append(f"+2 years<={resume['years']}")
        elif y > resume["years"] + 2:
            score -= 2; reasons.append(f"-2 years>{resume['years']+2}")
    # Modules
    mods = set(m.upper() for m in sig.get("modules",[]))
    mod_overlap = (mods & resume["modules_sn"]) | (mods & resume["modules_sf"])
    if mod_overlap:
        score += 2; reasons.append(f"+2 modules {mod_overlap}")
    # Bilingual / clearance
    if sig.get("bilingual") and not resume.get("bilingual"):
        score -= 2; reasons.append("-2 bilingual required")
    if sig.get("clearance"):
        score -= 1; reasons.append("-1 clearance")
    # Remote/hybrid bonus
    if sig.get("remote") or sig.get("hybrid"):
        score += 1; reasons.append("+1 remote/hybrid")
    # Bucket
    if score >= 4:
        bucket = "apply"
    elif score >= 1:
        bucket = "consider"
    else:
        bucket = "skip"
    return {"score": score, "reasons": reasons, "bucket": bucket}

def main():
    if len(sys.argv) < 2:
        print("Usage: python jd_extractor.py urls.json"); sys.exit(1)
    urls = json.load(open(sys.argv[1]))
    out = []
    for u in urls:
        jd = extract_jd(u)
        if not jd: continue
        sig = parse_signals(jd.get("description",""))
        jd["signals"] = sig
        sc = score_job(jd)
        jd.update(sc)
        out.append(jd)
        print(f"✓ {jd['title'][:50]}... score={sc['score']} bucket={sc['bucket']}")
    json.dump(out, open("/tmp/jd_scored.json","w"), indent=2)
    print(f"\nWrote {len(out)} scored jobs → /tmp/jd_scored.json")

if __name__ == "__main__":
    main()
```

**Run command:**
```bash
python3 /tmp/jobs/jd_extractor.py /tmp/jd_urls.json
```

**Requirement parsing regex table:**
| Signal | Regex | Notes |
|--------|-------|-------|
| Certs | `\b(CSA\|CAD\|CIS[- ]?(?:PA\|RC\|HAM\|SAM\|DISCO\|SPM\|HR\|ITSM\|EM\|CSDM)\|Platform Developer\|...)\b` | Case-insensitive, deduped |
| Modules | `\b(ITSM\|ITOM\|GRC\|IRM\|...\|Data Cloud)\b` | SN + SF modules |
| Years | `(\d+)\s*(?:\+|or more)?\s*(?:years?\|yrs?)` | First match only — spot-check |
| Hybrid | `\bhybrid\b\|2 days\|3 days` | Weak inference |
| Bilingual | `\bbilingual\b\|fran[cç]ais\|French` | Title-only French queries are noisy |
| Clearance | `\bclearance\b\|\bsecret\b\|top secret\|reliability` | Hard blocker for most candidates |

**Resume scoring model (weighted):**
- +3: certs subset of resume
- -1: certs gap
- +2: years ≤ 6
- -2: years > 8
- +2: modules overlap
- -2: bilingual required (resume not bilingual)
- -1: clearance required
- +1: remote/hybrid
- Bucket: apply (≥4), consider (≥1), skip (<1)

**Output:** `job_search_application_tracker_YYYY-MM-DDTHHMMSSZ.json` + `.md` with apply/consider/skip sections, reasons, URLs, and Key Insights block.

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