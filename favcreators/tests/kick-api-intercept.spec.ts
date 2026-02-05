import { test } from '@playwright/test';

test('Intercept Kick API responses via browser', async ({ page }) => {
  console.log('\n========== KICK API INTERCEPT ==========\n');
  
  // Intercept API calls
  const apiResponses: Record<string, any> = {};
  
  page.on('response', async (response) => {
    const url = response.url();
    if (url.includes('/api/') && url.includes('channels')) {
      try {
        const json = await response.json();
        apiResponses[url] = json;
        console.log(`\nAPI Response from: ${url}`);
        console.log(`  is_live: ${json.is_live}`);
        console.log(`  livestream: ${json.livestream ? 'PRESENT' : 'null'}`);
        if (json.livestream) {
          console.log(`  livestream.is_live: ${json.livestream.is_live}`);
          console.log(`  livestream.viewer_count: ${json.livestream.viewer_count}`);
          console.log(`  livestream.session_title: ${json.livestream.session_title?.substring(0, 50)}`);
        }
      } catch (e) {
        // Not JSON
      }
    }
  });
  
  for (const user of ['amandasoliss', 'nataliereynolds']) {
    console.log(`\n=========== ${user} ===========`);
    
    // Navigate and wait for full load
    await page.goto(`https://kick.com/${user}`, { waitUntil: 'networkidle', timeout: 45000 });
    await page.waitForTimeout(5000);
    
    // After page loads, check visible elements
    const html = await page.content();
    console.log(`\nRendered HTML length: ${html.length}`);
    
    // Look for live/offline indicators in rendered DOM
    const liveIndicator = await page.locator('[class*="live"]').first().textContent().catch(() => null);
    const offlineIndicator = await page.locator('[class*="offline"]').first().textContent().catch(() => null);
    
    console.log(`Live indicator text: ${liveIndicator}`);
    console.log(`Offline indicator text: ${offlineIndicator}`);
    
    // Check page title
    const title = await page.title();
    console.log(`Page title: ${title}`);
    
    // Try to find viewer count
    const viewerCount = await page.locator('[class*="viewer"]').first().textContent().catch(() => null);
    console.log(`Viewer count element: ${viewerCount}`);
    
    // Check for stream title
    const streamTitle = await page.$eval('[class*="stream-title"], [class*="session-title"]', el => el.textContent).catch(() => null);
    console.log(`Stream title: ${streamTitle}`);
    
    // Take a screenshot for debugging
    await page.screenshot({ path: `kick-${user}.png` });
    console.log(`Screenshot saved: kick-${user}.png`);
  }
  
  console.log('\n\nAll API Responses captured:');
  for (const [url, data] of Object.entries(apiResponses)) {
    console.log(`\n${url}:`);
    console.log(JSON.stringify(data, null, 2).substring(0, 1000));
  }
});
