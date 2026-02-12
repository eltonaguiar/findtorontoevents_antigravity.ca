const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch();
    const page = await browser.newPage();
    let allPassed = true;

    console.log('TEST 1: Checking all MOVIESHOWS links on index.html...');
    await page.goto('https://findtorontoevents.ca/', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(4000);

    const movieLinks = await page.evaluate(() => {
        const links = document.querySelectorAll('a[href*="MOVIESHOWS"], a[href*="movieshows"]');
        return Array.from(links).map(a => ({
            href: a.getAttribute('href'),
            text: a.textContent.trim().substring(0, 60)
        }));
    });

    console.log('Found ' + movieLinks.length + ' MOVIESHOWS links:');
    let badLinks = [];
    for (const link of movieLinks) {
        const ok = link.href.includes('/MOVIESHOWS2/');
        console.log('  [' + (ok ? 'OK' : 'FAIL') + '] "' + link.text + '" -> ' + link.href);
        if (!ok) badLinks.push(link);
    }

    if (badLinks.length === 0) {
        console.log('PASS: All ' + movieLinks.length + ' links point to /MOVIESHOWS2/\n');
    } else {
        console.log('FAIL: ' + badLinks.length + ' links still pointing to wrong URL\n');
        allPassed = false;
    }

    console.log('TEST 2: No /MOVIESHOWS/ or /MOVIESHOWS3/ links...');
    const oldLinks = await page.evaluate(() => {
        const links = document.querySelectorAll('a');
        return Array.from(links).filter(a => {
            const h = a.getAttribute('href') || '';
            return (h === '/MOVIESHOWS/' || h === '/MOVIESHOWS3/');
        }).map(a => ({ href: a.getAttribute('href'), text: a.textContent.trim().substring(0, 60) }));
    });

    if (oldLinks.length === 0) {
        console.log('PASS: No old /MOVIESHOWS/ or /MOVIESHOWS3/ links found\n');
    } else {
        console.log('FAIL: Found ' + oldLinks.length + ' old links:');
        oldLinks.forEach(l => console.log('  BAD: "' + l.text + '" -> ' + l.href));
        console.log('');
        allPassed = false;
    }

    console.log('TEST 3: /MOVIESHOWS2/ loads and redirects to app.html...');
    await page.goto('https://findtorontoevents.ca/MOVIESHOWS2/', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(3000);
    const finalUrl = page.url();
    console.log('Final URL: ' + finalUrl);
    if (finalUrl.includes('app.html')) {
        console.log('PASS: Redirects to app.html\n');
    } else {
        console.log('FAIL: Did not redirect to app.html\n');
        allPassed = false;
    }

    console.log('=== SUMMARY ===');
    console.log(allPassed ? 'ALL TESTS PASSED' : 'SOME TESTS FAILED');

    await browser.close();
    process.exit(allPassed ? 0 : 1);
})().catch(e => { console.error(e); process.exit(1); });
