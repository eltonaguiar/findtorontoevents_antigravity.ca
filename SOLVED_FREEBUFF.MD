# SG-AWS EC2 partial imports (`MISSING_DEPENDENCY`) — root cause

**Instance:** `dev296154.service-now.com`
**Scope:** read-only investigation. **Nothing was created, changed, run or reprocessed.**
**Connector:** Service Graph Connector for AWS. EC2 feed `SG-AWS-EC2` → robust transformer `SG-AWS-EC2-Instance` (`sys_robust_import_set_transformer` `a4c8995253203010a3e4ddeeff7b1221`) → RTE definition `64c8995253203010a3e4ddeeff7b121e`.
**Affected:** NIC `eni-04843cac6d5784192`, volume `vol-0d78f1f1bebee052f`, VM `i-0c9860cc1569c41a4` (`sgclab-app-01`), account `639051062568`, region `us-east-2`, connection alias `c3f0b8c453b32010c23bddeeff7b12ee`.

---

## TL;DR

The EC2 mapping is **not broken**. For `cmdb_ci_nic` and `cmdb_ci_storage_volume` it is **reference-only by design** — it carries a `source_native_key` and nothing else, because those CIs are supposed to be created by two sibling imports (`SG-AWS-Network-Interface`, `SG-AWS-Storage-Volume`).

Both prerequisites **exist and are active**, but:

* they are `run_type=parent` children of **`SG-AWS-Organization`, which is inactive** — so they never run on a schedule, and a manual `SG-AWS-EC2` run executes only EC2;
* **`SG-AWS-Network-Interface` has run exactly once and loaded 0 rows** (`CEX0001013`, 2026-11-07 07:00:31), so it created nothing — `cmdb_ci_nic` is empty;
* **`SG-AWS-Storage-Volume` has never executed at all** — no execution record, no import set, 0 rows in its import set table.

With no pre-existing NIC/volume CI carrying the matching `source_native_key`, IRE cannot resolve the dependents and emits `MISSING_DEPENDENCY` — 2 CI items + 3 relationships per EC2 run, blocking 6 entries per execution (`ire_partial=6`).

The remaining unknown is narrow and separate: **why the single NIC import run returned 0 rows** (it completed with `errors=0`, so AWS/the load layer returned nothing rather than erroring).

---

## Final findings

1. **All three imports are configured, active, and ordered.**
   | Import | `sys_id` | active | run_type | parent | order |
   |---|---|---|---|---|---|
   | `SG-AWS-Organization` | `4bf63f53eb2c7010a24882ea7c5228f6` | **false** | daily | — | — |
   | `SG-AWS-Network-Interface` | `e2f9b7d3eb2c7010a24882ea7c5228e9` | true | parent | Organization | **140** |
   | `SG-AWS-Storage-Volume` | `e6fbff17eb2c7010a24882ea7c522835` | true | parent | Organization | **160** |
   | `SG-AWS-EC2` | `cd2b7317eb2c7010a24882ea7c5228ad` | true | parent | Organization | **180** |

   Ordering is the design: NIC → Volume → EC2. EC2 relies on the two higher-priority children having already produced the CIs.

2. **The EC2 mapping is reference-only for exactly these two classes.** RTE entities in definition `64c89952…`:
   * `Cloud Mgmt Network Interface 1` (`bee959d253203010a3e4ddeeff7b1243`) → fields: `source_native_key`, `cmdb_ci`
   * `Cloud Mgmt Network Interface 2` (`f17c51a85386011051f9ddeeff7b1215`) → field: `source_native_key` only
   * `Storage Volume 1` (`c49988af4362511070a4bc54aab8f278`) → field: `source_native_key` only

   No `object_id`, no `public_ip`, no `name`, no `size`. `cmdb_ci` on NIC 1 is a hard reference (no source field) to entity `Virtual Machine Instance 1` (`eea955d253203010a3e4ddeeff7b12f2`). So the **blank Object ID / Public IP mappings are correct for this feed** — there is no attribute mapping to fill them.

3. **The prerequisite mappings *are* authoritative.** In the NIC import's definition `57a3928253203010a3e4ddeeff7b123f`, `cmdb_ci_nic` entities carry `object_id`, `name`, `private_ip`, `public_ip`, `private_dns`, `public_dns`, `ip_address`, `state`, `install_status`, `operational_status`. In the volume import's definition `9936cf0253603010a3e4ddeeff7b12c4`, `Storage Volume 1` carries `object_id`, `volume_id`, `size`, `size_bytes`, `storage_type`, `name`, `state`, … — exactly the attributes the EC2 stub omits.

4. **Both CI identifiers are `Dependent`** — `cmdb_identifier` for `cmdb_ci_nic` and for `cmdb_ci_storage_volume` all return `independent=false`. A dependent identifier cannot mint a CI from the stub payload alone; it needs the parent/anchor plus identifier attributes, or an existing record.

5. **`source_native_key` formats match across feeds.** Both the EC2 stub and the NIC import's authoritative entity map `source_native_key` from the same source field **`nicSourceNativeKey`**. §5 collision risk is therefore low: once the prerequisite import actually loads rows, the EC2 references should resolve.

6. **Run history (authoritative, `sn_cmdb_int_util_cmdb_integration_execution`):**
   ```
   NIC     CEX0001013  2026-11-07 07:00:31  complete  rows=0  inserts=0  ire_*=0  errors=0
   VOLUME  (no execution record at all)
   EC2     CEX0001019  2026-11-07 07:10:47  complete  rows=1  inserts=23 ire_inserted=23 ire_partial=6
   EC2     CEX0001022  2026-11-07 07:16:36  complete  rows=1  ire_updated=1  ire_unchanged=41 ire_partial=6
   EC2     CEX0001029  2026-11-08 02:42:24  complete  rows=1  ire_updated=1  ire_unchanged=29 ire_partial=6
   EC2     CEX0001026/31 2026-11-08 02:50:32 / 02:51  complete  rows=1  ire_updated=2 ire_unchanged=28 ire_partial=6
   ```
   Note: `CEX0001019` shows `rows=1` and `ire_inserted=23` because a Service Graph row is a whole JSON page, not one record.

7. **Data actually loaded:**
   * `sn_aws_integ_sg_aws_ec2` → **5 rows**, every one containing `eni-04843cac6d5784192` and `vol-0d78f1f1bebee052f`. EC2 really does see both resources.
   * `sn_aws_integ_sg_aws_network_interface` → **0 rows** (its two import sets `ISET0010025` / `ISET0010026` are `processed` but empty).
   * `sn_aws_integ_sg_aws_storage_volume` → **0 rows**, and `sys_import_set` has **0** records for that scheduled import.

8. **Target CI state:**
   * `cmdb_ci_nic` → **0 records**.
   * `cmdb_ci_storage_volume` → 7 records, all `discovery_source=ServiceNow`, names like `C`, `D`, `E`, `/dev/nvme0n1p1`, **all `object_id` blank** — Mid Server disk discovery, unrelated to AWS. No AWS volume exists.

9. **`sys_object_source` proves the split.** Rows exist only for the CIs that were successfully created:
   ```
   …|VNICEndpoint|i-0c9860cc1569c41a4|eni-04843cac6d5784192
   …|StorageMapping|i-0c9860cc1569c41a4|vol-0d78f1f1bebee052f
   …|BlockEndpoint|i-0c9860cc1569c41a4|vol-0d78f1f1bebee052f
   ```
   There is **no** `…|639051062568|us-east-2|eni-04843cac6d5784192` and **no** plain volume key — the keys the EC2 stubs carry. The suites the payload did resolve (`cmdb_ci_endpoint_vnic`, `cmdb_ci_storage_mapping`, `cmdb_ci_endpoint_block`) are exactly the entities that carry real attributes.

10. **Stored partial payload (canonical case, TH0001036 → CISET0010013 → ISET0010039, `2026-11-08 02:51:41`):** 4 items —
    * `cmdb_ci_vm_instance` ✔ (values: `discovery_source`; key `…|639051062568|us-east-2|i-0c9860cc1569c41a4`)
    * `cmdb_ci_endpoint_vnic` ✔ (key `…|VNICEndpoint|…|eni-…`)
    * `cmdb_ci_nic` ✘ `reason: MISSING_DEPENDENCY`, values `{discovery_source: SG-AWS}` only, key `…|639051062568|us-east-2|eni-04843cac6d5784192`
    * `cmdb_ci_storage_volume` ✘ `reason: MISSING_DEPENDENCY`, values `{discovery_source: SG-AWS}` only, key `…|639051062568|us-east-2|vol-0d78f1f1bebee052f`

    plus 3 blocked relationships (`Use End Point To::Use End Point From` ×2, `Contains::Contained by`) and one `referenceItems` entry: `cmdb_ci` on the NIC → `d37c82afa31c97d0783487146f898f3d`.

---

## Breadcrumbs (what was queried, abbreviated)

Authentication: HTTP Basic (`admin`) against `/api/now/table/*`, GET only. Verified with a raw probe — see Proof §A.

| Purpose | Table(s) |
|---|---|
| Scheduled imports | `scheduled_import_set` (alias view `scheduled_data_import`) |
| Connector executions | `sn_cmdb_int_util_cmdb_integration_execution` (`CEX…`) |
| Import sets / transform history | `sys_import_set` (`ISET…`), `sys_import_set_run` (`TH…`), `sys_concurrent_import_set` (`CISET…`) |
| ETL mapping | `sys_robust_import_set_transformer` → `robust_transform_engine` → `sys_rte_definition` → `sys_rte_eb_entity` / `sys_rte_eb_field` / `sys_rte_eb_field_mapping` |
| Partial payloads | `cmdb_ire_partial_payloads` (field `payload_item`) |
| Object source keys | `sys_object_source` (field `id` = `source_native_key`) |
| Identifiers | `cmdb_identifier` (`table=cmdb_ci_nic` / `cmdb_ci_storage_volume`) |
| Data sources | `sys_data_source` (`import_set_table_name`) |

Gotcha worth recording: **the REST API silently drops query clauses that name a non-existent column.** Filtering `sys_rte_eb_field_mapping` by `sys_rte_eb_field` (correct column: `target_sys_rte_eb_field`) and `sys_import_set_row`/`sys_properties` by guessed columns produced full-table counts (e.g. a bogus `62424`) instead of an error. Always compare a filtered count against the unfiltered count before trusting it.

---

## Proof

### A. The client is genuinely authenticated (not a login redirect, not a silent denial)

```
A. NO auth header (negative control)
   status 401 Unauthorized | Content-Type application/json;charset=UTF-8
   Location: None | body: {"error":{"message":"User is not authenticated", ...},"status":"failure"}
B. Basic auth (admin)
   status 200 OK | Content-Type application/json;charset=UTF-8
   Location: None | X-Total-Count: 151 | Server: snow_adc
   body: {"result":[{"name":"SGO-Dynatrace Azure Scale Sets VM","active":"true","run_type":"parent"}]}
C. authenticated query with no matches -> 200 application/json, body {"result":[]}
D. wrong/ACL-blocked table -> 400 {"error":{"message":"Invalid table sys_object_source_info"}}
```
So: 401 = auth failure (JSON, no HTML), 200 + `result: []` = authorised-but-empty, 400 = bad table name. No case produced an HTML login page.

### B. The EC2 mapping has nothing to identify a NIC with

```
Cloud Mgmt Network Interface 1  -> [source_native_key, cmdb_ci]
Cloud Mgmt Network Interface 2  -> [source_native_key]
Storage Volume 1                -> [source_native_key]
```
versus the prerequisite feeds:
```
NIC import, cmdb_ci_nic       -> [private_dns, name, operational_status, install_status, private_ip,
                                  public_dns, public_ip, source_native_key, state, object_id, ip_address]
Volume import, Storage Volume 1 -> [size_bytes, object_id, source_native_key, storage_type,
                                  operational_status, name, install_status, volume_id, state, size]
```
And the shared key source:
```
Cloud Mgmt Network Interface 1 . source_native_key  <- nicSourceNativeKey
Cloud Mgmt Network Interface 1 . cmdb_ci            -> entity "Virtual Machine Instance 1" (cmdb_ci_vm_instance)
```

### C. Identifier dependency
```
cmdb_identifier table=cmdb_ci_nic            independent=false (3 rows)
cmdb_identifier table=cmdb_ci_storage_volume independent=false (3 rows)
```

### D. Partial payload (verbatim excerpt, `2026-11-08 02:51:41`)
```json
{ "className": "cmdb_ci_nic",
  "values": { "discovery_source": "SG-AWS" },
  "sys_object_source_info": { "source_feed": "SG-AWS-EC2-Instance", "source_name": "SG-AWS",
    "source_native_key": "c3f0b8c453b32010c23bddeeff7b12ee|639051062568|us-east-2|eni-04843cac6d5784192" },
  "internal_id": "537c82afc11c97d097877a92cb03ab3e",
  "reason": "MISSING_DEPENDENCY" }
...
"referenceItems": [ { "referenceField": "cmdb_ci",
                      "referencedBy": "537c82afc11c97d097877a92cb03ab3e",
                      "referenced":   "d37c82afa31c97d0783487146f898f3d" } ]
```

### E. Nothing produced the CIs
```
NIC   CEX0001013  rows=0  -> sn_aws_integ_sg_aws_network_interface = 0 rows   (ISET0010025/26 processed, empty)
VOL   no CEX      -> sn_aws_integ_sg_aws_storage_volume      = 0 rows, 0 import sets ever
cmdb_ci_nic = 0 records
cmdb_ci_storage_volume = 7 records, all discovery_source=ServiceNow, object_id blank
```

---

## Tried and ruled out (in order)

1. **"Blank Object ID mappings are the defect."** Ruled out. Those entities are stubs — they have *no* attribute mappings at all. Blank is correct for a reference-only feed; the attributes live in the prerequisite feeds' mappings (§B).
2. **The dangling internal payload id `d37c82afa31c97d0783487146f898f3d`.** Ruled out as a cause. It appears as an `internal_id` in **none** of the 9 stored payloads, and it is different on every run (`f5cf319f…`, `2e6eb91b…`, `3c168267…`, `d37c82af…`). Decisive: in the 07:11 and 07:17 runs the reference **correctly pointed at the VM's own `internal_id`** (`826eb91ba7dc93d0…`, `f5cf319fa7dc93d0…`) and the NIC was **still** `MISSING_DEPENDENCY`. It is a symptom of the item never being emitted, not the trigger.
3. **Inactive `SG-AWS-Organization` alone.** Necessary-but-not-sufficient. It does explain why nothing runs on schedule and why the manual EC2 runs never triggered NIC/Volume (their CEX timestamps 07:00 vs EC2 07:10/07:16/02:23/02:42/02:51 never coincide). But chain-activating it alone would not fix the warnings, because §E shows the NIC feed loads 0 rows and the volume feed has never run.
4. **Classic transform-map machinery.** Dead end, and explains the initially "empty" evidence: the connector does not use `sys_transform_map` / `sys_transform_entry`. `sys_import_set_run.sys_transform_map` is blank and `sys_robust_transformer` is set; the mapping is an RTE definition. Hence "Transform Target Rows" and the standard import logs are genuinely empty here — that is normal for this connector, not a symptom.
5. **`sysauto_import` / `sys_object_source_info`.** Wrong tables: `sysauto_import` returns 0 rows (correct table is `scheduled_import_set`), and `sys_object_source_info` is not a queryable table (400). The object-source data lives in `sys_object_source`, keyed in `id`.
6. **"The prerequisites are not configured" (claim from a parallel agent).** **Incorrect.** Both exist as active `scheduled_import_set` records (ids in §1). Their data sources also exist: `SG-AWS-Network-Interface` = `2a5c4a8253203010a3e4ddeeff7b12c5`, `SG-AWS-Storage-Volume` = `9f35074653603010a3e4ddeeff7b1208`.  Creating new schedules on that premise would add duplicate orchestration over the same source keys — do not do it.
7. **Permissions/ACL as the reason the partials are invisible elsewhere.** No: partial payloads, executions and import sets are all readable as `admin`; the blank standard logs are a connector-architecture fact (§D/§E), not an ACL artefact.

---

## Smallest repair — proposed, **not executed**

Do **not** touch mappings, identification rules, `cmdb_ci_nic` records, or the partials. Do **not** create duplicate scheduled imports.

**Step 1 — explain the `rows=0` (diagnostic, before changing anything).**
Run `SG-AWS-Network-Interface` once (Execute Now) and watch `CEX` `rows`. If it is 0 again, the AWS call is returning an empty page — check, in this order: (a) `ec2:DescribeNetworkInterfaces` (and `ec2:DescribeVolumes`) allowed for the role behind alias `c3f0b8c4…`; (b) the account/region scope the connector applies (`639051062568` / `us-east-2`); (c) the load script's page/next-token handling. NCIs appear in the EC2 payload, so the account/region scope is proven reachable — a permissions/API-scope difference is the leading hypothesis, but it is **not yet proven**.

**Step 2 — populate prerequisites in chain order.**
1. Execute `SG-AWS-Network-Interface` → expect `cmdb_ci_nic` to gain `eni-04843cac6d5784192` with `object_id` set and a `sys_object_source.id` of `…|639051062568|us-east-2|eni-04843cac6d5784192`.
2. Execute `SG-AWS-Storage-Volume` → expect `vol-0d78f1f1bebee052f` with `object_id` set.
3. Re-run `SG-AWS-EC2` → expect `ire_partial` to drop from 6 to 0 for this row, the `cmdb_rel_ci` warnings (3) to clear, and no new `cmdb_ire_partial_payloads` row referencing this eni/vol.

**Step 3 — keep it running.** Either activate the `SG-AWS-Organization` chain (it also pulls org discovery the user has deliberately left off — decide explicitly) or give the three children their own schedule in the 140 → 160 → 180 order. Activating the parent is the smaller change; leaving it inactive means EC2 will keep emitting dependents that nothing creates.

**Acceptance test:** latest `CEX` for `SG-AWS-EC2` has `ire_partial=0`; `cmdb_ci_nic` contains the eni with a non-blank `object_id`; `cmdb_rel_ci` shows VM→NIC and VM→volume links; no new partial payload for these keys.

---

## Open question

**Why did `CEX0001013` load 0 rows?** Facts: `state=complete`, `errors=0`, `skipped=0`, data source `last_success_import_time=2026-11-07 07:01:37`, import set table 0 rows, two import sets (`ISET0010025`, `ISET0010026`) both `processed`. "Complete with zero rows" means the AWS/data-layer response was empty rather than an error — but I did not get to the API-response level from outside, and I did not run anything to find out. That is the single piece still needed before Step 2 can be expected to work.

---

## Method / hygiene notes

* Authentication: HTTP Basic, `admin`, GET only; credentials never printed; held in a `chmod 600` scratch file outside the repo.
* No writes of any kind: no mapping edits, no import runs, no partial reprocessing, no CI creation, no chain activation.
* Not present in this checkout: `SOLVED_HERMES.MD` / `SOLVED_MINI_HERMES.MD` (`ls SOLVED_*` → nothing). Their claim that the prerequisites are unconfigured should be corrected wherever those files live.
