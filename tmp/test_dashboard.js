const { chromium } = require('playwright');
(async () => {
    const b = await chromium.launch();
    const p = await b.newPage();
    const errs = [];
    p.on('pageerror', e => errs.push('PageError: ' + e.message));
    p.on('console', m => { if (m.type() === 'error') errs.push('ConsoleErr: ' + m.text()); });

    await p.goto('http://localhost:5173/index.html', { waitUntil: 'networkidle', timeout: 15000 });
    await p.waitForTimeout(3000);

    // Check picks table
    const pickRows = await p.$$eval('#picksBody tr', rows => rows.length);
    console.log('Pick rows:', pickRows);

    // Get first row cells to check P&L and timestamps
    const cells = await p.$$eval('#picksBody tr:first-child td', tds => tds.map(t => t.textContent.trim()));
    console.log('First row cells:', JSON.stringify(cells));

    // Check for EST in any cell
    const hasEST = cells.some(c => c.includes('EST'));
    console.log('Has EST timestamp:', hasEST);

    // Check P&L is not 0.00% (should be non-zero for moved prices)
    const plCell = cells[6] || '';
    console.log('P&L cell:', plCell);

    // Check for algorithm methodology tabs in modal
    await p.click('#leaderboardBody tr:first-child');
    await p.waitForTimeout(500);
    const modalVisible = await p.$eval('#algoModal', el => el.classList.contains('active'));
    console.log('Modal opened:', modalVisible);

    const hasTabs = await p.$$eval('#algoModal button', btns => btns.map(b => b.textContent));
    console.log('Modal tabs:', hasTabs.filter(t => t.includes('Methodology') || t.includes('Picks') || t.includes('Audit')));

    console.log('JS Errors:', errs.length);
    errs.forEach(e => console.log(' -', e));

    await b.close();
    process.exit(errs.length > 0 ? 1 : 0);
})();
