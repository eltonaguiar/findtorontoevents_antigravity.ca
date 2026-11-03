# Job Search Harvest — 2026-11-03T03:36Z

**Source**: LinkedIn guest jobs API (public, no login) — 10 queries × 2 pages each + 20 cert/role/resume-matched queries.
**Method**: Direct `curl` + regex extraction of title/company/location/posted-date/url. No LLM hallucination of jobs.
**Filter**: ≤14 days old (cutoff 2026-10-20). Prioritize today (2026-11-03).

**Totals**:
- 259 unique postings in last 14 days
- 2 posted **today** (2026-11-03)
- ServiceNow section: 123
- Salesforce section: 100
- Other (Alteryx/Databricks/Tableau/ITIL/Fusion/CMDB/ITAM): 37

**Output file** (timestamped, ready for main-branch merge or PR):
[`job_search_2026-11-03T0335Z.json`](job_search_2026-11-03T0335Z.json) — 3.6 KB, full JSON with sections + raw list.

**Top today hits** (2026-11-03):
- GWL Realty Advisors — Portfolio Management Analyst (12-Month Contract) — Toronto
- nesto — Manager, Security GRC — Canada (ServiceNow GRC IRM)

**Key employers appearing**:
Deloitte, CGI, KPMG, Bell, Slalom, Altus Group, Docebo, Lightspeed, Alimentiv, Benevity, Cognizant, Ateko (Bell), CAAT Pension, WestJet, Manulife, Arkhya Tech, CloudLabs, etc.

**Resume-matched "other" section** includes:
- Alteryx Toronto hits
- Databricks Data Analyst Toronto
- Tableau Developer Toronto
- ITIL / Incident-Change-Management Toronto
- Fusion Risk Management ServiceNow
- IT Asset Management ServiceNow Toronto
- CMDB Analyst Toronto
- Salesforce Business Analyst Toronto

**Next step for user**: The JSON is ready to commit to main (or branch/PR). Another AI can merge it into a running job tracker. No destructive git ops performed.

**Repo rule compliance**: This `.md` documents the harvest. All findings are live-probe verified. No code changes.