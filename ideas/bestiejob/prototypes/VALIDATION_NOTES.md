# Prototype validation notes

Generated: 2026-11-18T04:35:50Z

## Fixture outcomes (classifier + normalizer)

| case | geo_bucket | tracks | certs | needs_confirm | exclude | dedupe_key (short) | liveness |
|---|---|---|---|---:|---:|---|---|
| SN_body_only_cert | Toronto | Other,ServiceNow | CSA,CAD | False | False | 6f9b8dd7df4e | listed/None |
| SF_LWC_Apex_French_Canada_remote | Remote (Canada signal) | Salesforce | PD1 | True | False | 59cecffc16d6 | listed/None |
| ITSM_CMDB_ITAM_GTA | GTA (non-Toronto core) | Other,ServiceNow |  | False | False | 1858a339c578 | listed/None |
| Global_remote_confirm | Global remote — confirm Ontario eligibility | ServiceNow |  | True | False | 5d9ae4fe972f | listed/None |
| US_only_exclusion | Other/unknown | Salesforce |  | False | True | 81e3d9c5d35a | listed/None |
| Hybrid_Toronto | Toronto | Other,ServiceNow |  | False | False | b7cde8f153f7 | listed/None |
| Stale_undated | GTA (non-Toronto core) | Other,ServiceNow |  | False | False | 7e764b4281c3 | unknown/None |
| Duplicate_URL_req_a | Remote (Canada signal) | Salesforce |  | True | False | 30a926c03e51 | listed/None |
| Duplicate_URL_req_b | Remote (Canada signal) | Salesforce |  | True | False | 30a926c03e51 | listed/None |
| Agency_undisclosed_client | Remote (Ontario/Canada-eligible signal) | Other,ServiceNow | CIS,CTA | False | False | 45076b20997a | listed/None |
| Dead_link_candidate | GTA (non-Toronto core) | Other,Salesforce |  | False | False | 5f14e107459a | suspect_dead/404 |

## Dedupe check
- records: 11, unique dedupe_key: 10, duplicate groups: 1
- `30a926c03e5160b6…`: ['Salesforce Developer', 'Salesforce Developer']

## Observations
- French remote title/body (`Télétravail - Canada`) classified as Canada-remote with `needs_confirm=true` when Ontario not explicit — correct for verify queue.
- Global-remote flagged `needs_confirm=true`; US-only flagged `exclude_signal=true`.
- Body/cert cues detected (e.g. CSA/CAD/CIS/CTA/PD1) and mixed SN/SF/Other tracks scored where evidence present.
- Normalizer strips tracking params, preserves `posting_raw`, sets `dates.posted_at=null` (must be verified absolute source date before publish), carries `time_value_raw/time_field`, and emits `review.needs_verification=true`.
- Dedupe key prefers `source+posting_id`, then `source+req_id`, then normalized URL, then fingerprint; identical URL+req fixture pair collapsed as expected.

## Gaps / next calibration
- Add stronger FR/EN role phrases and CIS-subtype/ITIL handling; reduce bare-token false positives (e.g. generic platform roles) with context rules.
- Refine geo: distinguish “Canada (province unspecified) remote” vs “Ontario-eligible” with evidence; handle more GTA/locality spellings and bilingual location strings.
- Preserve/derive `hiring_channel`, employer/client, and `access_level` from richer inputs; map to canonical schema used by inbox/merge.
- Add dead-link/HTTP check integration + absolute posted-date extraction/verification stage outputs.
- Expand fixtures with negative cases and real labeled samples; add simple precision/recall harness.
