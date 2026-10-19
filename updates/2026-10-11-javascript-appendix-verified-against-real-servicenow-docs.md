# 2026-10-11 — Appendix T/U corrected against REAL ServiceNow docs (research breakthrough)

## The breakthrough

Previous attempts to scrape `docs.servicenow.com` failed (JS-only FluidTopics
SPA; headless browser returned only "Loading application..."). This session
cracked it:

**The docs site is a FluidTopics Knowledge Hub app with an open JSON API.**

- `GET /api/khub/maps` → all doc bundles (1,489 maps).
- `GET /api/khub/maps/{mapId}/topics` → every page in a bundle.
- `GET /api/khub/maps/{mapId}/topics/{topicId}/content` → the real page HTML.

Used the **English Zurich** bundles:
- Platform Administration map `7LhbZn3yz3Q58qhjZoU9iQ`
- API Reference map `MVRCUFVyKWd7vUoUukbW6g`

Saved the method as a skill: `research/servicenow-docs-api`.

## What the real docs corrected (my earlier appendix was wrong/invented)

| My earlier claim | What the Zurich docs actually say | Fixed |
|---|---|---|
| "There is no GlideRecord in client scope" (impossible) | **GlideRecord – Client EXISTS.** It is **not supported in scoped applications**; queries run on the server; it **applies ACLs** of the executing user. Docs: "Instead, create a script include and use the GlideAjax API, or use the REST APIs." | ✅ all 3 occurrences |
| UI Scripts have an "on-demand/deferred" mode | UI Scripts have only a **Global** toggle. Global = "loads on every page in the system" (docs warn it *impacts performance*); **cannot be global in a scoped app**; **not supported on mobile or Next Experience**. Called via `g_ui_scripts` / `.jsdbx`. | ✅ |
| (not stated) | **GlideAjax preferred method is `getXML()`** (async); `getXMLWait()` is discouraged and unavailable to scoped apps. | ✅ noted |
| "business rule where flow fits" (vague) | Docs: business rules are a **"classic automation solution"** — *"Use Workflow Studio for any new process automation."* | ✅ quoted |
| Instance Scan "baseline suites (Scripting/Security/…)" | Real check **types**: Table Check, Column Type Check, Script Only Check, **Linter Check** (generates an AST). Real **scan types**: Full, Point, Test. **Role: `scan_user`**. **Limited domain-separation support.** | ✅ |

## What was added / corrected in the page

`findtorontoevents.ca/servicenow/javascript/index.html` — Appendices R, T, U:

1. **Appendix T — UI Scripts section rewritten** with the real field semantics
   (Global = every page; scoped-app/mobile/Next Experience limits; how it's
   called), plus a new **"Client-side GlideRecord — supported, but know the
   limits"** block.
2. **Appendix T — Instance Scan rebuilt** with the four real check types
   (incl. **Linter Check**), the Full/Point/Test scan types, the **quota rule**,
   the **`scan_user`** role, and the **domain-separation caveat**.
3. **Appendix U — anti-pattern rows corrected**: client-side GlideRecord (scoped
   exception), new-business-rule guidance (Workflow Studio quote), and the
   global-UI-Script row.
4. **Appendix R (L6) — GlideAjax note** updated to prefer `getXML()` and warn
   about `getXMLWait()`; "client query (impossible)" row fixed.
5. **Knowledge-check answers** corrected in three places (no more "no
   GlideRecord in client scope" / "on-demand UI Scripts").
6. Added a **"Sources — verified against official ServiceNow docs (Zurich)"**
   callout listing the exact doc pages.

## Verification

- 51 TOC links resolve; 22 appendix sections; 21 knowledge checks.
- Zero `pageerror` events (local + live).
- Grep checks: `on-demand UI Scripts` → **0** occurrences (bad claim gone);
  `scan_user`, `Linter Check`, `GlideRecord – Client` present.
- Live page after `python3 upload_javascript.py` carries the corrections
  (4 doc-verified strings present; 0 of the old bad claim).

## Artifacts

- Local doc dumps saved: `/tmp/sn_ui_scripts.txt`, `/tmp/sn_gliderecord_client.txt`,
  `/tmp/sn_is_check_types.txt`, `/tmp/sn_data_policy.txt`,
  `/tmp/sn_assignment_rules.txt`, `/tmp/sn_classic_br.txt`, etc.
- Skill: `~/.hermes/skills/research/servicenow-docs-api/SKILL.md`

## Remaining currency caveat

Facts are pinned to the **Zurich** release (the docs' current default). ServiceNow
ships twice a year; menu labels and a few properties can shift. The cited method
(the khub API) lets any future pass re-verify quickly against a newer release.
