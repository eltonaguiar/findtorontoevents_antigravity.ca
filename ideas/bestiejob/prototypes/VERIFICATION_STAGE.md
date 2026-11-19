# Verification stage design (prototype)

Lead records (`classification.status=lead_only`, `review.needs_verification=true`) **must not** be published. Verification promotes leads to review/publishable states with evidence.

## Pipeline position
`scan_boards.py` → `normalize_lead.py` + `job_signal_matcher.py` → **verify** → dedupe/review queue → inbox merge/build (single writer `bestiejob-main-write`).

## Gates and outputs

| Gate | Inputs | Output fields (suggested) | Pass/hold rules |
|---|---|---|---|
| Identity/issuer | posting/apply URLs, source adapter ids, page/issuer evidence | `identity.posting_id/req_id`, `source.provenance`, `urls.corroborating[]` | Hold if issuer/tenant cannot be confirmed from official source. |
| Liveness/access | HTTP status, final URL, listing presence, page markers | `liveness.state` (`live/removed/closed/blocked/unknown`), `http_status`, `access_level` (`listed/apply_shown/form_reached/gated_route/needs_review`) | 404/410/451 or removed-from-official-list => dead/removed (with evidence). 401/403/429/5xx/timeouts => `blocked/unknown` (never mark closed by failure). |
| Date | issuer date fields/text, checked time | `dates.posted_at` (absolute ISO8601) or null+reason, `time_field`, `time_value_raw`, `date_evidence` | Require source-backed absolute date for fresh/publish windows; never infer from relative age. Conflicts => null with evidence. |
| Geo/eligibility | location/mode/body evidence, classifier `eligible` | `location.geo_*`, `eligible.*`, evidence | Toronto/GTA local or Canada/Ontario-remote eligible vs global-confirm vs excluded; unresolved => review/confirm. |
| Duty/track fit | title + body duties, certs | `classification.tracks/certs/evidence`, confidence/review flag | Substantive platform/build duty required for SN/SF; generic CRM-use-only => reject/downscope. |
| Rights/reuse | source policy, terms/attribution | `rights.reuse`, attribution notes | `unknown` => do not redistribute/public-publish. |
| Dedupe readiness | normalized URL/ids/title-company-location fingerprint | `identity.dedupe_key`, duplicate candidates | Merge only on strong identity; title+city alone => review. |

## Runnable stub (interface contract)
Prototype stub should accept normalized JSONL and emit verification-enriched JSONL without network by default:
- **Input:** `*.normalized.jsonl`
- **Checks (offline mode):** field completeness, date parseability/absoluteness, URL scheme validity, classifier-derived eligibility/confirm/exclude flags, stale/undated flagging, dedupe-key presence.
- **Checks (online mode, future, permissioned):** bounded HEAD/GET per allowed host, redirect/final-URL capture, status classification, optional content markers; respect rate limits/robots/terms and stop on denial.
- **Output:** per-record `verification` object `{status: pass|review|reject, reasons[], checked_at, gates{...}}` plus updated `liveness/dates/review` fields; never fabricate `posted_at`.

## Decision states
- **pass (reviewable/publishable if rights+merge rules satisfied):** core gates satisfied with evidence.
- **review:** ambiguous geo/eligibility, missing/ambiguous date, access-gated, weak duty evidence, possible duplicate.
- **reject:** out-of-scope/excluded, confirmed closed/removed/dead-link per policy, rights prohibit, non-job/insufficient evidence.

## Metrics to emit
counts by source/adapter: scanned leads, normalized, verified-pass, review, reject, dead, unknown/blocked, deduped, promoted; reasons breakdown; latency and recheck age.

## Safety
- No credentials, no form submissions, no bypassing access controls.
- Preserve raw evidence pointers; append-only observations when persisted.
- Failed fetch ≠ closure; keep prior known state unless contradicted by authoritative evidence.
