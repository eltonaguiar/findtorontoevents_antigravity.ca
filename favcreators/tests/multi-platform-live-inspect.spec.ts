import { test, expect } from '@playwright/test';

/**
 * Inspect live vs offline pages on multiple streaming platforms
 * to understand detection patterns for each.
 */

test.describe('Multi-Platform Live Detection Inspection', () => {
  
  // ==================== TWITCH ====================
  test('Twitch - inspect live vs offline page structure', async ({ page }) => {
    console.log('\n========== TWITCH INSPECTION ==========\n');
    
    // Find a popular streamer who might be live
    const twitchUsers = ['xqc', 'kaicenat', 'shroud', 'pokimane', 'ninja'];
    
    for (const user of twitchUsers) {
      console.log(`\n--- Checking Twitch: ${user} ---`);
      
      try {
        await page.goto(`https://www.twitch.tv/${user}`, { waitUntil: 'domcontentloaded', timeout: 15000 });
        await page.waitForTimeout(3000);
        
        const html = await page.content();
        const title = await page.title();
        
        console.log(`Title: ${title}`);
        console.log(`HTML Length: ${html.length}`);
        
        // Check for live indicators
        const isLiveIndicators = {
          hasLiveBadge: html.includes('tw-channel-status-text-indicator') || html.includes('live-indicator'),
          hasStreamPlayer: html.includes('video-player') || html.includes('persistent-player'),
          titleContainsLive: title.toLowerCase().includes('live'),
          hasViewerCount: /\d+(\.\d+)?[KkMm]?\s*(viewer|watching)/i.test(html),
          jsonLdLive: html.includes('"isLiveBroadcast":true') || html.includes('"isLiveBroadcast": true'),
          offlineIndicator: html.includes('is currently offline') || html.includes('offline-message'),
          channelStatusLive: html.includes('"isLive":true') || html.includes('"status":"live"'),
        };
        
        console.log('Indicators:', JSON.stringify(isLiveIndicators, null, 2));
        
        // Extract any JSON-LD data
        const jsonLdMatch = html.match(/<script type="application\/ld\+json">([^<]+)<\/script>/);
        if (jsonLdMatch) {
          console.log('Found JSON-LD data (first 500 chars):', jsonLdMatch[1].substring(0, 500));
        }
        
        // Check meta tags
        const ogTitle = await page.$eval('meta[property="og:title"]', el => el.getAttribute('content')).catch(() => null);
        const ogDesc = await page.$eval('meta[property="og:description"]', el => el.getAttribute('content')).catch(() => null);
        console.log(`og:title: ${ogTitle}`);
        console.log(`og:description: ${ogDesc}`);
        
        // If found a live one, we have enough data
        if (isLiveIndicators.channelStatusLive || isLiveIndicators.jsonLdLive || 
            (isLiveIndicators.hasStreamPlayer && !isLiveIndicators.offlineIndicator)) {
          console.log(`\n*** ${user} appears to be LIVE ***`);
          break;
        }
      } catch (e) {
        console.log(`Error checking ${user}:`, e.message);
      }
    }
  });

  // ==================== KICK ====================
  test('Kick - inspect live vs offline page structure', async ({ page }) => {
    console.log('\n========== KICK INSPECTION ==========\n');
    
    // Popular Kick streamers
    const kickUsers = ['xqc', 'adin', 'amouranth', 'trainwreckstv'];
    
    for (const user of kickUsers) {
      console.log(`\n--- Checking Kick: ${user} ---`);
      
      try {
        await page.goto(`https://kick.com/${user}`, { waitUntil: 'domcontentloaded', timeout: 15000 });
        await page.waitForTimeout(3000);
        
        const html = await page.content();
        const title = await page.title();
        
        console.log(`Title: ${title}`);
        console.log(`HTML Length: ${html.length}`);
        
        // Check for live indicators
        const isLiveIndicators = {
          hasLiveBadge: html.includes('LIVE') && html.includes('badge'),
          hasVideoPlayer: html.includes('video-player') || html.includes('livestream'),
          titleContainsLive: title.toLowerCase().includes('live'),
          hasViewerCount: /(\d+[\d,]*)\s*(viewer|watching)/i.test(html),
          offlineIndicator: html.includes('offline') || html.includes('is not streaming'),
          nuxtDataLive: html.includes('"livestream"') && html.includes('"is_live":true'),
        };
        
        console.log('Indicators:', JSON.stringify(isLiveIndicators, null, 2));
        
        // Look for __NUXT_DATA__ or similar
        const nuxtMatch = html.match(/<script[^>]*id="__NUXT_DATA__"[^>]*>([^<]+)<\/script>/);
        if (nuxtMatch) {
          console.log('Found NUXT_DATA (first 500 chars):', nuxtMatch[1].substring(0, 500));
        }
        
        // Check API endpoint
        const apiResponse = await page.request.get(`https://kick.com/api/v1/channels/${user}`).catch(() => null);
        if (apiResponse && apiResponse.ok()) {
          const apiData = await apiResponse.json();
          console.log('Kick API Response (key fields):');
          console.log(`  - livestream: ${apiData.livestream ? 'PRESENT' : 'null'}`);
          console.log(`  - is_banned: ${apiData.is_banned}`);
          console.log(`  - verified: ${apiData.verified}`);
          if (apiData.livestream) {
            console.log(`  - livestream.is_live: ${apiData.livestream.is_live}`);
            console.log(`  - livestream.viewer_count: ${apiData.livestream.viewer_count}`);
            console.log(`\n*** ${user} is LIVE on Kick ***`);
          }
        }
        
      } catch (e) {
        console.log(`Error checking ${user}:`, e.message);
      }
    }
  });

  // ==================== YOUTUBE ====================
  test('YouTube - inspect live vs offline page structure', async ({ page }) => {
    console.log('\n========== YOUTUBE LIVE INSPECTION ==========\n');
    
    // Check YouTube Live page for any live streams
    try {
      await page.goto('https://www.youtube.com/live', { waitUntil: 'domcontentloaded', timeout: 15000 });
      await page.waitForTimeout(3000);
      
      const html = await page.content();
      console.log(`YouTube Live Page HTML Length: ${html.length}`);
      
      // Look for live video links
      const liveVideoLinks = await page.$$eval('a[href*="/watch?v="]', links => 
        links.slice(0, 5).map(l => l.getAttribute('href'))
      );
      console.log('Found live video links:', liveVideoLinks);
      
      if (liveVideoLinks.length > 0) {
        // Check first live video
        const liveUrl = `https://www.youtube.com${liveVideoLinks[0]}`;
        console.log(`\nChecking live video: ${liveUrl}`);
        
        await page.goto(liveUrl, { waitUntil: 'domcontentloaded', timeout: 15000 });
        await page.waitForTimeout(3000);
        
        const videoHtml = await page.content();
        const videoTitle = await page.title();
        
        console.log(`Video Title: ${videoTitle}`);
        
        const ytIndicators = {
          hasLiveBadge: videoHtml.includes('LIVE') || videoHtml.includes('live-badge'),
          isLiveBroadcast: videoHtml.includes('"isLiveBroadcast":true'),
          hasViewerCount: /(\d+[\d,]*)\s*(watching|viewers)/i.test(videoHtml),
          ytInitialData: videoHtml.includes('ytInitialPlayerResponse') || videoHtml.includes('ytInitialData'),
        };
        
        console.log('YouTube Live Indicators:', JSON.stringify(ytIndicators, null, 2));
      }
      
    } catch (e) {
      console.log('Error checking YouTube:', e.message);
    }
    
    // Also check a specific channel's live page
    console.log('\n--- Checking specific YouTube channel live ---');
    try {
      // MrBeast or similar popular channel
      await page.goto('https://www.youtube.com/@MrBeast/live', { waitUntil: 'domcontentloaded', timeout: 15000 });
      await page.waitForTimeout(3000);
      
      const html = await page.content();
      const title = await page.title();
      
      console.log(`Title: ${title}`);
      console.log(`HTML contains "offline": ${html.includes('offline')}`);
      console.log(`HTML contains "isLiveBroadcast": ${html.includes('isLiveBroadcast')}`);
      console.log(`HTML contains "LIVE": ${html.includes('>LIVE<') || html.includes('"LIVE"')}`);
      
    } catch (e) {
      console.log('Error:', e.message);
    }
  });

  // ==================== SUMMARY TEST ====================
  test('Generate detection patterns summary', async ({ page }) => {
    console.log('\n========== DETECTION PATTERNS SUMMARY ==========\n');
    
    console.log(`
TIKTOK:
  - Primary: SIGI_STATE JSON -> LiveRoom.liveRoomUserInfo.user.status (2=live, 4=offline)
  - Secondary: roomId presence (non-empty, non-zero)
  - Tertiary: Stream URLs (tiktokcdn.com/stage/stream-*)

TWITCH:
  - Primary: JSON-LD "isLiveBroadcast":true
  - Secondary: "isLive":true in page data
  - Tertiary: Absence of "is currently offline"
  - API: Helix API (requires auth) or page scraping

KICK:
  - Primary: API endpoint /api/v1/channels/{user} -> livestream object presence
  - Secondary: livestream.is_live === true
  - Tertiary: Viewer count > 0

YOUTUBE:
  - Primary: ytInitialPlayerResponse -> "isLive":true
  - Secondary: "isLiveBroadcast":true in JSON-LD
  - Tertiary: Live badge presence in DOM
    `);
  });
});
