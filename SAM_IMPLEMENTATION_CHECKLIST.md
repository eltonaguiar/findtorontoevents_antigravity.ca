# ServiceNow SAM Implementation Checklist
# Generated: 2026-11-13T15:44:42Z
# Unique Identifier: SAM-IMPLEMENTATION-GAP-ANALYSIS-2026-11-13

## Overview
This document provides a comprehensive checklist for implementing a ServiceNow Software Asset Management (SAM) module, addressing gaps identified in cross-referencing GitHub documentation with industry best practices.

## 1. Prerequisites and Dependencies
### 1.1 Plugin/Subscription Requirements
- [ ] SAM Professional entitlement/plugin activated
- [ ] SAM Foundation plugin activated (if applicable)
- [ ] Required roles verified: sam_admin, sam_user, model_manager, asset, procurement_user, contract_manager
- [ ] Workspace and integration roles configured
- [ ] Instance version/family pin confirmed with known breaking changes

### 1.2 Dependent Modules
- [ ] Discovery plugin activated
- [ ] CMDB Identification and Reconciliation Engine (IRE) configured
- [ ] Contract Management plugin activated
- [ ] Procurement plugin activated (if required)
- [ ] Content Services integration configured
- [ ] Store apps/publisher packs installed as needed

## 2. Data Model and Source-System Contracts
### 2.1 Authoritative Sources Definition
- [ ] Inventory sources: Discovery, SCCM/MECM, Jamf, Intune, or other approved sources
- [ ] Entitlement sources: Purchase records, contracts, procurement systems
- [ ] Contract sources: Contract repositories, legal systems
- [ ] User/device sources: HR systems, Active Directory, CMDB
- [ ] SaaS subscription sources: Subscription portals, usage data

### 2.2 Data Contracts
- [ ] Required fields documented for each source
- [ ] Update frequency defined for each source
- [ ] Error handling procedures established
- [ ] Data ownership assigned for each source
- [ ] Import approach documented (transform maps, IntegrationHub, REST, Service Graph connectors)

### 2.3 Deduplication and Data Quality
- [ ] Deduplication rules defined for installs, CIs, and entitlements
- [ ] Stale data handling procedures established
- [ ] Retirement rules for decommissioned software/devices
- [ ] IRE usage confirmed for non-Discovery inventory sources
- [ ] Duplicate install handling across sources configured

## 3. Software Model Strategy
### 3.1 Software Models
- [ ] Publisher/product/version/edition modeling approach defined
- [ ] Discovery maps validated for high-value publishers
- [ ] Suite relationships modeled (bundles, upgrades, downgrades)
- [ ] Upgrade/downgrade rights configured
- [ ] Cross-grade rights documented

### 3.2 Content Library/PPN Strategy
- [ ] Content Library integration configured
- [ ] PPN-based software-model matching enabled
- [ ] Fallback manual modeling procedures documented
- [ ] Content updates scheduled and monitored

### 3.3 License Metrics
- [ ] Per-device, per-user, named-user, per-core, processor metrics configured
- [ ] Vendor-specific metric groups created for Microsoft, Oracle, IBM, Adobe, SAP, VMware, Citrix
- [ ] Metric groups assigned to software models
- [ ] License metric validation procedures established

## 4. Entitlement Management
### 4.1 Entitlement Import
- [ ] Purchase records, license metrics, quantities defined
- [ ] Contract/PO terms, maintenance dates documented
- [ ] Upgrade/downgrade rights configured
- [ ] Allocations and entitlements imported before reconciliation
- [ ] PPN matching for entitlements configured

### 4.2 Reconciliation
- [ ] On-demand reconciliation tested
- [ ] Weekly reconciliation scheduled
- [ ] Shortfall/surplus results validated
- [ ] License Workbench configured and validated
- [ ] Reconciliation test cases with expected results documented

## 5. SaaS Subscription Management
### 5.1 SaaS Subscriptions
- [ ] sn_sam_saas_int plugin activated
- [ ] Seat/usage ingestion configured
- [ ] Subscription records and renewal dates tracked
- [ ] Consumption summaries generated
- [ ] Custom integration developed for SaaS portals if required

## 6. Process Design and Governance
### 6.1 Data Ownership
- [ ] Data owners assigned for entitlements, contracts, procurement, software models, normalization, reconciliation
- [ ] Process owners defined for each major data domain
- [ ] Role-based access model configured (admin, analyst, read-only, procurement)

### 6.2 Change Control
- [ ] Software-model changes follow controlled release process
- [ ] Metric changes follow controlled release process
- [ ] Discovery-map changes follow controlled release process
- [ ] Normalization changes follow controlled release process
- [ ] Reconciliation-rule changes follow controlled release process
- [ ] Audit trail preserved for evidence linking entitlements to POs/invoices/contracts

### 6.3 Operational Cadence
- [ ] Daily normalization schedule established
- [ ] Weekly reconciliation schedule established
- [ ] Monthly review process defined
- [ ] Quarterly true-up process defined
- [ ] Reclamation and optimization workflows defined with business owners

## 7. Validation and Testing
### 7.1 Test Cases
- [ ] Per-device entitlement test: 1 entitlement, 2 installs, expected shortfall of 1
- [ ] Named-user entitlement test: inactive users excluded
- [ ] Suite/downgrade rights test scenarios
- [ ] CI-to-install linkage validation
- [ ] Duplicate install handling validation
- [ ] Stale install cleanup validation

### 7.2 Data Quality Acceptance Criteria
- [ ] Minimum thresholds for normalized installs
- [ ] Entitlement completeness thresholds
- [ ] CI coverage thresholds
- [ ] Reconciliation accuracy thresholds
- [ ] Performance considerations for large install/entitlement volumes

## 8. Reporting and Dashboards
### 8.1 Primary Reports
- [ ] License Workbench configured
- [ ] Compliance reports configured
- [ ] Optimization reports configured
- [ ] Reclamation reports configured
- [ ] Scheduled distribution configured

### 8.2 Training and Documentation
- [ ] User training materials created
- [ ] Runbooks for day-to-day users created
- [ ] Exception handling procedures documented
- [ ] Rollback procedures documented

## 9. Cutover and Operations
### 9.1 Migration/Cutover
- [ ] Migration steps from prior systems/legacy tables documented
- [ ] Hypercare support model defined
- [ ] Known-issue list maintained
- [ ] Monitoring and alerting configured
- [ ] Rollback procedures documented

## 10. Pilot and Rollout
### 10.1 Pilot Scope
- [ ] Limited product set selected
- [ ] End-to-end validation completed
- [ ] Success criteria defined
- [ ] Go/no-go criteria met

### 10.2 Production Rollout
- [ ] Expansion to additional publishers planned
- [ ] Expansion to additional sources planned
- [ ] Production support model established
- [ ] Ongoing monitoring and optimization planned

## 11. CMDB Assumptions to Challenge
### 11.1 Success Criteria Redefinition
- [ ] "CI inserted correctly" redefined as "entitlement, software model, normalized install, and consumption calculation must reconcile correctly"
- [ ] Closed-loop validation implemented: entitlement ↔ software model ↔ normalized install/consumption ↔ reconciliation result

### 11.2 Additional Controls
- [ ] CI-to-install linkage quality validated (per-device and per-user metrics)
- [ ] Explicit IRE usage for non-Discovery inventory sources
- [ ] Suite/bundle/upgrade/downgrade rights modeling
- [ ] Vendor-specific metric groups instead of generic "Common"

## 12. Likely Documentation Omissions
### 12.1 Prerequisites and Dependency Map
- [ ] SAM plugin/subscription, Discovery plugin, MID Servers where applicable
- [ ] Source connectors, content service, required roles

### 12.2 Test Cases
- [ ] "1 per-device entitlement + 2 installs → shortfall of 1"
- [ ] "Named-user entitlement with inactive users excluded"
- [ ] Other reconciliation test scenarios

### 12.3 Data-Quality Acceptance Criteria
- [ ] Minimum thresholds for normalized installs
- [ ] Entitlement completeness thresholds
- [ ] CI coverage thresholds
- [ ] Reconciliation accuracy thresholds

### 12.4 Rollback and Exception Procedures
- [ ] Software model misclassification procedures
- [ ] Entitlement import with wrong metric procedures
- [ ] Duplicate inventory from source integration procedures

### 12.5 SaaS-Specific Process
- [ ] Subscription ingestion procedures
- [ ] Seat count tracking
- [ ] Usage data collection
- [ ] Renewal tracking
- [ ] Custom integration requirements for ServiceNow subscription-usage scenarios

### 12.6 Vendor-Specific Licensing
- [ ] Microsoft, Oracle, IBM, Adobe, SAP, VMware, Citrix metric groups
- [ ] Publisher-specific entitlement interpretation

## 13. Recommended Addition to Repository
### 13.1 SAM_IMPLEMENTATION_CHECKLIST.md
- [ ] This document created with comprehensive gates

### 13.2 Gate Categories
- [ ] Plugin/subscription and roles verified
- [ ] Inventory source(s) selected and validated
- [ ] Entitlement source, fields, and import approach defined (including PPN/Content Library strategy)
- [ ] Software-model and license-metric matrix for priority publishers
- [ ] Normalization exception workflow
- [ ] Reconciliation test cases with expected results
- [ ] SaaS subscription and usage plan
- [ ] Data ownership, access model, and audit trail
- [ ] Pilot scope, success metrics, and production rollout criteria

## References
- GitHub: ALT_PARALLELSWARM_SAM (https://github.com/eltonaguiar/ALT_PARALLELSWARM_SAM/tree/main)
- GitHub: ServiceNow_Learning_TSOM-_CSM_FSM_SalesCRM_HAM_ITSM (https://eltonaguiar.github.io/ServiceNow_Learning_TSOM-_CSM_FSM_SalesCRM_HAM_ITSM/docs/modules/sam/sam-guide/)
- GitHub: ServiceNow_Learning (https://eltonaguiar.github.io/ServiceNow_Learning/)
- ServiceNow SAM Implementation Best Practices
- CMDB Identification and Reconciliation Engine (IRE) documentation
- Software Asset Management Professional plugin documentation

## Document Metadata
- **Generated**: 2026-11-13T15:44:42Z
- **Unique Identifier**: SAM-IMPLEMENTATION-GAP-ANALYSIS-2026-11-13
- **Version**: 1.0
- **Status**: Initial Gap Analysis Complete
- **Next Review**: Upon implementation of pilot phase