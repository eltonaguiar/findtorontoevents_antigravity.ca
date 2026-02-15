#!/usr/bin/env node
/**
 * resolve_allevents_links.js
 *
 * Background enrichment job: resolves AllEvents.in URLs in events.json
 * to their original source (Eventbrite, Meetup, etc.)
 *
 * When a resolution succeeds:
 *   - event.url → replaced with the resolved source URL
 *   - event.originalUrl → the AllEvents.in URL (preserved for reference)
 *   - event.source → updated to the actual source (e.g., "Eventbrite")
 *   - event.resolvedSource → name of resolved platform
 *
 * When resolution fails (native AllEvents.in event with no external source):
 *   - event.url → unchanged
 *   - event.resolvedSource → "none" (so we don't retry next run)
 *
 * Usage:
 *   node tools/resolve_allevents_links.js              # local, updates next/events.json
 *   node tools/resolve_allevents_links.js --dry-run     # preview without writing
 *   node tools/resolve_allevents_links.js --server       # use server API instead of direct fetch
 *   node tools/resolve_allevents_links.js --force        # re-resolve even if already attempted
 */

var fs = require('fs');
var path = require('path');
var http = require('http');
var https = require('https');
var url = require('url');

var isDryRun = process.argv.indexOf('--dry-run') !== -1;
var useServer = process.argv.indexOf('--server') !== -1;
var forceResolve = process.argv.indexOf('--force') !== -1;
var CONCURRENCY = 5;
var BATCH_DELAY_MS = 500; // ms between batches
var TIMEOUT_MS = 12000;

var ROOT = path.resolve(__dirname, '..');
var EVENTS_PATH = path.join(ROOT, 'next', 'events.json');

// ── Known source patterns (same as resolve_link.php) ──
var SOURCE_PATTERNS = [
  { domain: /(?:www\.)?eventbrite\.\w+/i, name: 'Eventbrite' },
  { domain: /(?:www\.)?meetup\.com/i, name: 'Meetup' },
  { domain: /(?:www\.)?ticketmaster\.\w+/i, name: 'Ticketmaster' },
  { domain: /(?:www\.)?seatgeek\.\w+/i, name: 'SeatGeek' },
  { domain: /(?:www\.)?stubhub\.\w+/i, name: 'StubHub' },
  { domain: /(?:www\.)?axs\.com/i, name: 'AXS' },
  { domain: /(?:www\.)?universe\.com/i, name: 'Universe' },
  { domain: /(?:www\.)?showpass\.com/i, name: 'Showpass' },
  { domain: /(?:www\.)?dice\.fm/i, name: 'Dice.fm' },
  { domain: /(?:www\.)?partiful\.com/i, name: 'Partiful' },
  { domain: /(?:www\.)?lu\.ma/i, name: 'Luma' },
  { domain: /(?:www\.)?humanitix\.com/i, name: 'Humanitix' },
  { domain: /(?:www\.)?zeffy\.com/i, name: 'Zeffy' },
  { domain: /(?:www\.)?tickettailor\.com/i, name: 'TicketTailor' },
  { domain: /(?:www\.)?songkick\.com/i, name: 'Songkick' },
  { domain: /(?:www\.)?bandsintown\.com/i, name: 'Bandsintown' },
  { domain: /(?:www\.)?todaytix\.com/i, name: 'TodayTix' },
  { domain: /(?:www\.)?ticketWeb\.ca/i, name: 'TicketWeb' },
  { domain: /(?:www\.)?ticketweb\.com/i, name: 'TicketWeb' },
  { domain: /(?:www\.)?rotate\.com/i, name: 'Rotate' },
  { domain: /(?:www\.)?tixr\.com/i, name: 'Tixr' },
];

function identifySource(testUrl) {
  for (var i = 0; i < SOURCE_PATTERNS.length; i++) {
    if (SOURCE_PATTERNS[i].domain.test(testUrl)) return SOURCE_PATTERNS[i].name;
  }
  return null;
}

// ── Unwrap tracking/affiliate wrappers ──
function unwrapUrl(rawUrl) {
  // Pattern: ...pxf.io/...?u=https%3A%2F%2Fwww.eventbrite.com%2F...
  var m = rawUrl.match(/[?&]u=(https?%3A%2F%2F[^&]+)/i);
  if (m) {
    var inner = decodeURIComponent(m[1]);
    if (inner.length > 20) return inner;
  }
  // Pattern: ...?url=https://...
  var m2 = rawUrl.match(/[?&](?:url|dest|redirect|target|goto)=(https?[^&]+)/i);
  if (m2) {
    var inner2 = decodeURIComponent(m2[1]);
    if (inner2.length > 20) return inner2;
  }
  return rawUrl;
}

function cleanUrl(rawUrl) {
  var cleaned = unwrapUrl(rawUrl);
  // Remove tracking params
  cleaned = cleaned.replace(/[&?](?:utm_[a-z]+|ref|aff|fbclid|gclid|mc_eid|source|medium|campaign)=[^&]*/g, '');
  cleaned = cleaned.replace(/\?&/, '?').replace(/\?$/, '');
  return cleaned;
}

// ── Fetch a URL following redirects ──
function fetchPage(pageUrl, redirectsLeft) {
  if (redirectsLeft === undefined) redirectsLeft = 8;
  return new Promise(function(resolve, reject) {
    if (redirectsLeft <= 0) return reject(new Error('Too many redirects'));
    var parsed = url.parse(pageUrl);
    var mod = parsed.protocol === 'https:' ? https : http;
    var req = mod.get(pageUrl, {
      timeout: TIMEOUT_MS,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5'
      }
    }, function(res) {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        var loc = res.headers.location;
        if (loc.indexOf('/') === 0) loc = parsed.protocol + '//' + parsed.host + loc;
        res.resume();
        return fetchPage(loc, redirectsLeft - 1).then(resolve, reject);
      }
      if (res.statusCode !== 200) {
        res.resume();
        return reject(new Error('HTTP ' + res.statusCode));
      }
      var chunks = [];
      var total = 0;
      var MAX = 512 * 1024;
      res.on('data', function(c) { if (total < MAX) { chunks.push(c); total += c.length; } });
      res.on('end', function() {
        var finalUrl = pageUrl; // after redirects
        resolve({ body: Buffer.concat(chunks).toString('utf-8'), finalUrl: finalUrl });
      });
      res.on('error', reject);
    });
    req.on('timeout', function() { req.destroy(); reject(new Error('Timeout')); });
    req.on('error', reject);
  });
}

// ── Extract source URL from HTML ──
function extractSourceUrl(html) {
  // 1. href links matching known platforms
  for (var i = 0; i < SOURCE_PATTERNS.length; i++) {
    var p = SOURCE_PATTERNS[i];
    // Build a regex that finds href="https://...domain.../..."
    var re = new RegExp('href\\s*=\\s*["\']?(https?://(?:www\\.)?' + p.domain.source + '/[^"\'\\s>]+)', 'i');
    var m = html.match(re);
    if (m) return { url: cleanUrl(m[1]), source: p.name, method: 'href_link' };
  }

  // 2. JSON-LD ticket_url / registration_url
  var jsonLdMatch = html.match(/"(?:ticket_url|registration_url|ticketUrl)"\s*:\s*"(https?:\/\/[^"]+)"/i);
  if (jsonLdMatch) {
    var ticketUrl = cleanUrl(jsonLdMatch[1]);
    var src = identifySource(ticketUrl);
    if (src) return { url: ticketUrl, source: src, method: 'json_ld' };
  }

  // 3. "Get Tickets" / "Register" button links
  var btnRe = /href\s*=\s*["'](https?:\/\/[^"']+)["'][^>]*>(?:[^<]*(?:ticket|register|rsvp|book|buy)[^<]*)/gi;
  var btnMatch;
  while ((btnMatch = btnRe.exec(html)) !== null) {
    var btnUrl = cleanUrl(btnMatch[1]);
    if (btnUrl.indexOf('allevents.in') === -1) {
      var btnSrc = identifySource(btnUrl);
      if (btnSrc) return { url: btnUrl, source: btnSrc, method: 'button_link' };
    }
  }

  // 4. Fallback: any external link matching a known source
  var allLinksRe = /href\s*=\s*["'](https?:\/\/[^"']+)["']/gi;
  var linkMatch;
  while ((linkMatch = allLinksRe.exec(html)) !== null) {
    var linkUrl = cleanUrl(linkMatch[1]);
    if (linkUrl.indexOf('allevents.in') !== -1) continue;
    var linkSrc = identifySource(linkUrl);
    if (linkSrc) return { url: linkUrl, source: linkSrc, method: 'page_link' };
  }

  return null;
}

// ── Resolve a single event ──
function resolveEvent(ev) {
  return fetchPage(ev.url).then(function(result) {
    // Check if the final URL (after redirects) is already a known source
    var redirectSrc = identifySource(result.finalUrl);
    if (redirectSrc && result.finalUrl !== ev.url) {
      return { url: cleanUrl(result.finalUrl), source: redirectSrc, method: 'redirect' };
    }
    // Parse the page
    return extractSourceUrl(result.body);
  });
}

// ── Server API resolution (alternative) ──
function resolveViaServer(urls) {
  return new Promise(function(resolve, reject) {
    var postData = JSON.stringify({ urls: urls });
    var opts = {
      hostname: 'findtorontoevents.ca',
      path: '/api/events/resolve_link.php',
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(postData) }
    };
    var req = https.request(opts, function(res) {
      var d = '';
      res.on('data', function(c) { d += c; });
      res.on('end', function() {
        try { resolve(JSON.parse(d)); } catch(e) { reject(new Error('Parse error: ' + d.substring(0, 200))); }
      });
    });
    req.on('error', reject);
    req.write(postData);
    req.end();
  });
}

// ── Process in batches ──
function sleep(ms) { return new Promise(function(r) { setTimeout(r, ms); }); }

async function processBatch(events, batchNum, totalBatches) {
  var results = [];
  var promises = events.map(function(ev) {
    return resolveEvent(ev).then(function(r) {
      results.push({ event: ev, resolved: r });
    }).catch(function(err) {
      results.push({ event: ev, resolved: null, error: err.message });
    });
  });
  await Promise.all(promises);
  return results;
}

async function processServerBatch(events) {
  var urls = events.map(function(ev) { return ev.url; });
  try {
    var data = await resolveViaServer(urls);
    if (!data.results) return events.map(function(ev) { return { event: ev, resolved: null, error: 'bad response' }; });
    return data.results.map(function(r, i) {
      return {
        event: events[i],
        resolved: r.resolved_url ? { url: r.resolved_url, source: r.source, method: r.method } : null,
        error: r.error || null
      };
    });
  } catch(e) {
    return events.map(function(ev) { return { event: ev, resolved: null, error: e.message }; });
  }
}

// ── Main ──
async function main() {
  if (!fs.existsSync(EVENTS_PATH)) {
    console.error('events.json not found at', EVENTS_PATH);
    process.exit(1);
  }

  var events = JSON.parse(fs.readFileSync(EVENTS_PATH, 'utf8'));
  console.log('Total events:', events.length);

  // Find AllEvents.in events that need resolution
  var toResolve = events.filter(function(ev) {
    if (!ev.url || ev.url.indexOf('allevents.in') === -1) return false;
    if (!forceResolve && ev.resolvedSource) return false; // already attempted
    return true;
  });

  console.log('AllEvents.in events needing resolution:', toResolve.length);
  if (toResolve.length === 0) {
    console.log('Nothing to resolve.');
    return;
  }

  if (isDryRun) console.log('[DRY RUN] Will not write changes.\n');

  // Process in batches
  var resolved = 0, failed = 0, unchanged = 0;
  var batchSize = useServer ? 15 : CONCURRENCY;
  var totalBatches = Math.ceil(toResolve.length / batchSize);

  for (var b = 0; b < totalBatches; b++) {
    var batch = toResolve.slice(b * batchSize, (b + 1) * batchSize);
    process.stdout.write('Batch ' + (b + 1) + '/' + totalBatches + ' (' + batch.length + ' events)...');

    var results;
    if (useServer) {
      results = await processServerBatch(batch);
    } else {
      results = await processBatch(batch, b, totalBatches);
    }

    results.forEach(function(r) {
      var ev = r.event;
      if (r.resolved && r.resolved.url) {
        // Find the event in the main array and update it
        for (var i = 0; i < events.length; i++) {
          if (events[i].id === ev.id) {
            events[i].originalUrl = ev.url;
            events[i].url = r.resolved.url;
            events[i].resolvedSource = r.resolved.source;
            // Keep source as "AllEvents.in" but add resolvedSource for clarity
            break;
          }
        }
        resolved++;
        if (!isDryRun) {
          // silent
        } else {
          console.log('\n  OK: ' + ev.title.substring(0, 45) + ' -> ' + r.resolved.source + ' (' + r.resolved.method + ')');
        }
      } else {
        // Mark as attempted so we don't retry
        for (var i = 0; i < events.length; i++) {
          if (events[i].id === ev.id) {
            events[i].resolvedSource = 'none';
            break;
          }
        }
        failed++;
      }
    });

    process.stdout.write(' resolved ' + resolved + ', no-match ' + failed + '\n');

    // Rate limiting between batches
    if (b < totalBatches - 1) await sleep(BATCH_DELAY_MS);
  }

  console.log('\n=== Summary ===');
  console.log('Resolved:', resolved);
  console.log('No external source:', failed);
  console.log('Total processed:', resolved + failed);
  console.log('Resolution rate:', Math.round(resolved / (resolved + failed) * 100) + '%');

  // Tag event router status on all events
  var routerCount = 0;
  events.forEach(function(ev) {
    if (ev.url && ev.url.indexOf('allevents.in') !== -1) {
      ev.isEventRouter = true;
      routerCount++;
    } else {
      ev.isEventRouter = false;
    }
  });
  console.log('Tagged ' + routerCount + ' events as event router (aggregator-only)');

  if (!isDryRun) {
    fs.writeFileSync(EVENTS_PATH, JSON.stringify(events, null, 2));
    console.log('\nWritten updated events.json (' + events.length + ' events)');
  } else {
    console.log('\n[DRY RUN] No files modified.');
  }
}

main().catch(function(err) {
  console.error('Fatal:', err);
  process.exit(1);
});
