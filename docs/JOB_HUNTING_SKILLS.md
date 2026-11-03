# Job Hunting Skills Catalog — Reusable Tools & Actions
# Compiled 2026-11-03 for Elton Aguiar (ServiceNow CSA/CAD/CIS-*, Salesforce PD1/JS1/Platform Admin, Toronto/GTA)
# Purpose: document each reusable job-hunting skill/tool so it can be re-applied, combined, or improved.
# Each skill lists: what it does, how to invoke, when to use it, and the quality benefit.

================================================================================
HOW TO USE THIS CATALOG
================================================================================
Treat each numbered skill as a reusable action. Combine skills into a pipeline
(e.g. Discover → Filter → AI-Score → Tailor → Apply → Track). Re-run any skill
when market conditions change (new postings, new certs, new target companies).

================================================================================
SKILL 1 — Free Job Discovery (keyless job-board APIs)
================================================================================
Tool:        tools/job_discover.py
Purpose:     Pull fresh postings from free, keyless job-board APIs, normalize to
             a common schema, client-side filter by target keywords + location +
             freshness (past 14 days), and append de-duped results to a master CSV.
Sources:     arbeitnow, remoteok, remotive, freehire (plus optional Indeed RSS
             and direct company ATS boards via --companies / --indeed).
Invoke:
  python3 tools/job_discover.py --round "R1 SNOW Toronto" \
      --query "servicenow" --location "toronto" \
      --limit 60 --top 60 --no-ai --master jobs_master.csv
  python3 tools/job_discover.py --round "R5 SF Toronto" \
      --query "salesforce" --location "toronto" \
      --limit 60 --top 60 --no-ai --master jobs_master.csv
  python3 tools/job_discover.py --round "R9 SNOW CSA CAD" \
      --query "servicenow developer CSA CAD" --location "toronto" \
      --limit 40 --top 40 --no-ai --indeed --master jobs_master.csv
When:        Weekly refresh (Monday per methodology) or anytime you want new
             postings. Run one round per keyword+location combo.
Quality benefit: Never miss a fresh posting; de-dup across rounds prevents
             re-scoring the same job twice; freshness filter keeps pipeline current.
Files:       jobs_master.csv (append-mode master), data/web_search_jobs_round*.json

================================================================================
SKILL 2 — AI Second-Opinion Fan-Out (apply / skip / maybe scoring)
================================================================================
Tool:        tools/ai_second_opinion.py
Purpose:     Fan one question to 5 free verified AI providers, aggregate consensus
             + confidence, return exit code (0=lean yes, 1=lean no, 2=mixed/dead).
Providers (verified PONG 2026-11-03): Groq (gpt-oss-120b), Gemini (gemini-2.5-flash),
             OpenRouter free (nemotron-3.5-lightning:free), vLLM local (Qwen2.5-14B),
             Ollama local (deepseek-r1:32b).
Invoke:
  python3 tools/ai_second_opinion.py "should I apply to this role?" \
      --context "RESUME: ...\nJOB: ..."
  python3 tools/ai_second_opinion.py --file question.txt --context-file ctx.txt --json
When:        After discovery, before tailoring/apply. Score each candidate job.
Quality benefit: Multi-provider consensus reduces single-model bias; confidence
             score ranks which jobs deserve tailored applications; exit code is
             scriptable for auto-apply decisions.
Files:       jobs_master.csv gains ai_recommendation / ai_confidence /
             ai_yes_votes / ai_no_votes / ai_rationale columns.

================================================================================
SKILL 3 — Company ATS Board Probe (direct employer careers)
================================================================================
Tool:        tools/ats_probe.py
Purpose:     Probe company Greenhouse/Lever/Ashby ATS boards for ServiceNow/Salesforce
             roles using public board tokens (no auth needed). Discovers working
             tokens and pulls live postings directly from employers.
Invoke:
  python3 tools/ats_probe.py --companies data/ats_probe_companies.json \
      --out data/ats_probe_results.json
Companies probed (46 target ATS boards): levio, varicent, kpmg, benevity, loopio,
             plus ServiceNow/Salesforce consulting partners and GTA employers.
When:        Weekly, targeting your 20–40 company target list. Best for employers
             whose postings don't appear on job boards.
Quality benefit: Direct-from-employer postings are freshest and often not yet on
             aggregators; bypasses job-board noise.
Files:       data/ats_probe_companies.json, data/ats_probe_results.json

================================================================================
SKILL 4 — Certified-Keyword Bank (cert-aligned search terms)
================================================================================
File:        job_search_cert_keyword_bank_2026-11-03.md
Purpose:     Centralized keyword list for ServiceNow (CSA, CAD, CIS-PA/RC/HAM/SAM/
             DISCO/SPM/HR, ITOM, CMDB, CSDM, Flow Designer, Integration Hub,
             Scripted REST APIs, MID Server, ACLs, scoped apps) and Salesforce
             (Platform Developer I, JavaScript Developer I, Platform Admin,
             Apex, LWC, Omnistudio, FSC, Revenue Cloud, Marketing Cloud, Data Cloud,
             CPQ, Experience Cloud).
Invoke:      Feed keywords into job_discover.py --query and ats_probe.py searches.
             Rotate keywords per round to surface different posting subsets.
When:        Every discovery round. Rotate so no keyword subset is exhausted.
Quality benefit: Cert-aligned keywords surface roles where Elton's active
             certifications are a direct match (higher apply-confidence).
Files:       job_search_cert_keyword_bank_2026-11-03.md

================================================================================
SKILL 5 — Master Job Tracking CSV (pipeline of record)
================================================================================
File:        jobs_master.csv
Purpose:     Append-mode master ledger of every discovered job. Columns: round,
             source, fresh, posted, title, company, location, remote, url,
             ai_recommendation, ai_confidence, ai_yes_votes, ai_no_votes,
             matched_keywords, ai_rationale, salary, visa_sponsorship, tags.
Invoke:      job_discover.py appends automatically (dedupe by title+company+url).
             Review weekly: filter ai_recommendation==APPLY, sort by confidence,
             tailor + apply to top-N.
When:        Single source of truth; never re-discover without checking master first.
Quality benefit: One pipeline, no duplicate applications, track stage/next action
             per methodology Stage 6. Dedupe prevents wasted re-scoring.
Files:       jobs_master.csv

================================================================================
SKILL 6 — Resume-as-Context for AI Scoring
================================================================================
File:        /tmp/resume_elton.txt (Elton Aguiar resume text)
Purpose:     Full résumé (summary, certs, work history at CIBC/BMO/Metrolinx/RBC/IDC,
             skills) fed as context to AI second-opinion scoring so recommendations
             are grounded in real experience, not generic.
Invoke:      Pass --resume-file /tmp/resume_elton.txt to job_discover.py or
             paste RESUME section into ai_second_opinion.py --context.
When:        Every scoring round. Update when certs/experience change.
Quality benefit: AI scores reflect actual fit (6+ yrs fintech, CSA/CAD, PD1/JS1),
             not hallucinated qualifications.
Files:       /tmp/resume_elton.txt

================================================================================
SKILL 7 — Free AI Provider Roster (verified endpoints + keys)
================================================================================
File:        dbpasses_ASK_2026-11-02.txt (capability map) + dbpasses.txt (key vault)
Purpose:     Verified free AI providers for second-opinion scoring: Groq, Gemini,
             HuggingFace, DeepInfra, OpenRouter, Mistral, PublicAI, Cohere, Cloudflare,
             GitHub Models, Pollinations (keyless), Nous, Z.AI, LLM7 (keyless),
             Kilo Gateway (keyless), OVH (anonymous), local vLLM:8000, Ollama:11434,
             LiteLLM:4000.
Invoke:      ai_second_opinion.py reads from this roster. Add newly verified
             providers to dbpasses_ASK_MISSING_*_2026-11-03.txt files.
When:        Before each scoring round, confirm provider health (PONG probe).
Quality benefit: Zero-cost, unlimited-volume second opinions; local models
             (vLLM/Ollama) have no rate limits for high-volume scoring.
Files:       dbpasses_ASK_2026-11-02.txt, dbpasses.txt, dbpasses_ASK_MISSING_*

================================================================================
SKILL 8 — Target Company List & Career Pages
================================================================================
Purpose:     20–40 companies Elton would genuinely join (fintech + consulting +
             GTA employers). Bookmark each careers page; note ATS type (Greenhouse/
             Lever/Ashby/Workday) for quick re-checks.
Target employers (from resume + research): CIBC, BMO, Metrolinx, RBC, Scotiabank,
             Brookfield, Export Development Canada, Deloitte, Accenture, Capgemini,
             Cognizant, TATA, KPMG, Infosys, CGI, Lightspeed, Moneris, Pyramid
             Consulting, Bell, TEEMA, Versapay, EPAM, ServiceNow, Salesforce,
             ServiceNow/Salesforce consulting partners.
When:        Weekly careers-page re-check (Monday). Supplement with API discovery.
Quality benefit: Employer-direct applications often get reviewed before board-posted
             ones; target-list focus prevents spray-and-pray.
Files:       (maintain in jobs_master.csv source notes or a target-companies.md)

================================================================================
SKILL 9 — GTA Suburb + Remote Canada Expansion
================================================================================
Purpose:     Run discovery per GTA suburb (Mississauga, Markham, Etobicoke, North
             York, Scarborough, Brampton, Vaughan, Oakville, Pickering, Ajax,
             Concord, Woodbridge, Burlington) plus "remote canada" and ambiguous
             Canada postings.
Invoke:      job_discover.py --location mississauga|markham|etobicoke|... or
             --location "remote canada".
When:        After downtown Toronto is exhausted; weekly rotation through suburbs.
Quality benefit: Suburbs have less competition; remote Canada widens the pool
             without relocation.
Files:       jobs_master.csv (location column tracks suburb/remote)

================================================================================
SKILL 10 — Contracting / Staffing Agency Pipeline
================================================================================
Purpose:     Contract roles (6–12 months) convert faster and are plentiful for
             ServiceNow/Salesforce in GTA. Register with agencies and monitor
             their contract postings.
Agencies found: Pyramid Consulting Inc., Capgemini, Panasonic/PCI, BFG Enterprise
             Services, Compugen Inc., 2iSolutions Inc., TEEMA, Insight Global,
             Slalom, J&M Group, US Tech Solutions, Newport Williams, Mindlance,
             OnX, Periscope Search Group, Hire DigITalent, MSITEK, Quantum World,
             Tamanna Technology, Russell Tobin, LanceSoft, Dynamic Connections.
When:        Weekly contract-specific search (query "servicenow contract",
             "salesforce contract"). Apply to contract roles first (faster hire).
Quality benefit: Contracts are a foot-in-the-door at target employers; many
             convert to permanent.
Files:       jobs_master.csv (source=contract agency)

================================================================================
SKILL 11 — Partner-Ecosystem Company Targeting
================================================================================
Purpose:     ServiceNow and Salesforce consulting partners hire developers/admins
             to staff client implementations. Target their careers pages directly.
Partners found: ServiceNow Partner Finder (servicenow.com/partners), Salesforce
             Consulting Partners (salesforce.com/partners), Clutch.co Toronto
             Salesforce consultants (Keyrus, HIC Global Solutions, Passion Fruit
             Partners, NAV43, Massive Insights, Customertimes), Deloitte DTC,
             Accenture, Capgemini, Cognizant, TATA, KPMG, Infosys, Slalom,
             CloudKettle Inc.
When:        Weekly partner-careers-page check. Partners post frequently.
Quality benefit: Partners value certifications (CSA/CAD/PD1/JS1) highly; Elton's
             cert stack is a direct match.
Files:       (careers-page URLs in target-company notes)

================================================================================
SKILL 12 — Fresh / Posted-Today Prioritization
================================================================================
Purpose:     Apply within 24–48h of a role going live (early-window advantage).
             Flag postings with posted==TODAY or fresh==True; prioritize those.
Invoke:      In jobs_master.csv, filter posted contains "TODAY"; sort fresh first.
             LinkedIn filter "Past 24 hours"; Workopolis filter "Date Added: 24 hours".
When:        Every morning check. Today-posted jobs first.
Quality benefit: Early applicants have significantly higher response rates.
Files:       jobs_master.csv (fresh/posted columns)

================================================================================
SKILL 13 — Quality Validation (link + company + location + salary check)
================================================================================
Purpose:     Before committing a job to the master pipeline, verify: URL resolves,
             company is real, location matches target (Toronto/GTA/remote Canada),
             salary is sane for role/level. Discard expired/404/blocked postings.
Invoke:      Spot-check top-N jobs per round; re-verify before applying.
When:        Before apply; after any bulk discovery round.
Quality benefit: Prevents wasted applications to dead postings; keeps pipeline
             clean and actionable.
Files:       jobs_master.csv (remove invalid rows)

================================================================================
SKILL 14 — Tailor & Apply (resume + cover per posting)
================================================================================
Purpose:     Mirror the posting's language so you clear ATS and read as a fit.
             Tailor headline + top bullets per role; skip generic cover letters
             unless asked.
Invoke:      For each APPLY-ranked job: adjust resume summary to echo posting
             keywords (from matched_keywords column), write 1 short cover note,
             apply via company careers page (preferred) or job board.
Cadence:     3–5 applications/week while employed; 8–15/week while searching.
Quality benefit: Tailored applications clear ATS and signal genuine fit; volume
             is secondary to targeting.
Files:       (per-application tailored resume/cover letters)

================================================================================
SKILL 15 — Pipeline Review & Follow-Up (Stage 6 of methodology)
================================================================================
Purpose:     Track every opportunity: company, role, date applied, stage, next
             action + date. Review weekly; find bottleneck; change one thing.
             Follow up ~1 week after applying, max twice, then move on.
Invoke:      Weekly Friday review of jobs_master.csv. Add next_action_date to
             each applied row. Move stale rows to rejected/paused.
When:        Friday pipeline review (per methodology weekly rhythm).
Quality benefit: An application with no next action is passive; weekly review
             keeps momentum and surfaces where you're stuck.
Files:       jobs_master.csv (add stage/next_action columns as needed)

================================================================================
RECOMMENDED WEEKLY PIPELINE (combine skills)
================================================================================
Monday:    Skill 1 (discover all keywords/locations) → Skill 3 (ATS probe) →
           Skill 9 (suburbs/remote) → Skill 10 (contracts) → Skill 11 (partners)
           → Skill 13 (validate) → update jobs_master.csv
Tue–Thu:   Skill 2 (AI score top-N) → Skill 6 (resume context) → Skill 4
           (cert keywords) → Skill 12 (fresh-today first) → Skill 14 (tailor +
           apply 3–8 best-fit) → Skill 15 (log next actions)
Friday:    Skill 15 (pipeline review + follow-ups) → network outreach (5–8 msgs)
Weekend:   Skill 7 (provider health re-check) → build proof (one project/demo)

================================================================================
FILES IN THIS SESSION
================================================================================
  docs/JOB_HUNTING_SKILLS.md             (this file)
  tools/job_discover.py                  (Skill 1)
  tools/ai_second_opinion.py             (Skill 2)
  tools/ats_probe.py                     (Skill 3)
  job_search_cert_keyword_bank_2026-11-03.md  (Skill 4)
  jobs_master.csv                        (Skill 5)
  /tmp/resume_elton.txt                  (Skill 6)
  dbpasses_ASK_2026-11-02.txt            (Skill 7 roster)
  dbpasses.txt                           (Skill 7 key vault)
  dbpasses_ASK_MISSING_*_2026-11-03.txt  (Skill 7 additional providers)
  JOB_SEARCH_METHODOLOGY.md              (6-stage execution framework)
  data/ats_probe_companies.json          (Skill 3 company list)
  data/ats_probe_results.json            (Skill 3 results)
  data/web_search_jobs_round*.json       (Skill 1 raw results)
