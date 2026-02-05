import { test, expect } from '@playwright/test';

test('Deep investigation of live status detection', async ({ page }) => {
    console.log('=== STARTING DEEP INVESTIGATION ===');

    // Navigate to the app
    await page.goto('http://localhost:3000/fc/');

    // Wait for app to fully load
    await page.waitForTimeout(10000);

    console.log('Step 1: Getting initial creator data from localStorage');

    // Get initial state
    const initialData = await page.evaluate(() => {
        const stored = localStorage.getItem('fav_creators');
        if (!stored) return null;

        const creators = JSON.parse(stored);
        const loltyler1 = creators.find((c: any) => c.name.toLowerCase().includes('tyler1'));
        const jcelynaa = creators.find((c: any) => c.name.toLowerCase().includes('jcelynaa'));
        const honeymoontarot = creators.find((c: any) => c.name.toLowerCase().includes('honeymoon'));
        const xqc = creators.find((c: any) => c.name.toLowerCase().includes('xqc'));

        return {
            loltyler1: loltyler1 ? {
                name: loltyler1.name,
                isLive: loltyler1.isLive,
                accounts: loltyler1.accounts.map((a: any) => ({
                    platform: a.platform,
                    username: a.username,
                    isLive: a.isLive,
                    checkLive: a.checkLive
                }))
            } : null,
            jcelynaa: jcelynaa ? {
                name: jcelynaa.name,
                isLive: jcelynaa.isLive,
                accounts: jcelynaa.accounts.map((a: any) => ({
                    platform: a.platform,
                    username: a.username,
                    isLive: a.isLive,
                    checkLive: a.checkLive
                }))
            } : null,
            honeymoontarot: honeymoontarot ? {
                name: honeymoontarot.name,
                isLive: honeymoontarot.isLive,
                accounts: honeymoontarot.accounts.map((a: any) => ({
                    platform: a.platform,
                    username: a.username,
                    isLive: a.isLive,
                    checkLive: a.checkLive
                }))
            } : null,
            xqc: xqc ? {
                name: xqc.name,
                isLive: xqc.isLive,
                accounts: xqc.accounts.map((a: any) => ({
                    platform: a.platform,
                    username: a.username,
                    isLive: a.isLive,
                    checkLive: a.checkLive
                }))
            } : null
        };
    });

    console.log('Initial state:', JSON.stringify(initialData, null, 2));

    console.log('\nStep 2: Capturing console logs during live check');

    // Capture console logs
    const consoleLogs: string[] = [];
    page.on('console', msg => {
        const text = msg.text();
        if (text.includes('TLC') || text.includes('SKIP') || text.includes('DEBUG') || text.includes('tyler1') || text.includes('jcelynaa') || text.includes('honeymoon') || text.includes('xqc')) {
            consoleLogs.push(text);
        }
    });

    // Click the check all button
    console.log('\nStep 3: Clicking "Check All Live Status" button');
    await page.click('button:has-text("Check All Live Status")');

    // Wait for checks to complete
    await page.waitForTimeout(15000);

    console.log('\nStep 4: Console logs captured:');
    consoleLogs.forEach(log => console.log(log));

    console.log('\nStep 5: Getting final creator data from localStorage');

    // Get final state
    const finalData = await page.evaluate(() => {
        const stored = localStorage.getItem('fav_creators');
        if (!stored) return null;

        const creators = JSON.parse(stored);
        const loltyler1 = creators.find((c: any) => c.name.toLowerCase().includes('tyler1'));
        const jcelynaa = creators.find((c: any) => c.name.toLowerCase().includes('jcelynaa'));
        const honeymoontarot = creators.find((c: any) => c.name.toLowerCase().includes('honeymoon'));
        const xqc = creators.find((c: any) => c.name.toLowerCase().includes('xqc'));

        return {
            loltyler1: loltyler1 ? {
                name: loltyler1.name,
                isLive: loltyler1.isLive,
                lastChecked: loltyler1.lastChecked,
                accounts: loltyler1.accounts.map((a: any) => ({
                    platform: a.platform,
                    username: a.username,
                    isLive: a.isLive,
                    checkLive: a.checkLive,
                    lastChecked: a.lastChecked
                }))
            } : null,
            jcelynaa: jcelynaa ? {
                name: jcelynaa.name,
                isLive: jcelynaa.isLive,
                lastChecked: jcelynaa.lastChecked,
                accounts: jcelynaa.accounts.map((a: any) => ({
                    platform: a.platform,
                    username: a.username,
                    isLive: a.isLive,
                    checkLive: a.checkLive,
                    lastChecked: a.lastChecked
                }))
            } : null,
            honeymoontarot: honeymoontarot ? {
                name: honeymoontarot.name,
                isLive: honeymoontarot.isLive,
                lastChecked: honeymoontarot.lastChecked,
                accounts: honeymoontarot.accounts.map((a: any) => ({
                    platform: a.platform,
                    username: a.username,
                    isLive: a.isLive,
                    checkLive: a.checkLive,
                    lastChecked: a.lastChecked
                }))
            } : null,
            xqc: xqc ? {
                name: xqc.name,
                isLive: xqc.isLive,
                lastChecked: xqc.lastChecked,
                accounts: xqc.accounts.map((a: any) => ({
                    platform: a.platform,
                    username: a.username,
                    isLive: a.isLive,
                    checkLive: a.checkLive,
                    lastChecked: a.lastChecked
                }))
            } : null
        };
    });

    console.log('\nFinal state:', JSON.stringify(finalData, null, 2));

    console.log('\n=== ANALYSIS ===');

    // Analyze loltyler1
    if (finalData?.loltyler1) {
        const twitchAccount = finalData.loltyler1.accounts.find((a: any) => a.platform === 'twitch');
        const twitchLogs = consoleLogs.filter(log => log.includes('loltyler1') && log.includes('twitch'));

        console.log('\nloltyler1 Analysis:');
        console.log('- Creator isLive:', finalData.loltyler1.isLive);
        console.log('- Twitch account isLive:', twitchAccount?.isLive);
        console.log('- Twitch account checkLive:', twitchAccount?.checkLive);
        console.log('- TLC logs for Twitch:', twitchLogs);

        const tlcDetectedLive = twitchLogs.some(log => log.includes('LIVE'));
        console.log('- TLC detected as LIVE:', tlcDetectedLive);
        console.log('- Account shows as live:', twitchAccount?.isLive);
        console.log('- MISMATCH:', tlcDetectedLive && !twitchAccount?.isLive);
    }

    // Analyze jcelynaa
    if (finalData?.jcelynaa) {
        const tiktokAccount = finalData.jcelynaa.accounts.find((a: any) => a.platform === 'tiktok');
        const tiktokLogs = consoleLogs.filter(log => log.includes('jcelynaa') && log.includes('tiktok'));

        console.log('\njcelynaa Analysis:');
        console.log('- Creator isLive:', finalData.jcelynaa.isLive);
        console.log('- TikTok account isLive:', tiktokAccount?.isLive);
        console.log('- TikTok account checkLive:', tiktokAccount?.checkLive);
        console.log('- TLC logs for TikTok:', tiktokLogs);

        const tlcDetectedLive = tiktokLogs.some(log => log.includes('LIVE'));
        console.log('- TLC detected as LIVE:', tlcDetectedLive);
        console.log('- Account shows as live:', tiktokAccount?.isLive);
        console.log('- MISMATCH:', tlcDetectedLive && !tiktokAccount?.isLive);
    }

    // Analyze honeymoontarot30
    if (finalData?.honeymoontarot) {
        const tiktokAccount = finalData.honeymoontarot.accounts.find((a: any) => a.platform === 'tiktok');
        const tiktokLogs = consoleLogs.filter(log => log.includes('honeymoon') && log.includes('tiktok'));

        console.log('\nhoneymoontarot30 Analysis:');
        console.log('- Creator isLive:', finalData.honeymoontarot.isLive);
        console.log('- TikTok account isLive:', tiktokAccount?.isLive);
        console.log('- TikTok account checkLive:', tiktokAccount?.checkLive);
        console.log('- TLC logs for TikTok:', tiktokLogs);

        const tlcDetectedLive = tiktokLogs.some(log => log.includes('LIVE'));
        console.log('- TLC detected as LIVE:', tlcDetectedLive);
        console.log('- Account shows as live:', tiktokAccount?.isLive);
        console.log('- MISMATCH:', tlcDetectedLive && !tiktokAccount?.isLive);
    }

    // Analyze xqc
    if (finalData?.xqc) {
        const twitchAccount = finalData.xqc.accounts.find((a: any) => a.platform === 'twitch');
        const twitchLogs = consoleLogs.filter(log => log.includes('xqc') && log.includes('twitch'));

        console.log('\nxqc Analysis:');
        console.log('- Creator isLive:', finalData.xqc.isLive);
        console.log('- Twitch account isLive:', twitchAccount?.isLive);
        console.log('- Twitch account checkLive:', twitchAccount?.checkLive);
        console.log('- TLC logs for Twitch:', twitchLogs);

        const tlcDetectedLive = twitchLogs.some(log => log.includes('LIVE'));
        console.log('- TLC detected as LIVE:', tlcDetectedLive);
        console.log('- Account shows as live:', twitchAccount?.isLive);
        console.log('- MISMATCH:', tlcDetectedLive && !twitchAccount?.isLive);
    }

    console.log('\n=== END INVESTIGATION ===');

    // Take screenshot
    await page.screenshot({ path: 'live-status-investigation.png', fullPage: true });
});
