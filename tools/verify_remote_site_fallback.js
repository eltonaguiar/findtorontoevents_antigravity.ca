#!/usr/bin/env node
/**
 * Fallback remote site verification (no Playwright).
 * Use when Playwright is unavailable or fails. Performs HTTP checks only:
 * - Homepage 200 and HTML contains expected structure
 * - Main chunk 200 and returns JavaScript (not HTML/ModSecurity)
 * - events.json 200 and returns JSON with events length > 0
 *
 * Environment:
 *   VERIFY_REMOTE_URL  Base URL (default https://findtorontoevents.ca)
 *   FTP_SERVER, FTP_USER, FTP_PASS  Not used by this script; see .cursor/rules for deploy
 *
 * Usage: node tools/verify_remote_site_fallback.js
 */

const BASE =
  (process.env.VERIFY_REMOTE_URL || 'https://findtorontoevents.ca').replace(
    /\/$/,
    ''
  );
const CHUNK_PATH = '/next/_next/static/chunks/a2ac3a6616d60872.js';
const EVENTS_JSON_PATH = '/next/events.json';

async function fetchText(url, opts = {}) {
  const res = await fetch(url, {
    ...opts,
    headers: { 'User-Agent': 'findtorontoevents-verify/1' },
  });
  return { ok: res.ok, status: res.status, text: await res.text(), url };
}

async function main() {
  const failures = [];
  let passed = 0;

  // 1. Homepage
  const index = await fetchText(BASE + '/');
  if (!index.ok) {
    failures.push(`Homepage: ${index.status} ${index.url}`);
  } else {
    if (
      !index.text.includes('events-grid') &&
      !index.text.includes('id="events-grid"')
    ) {
      failures.push('Homepage: missing #events-grid in HTML');
    } else if (!index.text.includes('/next/_next/static/chunks/')) {
      failures.push('Homepage: missing chunk references in HTML');
    } else {
      passed++;
    }
  }

  // 2. Main chunk
  const chunk = await fetchText(BASE + CHUNK_PATH);
  if (!chunk.ok) {
    failures.push(`Chunk: ${chunk.status} ${chunk.url}`);
  } else {
    const isJs =
      chunk.text.includes('TURBOPACK') || chunk.text.includes('(function');
    const isBad =
      chunk.text.startsWith('<!') ||
      chunk.text.toLowerCase().includes('denied by modsecurity');
    if (!isJs || isBad) {
      failures.push(
        'Chunk: response is not valid JS (HTML or ModSecurity block?)'
      );
    } else {
      passed++;
    }
  }

  // 3. events.json
  const eventsUrl = BASE + EVENTS_JSON_PATH;
  const eventsRes = await fetchText(eventsUrl);
  if (!eventsRes.ok) {
    failures.push(`events.json: ${eventsRes.status} ${eventsUrl}`);
  } else {
    let data;
    try {
      data = JSON.parse(eventsRes.text);
    } catch (e) {
      failures.push('events.json: invalid JSON');
    }
    if (data) {
      const list = Array.isArray(data) ? data : data.events || data.data || [];
      if (list.length === 0) {
        failures.push('events.json: zero events (array empty or missing)');
      } else {
        passed++;
      }
    }
  }

  // Report
  const total = 3;
  if (failures.length) {
    console.error('Remote verification (fallback) FAILED:');
    failures.forEach((f) => console.error('  -', f));
    process.exit(1);
  }
  console.log(
    `Remote verification (fallback) passed: ${passed}/${total} checks (${BASE})`
  );
  process.exit(0);
}

main().catch((err) => {
  console.error('Verify failed:', err.message);
  process.exit(1);
});
