# New Tools Analysis — scan_boards.py & render_board.py

**Date:** 2026-11-18
**Files:** `/tmp/kit/scan_boards.py`, `/tmp/kit/render_board.py`, `/tmp/kit/employer-watchlist.csv`

## What They Are

A minimal, self-contained ATS job-discovery kit with zero dependencies (stdlib only). Two scripts, one config CSV.

### scan_boards.py
Read-only tool that queries 4 ATS public APIs (Lever, Greenhouse, Ashby, SmartRecruiters) via standard library HTTP. Keyword-filters for ServiceNow/Salesforce/Other patterns in title+description. Outputs JSONL leads with `candidate_tracks` and `status: lead_only`. Designed to be safe by default (`--plan` mode shows endpoints without touching the network; explicit `--read` required to fetch).

### render_board.py
Takes a `job-snapshot.csv` (human-reviewed leads) and builds a static HTML board with filterable cards (track, location, date, channel). No network, no dependencies. Single-batch snapshot renderer — one verification date per run.

### Key Design Decisions
- **No scraping** — only documented public API endpoints for ATS platforms
- **No browser, no accounts** — pure HTTP with stdlib
- **Lead-only output** — says "I found a keyword match, not a verified job"
- **Static HTML rendered locally** — no server needed to view
- **employer-watchlist.csv** as source registry — add a row, get a feed

## Gap vs Existing BESTIEJOB Pipeline

| Capability | scan_boards.py | Existing pipeline |
|------------|---------------|-------------------|
| Sources covered | 4 ATS (Lever, Greenhouse, Ashby, SmartRecruiters) | Same 4 + Workday CXS (16 tenants) + Adzuna + LinkedIn guest + gap channels + agency boards + remote feeds |
| Pagination/Search | Yes (Lever/SmartRecruiters paginated; Greenhouse/Ashby full list) | Same |
| Keyword filter | ServiceNow/Salesforce/Other regex in title+body | Same + secondary tags (VBA, Alteryx, Python, etc.) |
| Deduplication | None (raw output, dedup deferred to human review) | Full URL + fingerprint + cross-source dedup |
| Date handling | Passes through raw `updated_at`/`publishedAt`/`releasedDate` | Extracts, normalizes, cross-checks JSON-LD, stamps provenance |
| Liveness check | None (status: lead_only) | Full liveness gate (404/410/451 drops + verifiedAt stamps) |
| Merger to board | None (expected human review → job-snapshot.csv) | Automated inbox→README merger with row caps |
| CI/quality gates | None | board_invariants.py + README row guards |
| Coverage | 3 companies in watchlist (Alimentiv, EQ Bank) | 2,800+ live listings across 11+ sources |

## Suggested Approach — Hybrid

The cleanest path is **not** a rewrite but a **targeted adoption** of this kit's design philosophy into the existing pipeline:

1. **Adopt `scan_boards.py`'s config-driven ATS registry pattern** — Replace the current hard-coded ATS board lists in `daily_job_scan.mjs` with an `ats-registry.csv` (source_id, adapter, board_token). This lets agents add new ATS sources by appending a CSV row instead of editing JavaScript. The existing scan code becomes a registry reader.

2. **Adopt `render_board.py`'s static HTML approach for the individual agent review board** — Use a lightweight HTML renderer for the `inbox/` review step, so a scanning agent can `--plan` to see endpoints, `--read` to get leads, filter locally, and produce a `job-snapshot.csv` — then `render_board.py` to preview before the merge step. This decouples the scan agent from the full pipeline.

3. **Keep the existing pipeline's strengths** — The liveness gate (`verify_links.py`), the deduplication (URL normalization + title+company fingerprint + requisition ID tying), the CI quality gates (`board_invariants.py`), the date provenance, and the multi-source merger (`jobs_merge_inbox.py`) are all working and hardened. Don't replace them.

4. **Add Workable (`listJobs` POST) and Workday CXS (`searchJobs`) to the kit's SUPPORTED set** — Those are the two missing ATS types from the existing pipeline that the kit doesn't cover.

## File

Written to `updates/2026-11-18-scan_boards-analysis.md`