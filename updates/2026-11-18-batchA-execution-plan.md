# Batch A (company portals) — execution plan

**Owner:** kilo · seat `inbox/gx10-c9b9/bestiejobharvest-v2/kilo` · 2026-11-18
**Inputs:** `AGENT-RUNBOOK (2).md` (reviewed), kit `scan_boards.py` + `render_board.py`, watchlist `updates/2026-11-18-batchA-employer-watchlist.csv`.
**Principle:** employer/ATS-first, offline-by-default, rights-gated. No guest-endpoint scraping, no auto-apply, no credentials, no PII, no republication of restricted text.

## Why Batch A first
Highest signal + lowest duplication + the board's acknowledged coverage gap (employer ATS was ~31 Workday rows vs ~55% LinkedIn+Adzuna on 2026-11-11). The kit already implements it for four documented ATS APIs.

## Verified tokens (probed live 2026-11-18, read-only)
| source_id | adapter | postings | platform-titles |
|---|---|---|---|
| eqbank | lever | 79 | 1 |
| versapay | lever | 30 | 2 (corrected: Lever, not Greenhouse) |
| levio | greenhouse | 56 | 5 |
| solink | ashby | 24 | 0 (board live, no current SN/SF) |
| servicenow | smartrecruiters | live | — (a job AT ServiceNow ≠ a build role) |

Resolve-required (adapter/token TBD — resolve via the official careers link, never assume brand = slug): alimentiv, ensiti, lanefour, tractionrec (BambooHR — not kit-supported), ateko (FX Innovation + ADP — not kit-supported), pentio, glidefast, rapdev, newrocket, crossfuze, cea.

## Run loop (per small employer batch)
1. **Offline plan (no reads):** `python3 scan_boards.py --plan --source eqbank versapay levio solink servicenow` — inspect exactly which public list endpoints would be read.
2. **Rights gate:** confirm each source's `rights` (own_site_attributed / permitted_api_private). `unknown` → do **not** read or publish. Adzuna/LinkedIn/Indeed guest routes stay out of Batch A (see governance note).
3. **Read (only permitted sources):** `python3 scan_boards.py --read --source eqbank versapay --out leads-<date>.jsonl` (bounded `--max-pages`/`--max-details`/`--delay`; honor `Retry-After`; stop host on 401/403/429). Output is `status=lead_only` — candidates, not verified jobs.
4. **Verify each lead (runbook §3):** resolve issuer → confirm it exists now (`form_reached`/`apply_shown`/`gated_route`/`listed`/`needs_review`/`closed`) → read duties for a platform **and a build action** → read work mode + eligibility → verify dates/pay against the literal source clock (never back-calc "3 days ago"; `updated_at` ≠ posted; `publishedAt` = last published) → closure decision.
5. **Dedupe (identity order):** `(ATS, tenant, posting_id)` → verified employer req + country → normalized canonical URL (strip tracking, keep `jobId`) → *review* similar title+company+area. Same title+city is **not** sufficient to merge.
6. **Stage rights-cleared rows into BestieJob** via the existing path: one file per agent per day `inbox/<agent>--YYYY-MM-DD--vN.md`, `Posted|Role|Company|Location|URL|Note`; `python3 scripts/check_inbox.py --file ...` then `python3 tools/jobs_merge_inbox.py --dry-run` (inspect whole diff) → additive merge → `sync_readme_to_jobs.mjs` + `build_site.py` + `board_invariants.py`. Single `bestiejob-main-write` writer; no push/deploy without authorization. Keep rich evidence in a **private sidecar** (merger's 6th-cell Note is not reliably carried).

## Workday tenants → existing pipeline, not the kit
`scan_boards.py` supports only lever/greenhouse/ashby/smartrecruiters. Route the big-5/consulting Workday tenants (salesforce, rbc, bmo, cibc, scotiabank, manulife, sunlife, telus, rogers, bell, opg, metrolinx, hydroone, cgi, ibm, deloitte, kpmgca, ey, cdw, cognizant, techmahindra, fujitsu, bdo, unisys, dxc, avanade, opentext) through `gap_channels_scan.py` (Workday CXS) with the same verify/dedupe/rights gates.

## Cadence (runbook §1)
Daily for proven repeat hirers + contract channels near deadline; weekly for local partners/ISVs/former hirers; monthly or after an event for directories/sponsor orgs. Promote a source when it yields verified roles; rotate sources that don't.

## Measure before scaling (runbook §5)
7-day pilot across the four angles; equal request/time budgets; same dev definition, location rules, date window, canonical verifier. Report **incremental unique yield**, **verification quality** (verified÷reviewed, with false-remote/dead/wrong-track/dup/blocked split), **issuer→discovery freshness lag** (+48h, day 7), and **cost per verified job** — and **exclusive vs shared** finds so the first adapter doesn't take all the credit. Rank the angles on this evidence.

## Governance note (highest priority)
A public board is **redistribution**. The live BESTIEJOB automation uses the LinkedIn guest API + Adzuna, which the runbook flags (LinkedIn bars scraping; Adzuna needs attribution + a licence for commercial/redistribution use). Add a `rights` field to the inbox schema and gate publishing on it (`unknown`/restricted → hold). Batch A's four documented ATS APIs are the clean path; keep aggregators for private discovery only until rights are cleared.

## Immediate next actions
1. Commit `employer-watchlist.csv` + `job-snapshot.csv` into the BESTIEJOB kit (currently 404 on main/pinned rev) and pin the kit to a revision.
2. Resolve the 11 `resolve_employer` tenants via official careers links; promote to verified with adapter+token.
3. Dry-run `scan_boards.py --plan` on the verified five; then a permitted `--read` on 2–3.
4. Add the `rights` column to the inbox row schema + merger gate.
