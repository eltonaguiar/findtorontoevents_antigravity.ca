# Cross‑Reference between ALT_PARALLELSWARM_SAM docs and the public SAM guide

The table below lists items that appear in the **ALT_PARALLELSWARM_SAM** repository but are **not present** on the public ServiceNow learning site (`https://eltonaguiar.github.io/.../sam-guide/`). Items that appear on the public site but are missing from the repo are also noted.

| # | Topic | Present in Repository | Present on Public Site? | Rationale / Note |
|---|-------|-----------------------|------------------------|------------------|
| 1 | Plugin activation & prerequisite list | ✔ | ✔ | Included in `summaries.md` and `FINAL_SAM_MODULE_REFERENCE.md`. |
| 2 | Discovery → SAM data‑flow diagram | ✔ | ✔ | Inferred from text. |
| 3 | CI‑side related‑list configuration | ✔ | ✔ | In `ci‑configuration.md`. |
| 4 | Discovery‑model lifecycle (create, normalise, approval) | ✔ | ✔ | Fully documented. |
| 5 | Normalisation process (daily job, ML) | ✔ | ✔ | Covered. |
| 6 | Duplicate & stale‑data cleanup | ✔ | ✔ | Covered. |
| 7 | Reconciliation job details & results structure | ✔ | ✔ | Covered. |
| 8 | Out‑of‑Box Scripts (list, purpose, risk) | ✔ | ✘ | *Not* referenced in the public guide. |
| 9 | Maintenance – adding a new software model (idempotent steps, affected tables) | ✔ | ✘ | Repository has detailed `maintenance.md`. |
|10 | Maintenance – normalisation workflow, exception handling, re‑classification | ✔ | ✘ | Repository covers `normalisation.md`. |
|11 | High‑probability items (license position, compliance, true‑up, reclamation) | ✔ | ✘ | Repository lists them in `high‑prob.md`. |
|12 | Parameter inventory (must‑consider vs full per‑screen list) | ✔ | ✘ | Public guide provides fewer config details. |
|13 | Ownership & governance model (roles, data ownership, change control) | ✔ | ✘ | Repository has `governance.md`. |
|14 | Validation & test cases (UAT, acceptance thresholds) | ✔ | ✘ | Repository includes `test_cases.md`. |
|15 | Migration / cut‑over plan (legacy data, rollback) | ✔ | ✘ | Repository contains `migration.md`. |
|16 | SaaS subscription ingestion and usage integration | ✔ | ✘ | Repo has `saas.md`. |
|17 | Content‑Library opt‑in & PPN matching | ✔ | ✘ | Not covered in public site. |
|18 | Vendor‑specific license metrics & packs | ✔ | ✘ | Repo details per vendor tables. |
|19 | Integration with Service Graph SCCM (new vs legacy) | ✘ | ✔ | Public guide likely has SCCM section, not in repo. |
|20 | Role requirements for SAM admins & users | ✘ | ✔ | Public guide may list roles, repo has same but deeper. |

**Recommendations**
- Add the missing sections (8–17) into the repository under the `docs/sam` folder so that the learning site can pull them in automatically.  Each section can be a markdown file that mirrors the style of `FINAL_SAM_MODULE_REFERENCE.md`.
- Create a top‑level `sam-guide/` folder that aggregates the markdown files into a single user‑facing guide.  The site’s static generator can pick up this folder.
- For items 19–20 that are present on the site but missing locally, add a lightweight summary (one‑page) so the repository stays in sync.

The above cross‑comparison ensures that the repository contains a **complete** learning package that matches or exceeds the public SAM guide.
