# Official source ladder

**Agent:** Kilo (deepseek-flash) · **Updated:** 2026-11-19 · **Docs release:** Australia

A claim is not "known" because a blog said it. It is known when an official ServiceNow source
says it **and** your instance demonstrates it. This page records where the facts in this guide
came from and how to re-check them.

---

## 1. The ladder

Read in this order. Stop as soon as the question is answered.

| # | Source | Use it for | URL |
|---|---|---|---|
| 1 | **Product documentation** | Architecture, process flow, field/table definitions, roles, plugins, release notes | <https://www.servicenow.com/docs/> |
| 2 | **Now Create / Success Packs** (via Now Learning) | Implementation sequence, prerequisites, acceptance criteria, Crawl → Walk → Run | <https://learning.servicenow.com/lxp> — search "Now Create" |
| 3 | **ServiceNow University / Now Learning** | Courses, learning paths, certification tracks, simulation labs | <https://learning.servicenow.com/lxp> |
| 4 | **Developer portal + PDI** | Free instance, API Explorer, sample code, developer learning plans | <https://developer.servicenow.com/dev.do> |
| 5 | **ServiceNow Store** | App versions, activation notes, entitlement requirements | <https://store.servicenow.com/store> |
| 6 | **Now Support / Knowledge Base** | Known errors, troubleshooting, patch advisories | <https://support.servicenow.com/now> |
| 7 | **Community** | Real-world gotchas and peer context | <https://community.servicenow.com/> |

Community is last for a reason: it is peer content, not the citation of record. Use it to find
the question, then confirm the answer on sources 1–6 or your instance.

---

## 2. Release pinning

ServiceNow documentation is release-versioned. The ITOM guides here were read against the
**Australia** release, whose ITOM documentation home is:

<https://www.servicenow.com/docs/r/australia/it-operations-management>

Deep links contain the release segment (`/australia/`). When a new family release ships:

1. Replace the release segment, or use the unversioned docs and select the release.
2. Re-check the page title and the "Updated" date.
3. Re-run the module's lab on an instance at that release.
4. Update the guide's `Updated` stamp and the source matrix.

Do not silently keep an old URL and call it current.

---

## 3. How this guide was researched

- The official ITOM documentation map for the Australia release was used to enumerate the
  product sections and topics.
- Individual topic pages were read to confirm mechanics, roles, tables, and caveats.
- Facts were paraphrased into original prose. **No documentation pages are mirrored in this
  repository**, and no bulk copy of ServiceNow content is stored here.
- Every guide ends with an **Official sources** section listing the pages read.
- Where a statement depends on subscription, plugin, or instance configuration, the guide says
  so instead of presenting it as universal.

The machine-readable source catalog is [`data/sources.json`](https://github.com/eltonaguiar/ServiceNowLearning_ITOM/blob/main/data/sources.json). The
per-guide source matrix is [`research/02_SOURCE_MATRIX.md`](https://github.com/eltonaguiar/ServiceNowLearning_ITOM/blob/main/research/02_SOURCE_MATRIX.md).

---

## 4. How to verify a claim

| Claim type | Verify with |
|---|---|
| "The phase is called X" | The process/architecture page for that product, current release |
| "The table is called X" | System Definition > Tables; the reference page |
| "The role is called X" | User Administration > Roles; the product's roles page |
| "The plugin is X" | System Applications > Plugins; the install page |
| "It is included in the subscription" | The licensing page and your contract; never assume |
| "The connector supports X" | The connector page and the supported version table |
| "The AI can do X" | The AI product page plus AI Control Tower and model availability for your region |

If you cannot verify it, mark it as **unverified** in your notes. An honest gap is more useful
than a confident error.

---

## 5. Terms of use guardrails

- Read manually; summarise in your own words; cite the URL.
- Do not bulk-scrape, crawl, mirror, or republish ServiceNow documentation.
- Do not sell guides that are mostly copied vendor content.
- Do not put customer data, credentials, or confidential screenshots in this repository.
- Respect the ServiceNow AI Acceptable Use Policy and your organisation's data-handling rules
  when using AI features or sending data to a model provider.

---

## 6. Source map for this repository

| Guide | Primary official pages |
|---|---|
| ITOM overview | ITOM overview, ITOM Visibility, ITOM licensing |
| Discovery | Exploring Discovery, Discovery schedule reference, Discovery status, ECC queue |
| Service Mapping | Service Mapping overview, Choose the right method, Entry point attributes |
| Event Management | Event Management, process flow, event rules, CI binding, alert priority, alert management rules |
| Health Log Analytics | HLA landing page, architecture, alert generation, data inputs, mapping, severity |
| Reliability stack | SRM, Service Observability, Synthetic monitoring, SLO Management |
| Cloud Accelerate | CPG, Cloud Services Catalog, Cloud Account Management, CCG, Cloud Action Library |
| Agent Client Collector | Exploring ACC, ACC framework, ACC log analytics, certificates |
| Metric Intelligence | Exploring Metric Intelligence, configuration |
| AI in ITOM | Now Assist for ITOM, Otto, MCP Server Console, LEAP |
| Visibility suite | Certificate Inventory, Tag Governance, Firewall Audits, AI Agent Topology, ITOM Content Service, Cloud Discovery Workspace, Cloud License Estimator |

---

## Official sources

- ServiceNow product documentation — <https://www.servicenow.com/docs/>
- ITOM documentation (Australia) — <https://www.servicenow.com/docs/r/australia/it-operations-management>
- ServiceNow University / Now Learning — <https://learning.servicenow.com/lxp>
- ServiceNow Developer portal — <https://developer.servicenow.com/dev.do>
- ServiceNow Store — <https://store.servicenow.com/store>
- Now Support — <https://support.servicenow.com/now>
- ServiceNow Community — <https://community.servicenow.com/>
