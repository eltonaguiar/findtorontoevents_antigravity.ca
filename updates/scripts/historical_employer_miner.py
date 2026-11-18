#!/usr/bin/env python3
"""Mine the live BESTIEJOB feed + local pipeline data for every unique employer.
Output: employer-registry.csv — ready to seed employer-watchlist.csv.
Usage: python3 scripts/historical_employer_miner.py
"""
import csv, json, re, sys
from collections import defaultdict
from pathlib import Path
from urllib.request import urlopen

FEED_URL = 'https://eltonaguiar.github.io/BESTIEJOB/jobs.json'
ATS_PATTERN = re.compile(r'(workday|greenhouse|lever|ashby|smartrecruiters|bamboohr)', re.I)

def extract_ats_tenant(url):
    for ats, pattern in [
        ('workday', r'//([\w-]+)\.wd\d*\.myworkdayjobs\.com'),
        ('greenhouse', r'boards-api\.greenhouse\.io/v1/boards/([\w-]+)'),
        ('greenhouse', r'job-boards\.greenhouse\.io/([\w-]+)'),
        ('lever', r'api\.lever\.co/v0/postings/([\w-]+)'),
        ('lever', r'jobs\.lever\.co/([\w-]+)'),
        ('ashby', r'api\.ashbyhq\.com/posting-api/job-board/([\w-]+)'),
        ('ashby', r'jobs\.ashbyhq\.com/([\w-]+)'),
        ('smartrecruiters', r'api\.smartrecruiters\.com/v1/companies/([\w-]+)'),
        ('smartrecruiters', r'jobs\.smartrecruiters\.com/([\w-]+)'),
    ]:
        m = re.search(pattern, url)
        if m:
            return ats, m.group(1)
    return '', ''

def main():
    print(f"Fetching: {FEED_URL}", file=sys.stderr)
    data = json.loads(urlopen(FEED_URL, timeout=30).read())
    jobs = data.get('jobs', [])

    employers = defaultdict(lambda: {
        'names': set(), 'sources': set(), 'ats_tenants': set(),
        'count': 0, 'last_seen': '', 'sn_count': 0, 'sf_count': 0
    })

    for j in jobs:
        company = (j.get('company') or '').strip()
        if not company:
            continue
        key = re.sub(r'\b(inc|corp|ltd|limited|llc|gmbh|co|canada)\b\.?', '', company, flags=re.I).strip()
        key = re.sub(r'\s+', ' ', key).lower()
        e = employers[key]
        e['names'].add(company)
        e['sources'].add(j.get('source', ''))
        e['count'] += 1
        tags = j.get('tags', [])
        if 'servicenow' in tags: e['sn_count'] += 1
        if 'salesforce' in tags: e['sf_count'] += 1
        url = j.get('url', '')
        if url:
            ats, tenant = extract_ats_tenant(url)
            if ats and tenant:
                e['ats_tenants'].add(f"{ats}:{tenant}")
        posted = j.get('postedDate', '')
        if posted > e['last_seen']:
            e['last_seen'] = posted

    rows = sorted(employers.items(), key=lambda x: -x[1]['count'])

    out = Path(__file__).resolve().parent.parent / 'employer-registry.csv'
    with out.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['canonical_name', 'sample_names', 'sources', 'ats_tenants',
                     'total_rows', 'servicenow_rows', 'salesforce_rows',
                     'last_seen', 'direct_feed_candidate'])
        for key, e in rows:
            candidate = 'yes' if e['ats_tenants'] else 'no'
            w.writerow([
                key,
                '; '.join(sorted(e['names'])[:3]),
                '; '.join(sorted(e['sources'])),
                '; '.join(sorted(e['ats_tenants'])),
                e['count'], e['sn_count'], e['sf_count'],
                e['last_seen'][:10],
                candidate
            ])

    direct = sum(1 for _, e in employers.items() if e['ats_tenants'])
    print(f"\nWritten: {out.name}", file=sys.stderr)
    print(f"Unique employers: {len(employers)}", file=sys.stderr)
    print(f"Direct ATS candidates: {direct}", file=sys.stderr)
    print(f"\nTop 20 by volume:", file=sys.stderr)
    for key, e in rows[:20]:
        ats_str = ', '.join(sorted(e['ats_tenants'])) if e['ats_tenants'] else 'none'
        print(f"  {key}: {e['count']} rows ({e['sn_count']} SN, {e['sf_count']} SF) ATS: {ats_str}", file=sys.stderr)

if __name__ == '__main__':
    main()