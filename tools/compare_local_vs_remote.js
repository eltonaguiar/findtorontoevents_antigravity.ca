#!/usr/bin/env node
/**
 * Cross-compare local site (after local verification) vs remote site.
 * Use when local verified passed and you're ready to deploy: detect if remote
 * is missing chunks, has different index/chunk content, or stale data.
 *
 * Environment:
 *   LOCAL_BASE   Local site URL (default http://localhost:9000)
 *   REMOTE_BASE  Remote site URL (default https://findtorontoevents.ca)
 *
 * Prerequisite: Local server running (e.g. python tools/serve_local.py).
 *
 * Usage: node tools/compare_local_vs_remote.js
 */

const LOCAL_BASE = (process.env.LOCAL_BASE || 'http://localhost:9000').replace(
  /\/$/,
  ''
);
const REMOTE_BASE = (
  process.env.REMOTE_BASE ||
  process.env.VERIFY_REMOTE_URL ||
  'https://findtorontoevents.ca'
).replace(/\/$/, '');

const CHUNKS_REGEX = /\/next\/_next\/static\/chunks\/([a-zA-Z0-9_-]+\.js)(?:\?[^"'\s]*)?/g;
const MAIN_CHUNK = 'a2ac3a6616d60872.js';
const EVENTS_JSON_PATH = '/next/events.json';

async function fetchText(url, opts = {}) {
  try {
    const res = await fetch(url, {
      ...opts,
      headers: { 'User-Agent': 'findtorontoevents-compare/1' },
    });
    return { ok: res.ok, status: res.status, text: await res.text(), url };
  } catch (e) {
    return { ok: false, status: 0, text: '', url, error: e.message };
  }
}

function extractChunkIds(html) {
  const ids = new Set();
  let m;
  CHUNKS_REGEX.lastIndex = 0;
  while ((m = CHUNKS_REGEX.exec(html)) !== null) ids.add(m[1]);
  return ids;
}

function shortHash(text) {
  if (!text || text.length === 0) return 'empty';
  const len = text.length;
  const sample =
    text.slice(0, 200) + (len > 400 ? text.slice(len - 200) : '');
  let h = 0;
  for (let i = 0; i < sample.length; i++)
    h = (Math.imul(31, h) + sample.charCodeAt(i)) | 0;
  return len + '-' + (h >>> 0).toString(36);
}

async function main() {
  const warnings = [];
  const errors = [];
  const notes = [];

  console.log('Cross-comparison: local vs remote');
  console.log('  Local:  ' + LOCAL_BASE);
  console.log('  Remote: ' + REMOTE_BASE);
  console.log('');

  // --- Index: fetch both ---
  const [localIndex, remoteIndex] = await Promise.all([
    fetchText(LOCAL_BASE + '/'),
    fetchText(REMOTE_BASE + '/'),
  ]);

  if (!localIndex.ok) {
    const msg = localIndex.error
      ? 'Local index unreachable: ' + localIndex.error + ' (' + LOCAL_BASE + '/). Start local server: python tools/serve_local.py'
      : 'Local index: ' + localIndex.status + ' (' + LOCAL_BASE + '/). Start local server: python tools/serve_local.py';
    errors.push(msg);
    report(errors, warnings, notes);
    process.exit(1);
  }

  if (!remoteIndex.ok) {
    const msg = remoteIndex.error
      ? 'Remote index unreachable: ' + remoteIndex.error + ' (' + REMOTE_BASE + '/)'
      : 'Remote index: ' + remoteIndex.status + ' (' + REMOTE_BASE + '/)';
    errors.push(msg);
    report(errors, warnings, notes);
    process.exit(1);
  }

  notes.push('Both index pages returned 200.');

  // --- Chunk list from index ---
  const localChunks = extractChunkIds(localIndex.text);
  const remoteChunks = extractChunkIds(remoteIndex.text);

  const onlyLocal = [...localChunks].filter((id) => !remoteChunks.has(id));
  const onlyRemote = [...remoteChunks].filter((id) => !localChunks.has(id));

  if (onlyLocal.length > 0) {
    errors.push(
      'Remote is missing chunk(s) that local has: ' + onlyLocal.join(', ')
    );
  }
  if (onlyRemote.length > 0) {
    notes.push(
      'Remote has extra chunk(s) not in local (ok if older deploy): ' +
        onlyRemote.join(', ')
    );
  }
  if (localChunks.size > 0 && onlyLocal.length === 0) {
    notes.push(
      'Chunk set: local ' +
        localChunks.size +
        ', remote ' +
        remoteChunks.size +
        '; remote has all local chunks.'
    );
  }

  // --- Main chunk content ---
  const chunkPath = '/next/_next/static/chunks/' + MAIN_CHUNK;
  const [localChunk, remoteChunk] = await Promise.all([
    fetchText(LOCAL_BASE + chunkPath),
    fetchText(REMOTE_BASE + chunkPath),
  ]);

  if (!localChunk.ok) {
    warnings.push('Local main chunk not fetched: ' + localChunk.status);
  } else if (!remoteChunk.ok) {
    errors.push('Remote main chunk not fetched: ' + remoteChunk.status);
  } else {
    const localIsJs =
      localChunk.text.includes('TURBOPACK') ||
      localChunk.text.includes('(function');
    const remoteIsJs =
      remoteChunk.text.includes('TURBOPACK') ||
      remoteChunk.text.includes('(function');
    if (!remoteIsJs || remoteChunk.text.startsWith('<!')) {
      errors.push(
        'Remote main chunk is not valid JS (HTML or error page?). Deploy chunks.'
      );
    } else if (!localIsJs) {
      warnings.push('Local main chunk did not look like expected JS.');
    } else {
      const localSig = shortHash(localChunk.text);
      const remoteSig = shortHash(remoteChunk.text);
      if (localSig !== remoteSig) {
        warnings.push(
          'Main chunk differs (local vs remote). Remote may be outdated — deploy next/_next/static/chunks/' +
            MAIN_CHUNK
        );
      } else {
        notes.push('Main chunk content matches.');
      }
    }
  }

  // --- events.json ---
  const [localEvents, remoteEvents] = await Promise.all([
    fetchText(LOCAL_BASE + EVENTS_JSON_PATH),
    fetchText(REMOTE_BASE + EVENTS_JSON_PATH),
  ]);

  if (localEvents.ok && remoteEvents.ok) {
    let localList = [];
    let remoteList = [];
    try {
      const localData = JSON.parse(localEvents.text);
      localList = Array.isArray(localData)
        ? localData
        : localData.events || localData.data || [];
    } catch (_) {}
    try {
      const remoteData = JSON.parse(remoteEvents.text);
      remoteList = Array.isArray(remoteData)
        ? remoteData
        : remoteData.events || remoteData.data || [];
    } catch (_) {}

    const localN = localList.length;
    const remoteN = remoteList.length;
    if (remoteN === 0 && localN > 0) {
      warnings.push(
        'Remote events.json has 0 events while local has ' +
          localN +
          '. Deploy events.json.'
      );
    } else if (localN !== remoteN) {
      notes.push(
        'Events count: local ' + localN + ', remote ' + remoteN + '.'
      );
    } else {
      notes.push('Events count matches: ' + localN + '.');
    }
  } else {
    if (!remoteEvents.ok)
      warnings.push('Remote events.json: ' + remoteEvents.status);
    if (!localEvents.ok) notes.push('Local events.json: ' + localEvents.status);
  }

  // --- Index title / key meta (optional) ---
  const localTitle = localIndex.text.match(/<title[^>]*>([^<]+)<\/title>/)?.[1] || '';
  const remoteTitle = remoteIndex.text.match(/<title[^>]*>([^<]+)<\/title>/)?.[1] || '';
  if (
    localTitle &&
    remoteTitle &&
    localTitle.trim() !== remoteTitle.trim()
  ) {
    warnings.push(
      'Index <title> differs: local vs remote may be out of sync. Deploy index.html.'
    );
  }

  report(errors, warnings, notes);
  process.exit(errors.length > 0 ? 1 : 0);
}

function report(errors, warnings, notes) {
  if (errors.length) {
    console.log('FAIL (remote missing or out of sync):');
    errors.forEach((e) => console.log('  - ' + e));
  }
  if (warnings.length) {
    console.log('WARN:');
    warnings.forEach((w) => console.log('  - ' + w));
  }
  if (notes.length) {
    console.log('OK:');
    notes.forEach((n) => console.log('  - ' + n));
  }
  if (errors.length === 0 && warnings.length === 0 && notes.length > 0) {
    console.log('');
    console.log('Cross-comparison: remote is in sync with local (nothing missing).');
  } else if (errors.length === 0 && warnings.length > 0) {
    console.log('');
    console.log(
      'Cross-comparison: remote may be outdated or missing data; review WARN above.'
    );
  }
}

main().catch((err) => {
  console.error('Compare failed:', err.message);
  process.exit(1);
});
