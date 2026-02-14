import { test, expect } from '@playwright/test';

const PAGES = [
  { name: 'picks.html', url: '/findstocks/portfolio2/picks.html', btnText: 'View Audit Trail', required: true },
  { name: 'horizon-picks.html', url: '/findstocks/portfolio2/horizon-picks.html', btnText: 'View Audit Trail', required: false },
  { name: 'consolidated.html', url: '/findstocks/portfolio2/consolidated.html', btnText: 'Audit Trail', required: true },
];

for (const pg of PAGES) {
  test(`Audit Trail works on ${pg.name}`, async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(`PageError: ${err.message}`));
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(`ConsoleError: ${msg.text()}`);
    });

    await page.goto('https://findtorontoevents.ca' + pg.url, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(4000);

    // Check buttons exist
    const auditButtons = page.locator(`button:has-text("${pg.btnText}")`);
    const count = await auditButtons.count();
    console.log(`[${pg.name}] Found ${count} audit trail buttons`);
    if (pg.required) {
      expect(count).toBeGreaterThan(0);
    } else if (count === 0) {
      console.log(`[${pg.name}] No picks loaded (empty data) — skipping modal test`);
      return;
    }

    // Click the first button
    await auditButtons.first().click();
    await page.waitForTimeout(2000);

    // Check modal appeared
    const modal = page.locator('#auditModal');
    await expect(modal).toBeVisible();

    // Check modal has content (not error)
    const modalText = await modal.textContent();
    console.log(`[${pg.name}] Modal: ${modalText?.substring(0, 200)}`);

    // Should NOT have "Error parsing"
    expect(modalText).not.toContain('Error parsing audit data');

    // Should have audit content or "No audit trail found"
    const hasContent = modalText?.includes('Algorithm:') || modalText?.includes('No audit trail found') || modalText?.includes('stock_picks');
    expect(hasContent).toBeTruthy();

    // Close modal
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);

    // Check no JS errors from our code (filter noise)
    const realErrors = errors.filter(e => !e.includes('favicon') && !e.includes('net::') && !e.includes('ERR_') && !e.includes('modsecurity'));
    console.log(`[${pg.name}] JS errors: ${realErrors.length}`, realErrors);
    expect(realErrors.length).toBe(0);
  });
}
