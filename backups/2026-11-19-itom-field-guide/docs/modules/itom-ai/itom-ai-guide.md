# AI in ITOM

**Agent:** Kilo (deepseek-flash) · **Updated:** 2026-11-19 · **App:** AI in ITOM · **Confidence:** high (official docs, fast-moving area)

AI in ITOM is not a single button. It is a set of capabilities, model providers, governance
controls, and product-specific skills layered on records you must already trust. The Australia
release also changes the packaging direction: **Now Assist for ITOM is being prepared for future
deprecation**, while **ServiceNow Otto for ITOM** and the **ITOM MCP Server Console** are the
forward-looking surfaces.

Read this guide as a governance map, not a feature catalogue. The features will move; the
governance questions will not.

---

## Contents

- [What changed in the Australia era](#what-changed-in-the-australia-era)
- [AI tiers](#ai-tiers)
- [Model providers and controls](#model-providers-and-controls)
- [ServiceNow Otto for ITOM](#servicenow-otto-for-itom)
- [ITOM MCP Server Console](#itom-mcp-server-console)
- [Now Assist and Otto inside the Service Operations Workspace](#now-assist-and-otto-inside-the-service-operations-workspace)
- [Where AI appears in ITOM](#where-ai-appears-in-itom)
- [LEAP](#leap)
- [Governance checklist](#governance-checklist)
- [Regional and data considerations](#regional-and-data-considerations)
- [Common mistakes](#common-mistakes)
- [Quiz](#quiz)
- [Official sources](#official-sources)
- [Related guides](#related-guides)

---

## What changed in the Australia era

From the official Now Assist for ITOM page:

- Starting with the **Australia** release, Now Assist is being prepared for future deprecation.
- It is hidden and no longer installed on new instances.
- It continues to be supported for existing customers.
- The platform introduces a new AI experience with **Foundation**, **Advanced**, and **Prime**
  tiers.
- ServiceNow Otto for ITOM is the current assistant/agent direction in the ITOM documentation.
- The ITOM MCP Server Console exposes ITOM capabilities to AI agents through the Model Context
  Protocol.

**Do not build a new architecture on a deprecating surface without a migration plan.** Check the
deprecation KB and the current product page before you commit.

---

## AI tiers

| Tier | What it means |
|---|---|
| **Foundation** | Basic AI insights |
| **Advanced** | AI to enhance productivity across relevant use cases |
| **Prime** | Autonomous AI actions with the full AI assets and custom creation capability |

The tier is a licensing and capability boundary, not a quality rating. A Prime licence does not
make a bad use case good.

---

## Model providers and controls

The Australia docs list these model providers for generative AI skills and AI agents:

- Now LLM Service
- Azure OpenAI
- Google Gemini
- Anthropic Claude

Configuration controls live in **AI Control Tower** (which options are available) and
**AI Admin Hub** (skill-level preferences).

Rules:

- Not all providers are available in all regions or for all customers.
- Restrictions apply to in-country SKUs, regulated markets, FedRAMP, NSC DOD IL5, Australia
  IRAP-Protected data centres, self-hosted environments, and other restricted environments.
- Check availability before designing a workflow that depends on a specific model.

---

## ServiceNow Otto for ITOM

Otto for ITOM is the AI assistant/agent capability referenced throughout the Australia ITOM
documentation. It is used for:

- AI-assisted log mapping in Health Log Analytics (suggesting the best log fields).
- Setup assistance for ITOM AIOps apps.
- Problem-record and playbook generation in LEAP.
- Other ITOM skills as they are released.

The installation and app list are documented. Treat the installed app list as the source of
truth for what your instance can actually do.

---

## ITOM MCP Server Console

The **ITOM MCP Server Console** is used to manage the MCP server that exposes ITOM capabilities
to AI agents. The official page describes using the console; the details are product-version
specific.

Governance questions to ask before exposing anything:

1. Which ITOM capabilities are exposed as tools?
2. Which agent identities can call them?
3. What is read-only versus write-capable?
4. Where are the approvals and audit records?
5. What happens when the agent is wrong?

If you cannot answer those five, do not connect the agent to production.

---

## Now Assist and Otto inside the Service Operations Workspace

The most visible AI in ITOM lives in the Service Operations Workspace (SOW) and the Express
List. These are **existing-customer capabilities** under the Now Assist for ITOM packaging, and
the same functions are the forward path under ServiceNow Otto for ITOM. Verify the current app
version and entitlement on your instance.

### Alert analysis by ServiceNow Otto

In the Express List, a user can open an alert and select **Analyze** in **Alert analysis by
ServiceNow Otto**. The result:

- a **human-readable brief** of the alert,
- **technical information** to help investigate it,
- copy/refresh actions (refreshing regenerates and deletes past results).

Prerequisites: the ServiceNow Otto for ITOM application and the `evt_mgmt_operator` role.

### Past related incidents summary

With the **Alert investigation skill** active, a user can request an investigation of past
incidents related to the current alert. The ServiceNow Otto panel returns a summary of the most
relevant related incidents and the strategies used to resolve them.

Role: `evt_mgmt_operator`.

### Save an analysis as an alert group description

The AI-generated alert analysis can be saved as the description of an alert group. This keeps a
concise, AI-written summary visible to the whole team.

Roles: `evt_mgmt_operator`, `evt_mgmt_admin`.

### Probable Root Cause Analysis (RCA)

Probable RCA reduces mean time to repair by listing the likely root causes of an alert. It uses:

1. **Alerts** and alert groups,
2. **CI topology** in the CMDB,
3. **Change requests** on the relevant CIs.

It filters relevant change requests, calculates a root cause score, and shows the top five
probable root causes with an explanation of how the alert correlates to the change. For alert
groups it identifies upstream topology-origin CIs to explain cascading failures.

- The score prioritises changes on topology-originating CIs, then related CIs, then direct CIs.
- It can be disabled with the system property `sa_analytics.disable_prc` set to `true`.
- It is not a verdict. It is a ranked hypothesis list: verify the change and the CI topology
  before declaring a root cause.

### Human control

Every AI output in this section is **assistive**:

- The alert analysis is a brief; the alert record is the source of truth.
- The past-incident summary is context; the incidents are the evidence.
- The saved alert group description is editable.
- RCA is a hypothesis; the change record and the relationship map are the proof.

If you cannot verify an AI statement against a record, do not teach it.

---

## Where AI appears in ITOM

| Area | AI capability (examples) | Human control |
|---|---|---|
| Discovery | AI-assisted content and process classification (ITOM Content Service) | Review suggestions before promoting |
| Service Mapping | Automated Service Suggestions / Predictive Intelligence | Review connections; tune rules |
| Health Log Analytics | AI-assisted log mapping; anomaly detection | Test mapping; mark significant/mute |
| Event Management | Alert analysis, past-incident summary, alert group description, probable RCA | Verify the alert, CI, and change records |
| SLO Management | AI-generated SLO suggestions | Agree the target and owner |
| Certificate Inventory | AI-assisted renewal | Approve or reject the renewal |
| Firewall Audits | AI in firewall audit reporting | Verify the finding |
| LEAP | Knowledge and playbook generation | Review before publishing |
| Service Observability | Analyze dashboards/service health | Verify the metric and entity |

The pattern is consistent: **AI proposes, the record disposes.**

---

## LEAP

The Learning Enhanced Automation Platform uses AI-driven insights and automation to help manage
IT operations. It supports:

- creating problem records and playbooks,
- AI model providers (Azure OpenAI, Google Gemini, Anthropic Claude),
- skill-level configuration in AI Admin Hub,
- LEAP savings metrics and prioritisation logic.

LEAP is under ITOM Visibility in the Australia documentation. It is an AI capability, not a
discovery engine.

---

## Governance checklist

Before enabling any ITOM AI capability:

- [ ] The use case has a named owner and a measurable outcome.
- [ ] The data the AI will read is classified and allowed to leave the region (if applicable).
- [ ] The model provider is available for your region/SKU.
- [ ] AI Control Tower and AI Admin Hub are configured.
- [ ] The capability is read-only or has an approval gate for writes.
- [ ] There is an audit trail for AI actions.
- [ ] A human verifies outputs against the record.
- [ ] There is an off-ramp if the model is unavailable or wrong.
- [ ] Users are told when they are seeing AI-generated content.
- [ ] The AI Acceptable Use Policy and data opt-out are understood.

---

## Regional and data considerations

From the official pages:

- Data may be transferred from the customer instance to a centralized ServiceNow environment in
  a different region, and potentially to a third-party cloud provider such as Microsoft Azure.
- ServiceNow collects inputs, outputs, and edits to improve its AI technologies.
- Customers can opt out of future data collection via the AI Opt-Out page.
- Some AI products/features are unavailable in FedRAMP, NSC DOD IL5, Australia IRAP-Protected
  data centres, self-hosted environments, and other restricted environments.
- Some products/skills are unavailable in Regulated Markets.

These are contractual and compliance decisions. Do not let a lab shortcut them.

---

## Common mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Treating Now Assist for ITOM as the permanent architecture | New instances do not get it | Plan for Otto/MCP and check the deprecation KB |
| Enabling AI without a model-availability check | The skill does not work in your region | Verify AI Control Tower and provider availability |
| Letting an agent write without approval | Unreviewed changes to production | Read-only first; approval gate for writes |
| Trusting a summary as evidence | Confident wrong answer | Verify against `em_alert`, the map, or the log |
| Ignoring data residency | Compliance breach | Review data processing and opt-out |
| No owner for AI output | Nobody fixes wrong suggestions | Assign an owner and a review cadence |
| Skipping the Acceptable Use Policy | Legal/ethical risk | Read and apply it |

---

## Quiz

1. **What is happening to Now Assist for ITOM in the Australia release?**
   <details><summary>Answer</summary>It is being prepared for future deprecation: hidden, not installed on new instances, but supported for existing customers.</details>

2. **Name the three AI tiers.**
   <details><summary>Answer</summary>Foundation, Advanced, Prime.</details>

3. **Where do you control which model providers are available?**
   <details><summary>Answer</summary>AI Control Tower (configuration controls) and AI Admin Hub (skill-level preferences).</details>

4. **What is the ITOM MCP Server Console for?**
   <details><summary>Answer</summary>Managing the MCP server that exposes ITOM capabilities to AI agents.</details>

5. **What is the rule of thumb for AI output in ITOM?**
   <details><summary>Answer</summary>AI proposes, the record disposes: verify against the actual record before acting or teaching.</details>

6. **What three inputs does Probable RCA use?**
   <details><summary>Answer</summary>Alerts/alert groups, CI topology in the CMDB, and change requests on the relevant CIs.</details>

7. **Where in the UI do you find alert analysis by ServiceNow Otto?**
   <details><summary>Answer</summary>The Express List in the Service Operations Workspace: open an alert and select Analyze in Alert analysis by ServiceNow Otto.</details>

---

## Official sources

- Now Assist for ITOM — <https://www.servicenow.com/docs/r/australia/it-operations-management/now-assist-for-it-operations-management.html>
- Install Otto for ITOM — <https://www.servicenow.com/docs/r/australia/it-operations-management/install-now-assist-itom.html>
- Applications installed with Otto for ITOM — <https://www.servicenow.com/docs/r/australia/it-operations-management/app-now-assist-itom.html>
- Use the ITOM MCP Server Console — <https://www.servicenow.com/docs/r/australia/it-operations-management/use-itom-mcp-server.html>
- AI in ITOM — <https://www.servicenow.com/docs/r/australia/it-operations-management/ai-in-it-operations-management.html>
- LEAP — <https://www.servicenow.com/docs/r/australia/it-operations-management/aiops-leap-learning-enhanced-automation-playbooks/aiops-leap.html>
- HLA AI-assisted mapping — <https://www.servicenow.com/docs/r/australia/it-operations-management/health-log-analytics/hla-data-input-automapping.html>
- Alert analysis by ServiceNow Otto — <https://www.servicenow.com/docs/r/australia/it-operations-management/event-management/alert-summary-now-assist-express-list.html>
- Generate a past related incidents summary — <https://www.servicenow.com/docs/r/australia/it-operations-management/event-management/nai-analyze-past-incidents.html>
- Save alert analysis as alert group description — <https://www.servicenow.com/docs/r/australia/it-operations-management/event-management/alert-group-descr-now-assist-el.html>
- Probable Root Cause Analysis — <https://www.servicenow.com/docs/r/australia/it-operations-management/event-management/probable-rca.html>

---

## Related guides

- [ITOM overview](../itom-overview/itom-overview-guide.md)
- [Discovery](../discovery/discovery-guide.md)
- [Health Log Analytics](../health-log-analytics/health-log-analytics-guide.md)
- [Visibility suite](../visibility-suite/visibility-suite-guide.md)
