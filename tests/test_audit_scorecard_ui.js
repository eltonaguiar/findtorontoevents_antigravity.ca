'use strict';
const assert = require('node:assert/strict');
const {test} = require('node:test');
const ui = require('../audit_dashboard/audit_scorecard.js');

test('no invented horizon, certainty or current forecast from a bar timeframe', () => {
  const p = ui.pickPlan({direction:'LONG',entry_price:100,take_profit:110,stop_loss:95,trade_timeframe:'1d'});
  assert.equal(p.geometry, true);
  assert.equal(p.reward_risk, 2);
  assert.match(p.horizon, /unverified/);
  assert.equal(p.signal_at, null);
  assert.equal(Object.hasOwn(p, 'certainty'), false);
});
test('snapshot ages at browser runtime without changing deterministic verdicts', () => {
  const data={source:{snapshot_updated_at:'2026-10-22T22:00:00Z'}};
  assert.equal(ui.effectiveHealth({health:'OK'},data,Date.parse('2026-10-30T22:00:00Z')),'STALE');
  assert.equal(ui.effectiveHealth({health:'EMPTY'},data,Date.parse('2026-10-30T22:00:00Z')),'EMPTY');
  assert.equal(ui.effectiveHealth({health:'BROKEN'},data,Date.parse('2026-10-22T22:00:00Z')),'BROKEN');
  assert.equal(ui.effectiveHealth({health:'OK'},{source:{}},Date.now()),'BROKEN');
});
test('owned evidence never merges same-named strategies across source, class or direction', () => {
  const s={asset_class:'CRYPTO',source_system:'alpha_engine',strategy:'momentum',direction:'LONG'};
  const other={...s,source_system:'other_engine'};
  const keys=[{asset_class:'CRYPTO',source:'alphaengine',strategy:'momentum',direction:'LONG'}];
  assert.deepEqual(ui.filterOwned([s,other,{...s,asset_class:'ETF'},{...s,direction:'SHORT'}],keys),[s]);
  assert.deepEqual(ui.filterOwned([s,{...s,source_system:'AlphaEngine'}],keys),[],
    'ambiguous source normalization must not guess which source owns evidence');
});
test('every authoritative gate has a simple test explanation, not just a code', () => {
  const rules=require('../audit/gates.json');
  for (const key of Object.keys(rules.gates)) {
    const [title,reason]=ui.gateExplanation(key);
    assert.notEqual(title,'Evidence requirement',key);
    assert.ok(reason.length>40,key);
  }
});
test('LONG and SHORT stored exit geometry, explicit maximum holding deadline', () => {
  const p = ui.pickPlan({direction:'SHORT',entry_price:100,take_profit:90,stop_loss:105,max_hold_hours:48});
  assert.equal(p.geometry, true);
  assert.match(p.horizon, /48.00 hours maximum/);
  assert.equal(ui.pickPlan({direction:'SHORT',entry_price:100,take_profit:110,stop_loss:95}).geometry, false);
  assert.equal(ui.pickPlan({direction:'BUY',entry_price:100,take_profit:110,stop_loss:95}).direction, 'LONG');
});
test('zero, empty, nonfinite and missing prices never become valid exits', () => {
  for (const value of [0, null, '', 'NaN', undefined]) {
    assert.equal(ui.pickPlan({direction:'LONG',entry_price:100,take_profit:110,stop_loss:value}).geometry, false);
  }
  assert.equal(ui.number(null), 'unverified');
  assert.equal(ui.number(Infinity), 'unverified');
});
test('only matching versioned verdicts; no fallback top candidates', () => {
  const good = {schema_version:1,source:{},classes:{},strategies:[],top_verified:[],rules_hash:'a'.repeat(64),generated_at:'2026-10-22T22:00:00Z'};
  assert.equal(ui.validate(good, {generated_at:'2026-10-22T22:00:00+00:00'}), good);
  assert.throws(() => ui.validate(good, {generated_at:'2026-10-23T22:00:00Z'}), /snapshot/);
  assert.throws(() => ui.validate({...good, top_verified:[{label:'READY',score:100}]}), /label/);
  assert.throws(() => ui.validate({...good, rules_hash:''}), /contract/);
});
