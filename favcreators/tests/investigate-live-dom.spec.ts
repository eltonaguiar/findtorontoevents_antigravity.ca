import { test } from '@playwright/test';

test('Investigate live status - React state approach', async ({ page }) => {
    console.log('=== STARTING INVESTIGATION ===');

    await page.goto('http://localhost:3000/fc/');
    await page.waitForTimeout(12000); // Wait for DB load

    console.log('\nStep 1: Injecting state inspector into page');

    // Inject a global function to access React state
    await page.evaluate(() => {
        (window as any).getCreatorData = () => {
            // Try to find the React root and access state
            const root = document.querySelector('#root');
            if (!root) return null;

            // Access React Fiber to get state (this is a hack but works)
            const fiber = (root as any)._reactRootContainer?._internalRoot?.current;
            return fiber;
        };
    });

    console.log('\nStep 2: Clicking Check All Live Status');

    // Capture console
    const logs: string[] = [];
    page.on('console', msg => {
        const text = msg.text();
        if (text.includes('tyler1') || text.includes('jcelynaa') || text.includes('honeymoon') || text.includes('xqc') || text.includes('TLC') || text.includes('DEBUG')) {
            logs.push(text);
        }
    });

    await page.click('button:has-text("Check All Live Status")');
    await page.waitForTimeout(18000);

    console.log('\nStep 3: Console logs:');
    logs.forEach(log => console.log(log));

    console.log('\nStep 4: Checking DOM for live indicators');

    // Check DOM directly for live status
    const domCheck = await page.evaluate(() => {
        const cards = Array.from(document.querySelectorAll('.creator-card'));

        const findCard = (name: string) => {
            const card = cards.find(c => c.textContent?.toLowerCase().includes(name));
            if (!card) return null;

            const nameEl = card.querySelector('h3');
            const hasLiveIndicator = card.querySelector('.live-indicator') !== null;
            const hasLiveClass = card.classList.contains('live');

            // Check account links
            const accountLinks = Array.from(card.querySelectorAll('.account-link')).map(link => ({
                classes: link.className,
                hasLiveClass: link.classList.contains('live'),
                text: link.textContent
            }));

            return {
                name: nameEl?.textContent,
                hasLiveIndicator,
                hasLiveClass,
                accountLinks
            };
        };

        return {
            loltyler1: findCard('tyler1'),
            jcelynaa: findCard('jcelynaa'),
            honeymoontarot: findCard('honeymoon'),
            xqc: findCard('xqc')
        };
    });

    console.log('\nDOM Check Results:', JSON.stringify(domCheck, null, 2));

    console.log('\n=== ANALYSIS ===');

    // Analyze each creator
    ['loltyler1', 'jcelynaa', 'honeymoontarot', 'xqc'].forEach(creator => {
        const tlcLogs = logs.filter(log => log.toLowerCase().includes(creator) && log.includes('TLC'));
        const liveLogs = tlcLogs.filter(log => log.includes('LIVE'));
        const domData = (domCheck as any)[creator];

        if (tlcLogs.length > 0 || domData) {
            console.log(`\n${creator}:`);
            console.log(`  TLC logs: ${tlcLogs.length} total, ${liveLogs.length} showing LIVE`);
            console.log(`  DOM shows live: ${domData?.hasLiveIndicator || domData?.hasLiveClass}`);
            console.log(`  Account links:`, domData?.accountLinks);

            if (liveLogs.length > 0 && !domData?.hasLiveIndicator && !domData?.hasLiveClass) {
                console.log(`  ❌ MISMATCH: TLC detected LIVE but DOM shows offline`);
                console.log(`  Live detection logs:`, liveLogs);
            }
        }
    });

    await page.screenshot({ path: 'investigation-result.png', fullPage: true });

    console.log('\n=== END INVESTIGATION ===');
});
