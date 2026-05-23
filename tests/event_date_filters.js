/**
 * Standalone, testable copies of the date-window filter math used by the
 * homepage chips ("Next Month", "This Month") in
 * TORONTOEVENTS_ANTIGRAVITY/index.html.
 *
 * The functions in index.html call `new Date()` directly. To keep the unit
 * tests deterministic, the versions here accept an injectable `now`.
 *
 * If you change the filter math in index.html, update this file in lockstep
 * and run:  node --test tests/event_date_filters.unit.test.js
 */

'use strict';

function getNextMonthWindow(now) {
  if (now == null) now = new Date();
  var nextY = now.getFullYear();
  var nextM = now.getMonth() + 1;
  if (nextM > 11) {
    nextM = 0;
    nextY += 1;
  }
  var startStr = nextY + '-' + String(nextM + 1).padStart(2, '0') + '-01';
  var endDay = new Date(nextY, nextM + 1, 0).getDate();
  var endStr =
    nextY +
    '-' +
    String(nextM + 1).padStart(2, '0') +
    '-' +
    String(endDay).padStart(2, '0');
  return { start: startStr, end: endStr };
}

var _YMD_RE = /^\d{4}-\d{2}-\d{2}/;

function eventInNextMonth(eventData, now) {
  if (!eventData || !eventData.date) return false;
  var raw = String(eventData.date);
  if (!_YMD_RE.test(raw)) return false;
  var startYmd = raw.substring(0, 10);
  // Multi-day overlap: event runs [start, end]; treat as in-window iff
  // [start, end] overlaps [window.start, window.end]. end falls back to
  // start when missing OR malformed (non-string, "TBD", null, etc.).
  var rawEnd = eventData.end_date != null ? eventData.end_date :
               (eventData.endDate != null ? eventData.endDate : raw);
  var endYmd = startYmd;
  if (typeof rawEnd === 'string' && _YMD_RE.test(rawEnd)) {
    endYmd = rawEnd.substring(0, 10);
  }
  if (endYmd < startYmd) endYmd = startYmd;
  var w = getNextMonthWindow(now);
  return startYmd <= w.end && endYmd >= w.start;
}

function eventInNextMonthAnyOccurrence(eventData, now) {
  if (!eventData) return false;
  var w = getNextMonthWindow(now);
  if (Array.isArray(eventData.occurrences) && eventData.occurrences.length) {
    for (var i = 0; i < eventData.occurrences.length; i++) {
      var d = String(eventData.occurrences[i] || '');
      if (d.length < 10) continue;
      var ymd = d.substring(0, 10);
      if (ymd >= w.start && ymd <= w.end) return true;
    }
    return false;
  }
  return eventInNextMonth(eventData, now);
}

function getThisMonthFromTodayWindow(now) {
  if (now == null) now = new Date();
  var y = now.getFullYear();
  var m = String(now.getMonth() + 1).padStart(2, '0');
  var d = String(now.getDate()).padStart(2, '0');
  var start = y + '-' + m + '-' + d;
  var lastDay = new Date(y, now.getMonth() + 1, 0).getDate();
  var end = y + '-' + m + '-' + String(lastDay).padStart(2, '0');
  return { start: start, end: end };
}

function dispInThisMonthFromToday(disp, now) {
  if (!disp || disp.length < 10) return false;
  var w = getThisMonthFromTodayWindow(now);
  return disp >= w.start && disp <= w.end;
}

module.exports = {
  getNextMonthWindow: getNextMonthWindow,
  eventInNextMonth: eventInNextMonth,
  eventInNextMonthAnyOccurrence: eventInNextMonthAnyOccurrence,
  getThisMonthFromTodayWindow: getThisMonthFromTodayWindow,
  dispInThisMonthFromToday: dispInThisMonthFromToday,
};
