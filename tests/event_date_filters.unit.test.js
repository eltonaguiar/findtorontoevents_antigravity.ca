/**
 * Unit tests for the homepage date-window filter math.
 * Run:  node --test tests/event_date_filters.unit.test.js
 */

'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const {
  getNextMonthWindow,
  eventInNextMonth,
  eventInNextMonthAnyOccurrence,
  getThisMonthFromTodayWindow,
  dispInThisMonthFromToday,
} = require('./event_date_filters');

const NOW = new Date(2026, 4, 1); // May 1, 2026 local

test('getNextMonthWindow: May 1 2026 → June 1..30 2026', () => {
  const w = getNextMonthWindow(NOW);
  assert.equal(w.start, '2026-06-01');
  assert.equal(w.end, '2026-06-30');
});

test('getNextMonthWindow: Dec 15 2026 → Jan 1..31 2027 (year wrap)', () => {
  const w = getNextMonthWindow(new Date(2026, 11, 15));
  assert.equal(w.start, '2027-01-01');
  assert.equal(w.end, '2027-01-31');
});

test('getNextMonthWindow: Jan 31 2026 → Feb 1..28 2026 (non-leap)', () => {
  const w = getNextMonthWindow(new Date(2026, 0, 31));
  assert.equal(w.start, '2026-02-01');
  assert.equal(w.end, '2026-02-28');
});

test('getNextMonthWindow: Jan 1 2024 → Feb 1..29 2024 (leap)', () => {
  const w = getNextMonthWindow(new Date(2024, 0, 1));
  assert.equal(w.start, '2024-02-01');
  assert.equal(w.end, '2024-02-29');
});

test('getNextMonthWindow: Jan 1 2100 → Feb 1..28 2100 (centennial non-leap)', () => {
  const w = getNextMonthWindow(new Date(2100, 0, 1));
  assert.equal(w.start, '2100-02-01');
  assert.equal(w.end, '2100-02-28');
});

test('eventInNextMonth: June 15 2026 matches', () => {
  assert.equal(eventInNextMonth({ date: '2026-06-15' }, NOW), true);
});

test('eventInNextMonth: June 1 (start) and June 30 (end) match; May 31 and July 1 do not', () => {
  assert.equal(eventInNextMonth({ date: '2026-06-01' }, NOW), true);
  assert.equal(eventInNextMonth({ date: '2026-06-30' }, NOW), true);
  assert.equal(eventInNextMonth({ date: '2026-05-31' }, NOW), false);
  assert.equal(eventInNextMonth({ date: '2026-07-01' }, NOW), false);
});

test('eventInNextMonth: today does NOT match', () => {
  assert.equal(eventInNextMonth({ date: '2026-05-01' }, NOW), false);
});

test('eventInNextMonth: ISO timestamp form matches', () => {
  assert.equal(eventInNextMonth({ date: '2026-06-15T19:00:00Z' }, NOW), true);
});

test('eventInNextMonth: missing/short returns false', () => {
  assert.equal(eventInNextMonth(null, NOW), false);
  assert.equal(eventInNextMonth({}, NOW), false);
  assert.equal(eventInNextMonth({ date: '' }, NOW), false);
  assert.equal(eventInNextMonth({ date: '2026-0' }, NOW), false);
});

test('eventInNextMonth: Dec 31 2026 → Jan 5 2027 matches; Dec 31 itself does not', () => {
  const dec = new Date(2026, 11, 31);
  assert.equal(eventInNextMonth({ date: '2027-01-05' }, dec), true);
  assert.equal(eventInNextMonth({ date: '2026-12-31' }, dec), false);
  assert.equal(eventInNextMonth({ date: '2027-02-01' }, dec), false);
});

test('eventInNextMonth: multi-day event spanning current → next month matches via overlap', () => {
  // Apr 15 → Jun 15 (running through both May and June). Today is May 1.
  // The event is active during all of June, so Next Month should keep it.
  assert.equal(
    eventInNextMonth({ date: '2026-04-15', end_date: '2026-06-15' }, NOW),
    true,
  );
  // Apr 15 → May 31 (ends before next month starts) — does NOT overlap June.
  assert.equal(
    eventInNextMonth({ date: '2026-04-15', end_date: '2026-05-31' }, NOW),
    false,
  );
  // June 15 → July 5 (starts inside next month) — overlaps.
  assert.equal(
    eventInNextMonth({ date: '2026-06-15', end_date: '2026-07-05' }, NOW),
    true,
  );
  // July 1 → July 31 (after next month entirely) — no overlap.
  assert.equal(
    eventInNextMonth({ date: '2026-07-01', end_date: '2026-07-31' }, NOW),
    false,
  );
  // Malformed end < start: treat as single-day (start), so May 31 still won't match.
  assert.equal(
    eventInNextMonth({ date: '2026-05-31', end_date: '2026-05-15' }, NOW),
    false,
  );
});

test('eventInNextMonth: endDate (camelCase) falls back when end_date missing', () => {
  assert.equal(
    eventInNextMonth({ date: '2026-04-15', endDate: '2026-06-15' }, NOW),
    true,
  );
});

test('eventInNextMonth: malformed end_date does NOT cause false positive', () => {
  // Cerebras review 2026-05-01: an Apr 15 event with end_date="TBD" must
  // not match next-month via lex compare ("TBD" > "2026-..." by codepoint).
  assert.equal(
    eventInNextMonth({ date: '2026-04-15', end_date: 'TBD' }, NOW),
    false,
  );
  assert.equal(
    eventInNextMonth({ date: '2026-04-15', end_date: null }, NOW),
    false,
  );
  assert.equal(
    eventInNextMonth({ date: '2026-04-15', end_date: '' }, NOW),
    false,
  );
  assert.equal(
    eventInNextMonth({ date: '2026-04-15', end_date: 12345 }, NOW),
    false,
  );
  // Sanity: well-formed Apr 15 → Jun 15 IS still a match.
  assert.equal(
    eventInNextMonth({ date: '2026-04-15', end_date: '2026-06-15' }, NOW),
    true,
  );
});

test('eventInNextMonth: malformed start date returns false', () => {
  assert.equal(eventInNextMonth({ date: 'TBD' }, NOW), false);
  assert.equal(eventInNextMonth({ date: '04-15-2026' }, NOW), false);
  assert.equal(eventInNextMonth({ date: 12345 }, NOW), false);
});

test('eventInNextMonthAnyOccurrence: recurring event with first occurrence in May matches if it has a June occurrence', () => {
  const recurringFriday = {
    date: '2026-05-08',
    occurrences: [
      '2026-05-08', '2026-05-15', '2026-05-22', '2026-05-29',
      '2026-06-05', '2026-06-12', '2026-06-19', '2026-06-26',
    ],
  };
  assert.equal(eventInNextMonthAnyOccurrence(recurringFriday, NOW), true);
});

test('eventInNextMonthAnyOccurrence: recurring event with only May occurrences does not match', () => {
  const mayOnly = { date: '2026-05-08', occurrences: ['2026-05-08', '2026-05-15'] };
  assert.equal(eventInNextMonthAnyOccurrence(mayOnly, NOW), false);
});

test('eventInNextMonthAnyOccurrence: falls back to .date when occurrences missing', () => {
  assert.equal(eventInNextMonthAnyOccurrence({ date: '2026-06-15' }, NOW), true);
  assert.equal(eventInNextMonthAnyOccurrence({ date: '2026-05-15' }, NOW), false);
});

test('getThisMonthFromTodayWindow: May 15 2026 → 2026-05-15..2026-05-31', () => {
  const w = getThisMonthFromTodayWindow(new Date(2026, 4, 15));
  assert.equal(w.start, '2026-05-15');
  assert.equal(w.end, '2026-05-31');
});

test('getThisMonthFromTodayWindow: Feb 1 2024 → 2024-02-01..2024-02-29 (leap)', () => {
  const w = getThisMonthFromTodayWindow(new Date(2024, 1, 1));
  assert.equal(w.start, '2024-02-01');
  assert.equal(w.end, '2024-02-29');
});

test('dispInThisMonthFromToday: May 5 matches when today is May 1; April 30 does not; June 1 does not', () => {
  assert.equal(dispInThisMonthFromToday('2026-05-05', NOW), true);
  assert.equal(dispInThisMonthFromToday('2026-04-30', NOW), false);
  assert.equal(dispInThisMonthFromToday('2026-06-01', NOW), false);
  assert.equal(dispInThisMonthFromToday('2026-05-01', NOW), true);
});

test('dispInThisMonthFromToday: empty/short input returns false', () => {
  assert.equal(dispInThisMonthFromToday('', NOW), false);
  assert.equal(dispInThisMonthFromToday('2026-05', NOW), false);
});

test('getNextMonthWindow: every month in 2026 has correct window', () => {
  const cases = [
    ['2026-01-15', '2026-02-01', '2026-02-28'],
    ['2026-02-15', '2026-03-01', '2026-03-31'],
    ['2026-03-15', '2026-04-01', '2026-04-30'],
    ['2026-04-15', '2026-05-01', '2026-05-31'],
    ['2026-05-15', '2026-06-01', '2026-06-30'],
    ['2026-06-15', '2026-07-01', '2026-07-31'],
    ['2026-07-15', '2026-08-01', '2026-08-31'],
    ['2026-08-15', '2026-09-01', '2026-09-30'],
    ['2026-09-15', '2026-10-01', '2026-10-31'],
    ['2026-10-15', '2026-11-01', '2026-11-30'],
    ['2026-11-15', '2026-12-01', '2026-12-31'],
    ['2026-12-15', '2027-01-01', '2027-01-31'],
  ];
  for (const [todayStr, expectStart, expectEnd] of cases) {
    const [y, m, d] = todayStr.split('-').map(Number);
    const w = getNextMonthWindow(new Date(y, m - 1, d));
    assert.equal(w.start, expectStart, 'start for today=' + todayStr);
    assert.equal(w.end, expectEnd, 'end for today=' + todayStr);
  }
});
