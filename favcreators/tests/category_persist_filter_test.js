/**
 * FavCreators CATEGORY persistence + filter test (reported 2026-10-18).
 *
 * User zerounderscore@gmail.com created category "TorontoStreamer", added two
 * creators they already follow (Kick Moxie, TikTok @a.r.a.moore) to it via the
 * bulk "Apply category" action — then filtering by the category showed nothing.
 *
 * Root cause (fixed in docs/assets/main-DF_ZQ_dn.js):
 *   1. Bulk "Apply category" (Ss) and Rename Category (yl) updated React state
 *      but never called the persist function Ra() -> save_creators.php, so the
 *      assignment evaporated on reload (server list always won with "Other").
 *   2. The category filter compared with exact-case `creator.category === filter`
 *      against mixed-case stored data ("other" vs "Other" vs "entertainment"),
 *      so even persisted categories could filter to zero creators.
 *   3. Add-Creator modal save (hi) also skipped Ra() (same lost-on-reload class).
 *
 * What this test proves end-to-end (real MySQL via API):
 *   - quick-add the two reported creators (Kick moxie + TikTok a.r.a.moore)
 *   - create category "TorontoStreamer" (➕ New Cat prompt)
 *   - select both creators in Table view, bulk "Apply category"
 *   - a save_creators.php POST fires carrying the new category
 *   - FRESH DB READ shows category=TorontoStreamer on both creators
 *   - reload: category survives (server list wins)
 *   - filtering by "TorontoStreamer" shows both creators (not an empty list)
 *
 * Run (local build + live API):
 *   FAVCREATORS_API_PROXY=https://findtorontoevents.ca python3 tools/serve_local.py &
 *   node favcreators/tests/category_persist_filter_test.js
 * Run against production UI (after FTP deploy):
 *   SITE=https://findtorontoevents.ca node favcreators/tests/category_persist_filter_test.js
 */
const { chromium } = require("playwright");

const SITE = process.env.SITE || "http://localhost:5173";
const CATEGORY = "TorontoStreamer";
const CREATORS = [
  { handle: "moxie", url: "https://kick.com/moxie", label: "Moxie (Kick)" },
  { handle: "a.r.a.moore", url: "https://tiktok.com/@a.r.a.moore", label: "A.r.a.moore (TikTok)" },
];

const STAMP = Date.now();
const USER = {
  email: `fc.cattest.${STAMP}@example.com`,
  password: "CatTest1234!x",
  id: null,
};

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

/** Page-side capture of save_creators.php responses (Playwright's
 *  response.text() never resolves for this endpoint; a fetch clone inside
 *  the page does — same trick as follow_persist_ui_test.js). */
async function addSaveCapture(ctx) {
  await ctx.addInitScript(() => {
    window.__fc_saves = [];
    const orig = window.fetch.bind(window);
    window.fetch = async (...args) => {
      const url = typeof args[0] === "string" ? args[0] : (args[0] && args[0].url) || "";
      const res = await orig(...args);
      if (url.includes("save_creators.php")) {
        // capture the REQUEST body (what was persisted), not just the response
        let reqBody = "";
        try {
          reqBody = args[1] && args[1].body ? String(args[1].body) : "";
        } catch (e) {}
        const clone = res.clone();
        clone
          .text()
          .then((t) =>
            window.__fc_saves.push({ t: Date.now(), status: res.status, body: t.slice(0, 200), reqBody })
          )
          .catch(() => {});
      }
      return res;
    };
  });
}

async function openApp(page) {
  await page.goto(`${SITE}/fc/#/guest`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForSelector(".quick-add-input", { timeout: 45000 });
  await page.waitForFunction(() => !!window.__fc_logged_in_user__, null, { timeout: 45000 });
  // let the SPA's server-list load settle (its loading guard suppresses saves mid-flight)
  await page.waitForTimeout(6000);
  return page.evaluate(() => window.__fc_logged_in_user__);
}

async function quickAddAndPersist(page, url, handle) {
  const idx = (await page.evaluate(() => window.__fc_saves.length)) || 0;
  await page.fill(".quick-add-input", url);
  await page.click(".quick-add-btn");
  await page.waitForFunction(
    (h) => (localStorage.getItem("fav_creators") || "").includes(h),
    handle,
    { timeout: 45000 }
  );
  const t0 = Date.now();
  let saved = null;
  while (Date.now() - t0 < 45000) {
    const saves = await page.evaluate(() => window.__fc_saves);
    const post = (saves || []).slice(idx).find((s) => s.t >= Date.now() - 44000 && /success/i.test(s.body));
    if (post) { saved = post; break; }
    await new Promise((r) => setTimeout(r, 500));
  }
  return saved;
}

async function freshDbRead(page, handles) {
  return page.evaluate(async (hs) => {
    const uid = (window.__fc_logged_in_user__ || {}).id || 0;
    const res = await fetch(`/fc/api/get_my_creators.php?user_id=${uid}`, { credentials: "include" });
    const json = await res.json();
    const makers = json.creators || [];
    const out = { uid, count: makers.length, found: {} };
    for (const h of hs) {
      const hit = makers.find((c) => (c.accounts || []).some((a) => a && a.username === h));
      out.found[h] = hit ? { name: hit.name, category: hit.category } : null;
    }
    return out;
  }, handles);
}

/** Remove the test handles from the user's DB list so the run starts clean. */
async function resetHandles(ctx, uid, handles) {
  const get = await ctx.request.get(`${SITE}/fc/api/get_my_creators.php?user_id=${uid}`);
  const list = ((await get.json()).creators) || [];
  const keep = list.filter((c) => !(c.accounts || []).some((a) => a && handles.includes(a.username)));
  if (keep.length !== list.length) {
    await ctx.request.post(`${SITE}/fc/api/save_creators.php`, {
      data: { user_id: uid, creators: keep },
    });
  }
  return list.length - keep.length;
}

(async () => {
  const browser = await launch();
  const apiCtx = await browser.newContext({ ignoreHTTPSErrors: true });

  // ---- register a fresh throwaway account (isolated list; never touches real users)
  const reg = await apiCtx.request.post(`${SITE}/fc/api/register.php`, {
    data: { email: USER.email, password: USER.password, displayName: "FC Cat Test" },
    timeout: 25000,
  });
  const regBody = await reg.text();
  const regOk = (reg.status() === 200 && regBody.includes('"user"')) || reg.status() === 409;
  if (reg.status() === 200 && regBody.includes('"user"')) USER.id = JSON.parse(regBody).user.id;
  record("register throwaway test user", regOk, `HTTP ${reg.status()} ${regBody.slice(0, 80)}`);

  const ctx = await browser.newContext({
    viewport: { width: 1366, height: 900 },
    ignoreHTTPSErrors: true,
    userAgent:
      "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
  });
  await addSaveCapture(ctx);
  // dialogs: ➕ New Cat uses window.prompt
  let promptValue = null;

  const login = await ctx.request.post(`${SITE}/fc/api/login.php`, {
    data: { email: USER.email, password: USER.password },
  });
  const loginBody = await login.text();
  const loggedIn = login.status() === 200 && loginBody.includes('"user"');
  record("login.php", loggedIn, loginBody.slice(0, 80));
  const uid = loggedIn ? JSON.parse(loginBody).user.id : 0;

  const removed = await resetHandles(ctx, uid, CREATORS.map((c) => c.handle));
  record("baseline reset", true, `removed=${removed}`);

  const page = await ctx.newPage();
  page.setDefaultTimeout(25000);
  const pageErrors = [];
  page.on("pageerror", (e) => pageErrors.push(String(e).slice(0, 200)));
  page.on("dialog", async (d) => {
    if (d.type() === "prompt" && promptValue) await d.accept(promptValue);
    else await d.accept(d.type() === "confirm" ? true : undefined);
  });

  const who = await openApp(page);
  record("SPA session", !!who && who.id > 0, `user_id=${who && who.id}`);

  // ---- 1. quick-add both reported creators ----
  for (const c of CREATORS) {
    const saved = await quickAddAndPersist(page, c.url, c.handle);
    record(`quick-add ${c.label} persists`, !!saved, saved ? `save body=${saved.body}` : "no successful save after add");
  }

  // ---- 2. create the category (New Cat prompt) ----
  promptValue = CATEGORY;
  await page.locator('button[title="Create New Category"]').click();
  await page.waitForFunction(
    (cat) => (localStorage.getItem("fav_creators_categories") || "").includes(cat),
    CATEGORY,
    { timeout: 10000 }
  ).catch(() => {});
  const catCreated = await page.evaluate(
    (cat) => (localStorage.getItem("fav_creators_categories") || "").includes(cat),
    CATEGORY
  );
  record(`category "${CATEGORY}" created`, catCreated, `fav_creators_categories=${await page.evaluate(() => localStorage.getItem("fav_creators_categories"))}`);

  // ---- 3. Table view: select both creators, bulk Apply category ----
  await page.locator("button.btn-secondary", { hasText: /Tabular View/i }).first().click();
  await page.waitForTimeout(800);
  for (const c of CREATORS) {
    const row = page.locator("tr", { hasText: new RegExp(c.handle, "i") }).first();
    await row.locator('input[type="checkbox"]').first().click();
    await page.waitForTimeout(300);
  }
  const bulkVisible = await page.locator(".bulk-action-bar").isVisible().catch(() => false);
  record("bulk action bar appears after selecting 2 creators", bulkVisible, bulkVisible ? "visible" : "NOT visible");

  const savesBefore = await page.evaluate(() => window.__fc_saves.length);
  await page.locator(".bulk-action-bar select").first().selectOption(CATEGORY);
  await page.locator('button:has-text("Apply category")').first().click();
  await page.waitForTimeout(2500);

  // ---- 4. save fired with the category ----
  const saves = await page.evaluate(() => window.__fc_saves);
  const catSave = (saves || []).slice(savesBefore).find((s) => (s.reqBody || "").includes(CATEGORY));
  record("save_creators.php fired with new category", !!catSave, catSave ? `HTTP ${catSave.status} body=${catSave.body.slice(0, 100)}` : `no save containing ${CATEGORY} (saves=${(saves || []).length - savesBefore})`);

  // ---- 5. FRESH DB READ: category persisted server-side ----
  const db1 = await freshDbRead(page, CREATORS.map((c) => c.handle));
  const allSet = CREATORS.every((c) => db1.found[c.handle] && String(db1.found[c.handle].category).toLowerCase() === CATEGORY.toLowerCase());
  record("fresh DB read: both creators have the category", allSet, JSON.stringify(db1.found));

  // ---- 6. reload: server list wins, category must survive ----
  await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForFunction(() => !!window.__fc_logged_in_user__, null, { timeout: 45000 });
  await page.waitForTimeout(6000);
  const db2 = await freshDbRead(page, CREATORS.map((c) => c.handle));
  const survived = CREATORS.every((c) => db2.found[c.handle] && String(db2.found[c.handle].category).toLowerCase() === CATEGORY.toLowerCase());
  record("after reload: category survives (server wins)", survived, JSON.stringify(db2.found));

  const catListOk = await page.evaluate(
    (cat) => (localStorage.getItem("fav_creators_categories") || "").includes(cat),
    CATEGORY
  );
  record("after reload: category still in category list", catListOk, String(catListOk));

  // ---- 7. filter by the category: both creators must be visible ----
  await page.locator(".filter-dropdown").first().selectOption(CATEGORY);
  await page.waitForTimeout(1200);
  const visible = await page.evaluate(() => {
    const txt = document.body.innerText.toLowerCase();
    return { moxie: txt.includes("moxie"), ara: txt.includes("a.r.a.moore") };
  });
  record("filter by category shows Moxie", visible.moxie, JSON.stringify(visible));
  record("filter by category shows A.r.a.moore", visible.ara, JSON.stringify(visible));

  record("no page errors", pageErrors.length === 0, pageErrors.join(" | ") || "clean");

  await ctx.close();
  await apiCtx.close();
  await browser.close();

  const failed = results.filter((r) => !r.ok);
  console.log("\n=== FavCreators category persistence + filter ===");
  console.log(
    failed.length === 0
      ? "ALL PASS — bulk Apply category persists across reload and filtering shows the creators"
      : `${failed.length} FAILED:\n` + failed.map((f) => `  - ${f.name}: ${f.detail}`).join("\n")
  );
  process.exit(failed.length === 0 ? 0 : 1);
})().catch((e) => {
  console.error("TEST CRASHED:", e);
  process.exit(2);
});
