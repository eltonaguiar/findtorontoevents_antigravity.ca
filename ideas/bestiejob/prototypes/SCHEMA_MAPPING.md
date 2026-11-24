# Normalized schema mapping (draft)

**Status:** prototype alignment (2026-11-18). Reconciles `scan_boards.py` leads, `render_board.py`/snapshot fields, LLM-delegated schema drafts (`llm-delegated/03-normalized-schema-hermes.md`, `04-normalized-schema.md`), and `normalize_lead.py` (`bestiejob.normalized_lead_draft.v0`).

**Goal:** one canonical, evidence-preserving record for `scan -> verify -> dedupe -> inbox merge -> publish` under BESTIEJOB single-writer flow.

## 1. Draft shape (`bestiejob.normalized_lead_draft.v0`)

| Section | Field | Purpose | Notes |
|---|---|---|---|
| identity | dedupe_key | Stable dedupe identity | SHA-256 of preferred key: `source+posting_id` → `source+req_id` → normalized posting URL → fingerprint(title/company/location). |
| identity | source_id, posting_id, req_id | Source identity/traceability | Keep both posting and requisition IDs when present. |
| source | adapter, publisher, observed_at_utc | Provenance | Adapter/ATS name, emitting org/board, observation time. |
| source | provenance | Input lineage | e.g. `scan_boards_lead_or_snapshot`. |
| urls | posting, posting_raw, apply, corroborating[] | Navigation/evidence | `posting` normalized (tracking stripped); `posting_raw` preserved; corroborating/issuer links kept. |
| company | name, client, hiring_channel | Employer attribution | Distinguish agency/publisher vs end-client when known. |
| title | title | Raw role title | Never rename to force category match. |
| location | raw, mode_as_listed, geo_bucket, eligible{} | Geo/remote/eligibility | `eligible`: toronto_gta_local, canada_remote_signal, ontario_eligible_signal, needs_confirm, exclude_signal, hybrid_or_onsite. |
| dates | posted_at, time_field, time_value_raw, closes_on, valid_through | Time evidence | **`posted_at` null until verified absolute source date**; preserve source field/value semantics. |
| content | description, snippet | Match/verify evidence | Snippet derived; keep body text for verification where rights allow. |
| classification | tracks[], certs[], track_scores{}, evidence[], status | Relevance signals | Pre-verify hints only (`lead_only`); evidence strings explain matches. |
| liveness | state, http_status, access_level | Freshness/access | `unknown/listed/suspect_dead/...` + checked status; separate from geo eligibility. |
| rights | reuse | Redistribution posture | `unknown/manual/permitted/approved` etc. per policy. |
| review | needs_verification, notes[] | Gatekeeping | Default true; promote only after verify gates pass. |

## 2. Source mapping

### From `scan_boards.py` lead (JSONL)
| Lead field | Draft field(s) | Note |
|---|---|---|
| source | identity.source_id, dedupe basis | Board/source token id. |
| publisher | source.publisher, company.name | Issuer/org label. |
| ats | source.adapter | lever/greenhouse/ashby/smartrecruiters. |
| posting_id | identity.posting_id, dedupe basis | ATS posting id. |
| title | title | |
| posting_url | urls.posting/posting_raw | Normalized + raw kept. |
| apply_url | urls.apply | |
| location_as_listed | location.raw | |
| mode_as_listed | location.mode_as_listed | |
| time_field | dates.time_field | GH `updated_at` != posted; Ashby `publishedAt` = last published. |
| time_value | dates.time_value_raw | Not auto-promoted to posted_at. |
| candidate_tracks | classification.tracks (fallback) | Merged with classifier scores. |
| status (`lead_only`) | classification.status | |
| observed_at_utc | source.observed_at_utc | |

### From `render_board.py` / `job-snapshot.csv` (evidence snapshot)
| Snapshot field | Draft field(s) | Note |
|---|---|---|
| publisher, posting_id | identity/source/company | Unique within issuer in snapshot. |
| posting_url, apply_entry_url, corroborating_url | urls.posting/apply/corroborating | |
| title, employer_or_client, hiring_channel | title, company.* | Preserve attribution. |
| location_summary, geo_bucket, geo_evidence | location.raw/geo_bucket, review.notes or evidence ext. | Snapshot buckets align with render groups. |
| work/terms/pay/access fields | (extend) | Keep in extended snapshot schema; not all required for lead normalize. |
| posted_on, closes_on, valid_through, date_evidence, checked_local_date | dates.*, source/provenance | Absolute dates usable after verification; single-batch checked date in snapshot. |
| open_evidence, access_level | liveness.access_level/state hints | |
| developer_evidence/candidate_note | content/classification evidence | |

### To BESTIEJOB inbox/merge (target alignment — verified against live `main` scripts/tools, 2026-11-18)
- Produce **verified, rights-cleared** rows only; leads stay out of publish path.
- Required for fresh/publish flows: canonical posting URL, issuer/company, title, location/eligibility evidence, **absolute posted_at (source-backed)**, liveness state, dedupe identity (posting/req/URL), track classification with evidence, rights/provenance.
- **Inbox file naming (`scripts/check_inbox.py`, `tools/jobs_merge_inbox.py`):** `<model-slug>--<YYYY-MM-DD>--v<N>.md` (ignored: `_*/TEMPLATE*/README*`). Version increments for resubmits; merger leaves inbox as-is unless `--bump-inbox` (CI).
- **Row format:** `| Posted | Role | Company | Location | URL | (note optional) |` — dated rows require absolute `YYYY-MM-DD` and an `http(s)` URL; undated markers (`— - ? n/a unknown tbd empty`) allowed by checker but skipped by merge. Min 5 cells.
- **Merger ingest filters (`jobs_merge_inbox.py`):** drops duplicates vs README/APPLIED URLs (normalized), listing pages, **signup-gated/paywall domains** (`tools/job_source_truth.domain_is_gated`), sales/marketing function titles (EXCL regex), rows with leaked links in cells, placeholder company/title cells, and non-Canadian locations (`locscope.is_foreign`). Default mode is **additive insert** (no row removal/cap); `--rebuild` is legacy/destructive (opt-in). Refuses write on unreadable/glued rows (`--allow-row-loss` override exists but unsafe).
- **Dedupe/classification:** URL normalization consistent with `jobs_consolidate.normalise_url`; family via `jobs_consolidate.classify(title,url)` (`servicenow`/`salesforce`/`other`). Prototype `dedupe_key`/`tracks` must be mapped to these semantics before merge.
- **Operational:** single-writer `bestiejob-main-write`; run `check_inbox.py`, `jobs_merge_inbox.py --dry-run` (inspect full diff), then authorized merge/build/sync steps; monitor truth-check/link/board-invariants gates. Reconfirm conventions in `docs/JOB_SUBMISSION_METHODOLOGY.md` on live `main` before staging.

## 3. Gaps vs current draft (to close)
- **Canonical field names:** align keys with live BESTIEJOB feed/inbox schema (naming/requiredness).
- **Employer vs agency/client split:** richer fields and evidence (redacted-client handling).
- **Evidence model:** structured evidence records (field, value, source, quote/snippet ref) beyond `classification.evidence[]`.
- **Access/rights enums:** standardize (`form_reached/apply_shown/gated/listed/...`, reuse policy states).
- **Liveness semantics:** separate HTTP state, listing presence, closure/deadline, and access gate outcomes.
- **Geo parsing:** structured city/region/country/latlon optional; bilingual strings; “Ontario-eligible but province unspecified” review state.
- **Date parsing/verification:** normalize absolute dates with timezone/source; never infer from relative text.
- **Multi-source edges:** `source_edges[]` for merged/seen-across sources with per-source provenance.

## 4. Dedupe identity (current prototype behavior)
1. `ats:{source_id}:posting:{posting_id}`
2. `ats:{source_id}:req:{req_id}`
3. `url:{normalized_posting_url}` (lowercased host/scheme, trimmed slash/fragment, tracking params stripped)
4. `fp:{title|company|location}` slug fingerprint

**Known limits:** same job across tenants/boards, locale aliases, tracking/identity params edge cases, and agency-repost ambiguity require verify/review (never auto-merge on title+city alone).

## 5. Integration contract (recommended)
- **Lead stage:** `scan_boards` → `normalize_lead` (+ `job_signal_matcher`) → `lead_only`, `needs_verification=true`.
- **Verify stage:** produce verification result (posted_at absolute or null-with-reason, liveness/access, geo/eligibility evidence, rights) → eligible for dedupe/review.
- **Publish stage:** only verified, rights-cleared, deduped records enter inbox/merge/build; emit metrics and rejection reasons.
