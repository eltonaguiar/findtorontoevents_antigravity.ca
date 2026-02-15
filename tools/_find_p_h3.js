// Quick script to find p>h3 patterns in React chunks
const fs = require('fs');
const c = fs.readFileSync('next/_next/static/chunks/afe53b3593ec888c.js', 'utf8');

// Find jsx("p", ...) calls and check if h3 is nearby
let re = /jsx\)\("p"/g;
let m;
let count = 0;
while ((m = re.exec(c)) !== null) {
  count++;
  let around = c.substring(Math.max(0, m.index - 30), Math.min(c.length, m.index + 200));
  if (around.indexOf('h3') !== -1 || around.indexOf('"h2"') !== -1) {
    console.log('=== MATCH at', m.index, '===');
    console.log(around);
    console.log();
  }
}
console.log('Total jsx("p") calls:', count);

// Also search for the pattern where p wraps children that include h3
let re2 = /jsxs?\)\("p"[^)]*children[^}]*"h3"/g;
let m2;
while ((m2 = re2.exec(c)) !== null) {
  console.log('=== CHILDREN MATCH at', m2.index, '===');
  console.log(c.substring(m2.index, m2.index + 300));
  console.log();
}

// Check all chunks
const files = fs.readdirSync('next/_next/static/chunks').filter(f => f.endsWith('.js'));
for (const file of files) {
  const content = fs.readFileSync('next/_next/static/chunks/' + file, 'utf8');
  // Look for pattern: createElement("p", ..., createElement("h3"
  if (content.indexOf('"p",') !== -1 && content.indexOf('"h3"') !== -1) {
    // Look for p wrapping h3
    let idx = 0;
    while (true) {
      idx = content.indexOf('"p"', idx);
      if (idx === -1) break;
      let nearby = content.substring(idx, Math.min(content.length, idx + 300));
      if (nearby.indexOf('"h3"') !== -1 && nearby.indexOf('"h3"') < 200) {
        console.log('=== In', file, 'at', idx, '===');
        console.log(nearby.substring(0, 200));
        console.log();
      }
      idx += 3;
    }
  }
}
