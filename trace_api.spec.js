const { test, expect } = require('@playwright/test');

test('trace all API calls', async ({ page }) => {
  const apiCalls = [];
  
  // Intercept all requests
  page.on('request', request => {
    if (request.url().includes('.php') || request.url().includes('api')) {
      apiCalls.push(request.url());
    }
  });
  
  // Intercept responses
  page.on('response', async response => {
    if (response.url().includes('competition.php')) {
      try {
        const data = await response.json();
        console.log('API Response from:', response.url());
        console.log('Timestamp:', data.timestamp);
        console.log('Algos:', data.algorithms?.length);
        
        // Check dates
        for (const algo of data.algorithms || []) {
          for (const pick of algo.picks || []) {
            if (pick.pickDate === '2026-02-15' || pick.pickDate === '2026-02-01') {
              console.log('WEEKEND PICK:', pick.ticker, pick.pickDate);
            }
          }
        }
      } catch (e) {}
    }
  });
  
  await page.goto('https://findtorontoevents.ca/findstocks/kimis_claw/live.html?_=' + Date.now());
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(3000);
  
  console.log('\nAll API calls:', apiCalls);
});
