// Regression test: the dashboard must not render the zero-loss PF sentinel
// (999 / Infinity) as if it were a real profit factor.
// Run: node tests/test_dashboard_pf_sentinel.js
'use strict';

const fs = require('fs');
const path = require('path');
const assert = require('assert');

const jsPath = path.join(__dirname, '..', 'audit_dashboard', 'dashboard_enhancements.js');
const src = fs.readFileSync(jsPath, 'utf8');

// Extract the fmtPF function body and evaluate it in isolation.
const m = src.match(/function\s+fmtPF\s*\([^)]*\)\s*\{[\s\S]*?\n  \}/);
assert.ok(m, 'fmtPF helper must exist in dashboard_enhancements.js');
// eslint-disable-next-line no-eval
const fmtPF = eval('(' + m[0] + ')');

assert.strictEqual(fmtPF(1.5), '1.50', 'normal PF formats to 2dp');
assert.strictEqual(fmtPF(0.0), '0.00', 'zero PF is a real value');
assert.strictEqual(fmtPF(999), 'n/a', '999 sentinel must render n/a');
assert.strictEqual(fmtPF(999.0), 'n/a', '999.0 sentinel must render n/a');
assert.strictEqual(fmtPF(Infinity), 'n/a', 'Infinity must render n/a');
assert.strictEqual(fmtPF(null), 'n/a', 'null must render n/a');
assert.strictEqual(fmtPF(undefined), 'n/a', 'undefined must render n/a');

// The old bare render (which showed 999.00 / Infinity) must be gone.
assert.ok(
  !src.includes("Number(v.pf).toFixed(2)"),
  'bare Number(v.pf).toFixed(2) render must be replaced by fmtPF'
);

console.log('test_dashboard_pf_sentinel: OK');
