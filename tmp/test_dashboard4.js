const { chromium } = require('playwright');
(async () => {
    const b = await chromium.launch();
    const p = await b.newPage();
    const errs = [];
    p.on('pageerror', e => errs.push('PageError: ' + e.message));
    p.on('console', m => { if (m.type() === 'error') errs.push('ConsoleErr: ' + m.text()); });

    await p.goto('http://localhost:5174/index.html', { waitUntil: 'networkidle', timeout: 15000 });
    await p.waitForTimeout(4000);

    const pickRows = await p.$$eval('#picksBody tr', rows => rows.length);
    console.log('Pick rows:', pickRows);

    if (pickRows > 0) {
        const firstRowCells = await p.$$eval('#picksBody tr:first-child td', tds => tds.map(t => t.textContent.trim()));
        console.log('Columns:', firstRowCells.length);
        console.log('First row:', JSON.stringify(firstRowCells));

        var hasEST = firstRowCells.some(c => c.includes('EST'));
        console.log('Has EST timestamp:', hasEST);
        console.log('P&L % cell (idx 6):', firstRowCells[6] || 'MISSING');
        console.log('P&L $ cell (idx 7):', firstRowCells[7] || 'MISSING');
        console.log('Reason cell (idx 10):', firstRowCells[10] || 'MISSING');
    }

    // Test clicking an algo
    const lbRows = await p.$$eval('#leaderboardBody tr', rows => rows.length);
    console.log('Leaderboard rows:', lbRows);
    if (lbRows > 0) {
        await p.click('#leaderboardBody tr:first-child');
        await p.waitForTimeout(1000);
        const modalVisible = await p.$eval('#algoModal', el => el.classList.contains('active'));
        console.log('Modal opened:', modalVisible);
        if (modalVisible) {
            const tabBtns = await p.$$eval('#algoModal button', btns => btns.map(b => b.textContent.trim()));
            console.log('Tabs:', tabBtns);

            // Click Methodology tab
            var methTab = await p.$('#tabBtn_methodology');
            if (methTab) { await methTab.click(); await p.waitForTimeout(300); }
            var methVis = await p.$eval('#algoTab_methodology', el => el.style.display !== 'none');
            console.log('Methodology visible:', methVis);
            var methText = await p.$eval('#algoTab_methodology', el => el.innerText.substring(0, 300));
            console.log('Methodology:', methText);
        }
    }

    console.log('\nJS Errors:', errs.length);
    errs.forEach(e => console.log(' -', e));
    await b.close();
    process.exit(errs.length > 0 ? 1 : 0);
})();
