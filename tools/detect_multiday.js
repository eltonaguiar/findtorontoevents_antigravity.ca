#!/usr/bin/env node
/**
 * detect_multiday.js
 *
 * Detects multi-day / recurring events by:
 *  1. Checking endDate vs date (span > 1 day)
 *  2. Fetching Eventbrite/SeatGeek pages for "Multiple dates" indicator
 *  3. Checking title/description for recurring keywords
 *
 * Sets event.isMultiDay = true when detected.
 *
 * Usage:
 *   node tools/detect_multiday.js              # detect and save
 *   node tools/detect_multiday.js --dry-run    # preview only
 *   node tools/detect_multiday.js --force      # re-check all
 */

var fs = require('fs');
var path = require('path');
var https = require('https');
var http = require('http');

var isDryRun = process.argv.indexOf('--dry-run') !== -1;
var forceCheck = process.argv.indexOf('--force') !== -1;
var CONCURRENCY = 5;
var BATCH_DELAY_MS = 500;
var TIMEOUT_MS = 10000;

var ROOT = path.resolve(__dirname, '..');
var EVENTS_PATH = path.join(ROOT, 'next', 'events.json');

function fetchPage(pageUrl, redirectsLeft) {
  if (redirectsLeft === undefined) redirectsLeft = 5;
  return new Promise(function(resolve, reject) {
    if (redirectsLeft <= 0) return reject(new Error('Too many redirects'));
    var parsed;
    try { parsed = new URL(pageUrl); } catch(e) { return reject(e); }
    var mod = parsed.protocol === 'https:' ? https : http;
    mod.get(pageUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html'
      },
      timeout: TIMEOUT_MS
    }, function(res) {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        var loc = res.headers.location;
        if (loc[0] === '/') loc = parsed.protocol + '//' + parsed.hostname + loc;
        res.resume();
        return fetchPage(loc, redirectsLeft - 1).then(resolve, reject);
      }
      var chunks = [];
      var total = 0;
      var MAX = 128 * 1024;
      res.on('data', function(c) { if (total < MAX) { chunks.push(c); total += c.length; } });
      res.on('end', function() { resolve(Buffer.concat(chunks).toString('utf-8')); });
      res.on('error', reject);
    }).on('error', reject).on('timeout', function() { reject(new Error('timeout')); });
  });
}

function sleep(ms) { return new Promise(function(r) { setTimeout(r, ms); }); }

// Multi-day detection patterns in HTML
var MULTIDAY_PATTERNS = [
  /multiple\s+dates/i,
  /recurring\s+event/i,
  /more\s+dates/i,
  /select\s+a\s+date/i,
  /other\s+dates/i,
  /series\s+event/i,
  /repeats\s+(every|weekly|daily|monthly)/i,
];

async function main() {
  var events = JSON.parse(fs.readFileSync(EVENTS_PATH, 'utf8'));
  console.log('Total events:', events.length);

  var multiDayCount = 0;

  // Phase 1: Date range detection (no network needed)
  events.forEach(function(ev) {
    if (ev.isMultiDay && !forceCheck) return;

    // Check endDate span
    if (ev.endDate && ev.date) {
      var start = new Date(ev.date).getTime();
      var end = new Date(ev.endDate).getTime();
      if (!isNaN(start) && !isNaN(end)) {
        var diffDays = (end - start) / (1000 * 60 * 60 * 24);
        if (diffDays > 1) {
          ev.isMultiDay = true;
          multiDayCount++;
          return;
        }
      }
    }

    // Check title/description keywords
    var text = (ev.title || '') + ' ' + (ev.description || '');
    for (var i = 0; i < MULTIDAY_PATTERNS.length; i++) {
      if (MULTIDAY_PATTERNS[i].test(text)) {
        ev.isMultiDay = true;
        multiDayCount++;
        return;
      }
    }
  });

  console.log('Multi-day from date range + keywords:', multiDayCount);

  // Phase 2: Check Eventbrite pages for "Multiple dates"
  var toCheck = events.filter(function(ev) {
    if (ev.isMultiDay) return false;
    if (!ev.url) return false;
    if (!forceCheck && ev.multiDayChecked) return false;
    return /eventbrite\.\w+/i.test(ev.url);
  });

  console.log('Eventbrite events to check for multi-date:', toCheck.length);

  if (toCheck.length > 0) {
    var webMultiDay = 0;
    var totalBatches = Math.ceil(toCheck.length / CONCURRENCY);

    for (var b = 0; b < totalBatches; b++) {
      var batch = toCheck.slice(b * CONCURRENCY, (b + 1) * CONCURRENCY);
      process.stdout.write('Batch ' + (b + 1) + '/' + totalBatches + '...');

      var results = await Promise.all(batch.map(function(ev) {
        return fetchPage(ev.url).then(function(html) {
          var isMulti = false;
          for (var i = 0; i < MULTIDAY_PATTERNS.length; i++) {
            if (MULTIDAY_PATTERNS[i].test(html)) {
              isMulti = true;
              break;
            }
          }
          return { id: ev.id, isMulti: isMulti, title: ev.title };
        }).catch(function() {
          return { id: ev.id, isMulti: false, error: true };
        });
      }));

      results.forEach(function(r) {
        for (var i = 0; i < events.length; i++) {
          if (events[i].id === r.id) {
            events[i].multiDayChecked = new Date().toISOString();
            if (r.isMulti) {
              events[i].isMultiDay = true;
              webMultiDay++;
              multiDayCount++;
            }
            break;
          }
        }
      });

      process.stdout.write(' found ' + webMultiDay + ' multi-day so far\n');
      if (b < totalBatches - 1) await sleep(BATCH_DELAY_MS);
    }
  }

  console.log('\n=== Summary ===');
  console.log('Total multi-day events:', multiDayCount);
  var mdEvents = events.filter(function(ev) { return ev.isMultiDay; });
  mdEvents.forEach(function(ev) {
    console.log('  ' + ev.title.substring(0, 55));
  });

  if (!isDryRun) {
    fs.writeFileSync(EVENTS_PATH, JSON.stringify(events, null, 2));
    console.log('\nSaved.');
  } else {
    console.log('\n[DRY RUN] No files modified.');
  }
}

main().catch(function(err) {
  console.error('Fatal:', err);
  process.exit(1);
});
