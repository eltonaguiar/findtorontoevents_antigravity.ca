# Licensing and prerequisites

**Agent:** Kilo (deepseek-flash) · **Updated:** 2026-11-19 · **Docs release:** Australia

ITOM is not one entitlement. It is a set of subscriptions, Store apps, plugins, and roles.
This page gives you the questions to ask before you build, not a price list — ServiceNow
documentation deliberately does not publish prices or contract packaging.

---

## 1. The licensing application

The **ITOM/OT SU Licensing** application calculates and displays how many subscriptions your
organisation purchases and consumes. It covers subscriptions for:

- ITOM Visibility
- ITOM Discovery
- ITOM AIOps
- Health Log Analytics
- ITOM Optimization
- ITOM Cloud Accelerate
- Digital End-User Experience (DEX)
- Service Observability

You can buy them separately (à la carte) or in a bundle. The application provides:

| Capability | What it shows | Role |
|---|---|---|
| Usage against allocated units | Resource usage versus purchased subscription units | `sn_itom_license.reader` |
| Licensing dashboard | Daily usage count and average consumption over 90 days; which resources are counted | `admin` |
| 2026 Packaging SKU prediction | Current CI consumption versus predicted usage under the 2026 packaging SKU | `admin` |

The practical lesson: **licence consumption follows resource counts**. Discovery that creates
more CIs, cloud accounts that add resources, and agents that add inventory can all change the
number. Design with the counting model in mind, not after the invoice.

---

## 2. Subscription map

| Capability | Typical entitlement | Verify |
|---|---|---|
| Discovery | ITOM Visibility subscription; `com.snc.discovery` plugin | Plugin active and subscription present |
| Service Mapping | ITOM Visibility subscription; `com.snc.service-mapping` plugin; Service Mapping activation | `sm_admin` role and activation completed |
| Event Management | ITOM AIOps subscription | Event Management plugins and Store apps installed |
| Health Log Analytics | Separate HLA subscription | HLA Store app installed; log storage provisioned |
| Metric Intelligence | Part of the AIOps/metrics estate | Metric definitions and connectors available |
| Service Reliability Management | **ITSM Standard + ITOM Operator Professional** | Both subscriptions present |
| Service Observability | Service Observability subscription | Vendor connectors and SOW configured |
| Synthetic monitoring | AIOps/observability entitlement | ACC proxy or MID Server locations configured |
| SLO Management | AIOps/reliability entitlement | SLO features visible in SOW |
| Cloud Account Management | ITOM Cloud Accelerate licence | Cloud Governance Suite (CGS) prerequisite for Cloud Workspace |
| Cloud Services Catalog | ITOM Cloud Accelerate / Cloud Governance Suite | Store apps and cloud credentials configured |
| Now Assist / Otto for ITOM | AI tier and ITOM entitlement | AI Control Tower and AI Admin Hub configured |

> **Do not infer entitlement from a menu.** A menu item can exist while the subscription or
> Store app that makes it useful is absent. Check **System Applications > All Available
> Applications**, the subscription record, and the Store app version.

---

## 3. Release cadence

ITOM applications receive regular updates from the **ServiceNow Store**, with schedules that
are independent of family releases. You must deploy upgrades to get the latest features. This
is why a guide pinned to a family release can be right about the architecture and stale about
a specific form.

When a page matters, check:

1. The release selector on the documentation page.
2. The Store app version in your instance.
3. The plugin list (`v_plugin` or **System Applications > Plugins**).

---

## 4. Platform prerequisites

Before any ITOM lab or build, confirm:

| Prerequisite | Why | How to check |
|---|---|---|
| **MID Server** | Discovery, Event Management pull connectors, HLA, ACC, and Orchestration need a route into the network | `MID Server > Servers`; status Up and Validated |
| **Credentials** | Discovery cannot classify or explore without them | `Discovery > Credentials` or the ITOM Configuration Console |
| **Users and groups** | Alerts route to assignment groups; approvals need owners | `User Administration > Users/Groups` |
| **CMDB classes and identification** | Duplicate CIs poison every map and alert | CI Class Manager; identification and reconciliation rules |
| **Locations and schedules** | SLAs and maintenance windows compute against them | Foundation data |
| **Time sync** | Log and event timestamps decide ordering and correlation | NTP on MID Server and sources |
| **Tags** | Tag-based mapping and cloud governance depend on them | CI tags and cloud tag policies |
| **Maintenance windows** | Change work should not create an alert storm | Event Management maintenance rules |

---

## 5. The PDI reality

A free Personal Developer Instance (PDI) is excellent for platform mechanics but often lacks
ITOM entitlements. Before a lab:

- Confirm the plugin is available. If it is not, use the lab's **design-only path**: draw the
  records and rules, then verify the concepts against official docs.
- Never request or use production credentials in a PDI.
- A PDI can be reclaimed after inactivity. Export any artifact you care about.
- Some ITOM apps are Store apps that require a ServiceNow Store account and entitlement.

A lab that cannot run is still useful if it produces a correct design and a list of missing
prerequisites. A lab that pretends to run is not.

---

## 6. Cloud Accelerate entitlement notes

The cloud family has its own layering:

- **Cloud Account Management** becomes available with the ITOM Cloud Accelerate licence.
- **Cloud Governance Suite (CGS)** is a prerequisite for **Cloud Workspace** and provides the
  home page and asset explorer.
- **CGS + Cloud Account Management** adds account overview, requests and approvals,
  certification, the compliance dashboard, configuration, and request policies.
- **Cloud Provisioning and Governance (CPG)** is being prepared for deprecation. From the
  Brazil release onward it is no longer installed on new instances, but remains supported for
  existing customers. New work should evaluate **Cloud Services Catalog**.

This is a fast-moving area. Verify the current entitlement names on the Store and in your
contract before designing.

---

## 7. Licensing anti-patterns

| Anti-pattern | Consequence |
|---|---|
| Building Discovery without checking the subscription | A working schedule that cannot be licensed |
| Assuming HLA is included with Event Management | It is a separate licence |
| Assuming CPG is the greenfield cloud product | New instances do not get it; use Cloud Services Catalog |
| Counting only "servers" | CIs, cloud resources, and network devices may all count |
| Buying a bundle without mapping use cases | You pay for capability nobody operates |
| Letting discovery create CIs nobody owns | Licence growth with no operational value |

---

## Official sources

- ITOM/OT SU Licensing overview — <https://www.servicenow.com/docs/r/australia/it-operations-management/explore-itom-licensing.html>
- ITOM overview and licensing statement — <https://www.servicenow.com/docs/r/australia/it-operations-management/r_ITOMApplications.html>
- ITOM Visibility licensing and plugins — <https://www.servicenow.com/docs/r/australia/it-operations-management/itom-visibility/itom-visibility-landing-page.html>
- Service Reliability Management prerequisites — <https://www.servicenow.com/docs/r/australia/it-operations-management/service-reliability-management/sr-landing-page.html>
- Health Log Analytics licensing — <https://www.servicenow.com/docs/r/australia/it-operations-management/health-log-analytics/hla-landing-page.html>
- Cloud Account Management entitlements — <https://www.servicenow.com/docs/r/australia/it-operations-management/cloud-account-management/exploring-cam.html>
- Cloud Provisioning and Governance deprecation note — <https://www.servicenow.com/docs/r/australia/it-operations-management/cloud-configuration-governance/cloud-management-v2-landing-page.html>
- ServiceNow Store — <https://store.servicenow.com/store>
