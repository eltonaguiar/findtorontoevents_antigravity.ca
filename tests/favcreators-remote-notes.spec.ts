/**
 * Remote FavCreators: verify status.php and get_notes.php return JSON (and Starfireara note when DB works),
 * and guest page shows Database connected + note when API and DB are ok.
 * Run with: VERIFY_REMOTE=1 npx playwright test tests/favcreators-remote-notes.spec.ts
 *
 * Resolves API base: tries /fc/api first, then /findevents/fc/api when host serves API under findevents.
 */

import { test, expect } from '@playwright/test';

const REMOTE_BASE = process.env.VERIFY_REMOTE_URL || 'https://findtorontoevents.ca';
const GUEST_URL = `${REMOTE_BASE}/fc/#/guest`;

/** Resolve which API base returns JSON (fc/api or findevents/fc/api). */
async function resolveFcApi(request: { get: (url: string) => Promise<{ status: () => number; text: () => Promise<string> }> }): Promise<string> {
  const primary = `${REMOTE_BASE}/fc/api`;
  const r1 = await request.get(`${primary}/status.php`);
  const t1 = await r1.text();
  if (r1.status() === 200 && t1.trim().startsWith('{')) return primary;
  const fallback = `${REMOTE_BASE}/findevents/fc/api`;
  const r2 = await request.get(`${fallback}/status.php`);
  const t2 = await r2.text();
  if (r2.status() === 200 && t2.trim().startsWith('{')) return fallback;
  return primary;
}

test.describe('FavCreators remote: Starfireara note from DB', () => {
  test('status.php returns 200 and JSON; read_ok and note when DB works', async ({ request }) => {
    const FC_API = await resolveFcApi(request);
    const res = await request.get(`${FC_API}/status.php`);
    expect(res.status()).toBe(200);
    const text = await res.text();
    expect(text.trim().startsWith('{'), 'status.php must return JSON').toBe(true);
    const data = JSON.parse(text);
    expect(data).toBeDefined();
    expect(typeof data).toBe('object');
    if (data.error) {
      test.info().annotations.push({ type: 'note', description: `status.php: ${data.error}` });
    }
    if (data.ok === true && data.read_ok === true) {
      const note = data.starfireara_note ?? data.get_notes_sample?.['6'];
      expect(note, 'when DB read ok, status.php should return starfireara_note or get_notes_sample["6"]').toBeTruthy();
    }
  });

  test('get_notes.php?user_id=0 returns 200 and JSON; creator 6 note when DB has it', async ({ request }) => {
    const FC_API = await resolveFcApi(request);
    const res = await request.get(`${FC_API}/get_notes.php?user_id=0`);
    expect(res.status()).toBe(200);
    const text = await res.text();
    expect(text.trim()).toBeTruthy();
    expect(text.trim().startsWith('{') || text.trim().startsWith('['), 'get_notes must return JSON').toBe(true);
    const notes = JSON.parse(text);
    expect(typeof notes).toBe('object');
    const note6 = notes['6'] ?? notes[6];
    if (note6) {
      test.info().annotations.push({ type: 'note', description: 'Creator 6 (Starfireara) note present' });
    }
    // Note may be empty if creator_defaults/user_notes have no row for 6 yet
    expect(notes !== null && typeof notes === 'object').toBe(true);
  });

  test('guest page shows Database banner; Starfireara note when DB configured', async ({ page }) => {
    await page.goto(GUEST_URL, { waitUntil: 'domcontentloaded', timeout: 20000 });
    await expect(page.locator('#root')).toBeVisible({ timeout: 15000 });

    await page.waitForTimeout(5000);
    const banner = page.locator('[role="status"]').filter({ hasText: /Database|Connected|Starfireara|note|Not connected/i });
    await expect(banner).toBeVisible({ timeout: 10000 });

    const bannerText = (await banner.textContent()) || '';
    expect(bannerText).toMatch(/Database|Connected|Starfireara|note|Not connected/i);

    const noteField = page.locator('#note-6');
    await expect(noteField).toBeVisible({ timeout: 8000 });
    const noteValue = await noteField.inputValue();
    if (noteValue.length > 0) {
      test.info().annotations.push({ type: 'note', description: 'Starfireara Personal note filled from DB' });
    }
    // When DB is connected (banner says Connected/Starfireara), note should be filled (run seed_creator_defaults.php or save as admin)
    const dbConnected = /Connected|Starfireara|read ok/i.test(bannerText) && !/Not connected|error|failed/i.test(bannerText);
    if (dbConnected) {
      expect(noteValue.length, 'When DB connected, Starfireara note (#note-6) should be filled; run /fc/api/seed_creator_defaults.php or save as admin').toBeGreaterThan(0);
    }
  });
});
