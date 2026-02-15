#!/usr/bin/env node
/**
 * cleanup_past_events.js — Remove past events from next/events.json
 *
 * Can be run:
 *  1. Locally:  node tools/cleanup_past_events.js
 *  2. Via GitHub Actions (scheduled daily)
 *  3. Trigger server-side:  node tools/cleanup_past_events.js --remote
 *
 * Local mode:
 *   - Reads next/events.json
 *   - Filters out events that ended before today (EST)
 *   - Archives them to next/events_archive.json
 *   - Overwrites next/events.json with only current/future events
 *
 * Remote mode (--remote):
 *   - Calls the server-side cleanup_events.php endpoint
 */

const fs = require('fs');
const path = require('path');
const https = require('https');

const isRemote = process.argv.includes('--remote');
const isDryRun = process.argv.includes('--dry-run');

function getEstToday() {
  // Get current date in Eastern Time (UTC-5 conservative for EST)
  var now = new Date();
  var estOffset = -5 * 60; // minutes
  var utcMs = now.getTime() + (now.getTimezoneOffset() * 60000);
  var estDate = new Date(utcMs + (estOffset * 60000));
  var year = estDate.getFullYear();
  var month = String(estDate.getMonth() + 1).padStart(2, '0');
  var day = String(estDate.getDate()).padStart(2, '0');
  return new Date(year + '-' + month + '-' + day + 'T00:00:00-05:00');
}

function runLocal() {
  var root = path.resolve(__dirname, '..');
  var eventsPath = path.join(root, 'next', 'events.json');
  var archivePath = path.join(root, 'next', 'events_archive.json');

  if (!fs.existsSync(eventsPath)) {
    console.error('events.json not found at', eventsPath);
    process.exit(1);
  }

  var events = JSON.parse(fs.readFileSync(eventsPath, 'utf8'));
  console.log('Total events before cleanup:', events.length);

  var today = getEstToday();
  console.log('Today (EST):', today.toISOString());

  var kept = [];
  var archived = [];

  events.forEach(function(ev) {
    // Use START date — a Feb 14 event should not show on Feb 15,
    // even if its endDate bleeds into the next day (e.g. party 7PM-2AM)
    var startStr = ev.date;
    if (!startStr) { kept.push(ev); return; }
    var startDate = new Date(startStr);
    if (startDate < today) {
      ev.archived_on = new Date().toISOString();
      archived.push(ev);
    } else {
      kept.push(ev);
    }
  });

  console.log('Kept:', kept.length, '| Archived:', archived.length);

  if (isDryRun) {
    console.log('[DRY RUN] Would archive these events:');
    archived.forEach(function(ev) {
      console.log('  -', ev.date, '|', ev.title.substring(0, 60));
    });
    return;
  }

  // Load existing archive and merge (deduplicate by ID)
  var existingArchive = [];
  if (fs.existsSync(archivePath)) {
    try {
      existingArchive = JSON.parse(fs.readFileSync(archivePath, 'utf8'));
    } catch (e) {
      console.warn('Could not parse existing archive, starting fresh');
    }
  }

  var archiveIds = {};
  existingArchive.forEach(function(ev) { if (ev.id) archiveIds[ev.id] = true; });
  var added = 0;
  archived.forEach(function(ev) {
    if (ev.id && archiveIds[ev.id]) return;
    existingArchive.push(ev);
    added++;
  });

  fs.writeFileSync(eventsPath, JSON.stringify(kept, null, 2));
  fs.writeFileSync(archivePath, JSON.stringify(existingArchive, null, 2));

  console.log('Written', kept.length, 'events to events.json');
  console.log('Archive now has', existingArchive.length, 'events (' + added + ' newly added)');
}

function runRemote() {
  var url = 'https://findtorontoevents.ca/api/events/cleanup_events.php';
  console.log('Calling remote cleanup:', url);

  https.get(url, function(res) {
    var data = '';
    res.on('data', function(chunk) { data += chunk; });
    res.on('end', function() {
      console.log('Response status:', res.statusCode);
      try {
        var result = JSON.parse(data);
        console.log(JSON.stringify(result, null, 2));
        if (result.ok) {
          console.log('Cleanup successful: kept', result.kept, '| archived', result.archived);
        } else {
          console.error('Cleanup failed:', result.errors);
          process.exit(1);
        }
      } catch (e) {
        console.error('Invalid response:', data.substring(0, 500));
        process.exit(1);
      }
    });
  }).on('error', function(err) {
    console.error('Request failed:', err.message);
    process.exit(1);
  });
}

if (isRemote) {
  runRemote();
} else {
  runLocal();
}
