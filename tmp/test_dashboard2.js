const { chromium } = require('playwright');
(async () => {
    const b = await chromium.launch();
    const p = await b.newPage();
    const errs = [];
    const warns = [];
    p.on('pageerror', e => errs.push('PageError: ' + e.message));
    p.on('console', m => {
        if (m.type() === 'error') errs.push('ConsoleErr: ' + m.text());
        if (m.type() === 'warning') warns.push('Warn: ' + m.text());
        if (m.type() === 'log') console.log('[PAGE]', m.text());
    });

    await p.goto('http://localhost:5173/index.html', { waitUntil: 'networkidle', timeout: 15000 });
    await p.waitForTimeout(3000);

    // Check picks
    const pickRows = await p.$$eval('#picksBody tr', rows => rows.length);
    console.log('Pick rows:', pickRows);

    // Get all visible text
    const bodyText = await p.$eval('body', el => el.innerText.substring(0, 2000));
    console.log('=== Page text (first 2000 chars) ===');
    console.log(bodyText);

    console.log('\nErrors:', errs.length);
    errs.forEach(e => console.log(' -', e));
    console.log('Warnings:', warns.length);
    warns.forEach(w => console.log(' -', w));

    await b.close();
    process.exit(0);
})();
