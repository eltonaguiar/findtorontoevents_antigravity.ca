const { chromium } = require('playwright');

(async () => {
    const b = await chromium.launch({ headless: true });
    const p = await b.newPage();
    const errs = [];
    
    p.on('pageerror', e => errs.push('PageErr: ' + e.message));
    p.on('console', m => {
        if (m.type() === 'error') errs.push('Console: ' + m.text());
    });
    
    await p.goto('http://localhost:5174/favcreators/public/taste-profile/index.html', {
        waitUntil: 'networkidle',
        timeout: 15000
    }).catch(e => console.log('Nav error:', e.message));
    
    await p.waitForTimeout(4000);
    
    const title = await p.title().catch(() => '');
    const h1 = await p.$eval('.header h1', e => e.textContent).catch(() => 'no h1');
    const statsCount = await p.$$eval('.stat-card', els => els.length).catch(() => 0);
    const artistCount = await p.$$eval('.artist-card', els => els.length).catch(() => 0);
    const playlistCount = await p.$$eval('.playlist-card', els => els.length).catch(() => 0);
    const genreCount = await p.$$eval('.genre-bar-row', els => els.length).catch(() => 0);
    const ytStatus = await p.$eval('#yt-status', e => e.textContent).catch(() => '');
    const resultsVisible = await p.$eval('#yt-results', e => !e.classList.contains('hidden')).catch(() => false);
    
    console.log('=== Taste Profile Test ===');
    console.log('Title:', title);
    console.log('H1:', h1);
    console.log('YT Status:', ytStatus);
    console.log('Results visible:', resultsVisible);
    console.log('Stats cards:', statsCount);
    console.log('Artist cards:', artistCount);
    console.log('Playlist cards:', playlistCount);
    console.log('Genre bars:', genreCount);
    console.log('JS Errors:', errs.length);
    errs.forEach(e => console.log('  -', e));
    
    if (errs.length > 0) {
        console.log('\nFAILED: JS errors detected');
    } else if (artistCount > 0) {
        console.log('\nPASSED: Page loaded with data');
    } else {
        console.log('\nWARNING: Page loaded but no data rendered (check JSON path)');
    }
    
    await b.close();
    process.exit(errs.length > 0 ? 1 : 0);
})();
