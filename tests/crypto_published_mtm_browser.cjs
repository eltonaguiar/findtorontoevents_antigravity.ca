const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright');

(async () => {
  const root = path.resolve(__dirname, '..');
  const html = fs.readFileSync(path.join(root, 'audit_dashboard/opencode_paper_trading.html'), 'utf8');
  const results = JSON.parse(fs.readFileSync(path.join(root, 'audit_dashboard/data/published_strategy_gates.json'), 'utf8'));
  const browser = await chromium.launch({headless: true});
  try {
    for (const width of [1440, 390]) {
      const page = await browser.newPage({viewport: {width, height: 900}});
      let mode = 'valid';
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.route('https://btc-mtm.test/**', route => {
        if (route.request().url().endsWith('/data/published_strategy_gates.json')) {
          const copy = structuredClone(results);
          const btc = copy.find(row => row.label === 'BTC 12-month absolute momentum');
          if (mode === 'old') btc.equity_basis = 'completed_trades_only';
          if (mode === 'string') btc.mdd = '81.74';
          if (mode === 'error') return route.fulfill({status: 500, body: 'private diagnostic'});
          return route.fulfill({contentType: 'application/json', body: JSON.stringify(copy)});
        }
        return route.fulfill({contentType: 'text/html', body: html});
      });
      await page.goto('https://btc-mtm.test/opencode_paper_trading.html');
      const host = page.locator('#btc-mtm-evidence');
      await host.locator('table').waitFor();
      assert.match(await host.innerText(), /81\.74% loss/);
      assert.match(await host.innerText(), /53\.35%/);
      assert.match(await host.innerText(), /WR hidden/);
      assert.match(await host.innerText(), /unverified - cannot pass/);
      assert.doesNotMatch(await host.innerText(), /12\.5%|94\.87|7\/9/);
      const detail = page.locator('details').filter({has: page.locator('summary', {hasText: 'what changed and what does it mean?'})});
      await detail.locator('summary').click();
      assert.match(await detail.innerText(), /roller-coaster/);
      for (mode of ['old', 'string', 'error']) {
        await page.reload();
        await page.waitForFunction(() => document.querySelector('#btc-mtm-evidence').textContent.includes('verdicts unavailable'));
        assert.equal(await host.locator('table').count(), 0);
        assert.doesNotMatch(await host.innerText(), /private diagnostic/);
      }
      assert.deepEqual(errors, []);
      await page.close();
    }
    console.log('PASS: desktop/mobile real rebuilt BTC results, expandable ELI5, old/string/error evidence fails closed');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
