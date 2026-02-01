import { test, expect } from '@playwright/test';

const BASE = 'http://127.0.0.1:9000';
const EVENTS_GRID = '#events-grid';
const REACT_LOAD_WAIT_MS = 30000;

test.describe('Debug events loading at 127.0.0.1:9000', () => {
  test('inspect: log network + console and assert events load', async ({ page }) => {
    const networkLog: { url: string; status?: number }[] = [];
    const consoleLog: { type: string; text: string }[] = [];

    page.on('request', (req) => {
      const url = req.url();
      if (url.includes('events.json') || url.includes('chunks/') || url.includes('js-proxy'))
        networkLog.push({ url });
    });
    page.on('response', async (res) => {
      const url = res.url();
      if (url.includes('events.json') || url.includes('chunks/') || url.includes('js-proxy')) {
        const idx = networkLog.findIndex((n) => n.url === url);
        if (idx >= 0) networkLog[idx].status = res.status();
      }
    });
    page.on('console', (msg) => {
      consoleLog.push({ type: msg.type(), text: msg.text() });
    });

    await page.goto(BASE + '/', { waitUntil: 'networkidle', timeout: 20000 });

    // Wait for events grid and cards
    const grid = page.locator(EVENTS_GRID);
    await expect(grid).toBeVisible({ timeout: 5000 });
    // Event cards: links to event URLs or elements with event-card class
    const eventLinks = grid.locator('a[href*="http"]').or(grid.locator('[class*="event-card"], [class*="EventCard"]'));
    await expect(eventLinks.first()).toBeVisible({ timeout: REACT_LOAD_WAIT_MS });

    const cardCount = await eventLinks.count();
    expect(cardCount).toBeGreaterThan(0);

    // Log diagnostics
    const eventsReq = networkLog.filter((n) => n.url.includes('events.json'));
    const chunkReqs = networkLog.filter((n) => n.url.includes('chunks') || n.url.includes('js-proxy'));
    console.log('events.json requests:', eventsReq.length, eventsReq.map((r) => ({ url: r.url, status: r.status })));
    console.log('chunk requests (sample):', chunkReqs.slice(0, 5).map((r) => ({ url: r.url, status: r.status })));
    const errs = consoleLog.filter((c) => c.type === 'error');
    if (errs.length) console.log('console errors:', errs.slice(0, 10));
  });
});
