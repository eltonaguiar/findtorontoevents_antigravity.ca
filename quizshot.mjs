import { chromium } from 'playwright';
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1280, height: 900 } });
await p.goto('http://localhost:8792/quiz.html', { waitUntil: 'networkidle' });
await p.waitForTimeout(1200);
await p.screenshot({ path: '/tmp/quiz_new.png' });
// functional check: answer Q1 correctly
await p.fill('#q1', 'gs.daysAgoStart(7)');
await p.click('button[onclick="checkQ1()"]');
const res = await p.textContent('#q1-result');
console.log('Q1 check:', res.trim());
await b.close();
