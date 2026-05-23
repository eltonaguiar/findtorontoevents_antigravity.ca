/**
 * Unit tests for PR #751 month-filter fixes.
 *
 * Per 5-engine 3-round swarm review (MERGE_AFTER_FIXES, 4/5):
 *   - Fix 1: __RAW_EVENTS__ pre-filter keeps still-running events
 *            (start>=today OR end>=today).
 *   - Fix 2: applyFilters() shouldShow=false when eventData=null
 *            and __RAW_EVENTS__ has loaded (zombie hide); race-
 *            safety: shouldShow=true (fallback path) when feed
 *            not yet loaded.
 *   - Fix 3: badge hide uses date-pattern regex, not just length<=30.
 *            Must match "MAY 8" and "MAY 8 Wednesday"; must reject
 *            long description prose.
 *
 * Run:  node --test tests/test_month_filter.unit.test.js
 */

'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

// ---------------------------------------------------------------------------
// Fix 1 — pre-filter logic (start>=today OR end>=today)
// ---------------------------------------------------------------------------
function fix1Filter(events, todayStr) {
  return events.filter(function (e) {
    var _ed = String(e.date || e.start_date || e.startDate || '');
    if (!_ed) return true;
    var _end = String(e.end_date || e.endDate || _ed);
    return _ed.substring(0, 10) >= todayStr || _end.substring(0, 10) >= todayStr;
  });
}

test('Fix 1: pre-filter keeps running event with past start, future end', () => {
  const today = '2026-05-04';
  const events = [
    { title: '& Juliet', date: '2025-12-03', end_date: '2026-05-17' },
  ];
  const filtered = fix1Filter(events, today);
  assert.equal(filtered.length, 1);
  assert.equal(filtered[0].title, '& Juliet');
});

test('Fix 1: pre-filter drops event with both start and end in the past', () => {
  const today = '2026-05-04';
  const events = [
    { title: 'Declaration of the Understory', date: '2025-05-23', end_date: '2025-05-23' },
    { title: 'Bathed in Strange Light', date: '2025-05-23' },
  ];
  const filtered = fix1Filter(events, today);
  assert.equal(filtered.length, 0);
});

// ---------------------------------------------------------------------------
// Fix 2 — eventData=null fallback in This Month branch
// ---------------------------------------------------------------------------
function fix2ShouldShow({ eventData, rawEventsLoaded, parsedFromDisplay }) {
  let shouldShow = true;
  let fellBackToParse = false;
  let _eStartTM = null;
  if (!_eStartTM) {
    if (!eventData && rawEventsLoaded) {
      shouldShow = false;
    } else {
      fellBackToParse = true;
      _eStartTM = parsedFromDisplay;
    }
  }
  return { shouldShow, fellBackToParse, _eStartTM };
}

test('Fix 2: shouldShow=false when eventData=null AND feed loaded', () => {
  const r = fix2ShouldShow({ eventData: null, rawEventsLoaded: true, parsedFromDisplay: '2026-05-23' });
  assert.equal(r.shouldShow, false);
  assert.equal(r.fellBackToParse, false);
});

test('Fix 2: shouldShow=true (race fallback) when eventData=null AND feed not yet loaded', () => {
  const r = fix2ShouldShow({ eventData: null, rawEventsLoaded: false, parsedFromDisplay: '2026-05-08' });
  assert.equal(r.shouldShow, true);
  assert.equal(r.fellBackToParse, true);
  assert.equal(r._eStartTM, '2026-05-08');
});

// ---------------------------------------------------------------------------
// Fix 3 — tightened date-pattern regex for badge-hide
// ---------------------------------------------------------------------------
const BADGE_HIDE_RE = /^[A-Z]{3}\s*\n?\s*\d{1,2}(\s+(?:[A-Z][a-z]+|\d{4}|,\s*\d{4}))?\s*$/i;
function shouldHideBadge(text) {
  return BADGE_HIDE_RE.test(text) && text.length <= 30;
}

test('Fix 3: hide pattern matches "MAY 8" date label', () => {
  assert.equal(shouldHideBadge('MAY 8'), true);
  assert.equal(shouldHideBadge('JUN 12'), true);
  assert.equal(shouldHideBadge('DEC 31'), true);
});

test('Fix 3: hide pattern skips long description prose (false-positive guard)', () => {
  assert.equal(shouldHideBadge('Ave 5 free admission tonight!'), false);
  assert.equal(shouldHideBadge('Get 50% off in May'), false);
  assert.equal(shouldHideBadge('A description of an event happening at 7pm tonight downtown'), false);
  assert.equal(shouldHideBadge('MAY 8 is the best day for live music in Toronto'), false);
});

test('Fix 3: hide pattern matches "MAY 8 Wednesday" day-of-week suffix', () => {
  assert.equal(shouldHideBadge('MAY 8 Wednesday'), true);
  assert.equal(shouldHideBadge('JUN 12 Friday'), true);
  assert.equal(shouldHideBadge('MAY 8 2026'), true);
});
