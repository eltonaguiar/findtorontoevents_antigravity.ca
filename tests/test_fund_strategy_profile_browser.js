'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const html = fs.readFileSync(path.join(__dirname, '../audit_dashboard/funds.html'), 'utf8');
const start = html.indexOf('// ===== FUND STRATEGY PROFILE =====');
const end = html.indexOf('// ===== RENDER: LIVE PICKS =====', start);
const factsStart = html.indexOf('function renderFactSheets()');
const factsEnd = html.indexOf('// ===== DATA LOADING =====', factsStart);

(async () => {
  const browser = await chromium.launch({headless: true});
  try {
    for (const width of [1280, 390]) {
      const page = await browser.newPage({viewport: {width, height: 900}});
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.setContent(html.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, ''));
      await page.addScriptTag({content: `
        const STRAT_INFO = {example: {desc: 'Fixture description', eli5: 'A basket, not a guarantee.'}};
        const D = {systems: [{name: 'qa_fixture', closed_picks: 12, strategies: [{name: 'example'}]}], picks: {active: []}};
        const getTier = () => 'WATCH', riskLevel = () => 3, growth10k = () => 10000;
        const RISK_LABELS = {3: 'Medium'}, pnlClass = () => '', fmt = value => String(value || 0);
        const riskMeterHTML = () => '';
        ${html.slice(start, end)}
        ${html.slice(factsStart, factsEnd)}
        showFundDetail('qa_fixture'); renderFactSheets();
      `});
      const modal = page.locator('#modal-content .strategy-profile');
      assert.equal(await modal.count(), 1);
      assert.match(await modal.innerText(), /Not supplied/);
      await modal.locator('summary').filter({hasText: 'what are we checking'}).click();
      assert.equal(await modal.locator('details').first().getAttribute('open'), '');
      await modal.locator('summary').filter({hasText: 'Methods observed'}).click();
      assert.match(await modal.innerText(), /Fixture description/);
      assert.equal(await page.locator('#factsheets-container .strategy-profile').count(), 1);
      const fits = await modal.evaluate(el => el.scrollWidth <= el.clientWidth + 1);
      assert.ok(fits, `Strategy block fits at width ${width}`);
      assert.deepEqual(errors, []);
      await page.close();
      console.log(`PASS: actual modal and fact-sheet rendering, expandable explanations and layout at ${width}px`);
    }
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
