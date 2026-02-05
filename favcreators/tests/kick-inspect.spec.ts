import { test } from '@playwright/test';

test('Inspect Kick page HTML for live detection patterns', async ({ page }) => {
  console.log('\n========== KICK HTML INSPECTION ==========\n');
  
  for (const user of ['amandasoliss', 'nataliereynolds']) {
    console.log(`\n--- ${user} ---`);
    
    await page.goto(`https://kick.com/${user}`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(3000);
    
    const html = await page.content();
    console.log(`HTML Length: ${html.length}`);
    
    // Check for __NEXT_DATA__
    const nextDataMatch = html.match(/<script\s+id="__NEXT_DATA__"[^>]*>(\{.+?\})<\/script>/s);
    if (nextDataMatch) {
      console.log('__NEXT_DATA__ found!');
      try {
        const data = JSON.parse(nextDataMatch[1]);
        console.log('  Keys:', Object.keys(data).join(', '));
        if (data.props?.pageProps) {
          console.log('  pageProps keys:', Object.keys(data.props.pageProps).join(', '));
          if (data.props.pageProps.channelData) {
            const cd = data.props.pageProps.channelData;
            console.log(`  channelData.is_live: ${cd.is_live}`);
            console.log(`  channelData.livestream: ${cd.livestream ? 'PRESENT' : 'null'}`);
          }
        }
      } catch (e) {
        console.log('  Failed to parse __NEXT_DATA__');
      }
    } else {
      console.log('__NEXT_DATA__ NOT FOUND');
    }
    
    // Check for NUXT data (Kick might use Nuxt instead of Next)
    const nuxtMatch = html.match(/__NUXT[^>]*>([^<]{0,500})/);
    if (nuxtMatch) {
      console.log('NUXT data found (snippet):', nuxtMatch[1].substring(0, 200));
    }
    
    // Check for various patterns
    console.log('\nPattern checks:');
    console.log(`  "livestream":null present: ${html.includes('"livestream":null')}`);
    console.log(`  "livestream":{ present: ${html.includes('"livestream":{')}`);
    console.log(`  "is_live":true present: ${html.includes('"is_live":true')}`);
    console.log(`  "is_live":false present: ${html.includes('"is_live":false')}`);
    console.log(`  >LIVE< present: ${html.includes('>LIVE<')}`);
    console.log(`  >OFFLINE< present: ${html.includes('>OFFLINE<')}`);
    console.log(`  "viewer_count" present: ${html.includes('"viewer_count"')}`);
    console.log(`  is offline text: ${html.toLowerCase().includes('is offline')}`);
    
    // Try to find any JSON-like structures with channel data
    const channelJsonMatch = html.match(/"channel"\s*:\s*\{[^}]{50,200}/);
    if (channelJsonMatch) {
      console.log('\nChannel JSON snippet:', channelJsonMatch[0].substring(0, 150));
    }
    
    // Check for window.__INITIAL_STATE__ or similar
    if (html.includes('__INITIAL_STATE__')) {
      console.log('__INITIAL_STATE__ found in page');
    }
    
    // Look for Nuxt hydration
    if (html.includes('__NUXT_DATA__')) {
      console.log('__NUXT_DATA__ found');
      const nuxtDataMatch = html.match(/<script[^>]*id="__NUXT_DATA__"[^>]*>([^<]+)<\/script>/);
      if (nuxtDataMatch) {
        console.log('NUXT_DATA content (first 500 chars):', nuxtDataMatch[1].substring(0, 500));
      }
    }
    
    // Check page title
    const title = await page.title();
    console.log(`\nPage title: ${title}`);
    
    // Check for live indicator in visible text
    const liveText = await page.locator('text=LIVE').first().isVisible().catch(() => false);
    const offlineText = await page.locator('text=OFFLINE').first().isVisible().catch(() => false);
    console.log(`Visible LIVE text: ${liveText}`);
    console.log(`Visible OFFLINE text: ${offlineText}`);
  }
});
