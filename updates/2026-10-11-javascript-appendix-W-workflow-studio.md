# 2026-10-11 — Appendix W (Workflow Studio/Flows) + more verified API findings

## What was done

The full topic-indexer finished, producing an index of **160 English Zurich doc
bundles / 15,390 candidate topics** (`/tmp/sndocs/_topics_index.json`). From it
I ran a second curated harvest (19 more pages) targeting the two richest
scripting bundles I hadn't mined:

- **Zurich ServiceNow AI Platform Capabilities** (`zS6yb8e~gR8BPjeviYdV9g`)
- **Zurich Build workflows** (`0MvJg~UYByX0VxWLomI71w`)

plus API-Reference gaps (GlideDateTime, GlideElement, GlideSystem, GlideFilter —
some 40–60 KB each).

## New content added

### Appendix W — "Workflow Studio, Flows & Reusable Low-Code" (id `appendix-flowstudio`)

All doc-sourced (Zurich):

- **Flows vs Playbooks decision rule** — Flows: minimal/no user interaction,
  high volume ("hundreds or thousands of instances per second… especially when
  flow reporting is disabled"), few subflows. Playbooks: multiple manual user
  interactions, lower volume (they generate UI + store detailed execution
  data), many subflows.
- **Subflows** — verbatim docs: *"have no trigger and run only when called by a
  playbook, flow, another subflow, or a script"*; inputs + outputs; the
  "Script Include is to server JS what a subflow is to no-code" parallel.
- **Decision tables** — docs quote: separate decision logic from code so
  business SMEs maintain rules without code change.
- **Flow debugging/admin** — flow debugger, flow reporting overhead, priority
  / retention settings, domain-separation considerations.
- **Where custom code still belongs** table (Script Include / UI Script /
  Flow Action+Subflow / Decision Table / Scripted REST / Script Action).
- 5-question knowledge check.

### Appendix V additions — GlideElement & GlideFilter gotchas
- `changes()` — **not supported within ACL scripts**; not for Journal fields.
- `nil()` — correct null check.
- `getRefRecord()` — returns an **empty GlideRecord, not null**, for empty refs.
- `getReferenceTable()` — returns the reference's table name.
- `GlideFilter` — **case-sensitive by default** (vs case-insensitive GlideRecord
  queries) — a subtle mismatch when reusing a UI filter string.

TOC entry "W. Workflow Studio & Flows"; badge → "28 sections + 24-part appendix".

## Verification

- 53 TOC links resolve; 24 appendix sections; 23 knowledge-check blocks.
- Zero `pageerror` events locally and live.
- Live page carries `appendix-flowstudio`, the section heading, and the
  GlideFilter "case-sensitive by default" note.
- Deployed with `python3 upload_javascript.py`.

## Corpus status (in /tmp/sndocs — ephemeral)

- 1st harvest: 23 pages; 2nd harvest: 19 pages (42 total).
- `_topics_index.json` (160 bundles) + `_cands.json` (15,390 candidates).
- Remaining high-value unmined bundles if wanted: ServiceNow AI Platform
  Capabilities (548 scripting-relevant topics), Platform Analytics, Platform
  security, Workflow Data Fabric.

## Limits

- Pinned to **Zurich**. No copyrighted text bulk-copied (short quotes as
  citations). No personal/contact details added to the page.
