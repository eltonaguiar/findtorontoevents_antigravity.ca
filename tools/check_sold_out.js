#!/usr/bin/env node
/**
 * check_sold_out.js
 *
 * Checks events with ticketing-source URLs (Eventbrite, Ticketmaster, etc.)
 * for sold-out / sales-ended / event-ended / cancelled status.
 *
 * Detected events are:
 *   1. Archived to next/events_sold_out.json (appended, deduplicated)
 *   2. Removed from next/events.json so users don't see dead listings
 *
 * Each archived event gets:
 *   - event.soldOutStatus  = "SOLD_OUT" | "SALES_ENDED" | "EVENT_ENDED" | "CANCELLED" | "UNAVAILABLE"
 *   - event.soldOutChecked = ISO timestamp of when we detected it
 *
 * Usage:
 *   node tools/check_sold_out.js                # check + remove
 *   node tools/check_sold_out.js --dry-run      # preview, no writes
 *   node tools/check_sold_out.js --force        # re-check even recently checked events
 *   node tools/check_sold_out.js --verbose      # show each event result
 */

var fs = require('fs');
var path = require('path');
var http = require('http');
var https = require('https');
var urlMod = require('url');

var isDryRun = process.argv.indexOf('--dry-run') !== -1;
var forceCheck = process.argv.indexOf('--force') !== -1;
var verbose = process.argv.indexOf('--verbose') !== -1;
var CONCURRENCY = 4;
var BATCH_DELAY_MS = 800;
var TIMEOUT_MS = 15000;

var ROOT = path.resolve(__dirname, '..');
var EVENTS_PATH = path.join(ROOT, 'next', 'events.json');
var SOLD_OUT_PATH = path.join(ROOT, 'next', 'events_sold_out.json');

// ── Status detection patterns ──

var EVENTBRITE_PATTERNS = [
  { pattern: /sales?\s+ended/i,        status: 'SALES_ENDED'  },
  { pattern: /event\s+ended/i,         status: 'EVENT_ENDED'  },
  { pattern: /sold\s*out/i,            status: 'SOLD_OUT'     },
  { pattern: /no\s+longer\s+available/i, status: 'UNAVAILABLE' },
  { pattern: /event\s+cancelled/i,     status: 'CANCELLED'    },
  { pattern: /event\s+canceled/i,      status: 'CANCELLED'    },
  { pattern: /tickets?\s+unavailable/i, status: 'UNAVAILABLE' },
  { pattern: /registration\s+closed/i, status: 'SALES_ENDED'  },
];

var TICKETMASTER_PATTERNS = [
  { pattern: /not\s+available/i,           status: 'UNAVAILABLE' },
  { pattern: /no\s+longer\s+available/i,   status: 'UNAVAILABLE' },
  { pattern: /sold\s*out/i,               status: 'SOLD_OUT'    },
  { pattern: /off\s*sale/i,               status: 'SALES_ENDED' },
  { pattern: /event\s+cancelled/i,        status: 'CANCELLED'   },
  { pattern: /event\s+canceled/i,         status: 'CANCELLED'   },
  { pattern: /postponed/i,                status: 'CANCELLED'   },
  { pattern: /rescheduled/i,              status: 'CANCELLED'   },
];

var GENERIC_PATTERNS = [
  { pattern: /sold\s*out/i,               status: 'SOLD_OUT'    },
  { pattern: /sales?\s+ended/i,           status: 'SALES_ENDED' },
  { pattern: /event\s+ended/i,            status: 'EVENT_ENDED' },
  { pattern: /no\s+longer\s+available/i,  status: 'UNAVAILABLE' },
  { pattern: /event\s+cancelled/i,        status: 'CANCELLED'   },
  { pattern: /event\s+canceled/i,         status: 'CANCELLED'   },
  { pattern: /registration\s+closed/i,    status: 'SALES_ENDED' },
  { pattern: /tickets?\s+unavailable/i,   status: 'UNAVAILABLE' },
];

// ── Determine which patterns to use based on URL ──
function getPatternsForUrl(eventUrl) {
  if (/eventbrite\.\w+/i.test(eventUrl)) return EVENTBRITE_PATTERNS;
  if (/ticketmaster\.\w+/i.test(eventUrl)) return TICKETMASTER_PATTERNS;
  if (/seatgeek\.\w+/i.test(eventUrl)) return GENERIC_PATTERNS;
  if (/stubhub\.\w+/i.test(eventUrl)) return GENERIC_PATTERNS;
  if (/axs\.com/i.test(eventUrl)) return GENERIC_PATTERNS;
  if (/dice\.fm/i.test(eventUrl)) return GENERIC_PATTERNS;
  if (/showpass\.com/i.test(eventUrl)) return GENERIC_PATTERNS;
  if (/universe\.com/i.test(eventUrl)) return GENERIC_PATTERNS;
  if (/lu\.ma/i.test(eventUrl)) return GENERIC_PATTERNS;
  if (/humanitix\.com/i.test(eventUrl)) return GENERIC_PATTERNS;
  if (/zeffy\.com/i.test(eventUrl)) return GENERIC_PATTERNS;
  if (/songkick\.com/i.test(eventUrl)) return GENERIC_PATTERNS;
  if (/bandsintown\.com/i.test(eventUrl)) return GENERIC_PATTERNS;
  if (/todaytix\.com/i.test(eventUrl)) return GENERIC_PATTERNS;
  if (/ticketweb\.\w+/i.test(eventUrl)) return GENERIC_PATTERNS;
  if (/tixr\.com/i.test(eventUrl)) return GENERIC_PATTERNS;
  return null; // don't check URLs we don't know how to parse
}

// ── Fetch a URL following redirects ──
function fetchPage(pageUrl, redirectsLeft) {
  if (redirectsLeft === undefined) redirectsLeft = 6;
  return new Promise(function(resolve, reject) {
    if (redirectsLeft <= 0) return reject(new Error('Too many redirects'));
    var parsed;
    try { parsed = new URL(pageUrl); } catch(e) { return reject(new Error('Invalid URL: ' + pageUrl)); }
    var mod = parsed.protocol === 'https:' ? https : http;
    var opts = {
      hostname: parsed.hostname,
      path: parsed.pathname + parsed.search,
      timeout: TIMEOUT_MS,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'identity'
      }
    };
    var req = mod.get(opts, function(res) {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        var loc = res.headers.location;
        if (loc.indexOf('/') === 0) loc = parsed.protocol + '//' + parsed.hostname + loc;
        res.resume();
        return fetchPage(loc, redirectsLeft - 1).then(resolve, reject);
      }
      // 404 / 410 means event removed
      if (res.statusCode === 404 || res.statusCode === 410) {
        res.resume();
        return resolve({ body: '', statusCode: res.statusCode, finalUrl: pageUrl });
      }
      if (res.statusCode !== 200) {
        res.resume();
        return reject(new Error('HTTP ' + res.statusCode));
      }
      var chunks = [];
      var total = 0;
      var MAX = 256 * 1024; // 256 KB — we only need to scan status text
      res.on('data', function(c) { if (total < MAX) { chunks.push(c); total += c.length; } });
      res.on('end', function() {
        resolve({ body: Buffer.concat(chunks).toString('utf-8'), statusCode: 200, finalUrl: pageUrl });
      });
      res.on('error', reject);
    });
    req.on('timeout', function() { req.destroy(); reject(new Error('Timeout')); });
    req.on('error', reject);
  });
}

// ── Check a single event ──
function checkEvent(ev) {
  var patterns = getPatternsForUrl(ev.url);
  if (!patterns) return Promise.resolve({ event: ev, soldOut: null });

  return fetchPage(ev.url).then(function(result) {
    // 404 / 410 = event removed
    if (result.statusCode === 404 || result.statusCode === 410) {
      return { event: ev, soldOut: 'UNAVAILABLE', method: 'http_' + result.statusCode };
    }

    var html = result.body;

    // For Eventbrite, focus on key status indicators
    // The page has structured data and visible status text
    // Narrow the search to avoid false positives from boilerplate text
    var searchArea = html;

    // Try to isolate the main content area for better accuracy
    // Eventbrite puts status in specific containers
    var mainMatch = html.match(/<main[^>]*>([\s\S]*?)<\/main>/i);
    if (mainMatch) searchArea = mainMatch[1];

    // Also check for structured data (JSON-LD)
    var jsonLdMatches = html.match(/<script[^>]*type\s*=\s*["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi);
    if (jsonLdMatches) {
      for (var j = 0; j < jsonLdMatches.length; j++) {
        var jsonContent = jsonLdMatches[j].replace(/<\/?script[^>]*>/gi, '');
        try {
          var ld = JSON.parse(jsonContent);
          // Schema.org Event status
          if (ld.eventStatus) {
            if (/cancelled/i.test(ld.eventStatus)) return { event: ev, soldOut: 'CANCELLED', method: 'json_ld_status' };
            if (/postponed/i.test(ld.eventStatus)) return { event: ev, soldOut: 'CANCELLED', method: 'json_ld_status' };
          }
          // Schema.org Offer availability
          if (ld.offers) {
            var offers = Array.isArray(ld.offers) ? ld.offers : [ld.offers];
            var allSoldOut = offers.length > 0 && offers.every(function(o) {
              return /soldout|outofstock/i.test(o.availability || '');
            });
            if (allSoldOut) return { event: ev, soldOut: 'SOLD_OUT', method: 'json_ld_offers' };
          }
        } catch(e) { /* ignore parse errors */ }
      }
    }

    // Check HTML patterns
    for (var i = 0; i < patterns.length; i++) {
      if (patterns[i].pattern.test(searchArea)) {
        // Avoid false positives: make sure the status text is in a prominent position
        // (not just in a footer link or unrelated text)
        // For "sold out" and "sales ended" on Eventbrite, these appear as main status banners
        return { event: ev, soldOut: patterns[i].status, method: 'html_pattern' };
      }
    }

    return { event: ev, soldOut: null };
  }).catch(function(err) {
    // Network errors — don't assume sold out, just skip
    if (verbose) console.log('    Error checking ' + ev.title.substring(0, 35) + ': ' + err.message);
    return { event: ev, soldOut: null, error: err.message };
  });
}

// ── Helpers ──
function sleep(ms) { return new Promise(function(r) { setTimeout(r, ms); }); }

function loadSoldOutArchive() {
  try {
    return JSON.parse(fs.readFileSync(SOLD_OUT_PATH, 'utf8'));
  } catch(e) {
    return [];
  }
}

function saveSoldOutArchive(archive) {
  fs.writeFileSync(SOLD_OUT_PATH, JSON.stringify(archive, null, 2));
}

// ── Main ──
async function main() {
  if (!fs.existsSync(EVENTS_PATH)) {
    console.error('events.json not found at', EVENTS_PATH);
    process.exit(1);
  }

  var events = JSON.parse(fs.readFileSync(EVENTS_PATH, 'utf8'));
  console.log('Total events:', events.length);

  // Find checkable events (those with known ticketing URLs)
  var toCheck = events.filter(function(ev) {
    if (!ev.url) return false;
    if (!getPatternsForUrl(ev.url)) return false;
    // Skip if recently checked (within last 6 hours) unless --force
    if (!forceCheck && ev.soldOutChecked) {
      var checked = new Date(ev.soldOutChecked).getTime();
      var sixHoursAgo = Date.now() - 6 * 60 * 60 * 1000;
      if (checked > sixHoursAgo) return false;
    }
    return true;
  });

  console.log('Events to check:', toCheck.length);
  if (toCheck.length === 0) {
    console.log('Nothing to check.');
    return;
  }

  if (isDryRun) console.log('[DRY RUN] Will not write changes.\n');

  // Process in batches
  var soldOutEvents = [];
  var checkedCount = 0;
  var errorCount = 0;
  var totalBatches = Math.ceil(toCheck.length / CONCURRENCY);

  for (var b = 0; b < totalBatches; b++) {
    var batch = toCheck.slice(b * CONCURRENCY, (b + 1) * CONCURRENCY);
    process.stdout.write('Batch ' + (b + 1) + '/' + totalBatches + ' (' + batch.length + ' events)...');

    var results = await Promise.all(batch.map(function(ev) { return checkEvent(ev); }));

    results.forEach(function(r) {
      if (r.error) {
        errorCount++;
        return;
      }
      checkedCount++;

      // Mark the event as checked (timestamp) even if not sold out
      for (var i = 0; i < events.length; i++) {
        if (events[i].id === r.event.id) {
          events[i].soldOutChecked = new Date().toISOString();
          break;
        }
      }

      if (r.soldOut) {
        soldOutEvents.push({
          event: r.event,
          status: r.soldOut,
          method: r.method
        });
        if (verbose) {
          console.log('\n  ' + r.soldOut + ': ' + r.event.title.substring(0, 50) + ' [' + r.method + ']');
        }
      }
    });

    var soldCount = soldOutEvents.length;
    process.stdout.write(' checked ' + checkedCount + ', sold-out/ended ' + soldCount + ', errors ' + errorCount + '\n');

    if (b < totalBatches - 1) await sleep(BATCH_DELAY_MS);
  }

  console.log('\n=== Summary ===');
  console.log('Checked:', checkedCount);
  console.log('Errors (skipped):', errorCount);
  console.log('Sold out / ended:', soldOutEvents.length);

  if (soldOutEvents.length > 0) {
    // Breakdown by status
    var breakdown = {};
    soldOutEvents.forEach(function(s) {
      breakdown[s.status] = (breakdown[s.status] || 0) + 1;
    });
    Object.keys(breakdown).forEach(function(k) {
      console.log('  ' + k + ': ' + breakdown[k]);
    });

    console.log('\nSold out / ended events:');
    soldOutEvents.forEach(function(s) {
      console.log('  [' + s.status + '] ' + s.event.title.substring(0, 55));
    });
  }

  if (!isDryRun && soldOutEvents.length > 0) {
    // Archive sold-out events
    var archive = loadSoldOutArchive();
    var archiveIds = {};
    archive.forEach(function(a) { archiveIds[a.id] = true; });

    var removedIds = {};
    soldOutEvents.forEach(function(s) {
      var ev = null;
      for (var i = 0; i < events.length; i++) {
        if (events[i].id === s.event.id) {
          ev = events[i];
          break;
        }
      }
      if (ev) {
        ev.soldOutStatus = s.status;
        ev.soldOutChecked = new Date().toISOString();
        ev.soldOutMethod = s.method;
        if (!archiveIds[ev.id]) {
          archive.push(ev);
        } else {
          // Update existing archive entry
          for (var j = 0; j < archive.length; j++) {
            if (archive[j].id === ev.id) {
              archive[j] = ev;
              break;
            }
          }
        }
        removedIds[ev.id] = true;
      }
    });

    // Remove sold-out events from main list
    var before = events.length;
    events = events.filter(function(ev) { return !removedIds[ev.id]; });
    var removed = before - events.length;

    // Write files
    fs.writeFileSync(EVENTS_PATH, JSON.stringify(events, null, 2));
    saveSoldOutArchive(archive);

    console.log('\nRemoved ' + removed + ' events from events.json (' + events.length + ' remaining)');
    console.log('Archived to events_sold_out.json (' + archive.length + ' total archived)');
  } else if (isDryRun) {
    console.log('\n[DRY RUN] No files modified.');
  } else {
    console.log('\nNo sold-out events found. events.json unchanged.');
    // Still write the checked timestamps
    fs.writeFileSync(EVENTS_PATH, JSON.stringify(events, null, 2));
  }
}

main().catch(function(err) {
  console.error('Fatal:', err);
  process.exit(1);
});
