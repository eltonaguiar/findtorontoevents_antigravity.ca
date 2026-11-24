# Delegated task output

- model: `ULTRA_FREE_CLOUD_LARGE`
- generated_utc: 2026-11-18T03:52:45Z
- status: ok

## Response

# High-Signal Keywords & Regex Hints for IT Service Management Role Detection

## Track 1: ServiceNow (Core)

| # | Signal Type | Keyword / Pattern | Regex Hint | Notes |
|---|---|---|---|---|
| 1 | Certification | CSA (Certified System Administrator) | `\bCSA\b` (case-insensitive, word boundary) | Must co-occur with ServiceNow context to avoid C#/CSA general matches |
| 2 | Certification | CAD (Certified Application Developer) | `\bCAD\b` | False positive risk: CAD as Computer-Aided Design. Require "ServiceNow" within ±20 tokens |
| 3 | Certification | CIS (Certified Implementation Specialist) | `CIS[\s-]*(?:ITSM|ITOM|ITAM|Discovery|Event|HR|CSM|GRC|IntegrationHub|Application|Platform|Software|Vendor|Sourcing|FieldService|MDC|Enterprise)` | CIS alone is too broad (Center for Internet Security, etc.) |
| 4 | Certification | CTA (Certified Technical Architect) | `\bCTA\b` | Rare; high value. Watch false positive "CTA" (call-to-action) |
| 5 | Certification | CSA-CAD combo | `(?:CSA|CAD).{0,200}(?:CAD|CSA)` | Strong signal when both appear in same posting |
| 6 | Role (EN) | ServiceNow Developer | `ServiceNow.{0,30}(?:Developer|Engineer|Architect)` | Also catch "SN Developer" |
| 7 | Role (EN) | ServiceNow Consultant | `ServiceNow.{0,30}(?:Consultant|Advisor|Admin|Administrator)` | |
| 8 | Role (FR) | Développeur ServiceNow | `D[ée]veloppeur.{0,20}ServiceNow\|ServiceNow.{0,20}D[ée]veloppeur` | Slash form: "Développeur(se)" |
| 9 | Role (FR) | Consultant/Administrateur ServiceNow | `(?:Consultant|Administrateur|Admin).{0,20}ServiceNow\|ServiceNow.{0,20}(?:Consultant|Administrateur|Admin)` | Also catch "Consultant(e)" |
| 10 | Platform Keyword | ServiceNow-specific products | `(?:ITSM|ITOM|ITAM|CSM|GRC|HRSD|Discovery|Orchestration|IntegrationHub|Flow Designer|App Engine|Service Portal|Now Platform|ServiceNow)` | ITSM/ITAM/ITOM also appear in broad IT context—require ServiceNow or adjacent certs |

## Track 2: Salesforce (Core)

| # | Signal Type | Keyword / Pattern | Regex Hint | Notes |
|---|---|---|---|---|
| 11 | Certification | PD1 / PD2 (Platform Developer I/II) | `(?:PD[1-2]|Platform Developer [I1II2])` | PD2 = Platform Developer II. Watch PD1 false positive (product design phase 1) |
| 12 | Certification | Salesforce Admin/Consultant certs | `(?:Salesforce).{0,30}(?:Admin|Administrator|
