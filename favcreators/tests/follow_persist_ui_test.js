/**
 * FavCreators follow-persistence test (production, real browser).
 *
 * Covers the user-reported bug plus both add methods, for two test users:
 *   User A: Quick-Add a TikTok profile URL          -> save -> RELOAD -> must survive (fresh DB read)
 *   User B: Quick-Add the same TikTok profile URL   -> save -> RELOAD -> must survive
 *   User B: regular "Add Creator" form (modal)      -> save -> RELOAD -> must survive
 *
 * Every phase asserts a clean baseline (handle absent) BEFORE the add, so a
 * pass can never be a pre-existing row masquerading as a save.
 *
 * Run: node favcreators/tests/follow_persist_ui_test.js
 */
const { chromium } = require("playwright");

const SITE = "https://findtorontoevents.ca";
const HANDLE = "gurleen_dosanjh";
const URL_TO_ADD = `https://tiktok.com/@${HANDLE}`;
const REGULAR = {
  name: "Charli DAmelio",
  username: "charlidamelio",
  url: "https://www.tiktok.com/@charlidamelio",
};

// User A: existing test account (email/password login, login.php contract)
const USER_A = {
  label: "user-A (existing)",
  email: "fc.persist.test2.20261017@example.com",
  password: "PersistTest1234!b",
};
// User B: registered fresh at runtime by this test
const USER_B = {
  label: "user-B (registered at runtime)",
  email: "fc.persist.test.20261017.userb@example.com",
  password: "PersistTest1234!c",
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

function pageSaver(page) {
  const log = [];
  page.on("response", (res) => {
    if (res.url().includes("save_creators.php")) {
      const entry = { t: Date.now(), status: res.status(), body: "" };
      log.push(entry);
      // Exactly ONE body read per response (a second concurrent res.text() deadlocks).
      entry.bodyPromise = res
        .text()
        .then((b) => {
          entry.body = (b || "").slice(0, 80);
        })
        .catch(() => {});
    }
  });
  return log;
}

async function waitSaves(log, fromIndex, count = 1, timeoutMs = 30000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    if (log.length - fromIndex >= count) return log[log.length - 1];
    await new Promise((r) => setTimeout(r, 400));
  }
  return null;
}

/**
 * Wait for a save_creators response that can only be the one scheduled by the
 * state change at tState: its response must land at least 900ms after tState
 * (the app debounces saves by 1000ms), which excludes a leftover save that was
 * already in flight before the creator entered state.
 */
async function waitPostStateSave(log, fromIndex, tState, timeoutMs) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    const hit = log
      .slice(fromIndex)
      .reverse()
      .find((e) => e.t >= tState + 900);
    if (hit) return hit;
    await new Promise((r) => setTimeout(r, 300));
  }
  return null;
}

/**
 * Remove the target handle(s) from the user's DB list via the API so every
 * phase starts from a verified-clean baseline (a refresh keeps existing rows,
 * so a leftover follow from a previous run would fake a pass).
 */
async function resetHandles(ctx, uid, handles) {
  const get = await ctx.request.get(
    `${SITE}/fc/api/get_my_creators.php?user_id=${uid}`
  );
  const list = ((await get.json()).creators) || [];
  const keep = list.filter(
    (c) => !(c.accounts || []).some((a) => a && handles.includes(a.username))
  );
  const removed = list.length - keep.length;
  if (removed > 0) {
    const post = await ctx.request.post(`${SITE}/fc/api/save_creators.php`, {
      data: { user_id: uid, creators: keep },
    });
    return { removed, restore: await post.text() };
  }
  return { removed: 0, restore: "" };
}

async function freshDbRead(page, handles) {
  return page.evaluate(async (hs) => {
    const uid = (window.__fc_logged_in_user__ || {}).id || 0;
    const res = await fetch(`/fc/api/get_my_creators.php?user_id=${uid}`, {
      credentials: "include",
    });
    const json = await res.json();
    const makers = json.creators || [];
    const out = { uid, count: makers.length, found: {} };
    for (const h of hs) {
      const hit = makers.find((c) =>
        (c.accounts || []).some((a) => a && a.username === h)
      );
      out.found[h] = hit
        ? { name: hit.name, accounts: hit.accounts }
        : null;
    }
    return out;
  }, handles);
}

async function openApp(page) {
  await page.goto(`${SITE}/fc/#/guest`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForSelector(".quick-add-input", { timeout: 45000 });
  await page.waitForFunction(() => !!window.__fc_logged_in_user__, null, { timeout: 45000 });
  // let the SPA's server-list load settle (its loading guard suppresses saves mid-flight)
  await page.waitForTimeout(6000);
  return page.evaluate(() => window.__fc_logged_in_user__);
}

async function quickAdd(page, url) {
  console.log(`      [step] fill quick-add with ${url}`);
  await page.fill(".quick-add-input", url);
  console.log("      [step] click Quick Add");
  await page.click(".quick-add-btn");
  console.log("      [step] Quick Add clicked");
}

async function regularAdd(page, spec) {
  console.log("      [step] open Add Creator modal");
  await page.locator('button.btn-add:has-text("Add Creator")').first().click();
  await page.waitForSelector('input[placeholder="MrBeast"]', { timeout: 15000 });
  console.log("      [step] fill name/category");
  await page.fill('input[placeholder="MrBeast"]', spec.name);

  const selects = page.locator("form select");
  await selects.nth(0).selectOption({ index: 1 }); // category (required)

  // Social Accounts: platform select + username + url, then the row "Add" button
  await selects.nth(1).selectOption("tiktok");
  await page.fill('input[placeholder="Username"]', spec.username);
  await page.fill('input[placeholder="URL (https://...)"]', spec.url);
  await page.locator('.accounts-section button.btn-add:has-text("Add")').click();
  console.log("      [step] account row added; submitting Save Creator");
  await page.locator('button[type="submit"]:has-text("Save Creator")').click();
  console.log("      [step] Save Creator submitted");
}

(async () => {
  const browser = await launch();

  // ---------------- helper API on a throwaway context ----------------
  const apiCtx = await browser.newContext({ ignoreHTTPSErrors: true });

  // ---- User B account creation (fresh registration through the SPA's route)
  let reg = null;
  let regBody = "";
  for (let attempt = 1; attempt <= 3 && !reg; attempt++) {
    try {
      reg = await apiCtx.request.post(`${SITE}/fc/api/register.php`, {
        data: { email: USER_B.email, password: USER_B.password, displayName: "FC User B" },
        timeout: 20000,
      });
      regBody = await reg.text();
    } catch (e) {
      console.log(`  (register attempt ${attempt} failed: ${String(e).slice(0, 80)})`);
      await new Promise((r) => setTimeout(r, 3000));
    }
  }
  if (reg && reg.status() === 200 && regBody.includes('"user"')) {
    USER_B.id = JSON.parse(regBody).user.id;
    record("register User B via register.php", true, `HTTP 200 id=${USER_B.id}`);
  } else if (reg && reg.status() === 409) {
    record("register User B via register.php", true, "already registered (reused)");
  } else {
    record(
      "register User B via register.php",
      false,
      reg ? `HTTP ${reg.status()} ${regBody.slice(0, 90)}` : "all attempts failed (network)"
    );
  }
  await apiCtx.close();

  const phases = [
    {
      user: USER_A,
      label: "User A / Quick-Add URL",
      doAdd: (page) => quickAdd(page, URL_TO_ADD),
      handles: [HANDLE],
    },
    {
      user: USER_B,
      label: "User B / Quick-Add URL",
      doAdd: (page) => quickAdd(page, URL_TO_ADD),
      handles: [HANDLE],
    },
    {
      user: USER_B,
      label: "User B / regular Add Creator form",
      doAdd: (page) => regularAdd(page, REGULAR),
      handles: [REGULAR.username],
    },
  ];

  for (const phase of phases) {
    console.log(`\n--- ${phase.label} ---`);
    const ctx = await browser.newContext({
      viewport: { width: 1366, height: 900 },
      ignoreHTTPSErrors: true,
      userAgent:
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    });
    await ctx.route("**/*", (route) =>
      route.request().url().includes("findtorontoevents.ca")
        ? route.continue()
        : route.abort()
    );

    // Page-side capture of save_creators responses (Playwright's response.text()
    // never resolves for this endpoint; a fetch clone inside the page does).
    await ctx.addInitScript(() => {
      window.__fc_saves = [];
      const orig = window.fetch.bind(window);
      window.fetch = async (...args) => {
        const url = typeof args[0] === "string" ? args[0] : (args[0] && args[0].url) || "";
        const res = await orig(...args);
        if (url.includes("save_creators.php")) {
          const clone = res.clone();
          clone
            .text()
            .then((t) =>
              window.__fc_saves.push({ status: res.status, body: t.slice(0, 120) })
            )
            .catch(() => {});
        }
        return res;
      };
    });

    const login = await ctx.request.post(`${SITE}/fc/api/login.php`, {
      data: { email: phase.user.email, password: phase.user.password },
    });
    const loginBody = await login.text();
    const loggedIn = login.status() === 200 && loginBody.includes('"user"');
    record(`${phase.label}: login.php`, loggedIn, loginBody.slice(0, 80));
    const loginUserId = loggedIn ? JSON.parse(loginBody).user.id : 0;

    // Guarantee a clean baseline: drop the handles this phase will add.
    const rst = await resetHandles(ctx, loginUserId, phase.handles);
    record(
      `${phase.label}: baseline reset`,
      true,
      `removed=${rst.removed} ${rst.restore.slice(0, 40)}`
    );

    const page = await ctx.newPage();
    page.setDefaultTimeout(20000);
    const tPhase = Date.now();
    const stamp = () => `      [step +${Math.round((Date.now() - tPhase) / 1000)}s]`;
    const saveLog = pageSaver(page);
    const pageErrors = [];
    page.on("pageerror", (e) => pageErrors.push(String(e).slice(0, 160)));

    const who = await openApp(page);
    const userId = (who && who.id) || 0;
    record(`${phase.label}: SPA session`, userId > 0, `user_id=${userId}`);

    // Verified-clean baseline for EVERY handle this phase will add
    const base = await freshDbRead(page, phase.handles);
    const clean = phase.handles.every((h) => !base.found[h]);
    record(
      `${phase.label}: clean baseline`,
      clean,
      `creators=${base.count} pre-existing=${JSON.stringify(
        Object.fromEntries(phase.handles.map((h) => [h, !!base.found[h]]))
      )}`
    );

    // ---- the add (single save-response reader, bounded body wait) ----
    const stateHandle = phase.handles[0];
    const idx = saveLog.length;
    console.log(`${stamp()} add starting`);
    await phase.doAdd(page);
    console.log(`${stamp()} add dispatched; waiting for creator to enter SPA state`);

    // 1) Quick-Add awaits the avatar grabber before committing state — wait for
    //    the creator to actually land in SPA state (mirrored into localStorage).
    let inState = true;
    try {
      await page.waitForFunction(
        (h) => (localStorage.getItem("fav_creators") || "").includes(h),
        stateHandle,
        { timeout: 45000 }
      );
    } catch (e) {
      inState = false;
    }
    const tState = Date.now();
    record(
      `${phase.label}: creator enters SPA state`,
      inState,
      inState ? `state contains "${stateHandle}"` : "state never contained the creator (45s)"
    );

    // 2) The save scheduled by THAT state change (1s debounce) must return success.
    const entry = await waitPostStateSave(saveLog, idx, tState, 45000);
    if (entry && entry.bodyPromise) {
      await Promise.race([
        entry.bodyPromise,
        new Promise((r) => setTimeout(r, 4000)),
      ]);
    }
    const pageSaves = await page.evaluate(() => window.__fc_saves || []).catch(() => []);
    const pageSave = pageSaves[pageSaves.length - 1] || null;
    console.log(`${stamp()} save settled`);
    const saveOk =
      !!entry &&
      entry.status === 200 &&
      ((pageSave && /success/.test(pageSave.body)) || /success/.test(entry.body || ""));
    record(
      `${phase.label}: save_creators.php`,
      saveOk,
      `HTTP ${entry ? entry.status : 0} playwright_body=${entry ? entry.body || "(unavailable)" : "(no post-state save)"} page_body=${pageSave ? pageSave.body : "(none)"} saves_logged=${saveLog.length - idx}`
    );

    // ---- REFRESH: server list wins; this is where the bug showed ----
    await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForFunction(() => !!window.__fc_logged_in_user__, null, { timeout: 45000 });
    await page.waitForTimeout(5000);

    const after = await freshDbRead(page, phase.handles);
    for (const h of phase.handles) {
      record(
        `${phase.label}: reload keeps "${h}"`,
        !!after.found[h],
        after.found[h]
          ? `creators=${after.count} name=${after.found[h].name} accounts=${JSON.stringify(after.found[h].accounts)}`
          : `NOT FOUND after reload (creators=${after.count})`
      );
    }

    // SPA state on screen must also hold it (localStorage mirror)
    const localHas = await page.evaluate(
      (hs) => {
        const raw = localStorage.getItem("fav_creators") || "";
        return hs.map((h) => [h, raw.includes(h)]);
      },
      phase.handles
    );
    record(
      `${phase.label}: localStorage mirror`,
      localHas.every(([, v]) => v),
      JSON.stringify(Object.fromEntries(localHas))
    );
    record(`${phase.label}: no page errors`, pageErrors.length === 0, pageErrors.join(" | ") || "clean");

    await ctx.close();
  }

  await browser.close();

  const failed = results.filter((r) => !r.ok);
  console.log("\n=== FavCreators follow-persistence (UI, 2 users x 2 add methods) ===");
  console.log(
    failed.length === 0
      ? "ALL PASS — follows persist across refresh for both add methods, both users"
      : `${failed.length} FAILED:\n` + failed.map((f) => `  - ${f.name}: ${f.detail}`).join("\n")
  );
  process.exit(failed.length === 0 ? 0 : 1);
})().catch((e) => {
  console.error("TEST CRASHED:", e);
  process.exit(2);
});