/**
 * Playwright investigation: SSR vs hydrated DOM diff for /audit/
 * Finds content that DISAPPEARS or gets HIDDEN after JS hydration.
 */

import { chromium } from 'playwright';
import { writeFileSync } from 'fs';
import https from 'https';

const TARGET_URL = 'https://findtorontoevents.ca/audit/';
const OUTPUT_JSON = '/home/eaguiar2015/findtorontoevents_antigravity.ca/reports/audit_removed_vs_hidden.json';

const KEY_PHRASES = [
  'TRUTH LAYER',
  'RAW is net-unprofitable',
  'FALSIFIED',
  'DATA QUALITY IMPROVEMENTS',
  'loading...',
  'no asset class currently passes',
];

// Fetch raw HTML without JS execution
function fetchRawHTML(url) {
  return new Promise((resolve, reject) => {
    https.get(url, { headers: { 'User-Agent': 'Mozilla/5.0 (compatible; AuditBot/1.0)' } }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve(data));
      res.on('error', reject);
    }).on('error', reject);
  });
}

// Extract text from HTML without executing JS (strip tags, normalize whitespace)
function extractTextFromHTML(html) {
  // Remove script tags and their content
  let text = html
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&nbsp;/g, ' ')
    .replace(/&#\d+;/g, ' ')
    .replace(/&[a-z]+;/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  return text;
}

// Split text into meaningful phrases (>30 chars)
function extractPhrases(text, minLen = 30) {
  // Split on common delimiters while preserving context
  const segments = text
    .split(/[|\n\r]+/)
    .map(s => s.trim())
    .filter(s => s.length >= minLen);

  // Also try splitting on periods/semicolons for sentence-level phrases
  const allPhrases = new Set();
  for (const seg of segments) {
    if (seg.length >= minLen) {
      allPhrases.add(seg);
    }
    // Sub-split on sentence boundaries
    const subSegs = seg.split(/[.;!?]+/).map(s => s.trim()).filter(s => s.length >= minLen);
    subSegs.forEach(s => allPhrases.add(s));
  }
  return Array.from(allPhrases);
}

async function main() {
  console.log('=== Audit Page SSR vs Hydrated DOM Diff ===\n');

  // Step 1: Fetch raw SSR HTML
  console.log('Step 1: Fetching raw SSR HTML (no JS)...');
  let rawHTML = '';
  try {
    rawHTML = await fetchRawHTML(TARGET_URL);
    console.log(`  Raw HTML fetched: ${rawHTML.length} bytes`);
  } catch (err) {
    console.error('  ERROR fetching raw HTML:', err.message);
  }

  const ssrText = extractTextFromHTML(rawHTML);
  const ssrPhrases = extractPhrases(ssrText);
  console.log(`  SSR text length: ${ssrText.length} chars`);
  console.log(`  SSR phrases extracted: ${ssrPhrases.length}`);

  // Step 2: Load with Playwright
  console.log('\nStep 2: Loading with Playwright (chromium, networkidle + 3s)...');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
  });
  const page = await context.newPage();

  const consoleErrors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(`[${msg.type()}] ${msg.text()}`);
    }
  });
  page.on('pageerror', err => {
    consoleErrors.push(`[pageerror] ${err.message}`);
  });

  try {
    await page.goto(TARGET_URL, { waitUntil: 'networkidle', timeout: 60000 });
  } catch (err) {
    console.log(`  Navigation warning (continuing): ${err.message}`);
  }

  // Extra 3s wait for deferred rendering
  await page.waitForTimeout(3000);

  // Step 3: Capture textContent (includes hidden) and innerText (visible only)
  console.log('\nStep 3: Capturing hydrated DOM text...');

  const [hydratedTextContent, hydratedInnerText] = await page.evaluate(() => {
    const tc = document.body ? document.body.textContent : '';
    const it = document.body ? document.body.innerText : '';
    return [tc, it];
  });

  const hydratedText = (hydratedTextContent || '').replace(/\s+/g, ' ').trim();
  const hydratedVisible = (hydratedInnerText || '').replace(/\s+/g, ' ').trim();

  console.log(`  Hydrated textContent length: ${hydratedText.length} chars`);
  console.log(`  Hydrated innerText (visible) length: ${hydratedVisible.length} chars`);

  // Step 4: Diff analysis
  console.log('\nStep 4: Diffing SSR vs hydrated...');

  const removed = [];
  const hidden = [];

  for (const phrase of ssrPhrases) {
    const inDom = hydratedText.includes(phrase);
    const inVisible = hydratedVisible.includes(phrase);
    if (!inDom) {
      removed.push(phrase);
    } else if (!inVisible) {
      hidden.push(phrase);
    }
  }

  console.log(`  REMOVED (not in DOM at all): ${removed.length} phrases`);
  console.log(`  HIDDEN (in DOM but not visible): ${hidden.length} phrases`);

  // Step 5: Key phrase status
  console.log('\nStep 5: Key phrase status:');
  const keyPhraseStatus = {};
  for (const phrase of KEY_PHRASES) {
    const inSSR = ssrText.toLowerCase().includes(phrase.toLowerCase());
    const inDom = hydratedText.toLowerCase().includes(phrase.toLowerCase());
    const inVisible = hydratedVisible.toLowerCase().includes(phrase.toLowerCase());

    let status;
    if (!inSSR && !inDom) status = 'NOT_IN_SSR_OR_DOM';
    else if (!inSSR && inDom) status = 'ADDED_BY_JS';
    else if (inSSR && !inDom) status = 'REMOVED';
    else if (inSSR && inDom && !inVisible) status = 'HIDDEN';
    else if (inSSR && inDom && inVisible) status = 'VISIBLE';
    else status = 'UNKNOWN';

    keyPhraseStatus[phrase] = { inSSR, inDom, inVisible, status };
    const icon = status === 'VISIBLE' ? '✓' : status === 'REMOVED' ? '✗ REMOVED' : status === 'HIDDEN' ? '~ HIDDEN' : status === 'ADDED_BY_JS' ? '+ JS-ADDED' : '? ' + status;
    console.log(`  "${phrase}" → ${icon}`);
  }

  // Console errors summary
  console.log(`\nConsole errors: ${consoleErrors.length}`);
  if (consoleErrors.length > 0) {
    consoleErrors.slice(0, 10).forEach(e => console.log(`  ${e}`));
    if (consoleErrors.length > 10) console.log(`  ... and ${consoleErrors.length - 10} more`);
  }

  // Sample removed phrases
  if (removed.length > 0) {
    console.log('\nSample REMOVED phrases (up to 10):');
    removed.slice(0, 10).forEach(p => console.log(`  - "${p.substring(0, 80)}${p.length > 80 ? '...' : ''}"`));
  }

  if (hidden.length > 0) {
    console.log('\nSample HIDDEN phrases (up to 10):');
    hidden.slice(0, 10).forEach(p => console.log(`  - "${p.substring(0, 80)}${p.length > 80 ? '...' : ''}"`));
  }

  await browser.close();

  // Build output JSON
  const output = {
    timestamp: new Date().toISOString(),
    url: TARGET_URL,
    ssrStats: {
      htmlBytes: rawHTML.length,
      textLength: ssrText.length,
      phrasesExtracted: ssrPhrases.length,
    },
    hydratedStats: {
      textContentLength: hydratedText.length,
      innerTextLength: hydratedVisible.length,
    },
    removed: removed.slice(0, 100),  // cap at 100 for sanity
    hidden: hidden.slice(0, 100),
    consoleErrors,
    keyPhrases: keyPhraseStatus,
    allRemovedCount: removed.length,
    allHiddenCount: hidden.length,
  };

  writeFileSync(OUTPUT_JSON, JSON.stringify(output, null, 2));
  console.log(`\nFull JSON saved to: ${OUTPUT_JSON}`);
  console.log('\n=== DONE ===');
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
