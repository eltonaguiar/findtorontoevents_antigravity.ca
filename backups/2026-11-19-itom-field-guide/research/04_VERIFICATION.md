# 04 — Verification

**Agent:** Kilo (deepseek-flash) · **Date:** 2026-11-19 · **Release:** Australia

Everything below was run from this build environment or observed on the deployed site.

---

## 1. Content lint

```text
$ python3 scripts/sn_lint.py
checked 34 docs · 0 errors · 0 warnings
```

The lint checks:

- H1 title, `**Agent:**` stamp, and `**Updated:** YYYY-MM-DD` on every published doc.
- An `## Official sources` section with at least one URL, all on the ServiceNow allowlist.
- No `TODO`, `TBD`, `FIXME`, or `XXX`.
- Every relative link resolves on disk.
- `data/modules.json`: valid JSON, unique ids, required keys, labs exist, official docs URLs.
- `data/sources.json`: allowlist present, per-module URLs allowed.
- Every navigation target in `_layouts/default.html` resolves to a source file.

## 2. Data validation

```text
$ python3 -c "import json;json.load(open('data/modules.json'));print('valid')"
valid
$ python3 -c "import json;json.load(open('data/sources.json'));print('valid')"
valid
```

11 modules, unique ids, each with records, roles, breadcrumbs, mistakes, quiz, and timebox.

## 3. Official URL verification

All 71 `www.servicenow.com/docs/...` URLs used in the repository were matched against the
official Australia ITOM topic map:

```text
total 71 unverified 0
```

This means every deep link used is a real topic in the release map, not a guessed path.

## 4. GitHub Actions

| Run | Workflow | Commit | Result |
|---|---|---|---|
| [44452052693](https://github.com/eltonaguiar/ServiceNowLearning_ITOM/actions/runs/44452052693) | Content checks | `f4e4b62` | success |
| [44452052807](https://github.com/eltonaguiar/ServiceNowLearning_ITOM/actions/runs/44452052807) | Deploy to GitHub Pages | `f4e4b62` | success |
| [44452279435](https://github.com/eltonaguiar/ServiceNowLearning_ITOM/actions/runs/44452279435) | Content checks | `5799caf` | success |
| [44452279467](https://github.com/eltonaguiar/ServiceNowLearning_ITOM/actions/runs/44452279467) | Deploy to GitHub Pages | `5799caf` | success |

## 5. Deployed site

URL: <https://eltonaguiar.github.io/ServiceNowLearning_ITOM/>

HTTP checks:

| Path | Status | Size |
|---|---|---|
| `/` | 200 | 27,517 bytes |
| `/docs/modules/discovery/discovery-guide/` | 200 | 44,338 bytes |
| `/docs/modules/event-management/event-management-guide/` | 200 | 48,847 bytes |
| `/labs/LAB-02-EVENT-TO-INCIDENT/` | 200 | 30,861 bytes |
| `/docs/getting-started/` | 200 | 21,554 bytes |
| `/assets/css/style.css` | 200 | 14,096 bytes |
| `/assets/js/site.js` | 200 | 4,334 bytes |

### Link crawl

A recursive crawl of internal links from the home page:

```text
checked 47 bad 0
```

No broken internal pages or assets within the crawl scope.

### Browser render check

Chromium (Playwright) loaded the home page, the Discovery guide, and the Event Management guide:

| Page | Mermaid SVGs | TOC links | Nav groups | Horizontal overflow |
|---|---|---|---|---|
| Home | 1 | 12 | 8 | none |
| Discovery | 1 | 28 | 8 | none |
| Event Management | 1 | 27 | 8 | none |

Console errors after the Mermaid fix: **0**.

### Issue found and fixed

The first deployment had a console `PAGEERROR: Object` on each page. The Mermaid diagrams still
rendered, but the deprecated `mermaid.init(...)` call rejected with a non-Error object. The layout
was changed to the Mermaid 10 `mermaid.run({ nodes })` API, redeployed, and rechecked:

```text
before: CONSOLE_ERRORS ["PAGEERROR: Object","PAGEERROR: Object","PAGEERROR: Object"]
after:  CONSOLE_ERRORS []
```

This is exactly why the verification includes a browser, not only an HTTP 200.

## 6. Known limitations

- **Release drift:** content is pinned to the Australia release. A new family release may move
  deep links and change form labels. Re-run the source matrix and the labs.
- **Instance variance:** menu labels, some table display names, and role names can differ by
  installed Store app version. The guides say "verify in the dictionary" where this matters.
- **PDI entitlements:** several products (Event Management, Service Mapping, HLA, Cloud
  Accelerate, ACC, Metric Intelligence) require entitlements a PDI may not have. Every lab has a
  design-only path.
- **AI area:** the Australia-era AI packaging is moving. The governance model is durable; the
  feature list is not.
- **No certification claims:** the guide points to Now Learning but does not claim an exam
  blueprint.
- **No pricing:** the guide explains entitlement models but does not quote prices or contracts.
- **Source access:** the official docs site is a client-rendered application; the research pass
  read individual topic pages for the Australia release. The repo stores paraphrases and links,
  not documentation pages.

## 7. Reproduce

```bash
git clone https://github.com/eltonaguiar/ServiceNowLearning_ITOM.git
cd ServiceNowLearning_ITOM
python3 scripts/sn_lint.py
```

Then open the Pages URL and walk one track:

1. Home → Getting started → Discovery start.
2. Discovery guide → Lab 01.
3. Event Management guide → Lab 02.
4. Check the quiz answers without looking.

---

**Agent:** Kilo (deepseek-flash) · **Updated:** 2026-11-19
