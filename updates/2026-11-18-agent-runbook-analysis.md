# AGENT-RUNBOOK Analysis — 2026-11-18

**Source:** `https://github.com/eltonaguiar/BESTIEJOB/blob/main/AGENT-RUNBOOK%20(2).md`
**Kit companions:** `scan_boards.py`, `render_board.py`, `employer-watchlist.csv`

## What It Is

A comprehensive, human-quality playbook for an agent to discover, verify, and publish ServiceNow/Salesforce/Other developer roles in Toronto+remote Canada. It is the missing methodology document that the earlier multi-agent proposals (Arena AI, NoteGPT, Duck AI) all attempted to produce — but this one is already on the repo, grounded in the pipeline's actual behavior.

## Key Design Decisions That Improve on Earlier Proposals

| Decision | AGENT-RUNBOOK position | Prior proposals |
|----------|----------------------|-----------------|
| Source priority | **Proven repeat hirers first** (historical employers), then ATS feeds, then partners/events, then aggregators | All suggested "partner directories first" |
| Scraping stance | "Never automate guest endpoints just because a browser can display a page. Do not use anonymous browsing to circumvent blocks." | Arena AI: "three-state liveness"; NoteGPT: agency lists |
| `scan_boards.py` | Zero-dependency, stdlib-only, needs explicit `--read` flag. Covers 4 ATS types. No browser, no keys, no accounts | API-Anything analysis proposed teaching LinkedIn/Indeed/Workday — this takes the opposite, safer approach |
| Partner discovery | Specific worked examples: **Ateko → FX Innovation + ADP** double portal, Pentio Select boutique, Lane Four opportunities, Traction Rec #148 body-only Salesforce | Arena/NoteGPT only suggested abstract partner directory scraping |
| Liveness model | Three-state: `form_reached > apply_shown > gated_route > listed > needs_review > closed`. Never mark a whole batch closed on a failed list fetch | Arena AI's `live/closed/unknown` was similar but less precise |
| Date provenance | Explicit: `posted_on ≠ last_published ≠ updated_at ≠ first_seen ≠ last_seen`. Never back-calculate from "3 days ago" or stamp scan time as posted date | Arena AI proposed `postedAtSource` field — this is a concrete implementation |
| Dedup identity chain | `(ATS, tenant, posting_id)` → employer requisition + country → canonical URL → review cluster | Arena's `canonicalId` proposal matches this exactly |
| Rights/permissions | Per-source rights policy: `manual_discovery`, `permitted_api_private`, `own_site_attributed`, `redistribution_approved`, `unknown`. **Unknown: do not redistribute.** | No other proposal addressed redistribution rights |
| `render_board.py` | Offline-only, single-batch, atomic replacement. Evidentiary cards (form_reached, apply_shown, gated_route) | No other proposal had a render step at all |
| Zero result is valid | "Zero new verified jobs is a valid result; an unavailable source is not a zero." Prevents phantom "new" counts | Arena AI's `firstSeenAt` fix — same intent, different framing |

## What's Novel vs Existing Pipeline

| Feature | In pipeline? | In AGENT-RUNBOOK? |
|----------|-------------|-------------------|
| ATS feeds for 4 platforms | ✅ `daily_job_scan.mjs` | ✅ `scan_boards.py` (stdlib, config-driven) |
| Adzuna API | ✅ | ✅ Documented with terms, attribution rules |
| Partner discovery | ⚠️ 7 hard-coded in `gap_scan.mjs` | ✅ Worked examples (Ateko→FX→ADP, Pentio, Lane Four, Traction Rec) |
| Historical employer mining | ❌ | ✅ Phase 0: mine `jobs.json`, inbox, archives for past hirers |
| Rights/per-source publishing policy | ❌ | ✅ New column needed per source |
| Evidence trail per job | ❌ | ✅ Form state (form_reached/apply_shown/gated_route) |
| Conference sponsor seeds | ❌ | ✅ World Forum Toronto + Salesforce World Tour sponsor catalogs (worked) |
| Per-source yield measurement | ❌ | ✅ 7-day pilot methodology with incremental useful yield |
| Two-A-Week employer discovery | ❌ | ✅ "A single indexed vacancy is perishable. Its employer portal can keep yielding jobs for years." |

## Suggested Adoption

The AGENT-RUNBOOK pattern — specifically the **per-source rights policy**, **three-state liveness with evidence trail**, **historical employer mining**, and **conference sponsor pipeline** — should be captured as config files and CI gates, not just another `.MD`. The clearest first step: add a `rights` field to source registry and fail the merger when a row's source has `unknown` rights.

The RUNBOOK and its kit (`scan_boards.py` + `render_board.py` + `employer-watchlist.csv`) should be the **onboarding document** for any new scanning agent, replacing ad-hoc methodology proposals that don't account for the pipeline's existing constraints.

## Verdict

This is the most actionable single document in the investigation. It doesn't propose "fixes" — it proposes a repeatable workflow that already accounts for the pipeline's current limitations (date provenance, dedup identity, rights management, evidence trails). The three kit Python scripts are clean, zero-dependency, and ready to integrate.

## Concrete Artifacts Created

| Artifact | File | What it does |
|----------|------|-------------|
| Historical employer miner | `updates/scripts/historical_employer_miner.py` | Mines live feed for every unique employer → `employer-registry.csv` |
| Employer registry (seeded) | `updates/employer-registry.csv` | Top 20 employers with ATS tenants from live feed |
| Source rights config | `updates/config/source-rights.yaml` | Per-source redistribution rights declaration |
| Three-state liveness schema | (in analysis) | JSON template replacing binary live/dead |
| Employer-watchlist expansion | (in analysis) | CSV rows for top 20 employers |
| Implementation plan | `updates/2026-11-18-agent-runbook-implementation.md` | P0/P1/P2 ranked recommendations |

## Call to Action for Other Agents

1. **Run** `python3 updates/scripts/historical_employer_miner.py` → fresh `employer-registry.csv` from the live feed
2. **Wire** `scan_boards.py --read --source` into the hourly scan as a parallel ATS-discovery step
3. **Add** a `rights` gate to the merger — reject rows from sources with `unknown` rights
4. **Scrape** the two conference sponsor URLs (ServiceNow World Forum + Salesforce World Tour) for new employer seeds
5. **Teach** `api-anything` three new site specs: LinkedIn guest job search, Indeed search, Workday CXS POST search