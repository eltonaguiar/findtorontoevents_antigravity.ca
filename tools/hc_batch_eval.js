/**
 * Batch-evaluate passesHighConvictionPick for an array of picks (stdin JSON).
 * Usage: node tools/hc_batch_eval.js < picks.json
 * Output: JSON array of booleans, same order as input.
 */
/* eslint-disable @typescript-eslint/no-require-imports */
const path = require('path');
const fs = require('fs');

const hc = require(path.join(__dirname, '..', 'audit_dashboard', 'hc_filter.js'));

function main() {
  const raw = fs.readFileSync(0, 'utf8');
  let picks;
  try {
    picks = JSON.parse(raw);
  } catch (e) {
    console.error('hc_batch_eval: invalid JSON stdin', e.message);
    process.exit(1);
  }
  if (!Array.isArray(picks)) {
    console.error('hc_batch_eval: expected JSON array');
    process.exit(1);
  }
  const out = picks.map((p) => hc.passesHighConvictionPick(p));
  process.stdout.write(JSON.stringify(out));
}

main();
