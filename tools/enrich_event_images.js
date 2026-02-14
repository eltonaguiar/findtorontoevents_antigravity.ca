#!/usr/bin/env node
/**
 * enrich_event_images.js
 * 
 * Reads events.json, finds events without images, fetches their source URLs,
 * extracts og:image (or other image meta tags) from the HTML, and writes
 * the enriched events.json back.
 *
 * Usage:
 *   node tools/enrich_event_images.js [--dry-run] [--limit N] [--concurrency N]
 *
 * Options:
 *   --dry-run       Don't write back to events.json, just report what would be added
 *   --limit N       Only process N events (for testing)
 *   --concurrency N How many parallel fetches (default: 5)
 */

const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');

// ─── Config ───
const EVENTS_PATH = path.join(__dirname, '..', 'next', 'events.json');
const TIMEOUT_MS = 10000;  // 10s per request
const DELAY_BETWEEN_BATCHES_MS = 500;

// Parse CLI args
const args = process.argv.slice(2);
const DRY_RUN = args.includes('--dry-run');
const limitIdx = args.indexOf('--limit');
const LIMIT = limitIdx !== -1 ? parseInt(args[limitIdx + 1], 10) : Infinity;
const concIdx = args.indexOf('--concurrency');
const CONCURRENCY = concIdx !== -1 ? parseInt(args[concIdx + 1], 10) : 5;

// ─── Helpers ───

/**
 * Fetch a URL and return the HTML body (follows up to 5 redirects).
 */
function fetchPage(pageUrl, redirectsLeft) {
  if (redirectsLeft === undefined) redirectsLeft = 5;
  return new Promise(function (resolve, reject) {
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
    }, function (res) {
      // Follow redirects
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        var loc = res.headers.location;
        if (loc.startsWith('/')) {
          loc = parsed.protocol + '//' + parsed.host + loc;
        }
        res.resume(); // Drain the response
        return fetchPage(loc, redirectsLeft - 1).then(resolve, reject);
      }
      if (res.statusCode !== 200) {
        res.resume();
        return reject(new Error('HTTP ' + res.statusCode));
      }

      var chunks = [];
      var totalLen = 0;
      var MAX_BYTES = 512 * 1024; // Only read first 512KB (we only need head/meta)
      res.on('data', function (chunk) {
        if (totalLen < MAX_BYTES) {
          chunks.push(chunk);
          totalLen += chunk.length;
        }
      });
      res.on('end', function () {
        resolve(Buffer.concat(chunks).toString('utf-8'));
      });
      res.on('error', reject);
    });
    req.on('timeout', function () { req.destroy(); reject(new Error('Timeout')); });
    req.on('error', reject);
  });
}

/**
 * Extract the best image URL from HTML meta tags.
 * Priority: og:image > twitter:image > itemprop image > first large image
 */
function extractImageFromHtml(html) {
  // Try og:image first
  var ogMatch = html.match(/<meta\s+(?:[^>]*?\s+)?(?:property|name)\s*=\s*["']og:image["']\s+(?:[^>]*?\s+)?content\s*=\s*["']([^"']+)["']/i);
  if (!ogMatch) {
    ogMatch = html.match(/<meta\s+(?:[^>]*?\s+)?content\s*=\s*["']([^"']+)["']\s+(?:[^>]*?\s+)?(?:property|name)\s*=\s*["']og:image["']/i);
  }
  if (ogMatch && ogMatch[1] && isValidImageUrl(ogMatch[1])) {
    return ogMatch[1];
  }

  // Try twitter:image
  var twMatch = html.match(/<meta\s+(?:[^>]*?\s+)?(?:property|name)\s*=\s*["']twitter:image["']\s+(?:[^>]*?\s+)?content\s*=\s*["']([^"']+)["']/i);
  if (!twMatch) {
    twMatch = html.match(/<meta\s+(?:[^>]*?\s+)?content\s*=\s*["']([^"']+)["']\s+(?:[^>]*?\s+)?(?:property|name)\s*=\s*["']twitter:image["']/i);
  }
  if (twMatch && twMatch[1] && isValidImageUrl(twMatch[1])) {
    return twMatch[1];
  }

  // Try itemprop image  
  var itemMatch = html.match(/<meta\s+(?:[^>]*?\s+)?itemprop\s*=\s*["']image["']\s+(?:[^>]*?\s+)?content\s*=\s*["']([^"']+)["']/i);
  if (!itemMatch) {
    itemMatch = html.match(/<meta\s+(?:[^>]*?\s+)?content\s*=\s*["']([^"']+)["']\s+(?:[^>]*?\s+)?itemprop\s*=\s*["']image["']/i);
  }
  if (itemMatch && itemMatch[1] && isValidImageUrl(itemMatch[1])) {
    return itemMatch[1];
  }

  // For AllEvents.in: look for the event banner image in their specific HTML patterns
  var aeBanner = html.match(/<img[^>]+class\s*=\s*["'][^"']*event[_-]?banner[^"']*["'][^>]+src\s*=\s*["']([^"']+)["']/i);
  if (!aeBanner) {
    aeBanner = html.match(/<img[^>]+src\s*=\s*["']([^"']+)["'][^>]+class\s*=\s*["'][^"']*event[_-]?banner[^"']*["']/i);
  }
  if (aeBanner && aeBanner[1] && isValidImageUrl(aeBanner[1])) {
    return aeBanner[1];
  }

  // For AllEvents.in: their CDN pattern
  var aeCdn = html.match(/["'](https:\/\/cdn\.allevents\.in\/[^"'\s]+\.(?:jpg|jpeg|png|webp)[^"'\s]*)["']/i);
  if (aeCdn && aeCdn[1] && isValidImageUrl(aeCdn[1])) {
    return aeCdn[1];
  }

  // Try JSON-LD structured data
  var jsonLdMatch = html.match(/<script[^>]+type\s*=\s*["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi);
  if (jsonLdMatch) {
    for (var i = 0; i < jsonLdMatch.length; i++) {
      var inner = jsonLdMatch[i].replace(/<script[^>]*>/i, '').replace(/<\/script>/i, '');
      try {
        var ld = JSON.parse(inner);
        // Could be array
        var items = Array.isArray(ld) ? ld : [ld];
        for (var j = 0; j < items.length; j++) {
          var item = items[j];
          if (item.image) {
            var img = Array.isArray(item.image) ? item.image[0] : item.image;
            if (typeof img === 'object' && img.url) img = img.url;
            if (typeof img === 'string' && isValidImageUrl(img)) return img;
          }
        }
      } catch (e) { /* ignore parse errors */ }
    }
  }

  return null;
}

/**
 * Check if a URL looks like a valid event image (not a generic icon/logo).
 */
function isValidImageUrl(u) {
  if (!u || typeof u !== 'string') return false;
  u = u.trim();
  if (u.length < 10) return false;
  // Must start with http
  if (!u.match(/^https?:\/\//i)) return false;
  // Reject tiny icons, favicons, logos, tracking pixels
  var lower = u.toLowerCase();
  if (lower.indexOf('favicon') !== -1) return false;
  if (lower.indexOf('logo') !== -1 && lower.indexOf('event') === -1) return false;
  if (lower.indexOf('pixel') !== -1) return false;
  if (lower.indexOf('tracking') !== -1) return false;
  if (lower.indexOf('1x1') !== -1) return false;
  if (lower.indexOf('spacer') !== -1) return false;
  // Reject data: URLs
  if (lower.startsWith('data:')) return false;
  // Reject very short SVGs
  if (lower.endsWith('.svg') && lower.length < 50) return false;
  return true;
}

/**
 * For AllEvents.in events, try to extract the Eventbrite/original event link
 * from the page, then fetch that page's og:image as a fallback.
 */
function extractExternalEventLink(html) {
  // AllEvents.in often links to the original event page (Eventbrite, etc.)
  var patterns = [
    /href\s*=\s*["'](https:\/\/(?:www\.)?eventbrite\.[^"'\s]+)["']/i,
    /href\s*=\s*["'](https:\/\/(?:www\.)?meetup\.com\/[^"'\s]+)["']/i,
    /href\s*=\s*["'](https:\/\/(?:www\.)?ticketmaster\.[^"'\s]+)["']/i,
    /href\s*=\s*["'](https:\/\/(?:www\.)?universe\.com\/[^"'\s]+)["']/i,
    /href\s*=\s*["'](https:\/\/(?:www\.)?showpass\.com\/[^"'\s]+)["']/i,
    /href\s*=\s*["'](https:\/\/(?:www\.)?dice\.fm\/[^"'\s]+)["']/i,
    // Generic "buy tickets" or "register" links
    /["']ticket_url["']\s*:\s*["'](https?:\/\/[^"']+)["']/i,
    /["']registration_url["']\s*:\s*["'](https?:\/\/[^"']+)["']/i,
  ];
  for (var i = 0; i < patterns.length; i++) {
    var m = html.match(patterns[i]);
    if (m && m[1]) return m[1];
  }
  return null;
}

/**
 * Process a single event: fetch URL, extract image.
 * Returns the image URL or null.
 */
async function processEvent(ev) {
  if (!ev.url || ev.url.trim() === '' || ev.url === '#') return null;
  
  try {
    var html = await fetchPage(ev.url);
    var img = extractImageFromHtml(html);
    
    if (img) return img;
    
    // If no image found and source is AllEvents.in, try external link
    if (ev.source === 'AllEvents.in' || ev.url.indexOf('allevents.in') !== -1) {
      var extLink = extractExternalEventLink(html);
      if (extLink) {
        try {
          var extHtml = await fetchPage(extLink);
          var extImg = extractImageFromHtml(extHtml);
          if (extImg) return extImg;
        } catch (e) {
          // External link failed, that's okay
        }
      }
    }
    
    return null;
  } catch (e) {
    // Fetch failed
    return null;
  }
}

/**
 * Process events in batches with concurrency control.
 */
async function processBatch(events) {
  var results = [];
  for (var i = 0; i < events.length; i += CONCURRENCY) {
    var batch = events.slice(i, i + CONCURRENCY);
    var batchNum = Math.floor(i / CONCURRENCY) + 1;
    var totalBatches = Math.ceil(events.length / CONCURRENCY);
    
    process.stdout.write('\r  Batch ' + batchNum + '/' + totalBatches + 
      ' (' + (i + batch.length) + '/' + events.length + ' events processed)');
    
    var promises = batch.map(function (item) {
      return processEvent(item.event).then(function (img) {
        return { index: item.index, image: img, title: item.event.title };
      });
    });
    
    var batchResults = await Promise.all(promises);
    results = results.concat(batchResults);
    
    // Delay between batches to be nice to servers
    if (i + CONCURRENCY < events.length) {
      await new Promise(function (r) { setTimeout(r, DELAY_BETWEEN_BATCHES_MS); });
    }
  }
  console.log(''); // newline
  return results;
}

// ─── Main ───
async function main() {
  console.log('=== Event Image Enrichment Tool ===\n');
  
  // Read events.json
  if (!fs.existsSync(EVENTS_PATH)) {
    console.error('ERROR: events.json not found at ' + EVENTS_PATH);
    process.exit(1);
  }
  
  var raw = fs.readFileSync(EVENTS_PATH, 'utf-8');
  var events = JSON.parse(raw);
  console.log('Total events: ' + events.length);
  
  // Find events without images
  var needsImage = [];
  var hasImage = 0;
  events.forEach(function (ev, idx) {
    if (ev.image && ev.image.trim() !== '') {
      hasImage++;
    } else if (ev.url && ev.url.trim() !== '' && ev.url !== '#') {
      needsImage.push({ index: idx, event: ev });
    }
  });
  
  console.log('Events with images: ' + hasImage);
  console.log('Events needing images: ' + needsImage.length);
  
  if (needsImage.length === 0) {
    console.log('\nAll events already have images. Nothing to do.');
    return;
  }
  
  // Apply limit
  var toProcess = needsImage;
  if (LIMIT < needsImage.length) {
    toProcess = needsImage.slice(0, LIMIT);
    console.log('Limiting to first ' + LIMIT + ' events (--limit)');
  }
  
  console.log('\nFetching images with concurrency=' + CONCURRENCY + '...\n');
  
  // Process all events
  var results = await processBatch(toProcess);
  
  // Count successes
  var found = 0;
  var notFound = 0;
  var bySource = {};
  
  results.forEach(function (r) {
    var ev = events[r.index];
    var src = ev.source || 'Unknown';
    if (!bySource[src]) bySource[src] = { found: 0, total: 0 };
    bySource[src].total++;
    
    if (r.image) {
      found++;
      bySource[src].found++;
      if (!DRY_RUN) {
        events[r.index].image = r.image;
      }
    } else {
      notFound++;
    }
  });
  
  console.log('\n=== Results ===');
  console.log('Images found: ' + found + ' / ' + toProcess.length);
  console.log('Not found: ' + notFound);
  console.log('\nBy source:');
  Object.keys(bySource).sort().forEach(function (src) {
    var s = bySource[src];
    console.log('  ' + src + ': ' + s.found + '/' + s.total + ' (' + Math.round(s.found / s.total * 100) + '%)');
  });
  
  // Show some examples of found images
  if (found > 0) {
    console.log('\nSample enriched events:');
    var shown = 0;
    results.forEach(function (r) {
      if (r.image && shown < 8) {
        console.log('  + ' + (r.title || '').substring(0, 60) + ' => ' + r.image.substring(0, 80) + '...');
        shown++;
      }
    });
  }
  
  if (DRY_RUN) {
    console.log('\n[DRY RUN] No changes written to events.json.');
  } else if (found > 0) {
    // Write back
    fs.writeFileSync(EVENTS_PATH, JSON.stringify(events, null, 2), 'utf-8');
    console.log('\nUpdated events.json with ' + found + ' new images.');
    console.log('Total events with images now: ' + (hasImage + found) + ' / ' + events.length);
  } else {
    console.log('\nNo new images found. events.json unchanged.');
  }
}

main().catch(function (err) {
  console.error('Fatal error:', err);
  process.exit(1);
});
