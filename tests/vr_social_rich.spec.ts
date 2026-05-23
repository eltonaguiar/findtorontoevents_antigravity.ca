import { test, expect, Page } from '@playwright/test';

/**
 * VR Social Identity & Rich Content — Set 16 Tests
 */

const BENIGN = [
  'Unexpected identifier', 'registerMaterial', 'registerShader', 'favicon.ico',
  'net::ERR', 'already registered', 'is not defined', 'Haptics',
  'webkitSpeechRecognition', 'open-meteo', 'fetch', 'NetworkError',
  'BroadcastChannel', 'SpeechRecognition', 'vibrate'
];
function benign(msg: string) { return BENIGN.some(k => msg.includes(k)); }

async function jsErrors(page: Page) {
  const errs: string[] = [];
  page.on('pageerror', e => { if (!benign(e.message)) errs.push(e.message); });
  return errs;
}

async function ready(page: Page, url: string) {
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(3500);
}

/* ── Core Loading ──────────────────────────────── */
test.describe('Set 16 Core Loading', () => {
  test('Hub: VRSocialRich global available', async ({ page }) => {
    const errs = await jsErrors(page);
    await ready(page, '/vr/');
    expect(await page.evaluate(() => typeof (window as any).VRSocialRich === 'object')).toBe(true);
    expect(await page.evaluate(() => (window as any).VRSocialRich.version)).toBe(16);
    expect(errs.length).toBe(0);
  });

  for (const z of [
    { name: 'Movies', url: '/vr/movies.html', zone: 'movies' },
    { name: 'Creators', url: '/vr/creators.html', zone: 'creators' },
    { name: 'Stocks', url: '/vr/stocks-zone.html', zone: 'stocks' },
    { name: 'Weather', url: '/vr/weather-zone.html', zone: 'weather' },
  ]) {
    test(`${z.name}: loaded`, async ({ page }) => {
      const errs = await jsErrors(page);
      await ready(page, z.url);
      expect(await page.evaluate(() => (window as any).VRSocialRich?.zone)).toBe(z.zone);
      expect(errs.length).toBe(0);
    });
  }
});

/* ── 1. Avatar / Profile System ──────────────── */
test.describe('Avatar Profile (#1)', () => {
  test('Default profile has name and avatar', async ({ page }) => {
    await ready(page, '/vr/');
    const p = await page.evaluate(() => (window as any).VRSocialRich.profile.get());
    expect(p.name).toBe('Explorer');
    expect(p.avatar).toBe('🧑‍🚀');
  });

  test('Save new name persists', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRSocialRich.profile.saveName('TestUser'));
    const p = await page.evaluate(() => (window as any).VRSocialRich.profile.get());
    expect(p.name).toBe('TestUser');
  });

  test('Set avatar updates profile', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRSocialRich.profile.setAvatar('🦊'));
    const p = await page.evaluate(() => (window as any).VRSocialRich.profile.get());
    expect(p.avatar).toBe('🦊');
  });

  test('Opens and closes editor dialog', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRSocialRich.profile.open());
    await page.waitForTimeout(300);
    expect(await page.locator('#vr16-profile').isVisible()).toBe(true);
    await page.evaluate(() => (window as any).VRSocialRich.profile.open());
    await page.waitForTimeout(300);
    expect(await page.locator('#vr16-profile').count()).toBe(0);
  });
});

/* ── 2. Leaderboard ──────────────────────────── */
test.describe('Leaderboard (#2)', () => {
  test('getScore returns a number', async ({ page }) => {
    await ready(page, '/vr/');
    const score = await page.evaluate(() => (window as any).VRSocialRich.leaderboard.getScore());
    expect(typeof score).toBe('number');
  });

  test('Opens and closes leaderboard dialog', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRSocialRich.leaderboard.open());
    await page.waitForTimeout(300);
    expect(await page.locator('#vr16-leaderboard').isVisible()).toBe(true);
    await page.evaluate(() => (window as any).VRSocialRich.leaderboard.open());
    await page.waitForTimeout(300);
    expect(await page.locator('#vr16-leaderboard').count()).toBe(0);
  });

  test('Entries include current profile', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRSocialRich.leaderboard.open());
    await page.waitForTimeout(300);
    const entries = await page.evaluate(() => (window as any).VRSocialRich.leaderboard.getEntries());
    expect(entries.length).toBeGreaterThanOrEqual(1);
    expect(entries[0].name).toBe('Explorer');
  });
});

/* ── 3. Event Reminders ──────────────────────── */
test.describe('Event Reminders (#3)', () => {
  test('Null on non-events zone', async ({ page }) => {
    await ready(page, '/vr/');
    const r = await page.evaluate(() => (window as any).VRSocialRich.eventReminders);
    expect(r).toBeNull();
  });

  // Test on movies page to verify the zone gate works
  test('Also null on movies zone', async ({ page }) => {
    await ready(page, '/vr/movies.html');
    const r = await page.evaluate(() => (window as any).VRSocialRich.eventReminders);
    expect(r).toBeNull();
  });
});

/* ── 4. Movie Trivia Quiz ────────────────────── */
test.describe('Movie Trivia (#4)', () => {
  test('Null on non-movies zone', async ({ page }) => {
    await ready(page, '/vr/');
    const r = await page.evaluate(() => (window as any).VRSocialRich.movieTrivia);
    expect(r).toBeNull();
  });

  test('Available on movies zone', async ({ page }) => {
    await ready(page, '/vr/movies.html');
    const r = await page.evaluate(() => typeof (window as any).VRSocialRich.movieTrivia?.start);
    expect(r).toBe('function');
  });

  test('Trivia button appears on movies', async ({ page }) => {
    await ready(page, '/vr/movies.html');
    await page.waitForTimeout(2500);
    expect(await page.locator('#vr16-trivia-btn').count()).toBeGreaterThanOrEqual(1);
  });

  test('Start quiz opens trivia dialog', async ({ page }) => {
    await ready(page, '/vr/movies.html');
    await page.evaluate(() => (window as any).VRSocialRich.movieTrivia.start());
    await page.waitForTimeout(300);
    expect(await page.locator('#vr16-trivia').isVisible()).toBe(true);
  });

  test('Answering closes trivia', async ({ page }) => {
    await ready(page, '/vr/movies.html');
    await page.evaluate(() => (window as any).VRSocialRich.movieTrivia.start());
    await page.waitForTimeout(300);
    await page.evaluate(() => (window as any).VRSocialRich.movieTrivia.answer('any'));
    await page.waitForTimeout(300);
    expect(await page.locator('#vr16-trivia').count()).toBe(0);
  });

  test('Score tracks answered count', async ({ page }) => {
    await ready(page, '/vr/movies.html');
    await page.evaluate(() => {
      (window as any).VRSocialRich.movieTrivia.start();
      (window as any).VRSocialRich.movieTrivia.answer('wrong');
    });
    const s = await page.evaluate(() => (window as any).VRSocialRich.movieTrivia.getScore());
    expect(s.answered).toBeGreaterThanOrEqual(1);
  });
});

/* ── 5. Stock News Feed ──────────────────────── */
test.describe('Stock News (#5)', () => {
  test('Null on non-stocks zone', async ({ page }) => {
    await ready(page, '/vr/');
    const r = await page.evaluate(() => (window as any).VRSocialRich.stockNews);
    expect(r).toBeNull();
  });

  test('Available on stocks zone', async ({ page }) => {
    await ready(page, '/vr/stocks-zone.html');
    const r = await page.evaluate(() => typeof (window as any).VRSocialRich.stockNews?.getHeadlines);
    expect(r).toBe('function');
  });

  test('Returns headlines array', async ({ page }) => {
    await ready(page, '/vr/stocks-zone.html');
    const h = await page.evaluate(() => (window as any).VRSocialRich.stockNews.getHeadlines());
    expect(h.length).toBeGreaterThanOrEqual(8);
    expect(h[0]).toHaveProperty('title');
    expect(h[0]).toHaveProperty('ticker');
    expect(h[0]).toHaveProperty('sentiment');
  });

  test('News feed widget appears', async ({ page }) => {
    await ready(page, '/vr/stocks-zone.html');
    await page.waitForTimeout(2500);
    expect(await page.locator('#vr16-stock-news').count()).toBeGreaterThanOrEqual(1);
  });
});

/* ── 6. Wellness Journal ─────────────────────── */
test.describe('Wellness Journal (#6)', () => {
  test('Null on non-wellness zone', async ({ page }) => {
    await ready(page, '/vr/');
    const r = await page.evaluate(() => (window as any).VRSocialRich.wellnessJournal);
    expect(r).toBeNull();
  });
});

/* ── 7. Weather Outfit ───────────────────────── */
test.describe('Weather Outfit (#7)', () => {
  test('Null on non-weather zone', async ({ page }) => {
    await ready(page, '/vr/');
    const r = await page.evaluate(() => (window as any).VRSocialRich.weatherOutfit);
    expect(r).toBeNull();
  });

  test('Available on weather zone', async ({ page }) => {
    await ready(page, '/vr/weather-zone.html');
    const r = await page.evaluate(() => typeof (window as any).VRSocialRich.weatherOutfit?.suggest);
    expect(r).toBe('function');
  });

  test('Returns correct outfit for cold temp', async ({ page }) => {
    await ready(page, '/vr/weather-zone.html');
    const o = await page.evaluate(() => (window as any).VRSocialRich.weatherOutfit.suggest(-15));
    expect(o.outfit).toContain('Heavy winter coat');
    expect(o.icon).toBe('🧥');
  });

  test('Returns correct outfit for warm temp', async ({ page }) => {
    await ready(page, '/vr/weather-zone.html');
    const o = await page.evaluate(() => (window as any).VRSocialRich.weatherOutfit.suggest(28));
    expect(o.outfit).toContain('breathable');
    expect(o.icon).toBe('🕶️');
  });
});

/* ── 8. Creator Discovery Quiz ───────────────── */
test.describe('Creator Quiz (#8)', () => {
  test('Null on non-creators zone', async ({ page }) => {
    await ready(page, '/vr/');
    const r = await page.evaluate(() => (window as any).VRSocialRich.creatorQuiz);
    expect(r).toBeNull();
  });

  test('Available on creators zone', async ({ page }) => {
    await ready(page, '/vr/creators.html');
    const r = await page.evaluate(() => typeof (window as any).VRSocialRich.creatorQuiz?.start);
    expect(r).toBe('function');
  });

  test('Start quiz opens first question', async ({ page }) => {
    await ready(page, '/vr/creators.html');
    await page.evaluate(() => (window as any).VRSocialRich.creatorQuiz.start());
    await page.waitForTimeout(300);
    expect(await page.locator('#vr16-quiz').isVisible()).toBe(true);
  });

  test('Answering all questions produces a result', async ({ page }) => {
    await ready(page, '/vr/creators.html');
    await page.evaluate(() => {
      const q = (window as any).VRSocialRich.creatorQuiz;
      q.start();
      q.answerQ(0, 'gaming');
      q.answerQ(1, 'hype');
      q.answerQ(2, 'large');
    });
    await page.waitForTimeout(500);
    const result = await page.evaluate(() => (window as any).VRSocialRich.creatorQuiz.getResult());
    expect(result).not.toBeNull();
    expect(result.match).toBeTruthy();
  });
});

/* ── 9. Hub World Map ────────────────────────── */
test.describe('Hub World Map (#9)', () => {
  test('Null on non-hub zone', async ({ page }) => {
    await ready(page, '/vr/movies.html');
    const r = await page.evaluate(() => (window as any).VRSocialRich.worldMap);
    expect(r).toBeNull();
  });

  test('Available on hub zone', async ({ page }) => {
    await ready(page, '/vr/');
    const r = await page.evaluate(() => typeof (window as any).VRSocialRich.worldMap?.getCities);
    expect(r).toBe('function');
  });

  test('Returns cities array with Toronto', async ({ page }) => {
    await ready(page, '/vr/');
    const c = await page.evaluate(() => (window as any).VRSocialRich.worldMap.getCities());
    expect(c.length).toBeGreaterThanOrEqual(6);
    expect(c.find((city: any) => city.name === 'Toronto')).toBeTruthy();
  });

  test('Map canvas renders', async ({ page }) => {
    await ready(page, '/vr/');
    await page.waitForTimeout(3000);
    expect(await page.locator('#vr16-map-canvas').count()).toBeGreaterThanOrEqual(1);
  });
});

/* ── 10. Progress Milestones ─────────────────── */
test.describe('Milestones (#10)', () => {
  test('count returns a number', async ({ page }) => {
    await ready(page, '/vr/');
    const c = await page.evaluate(() => (window as any).VRSocialRich.milestones.count());
    expect(typeof c).toBe('number');
  });

  test('Thresholds defined', async ({ page }) => {
    await ready(page, '/vr/');
    const t = await page.evaluate(() => (window as any).VRSocialRich.milestones.thresholds);
    expect(t.length).toBeGreaterThanOrEqual(5);
    expect(t[0].badge).toBe('🌱');
    expect(t[0].n).toBe(10);
  });

  test('Check triggers milestone badges for high counts', async ({ page }) => {
    await ready(page, '/vr/');
    // Seed localStorage so count is high
    await page.evaluate(() => {
      localStorage.setItem('vr10_achievements', JSON.stringify(['a','b','c','d','e','f','g','h','i','j']));
    });
    await page.evaluate(() => (window as any).VRSocialRich.milestones.check());
    await page.waitForTimeout(500);
    const unlocked = await page.evaluate(() => (window as any).VRSocialRich.milestones.getUnlocked());
    expect(unlocked.length).toBeGreaterThanOrEqual(1);
  });
});

/* ── Cross-Zone JS Error Checks ──────────────── */
test.describe('Cross-Zone JS Errors', () => {
  for (const z of [
    { name: 'Hub', url: '/vr/' },
    { name: 'Movies', url: '/vr/movies.html' },
    { name: 'Creators', url: '/vr/creators.html' },
    { name: 'Stocks', url: '/vr/stocks-zone.html' },
    { name: 'Weather', url: '/vr/weather-zone.html' },
  ]) {
    test(`${z.name}: no fatal JS errors`, async ({ page }) => {
      const errs = await jsErrors(page);
      await ready(page, z.url);
      expect(errs.length).toBe(0);
    });
  }
});

/* ── Nav Menu Integration ────────────────────── */
test.describe('Nav Menu Set 16 Buttons', () => {
  test('Profile button in nav menu', async ({ page }) => {
    await ready(page, '/vr/');
    const html = await page.evaluate(() => {
      const el = document.getElementById('vr-nav-menu-2d');
      return el ? el.innerHTML : '';
    });
    expect(html).toContain('Profile');
  });

  test('Leaderboard button in nav menu', async ({ page }) => {
    await ready(page, '/vr/');
    const html = await page.evaluate(() => {
      const el = document.getElementById('vr-nav-menu-2d');
      return el ? el.innerHTML : '';
    });
    expect(html).toContain('Rank');
  });
});
