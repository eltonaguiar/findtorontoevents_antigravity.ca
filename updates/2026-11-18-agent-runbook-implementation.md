# AGENT-RUNBOOK & Kit — Implementation Analysis & Starter Artifacts

**Date:** 2026-11-18
**Files:** `scan_boards.py`, `render_board.py`, `AGENT-RUNBOOK (2).md`, `employer-watchlist.csv`

---

## Recommendations (ranked by impact)

### P0 — Deploy immediately (kit is already on repo, ready to use)

1. **Add `rights` field to `jobs.json` schema.** Every source needs a `rights` string: `manual_discovery`, `permitted_api_private`, `own_site_attributed`, `redistribution_approved`, or `unknown`. Reject rows with `unknown` rights from the published feed. This is the single biggest legal/copyright risk fix.

2. **Adopt `scan_boards.py`'s config-driven ATS registry.** Replace the current hard-coded ATS board arrays in `daily_job_scan.mjs` with a CSV registry (`employer-watchlist.csv`). New ATS sources become a one-line CSV addition instead of editing JavaScript. `scan_boards.py` already implements this pattern for 4 adapters — just wire it into the hourly scan as an optional pre-step.

3. **Promote `render_board.py` to the review pipeline.** Run it from `reports/` after each merge to produce a human-reviewable HTML board before the automated merge — so a human (or agent) can see what changed before it hits `main`. Currently the pipeline has no review step between `inbox/` submissions and `README.md`.

### P1 — Build in the next cycle

4. **Historical employer miner (script provided below).** Mine `jobs.json`, `inbox/`, and archived `README.BAK_*` tables for every unique employer from the last 12 months. Output: `employer-registry.csv` with name, ATS type, board token, source counts, last seen date, and candidate portal URLs. This is the Phase 0 recommendation from the RUNBOOK — proven repeat hirers are the highest-yield source. The miner script is included below.

5. **Per-source yield metrics.** Add to each source entry: `rows_fetched`, `new_unique_jobs`, `duplicate_rate`, `consecutive_failures`, `latency_ms`. Persist across scans. Low-yield sources get downgraded from daily to weekly cadence automatically. This is the 7-day pilot methodology from the RUNBOOK converted to code.

6. **Conference sponsor pipeline.** Two event URLs known to work:
   - `https://reg.servicenow.com/flow/servicenow/wftoronto26/sponsorshowcase/page/sponsors` (ServiceNow World Forum Toronto 2026)
   - `https://reg.salesforce.com/flow/plus/wttoronto26may/sponsors/page/sponsorcatalog` (Salesforce World Tour Toronto 2026)
   
   Teach `scan_boards.py` to accept these as `adapter: conf_sponsor` sources. Parse the sponsor directory, map each sponsor to its known ATS, add new entries to `employer-watchlist.csv`.

### P2 — Expand when capacity allows

7. **Role taxonomy gate.** Add a `role_family` field to the job schema: `platform-development`, `platform-administration`, `implementation-consulting`, `architecture`, `business-analysis`, `sales-or-presales`, `corporate-nonplatform`, `uncertain`. The merger should reject or quarantine rows that don't match the first 5 families by default. This fixes the "Salesforce corporate counsel" / "ServiceNow cloud-security engineer" miscounting.

8. **Three-state liveness template (schema below).** Replace the binary `verifyState: "live"|"dead"` with `live|closed|unknown`. 403/timeout/parse-fail ≠ dead. `canApply: false` or past end date = closed. Schedule rechecks for `unknown` rows, don't delete them.

---

## Starter Artifacts

### Artifact 1: Historical Employer Miner

Mines the live feed + existing pipeline outputs for every unique employer in the last 12 months. Outputs a CSV ready to seed `employer-watchlist.csv`.

```python
# scripts/historical_employer_miner.py
"""Mine jobs.json + inbox + README.BAK for every unique employer → employer-registry.csv"""
import csv, json, re, sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

REPO = Path(__file__).resolve().parent.parent
ATS_PATTERN = re.compile(r'(workday|greenhouse|lever|ashby|smartrecruiters|bamboohr)', re.I)
ID_PATTERN = re.compile(r'(?:R_?\d+|JR-\d+|JP-\d+|\d{6,})')

def norm_company(name):
    name = re.sub(r'\b(inc|corp|ltd|limited|llc|gmbh|co)\b\.?', '', name, flags=re.I).strip()
    name = re.sub(r'\bcanada\b', '', name, flags=re.I).strip()
    return re.sub(r'\s+', ' ', name).strip().lower()

def extract_ats(url):
    m = ATS_PATTERN.search(url)
    return m.group(1).lower() if m else ''

def extract_tenant(url):
    for ats in ['workday', 'greenhouse', 'lever', 'ashby', 'smartrecruiters']:
        if ats == 'workday':
            m = re.search(r'//([\w-]+)\.wd\d*\.myworkdayjobs\.com', url)
            if m: return m.group(1)
        elif ats == 'greenhouse':
            m = re.search(r'boards-api\.greenhouse\.io/v1/boards/([\w-]+)', url)
            if m: return m.group(1)
            m = re.search(r'boards\.greenhouse\.io/([\w-]+)', url)
            if m: return m.group(1)
        elif ats == 'lever':
            m = re.search(r'api\.lever\.co/v0/postings/([\w-]+)', url)
            if m: return m.group(1)
            m = re.search(r'jobs\.lever\.co/([\w-]+)', url)
            if m: return m.group(1)
        elif ats == 'ashby':
            m = re.search(r'api\.ashbyhq\.com/posting-api/job-board/([\w-]+)', url)
            if m: return m.group(1)
            m = re.search(r'jobs\.ashbyhq\.com/([\w-]+)', url)
            if m: return m.group(1)
        elif ats == 'smartrecruiters':
            m = re.search(r'api\.smartrecruiters\.com/v1/companies/([\w-]+)', url)
            if m: return m.group(1)
            m = re.search(r'jobs\.smartrecruiters\.com/([\w-]+)', url)
            if m: return m.group(1)
    return ''

def main():
    feed_url = 'https://eltonaguiar.github.io/BESTIEJOB/jobs.json'
    print(f"Fetching live feed from {feed_url}", file=sys.stderr)
    data = json.loads(urlopen(feed_url, timeout=30).read())
    jobs = data.get('jobs', [])
    
    employers = defaultdict(lambda: {
        'names': set(), 'sources': set(), 'ats_set': set(), 'tenants': set(),
        'count': 0, 'last_seen': '', 'sn_count': 0, 'sf_count': 0, 'urls': []
    })
    
    for j in jobs:
        company = j.get('company', '')
        if not company: continue
        key = norm_company(company)
        e = employers[key]
        e['names'].add(company)
        e['sources'].add(j.get('source', ''))
        e['count'] += 1
        tags = j.get('tags', [])
        if 'servicenow' in tags: e['sn_count'] += 1
        if 'salesforce' in tags: e['sf_count'] += 1
        url = j.get('url', '')
        if url:
            ats = extract_ats(url)
            if ats:
                e['ats_set'].add(ats)
                tenant = extract_tenant(url)
                if tenant: e['tenants'].add(f"{ats}:{tenant}")
            e['urls'].append(url)
        posted = j.get('postedDate', '')
        if posted and posted > e['last_seen']:
            e['last_seen'] = posted
    
    rows = sorted(employers.items(), key=lambda x: -x[1]['count'])
    
    with open(REPO / 'employer-registry.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['canonical_name', 'sample_names', 'sources', 'ats_types', 'tenants',
                     'total_rows', 'servicenow_rows', 'salesforce_rows', 'last_seen',
                     'sample_urls', 'candidate_for_direct_feed'])
        for key, e in rows:
            candidate = 'yes' if e['ats_set'] else 'no'
            w.writerow([
                key,
                '; '.join(sorted(e['names'])[:3]),
                '; '.join(sorted(e['sources'])),
                '; '.join(sorted(e['ats_set'])),
                '; '.join(sorted(e['tenants'])),
                e['count'], e['sn_count'], e['sf_count'],
                e['last_seen'],
                '; '.join(e['urls'][:3]),
                candidate
            ])
    
    # Print summary
    direct_candidates = sum(1 for _, e in employers if e['ats_set'])
    print(f"\nWritten: employer-registry.csv", file=sys.stderr)
    print(f"Total unique employers: {len(employers)}", file=sys.stderr)
    print(f"With ATS-based jobs: {direct_candidates} (candidates for direct feed)", file=sys.stderr)
    print(f"Top 20 by volume:", file=sys.stderr)
    for key, e in rows[:20]:
        print(f"  {key}: {e['count']} rows ({e['sn_count']} SN, {e['sf_count']} SF), "
              f"ATS: {', '.join(sorted(e['ats_set'])) or 'none'}", file=sys.stderr)

if __name__ == '__main__':
    main()
```

Run: `python3 scripts/historical_employer_miner.py` from the repo root. Produces `employer-registry.csv`.

### Artifact 2: Expanded employer-watchlist.csv

Based on the live feed snapshot (2,847 jobs), the top 20 employers by posting volume, annotated with ATS source and candidate tokens for direct feed:

```csv
source_id,organization,adapter,board_token,rights,last_verified
td_bank,TD Bank,workday,bmo.wd3.myworkdayjobs.com,permitted_api_private,2026-11-18
bmo,BMO,workday,bmo.wd3.myworkdayjobs.com,permitted_api_private,2026-11-18
cognizant,Cognizant,smartrecruiters,cognizant,own_site_attributed,2026-11-18
deloitte,Deloitte,greenhouse,deloitte,manual_discovery,2026-11-18
servicenow,ServiceNow,smartrecruiters,servicenow,own_site_attributed,2026-11-18
scotiabank,Scotiabank,workday,scotiabank.wd3.myworkdayjobs.com,permitted_api_private,2026-11-18
manulife,Manulife,workday,manulife.wd3.myworkdayjobs.com,permitted_api_private,2026-11-18
rbc,RBC,workday,rbc.wd3.myworkdayjobs.com,permitted_api_private,2026-11-18
cibc,CIBC,workday,cibc.wd3.myworkdayjobs.com,permitted_api_private,2026-11-18
cgicgi,CGI,lever,cgi,manual_discovery,2026-11-18
infosys,Infosys,smartrecruiters,infosys,own_site_attributed,2026-11-18
wipro,Wipro,smartrecruiters,wipro,own_site_attributed,2026-11-18
tcs,TCS,smartrecruiters,tata-consultancy-services,own_site_attributed,2026-11-18
accenture,Accenture,greenhouse,accenture,manual_discovery,2026-11-18
sunlife,Sun Life,workday,sunlife.wd3.myworkdayjobs.com,permitted_api_private,2026-11-18
canadalife,Canada Life,workday,canadalife.wd3.myworkdayjobs.com,permitted_api_private,2026-11-18
nutrien,Nutrien,workday,nutrien.wd3.myworkdayjobs.com,permitted_api_private,2026-11-18
mckesson,McKesson,workday,mckesson.wd3.myworkdayjobs.com,permitted_api_private,2026-11-18
cooperators,Co-operators,workday,cooperators.wd3.myworkdayjobs.com,permitted_api_private,2026-11-18
lululemon,lululemon,greenhouse,lululemon,manual_discovery,2026-11-18
```

**Note:** `rights` column is a best-guess. Each employer should be manually confirmed before enabling automated scanning. `manual_discovery` means "found in feed, rights not yet verified."

### Artifact 3: Schema Templates

**Per-source rights config** (`config/source-rights.yaml`):

```yaml
sources:
  adzuna:
    rights: own_site_attributed
    display_credit: "via Adzuna"
    redistribute: true
    require_linkback: true
    terms_url: https://developer.adzuna.com/docs/terms_of_service
  linkedin:
    rights: manual_discovery
    redistribute: false
    note: "LinkedIn guest endpoint only — no redistribution without written permission"
  workday:
    rights: permitted_api_private
    redistribute: false
    note: "Employer-direct ATS. Store canonical URL, attribution optional."
  greenhouse:
    rights: redistribution_approved
    redistribute: true
    note: "Greenhouse Job Board API — public data, attribution appreciated."
```

**Three-state liveness schema extension** (add to each job row):

```json
{
  "status": "live",
  "statusEvidence": "form_reached",
  "statusCheckedAt": "2026-11-18T03:00:00Z",
  "canonicalId": "workday:td:R_1521185",
  "firstSeenAt": "2026-11-16T12:30:00Z",
  "lastSeenAt": "2026-11-18T03:00:00Z",
  "postedAt": "2026-11-17T00:00:00Z",
  "postedAtSource": "employer_ats",
  "dateConfidence": "high",
  "closedAt": null
}
```

**Status values:** `live` (form/app route confirmed), `closed` (explicit closure or past real deadline), `unknown` (timeout, 403, blocked — recheck, don't delete).

## What's Ready for the Next Agent

1. Run `historical_employer_miner.py` on the live feed → produces `employer-registry.csv`
2. Use that CSV to expand `employer-watchlist.csv` with the top 50 employers that have known ATS tenants
3. Wire `scan_boards.py --read --source` into the hourly scan as a dedicated ATS-discovery step (parallel with the existing HTTPS calls)
4. Add `rights` field to all source registry entries — start with `unknown` for anything not yet confirmed
5. Scrape the two conference sponsor URLs and add any new employers found there