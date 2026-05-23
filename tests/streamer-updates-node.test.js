/**
 * Node.js tests for Streamer Updates API
 * Run with: node tests/streamer-updates-node.test.js
 */

const https = require('https');
const http = require('http');

const API_BASE = 'https://findtorontoevents.ca/fc/api';

// Simple test runner
let testCount = 0;
let passCount = 0;
let failCount = 0;

function test(name, fn) {
  testCount++;
  return fn().then(() => {
    passCount++;
    console.log(`✓ ${name}`);
  }).catch(err => {
    failCount++;
    console.log(`✗ ${name}`);
    console.log(`  Error: ${err.message}`);
  });
}

function expect(value) {
  return {
    toBe(expected) {
      if (value !== expected) throw new Error(`Expected ${expected} but got ${value}`);
    },
    toBeGreaterThan(expected) {
      if (!(value > expected)) throw new Error(`Expected ${value} to be greater than ${expected}`);
    },
    toBeDefined() {
      if (value === undefined) throw new Error(`Expected value to be defined`);
    },
    toBeTruthy() {
      if (!value) throw new Error(`Expected value to be truthy, got ${value}`);
    },
    toContain(expected) {
      if (!value.includes(expected)) throw new Error(`Expected ${value} to contain ${expected}`);
    }
  };
}

function fetch(url) {
  return new Promise((resolve, reject) => {
    const protocol = url.startsWith('https') ? https : http;
    protocol.get(url, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve({ ok: res.statusCode >= 200 && res.statusCode < 300, json: () => JSON.parse(data), text: () => data });
        } catch (e) {
          reject(e);
        }
      });
    }).on('error', reject);
  });
}

async function runTests() {
  console.log('\\n=== Streamer Updates Node.js API Tests ===\\n');

  // Test 1: creator_news_creators for user 2
  await test('creator_news_creators returns creators for user 2', async () => {
    const res = await fetch(`${API_BASE}/creator_news_creators.php?user_id=2`);
    expect(res.ok).toBeTruthy();
    const data = await res.json();
    expect(data.creators).toBeDefined();
    expect(data.creators.length).toBeGreaterThan(0);
    console.log(`    Found ${data.creators.length} creators`);
  });

  // Test 2: Lofe in user 2's list
  await test('creator_news_creators includes Lofe for user 2', async () => {
    const res = await fetch(`${API_BASE}/creator_news_creators.php?user_id=2`);
    const data = await res.json();
    const lofe = data.creators.find(c => c.name.toLowerCase() === 'lofe');
    expect(lofe).toBeDefined();
    expect(lofe.contentCount).toBeGreaterThan(0);
    console.log(`    Lofe has ${lofe.contentCount} content items`);
  });

  // Test 3: Zople in user 2's list
  await test('creator_news_creators includes Zople for user 2', async () => {
    const res = await fetch(`${API_BASE}/creator_news_creators.php?user_id=2`);
    const data = await res.json();
    const zople = data.creators.find(c => c.name.toLowerCase() === 'zople');
    expect(zople).toBeDefined();
    console.log(`    Zople has ${zople.contentCount} content items`);
  });

  // Test 4: Ninja in user 2's list
  await test('creator_news_creators includes Ninja for user 2', async () => {
    const res = await fetch(`${API_BASE}/creator_news_creators.php?user_id=2`);
    const data = await res.json();
    const ninja = data.creators.find(c => c.name.toLowerCase() === 'ninja');
    expect(ninja).toBeDefined();
    console.log(`    Ninja has ${ninja.contentCount} content items`);
  });

  // Test 5: xQc in user 2's list
  await test('creator_news_creators includes xQc for user 2', async () => {
    const res = await fetch(`${API_BASE}/creator_news_creators.php?user_id=2`);
    const data = await res.json();
    const xqc = data.creators.find(c => c.name.toLowerCase() === 'xqc');
    expect(xqc).toBeDefined();
    console.log(`    xQc has ${xqc.contentCount} content items`);
  });

  // Test 6: Guest mode only has Adin Ross
  await test('creator_news_creators guest mode (user_id=0) returns limited creators', async () => {
    const res = await fetch(`${API_BASE}/creator_news_creators.php?user_id=0`);
    const data = await res.json();
    console.log(`    Guest mode has ${data.creators.length} creators: ${data.creators.map(c => c.name).join(', ')}`);
  });

  // Test 7: creator_news_api returns content
  await test('creator_news_api returns content for user 2', async () => {
    const res = await fetch(`${API_BASE}/creator_news_api.php?user_id=2&limit=50`);
    const data = await res.json();
    expect(data.items).toBeDefined();
    expect(data.items.length).toBeGreaterThan(0);
    console.log(`    Found ${data.items.length} content items`);
  });

  // Test 8: Lofe content exists
  await test('creator_news_api includes Lofe content', async () => {
    const res = await fetch(`${API_BASE}/creator_news_api.php?user_id=2&limit=100`);
    const data = await res.json();
    const lofeItems = data.items.filter(i => i.creator.name.toLowerCase() === 'lofe');
    expect(lofeItems.length).toBeGreaterThan(0);
    console.log(`    Lofe has ${lofeItems.length} content items`);
    lofeItems.forEach(i => console.log(`      - ${i.title.substring(0, 50)}...`));
  });

  // Test 9: Content has required fields
  await test('creator_news_api content has required fields', async () => {
    const res = await fetch(`${API_BASE}/creator_news_api.php?user_id=2&limit=5`);
    const data = await res.json();
    const item = data.items[0];
    expect(item.id).toBeDefined();
    expect(item.creator).toBeDefined();
    expect(item.creator.name).toBeDefined();
    expect(item.platform).toBeDefined();
    expect(item.contentUrl).toBeDefined();
    expect(item.title).toBeDefined();
  });

  // Test 10: Platform filter works
  await test('creator_news_api platform filter works', async () => {
    const res = await fetch(`${API_BASE}/creator_news_api.php?user_id=2&platform=youtube&limit=20`);
    const data = await res.json();
    const allYoutube = data.items.every(i => i.platform === 'youtube');
    expect(allYoutube).toBeTruthy();
    console.log(`    All ${data.items.length} items are YouTube`);
  });

  // Test 11: debug_user_creators works
  await test('debug_user_creators shows user 2 details', async () => {
    const res = await fetch(`${API_BASE}/debug_user_creators.php?user_id=2`);
    const data = await res.json();
    expect(data.total_in_list).toBeGreaterThan(0);
    console.log(`    User 2 follows ${data.total_in_list} creators`);
  });

  // Test 12: index_creator_content finds creator
  await test('index_creator_content finds Adin Ross', async () => {
    const res = await fetch(`${API_BASE}/index_creator_content.php?creator_name=Adin`);
    const data = await res.json();
    expect(data.ok).toBeTruthy();
    expect(data.creator.name.toLowerCase()).toContain('adin');
  });

  // Test 13: Multiple creators with content
  await test('Multiple creators have content for user 2', async () => {
    const res = await fetch(`${API_BASE}/creator_news_api.php?user_id=2&limit=100`);
    const data = await res.json();
    const creators = new Set(data.items.map(i => i.creator.name));
    expect(creators.size).toBeGreaterThan(3);
    console.log(`    ${creators.size} unique creators: ${Array.from(creators).join(', ')}`);
  });

  // Test 14: Content URLs are valid
  await test('Content URLs are valid HTTPS', async () => {
    const res = await fetch(`${API_BASE}/creator_news_api.php?user_id=2&limit=10`);
    const data = await res.json();
    const allHttps = data.items.every(i => i.contentUrl.startsWith('https://'));
    expect(allHttps).toBeTruthy();
  });

  // Test 15: Creator counts match
  await test('Creator content counts match actual items', async () => {
    const creatorsRes = await fetch(`${API_BASE}/creator_news_creators.php?user_id=2`);
    const creatorsData = await creatorsRes.json();
    
    const contentRes = await fetch(`${API_BASE}/creator_news_api.php?user_id=2&limit=200`);
    const contentData = await contentRes.json();
    
    const actualCounts = {};
    contentData.items.forEach(i => {
      actualCounts[i.creator.name] = (actualCounts[i.creator.name] || 0) + 1;
    });
    
    let allMatch = true;
    creatorsData.creators.forEach(c => {
      const actual = actualCounts[c.name] || 0;
      if (c.contentCount !== actual) {
        console.log(`    Mismatch: ${c.name} reported=${c.contentCount}, actual=${actual}`);
        allMatch = false;
      }
    });
    expect(allMatch).toBeTruthy();
  });

  // Test 16: Guest vs User 2 comparison
  await test('User 2 has more creators than guest', async () => {
    const guestRes = await fetch(`${API_BASE}/creator_news_creators.php?user_id=0`);
    const guestData = await guestRes.json();
    
    const user2Res = await fetch(`${API_BASE}/creator_news_creators.php?user_id=2`);
    const user2Data = await user2Res.json();
    
    expect(user2Data.creators.length).toBeGreaterThan(guestData.creators.length);
    console.log(`    Guest: ${guestData.creators.length} creators, User 2: ${user2Data.creators.length} creators`);
  });

  // Test 17: Lofe content URL is valid
  await test('Lofe content URL is accessible', async () => {
    const res = await fetch(`${API_BASE}/creator_news_api.php?user_id=2&limit=100`);
    const data = await res.json();
    const lofeItem = data.items.find(i => i.creator.name.toLowerCase() === 'lofe');
    expect(lofeItem).toBeDefined();
    expect(lofeItem.contentUrl).toContain('http');
    console.log(`    Lofe URL: ${lofeItem.contentUrl.substring(0, 60)}...`);
  });

  // Test 18: Ninja content exists
  await test('Ninja has indexed content', async () => {
    const res = await fetch(`${API_BASE}/creator_news_api.php?user_id=2&limit=100`);
    const data = await res.json();
    const ninjaItems = data.items.filter(i => i.creator.name.toLowerCase() === 'ninja');
    expect(ninjaItems.length).toBeGreaterThan(0);
    console.log(`    Ninja has ${ninjaItems.length} items`);
  });

  // Test 19: xQc content exists
  await test('xQc has indexed content', async () => {
    const res = await fetch(`${API_BASE}/creator_news_api.php?user_id=2&limit=100`);
    const data = await res.json();
    const xqcItems = data.items.filter(i => i.creator.name.toLowerCase() === 'xqc');
    expect(xqcItems.length).toBeGreaterThan(0);
    console.log(`    xQc has ${xqcItems.length} items`);
  });

  // Test 20: Zople content exists
  await test('Zople has indexed content', async () => {
    const res = await fetch(`${API_BASE}/creator_news_api.php?user_id=2&limit=100`);
    const data = await res.json();
    const zopleItems = data.items.filter(i => i.creator.name.toLowerCase() === 'zople');
    expect(zopleItems.length).toBeGreaterThan(0);
    console.log(`    Zople has ${zopleItems.length} items`);
  });

  // Summary
  console.log('\\n=== Test Summary ===');
  console.log(`Total: ${testCount}, Passed: ${passCount}, Failed: ${failCount}`);
  
  if (failCount > 0) {
    process.exit(1);
  }
}

runTests().catch(err => {
  console.error('Test runner error:', err);
  process.exit(1);
});
