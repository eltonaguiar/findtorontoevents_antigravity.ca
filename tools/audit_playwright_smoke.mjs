import { chromium } from 'playwright';
const browser = await chromium.launch();
const page = await browser.newContext().then(c => c.newPage());
const errors = [];
page.on('pageerror', e => errors.push(`pageerror: ${e.message}`));
page.on('console', m => { if (m.type() === 'error') errors.push(`console.error: ${m.text()}`); });
try {
  await page.goto('https://findtorontoevents.ca/audit/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(5000);
  const html = await page.content();
  const sportsCount = (html.match(/\bSPORTS\b/g) || []).length;
  const majorGoalVisible = await page.locator('text=/MAJOR GOAL/i').first().isVisible().catch(() => false);
  console.log(JSON.stringify({
    sports_refs: sportsCount,
    major_goal_visible: majorGoalVisible,
    js_errors: errors.length,
    errors: errors.slice(0, 10),
    title: await page.title(),
  }, null, 2));
} catch (e) {
  console.log(JSON.stringify({ goto_error: e.message, errors }, null, 2));
}
await browser.close();
