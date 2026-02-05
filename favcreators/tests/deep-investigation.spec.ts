import { test, expect } from '@playwright/test';

test.describe('Deep Investigation - Brunitarte Display', () => {
    test('trace API call and frontend rendering for user 2', async ({ page }) => {
        // Intercept API calls to see what data is actually returned
        const apiResponses: any[] = [];

        page.on('response', async (response) => {
            const url = response.url();
            if (url.includes('get_my_creators.php')) {
                const data = await response.json();
                apiResponses.push({
                    url,
                    status: response.status(),
                    creatorCount: data.creators?.length || 0,
                    creators: data.creators?.map((c: any) => c.name) || []
                });
                console.log(`\n=== API Response ===`);
                console.log(`URL: ${url}`);
                console.log(`Status: ${response.status()}`);
                console.log(`Creator Count: ${data.creators?.length || 0}`);
                console.log(`Creators: ${data.creators?.map((c: any) => c.name).join(', ')}`);
            }
        });

        // Navigate to the app
        await page.goto('https://findtorontoevents.ca/fc/');

        // Wait for app to initialize
        await page.waitForTimeout(5000);

        // Check console for "Loaded creators from DB"
        const logs: string[] = [];
        page.on('console', (msg) => {
            const text = msg.text();
            logs.push(text);
            if (text.includes('Loaded creators from DB')) {
                console.log(`\n=== CONSOLE LOG ===`);
                console.log(text);
            }
        });

        // Count visible creators in the table
        await page.waitForSelector('tr[data-creator-id], .creator-card', { timeout: 10000 });
        const visibleCreators = await page.locator('tr[data-creator-id]').count();
        console.log(`\n=== FRONTEND ===`);
        console.log(`Visible creators in table: ${visibleCreators}`);

        // Check if Brunitarte is visible
        const brunitarteVisible = await page.locator('text=Brunitarte').isVisible().catch(() => false);
        console.log(`Brunitarte visible: ${brunitarteVisible}`);

        // Get all visible creator names
        const creatorNames = await page.locator('tr[data-creator-id]').evaluateAll((rows) => {
            return rows.map(row => {
                const nameCell = row.querySelector('td:nth-child(2)');
                return nameCell?.textContent?.trim() || '';
            });
        });
        console.log(`\nVisible creator names:`);
        creatorNames.forEach((name, i) => console.log(`${i + 1}. ${name}`));

        // Check localStorage
        const localStorageData = await page.evaluate(() => {
            const data = localStorage.getItem('fav_creators');
            const version = localStorage.getItem('fav_creators_version');
            return { data: data ? JSON.parse(data) : null, version };
        });
        console.log(`\n=== LOCALSTORAGE ===`);
        console.log(`Version: ${localStorageData.version}`);
        console.log(`Creator count in localStorage: ${localStorageData.data?.length || 0}`);

        // Take screenshot
        await page.screenshot({
            path: 'e:/findtorontoevents_antigravity.ca/favcreators/test-results/brunitarte-investigation.png',
            fullPage: true
        });

        // Summary
        console.log(`\n=== SUMMARY ===`);
        console.log(`API returned: ${apiResponses[0]?.creatorCount || 0} creators`);
        console.log(`Frontend shows: ${visibleCreators} creators`);
        console.log(`Brunitarte in API: ${apiResponses[0]?.creators.includes('Brunitarte') || false}`);
        console.log(`Brunitarte visible: ${brunitarteVisible}`);

        // Fail if mismatch
        if (apiResponses[0]?.creatorCount !== visibleCreators) {
            throw new Error(`MISMATCH: API returned ${apiResponses[0]?.creatorCount} but frontend shows ${visibleCreators}`);
        }
    });

    test('check if frontend filters out creators without avatarUrl', async ({ page }) => {
        await page.goto('https://findtorontoevents.ca/fc/');
        await page.waitForTimeout(3000);

        // Check the App.tsx logic for filtering
        const response = await page.evaluate(async () => {
            const res = await fetch('https://findtorontoevents.ca/fc/api/get_my_creators.php?user_id=2');
            const data = await res.json();

            // Check if any creators have empty avatarUrl
            const creatorsWithoutAvatar = data.creators.filter((c: any) => !c.avatarUrl || c.avatarUrl === '');

            return {
                total: data.creators.length,
                withoutAvatar: creatorsWithoutAvatar.length,
                names: creatorsWithoutAvatar.map((c: any) => c.name)
            };
        });

        console.log(`\n=== AVATAR CHECK ===`);
        console.log(`Total creators: ${response.total}`);
        console.log(`Creators without avatarUrl: ${response.withoutAvatar}`);
        console.log(`Names: ${response.names.join(', ')}`);
    });
});
