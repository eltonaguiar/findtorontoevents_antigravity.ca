# CIS-VR ServiceNow Coding Guide Design

## Goal

Extend the existing CIS-VR study page into a practical ServiceNow Vulnerability Response coding guide grounded in official ServiceNow documentation.

## Audience and scope

The page is for learners and implementers who need to understand where supported ServiceNow configuration ends and custom scripting begins. Preserve the existing CIS-VR overview and implementation material, then add a focused coding chapter rather than replacing the page or creating a separate route.

## Content design

Add a coding chapter with:

- An implementation decision sequence: use supported Vulnerability Response integrations and configuration (including remediation task rules) before custom code.
- Short, illustrative JavaScript patterns explaining where logic belongs: import/transform customization, reusable server-side Script Includes, concise Business Rules, server-side record access using `GlideRecordSecure` where ACL enforcement is required, asynchronous client/server calls through GlideAjax, and secured/versioned Scripted REST APIs when a custom endpoint is actually needed.
- Boundary notes that distinguish client-side and server-side APIs, keep secrets and authorization on the server, validate external inputs, avoid unnecessary queries/updates, and test mappings and replay/idempotency with representative scanner data.
- Links directly to official ServiceNow product documentation, API reference, developer learning material, and the CIS-VR exam blueprint. Keep links release-aware; readers must use docs matching their instance release and installed Vulnerability Response application.

Do not present invented Vulnerability Response table names, unsupported internals, or snippets as deploy-ready without the target instance's release/schema. Clearly identify examples as patterns and direct readers to the release-matched dictionary and API documentation before using them.

## Existing page and boundaries

- Modify `findtorontoevents.ca/CIS-VR/index.html`, preserving its current standalone HTML/CSS structure, accessible navigation, official learning references, and independence disclaimer.
- Update the page table of contents and section numbering consistently when adding the coding chapter.
- Do not change unrelated application pages, build configuration, or deployment workflows.

## Validation

The change is documentation/content in a standalone HTML page. Validate that HTML structure is coherent, fragment links resolve to existing section IDs, and outbound ServiceNow links use HTTPS and point to official `servicenow.com` or `developer.servicenow.com` properties. Run the repository HTML inline-script syntax validator only if the target page contains inline scripts; otherwise no build is needed.

## Scope check

This is one focused update to an existing study page. The coding examples are educational patterns, not a production ServiceNow application or a certification substitute.
