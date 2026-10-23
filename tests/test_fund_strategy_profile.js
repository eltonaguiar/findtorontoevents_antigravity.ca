'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, '../audit_dashboard/funds.html'), 'utf8');
const start = html.indexOf('// ===== FUND STRATEGY PROFILE =====');
const end = html.indexOf('// ===== RENDER: FUND DETAIL MODAL =====', start);
assert.ok(start >= 0 && end > start, 'Profile implementation is present');
const context = { URL, STRAT_INFO: { exact_rule: {cat: 'Trend', desc: 'Editorial description', eli5: 'Follow a moving train.'} } };
vm.createContext(context);
vm.runInContext(html.slice(start, end), context);
const render = context.renderStrategyProfile;
let out = render({name: 'unknown', strategies: [{name: 'exact_rule_variant'}]});
assert.match(out, /Not supplied/);
assert.doesNotMatch(out, /Editorial description/);
assert.match(out, /not regulated mutual funds/i);
assert.match(out, /does not certify/i);
out = render({strategies: [{name: 'exact_rule'}]});
assert.match(out, /Editorial description/);
assert.match(out, /not an executable specification/);
assert.match(out, /<details>/);
out = render({strategy_profile: {
  objective: '<img src=x onerror=alert(1)>', strategy: 'Hold 30% stocks / 70% bonds.',
  allocation: '30/70', exits: 'Annual rebalance', benchmark: '30/70 comparator',
  source_url: 'javascript:alert(1)', checked_at: '2026-10-23',
  verification: 'Claimed only', eli5: 'A mixed basket.'
}});
assert.match(out, /&lt;img/);
assert.doesNotMatch(out, /<img|href="javascript:/);
assert.match(out, /Hold 30% stocks/);
assert.match(out, /Claimed only/);
assert.match(out, /Annual rebalance/);
assert.match(out, /Source URL unavailable or invalid/);
out = render({strategy_profile: {source_url: 'https://example.org/facts?a=1&b=2'}});
assert.match(out, /href="https:\/\/example.org\/facts\?a=1&amp;b=2"/);
assert.match(out, /rel="noopener noreferrer"/);
for (const source_url of ['https://user:pass@example.org/', 'https://', 'data:text/html,test', '//example.org/']) {
  out = render({strategy_profile: {source_url}});
  assert.match(out, /Source URL unavailable or invalid/);
  assert.doesNotMatch(out, /href=/);
}
for (const value of [null, [], 'bad', 42]) {
  assert.doesNotThrow(() => render({strategy_profile: value, strategies: value}));
}
out = render({strategies: [null, {}, {name: 42}, {name: 'exact_rule'}, {name: 'exact_rule'}]});
assert.match(out, /Methods observed in this system \(1\)/);
const many = Array.from({length: 15}, (_, i) => ({name: `rule_${i}`}));
out = render({strategies: many});
assert.match(out, /5 additional strategies/);
assert.doesNotMatch(out, /rule_14/);
assert.match(html, /h \+= renderStrategyProfile\(sys\)/);
assert.match(html, /\$\{renderStrategyProfile\(sys\)\}/);
for (const script of html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)) {
  new vm.Script(script[1]);
}
console.log('PASS: strategy profile metadata, missing rules, exact lookup, escaping, sources, limits, wiring and page syntax');
