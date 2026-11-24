# Changelog

**Agent:** Kilo (deepseek-flash) · **Repository:** ServiceNowLearning_ITOM

## v1.2.0 — 2026-11-19

### Added

- CMDB foundation guide.
- Automation and remediation guide.
- Resilience, security, and compliance guide.
- Coverage map page (pillars + subtopics).
- Containers/Kubernetes discovery section.
- Now Assist/Otto alert analysis, past incidents, alert group description, and Probable RCA in the AI guide.
- Cloud cost/capacity, Cloud Action Library, and Cloud Migration Assessment retirement correction.
- Peer review record (research/06_PEER_REVIEW.md).

### Changed

- Navigation, index, family map, README, study plan, roles/tables, common mistakes, glossary.
- Extended data/modules.json (14 modules) and data/sources.json.
- Extended research source matrix, decisions, and merge handoff.

### Verified

- `python3 scripts/sn_lint.py` passes (0 errors).


---

## v1.0.0 — 2026-11-19

### Added

- Full ITOM field guide: overview, Discovery, Service Mapping, Event Management, Health Log
  Analytics, reliability stack, Cloud Accelerate, Agent Client Collector, Metric Intelligence,
  AI in ITOM, and the Visibility specialist suite.
- Methodology: Orient → Model → Practise → Prove → Teach.
- ELI5, family map, licensing, roles and tables, common mistakes, study plan, glossary, and
  source ladder.
- Five labs: orientation, Discovery, event-to-incident, Service Mapping, and HLA.
- Seven getting-started pages.
- `data/modules.json` and `data/sources.json`.
- Research protocol artifacts: charter, plan, source matrix, content decisions, verification,
  and merge handoff.
- Jekyll site with the existing guide's design language.
- GitHub Pages deployment workflow and a content lint workflow.

### Verified

- `python3 scripts/sn_lint.py` — 34 docs, 0 errors, 0 warnings.
- All 71 official docs URLs matched the Australia ITOM topic map.
- Content checks and Pages deploy workflows succeeded.
- Deployed site: <https://eltonaguiar.github.io/ServiceNowLearning_ITOM/>.
- Internal link crawl: 47 checked, 0 broken.
- Browser check: Mermaid renders, TOC populates, no horizontal overflow, 0 console errors.

See `research/04_VERIFICATION.md` for details and known limitations.

## v1.0.1 — 2026-11-19

### Fixed

- Replaced the deprecated `mermaid.init(...)` call with the Mermaid 10 `mermaid.run({ nodes })`
  API. The diagrams rendered before, but the page emitted a console error on every load. The
  redeploy was verified with a headless browser: 0 console errors.

### Known limitations

- Content is pinned to the Australia release. Re-check on a new family release.
- Some products require entitlements not available on a PDI; labs include design-only paths.
- Menu labels and some table display names vary by Store app version; verify in the dictionary.
- The AI area is fast-moving; the governance model is more durable than the feature list.

---

**Agent:** Kilo (deepseek-flash) · **Updated:** 2026-11-19
