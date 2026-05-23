---
name: full-page-test
description: Fully test a page using Playwright and Node.js—crawl all navigation paths, check every link for HTTP errors, verify zero JavaScript errors on every page, and report broken routes. Use when the user asks to test a page, run a full site test, check all links, verify no JS errors across pages, or do a comprehensive page audit.
---

# Full Page Test

Use this skill when the user asks to **fully test a page**, **test all navigation paths**, **check for broken links**, **verify no JS errors site-wide**, **run a comprehensive page audit**, or **crawl and test all routes**.

## What it does

1. **Crawls** all internal links starting from a base URL (homepage by default)
2. **Visits each unique page** with Playwright (real browser)
3. **Collects JS errors** on every page (SyntaxError, TypeError, ReferenceError, uncaught exceptions, console errors)
4. **Checks HTTP status** of every navigated page (detects 404s, 500s, blocked resources)
5. **Verifies key elements** render on each page (no blank pages)
6. **Reports** a pass/fail summary with details per URL

## Quick start

### Option A: Playwright spec (recommended)

```bash
npx playwright test tests/full_page_test.spec.ts --project="Desktop Chrome"
```

Or test against the remote site:

```bash
VERIFY_REMOTE=1 npx playwright test tests/full_page_test.spec.ts --project="Desktop Chrome"
```

### Option B: Standalone Node.js runner (no Playwright config needed)

```bash
node .cursor/skills/full-page-test/scripts/run-full-page-test.js
```

With options:

```bash
node .cursor/skills/full-page-test/scripts/run-full-page-test.js --url https://findtorontoevents.ca --depth 2 --timeout 30000
```

## Configuration

| Env / Flag | Default | Description |
|---|---|---|
| `FULL_TEST_URL` | `http://localhost:5173` | Base URL to crawl |
| `FULL_TEST_DEPTH` | `2` | Max link-follow depth (0 = homepage only) |
| `FULL_TEST_TIMEOUT` | `15000` | Per-page navigation timeout (ms) |
| `FULL_TEST_SAME_ORIGIN` | `true` | Only follow same-origin links |
| `FULL_TEST_IGNORE` | (empty) | Comma-separated URL substrings to skip |

## How it works

### Phase 1: Discover links
- Load the base URL, extract all `<a href="...">` links
- Filter to same-origin internal links (unless `FULL_TEST_SAME_ORIGIN=false`)
- Normalize and deduplicate URLs
- Skip anchors (`#`-only), `mailto:`, `tel:`, `javascript:` links

### Phase 2: Visit each page
For each discovered URL (breadth-first up to `FULL_TEST_DEPTH`):
1. Navigate with Playwright (`waitUntil: 'networkidle'` with timeout fallback to `'domcontentloaded'`)
2. Collect all `pageerror` events and critical `console.error` messages
3. Check HTTP response status
4. Verify `document.body` has content (not blank)
5. Discover new links on this page (if depth allows)

### Phase 3: Report
- **PASS**: All pages returned 2xx, zero JS errors, all pages rendered content
- **FAIL**: Lists each failing URL with: HTTP status, JS errors, blank page flag

### JS error patterns detected
- `SyntaxError` / `Unexpected token`
- `ReferenceError` / `TypeError`
- `ChunkLoadError` / `Loading chunk`
- `denied by modsecurity`
- Any uncaught exception via `pageerror` event

### Ignored (not failures)
- React hydration mismatch (`#418`)
- Third-party script errors (Google Analytics, ad scripts)
- `favicon.ico` 404

## Integration with existing tests

This skill complements the existing `no_js_errors.spec.ts` (single page) and `verify_remote_site.spec.ts` (remote homepage). Use **full-page-test** when you need to verify **all navigation paths**, not just the homepage.

## When a test fails

| Failure | Likely cause | Fix |
|---|---|---|
| JS error on homepage | Chunk not serving JS | Use **fix-toronto-events** skill |
| 404 on a nav link | Broken link in index.html or Quick Nav | Use **fix-nav-menu** skill; verify link href |
| Blank page on sub-route | Missing HTML or server misconfiguration | Check that the path exists on server / in local files |
| JS error on sub-page only | Page-specific script issue | Inspect the error; check the sub-page's own JS |
| Timeout on a page | Slow server or infinite redirect | Increase `FULL_TEST_TIMEOUT`; check for redirect loops |

## Files

- **Playwright spec:** `tests/full_page_test.spec.ts`
- **Standalone runner:** `.cursor/skills/full-page-test/scripts/run-full-page-test.js`
- **Reference docs:** [reference.md](reference.md)
