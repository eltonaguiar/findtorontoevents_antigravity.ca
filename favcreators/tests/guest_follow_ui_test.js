/**
 * FavCreators GUEST follow-persistence test (production, real browser).
 *
 * Reproduces the user-reported bug for signed-out visitors on /fc/#/guest:
 *   1. Quick-Add "kick.com/kaneljoseph" -> warning toast must tell the guest
 *      to sign in -> creator appears -> RELOAD -> must STILL be followed.
 *   2. Quick-Add "kick:lirik" (platform-first colon form) -> parsed to
 *      lirik/kick -> appears -> RELOAD -> must STILL be followed.
 *
 * A fresh browser context = empty localStorage, i.e. a true guest baseline.
 * Run: node favcreators/tests/guest_follow_ui_test.js
 */
const { chromium } = require("playwright");

const SITE = "https://findtorontoevents.ca";
const CASES = [
  { input: "kick.com/kaneljoseph", handle: "kaneljoseph" },
  { input: "kick:lirik", handle: "lirik" },
];

const results = [];
const record = (name, ok, detail) => {
  results.push({ name, ok, detail });
  console.log(`  [${ok ? "PASS" : "FAIL"}] ${name}  ${detail}`);
};

async function launch() {
  try {
    return await chromium.launch({ headless: true });
  } catch (e) {
    return chromium.launch({ headless: true, channel: "chrome" });
  }
}

async function waitFor(page, fn, timeout, poll = 400) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeout) {
    if (await fn()) return true;
    await page.waitForTimeout(poll);
  }
  return false;
}

(async () => {
  const browser = await launch();
  const ctx = await browser.newContext({
    viewport: { width: 1400, height: 900 },
    userAgent:
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
  });
  const page = await ctx.newPage();

  // --- diagnostics: who wipes the guest list on reload? ---
  page.on("response", (res) => {
    if (res.url().includes("get_my_creators.php") || res.url().includes("sync_creators_table")) {
      console.log(`    [net] ${res.status()} ${res.url().slice(0, 110)}`);
    }
  });
  const dumpLS = async (label) => {
    const info = await page.evaluate(() => {
      try {
        const raw = localStorage.getItem("fav_creators");
        const arr = raw ? JSON.parse(raw) : null;
        return {
          has: !!raw,
          n: Array.isArray(arr) ? arr.length : -1,
          names: Array.isArray(arr) ? arr.slice(0, 6).map((c) => c.id) : [],
        };
      } catch (e) { return { err: String(e) }; }
    });
    console.log(`    [ls:${label}]`, JSON.stringify(info));
  };
  const dumpDom = async (label) => {
    const n = await page.locator('[class*="creator-card"]').count();
    console.log(`    [dom:${label}] creator-cards=${n}`);
  };

  await page.goto(`${SITE}/fc/#/guest`, { waitUntil: "domcontentloaded", timeout: 90000 });
  await page.waitForTimeout(10000);
  await dumpLS("initial");
  await dumpDom("initial");

  for (const c of CASES) {
    // --- clean baseline in this fresh context ---
    const before = await page.locator(`text=@${c.handle}`).count();
    record(`baseline clean (@${c.handle} absent)`, before === 0, `count=${before}`);
    if (before > 0) continue;

    // --- quick add ---
    await page.fill("input.quick-add-input", c.input);
    // Enter on the input (same handler as the button) — the floating AI-chat
    // panel (#fte-ai-panel) overlays the button and blocks pointer clicks.
    await page.press("input.quick-add-input", "Enter");

    const appeared = await waitFor(
      page,
      async () => (await page.locator(`text=@${c.handle}`).count()) > 0,
      20000
    );
    record(`quick add shows @${c.handle}`, appeared, `input=${c.input}`);

    // --- signed-out warning toast must appear ---
    const warned = await waitFor(
      page,
      async () => {
        const texts = await page.locator('[role="status"]').allInnerTexts();
        return texts.some((t) => t.includes("Not signed in") && t.includes("persist"));
      },
      10000,
      300
    );
    record(`guest warning toast for @${c.handle}`, warned, '"Not signed in ... persist" must show');

    await dumpLS("after-add");

    // --- reload: follow must survive ---
    await page.reload({ waitUntil: "domcontentloaded" });
    const early = await page.locator(`text=@${c.handle}`).count();
    console.log(`    [dom:@${c.handle}] early-after-reload=${early}`);
    await page.waitForTimeout(4000);
    await dumpLS("after-reload-4s");
    await page.waitForTimeout(9000);
    await dumpLS("after-reload-13s");
    const after = await page.locator(`text=@${c.handle}`).count();
    record(`survives reload (@${c.handle})`, after > 0, `count after refresh=${after}`);
  }

  const pass = results.filter((r) => r.ok).length;
  console.log(`\n=== FavCreators GUEST follow persistence (2 inputs x refresh) ===`);
  if (pass === results.length && results.length >= 6) {
    console.log(`ALL PASS — guest quick-adds survive refresh with warning toast (${pass}/${results.length})`);
  } else {
    console.log(`FAILED ${results.length - pass}/${results.length}`);
  }
  await browser.close();
  process.exit(pass === results.length && results.length >= 6 ? 0 : 1);
})().catch((e) => {
  console.error("GUEST_TEST_ERROR", e);
  process.exit(2);
});