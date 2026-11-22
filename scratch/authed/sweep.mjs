import { chromium } from 'playwright';
const NAMES={"19422130":"Xbox Series S 512GB","19422127":"Xbox Series S 1TB","20189840":"Xbox Series X 1TB",
"19422129":"Xbox Series X 1TB Digital","20105824":"Xbox Series X 2TB Galaxy","19446111":"PS5 Slim 1TB",
"19446112":"PS5 Slim Digital 825GB","19609594":"PS5 Disc Slim","19492009":"PS5 Pro",
"18477929":"PS5 Pro (alt SKU)","19970410":"PS5 Slim refurb","19827353":"PS5 open-box BO6"};
const browser = await chromium.connectOverCDP('http://localhost:9222');
const ctx = browser.contexts()[0];
const page = ctx.pages()[0] || await ctx.newPage();
// Do NOT navigate: a goto aborted the tab. Reuse the open page and only
// fetch if we are already on the bestbuy.ca origin.
if (!page.url().includes('bestbuy.ca')) {
  console.log(`current tab is ${page.url()} — not bestbuy.ca, cannot use its origin cookies`);
  await browser.close();
  process.exit(0);
}
// Same endpoint, but issued from the bestbuy.ca origin with your session cookies.
const data = await page.evaluate(async (skus) => {
  const u = `https://www.bestbuy.ca/ecomm-api/availability/products?accept=application%2Fvnd.bestbuy.standardproduct.v1%2Bjson&accept-language=en-CA&skus=${skus}&postalCode=M5B2H1`;
  const r = await fetch(u, { headers: { 'Accept': 'application/vnd.bestbuy.standardproduct.v1+json' } });
  return { status: r.status, body: r.ok ? await r.json() : await r.text() };
}, Object.keys(NAMES).join('|'));
console.log(`in-page fetch: HTTP ${data.status}`);
if (data.status === 200 && data.body) {
  const rows = (data.body.availabilities || []).map(a => {
    const sh = a.shipping || {}, pk = a.pickup || {};
    return [NAMES[a.sku] || '?', a.sku, sh.status, sh.quantityRemaining, pk.status];
  }).sort((x, y) => (['InStock','InStockOnlineOnly'].includes(x[2]) ? 0 : 1) - (['InStock','InStockOnlineOnly'].includes(y[2]) ? 0 : 1) || x[0].localeCompare(y[0]));
  for (const [n, s, st, q, pk] of rows) {
    const mark = st === 'InStock' ? 'OK ' : st === 'InStockOnlineOnly' ? 'OK*' : st === 'SoldOutOnline' ? 'X  ' : '?  ';
    console.log(`${mark} ${n.padEnd(26)} ${String(s).padEnd(10)} ${String(st).padEnd(18)} qty=${String(q).padEnd(6)} pickup=${pk}`);
  }
} else { console.log(String(data.body).slice(0, 300)); }
await browser.close();
