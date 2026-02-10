const fs = require('fs');
const path = require('path');

const filePath = path.join(__dirname, '..', 'affiliates', 'index.html');
let html = fs.readFileSync(filePath, 'utf8');

// Map product name substring -> tags
const tagMap = [
  ['Fanxiang 1TB', 'tech,home'],
  ['42% Urea Cream', 'skincare,winter,health'],
  ['Glysomed Hand Cream', 'skincare,winter,health'],
  ['10,000 Lux Light Therapy', 'health,winter'],
  ['Sleep Eye Mask', 'eyes,travel,health'],
  ['Pulsetto Vagus', 'health,tech'],
  ['Herbion Naturals', 'health,winter,edible'],
  ['Flavored Popcorn Kit', 'edible,kitchen'],
  ['Candy Selection', 'edible,candy'],
  ['Cholula Hot Sauce', 'edible,kitchen'],
  ['Ninja Precision', 'kitchen,drinks,tech'],
  ["S'well Insulated", 'kitchen,drinks,travel'],
  ['Heated Eye Mask', 'eyes,health'],
  ['Systane Ultra', 'eyes,health,travel'],
  ['Thealoz Duo', 'eyes,health'],
  ['Contact Lens Cleaner', 'eyes,health'],
  ['Bausch + Lomb Renu', 'eyes,health'],
  ['Deep Relief Heat', 'health,pain'],
  ['Herba Joint Pain', 'health,pain'],
  ['Lactase Chewable', 'health,edible'],
  ['Atrantil', 'health'],
  ['Enzymedica Digest Gold', 'health'],
  ['Electrolytes + Magnesium', 'health,drinks,edible'],
  ['Pure Protein Bars', 'edible,health'],
  ['Red Bull Zero', 'edible,drinks'],
  ['Remington Crafter', 'grooming'],
  ['Hair Taming Stick', 'grooming,winter,travel'],
  ['Lumin Dark Circle', 'grooming,eyes,skincare'],
  ['Precision Tweezer', 'grooming'],
  ['Listerine Cool Mint', 'grooming,travel'],
  ['Wallet Tracker', 'tech,travel'],
  ['Slim Wallet', 'travel'],
  ['Rechargeable AAA', 'tech,home'],
  ['Statik 360 Magnetic', 'tech'],
  ['Snake Camera', 'tech,home'],
  ['Raid Max Ant', 'home'],
  ['Hourglass Sand', 'home,kitchen'],
  ['Meta Quest 3', 'tech,vr'],
  ['RayNeo Air', 'tech,vr,travel'],
];

let count = 0;
for (const [nameSubstr, tags] of tagMap) {
  // Find the product-name div containing this substring, then find the product-card div before it
  const nameIdx = html.indexOf(nameSubstr);
  if (nameIdx === -1) {
    console.log('NOT FOUND: ' + nameSubstr);
    continue;
  }

  // Search backwards from nameIdx to find the nearest <div class="product-card">
  const before = html.substring(0, nameIdx);
  const cardIdx = before.lastIndexOf('<div class="product-card">');
  if (cardIdx === -1) {
    console.log('NO CARD FOUND FOR: ' + nameSubstr);
    continue;
  }

  // Check if this card already has data-tags
  const cardTag = html.substring(cardIdx, cardIdx + 60);
  if (cardTag.includes('data-tags')) {
    console.log('ALREADY TAGGED: ' + nameSubstr);
    continue;
  }

  // Replace the opening tag with one that includes data-tags
  html = html.substring(0, cardIdx) +
    '<div class="product-card" data-tags="' + tags + '">' +
    html.substring(cardIdx + '<div class="product-card">'.length);
  count++;
  console.log('TAGGED: ' + nameSubstr + ' -> ' + tags);
}

fs.writeFileSync(filePath, html, 'utf8');
console.log('\nDone! Tagged ' + count + ' products.');
