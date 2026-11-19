# 05 — Merge handoff

**Agent:** Kilo (deepseek-flash) · **Date:** 2026-11-19

This repository is designed to become a new **ITOM** section in the larger ServiceNow learning
site. This document is the integration plan. It deliberately does not modify the other repo.

---

## 1. Target

The existing module-guide repository is:

<https://github.com/eltonaguiar/ServiceNow_Learning_TSOM-_CSM_FSM_SalesCRM_HAM_ITSM>

It already contains an ITOM page at:

```
docs/modules/itom/itom-guide.md
```

and a Discovery guide at:

```
docs/modules/discovery/discovery-guide.md
```

Those pages are not empty. Do not overwrite them blindly. Merge by topic.

---

## 2. Recommended content mapping

| This repo | Target in the main site | Action |
|---|---|---|
| `docs/modules/itom-overview/itom-overview-guide.md` | `docs/modules/itom/itom-overview.md` | Add as the new family overview |
| `docs/modules/cmdb/cmdb-guide.md` | `docs/modules/itom/cmdb-foundation.md` | Add as the shared data foundation |
| `docs/modules/discovery/discovery-guide.md` | `docs/modules/itom/discovery.md` | Add as the ITOM Discovery guide; keep the existing FBD deep dive as a sibling |
| `docs/modules/service-mapping/service-mapping-guide.md` | `docs/modules/itom/service-mapping.md` | Add |
| `docs/modules/event-management/event-management-guide.md` | `docs/modules/itom/event-management.md` | Add |
| `docs/modules/health-log-analytics/health-log-analytics-guide.md` | `docs/modules/itom/health-log-analytics.md` | Add |
| `docs/modules/reliability-stack/reliability-stack-guide.md` | `docs/modules/itom/reliability-stack.md` | Add |
| `docs/modules/cloud-accelerate/cloud-accelerate-guide.md` | `docs/modules/itom/cloud-accelerate.md` | Add |
| `docs/modules/agent-client-collector/acc-guide.md` | `docs/modules/itom/agent-client-collector.md` | Add |
| `docs/modules/metric-intelligence/metric-intelligence-guide.md` | `docs/modules/itom/metric-intelligence.md` | Add |
| `docs/modules/itom-ai/itom-ai-guide.md` | `docs/modules/itom/ai-in-itom.md` | Add |
| `docs/modules/visibility-suite/visibility-suite-guide.md` | `docs/modules/itom/visibility-suite.md` | Add |
| `docs/modules/automation-remediation/automation-remediation-guide.md` | `docs/modules/itom/automation-remediation.md` | Add |
| `docs/modules/resilience-security/resilience-security-guide.md` | `docs/modules/itom/resilience-security-compliance.md` | Add |
| `docs/09-coverage-map.md` | `docs/itom/coverage-map.md` | Add |
| `docs/00-methodology.md` .. `docs/08-source-ladder.md` | `docs/itom/...` or shared reference | Add under a shared ITOM reference folder |
| `labs/LAB-*.md` | `labs/itom/...` | Add |
| `docs/getting-started/*.md` | `getting-started/itom/...` | Add |
| `data/modules.json` | Merge the `modules` array | Merge, do not replace the existing file blindly |
| `data/sources.json` | Merge the `per_module` entries | Merge |
| `assets/` | Usually identical; diff first | Reuse if identical |
| `_layouts/default.html` | Add ITOM nav entries | Merge nav, not the whole file |
| `research/`, `meta/`, `updates/` | Keep out of the published site | Keep in repo or a non-published folder |

---

## 3. Preserve URLs

If the main site already links to `/docs/modules/itom/itom-guide/`, keep that URL alive:

- Keep `itom-guide.md` as a short landing page that links to the new sub-guides, **or**
- add a redirect page (Jekyll `redirect_from` or an HTML meta refresh).

Do not break an existing inbound link.

---

## 4. Merge the existing Discovery content

The existing `docs/modules/discovery/discovery-guide.md` is a deep dive on File-Based Discovery.
The new guide is a broader ITOM Discovery guide. Recommended structure:

```
docs/modules/discovery/
  discovery-guide.md          # existing FBD deep dive (keep)
  discovery-overview.md       # new ITOM Discovery guide
  file-based-discovery.md     # optional split of the existing FBD content
```

Or, if the existing page is replaced:

1. Preserve its FBD sections in a new page.
2. Link both pages from the Discovery card and the ITOM sidebar.
3. Keep the old anchors or add redirects.

Do not silently delete the FBD content. It is complementary, not duplicated.

---

## 5. Navigation changes

Add a top-level **ITOM** group to the main site:

```yaml
ITOM:
  - ITOM overview
  - Discovery
  - Service Mapping
  - Event Management
  - Health Log Analytics
  - Reliability stack
  - Cloud Accelerate
  - Agent Client Collector
  - Metric Intelligence
  - AI in ITOM
  - Visibility suite
  - Licensing and prerequisites
  - Roles and tables
  - Common mistakes
  - Glossary
  - Labs
```

Order matters: overview → visibility → AIOps → cloud → agents/AI → reference → labs. This mirrors
the dependency order.

---

## 6. Data merge

The existing `data/modules.json` may be a different shape (for example, a sequence of objects).
Our file is:

```json
{
  "_meta": { "...": "..." },
  "modules": [ { "id": "...", "...": "..." } ]
}
```

Merge by `id`. Keep the existing module entries and append the ITOM entries. If the existing
file is a JSON Lines or concatenated-object format, normalise it first, then merge; do not
produce invalid JSON.

The existing `data/sources.json` has a similar `_meta`/`allowlisted_domains`/`ladder` shape.
Merge the `per_module` entries and keep one allowlist.

---

## 7. Site assets

The layout and CSS in this repo are adapted from the target site. Before merging:

1. Diff `assets/css/style.scss` and `assets/js/site.js` against the target.
2. If they are identical, do nothing.
3. If they differ, take the target's version unless this repo's changes are intentional.
4. Merge nav links, not the whole layout.

The ITOM pages use the same class names (`card-grid`, `card`, `verdict`, `pill`, `mermaid`), so
they render without CSS changes.

---

## 8. Content review before merge

- [ ] Every guide's "Official sources" still resolves.
- [ ] The Australia release pin is still accurate, or update it.
- [ ] The existing Discovery FBD content is preserved.
- [ ] The ITOM nav entries are added to the target layout.
- [ ] Existing inbound URLs still work.
- [ ] `data/modules.json` is valid JSON after the merge.
- [ ] `python3 scripts/sn_lint.py` passes in the merged repo (or the equivalent check).
- [ ] A spot-check of three pages renders the TOC, code blocks, and Mermaid diagrams.

---

## 9. What not to merge

- `research/` — internal evidence trail; keep it in the source repo or exclude it.
- `meta/` — agent records.
- `updates/` — changelog entries.
- `.github/workflows/` — the target has its own deployment; do not overwrite it.
- `README.md` — the target has its own.

---

## 10. Definition of done for the merge

1. The ITOM section is reachable from the main nav.
2. The old ITOM page still resolves and points to the new content.
3. Discovery FBD content is preserved.
4. All relative links resolve.
5. The Pages build succeeds.
6. A reader can go from the ITOM overview to a lab without a dead end.

---

**Agent:** Kilo (deepseek-flash) · **Updated:** 2026-11-19
