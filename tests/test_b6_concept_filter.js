/**
 * B6 — Concept family filter: unit tests.
 *
 * Run with: node --test tests/test_b6_concept_filter.js
 *
 * Tests:
 *  1. f-concept select has all 9 canonical concept family options
 *  2. matchFilter concept branch: returns false when concept_family mismatches
 *  3. matchFilter concept branch: returns true when concept_family matches
 *  4. matchFilter: fallback to 'standard' when pick.concept_family is absent
 *  5. matchFilter: empty f.concept (All Concepts) passes all picks
 *  6. Clear-filters ID list includes 'f-concept'
 *  7. Event-listener ID list includes 'f-concept'
 */

const { readFileSync } = require('fs');
const { test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('path');

const TEMPLATE_PATH = path.join(__dirname, '..', 'audit_dashboard', 'template.html');
const html = readFileSync(TEMPLATE_PATH, 'utf8');

// ── 1. All concept family options present ────────────────────────────────────
const EXPECTED_CONCEPT_VALUES = [
  'breakout_momentum',
  'mean_reversion',
  'trend_following',
  'value_quality',
  'sentiment_driven',
  'statistical_arb',
  'meme_coin',
  'cta_systematic',
  'standard',
];

test('f-concept select has all canonical concept family options', () => {
  for (const val of EXPECTED_CONCEPT_VALUES) {
    assert.ok(
      html.includes(`value="${val}"`),
      `Missing concept option: value="${val}"`
    );
  }
  assert.ok(html.includes('id="f-concept"'), 'f-concept select missing');
  assert.ok(html.includes('All Concepts'), 'Default "All Concepts" option missing');
});

// ── 2-5. matchFilter concept logic extracted from template ──────────────────
// Minimal matchFilter stub that only tests the concept branch.
function makeMatchFilter(htmlSrc) {
  // Extract the concept check line from matchFilter
  const match = htmlSrc.match(/if \(f\.concept && \(pick\.concept_family \|\| 'standard'\) !== f\.concept\) return false;/);
  return match !== null;
}

test('matchFilter concept check line exists in template', () => {
  assert.ok(
    makeMatchFilter(html),
    'matchFilter concept guard line not found in template.html'
  );
});

// Inline re-implementation of the concept guard for logic testing
function conceptGuardPasses(pick, fConcept) {
  const concept_family = pick.concept_family || 'standard';
  if (fConcept && concept_family !== fConcept) return false;
  return true;
}

test('matchFilter concept: rejects pick with mismatched concept_family', () => {
  const pick = { concept_family: 'breakout_momentum' };
  assert.strictEqual(conceptGuardPasses(pick, 'mean_reversion'), false);
});

test('matchFilter concept: passes pick with matching concept_family', () => {
  const pick = { concept_family: 'breakout_momentum' };
  assert.strictEqual(conceptGuardPasses(pick, 'breakout_momentum'), true);
});

test('matchFilter concept: missing concept_family falls back to standard', () => {
  const pick = {}; // no concept_family field
  assert.strictEqual(conceptGuardPasses(pick, 'standard'), true);
  assert.strictEqual(conceptGuardPasses(pick, 'breakout_momentum'), false);
});

test('matchFilter concept: empty f.concept (All Concepts) passes any pick', () => {
  const pick = { concept_family: 'breakout_momentum' };
  assert.strictEqual(conceptGuardPasses(pick, ''), true);
  assert.strictEqual(conceptGuardPasses({}, ''), true);
});

// ── 6. Clear-filters array includes f-concept ────────────────────────────────
test('clear-filters forEach includes f-concept', () => {
  // Find any forEach block that contains both 'f-concept' and resets values to ''
  const hasConceptInClearArray = html.includes("'f-concept'].forEach(id => {") &&
    html.includes("el(id).value = ''");
  assert.ok(hasConceptInClearArray, "'f-concept' not in clear-filters forEach in template.html");
});

// ── 7. Event-listener array includes f-concept ───────────────────────────────
test('event-listener forEach includes f-concept', () => {
  const listenerBlock = html.match(
    /\['f-asset'.*?'f-concept'\]\.forEach\(id => \{\s*el\(id\)\.addEventListener\('change'/
  );
  assert.ok(listenerBlock, "'f-concept' not in event-listener forEach in template.html");
});
