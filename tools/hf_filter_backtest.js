#!/usr/bin/env node
/**
 * Thin wrapper: runs `tools/hc_filter_backtest.py` (stdlib json accepts NaN; matches dashboard_hc_rules).
 *
 *   node tools/hf_filter_backtest.js [path/to/closed_picks.json]
 *   npm run backtest:hc-filter
 */
'use strict';

const { spawnSync } = require('child_process');
const path = require('path');

const repo = path.join(__dirname, '..');
const pyScript = path.join(__dirname, 'hc_filter_backtest.py');
const argv = [pyScript];
if (process.argv[2]) {
  argv.push(process.argv[2]);
}
const r = spawnSync('python', argv, { stdio: 'inherit', cwd: repo });
process.exit(r.status === null ? 1 : r.status);
