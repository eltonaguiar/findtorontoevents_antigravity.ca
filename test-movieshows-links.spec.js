const { test, expect } = require('@playwright/test');

test.describe('MOVIESHOWS2 link verification', () => {

  test('sidebar Movies & TV link points to /MOVIESHOWS2/', async ({ page }) => {
    await page.goto('https://findtorontoevents.ca/', { waitUntil: 'domcontentloaded', timeout: 30000 });
    // Wait for post-hydration fix script to run (fires at 500ms, 2s, 5s)
    await page.waitForTimeout(6000);

    // Find all links with "Movies & TV" text
    const moviesTvLinks = await page.$$eval('a', links => {
      return links
        .filter(a => {
          const text = a.textContent.trim();
          return text.includes('Movies & TV') || text.includes('Movies &amp; TV');
        })
        .map(a => ({
          href: a.getAttribute('href'),
          text: a.textContent.trim().substring(0, 50)
        }));
    });

    console.log('\nMovies & TV nav links found:');
    moviesTvLinks.forEach(l => console.log(`  "${l.text}" -> ${l.href}`));

    // All "Movies & TV" sidebar/nav links should point to MOVIESHOWS2
    const badNavLinks = moviesTvLinks.filter(l => {
      const href = (l.href || '').toUpperCase();
      return !href.includes('/MOVIESHOWS2/');
    });

    console.log(`\n${badNavLinks.length} incorrect Movies & TV nav links`);
    badNavLinks.forEach(l => console.log(`  BAD: "${l.text}" -> ${l.href}`));

    expect(badNavLinks.length, `Movies & TV nav links should all point to /MOVIESHOWS2/: ${JSON.stringify(badNavLinks)}`).toBe(0);
  });

  test('section cards keep correct 3-way destinations', async ({ page }) => {
    await page.goto('https://findtorontoevents.ca/', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(3000);

    // Find all MOVIESHOWS links
    const movieLinks = await page.$$eval('a[href*="MOVIESHOWS"], a[href*="movieshows"]', links => {
      return links.map(a => ({
        href: a.getAttribute('href'),
        text: a.textContent.trim().substring(0, 60)
      }));
    });

    console.log(`\nAll MOVIESHOWS links (${movieLinks.length}):`);
    movieLinks.forEach(l => console.log(`  "${l.text}" -> ${l.href}`));

    // Verify Now Showing links exist and point to /MOVIESHOWS/
    const nowShowingLinks = movieLinks.filter(l =>
      l.text.includes('Now Showing')
    );
    console.log(`\nNow Showing links: ${nowShowingLinks.length}`);
    expect(nowShowingLinks.length).toBeGreaterThan(0);
    nowShowingLinks.forEach(l => {
      expect(l.href.toUpperCase()).toContain('/MOVIESHOWS/');
      expect(l.href.toUpperCase()).not.toContain('/MOVIESHOWS2/');
    });

    // Verify Film Vault links exist and point to /MOVIESHOWS2/
    const filmVaultLinks = movieLinks.filter(l =>
      l.text.includes('Film Vault')
    );
    console.log(`Film Vault links: ${filmVaultLinks.length}`);
    expect(filmVaultLinks.length).toBeGreaterThan(0);
    filmVaultLinks.forEach(l => {
      expect(l.href.toUpperCase()).toContain('/MOVIESHOWS2/');
    });

    // Verify Binge Mode links exist and point to /MOVIESHOWS3/
    const bingeModeLinks = movieLinks.filter(l =>
      l.text.includes('Binge Mode')
    );
    console.log(`Binge Mode links: ${bingeModeLinks.length}`);
    expect(bingeModeLinks.length).toBeGreaterThan(0);
    bingeModeLinks.forEach(l => {
      expect(l.href.toUpperCase()).toContain('/MOVIESHOWS3/');
    });
  });

  test('/MOVIESHOWS2/ loads correctly and redirects to app.html', async ({ page }) => {
    const response = await page.goto('https://findtorontoevents.ca/MOVIESHOWS2/', { waitUntil: 'domcontentloaded', timeout: 30000 });

    expect(response.status()).toBe(200);

    await page.waitForTimeout(3000);
    const url = page.url();
    console.log(`\nFinal URL after redirect: ${url}`);
    expect(url).toContain('app.html');
  });

  test('build/index.html Movies & TV links point to /MOVIESHOWS2/', async ({ page }) => {
    await page.goto('https://findtorontoevents.ca/TORONTOEVENTS_ANTIGRAVITY/build/index.html', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(3000);

    // Find Movies & TV and Open App links
    const movieLinks = await page.$$eval('a[href*="MOVIESHOWS"]', links => {
      return links.map(a => ({
        href: a.getAttribute('href'),
        text: a.textContent.trim().substring(0, 50)
      }));
    });

    console.log('\nBuild index.html MOVIESHOWS links:');
    movieLinks.forEach(l => console.log(`  "${l.text}" -> ${l.href}`));

    // All build links should point to MOVIESHOWS2
    const badLinks = movieLinks.filter(l => !l.href.includes('MOVIESHOWS2'));
    expect(badLinks.length, `Build links not pointing to MOVIESHOWS2: ${JSON.stringify(badLinks)}`).toBe(0);
    expect(movieLinks.length).toBeGreaterThan(0);
  });
});
