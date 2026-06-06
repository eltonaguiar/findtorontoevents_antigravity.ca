/**
 * /audit/ wording audit -- captures page content at two states:
 *   1. domcontentloaded (before JS data fetches)
 *   2. networkidle (after all JS/data fetches complete)
 */
import { test, expect } from "@playwright/test";

test.describe("/audit/ wording audit", () => {
  async function captureSnapshot(page: any) {
    const snap: Record<string, string | null> = {};
    const safe = async (sel: string) => {
      try { return await page.locator(sel).textContent(); }
      catch { return null; }
    };
    for (const cls of ["EQUITY","CRYPTO","ETF","COMMODITY","FOREX","BOND"]) {
      try { snap["mg_"+cls] = await page.locator('[data-mg-class="'+cls+'"]').textContent(); }
      catch { snap["mg_"+cls] = null; }
    }
    snap.truth = await safe("#truth-layer-reality-banner");
    snap.ml = await safe("#ml-calibration-inversion-banner");
    snap.majorGoal = await safe("#major-goal-banner");
    snap.walkforward = await safe("#walkforward-by-class-body");
    snap.ic = await safe("#ic-analysis-body");
    snap.cards = await safe("#summary-cards");
    snap.perf = await safe("#perf-alerts-container");
    snap.decile = await safe("#decile-results-panel");
    snap.matrix = await safe("#agreement-matrix");
    snap.cryptoDisp = await safe("#crypto-disputed-banner");
    snap.topNRank = await safe("#enh-top-n-rank-backtest");
    return snap;
  }

  test("1: wording before vs after JS", async ({ page }) => {
    const errs: string[] = [];
    page.on("console", (m) => { if (m.type()==="error") errs.push(m.text()); });
    page.on("pageerror", (e) => errs.push("PAGE: "+e.message));

    await page.goto("https://findtorontoevents.ca/audit/", { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForTimeout(200);
    const s1 = await captureSnapshot(page);

    await page.goto("https://findtorontoevents.ca/audit/", { waitUntil: "networkidle", timeout: 60000 });
    await page.waitForTimeout(2000);
    const s2 = await captureSnapshot(page);

    console.log("\n"+"=".repeat(70));
    console.log("WORDING AUDIT: BEFORE vs AFTER JS");
    console.log("=".repeat(70));
    let shrunk=0,appeared=0,same=0;
    for (const [k,v1] of Object.entries(s1)) {
      const v2 = s2[k];
      const a=(v1??"").trim(), b=(v2??"").trim();
      if (a===b) { same++; continue; }
      if (!a && b) { appeared++; console.log("\n[APPEARED] "+k+"\n  AFTER: "+b.substring(0,300)); continue; }
      if (a && !b) { shrunk++; console.log("\n[DISAPPEARED] "+k+"\n  BEFORE: "+a.substring(0,300)); continue; }
      if (a.length>b.length*1.15) {
        shrunk++;
        console.log("\n[SHRUNK "+a.length+"->"+b.length+"] "+k);
        console.log("  BEFORE: "+a.substring(0,300));
        console.log("  AFTER:  "+b.substring(0,300));
      } else if (b.length>a.length*1.15) {
        appeared++;
        console.log("\n[GREW "+a.length+"->"+b.length+"] "+k);
      } else {
        console.log("\n[CHANGED] "+k);
      }
    }
    console.log("\nSUMMARY: "+same+" same, "+appeared+" appeared/grew, "+shrunk+" shrunk/disappeared");
    if (errs.length) console.log("\nERRORS:\n"+errs.slice(0,20).join("\n"));
    expect(page.locator("#major-goal-banner")).toBeVisible();
    expect(page.locator("#truth-layer-reality-banner")).toBeVisible();
    const st = await page.locator("#summary-cards").textContent();
    expect((st??"").length).toBeGreaterThan(5);
  });

  test("2: Decile Results in Smart Picks tab", async ({ page }) => {
    await page.goto("https://findtorontoevents.ca/audit/", { waitUntil: "networkidle", timeout: 60000 });
    await page.locator('[data-tab="smartpicks"]').click();
    await page.waitForTimeout(1000);
    const txt = await page.locator("#decile-results-panel").textContent()??"";
    console.log("\n=== Decile Panel ===");
    console.log(txt.substring(0,600));
    const ok = /ml_score|Backtested|Spearman|Predictor|Top.*20%/i.test(txt);
    console.log("Expected content: "+ok);
    const body = page.locator(".decile-body");
    if ((await body.getAttribute("class"))?.includes("collapsed")) {
      await page.locator("#decile-results-panel h3").click();
      await page.waitForTimeout(300);
    }
    const ex = await page.locator("#decile-results-panel").textContent()??"";
    console.log("After expand has Predictor Power Ranking: "+/Predictor Power Ranking/i.test(ex));
  });

  test("3: Top-N Rank Backtest persists", async ({ page }) => {
    await page.goto("https://findtorontoevents.ca/audit/", { waitUntil: "networkidle", timeout: 60000 });
    await page.waitForTimeout(3000);
    const el = page.locator("#enh-top-n-rank-backtest");
    const vis = await el.isVisible().catch(()=>false);
    console.log("\nTop-N visible: "+vis);
    if (vis) {
      const t = await el.textContent()??"";
      console.log("Text: "+t.substring(0,400));
      expect(t).toMatch(/Rank Backtest/i);
    } else {
      await page.locator('[data-tab="overview"]').click();
      await page.waitForTimeout(2000);
      await expect(el).toBeVisible({timeout:10000});
    }
    await page.waitForTimeout(2000);
    await expect(el).toBeVisible();
  });

  test("4: keyword search", async ({ page }) => {
    await page.goto("https://findtorontoevents.ca/audit/", { waitUntil: "networkidle", timeout: 60000 });
    const text = await page.locator("body").textContent()??"";
    const terms: Record<string, RegExp> = {
      "Top-N Rank Backtest": /Top-\d+.*Rank Backtest/i,
      "HINDSIGHT REPLAY": /HINDSIGHT.*REPLAY/i,
      "Predictor Power Ranking": /Predictor Power Ranking/i,
      "Per-Symbol Agreement": /Per-Symbol Agreement/i,
      "TRUTH LAYER": /TRUTH LAYER/i,
      "ML CALIBRATION INVERTED": /ML CALIBRATION INVERTED/i,
      "MAJOR GOAL": /MAJOR GOAL/i,
      "DISPUTED CRYPTO": /DISPUTED.*CRYPTO/i,
      "System Pair": /System Pair/i,
      "Backtested on": /Backtested on \d/i,
    };
    console.log("\n=== Word Search ===");
    for (const [label, re] of Object.entries(terms)) {
      console.log("  "+label+": "+(re.test(text)?"FOUND":"NOT FOUND"));
    }
    console.log("\nBody text: "+text.length+" chars");
  });
});
