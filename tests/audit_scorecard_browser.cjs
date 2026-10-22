'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright');
const root = path.resolve(__dirname, '..');
const output = process.env.AUDIT_QA_OUTPUT;
const fixtureDate = '2026-10-22T22:14:47Z';
const stats = (n, extra = {}) => ({
  asset_class:'EQUITY', strategy:'fixture_strategy', source_system:'fixture_only', direction:'LONG',
  label:'FAIL', score:5, n, wins:10, losses:n-10, win_rate:n<20?null:50, pf:1.1,
  pf_ci95:[0.8,1.4],pf_2x_cost:0.9,compound_return_pct:null,sum_trade_pct:4,mdd_pct:null,
  distinct_close_days:15,top_symbol_share:0.4,forward_status:'UNVERIFIED',health:'OK',
  excluded_n:12,exclusion_reasons:{placeholder_flat:12},first_close:'2026-09-01T00:00:00Z',
  last_close:fixtureDate,gates:{S1:{status:'FAIL',reason:'n<100'}},warning:false,recent5:[],inconsistent:false,
  ...extra
});
const snapshot = {
  generated_at:fixtureDate, summary:{total_closed_picks:40}, picks:{recent_closed:[],active:[
    {symbol:'TEST<svg onload=alert(1)>',asset_class:'EQUITY',strategy:'fixture_strategy',direction:'SHORT',
      entry_price:100,take_profit:90,stop_loss:105,trade_timeframe:'SWING',timestamp:fixtureDate}
  ]}
};
const verdicts = {
  schema_version:1,generated_at:fixtureDate,rules_hash:'a'.repeat(64),
  source:{snapshot_updated_at:fixtureDate,first_close:'2026-09-01T00:00:00Z',last_close:fixtureDate,input_closed_n:40,total_closed_n:100,total_known:true,scope:'recent_closed_subset'},
  classes:{CRYPTO:stats(19,{asset_class:'CRYPTO',warning:true}),EQUITY:stats(20),MUTUAL_FUND:stats(0,{health:'EMPTY'}),
    FOREX:stats(21,{health:'BROKEN',error_message:"Access denied for secret_user@10.0.0.1"})},
  strategies:[stats(20)],top_verified:[]
};
const ownedLedger = {
  schema_version:1,updated_at:fixtureDate,locked_at:fixtureDate,policy:'fixture-only',revision:1,
  candidates:{EQUITY:{source:'fixture',strategy:'fixture_strategy',n:20,net_pf:1.1,day_bootstrap_ci95:[-1,1]}},
  summary:{EQUITY:{verdict:'COLLECTING',n:19,active:1,net_pf:1.1,net_mean_pct:0.1,net_usd:10,day_bootstrap_ci95:[-1,1],win_rate:0.5,coinflip_q:1,paired_control:{day_bootstrap_ci95:[-1,1]}}},
  portfolio:{realized_equity_usd:10000,realized_drawdown_pct:0},trades:[
    {asset_class:'EQUITY',symbol:'TEST',observed_at:fixtureDate,entry_at:fixtureDate,entry:100,tp_distance:0.1,sl_distance:0.05,
      direction:'SHORT',control_direction:'LONG',status:'OPEN',expires_at:'2026-10-24T22:14:47Z'}
  ],database_quality:{raw_classes:[],outcome_classes:[],checked_at:fixtureDate,scope:'fixture'},rejections:{},screen:{},errors:[]
};
async function pageFor(browser, options = {}) {
  const page = await browser.newPage({viewport:options.mobile?{width:390,height:844}:{width:1440,height:1000}});
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.route('**/*', route => {
    const url = new URL(route.request().url());
    if (url.pathname === '/audit/' || url.pathname.endsWith('/ghcopilot_paper.html')) {
      const file = options.owned?'audit_dashboard/ghcopilot_paper.html':'audit_dashboard/template.html';
      let html = fs.readFileSync(path.join(root,file),'utf8');
      html = html.replace('// __DASHBOARD_DATA_PLACEHOLDER__', 'window.DASHBOARD_DATA = '+JSON.stringify(options.snapshot||snapshot)+';');
      return route.fulfill({contentType:'text/html',body:html});
    }
    if (url.pathname.endsWith('audit_scorecard.js')) return route.fulfill({contentType:'application/javascript',body:fs.readFileSync(path.join(root,'audit_dashboard/audit_scorecard.js'),'utf8')});
    if (url.pathname.endsWith('verdicts.json')) return route.fulfill(options.unavailable?{status:503,body:'unavailable'}:{contentType:'application/json',body:JSON.stringify(options.verdicts||verdicts)});
    if (url.pathname.endsWith('dashboard_data.json')) return route.fulfill({contentType:'application/json',body:JSON.stringify(options.snapshot||snapshot)});
    if (url.pathname.endsWith('ghcopilot_paper.json')) return route.fulfill({contentType:'application/json',body:JSON.stringify(ownedLedger)});
    return route.fulfill({status:404,body:'unavailable in isolated QA'});
  });
  await page.goto('http://audit.local/audit/'+(options.owned?'ghcopilot_paper.html':''),{waitUntil:'domcontentloaded'});
  return {page,errors};
}
(async () => {
  const browser = await chromium.launch({headless:true});
  try {
    for (const mobile of [false,true]) {
      const {page} = await pageFor(browser,{mobile});
      await page.locator('#top-verified-picks').getByText('No MONEY-READY strategy yet',{exact:true}).waitFor();
      const crypto = page.locator('#crypto-panel');
      assert.match(await crypto.innerText(),/n<20/);
      assert.match(await crypto.innerText(),/Too good to be true/);
      assert.match(await crypto.innerText(),/Compound Return\nunverified/);
      assert.match(await crypto.innerText(),/sum of trade % \(not a return\)/);
      await page.locator('#top-verified-picks').getByText('Plain-English decision: is there a real profit engine?',{exact:true}).waitFor();
      await page.locator('#top-verified-picks summary').filter({hasText:'how close are we'}).click();
      assert.match(await page.locator('#top-verified-picks').innerText(),/no percentage-complete readiness score is honest/);
      assert.match(await page.locator('#top-verified-picks').innerText(),/cannot currently verify beating the S&P 500/);
      const equity = page.locator('#non-crypto-panel article').filter({has:page.getByRole('heading',{name:/^EQUITY \| (OK|STALE)$/})});
      assert.match(await equity.innerText(),/50.00%/);
      assert.doesNotMatch(await equity.innerText(),/Too good to be true/);
      assert.match(await page.locator('#non-crypto-panel').innerText(),/Access denied/);
      assert.doesNotMatch(await page.locator('#non-crypto-panel').innerText(),/secret_user|10\.0\.0\.1/);
      assert.equal(await page.locator('#audit-exit-plans svg').count(),0);
      assert.match(await page.locator('#audit-exit-plans').innerText(),/no maximum holding rule supplied/);
      assert.match(await page.locator('#audit-exit-plans').innerText(),/100.000000 \/ 90.000000 \/ 105.000000/);
      await crypto.locator('summary').filter({hasText:'PF (95% day CI)'}).click();
      assert.match(await crypto.innerText(),/ELI5/);
      const overflows = await page.locator('#top-verified-picks').evaluate(e=>e.scrollWidth>e.clientWidth+1);
      assert.equal(overflows,false,'top section must fit mobile width');
      if(output)await page.screenshot({path:path.join(output,'grok-fixture-'+(mobile?'mobile':'desktop')+'.png')});
      await page.close();
    }
    for (const options of [{unavailable:true},{verdicts:{...verdicts,generated_at:'2026-10-21T22:14:47Z'}}]) {
      const {page}=await pageFor(browser,options);
      await page.locator('#crypto-panel').getByText('verdicts unavailable - no verified performance claim',{exact:true}).waitFor();
      assert.doesNotMatch(await page.locator('#top-verified-picks').innerText(),/fixture_strategy/);
      await page.close();
    }
    const owned=await pageFor(browser,{owned:true});
    await owned.page.locator('#trades').getByText(/TP 90.000000.*SL 105.000000/).waitFor();
    assert.match(await owned.page.locator('#trades').innerText(),/maximum 48 hours/);
    assert.match(await owned.page.locator('#classes').innerText(),/WR n<20/);
    assert.deepEqual(owned.errors,[]);
    await owned.page.close();
    if(process.env.AUDIT_SNAPSHOT&&process.env.AUDIT_VERDICTS){
      const real=await pageFor(browser,{snapshot:JSON.parse(fs.readFileSync(process.env.AUDIT_SNAPSHOT,'utf8')),verdicts:JSON.parse(fs.readFileSync(process.env.AUDIT_VERDICTS,'utf8'))});
      await real.page.locator('#top-verified-picks').getByText('No MONEY-READY strategy yet',{exact:true}).waitFor();
      assert.match(await real.page.locator('#top-verified-picks').innerText(),/3500 of 13162/);
      if(output){
        await real.page.screenshot({path:path.join(output,'grok-after-desktop.png')});
        await real.page.locator('#non-crypto-panel').screenshot({path:path.join(output,'grok-after-cards.png')});
        await real.page.setViewportSize({width:390,height:844});
        await real.page.evaluate(()=>window.scrollTo(0,0));
        await real.page.screenshot({path:path.join(output,'grok-after-mobile.png')});
      }
      await real.page.close();
    }
    console.log('PASS: desktop/mobile, exclusions, n19/20, ELI5, safe errors, snapshot mismatch, unavailable verdicts, paper TP/SL/48h; optional real snapshot');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
