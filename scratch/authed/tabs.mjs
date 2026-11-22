import { chromium } from 'playwright';
const browser = await chromium.connectOverCDP('http://localhost:9222');
const pages = browser.contexts()[0].pages();
for (const [i, page] of pages.entries()) {
  const url = page.url();
  const title = (await page.title().catch(() => '')).slice(0, 55);
  const text = ((await page.innerText('body').catch(() => '')) || '').replace(/\s+/g, ' ');
  const blocked = /access denied|unusual traffic|verify you are|just a moment|something went wrong|robot/i.test(text);
  // console-focused: lines naming a console AND a price or stock word
  const lines = text.split(/(?<=\.)\s+|\s{2,}/).filter(l =>
    /series [xs]/i.test(l) && /(\$[\d,]+\.\d{2}|in stock|out of stock|sold out|add to cart|unavailable)/i.test(l));
  const prices = [...new Set(lines.flatMap(l => l.match(/\$[\d,]+\.\d{2}/g) || []))].slice(0, 5);
  const stock = [...new Set((text.match(/(in stock|out of stock|sold out|add to cart|unavailable)/gi) || []).map(s => s.toLowerCase()))];
  console.log(`\n[${i}] ${title}`);
  console.log(`    ${url.slice(0, 90)}`);
  console.log(`    blocked=${blocked}  stock words: ${stock.join(', ') || '-'}`);
  console.log(`    console prices: ${prices.join(', ') || '-'}`);
  const sample = lines.slice(0, 2).map(l => l.slice(0, 110));
  sample.forEach(s => console.log(`    > ${s}`));
}
await browser.close();
