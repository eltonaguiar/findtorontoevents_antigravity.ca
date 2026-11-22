# Plan: Fix malformed Markdown tables on EBOND lab 03 + redeploy GitHub Pages

**Target repo:** `eltonaguiar/EBOND_ServiceNowSalesforce`
**Live URL:** https://eltonaguiar.github.io/EBOND_ServiceNowSalesforce/labs/03-snow-to-salesforce/
**Delivery:** new branch + PR (user merges; Pages redeploys on merge)
**Date:** 2026-11-22

## Problem

Tables render as run-on paragraphs because the Markdown table was pasted as a **single line**: header,
separator, and every data row joined with ` | ` and no newlines. GFM needs one row per line. Example
(the OAuth Grant type table) currently looks like:

```
| Option | What it does | Use it for this lab? | |---|---|---| | **Authorization Code** | ... | No — interactive user login | | ...
```

## Scope

- Fix every collapsed/malformed table on lab 03, not only the Grant Type table shown.
- Sweep the whole repo for the same collapse defect (other labs likely share the paste).
- Only touch table formatting; no content rewrites.

## Root-cause detection

A malformed table line matches: a line containing multiple `|---|` separator fragments and/or more than
one header-separator inside a single physical line. Regex used to find candidates:

```
^.*\|[-: ]{3,}\|.*\|[-: ]{3,}\|
```

plus lines where the count of `| ` occurrences is high but the file has no blank-line-separated row block.

## Steps

1. **Locate/obtain source.**
   - The repo is not in the current workspace; clone it into a scratch dir (e.g. `/tmp/EBOND` or a
     sibling folder), or confirm the user has an existing local clone to use.
   - Confirm auth: `gh auth status` or a configured PAT; needed for push + PR.

2. **Understand build/output.**
   - Inspect repo root: `README`, `_config.yml`, `mkdocs.yml`, `package.json`, `.github/workflows/`.
   - Identify whether `labs/03-snow-to-salesforce/` is:
     - (a) Markdown rendered by GitHub Pages/Jekyll → fix the `.md` source; Pages rebuilds on merge.
     - (b) Pre-built HTML checked in (`docs/` or `gh-pages` branch) → must regenerate/rebuild and commit
       the built HTML too.
   - Identify which branch feeds Pages (Settings → Pages source: `main` + `/docs`, `gh-pages`, or Actions).

3. **Find all malformed tables.**
   - Run the regex across `*.md` (and built `*.html` if tables are hardcoded) and list every offending
     line/table.

4. **Reformat each table.**
   - Split each run-on line into: header row, separator row (`|---|---|---|`), one line per data row.
   - Preserve cell text exactly (keep `**bold**`, emoji, em-dashes).
   - For very wide tables (>4 cols) consider the same-row layout is fine; do not restructure semantics.

5. **Regenerate built output (if applicable).**
   - If site is built (mkdocs/Jekyll/Node), run the documented build so served HTML matches the Markdown.
   - If tables are hand-written in HTML, apply the equivalent `<table>` fix.

6. **Verify locally.**
   - Preview render (e.g. `npx marked`, `pandoc`, or the project's local server) and confirm each table
     produces `<table>/<tr>/<td>` — not a single `<p>`.
   - Diff review: only table lines changed.

7. **Commit + PR.**
   - Create branch e.g. `fix/lab03-table-formatting`.
   - Commit only the changed lab/table files (respect "push only your own changes").
   - Push and open PR against the Pages source branch; include a before/after and list of labs fixed.
   - Do NOT force-push or touch unrelated branches.

8. **Verify deploy.**
   - After merge, watch the Pages build (Actions run or pages build) to success.
   - Fetch the live URL and confirm tables render (grep the HTML for `<table>` count on lab 03).

9. **Document.**
   - Add a short note (PR body and/or `updates/`-style `.md` in target repo if it follows that convention)
     describing what was broken, what changed, and the live verification.

## Risks / notes

- If Pages source is `gh-pages` branch (generated), the fix must land in the *source* markdown and be
  rebuilt — editing `gh-pages` directly will be overwritten.
- Wide tables on narrow screens may still scroll; that's CSS, not markdown — out of scope unless requested.
- Must not push commits authored by others; keep the branch limited to table-formatting changes.

## Definition of done

- Every table on lab 03 renders as a real HTML table on the live URL.
- Repo-wide collapse defect fixed where present.
- PR opened; after merge, Pages build green and live page verified.
