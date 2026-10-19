# CIS-VR ServiceNow Coding Guide Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an official-source-backed ServiceNow coding chapter to the existing CIS-VR study page.

**Architecture:** Keep the current standalone HTML page and add the coding chapter into its existing contents/navigation structure. Explain platform-first implementation choices and safe scripting boundaries with concise illustrative patterns; link each topic to official, release-matched ServiceNow references.

**Tech Stack:** HTML/CSS, JavaScript examples, ServiceNow product and developer documentation.

---

### Task 1: Extend and validate the existing CIS-VR page

**Files:**
- Modify: `findtorontoevents.ca/CIS-VR/index.html`

- [ ] **Step 1: Confirm existing page structure and preserve user changes**

Read the full target page and retain its current introduction, study sections, official exam links, disclaimer, responsive styling, and accessibility elements. Add a table-of-contents entry and a coding section without replacing the file.

- [ ] **Step 2: Add the ServiceNow coding material**

Explain the configuration-first sequence for Vulnerability Response, then illustrate where integration/transform scripts, Script Includes, Business Rules, `GlideRecordSecure`, GlideAjax, and Scripted REST APIs belong. Each code sample must be labeled as illustrative and use no assumed VR table names or undocumented product internals. Add official HTTPS links to ServiceNow docs, developer/API references, and the existing CIS-VR credential page; tell readers to use documentation matching their installed release and applications.

- [ ] **Step 3: Validate page navigation and reference URLs**

Check that every local table-of-contents fragment has a matching page ID and each new ServiceNow link uses HTTPS on `servicenow.com`, `developer.servicenow.com`, or `learning.servicenow.com`. Confirm section order and numbering are consistent. The target is a standalone HTML page without inline JavaScript, so no build or script syntax test is required unless that changes during editing.

- [ ] **Step 4: Review the final diff**

Run `git diff --check -- findtorontoevents.ca/CIS-VR/index.html` and inspect `git diff -- findtorontoevents.ca/CIS-VR/index.html` to verify the change is limited to the requested guide content and does not disturb unrelated working-tree changes.
