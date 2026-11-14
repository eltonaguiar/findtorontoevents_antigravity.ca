# Salesforce Crash Course Research Notes

**Research File:** research/salesforce/salesforceyetagain-v4/2026-11-14T02-11-53Z/crash_course.md
**Source:** https://eltonaguiar.github.io/ServiceNow_Learning_TSOM-_CSM_FSM_SalesCRM_HAM_ITSM/docs/salesforce/crash-course/
**Author:** opencode
**Date:** 2026-11-10

## Overview

The Salesforce Technical Training — ELI5 Crash Course is designed for complete beginners with no prior Salesforce experience. It provides a comprehensive, hands-on overview of the Salesforce platform as a cloud-based CRM platform.

## Core Concepts Covered

### 1. What Is Salesforce?

**Definition:** Cloud-based Customer Relationship Management (CRM) platform used to track:
- **Customers:** Who they are, what they bought, when they last called
- **Sales deals:** Opportunities, quotes, contracts
- **Support cases:** Tickets, issues, resolutions
- **Marketing campaigns:** Emails, ads, events

**ELI5 Analogy:** A school student folder system where every teacher can access the same folder.

**Key Characteristics:**
- **Cloud-based:** Hosted in the cloud
- **Multi-tenant:** Shared infrastructure across customers
- **Metadata-driven:** Everything defined by code rather on by clicks
- **Declarative vs Programmatic:** No-code (clicks) vs code (Apex)

### 2. The Big Picture: Objects, Records, Fields

**Three-layer architecture:**
- **Object:** Type of thing tracked (table in database)
  - *Standard Objects*: Account, Contact, Opportunity, Case, User (built-in)
  - *Custom Objects*: Built for specific business needs (Property Listing, Course Enrollment)
- **Record:** One specific instance of an object (row)
  - Example: "Acme Corp" (Account record)
- **Field:** One piece of data about that instance (column)
  - Example: Phone number, Industry, Annual Revenue

### 3. Navigation: Where Things Live

**Setup (Control Room) vs App Launcher (User view):**

**Setup Breadcrumb Examples:**
- `Setup > Object Manager > [Object Name]` (create/edit objects & fields)
- `Setup > Object Manager > [Object] > Fields & Relationships`
- `Setup > Users > Users`
- `Setup > Apex Classes`
- `Setup > Debug Logs`

**App Launcher (User):** 9-dot grid to access all applications

**ELI5:** Setup = control room, App Launcher = user view

### 4. Users, Profiles, Roles & Security

**Users:** Need username (email), profile, role (optional), license type

**License Types:**
- **Salesforce:** Full CRM access
- **Salesforce Platform:** Custom apps only
- **Chatter Free:** Collaboration only
- **External Identity:** Experience Cloud for customers/partners

**Profiles:** Control what users can see/do
  - Object permissions (read, create, edit, delete)
  - Field permissions
  - Page layouts
  - Login restrictions

**Permission Sets:** Additional access beyond profile (less permissive than admin)

**Roles:** Record-level sharing hierarchy

**Security Rules:** Profiles (what you can do), Permission Sets (extra access), Roles (which records you can see)

### 5. Data Integrity & Relationships

**Relationship Types:**
- **Lookup:** Loose association; child can exist without parent
  - Example: Case → Account
- **Master-Detail:** Tight; child cannot exist without parent; deleting parent deletes child
  - Example: Opportunity → Opportunity Line Item
- **Hierarchical:** Self-lookup (User → Manager)

**Roll-Up Summary Fields:** Master-Detail only; aggregate child records (SUM, COUNT, MIN/MAX)

**Data Integrity Best Practices:**
- Required fields
- Unique fields
- Validation rules
- Dependent picklists
- Record types

### 6. Automation: Flow, Process Builder, Workflow

**Flow (Modern Standard):** Replaces Workflow Rules and Process Builder
- **Screen Flow:** User clicks button; guided data entry
- **Record-Triggered Flow:** Record created/updated; auto-update fields, create related records
- **Scheduled-Triggered Flow:** On schedule; nightly data cleanup, batch emails
- **Platform Event Flow:** Event received; react to external system events

**Flow vs Code:** Use Flow for simple automation; use Apex for complex logic, bulk processing, API callouts

### 7. Code: Apex, Visualforce, LWC

**Apex:** Salesforce proprietary programming language (Java-like); server-side
- **Class:** Container for methods (`public class CaseHandler { ... }`)
- **Trigger:** Runs before/after record save (`trigger CaseTrigger on Case (before insert) { ... }`)
- **SOQL:** Query language (`SELECT Id, Name FROM Account WHERE Industry = 'Technology'`)
- **DML:** Insert, update, delete, upsert (`insert newCase;`)
- **Governor Limits:** Runtime limits (SOQL queries, DML rows, heap size, callouts, CPU time)

**Apex Example:**
```
trigger CaseAutoAssign on Case (before insert) {
    for (Case c : Trigger.new) {
        if (c.Origin == 'Phone' && c.Priority == 'High') {
            c.OwnerId = '00Gxx000000ABCDE';
        }
    }
}
```

**Visualforce:** Older UI framework (HTML-like tags); used for PDFs, precise layout
**Lightning Web Components (LWC):** Modern UI (JavaScript + HTML); standard for Lightning Experience

### 8. Integration: APIs & External Systems

**Integration Types:**
- **REST API:** Modern web/mobile, real-time
- **SOAP API:** Legacy enterprise systems
- **Bulk API:** Load millions of records
- **Streaming API:** Real-time notifications

**Best Practice:** Use Named Credentials for secure endpoint storage

### 9. Troubleshooting & Performance

**Common Issues & Solutions:**
- Apex code errors → Debug Logs (Setup > Debug Logs)
- Flow errors → Setup > Flow > Debug
- Record not saving → Validation Rules
- User can't see field → Profile Field-Level Security
- Slow page load → Setup > Optimizer
- API callout failing → Remote Site Settings / Named Credentials

**Governor Limits:**
- SOQL queries: 100 per transaction
- DML rows: 10,000 per transaction
- Heap size: 6 MB sync / 12 MB async
- Callouts: 100 per transaction
- CPU time: 10,000 ms sync / 60,000 ms async

**Bulkification:** Collect IDs first, query once, process in memory

### 10. Design Considerations

**Before Building:**
- Can Flow do this instead of code?
- Will this scale to 1M+ records?
- Who needs to see this data?
- What happens if external system is down?
- Is this data sensitive?
- Will users adopt this?

**Security Design:** Least privilege, field-level security, sharing rules, input validation
**Performance Design:** Bulkify triggers, selective queries, platform cache, asynchronous processing

### 11. Out-of-the-Box Features to Know

- **Record Types:** Different layouts, picklist values, business processes
- **Formula Fields:** Read-only calculated fields
- **Roll-Up Summary:** Master-Detail aggregate
- **Validation Rules:** Block invalid data
- **Approval Processes:** Multi-step record approval
- **Sandboxes:** Production copies for development
- **Change Sets:** Move config between orgs
- **Salesforce CLI:** Command-line tool
- **Developer Console:** Built-in IDE

### 12. Official Salesforce Learning Resources

**Trailhead:** Free, gamified learning platform
- Admin Beginner trail
- Developer Beginner trail
- Data Management trail
- Integration trail
- LWC basics
- Security trail

**Documentation:** Salesforce Help, Developer Docs, Apex Guide, LWC Guide

**YouTube:** Salesforce Developers, Salesforce Admins, Trailhead

## Quick Start Checklist

- Create free Salesforce Developer Org
- Complete Trailhead "Admin Beginner" trail
- Complete Trailhead "Developer Beginner" trail
- Create custom object with fields and relationships
- Build Record-Triggered Flow
- Write simple Apex trigger and test class
- Build basic LWC component
- Set up Named Credentials and make REST callout
- Review Debug Logs for failed operations