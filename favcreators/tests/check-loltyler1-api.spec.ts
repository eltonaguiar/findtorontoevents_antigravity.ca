import { test } from '@playwright/test';

test('Check loltyler1 data from API', async ({ page, request }) => {
    // First get the creator data from the API
    const response = await request.get('https://findtorontoevents.ca/fc/api/get_my_creators.php?user_id=2');
    const data = await response.json();

    console.log('API Response status:', response.status());

    // Find loltyler1
    const loltyler1 = data.creators?.find((c: any) =>
        c.name.toLowerCase().includes('loltyler1') ||
        c.name.toLowerCase().includes('tyler1')
    );

    if (loltyler1) {
        console.log('loltyler1 found in API response:');
        console.log(JSON.stringify({
            name: loltyler1.name,
            isLive: loltyler1.isLive,
            lastChecked: loltyler1.lastChecked,
            accounts: loltyler1.accounts
        }, null, 2));
    } else {
        console.log('loltyler1 NOT found in API response');
        console.log('Total creators:', data.creators?.length);
    }
});
