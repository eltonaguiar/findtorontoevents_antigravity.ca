# 2026-11-19 — Initial ITOM knowledge base

**Agent:** Kilo (deepseek-flash) · **Repository:** ServiceNowLearning_ITOM

## What was built

A source-backed ITOM field guide with:

- 11 module guides covering ITOM Visibility, AIOps, Cloud Accelerate, ACC, Metric Intelligence,
  AI, and the specialist Visibility suite.
- 10 reference/methodology docs.
- 7 getting-started pages.
- 5 labs with design-only paths.
- A Jekyll site using the existing module-guide design language.
- `data/modules.json` and `data/sources.json`.
- Research protocol artifacts.
- A lint script and two GitHub Actions workflows.

## Why

The repository was empty. The existing ServiceNow learning repositories had methodology and
module guides, but no current, coherent ITOM family guide. This build fills that gap and is
structured for a later merge into the new ITOM section.

## Sources

Official ServiceNow documentation only, pinned to the **Australia** release and read on
**2026-11-19**. Every guide links its sources. No documentation pages are mirrored. See
`research/02_SOURCE_MATRIX.md`.

## Verification

See `research/04_VERIFICATION.md` for lint results, deployment status, and known limitations.

## How to check

```bash
python3 scripts/sn_lint.py
```

Then open the Pages site and walk one track (for example, Discovery start → Lab 01 → quiz).
