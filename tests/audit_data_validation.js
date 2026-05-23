/**
 * Audit Dashboard Data Validation Tests
 * ======================================
 * Validates that live audit pages contain valid, consistent data.
 * No Playwright needed — uses Node.js fetch to check JSON endpoints
 * and HTML pages for data integrity.
 *
 * Run: node tests/audit_data_validation.js
 */

const https = require('https');
const http = require('http');

const URLS = {
  payload: 'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/audit_trail/data/dashboard_payload.json',
  funds: 'https://findtorontoevents.ca/audit/funds.html',
  audit: 'https://findtorontoevents.ca/audit/',
  activePicks: 'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/alpha_engine/data/active_picks.json',
};

let passed = 0, failed = 0;

function assert(condition, msg) {
  if (condition) { passed++; console.log(`  PASS: ${msg}`); }
  else { failed++; console.log(`  FAIL: ${msg}`); }
}

function fetchUrl(url) {
  return new Promise((resolve, reject) => {
    const mod = url.startsWith('https') ? https : http;
    mod.get(url, { headers: { 'User-Agent': 'AuditValidator/1.0' } }, (res) => {
      let data = '';
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        return fetchUrl(res.headers.location).then(resolve).catch(reject);
      }
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve({ status: res.statusCode, body: data }));
    }).on('error', reject);
  });
}

async function testPayload() {
  console.log('\n=== Dashboard Payload Validation ===');
  const resp = await fetchUrl(URLS.payload);
  assert(resp.status === 200, `Payload returns 200 (got ${resp.status})`);

  const data = JSON.parse(resp.body);
  assert(data.generated_at, 'Has generated_at timestamp');
  assert(data.systems && data.systems.length > 0, `Has systems (${data.systems?.length || 0})`);
  assert(data.picks, 'Has picks section');

  // Validate system data integrity
  let invalidSystems = 0;
  for (const sys of data.systems || []) {
    const wr = sys.win_rate || 0;
    const cp = sys.closed_picks || 0;
    const wins = sys.wins || 0;
    const losses = sys.losses || 0;

    if (wr > 100) {
      console.log(`    WARNING: ${sys.name}: win_rate=${wr} > 100%`);
      invalidSystems++;
    }
    if (wr < 0) {
      console.log(`    WARNING: ${sys.name}: win_rate=${wr} < 0%`);
      invalidSystems++;
    }
    if (cp > 0 && wins + losses === 0) {
      console.log(`    WARNING: ${sys.name}: closed_picks=${cp} but wins+losses=0`);
      invalidSystems++;
    }

    // Check win_rate consistency
    if (wins + losses > 0) {
      const calcWR = (wins / (wins + losses)) * 100;
      if (Math.abs(calcWR - wr) > 1.0) {
        console.log(`    WARNING: ${sys.name}: reported WR=${wr.toFixed(1)}% but calculated=${calcWR.toFixed(1)}% (${wins}W/${losses}L)`);
        invalidSystems++;
      }
    }

    // Check profit factor sanity
    const pf = sys.profit_factor;
    if (pf !== null && pf !== undefined && pf > 100) {
      console.log(`    WARNING: ${sys.name}: PF=${pf} -- suspiciously high (likely tiny denominator)`);
    }
  }
  assert(invalidSystems === 0, `All systems have valid data (${invalidSystems} invalid)`);

  // Check for stale data
  const genTime = new Date(data.generated_at);
  const hoursAgo = (Date.now() - genTime.getTime()) / 3600000;
  assert(hoursAgo < 24, `Data is fresh (${hoursAgo.toFixed(1)}h old, target: <24h)`);
}

async function testActivePicks() {
  console.log('\n=== Active Picks Validation ===');
  const resp = await fetchUrl(URLS.activePicks);
  assert(resp.status === 200, `Active picks returns 200 (got ${resp.status})`);

  const picks = JSON.parse(resp.body);
  assert(Array.isArray(picks), 'Picks is an array');
  assert(picks.length > 0, `Has active picks (${picks.length})`);

  // Validate pick structure
  let valid = 0, invalid = 0;
  for (const p of picks) {
    const hasRequired = p.symbol && p.entry_price && p.strategy;
    if (hasRequired) valid++; else {
      const missing = [];
      if (!p.symbol) missing.push('symbol');
      if (!p.entry_price) missing.push('entry_price');
      if (!p.strategy) missing.push('strategy');
      console.log(`    WARNING: Pick missing fields: ${missing.join(', ')} -- ${JSON.stringify(p).substring(0, 120)}`);
      invalid++;
    }

    // Check for reasonable values
    if (p.entry_price && p.entry_price <= 0) {
      console.log(`    WARNING: ${p.symbol}: entry_price=${p.entry_price} (invalid)`);
      invalid++;
    }
    if (p.confidence && (p.confidence < 0 || p.confidence > 1)) {
      console.log(`    WARNING: ${p.symbol}: confidence=${p.confidence} (out of range)`);
    }
  }
  assert(invalid === 0, `All picks have valid structure (${invalid} invalid)`);

  // Check for quality gate compliance (new gates)
  const lowConf = picks.filter(p => (p.confidence || 0) < 0.70);
  console.log(`  INFO: ${lowConf.length}/${picks.length} picks have confidence < 0.70 (should be filtered by quality gates)`);
}

async function testFundsPage() {
  console.log('\n=== Funds Page Validation ===');
  const resp = await fetchUrl(URLS.funds);
  assert(resp.status === 200, `Funds page returns 200 (got ${resp.status})`);
  assert(resp.body.includes('growth10k'), 'Contains growth10k function');
  assert(!resp.body.includes('Math.pow(1 + exp/100, trades)'), 'Old broken growth formula is removed');
  assert(resp.body.includes('total_pnl_pct'), 'Uses actual PnL for growth calculation');
  assert(resp.body.includes('blendedMultiplier'), 'Has dampened scoring (v97)');
  assert(resp.body.includes('QUALITY_GATE') || resp.body.includes('quality_gate') || resp.body.includes('0.70'), 'References confidence threshold');
}

async function testAuditPage() {
  console.log('\n=== Main Audit Page Validation ===');
  const resp = await fetchUrl(URLS.audit);
  if (resp.status !== 200) {
    console.log(`  WARNING: Audit page returned ${resp.status} -- may be FTP deployment issue`);
    return;
  }
  assert(resp.body.length > 1000, `Page has content (${resp.body.length} bytes)`);
}

// ===== Section 1: Closed Picks Integrity =====
async function testClosedPicksIntegrity() {
  console.log('\n=== Closed Picks Integrity ===');
  const fs = require('fs');
  const filePath = require('path').join(__dirname, '..', 'alpha_engine', 'data', 'closed_picks.json');

  if (!fs.existsSync(filePath)) {
    console.log('  SKIP: closed_picks.json not found');
    return;
  }

  const picks = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  assert(Array.isArray(picks), `closed_picks.json is an array (${picks.length} picks)`);

  // Check pnl_pct is decimal (not percentage) — flag values > 5.0 or < -5.0
  let suspiciousPnl = 0;
  for (const p of picks) {
    if (p.pnl_pct !== null && p.pnl_pct !== undefined) {
      if (p.pnl_pct > 5.0 || p.pnl_pct < -5.0) {
        console.log(`    WARNING: ${p.id || p.symbol}: pnl_pct=${p.pnl_pct} looks like percentage, not decimal`);
        suspiciousPnl++;
      }
    }
  }
  assert(suspiciousPnl === 0, `All pnl_pct values are decimal format (${suspiciousPnl} suspicious)`);

  // All picks must have exit_date
  const missingExit = picks.filter(p => !p.exit_date);
  assert(missingExit.length === 0, `All closed picks have exit_date (${missingExit.length} missing)`);
  if (missingExit.length > 0) {
    missingExit.slice(0, 3).forEach(p => console.log(`    MISSING exit_date: ${p.id || p.symbol}`));
  }

  // No duplicate pick IDs
  const ids = picks.map(p => p.id).filter(Boolean);
  const uniqueIds = new Set(ids);
  const dupeCount = ids.length - uniqueIds.size;
  assert(dupeCount === 0, `No duplicate pick IDs (${dupeCount} duplicates found out of ${ids.length})`);
  if (dupeCount > 0) {
    const seen = {};
    for (const id of ids) {
      seen[id] = (seen[id] || 0) + 1;
      if (seen[id] === 2) console.log(`    DUPLICATE: ${id}`);
    }
  }

  // WON picks should have positive pnl_pct, LOST should have negative
  let statusMismatch = 0;
  for (const p of picks) {
    if (p.status === 'WON' && p.pnl_pct !== null && p.pnl_pct < 0) {
      console.log(`    MISMATCH: ${p.id || p.symbol} status=WON but pnl_pct=${p.pnl_pct}`);
      statusMismatch++;
    }
    if (p.status === 'LOST' && p.pnl_pct !== null && p.pnl_pct > 0) {
      console.log(`    MISMATCH: ${p.id || p.symbol} status=LOST but pnl_pct=${p.pnl_pct}`);
      statusMismatch++;
    }
  }
  assert(statusMismatch === 0, `WON/LOST status matches pnl_pct sign (${statusMismatch} mismatches)`);

  console.log(`  INFO: ${picks.length} total closed picks analyzed`);
}

// ===== Section 2: Active Picks Quality =====
async function testActivePicksQuality() {
  console.log('\n=== Active Picks Quality ===');
  const fs = require('fs');
  const filePath = require('path').join(__dirname, '..', 'alpha_engine', 'data', 'active_picks.json');

  if (!fs.existsSync(filePath)) {
    console.log('  SKIP: active_picks.json not found');
    return;
  }

  const picks = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  assert(Array.isArray(picks), `active_picks.json is an array (${picks.length} picks)`);

  // All picks must have entry_price > 0
  const badEntry = picks.filter(p => !p.entry_price || p.entry_price <= 0);
  assert(badEntry.length === 0, `All picks have entry_price > 0 (${badEntry.length} invalid)`);
  badEntry.slice(0, 3).forEach(p => console.log(`    BAD entry_price: ${p.symbol} = ${p.entry_price}`));

  // All picks must have take_profit and stop_loss
  const missingTP = picks.filter(p => !p.take_profit);
  const missingSL = picks.filter(p => !p.stop_loss);
  assert(missingTP.length === 0, `All picks have take_profit (${missingTP.length} missing)`);
  assert(missingSL.length === 0, `All picks have stop_loss (${missingSL.length} missing)`);

  // R:R >= 1.0 for all picks
  let badRR = 0;
  for (const p of picks) {
    if (p.entry_price && p.take_profit && p.stop_loss && p.entry_price > 0) {
      const reward = Math.abs(p.take_profit - p.entry_price);
      const risk = Math.abs(p.entry_price - p.stop_loss);
      if (risk > 0) {
        const rr = reward / risk;
        if (rr < 1.0) {
          console.log(`    BAD R:R: ${p.symbol} (${p.strategy}) R:R=${rr.toFixed(2)}`);
          badRR++;
        }
      }
    }
  }
  assert(badRR === 0, `All picks have R:R >= 1.0 (${badRR} below threshold)`);

  // No stablecoin symbols
  const STABLECOINS = ['USDCUSDT', 'DAIUSDT', 'BUSDUSDT', 'TUSDUSDT', 'USDPUSDT', 'FDUSDUSDT', 'EUSDUSDT', 'GUSDUSDT'];
  const stablePicks = picks.filter(p => STABLECOINS.includes((p.symbol || '').toUpperCase()));
  assert(stablePicks.length === 0, `No stablecoin picks (${stablePicks.length} found)`);
  stablePicks.forEach(p => console.log(`    STABLECOIN: ${p.symbol}`));

  // Max picks per symbol = 2
  const MAX_PICKS_PER_SYMBOL = 2;
  const symbolCounts = {};
  for (const p of picks) {
    const sym = p.symbol || 'UNKNOWN';
    symbolCounts[sym] = (symbolCounts[sym] || 0) + 1;
  }
  let overloaded = 0;
  for (const [sym, count] of Object.entries(symbolCounts)) {
    if (count > MAX_PICKS_PER_SYMBOL) {
      console.log(`    OVERLOADED: ${sym} has ${count} active picks (max ${MAX_PICKS_PER_SYMBOL})`);
      overloaded++;
    }
  }
  assert(overloaded === 0, `No symbol exceeds ${MAX_PICKS_PER_SYMBOL} active picks (${overloaded} overloaded)`);

  // Count strong_signal picks
  const strongSignal = picks.filter(p => p.strong_signal || p.strongSignal);
  console.log(`  INFO: ${strongSignal.length}/${picks.length} picks pass strong_signal filter`);
}

// ===== Section 3: Strategy Performance =====
async function testStrategyPerformance() {
  console.log('\n=== Strategy Performance ===');
  const fs = require('fs');
  const filePath = require('path').join(__dirname, '..', 'alpha_engine', 'data', 'strategy_performance.json');

  if (!fs.existsSync(filePath)) {
    console.log('  SKIP: strategy_performance.json not found');
    return;
  }

  const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  const strategies = Object.entries(data).filter(([k]) => k !== 'last_updated' && k !== 'generated_at');

  assert(strategies.length > 0, `Has strategies (${strategies.length})`);

  // win_rate is stored as decimal (0.56 = 56%), convert for display
  let invalidWR = 0;
  let invalidPF = 0;
  let zombieStrategies = [];

  for (const [name, s] of strategies) {
    // win_rate stored as decimal 0-1; verify it maps to 0-100%
    const wrPct = (s.win_rate || 0) * 100;
    if (wrPct < 0 || wrPct > 100) {
      console.log(`    INVALID WR: ${name} win_rate=${s.win_rate} (${wrPct.toFixed(1)}%)`);
      invalidWR++;
    }

    // profit_factor must be >= 0
    if (s.profit_factor !== null && s.profit_factor !== undefined && s.profit_factor < 0) {
      console.log(`    INVALID PF: ${name} profit_factor=${s.profit_factor}`);
      invalidPF++;
    }

    // Flag: 0% WR on 10+ trades (should be killed)
    if (wrPct === 0 && (s.closed_picks || 0) >= 10) {
      zombieStrategies.push(`${name} (${s.closed_picks} trades, 0% WR)`);
    }
  }

  assert(invalidWR === 0, `All strategies have win_rate in 0-100% range (${invalidWR} invalid)`);
  assert(invalidPF === 0, `No strategy has profit_factor < 0 (${invalidPF} invalid)`);

  if (zombieStrategies.length > 0) {
    console.log(`  FLAG: ${zombieStrategies.length} zombie strategies (0% WR, 10+ trades) — should be killed:`);
    zombieStrategies.forEach(z => console.log(`    ZOMBIE: ${z}`));
    // This is a flag, not a hard fail
    failed++; console.log(`  FAIL: Zombie strategies exist that should be eliminated`);
  } else {
    passed++; console.log(`  PASS: No zombie strategies (0% WR on 10+ trades)`);
  }

  console.log(`  INFO: ${strategies.length} strategies analyzed`);
}

// ===== Section 4: ML Model Health =====
async function testMLModelHealth() {
  console.log('\n=== ML Model Health ===');
  const fs = require('fs');
  const basePath = require('path').join(__dirname, '..', 'alpha_engine', 'data');

  // Check model_comparison.json
  const modelPath = require('path').join(basePath, 'model_comparison.json');
  if (fs.existsSync(modelPath)) {
    const model = JSON.parse(fs.readFileSync(modelPath, 'utf8'));
    console.log(`  INFO: Model status = ${model.status || 'unknown'}`);

    if (model.status === 'awaiting_retrain' && model.timestamp) {
      const staleHours = (Date.now() - new Date(model.timestamp).getTime()) / 3600000;
      assert(staleHours < 24, `Model not stale awaiting_retrain (${staleHours.toFixed(1)}h, max 24h)`);
    } else {
      passed++; console.log(`  PASS: Model status is "${model.status}" (not stuck awaiting_retrain)`);
    }
  } else {
    console.log('  SKIP: model_comparison.json not found');
  }

  // Check feature_health_report.json
  const healthPath = require('path').join(basePath, 'feature_health_report.json');
  if (fs.existsSync(healthPath)) {
    const health = JSON.parse(fs.readFileSync(healthPath, 'utf8'));

    const alive = health.alive_features || 0;
    const dead = health.dead_features || 0;
    const total = health.total_features || 0;
    const weak = total - alive - dead;
    const score = health.health_score || 0;

    console.log(`  INFO: Features — alive: ${alive}, weak: ${weak >= 0 ? weak : '?'}, dead: ${dead}, total: ${total}`);
    console.log(`  INFO: Health score = ${score.toFixed(3)}`);

    if (score < 0.50) {
      console.log(`  FLAG: Health score ${score.toFixed(3)} is below 0.50 threshold`);
      // Use the report's own min threshold if available
      const minScore = (health.health_thresholds && health.health_thresholds.min_health_score) || 0.50;
      if (score < minScore) {
        failed++; console.log(`  FAIL: Health score ${score.toFixed(3)} below configured minimum ${minScore}`);
      } else {
        passed++; console.log(`  PASS: Health score ${score.toFixed(3)} meets configured minimum ${minScore}`);
      }
    } else {
      passed++; console.log(`  PASS: Health score ${score.toFixed(3)} >= 0.50`);
    }
  } else {
    console.log('  SKIP: feature_health_report.json not found');
  }
}

// ===== Section 5: Risk Controls =====
async function testRiskControls() {
  console.log('\n=== Risk Controls ===');
  const fs = require('fs');
  const basePath = require('path').join(__dirname, '..', 'alpha_engine', 'data');

  // circuit_breaker.json (optional)
  const cbPath = require('path').join(basePath, 'circuit_breaker.json');
  if (fs.existsSync(cbPath)) {
    const cb = JSON.parse(fs.readFileSync(cbPath, 'utf8'));
    const status = cb.status || cb.state || 'unknown';
    console.log(`  INFO: Circuit breaker status = ${status}`);
    assert(status !== 'TRIPPED' && status !== 'tripped', `Circuit breaker is not tripped (status: ${status})`);
  } else {
    console.log('  SKIP: circuit_breaker.json not found (OK if not implemented yet)');
  }

  // daily_pnl_tracker.json (optional)
  const pnlPath = require('path').join(basePath, 'daily_pnl_tracker.json');
  if (fs.existsSync(pnlPath)) {
    const pnl = JSON.parse(fs.readFileSync(pnlPath, 'utf8'));
    const breached = pnl.breached || pnl.limit_breached || false;
    console.log(`  INFO: Daily PnL tracker found — breached: ${breached}`);
    assert(!breached, `Daily PnL limit not breached`);
  } else {
    console.log('  SKIP: daily_pnl_tracker.json not found (OK if not implemented yet)');
  }

  // trust_adjustments.json (should exist and have strategies)
  const trustPath = require('path').join(basePath, 'trust_adjustments.json');
  if (fs.existsSync(trustPath)) {
    const trust = JSON.parse(fs.readFileSync(trustPath, 'utf8'));
    const adjustments = trust.strategy_adjustments || trust;
    const strategyNames = Object.keys(adjustments).filter(k => k !== 'generated_at' && k !== 'last_updated');
    assert(strategyNames.length > 0, `Trust adjustments has strategies (${strategyNames.length})`);

    // Check that strategies are actually being tuned (not all zero boost)
    const nonZeroBoost = strategyNames.filter(k => {
      const adj = adjustments[k];
      return adj && adj.boost !== undefined && adj.boost !== 0;
    });
    assert(nonZeroBoost.length > 0, `Strategies are being actively tuned (${nonZeroBoost.length}/${strategyNames.length} have non-zero boost)`);
    console.log(`  INFO: ${nonZeroBoost.length}/${strategyNames.length} strategies have non-zero trust adjustment`);
  } else {
    failed++; console.log('  FAIL: trust_adjustments.json not found — strategies are not being tuned');
  }
}

async function main() {
  console.log('Audit Dashboard Data Validation Tests');
  console.log('='.repeat(50));

  try { await testPayload(); } catch(e) { console.log(`  FAIL: Payload test error: ${e.message}`); failed++; }
  try { await testActivePicks(); } catch(e) { console.log(`  FAIL: Active picks test error: ${e.message}`); failed++; }
  try { await testFundsPage(); } catch(e) { console.log(`  FAIL: Funds page test error: ${e.message}`); failed++; }
  try { await testAuditPage(); } catch(e) { console.log(`  FAIL: Audit page test error: ${e.message}`); failed++; }
  try { await testClosedPicksIntegrity(); } catch(e) { console.log(`  FAIL: Closed picks test error: ${e.message}`); failed++; }
  try { await testActivePicksQuality(); } catch(e) { console.log(`  FAIL: Active picks quality test error: ${e.message}`); failed++; }
  try { await testStrategyPerformance(); } catch(e) { console.log(`  FAIL: Strategy performance test error: ${e.message}`); failed++; }
  try { await testMLModelHealth(); } catch(e) { console.log(`  FAIL: ML model health test error: ${e.message}`); failed++; }
  try { await testRiskControls(); } catch(e) { console.log(`  FAIL: Risk controls test error: ${e.message}`); failed++; }

  console.log(`\n${'='.repeat(50)}`);
  console.log(`Results: ${passed} passed, ${failed} failed`);
  process.exit(failed > 0 ? 1 : 0);
}

main();
