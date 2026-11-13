# ServiceNow SAM Module Full Reference

This document compiles the full configuration, data flow, discovery rules, and operational details for the **Software Asset Management (SAM)** module. It matches the style and depth of the final reference published for the *ALT_PARALLELSWARM* repo.

---

## 0. Overview
- SAM changes how ServiceNow Discovery stores software installation data. Discovery now writes to **`cmdb_sam_sw_install`** and triggers creation/updating of **`cmdb_sam_sw_discovery_model`** via a business rule.
- The canonical source of current software data is `cmdb_sam_sw_install`. All compliance, normalisation, and licensing calculations reference this table.

## 1. Plugin Activation
| Plugin | Purpose |
|--------|---------|
| `com.sn_samp_master_ws` | Activates SAM, creates tables, CS, UI, and business rules |
| `com.sn_samp_ml_normalization` | Optional ML‑based normalisation |
| Legacy SCCM plugins | **Deprecated** – use Service Graph for SCCM |

## 2. Discovery → SAM Data Flow
1. **Discovery** writes to `cmdb_sam_sw_install`. |
2. **Business rule** on `cmdb_sam_sw_install` checks for an existing `cmdb_sam_sw_discovery_model` with matching `publisher, product, version, edition`. | *If found:* updates install; *If not:* creates new discovery model. |
3. The discovery model is normalised automatically (daily scheduled job or ML). |
4. `cmdb_software_product_model` holds purchased entitlements and is linked via normalised fields.

## 3. CI‑Side Configuration
- Configure the related‑list **Software Installation → Installed on** on any computer server CI (`cmdb_ci_computer`). |
- This allows operators to see current installs directly from the CMDB record.

## 4. Discovery Models & Normalisation
- Discovery models cannot be created manually.
- Normalisation status: `Normalized`, `Partially Normalized`, `Publisher Normalized`, `Match Not Found`, or `Manually Normalized`.
- Manual normalisation is performed in the **Software Asset Workspace** → `Discovery Models` → `Normalize` action.

## 5. Normalisation Process
- **Daily job** `SAM - Normalize discovery models using content library rules` runs, matching discovery data against the SAM Content Library.
- **ML Normalisation** (if plugin active) augments matches in real time.

## 6. Duplicates & Stale‑Data
- Duplicate installs arise when the same software is discovered via multiple sources (Discovery + SCCM). |
- Uninstalled software can be removed via the REST Table API (
  `DELETE api/now/table/cmdb_sam_sw_install?sysparm_query=installed_on=<id>`). |

## 7. Reconciliation
- Weekly reconciliation compares `cmdb_sam_sw_install` with `cmdb_software_product_model`.
- Results are displayed in three layers: **Product Results**, **Software Model Results**, and **License Metric Results**.

## 8. Configuration Options
- Plugins, scheduling, CI form configuration, content‑service opt‑in, Oracle domain‑specific properties, and SCCM integration are all configurable via standard ServiceNow locations described in the SAM docs.

## 9. Key Tables
| Table | Table name | Purpose |
|---|---|---|
| Software Installation | `cmdb_sam_sw_install` | Canonical discovery output |
| Discovery Model | `cmdb_sam_sw_discovery_model` | Holds normalised publisher/product/version/edition |
| Software Model | `cmdb_software_product_model` | Purchased entitlements |
| VMware License | `samp_vmware_license_key`/`samp_vmware_license_key_usage` |
| Oracle Options | `samp_oracle_options` |

## 10. Out‑of‑Box Scripts
A full list of all default scripts, business rules, and scheduled jobs is available in the *final* reference file. See the earlier `Out‑of‑Box Scripts` section in the documentation.

## 11. Maintenance
- Adding a new software model -> create a new record in `cmdb_software_product_model` (no direct insert into install table). |
- Normalise an existing discovery model via workspace action or edit. |
- Reclassify or delete a software model via the proper UI paths.

## 12. High‑Probability Items
- License position calculations, compliance dashboards, true‑up costing, and Oracle‑specific reconciliation rules are configuration knobs that organisations must review regularly.

## 13. Workspaces & Dashboards
- Key entry points: `Software Asset Workspace`, `License Operations`, `Reconciliation Dashboard`, `Compliance Dashboard`, and `License Position Report`.

## 14. Parameter Inventory
- See the *Parameter Inventory* section in the earlier documentation for a exhaustive list of mandatory and optional parameters.

---

**Prepared by the Kilo AI System – reference date 2026‑11‑13.**
