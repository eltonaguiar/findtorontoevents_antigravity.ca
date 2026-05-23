const assert = require('assert');

function hasExplicitTZ(str) {
  return /(?:Z|[+\-]\d{2}:?\d{2})$/i.test((str || '').trim());
}

function toEST(d) {
  const dt = d instanceof Date ? d : new Date(d);
  if (Number.isNaN(dt.getTime())) return null;
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/New_York',
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
    hour: 'numeric',
    minute: 'numeric',
    second: 'numeric',
    hour12: false,
  }).formatToParts(dt);
  const p = {};
  for (const part of parts) p[part.type] = part.value;
  let hr = parseInt(p.hour, 10);
  if (hr === 24) hr = 0;
  return new Date(
    parseInt(p.year, 10),
    parseInt(p.month, 10) - 1,
    parseInt(p.day, 10),
    hr,
    parseInt(p.minute, 10),
    parseInt(p.second, 10),
  );
}

function estDateStr(d) {
  const e = toEST(d);
  if (!e || Number.isNaN(e.getTime())) return '';
  const y = e.getFullYear();
  const m = String(e.getMonth() + 1).padStart(2, '0');
  const day = String(e.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function parseCommenceTime(ct) {
  return new Date(`${ct}${hasExplicitTZ(ct) ? '' : ' UTC'}`);
}

function run() {
  const negOffset = '2026-05-04T00:30:00-04:00';
  const zulu = '2026-05-04T04:30:00Z';
  const noTz = '2026-05-04 04:30:00';

  const parsedNeg = parseCommenceTime(negOffset);
  const parsedZulu = parseCommenceTime(zulu);
  const parsedNoTz = parseCommenceTime(noTz);

  assert.ok(!Number.isNaN(parsedNeg.getTime()), 'negative-offset time should parse');
  assert.ok(!Number.isNaN(parsedZulu.getTime()), 'zulu time should parse');
  assert.ok(!Number.isNaN(parsedNoTz.getTime()), 'no-timezone time should parse with UTC suffix');

  assert.strictEqual(estDateStr(parsedNeg), '2026-05-04');
  assert.strictEqual(estDateStr(parsedZulu), '2026-05-04');
  assert.strictEqual(estDateStr(parsedNoTz), '2026-05-04');

  console.log('sports_date_bucketing_regression: PASS');
}

run();
