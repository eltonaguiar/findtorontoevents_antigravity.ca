// One-off generator: writes a Playwright smoke test for torontoevent.net/MOVIESHOWS3/.
//
// Repaired 2026-11-23. The string array embedded UNESCAPED double quotes
// ("...require("playwright")..."), so the file was not parseable JavaScript at all.
// Same behaviour, plus three fixes to the code it emits, which could never have run:
//   page.$   -> page.$$     (.length on a single ElementHandle is undefined)
//   page.eval -> page.$eval (page.eval is not a Playwright API)
//   the "$" concatenation trick -> written plainly
const fs = require("fs");

const lines = [
  'const { chromium } = require("playwright");',
  "(async () => {",
  '  const browser = await chromium.launch({ args: ["--disable-cache"] });',
  "  const page = await browser.newPage();",
  "  const errors = [];",
  "  const apiResponses = [];",
  '  page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });',
  '  page.on("response", r => { if (r.url().includes("get-movies")) apiResponses.push({ url: r.url(), status: r.status() }); });',
  '  await page.goto("https://torontoevent.net/MOVIESHOWS3/", { waitUntil: "domcontentloaded", timeout: 30000 });',
  "  await page.waitForTimeout(8000);",
  '  const cards = await page.$$(".movie-card");',
  '  const gridContent = await page.$eval("#movies-grid", el => el.children.length).catch(() => 0);',
  '  const corsErrors = errors.filter(e => e.includes("CORS") || e.includes("Access-Control"));',
  '  console.log("API responses (cross-origin):", JSON.stringify(apiResponses));',
  '  console.log("Console errors:", JSON.stringify(errors));',
  '  console.log("CORS errors:", JSON.stringify(corsErrors));',
  '  console.log("Movie cards count:", cards.length);',
  '  console.log("Grid children:", gridContent);',
  "  const pass = cards.length > 50 && corsErrors.length === 0;",
  '  console.log(pass ? "RESULT: PASS - Movies loaded from cross-origin API" : "RESULT: FAIL - Check errors above");',
  "  await browser.close();",
  "})()",
].join("\n");

fs.writeFileSync("E:/findtorontoevents_antigravity.ca/test_ms3_torontoevent.js", lines);
console.log("Written:", lines.length);
