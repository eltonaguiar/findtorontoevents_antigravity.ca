import { test, expect } from '@playwright/test';

test.describe('Bob1 User - Complete Brunitarte Verification', () => {
    test('verify bob1 API returns 13 creators with Brunitarte', async ({ page }) => {
        // Test 1: Verify bob1 can login
        console.log('\n=== TEST 1: Bob1 Login ===');
        const loginResponse = await page.request.post('https://findtorontoevents.ca/fc/api/login_email.php', {
            data: {
                email: 'bob1',
                password: 'bob1'
            }
        });

        expect(loginResponse.ok()).toBe(true);
        const loginData = await loginResponse.json();
        console.log(`Login successful: ${JSON.stringify(loginData)}`);
        expect(loginData.id).toBeDefined();
        expect(loginData.email).toBe('bob1');

        const bob_id = loginData.id;

        // Test 2: Verify bob1's creator list from API
        console.log(`\n=== TEST 2: Bob1 Creator List (user_id=${bob_id}) ===`);
        const creatorsResponse = await page.request.get(`https://findtorontoevents.ca/fc/api/get_my_creators.php?user_id=${bob_id}`);

        expect(creatorsResponse.ok()).toBe(true);
        const creatorsData = await creatorsResponse.json();

        console.log(`Total creators: ${creatorsData.creators.length}`);
        expect(creatorsData.creators.length).toBe(13);

        const hasBrunitarte = creatorsData.creators.some((c: any) => c.name === 'Brunitarte');
        console.log(`Has Brunitarte: ${hasBrunitarte}`);
        expect(hasBrunitarte).toBe(true);

        console.log(`\nAll ${creatorsData.creators.length} creators:`);
        creatorsData.creators.forEach((c: any, i: number) => {
            console.log(`  ${i + 1}. ${c.name}`);
        });

        // Test 3: Verify Brunitarte data
        console.log(`\n=== TEST 3: Brunitarte Data ===`);
        const brunitarte = creatorsData.creators.find((c: any) => c.name === 'Brunitarte');
        console.log(`Brunitarte:`, JSON.stringify(brunitarte, null, 2));
        expect(brunitarte).toBeDefined();
        expect(brunitarte.id).toBe('brunitarte-1');

        console.log(`\n✅ ALL API TESTS PASSED`);
    });

    test('verify user 2 also has 13 creators', async ({ page }) => {
        console.log('\n=== TEST: User 2 Creator List ===');
        const response = await page.request.get('https://findtorontoevents.ca/fc/api/get_my_creators.php?user_id=2');

        expect(response.ok()).toBe(true);
        const data = await response.json();

        console.log(`User 2 total creators: ${data.creators.length}`);
        const hasBrunitarte = data.creators.some((c: any) => c.name === 'Brunitarte');
        console.log(`User 2 has Brunitarte: ${hasBrunitarte}`);

        expect(data.creators.length).toBe(13);
        expect(hasBrunitarte).toBe(true);

        console.log(`\n✅ USER 2 TEST PASSED`);
    });

    test('verify database has Brunitarte', async ({ page }) => {
        console.log('\n=== TEST: Database Check ===');
        const response = await page.request.get('https://findtorontoevents.ca/fc/api/emergency_check.php');
        const text = await response.text();

        console.log(text);

        expect(text).toContain('Total creators in DB: 13');
        expect(text).toContain('FOUND! Brunitarte');

        console.log(`\n✅ DATABASE TEST PASSED`);
    });

    test('verify guest view shows 12 creators (no Brunitarte)', async ({ page }) => {
        console.log('\n=== TEST: Guest View ===');
        const response = await page.request.get('https://findtorontoevents.ca/fc/api/get_my_creators.php?user_id=0');

        expect(response.ok()).toBe(true);
        const data = await response.json();

        console.log(`Guest total creators: ${data.creators.length}`);
        const hasBrunitarte = data.creators.some((c: any) => c.name === 'Brunitarte');
        console.log(`Guest has Brunitarte: ${hasBrunitarte}`);

        expect(data.creators.length).toBe(12);
        expect(hasBrunitarte).toBe(false);

        console.log(`\n✅ GUEST TEST PASSED`);
    });
});

test.describe('Frontend Display Tests', () => {
    test('check guest view in browser', async ({ page }) => {
        await page.goto('https://findtorontoevents.ca/fc/');

        // Clear cache
        await page.evaluate(() => {
            localStorage.clear();
            sessionStorage.clear();
        });

        await page.reload();
        await page.waitForTimeout(8000);

        const count = await page.locator('tr[data-creator-id]').count();
        console.log(`\n=== BROWSER: Guest View ===`);
        console.log(`Visible creators: ${count}`);

        await page.screenshot({
            path: 'e:/findtorontoevents_antigravity.ca/favcreators/test-results/guest-browser-view.png',
            fullPage: true
        });

        expect(count).toBe(12);
        console.log(`\n✅ BROWSER GUEST TEST PASSED`);
    });
});
