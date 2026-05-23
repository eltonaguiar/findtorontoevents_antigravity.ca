const { chromium } = require('playwright');
(async () => {
    const b = await chromium.launch();
    const p = await b.newPage();
    const errs = [];
    p.on('pageerror', e => errs.push('PageError: ' + e.message));
    p.on('console', m => {
        if (m.type() === 'error') errs.push('ConsoleErr: ' + m.text());
    });

    await p.goto('http://localhost:5174/index.html', { waitUntil: 'networkidle', timeout: 15000 });
    await p.waitForTimeout(4000);

    // Check picks table
    const pickRows = await p.$$eval('#picksBody tr', rows => rows.length);
    console.log('Pick rows:', pickRows);

    if (pickRows > 0) {
        // Get all cells from first pick row
        const firstRowCells = await p.$$eval('#picksBody tr:first-child td', tds => tds.map(t => t.textContent.trim()));
        console.log('First row:', JSON.stringify(firstRowCells, null, 2));

        // Check EST
        const hasEST = firstRowCells.some(c => c.includes('EST'));
        console.log('Has EST timestamp:', hasEST);

        // Check P&L is real (not 0.00%)
        console.log('P&L % cell:', firstRowCells[6] || 'MISSING');
        console.log('P&L $ cell:', firstRowCells[7] || 'MISSING');
        console.log('Reason cell:', firstRowCells[10] || 'MISSING');
    }

    // Test clicking an algo in leaderboard
    const lbRows = await p.$$eval('#leaderboardBody tr', rows => rows.length);
    console.log('Leaderboard rows:', lbRows);
    if (lbRows > 0) {
        await p.click('#leaderboardBody tr:first-child');
        await p.waitForTimeout(1000);
        const modalVisible = await p.$eval('#algoModal', el => el.classList.contains('active'));
        console.log('Modal opened:', modalVisible);

        // Check for tabs
        const tabTexts = await p.$$eval('#algoModal button', btns => btns.map(b => b.textContent.trim()));
        console.log('Modal buttons:', tabTexts);

        // Click Methodology tab
        const methBtn = await p.$('button:has-text("Methodology")');
        if (methBtn) {
            await methBtn.click();
            await p.waitForTimeout(500);
            const methContent = await p.$eval('#algoTab_methodology', el => el.innerText.substring(0, 500));
            console.log('Methodology content:', methContent);
        }

        // Click Active Picks tab
        const picksBtn = await p.$('button:has-text("Active Picks")');
        if (picksBtn) {
            await picksBtn.click();
            await p.waitForTimeout(500);
            const picksContent = await p.$eval('#algoTab_picks', el => el.innerText.substring(0, 500));
            console.log('Picks tab content:', picksContent);
        }

        // Click Audit tab
        const auditBtn = await p.$('button:has-text("Audit")');
        if (auditBtn) {
            await auditBtn.click();
            await p.waitForTimeout(500);
            const auditContent = await p.$eval('#algoTab_audit', el => el.innerText.substring(0, 500));
            console.log('Audit tab content:', auditContent);
        }
    }

    console.log('\nJS Errors:', errs.length);
    errs.forEach(e => console.log(' -', e));

    await b.close();
    process.exit(errs.length > 0 ? 1 : 0);
})();
