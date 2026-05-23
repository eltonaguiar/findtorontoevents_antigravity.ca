# Full Page Test — Reference

## Architecture

```
tests/full_page_test.spec.ts          ← Playwright spec (integrates with playwright.config.ts)
.cursor/skills/full-page-test/
├── SKILL.md                          ← Skill instructions
├── reference.md                      ← This file
└── scripts/
    └── run-full-page-test.js         ← Standalone Node.js runner
```

## How the crawler works

1. **BFS (breadth-first search)** starting from the base URL
2. At each page, Playwright navigates with `waitUntil: 'networkidle'` (with `domcontentloaded` fallback)
3. Two event listeners capture JS errors:
   - `pageerror` — catches uncaught exceptions thrown by page scripts
   - `console` event with `type === 'error'` — catches `console.error()` from page scripts
4. After the page loads, the crawler extracts all `<a href="...">` links
5. Links are normalized (protocol, host, path — hash stripped) and deduplicated
6. Same-origin links (by default) are queued for the next depth level
7. The crawl continues BFS until `MAX_DEPTH` is reached or no new links are found

## JS error detection

### Critical patterns (cause test failure)

| Pattern | What it catches |
|---|---|
| `SyntaxError` | Invalid JS syntax — usually chunk served as HTML |
| `Unexpected token` | Same as above (variant message) |
| `ChunkLoadError` | Webpack/Turbopack chunk failed to load |
| `Loading chunk` | Same (variant) |
| `denied by modsecurity` | Server WAF blocking JS file |
| `ReferenceError` | Undefined variable |
| `TypeError` | Null/undefined property access |
| `Uncaught ` | Generic uncaught exception prefix |
| `EvalError` | Eval failures |
| `URIError` | Malformed URI |
| `InternalError` | Engine-level error (e.g. stack overflow) |

### Ignored patterns (not failures)

| Pattern | Why ignored |
|---|---|
| `Minified React error #418` | Hydration mismatch — common in static export |
| `favicon.ico` | Missing favicon is not a JS error |
| `google analytics / gtag` | Third-party script noise |
| `ResizeObserver loop` | Browser quirk, not a real error |
| `Non-Error promise rejection` | Vague; usually third-party |

## Environment variables

| Variable | Type | Default | Description |
|---|---|---|---|
| `FULL_TEST_URL` | string | `http://localhost:5173` | Base URL to crawl |
| `FULL_TEST_DEPTH` | int | `2` | Max link-follow depth |
| `FULL_TEST_TIMEOUT` | int (ms) | `15000` | Per-page navigation timeout |
| `FULL_TEST_SAME_ORIGIN` | bool | `true` | Only follow same-origin links |
| `FULL_TEST_IGNORE` | string | (empty) | Comma-separated URL substrings to skip |
| `VERIFY_REMOTE` | `1`/`true` | (unset) | Use remote URL instead of localhost |
| `VERIFY_REMOTE_URL` | string | `https://findtorontoevents.ca` | Remote URL (when VERIFY_REMOTE=1) |

## CLI options (standalone runner only)

| Flag | Description |
|---|---|
| `--url <url>` | Base URL |
| `--depth <n>` | Max depth |
| `--timeout <ms>` | Per-page timeout |
| `--no-same-origin` | Follow cross-origin links |
| `--ignore <patterns>` | URL substrings to skip |
| `--headless false` | Run with visible browser |
| `--browser <name>` | `chromium`, `firefox`, or `webkit` |
| `--json` | Output as JSON |
| `--output <file>` | Save report to file |

## Example output

```
Full Page Test
URL: http://localhost:5173
Depth: 2 | Timeout: 15000ms | Same-origin: true
Browser: chromium | Headless: true

[1] [depth=0] http://localhost:5173/ ... HTTP:✅200 JS:✅ 3421ms links:18
[2] [depth=1] http://localhost:5173/WINDOWSFIXER/ ... HTTP:✅200 JS:✅ 1523ms links:4
[3] [depth=1] http://localhost:5173/MENTALHEALTHRESOURCES/ ... HTTP:✅200 JS:✅ 1102ms links:2
[4] [depth=1] http://localhost:5173/findstocks ... HTTP:✅200 JS:✅ 2201ms links:6
[5] [depth=1] http://localhost:5173/MOVIESHOWS/ ... HTTP:✅200 JS:✅ 1890ms links:12
[6] [depth=1] http://localhost:5173/fc/ ... HTTP:✅200 JS:✅ 2100ms links:5
[7] [depth=1] http://localhost:5173/vr/ ... HTTP:✅200 JS:✅ 1455ms links:8

======================================================================
FULL PAGE TEST REPORT
Base: http://localhost:5173 | Depth: 2 | Same-origin: true
======================================================================
Total pages: 7
Passed: 7
Failed: 0
======================================================================

✅ ALL PAGES PASSED
======================================================================
```

## Integration notes

- The Playwright spec uses the same `playwright.config.ts` as other tests (webServer, projects, etc.)
- The standalone runner is self-contained — it launches its own browser and needs no config
- Both tools use the same crawl logic and error detection patterns
- The spec is registered in `playwright.config.ts` so it runs with `npx playwright test`
- NPM script `test:full-page` runs the spec with Desktop Chrome project

## Troubleshooting

| Issue | Solution |
|---|---|
| Test times out | Increase `FULL_TEST_TIMEOUT` or reduce `FULL_TEST_DEPTH` |
| Too many pages crawled | Use `FULL_TEST_IGNORE` to skip paths, or reduce depth |
| False positive JS error | Add pattern to `IGNORE_ERROR_PATTERNS` in the spec |
| Standalone runner can't find Playwright | Run `npx playwright install chromium` first |
| Pages return 403/blocked | Server may block automated requests; check User-Agent |
