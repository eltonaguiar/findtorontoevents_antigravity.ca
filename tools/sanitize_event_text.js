#!/usr/bin/env node
/**
 * sanitize_event_text.js
 *
 * Detects and fixes encoding-garbled text in event titles and descriptions.
 * Catches mojibake (Cyrillic/Latin mixed encoding artifacts) and cleans them.
 *
 * Usage:
 *   node tools/sanitize_event_text.js              # fix and save
 *   node tools/sanitize_event_text.js --dry-run    # preview only
 */

var fs = require('fs');
var path = require('path');

var isDryRun = process.argv.indexOf('--dry-run') !== -1;
var ROOT = path.resolve(__dirname, '..');
var EVENTS_PATH = path.join(ROOT, 'next', 'events.json');

// Common mojibake patterns: Cyrillic chars that result from
// UTF-8 bytes being misinterpreted as Windows-1251 or similar
var MOJIBAKE_MAP = {
  '\u0424\u0417\u0443': '\u2122', // ФЗу → ™  (TM symbol)
  '\u0424\u0434\u0443': '\u2122', // Фду → ™
  '\u0424\u0448': '\u2013',       // Фш  → – (en-dash)
  '\u0414\u0439': '\uD83C\uDF82', // Дй  → 🎂 (birthday cake emoji)
  '\u044C': '\u00E1',             // ь   → á  (a-acute, e.g. Los Ángeles)
};

// Detect garbled text: mixed Cyrillic + Latin in ways that don't make
// sense for real multilingual content
function isGarbled(text) {
  if (!text) return false;
  // Cyrillic chars mixed with Latin in a single word
  if (/[\u0410-\u044F][A-Za-z]|[A-Za-z][\u0410-\u044F]/.test(text)) return true;
  // Known mojibake sequences
  for (var pattern in MOJIBAKE_MAP) {
    if (text.indexOf(pattern) !== -1) return true;
  }
  // Mostly Cyrillic but claims to be an English event
  var cyrCount = (text.match(/[\u0400-\u04FF]/g) || []).length;
  var latCount = (text.match(/[A-Za-z]/g) || []).length;
  if (cyrCount > 3 && latCount > 3 && cyrCount / (cyrCount + latCount) > 0.3) return true;
  return false;
}

// Attempt to clean known mojibake patterns
function cleanMojibake(text) {
  var cleaned = text;
  for (var pattern in MOJIBAKE_MAP) {
    while (cleaned.indexOf(pattern) !== -1) {
      cleaned = cleaned.replace(pattern, MOJIBAKE_MAP[pattern]);
    }
  }
  // Remove remaining isolated Cyrillic chars that are clearly noise
  // (single Cyrillic char surrounded by Latin)
  cleaned = cleaned.replace(/([A-Za-z])[\u0400-\u04FF]([A-Za-z])/g, '$1$2');
  // Remove leading/trailing Cyrillic noise
  cleaned = cleaned.replace(/^[\u0400-\u04FF\s]+(?=[A-Z])/g, '');
  cleaned = cleaned.replace(/[\u0400-\u04FF]+$/g, '');
  // Clean up double spaces, trim
  cleaned = cleaned.replace(/\s{2,}/g, ' ').trim();
  return cleaned;
}

// Try to extract a clean title from the URL slug
function titleFromUrl(eventUrl) {
  if (!eventUrl) return null;
  var m = eventUrl.match(/\/e\/([^/?]+)/); // Eventbrite
  if (!m) m = eventUrl.match(/\/toronto\/([^/?]+)/); // AllEvents.in
  if (!m) return null;
  var slug = m[1]
    .replace(/-tickets?-\d+$/, '') // remove eventbrite ticket suffix
    .replace(/-/g, ' ')
    .replace(/\b\w/g, function(c) { return c.toUpperCase(); }); // title case
  return slug;
}

function main() {
  if (!fs.existsSync(EVENTS_PATH)) {
    console.error('events.json not found at', EVENTS_PATH);
    process.exit(1);
  }

  var events = JSON.parse(fs.readFileSync(EVENTS_PATH, 'utf8'));
  console.log('Total events:', events.length);

  var garbled = [];
  events.forEach(function(ev) {
    if (isGarbled(ev.title) || isGarbled(ev.description)) {
      garbled.push(ev);
    }
  });

  console.log('Garbled text detected:', garbled.length);

  if (garbled.length === 0) {
    console.log('No encoding issues found.');
    return;
  }

  garbled.forEach(function(ev) {
    var origTitle = ev.title;
    var cleaned = cleanMojibake(ev.title);
    var stillGarbled = isGarbled(cleaned);

    // If still garbled after cleanup, try URL slug
    if (stillGarbled) {
      var urlTitle = titleFromUrl(ev.url);
      if (urlTitle && urlTitle.length > 5) {
        cleaned = urlTitle;
        stillGarbled = false;
      }
    }

    if (cleaned !== origTitle) {
      console.log('  FIXED: ' + origTitle.substring(0, 50));
      console.log('     ->  ' + cleaned.substring(0, 50));
      // Update in main array
      for (var i = 0; i < events.length; i++) {
        if (events[i].id === ev.id) {
          events[i].title = cleaned;
          break;
        }
      }
    } else if (stillGarbled) {
      console.log('  UNFIXABLE: ' + origTitle.substring(0, 50) + ' (manual review needed)');
    }
  });

  if (!isDryRun) {
    fs.writeFileSync(EVENTS_PATH, JSON.stringify(events, null, 2));
    console.log('\nSaved cleaned events.json');
  } else {
    console.log('\n[DRY RUN] No files modified.');
  }
}

main();
