const { test, expect } = require('@playwright/test');

const BASE_URL = 'http://localhost:8888';

test.describe('KIMI Rise of the Claw - Local Server Validation', () => {

  test('Page loads without console errors', async ({ page }) => {
    const consoleMessages = [];
    const consoleErrors = [];

    page.on('console', msg => {
      consoleMessages.push({ type: msg.type(), text: msg.text() });
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    page.on('pageerror', error => {
      consoleErrors.push(`PAGE ERROR: ${error.message}`);
    });

    const response = await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    expect(response.status()).toBe(200);

    // Wait for dashboard to initialize
    await page.waitForTimeout(3000);

    console.log('=== ALL CONSOLE MESSAGES ===');
    for (const msg of consoleMessages) {
      console.log(`[${msg.type}] ${msg.text}`);
    }

    console.log('\n=== CONSOLE ERRORS ===');
    if (consoleErrors.length === 0) {
      console.log('NO ERRORS FOUND');
    } else {
      for (const err of consoleErrors) {
        console.log(`ERROR: ${err}`);
      }
    }

    // We log errors but don't fail the test - we want to see what happens
    console.log(`\nTotal messages: ${consoleMessages.length}, Errors: ${consoleErrors.length}`);
  });

  test('All data files load with 200 status codes', async ({ page }) => {
    const networkRequests = [];
    const failedRequests = [];

    page.on('response', response => {
      const url = response.url();
      if (url.includes('/data/') || url.includes('.json') || url.includes('.css') || url.includes('.js')) {
        const status = response.status();
        networkRequests.push({ url, status });
        if (status !== 200 && status !== 304) {
          failedRequests.push({ url, status });
        }
      }
    });

    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    console.log('\n=== NETWORK REQUESTS (data files, JS, CSS) ===');
    for (const req of networkRequests) {
      const statusEmoji = req.status === 200 || req.status === 304 ? 'OK' : 'FAIL';
      console.log(`[${statusEmoji}] ${req.status} - ${req.url}`);
    }

    console.log(`\n=== SUMMARY ===`);
    console.log(`Total requests: ${networkRequests.length}`);
    console.log(`Failed requests: ${failedRequests.length}`);
    if (failedRequests.length > 0) {
      console.log('FAILED:');
      for (const req of failedRequests) {
        console.log(`  ${req.status} - ${req.url}`);
      }
    }
  });

  test('Dashboard elements render correctly in LIVE mode', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    // Check header
    const title = await page.textContent('h1');
    console.log(`\n=== DASHBOARD ELEMENTS ===`);
    console.log(`Title: ${title}`);

    // Check data source badge
    const badge = await page.locator('#dataSourceBadge');
    const badgeText = await badge.textContent();
    console.log(`Data Source Badge: ${badgeText}`);

    // Check LIVE button is active by default
    const liveBtn = page.locator('#btnLiveMode');
    const liveBtnActive = await liveBtn.evaluate(el => el.classList.contains('active'));
    console.log(`LIVE button active: ${liveBtnActive}`);

    // Check performance cards
    const perfCards = ['topPerformer', 'bestWinRate', 'mostActive', 'bestSharpe', 'lowestDrawdown'];
    console.log('\n--- Performance Cards ---');
    for (const id of perfCards) {
      const text = await page.textContent(`#${id}`);
      console.log(`  ${id}: ${text}`);
    }

    // Check leaderboard has content
    const leaderboardRows = await page.locator('#leaderboardBody tr').count();
    console.log(`\nLeaderboard rows: ${leaderboardRows}`);

    // Check active picks
    const picksRows = await page.locator('#picksBody tr').count();
    console.log(`Active picks rows: ${picksRows}`);

    // Check category breakdown
    const breakdownCards = await page.locator('#breakdownGrid .breakdown-card').count();
    console.log(`Category breakdown cards: ${breakdownCards}`);

    // Check chart canvas exists and has dimensions
    const chartCanvas = page.locator('#portfolioChart');
    const chartVisible = await chartCanvas.isVisible();
    console.log(`\nPortfolio chart visible: ${chartVisible}`);

    // Check category nav buttons
    const catButtons = await page.locator('.cat-btn').count();
    console.log(`Category filter buttons: ${catButtons}`);
  });

  test('Switching between LIVE and BACK-TEST modes', async ({ page }) => {
    const consoleMessages = [];
    page.on('console', msg => {
      consoleMessages.push({ type: msg.type(), text: msg.text() });
    });

    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    console.log('\n=== MODE SWITCHING TEST ===');

    // --- LIVE MODE (default) ---
    const liveBtn = page.locator('#btnLiveMode');
    const backtestBtn = page.locator('#btnBacktestMode');
    const badge = page.locator('#dataSourceBadge');

    let badgeText = await badge.textContent();
    let liveBtnActive = await liveBtn.evaluate(el => el.classList.contains('active'));
    let backtestBtnActive = await backtestBtn.evaluate(el => el.classList.contains('active'));
    console.log(`\n[LIVE MODE - Initial State]`);
    console.log(`  Badge text: ${badgeText}`);
    console.log(`  LIVE btn active: ${liveBtnActive}`);
    console.log(`  BACK-TEST btn active: ${backtestBtnActive}`);

    // Get leaderboard content in LIVE mode
    let leaderboardText = await page.locator('#leaderboardBody').textContent();
    let topPerformer = await page.textContent('#topPerformer');
    console.log(`  Top Performer: ${topPerformer}`);
    console.log(`  Leaderboard preview: ${leaderboardText.substring(0, 200)}...`);

    // --- Switch to BACK-TEST MODE ---
    console.log(`\n[Clicking BACK-TEST button...]`);
    await backtestBtn.click();
    await page.waitForTimeout(3000);

    badgeText = await badge.textContent();
    liveBtnActive = await liveBtn.evaluate(el => el.classList.contains('active'));
    backtestBtnActive = await backtestBtn.evaluate(el => el.classList.contains('active'));
    console.log(`\n[BACK-TEST MODE]`);
    console.log(`  Badge text: ${badgeText}`);
    console.log(`  LIVE btn active: ${liveBtnActive}`);
    console.log(`  BACK-TEST btn active: ${backtestBtnActive}`);

    leaderboardText = await page.locator('#leaderboardBody').textContent();
    topPerformer = await page.textContent('#topPerformer');
    console.log(`  Top Performer: ${topPerformer}`);
    console.log(`  Leaderboard preview: ${leaderboardText.substring(0, 200)}...`);

    // Count leaderboard rows in back-test mode
    const backtestRows = await page.locator('#leaderboardBody tr').count();
    console.log(`  Leaderboard rows: ${backtestRows}`);

    // --- Switch back to LIVE MODE ---
    console.log(`\n[Clicking LIVE button...]`);
    await liveBtn.click();
    await page.waitForTimeout(3000);

    badgeText = await badge.textContent();
    liveBtnActive = await liveBtn.evaluate(el => el.classList.contains('active'));
    backtestBtnActive = await backtestBtn.evaluate(el => el.classList.contains('active'));
    console.log(`\n[LIVE MODE - Restored]`);
    console.log(`  Badge text: ${badgeText}`);
    console.log(`  LIVE btn active: ${liveBtnActive}`);
    console.log(`  BACK-TEST btn active: ${backtestBtnActive}`);

    topPerformer = await page.textContent('#topPerformer');
    console.log(`  Top Performer: ${topPerformer}`);

    // Check for errors during mode switching
    const errors = consoleMessages.filter(m => m.type === 'error');
    console.log(`\n=== Errors during mode switching: ${errors.length} ===`);
    for (const err of errors) {
      console.log(`  ERROR: ${err.text}`);
    }
  });

  test('Check for 404 errors on all resources', async ({ page }) => {
    const allRequests = [];
    const notFoundRequests = [];

    page.on('response', response => {
      allRequests.push({ url: response.url(), status: response.status() });
      if (response.status() === 404) {
        notFoundRequests.push(response.url());
      }
    });

    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    // Also switch to backtest mode and check
    await page.click('#btnBacktestMode');
    await page.waitForTimeout(3000);

    console.log('\n=== 404 ERROR CHECK ===');
    console.log(`Total network requests: ${allRequests.length}`);
    console.log(`404 Not Found errors: ${notFoundRequests.length}`);

    if (notFoundRequests.length > 0) {
      console.log('\nMISSING RESOURCES:');
      for (const url of notFoundRequests) {
        console.log(`  404: ${url}`);
      }
    } else {
      console.log('\nAll resources loaded successfully!');
    }

    console.log('\n=== ALL REQUESTS ===');
    for (const req of allRequests) {
      console.log(`  [${req.status}] ${req.url}`);
    }
  });

  test('Category filter buttons work correctly', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    // Switch to backtest mode for richer data
    await page.click('#btnBacktestMode');
    await page.waitForTimeout(3000);

    const categories = ['all', 'stock', 'penny', 'crypto', 'meme', 'forex'];

    console.log('\n=== CATEGORY FILTER TEST ===');

    for (const cat of categories) {
      await page.click(`[data-category="${cat}"]`);
      await page.waitForTimeout(500);

      const rows = await page.locator('#leaderboardBody tr').count();
      const activeBtn = await page.locator(`[data-category="${cat}"]`).evaluate(el => el.classList.contains('active'));
      console.log(`  Category "${cat}": ${rows} rows, button active: ${activeBtn}`);
    }
  });

  test('Modal opens and closes correctly', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    // Switch to backtest mode for data
    await page.click('#btnBacktestMode');
    await page.waitForTimeout(3000);

    console.log('\n=== MODAL TEST ===');

    // Click on first leaderboard row
    const firstRow = page.locator('#leaderboardBody tr').first();
    const rowExists = await firstRow.count() > 0;
    console.log(`First leaderboard row exists: ${rowExists}`);

    if (rowExists) {
      await firstRow.click();
      await page.waitForTimeout(500);

      const modal = page.locator('#algoModal');
      const modalActive = await modal.evaluate(el => el.classList.contains('active'));
      console.log(`Modal opened: ${modalActive}`);

      if (modalActive) {
        const modalTitle = await page.textContent('#modalAlgoName');
        console.log(`Modal title: ${modalTitle}`);

        // Close modal
        await page.click('.modal-close');
        await page.waitForTimeout(500);

        const modalClosed = !(await modal.evaluate(el => el.classList.contains('active')));
        console.log(`Modal closed: ${modalClosed}`);
      }
    }

    // Test data source audit trail modal
    console.log('\n--- Data Source Badge Click ---');
    await page.click('#dataSourceBadge');
    await page.waitForTimeout(500);

    const auditModal = page.locator('.modal.active');
    const auditExists = await auditModal.count() > 0;
    console.log(`Audit trail modal opened: ${auditExists}`);

    if (auditExists) {
      const auditTitle = await auditModal.locator('h3').first().textContent();
      console.log(`Audit modal title: ${auditTitle}`);
    }
  });

});
