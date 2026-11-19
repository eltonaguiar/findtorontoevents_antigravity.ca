# Adapter coverage plan (beyond Lever/GH/Ashby/SmartRecruiters)

**Context:** `scan_boards.py` currently supports 4 documented ATS list APIs with keyword lead extraction. Goal: broaden high-yield, permissioned discovery while preserving verify-first, rights-aware ingestion.

## Priority batches (yield/risk-informed)

| Batch | Targets | Adapter/approach | Notes/risks |
|---|---|---|---|
| 1. Direct ATS/company portals (highest) | Workday CXS (tenant-specific), existing GH/Lever/Ashby/SR coverage expansion via `employer-watchlist.csv`, BambooHR/TalentNet/ADP/SuccessFactors where permitted | Documented/public JSON endpoints or employer-approved feeds; Workday `POST` search per tenant config (bounded) | Tenants vary; auth/CSRF/site changes common. Store tenant+site config as verified source records. |
| 2. Toronto/GTA + Canada-remote geo sources | Toronto/Mississauga/Markham/Brampton/Vaughan/Oakville/Burlington civic/crown portals; Canada-wide remote company boards | Per-site adapters or structured scrapes only where terms allow; prefer official feeds/search endpoints | Normalize locality/remote eligibility carefully; avoid generic aggregators-as-employer. |
| 3. Canadian gov/boards | Job Bank alerts/exports (where permitted), provincial/municipal boards, university/health networks | Manual-discovery or permitted ingestion paths; capture evidence and rights | Posting semantics/dates vary; dedupe across mirrors. |
| 4. Ecosystem leads (employer discovery, not vacancies) | SN/SF partners, ISVs, conference sponsors/attendees (rosters `<uncertain>` until verified) | Feed into watchlist/source research, not direct job ingest | Sponsorship != hiring; resolve to official careers/ATS before lead creation. |

## Normalized adapter contract (proposed)
Each adapter implements (conceptually):
- `plan(config) -> endpoints/notes` (no network)
- `scan(config, limits) -> lead records` with: `source_id, adapter, posting_id/req_id, title, posting_url, apply_url?, location_as_listed, mode/workplace, description/body?, time_field, time_value_raw, observed_at_utc, status=lead_only, provenance`
- Bounded: pages/details/timeouts/delay, 20MB-ish cap, no redirects to arbitrary hosts, stop on 401/403/429 with `Retry-After` awareness
- Idempotent/cached by `(source_id, posting_id)` and conditional requests where supported

## Integration path
1. Adapter emits leads → `normalize_lead.py` + `job_signal_matcher.py`
2. Verify stage (date/liveness/geo/duty/rights) → dedupe → review queue
3. Only verified/cleared rows to inbox merge/build
4. Per-source metrics: coverage, leads, verified, rejected reasons, failures/blocked, freshness lag

## Immediate next actions
- Inventory which high-yield SN/SF employers use Workday CXS; define tenant config schema and a read-only `--plan` probe.
- Expand `employer-watchlist.csv` (permission-checked) for Toronto/GTA/Canada-remote-relevant tenants on supported ATS types.
- Add adapter interface doc + stub module layout (no live scraping) to ease future implementation.
