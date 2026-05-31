#!/usr/bin/env node
'use strict';
/** Read JSON pick from argv[2] or stdin; print JSON {pass: boolean}. */
const path = require('path');
const { passesHighConvictionPick, resetHcGateParamsCache } = require(
  path.join(__dirname, '..', 'audit_dashboard', 'hc_filter.js')
);
resetHcGateParamsCache();

function readInput() {
  if (process.argv[2]) {
    return JSON.parse(process.argv[2]);
  }
  const chunks = [];
  process.stdin.on('data', (c) => chunks.push(c));
  return new Promise((resolve, reject) => {
    process.stdin.on('end', () => {
      try {
        resolve(JSON.parse(Buffer.concat(chunks).toString('utf8')));
      } catch (e) {
        reject(e);
      }
    });
  });
}

(async () => {
  const pick = await readInput();
  const pass = passesHighConvictionPick(pick);
  process.stdout.write(JSON.stringify({ pass: !!pass }));
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
