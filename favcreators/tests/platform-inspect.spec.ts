import { test } from '@playwright/test';

test.describe('Platform Live Detection Inspection', () => {
  
  test('Twitch - jynxzi (LIVE) vs pokimane (OFFLINE)', async ({ page }) => {
    console.log('\n========== TWITCH INSPECTION ==========\n');
    
    // LIVE user
    console.log('--- jynxzi (should be LIVE) ---');
    await page.goto('https://www.twitch.tv/jynxzi', { waitUntil: 'domcontentloaded', timeout: 20000 });
    await page.waitForTimeout(3000);
    
    let html = await page.content();
    console.log(`HTML Length: ${html.length}`);
    console.log(`Contains "isLiveBroadcast":true: ${html.includes('"isLiveBroadcast":true')}`);
    console.log(`Contains "isLive":true: ${html.includes('"isLive":true')}`);
    console.log(`Contains "offline": ${html.toLowerCase().includes('offline')}`);
    console.log(`Contains "currently offline": ${html.includes('currently offline')}`);
    console.log(`Contains "persistent-player": ${html.includes('persistent-player')}`);
    console.log(`Contains "video-player": ${html.includes('video-player')}`);
    console.log(`Contains viewer count pattern: ${/\d+[\d,]*\s*(viewer|watching)/i.test(html)}`);
    
    // Extract og:description
    const ogDesc1 = await page.$eval('meta[property="og:description"]', el => el.getAttribute('content')).catch(() => null);
    console.log(`og:description: ${ogDesc1?.substring(0, 100)}`);
    
    // OFFLINE user
    console.log('\n--- pokimane (should be OFFLINE) ---');
    await page.goto('https://www.twitch.tv/pokimane', { waitUntil: 'domcontentloaded', timeout: 20000 });
    await page.waitForTimeout(3000);
    
    html = await page.content();
    console.log(`HTML Length: ${html.length}`);
    console.log(`Contains "isLiveBroadcast":true: ${html.includes('"isLiveBroadcast":true')}`);
    console.log(`Contains "isLive":true: ${html.includes('"isLive":true')}`);
    console.log(`Contains "offline": ${html.toLowerCase().includes('offline')}`);
    console.log(`Contains "currently offline": ${html.includes('currently offline')}`);
    console.log(`Contains "persistent-player": ${html.includes('persistent-player')}`);
    
    const ogDesc2 = await page.$eval('meta[property="og:description"]', el => el.getAttribute('content')).catch(() => null);
    console.log(`og:description: ${ogDesc2?.substring(0, 100)}`);
  });

  test('Kick - amandasoliss (LIVE) vs nataliereynolds (OFFLINE)', async ({ page, request }) => {
    console.log('\n========== KICK INSPECTION ==========\n');
    
    // Try API directly (might be blocked)
    console.log('--- Testing Kick API ---');
    
    for (const user of ['amandasoliss', 'nataliereynolds']) {
      console.log(`\n--- ${user} ---`);
      
      // Try page first
      await page.goto(`https://kick.com/${user}`, { waitUntil: 'domcontentloaded', timeout: 20000 });
      await page.waitForTimeout(4000);
      
      const html = await page.content();
      console.log(`HTML Length: ${html.length}`);
      console.log(`Contains "is_live":true: ${html.includes('"is_live":true')}`);
      console.log(`Contains "livestream": ${html.includes('"livestream"')}`);
      console.log(`Contains LIVE badge: ${html.includes('>LIVE<') || html.includes('live-indicator')}`);
      console.log(`Contains "offline": ${html.toLowerCase().includes('offline')}`);
      
      // Check for NUXT data
      const nuxtMatch = html.match(/__NUXT_DATA__[^>]*>([^<]{0,2000})/);
      if (nuxtMatch) {
        console.log(`NUXT_DATA snippet: ${nuxtMatch[1].substring(0, 300)}...`);
      }
      
      // Try to find viewer count
      const viewerMatch = html.match(/(\d+[\d,]*)\s*(?:viewer|watching)/i);
      if (viewerMatch) {
        console.log(`Viewer count found: ${viewerMatch[1]}`);
      }
    }
  });

  test('YouTube - video URL (LIVE) vs channel (OFFLINE)', async ({ page }) => {
    console.log('\n========== YOUTUBE INSPECTION ==========\n');
    
    // LIVE - video URL
    console.log('--- Video 2Q_MTz0ObVA (should be LIVE) ---');
    await page.goto('https://www.youtube.com/watch?v=2Q_MTz0ObVA', { waitUntil: 'domcontentloaded', timeout: 20000 });
    await page.waitForTimeout(4000);
    
    let html = await page.content();
    console.log(`HTML Length: ${html.length}`);
    console.log(`Contains "isLiveBroadcast":true: ${html.includes('"isLiveBroadcast":true')}`);
    console.log(`Contains "isLive":true: ${html.includes('"isLive":true')}`);
    console.log(`Contains "isLiveContent":true: ${html.includes('"isLiveContent":true')}`);
    console.log(`Contains "liveStreamability": ${html.includes('liveStreamability')}`);
    console.log(`Contains "LIVE NOW" or similar: ${html.includes('LIVE') || html.includes('Live')}`);
    console.log(`Contains "BADGE_STYLE_TYPE_LIVE_NOW": ${html.includes('BADGE_STYLE_TYPE_LIVE_NOW')}`);
    
    // Try to extract ytInitialPlayerResponse
    const playerMatch = html.match(/ytInitialPlayerResponse\s*=\s*(\{.+?\});/s);
    if (playerMatch) {
      try {
        const playerData = JSON.parse(playerMatch[1]);
        console.log(`ytInitialPlayerResponse.videoDetails.isLive: ${playerData?.videoDetails?.isLive}`);
        console.log(`ytInitialPlayerResponse.videoDetails.isLiveContent: ${playerData?.videoDetails?.isLiveContent}`);
        console.log(`Has liveStreamability: ${!!playerData?.playabilityStatus?.liveStreamability}`);
      } catch(e) {
        console.log('Could not parse ytInitialPlayerResponse');
      }
    }
    
    // OFFLINE - channel /live page
    console.log('\n--- @tobedeleted2030 (should be OFFLINE) ---');
    await page.goto('https://www.youtube.com/@tobedeleted2030/live', { waitUntil: 'domcontentloaded', timeout: 20000 });
    await page.waitForTimeout(4000);
    
    html = await page.content();
    const title = await page.title();
    console.log(`Title: ${title}`);
    console.log(`HTML Length: ${html.length}`);
    console.log(`Contains "isLiveBroadcast":true: ${html.includes('"isLiveBroadcast":true')}`);
    console.log(`Contains "isLive":true: ${html.includes('"isLive":true')}`);
    console.log(`Contains "liveStreamability": ${html.includes('liveStreamability')}`);
    console.log(`Contains "This channel has no": ${html.includes('This channel has no')}`);
    console.log(`Contains "not currently live": ${html.includes('not currently live')}`);
    console.log(`Final URL: ${page.url()}`);
  });
});
