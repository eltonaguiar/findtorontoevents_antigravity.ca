# AI in ITOM start

**Agent:** Kilo (deepseek-flash) · **Updated:** 2026-11-19 · **Docs release:** Australia

A 45-minute orientation. The first job is governance, not prompts.

---

## 1. Understand the packaging shift

- **Now Assist for ITOM** is being prepared for future deprecation from the Australia release:
  hidden, not installed on new instances, supported for existing customers.
- **ServiceNow Otto for ITOM** and the **ITOM MCP Server Console** are the forward-looking
  surfaces in the current documentation.
- The platform AI tiers are **Foundation**, **Advanced**, and **Prime**.

Do not start a new architecture on a deprecating surface without a migration plan.

Full guide: [AI in ITOM](../modules/itom-ai/itom-ai-guide.md).

---

## 2. Check availability

| Check | Where |
|---|---|
| AI tier / entitlement | Contract and AI Control Tower |
| Model providers available | AI Control Tower; AI Admin Hub |
| Regional restrictions | Official AI product page and KBs |
| Data residency / opt-out | AI Opt-Out page and compliance |
| ITOM app entitlement | Licensing and Store |

If the model provider is unavailable in your region, the skill will not work. That is a
prerequisite failure, not a prompt problem.

---

## 3. Pick a safe first use case

Good first use cases are read-only and verifiable:

- Suggest a log mapping in HLA and compare it to the actual log.
- Summarise an alert and verify it against `em_alert` and the CI.
- Suggest a service candidate and compare it to the map.
- Generate a draft knowledge article for a well-understood issue and have the owner review it.

Bad first use cases:

- Autonomous remediation in production.
- Writing to the CMDB without review.
- Security-sensitive decisions.
- Anything you cannot verify against a record.

---

## 4. The governance checklist

- [ ] Owner and measurable outcome.
- [ ] Data classification and residency approved.
- [ ] Model provider available.
- [ ] AI Control Tower and AI Admin Hub configured.
- [ ] Read-only or approval gate for writes.
- [ ] Audit trail for AI actions.
- [ ] Human verification against the record.
- [ ] Off-ramp if the model is unavailable or wrong.
- [ ] Users told when content is AI-generated.
- [ ] Acceptable Use Policy and opt-out understood.

---

## 5. Prove it

For any AI-assisted result, write:

1. What the AI proposed.
2. Which record you checked.
3. Whether it matched.
4. What a human changed.
5. What you would not let the AI do yet.

If you cannot fill those five lines, the AI is not ready for that use case.

---

## Official sources

- Now Assist for ITOM — <https://www.servicenow.com/docs/r/australia/it-operations-management/now-assist-for-it-operations-management.html>
- Otto for ITOM — <https://www.servicenow.com/docs/r/australia/it-operations-management/install-now-assist-itom.html>
- ITOM MCP Server Console — <https://www.servicenow.com/docs/r/australia/it-operations-management/use-itom-mcp-server.html>
- AI in ITOM — <https://www.servicenow.com/docs/r/australia/it-operations-management/ai-in-it-operations-management.html>
- LEAP — <https://www.servicenow.com/docs/r/australia/it-operations-management/aiops-leap-learning-enhanced-automation-playbooks/aiops-leap.html>
