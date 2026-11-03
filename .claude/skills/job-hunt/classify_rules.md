# Classification prompt (paste rows as `index|title|company|location`)

Classify each Canadian job posting row into exactly one class:

- SN: ServiceNow PLATFORM role — developer/administrator/architect/consultant,
  ITSM/ITOM/CMDB/Discovery/Service Mapping, ITAM/SAM-with-platform, HRSD, SPM,
  CSM, SecOps, IRM/GRC-on-ServiceNow, Now Assist, Integration Hub.
- SF: Salesforce ecosystem — developer/administrator/architect/consultant/BA,
  Apex, LWC, Visualforce, OmniStudio, Vlocity, nCino, CPQ, Revenue Cloud,
  Marketing Cloud, Data Cloud, Commerce Cloud, FSC, Agentforce, MuleSoft, Copado.
- OTHER: resume-relevant IT — Power BI/Tableau/BI, Data Analyst/Engineer,
  Python, SQL, DevOps/CI-CD, ITAM/SAM, Systems Administrator, Alteryx, Databricks.
- REJECT: account exec/BDR/sales-engineer/recruiter, customer-success/CSM,
  GTM/RevOps managers, marketing-ops, generic management/ops/HR/finance roles,
  exec/director strategy, BIM/construction, business-continuity, service-desk/
  helpdesk, non-IT, US-only/India-only/Colombia-only locations.

Hard rules:
- A ServiceNow/Salesforce KEYWORD HIT in search does not make it a platform
  role. Titles like "Portfolio Management Analyst", "BIM Coordinator",
  "Executive Director", "Manager, Business Continuity" are REJECT.
- Same job via a different board/URL is a duplicate — but the MERGER handles
  URL dedup; your job is class only.
- Respond ONLY with a JSON array covering EVERY row, using the given indices:
  [{"i":0,"c":"SN"},{"i":1,"c":"REJECT"},...]
