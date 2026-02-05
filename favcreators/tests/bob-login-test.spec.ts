import { test, expect } from '@playwright/test';

test.describe('Bob User Login Test', () => {
    test('bob should login and see all 13 creators including Brunitarte', async ({ page }) => {
        // Navigate to FavCreators
        await page.goto('https://findtorontoevents.ca/fc/');

        // Wait for app to initialize
        await page.waitForTimeout(2000);

        // Click Login button
        await page.click('button:has-text("Login")');

        // Wait for login form
        await page.waitForSelector('input[type="email"], input[name="email"]', { timeout: 5000 });

        // Fill in bob's credentials
        await page.fill('input[type="email"], input[name="email"]', 'bob');
        await page.fill('input[type="password"], input[name="password"]', 'bob');

        // Click submit
        await page.click('button[type="submit"], button:has-text("Sign In")');

        // Wait for redirect back to app
        await page.waitForURL(/findtorontoevents\.ca\/fc/, { timeout: 10000 });

        // Wait for creators to load
        await page.waitForTimeout(3000);

        // Count creators
        const creatorRows = await page.locator('tr[data-creator-id]').count();
        console.log(`Bob sees ${creatorRows} creators`);

        // Check for Brunitarte
        const brunitarteVisible = await page.locator('text=Brunitarte').isVisible();
        console.log('Brunitarte visible:', brunitarteVisible);
        expect(brunitarteVisible).toBe(true);

        // Check for Tony Robbins
        const tonyVisible = await page.locator('text=Tony Robbins').isVisible();
        console.log('Tony Robbins visible:', tonyVisible);
        expect(tonyVisible).toBe(true);

        // Check for Chantellfloress
        const chantellVisible = await page.locator('text=Chantellfloress').isVisible();
        console.log('Chantellfloress visible:', chantellVisible);
        expect(chantellVisible).toBe(true);

        // Verify total count
        expect(creatorRows).toBe(13);

        // Take screenshot
        await page.screenshot({
            path: 'e:/findtorontoevents_antigravity.ca/favcreators/test-results/bob-login-success.png',
            fullPage: true
        });

        console.log('✅ Bob successfully sees all 13 creators!');
    });

    test('verify bob API returns 13 creators', async ({ request }) => {
        // Get bob's user ID first
        const bobResponse = await request.get('https://findtorontoevents.ca/fc/api/clone_to_bob.php');
        const bobData = await bobResponse.json();
        const bobId = bobData.bob_user_id;

        console.log(`Bob's user ID: ${bobId}`);

        // Get bob's creators
        const creatorsResponse = await request.get(`https://findtorontoevents.ca/fc/api/get_my_creators.php?user_id=${bobId}`);
        const creatorsData = await creatorsResponse.json();

        console.log(`Bob has ${creatorsData.creators.length} creators`);

        expect(creatorsData.creators.length).toBe(13);

        // Check for Brunitarte
        const brunitarte = creatorsData.creators.find((c: any) => c.name === 'Brunitarte');
        expect(brunitarte).toBeDefined();

        // List all creators
        console.log('\nBob\'s creators:');
        creatorsData.creators.forEach((c: any, i: number) => {
            console.log(`${i + 1}. ${c.name}`);
        });
    });
});
