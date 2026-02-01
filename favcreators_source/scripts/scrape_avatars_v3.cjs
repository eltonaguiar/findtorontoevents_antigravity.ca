// Failover v3 avatar scraper for all creators (CommonJS)
const fetch = require('node-fetch');
const fs = require('fs');

const creators = [
  {
    name: 'WTFPreston',
    tiktok: 'wtfprestonlive',
    instagram: 'wtfprestonlive',
    youtube: 'wtfprestonlive',
  },
  {
    name: 'Zarthestar',
    tiktok: 'zarthestarcomedy',
    instagram: 'zar.the.star',
    youtube: 'zarthestarcomedy',
  },
  {
    name: 'Starfireara',
    tiktok: 'starfireara',
    instagram: '',
    youtube: '',
  },
  {
    name: 'Adin Ross',
    tiktok: '',
    instagram: '',
    youtube: 'adinross',
    kick: 'adinross',
  },
];

async function getTikTokAvatar(username) {
  try {
    const res = await fetch(`https://www.tiktok.com/@${username}`);
    const html = await res.text();
    const match = html.match(/"avatarLarger":"(https:[^\"]+)"/);
    return match ? match[1].replace(/\\u0026/g, '&') : null;
  } catch (e) { return null; }
}

async function getYouTubeAvatar(username) {
  try {
    const res = await fetch(`https://www.youtube.com/@${username}/about`);
    const html = await res.text();
    const match = html.match(/"avatar":{"thumbnails":\[\{"url":"([^"]+)"/);
    return match ? match[1] : null;
  } catch (e) { return null; }
}

async function getInstagramAvatar(username) {
  try {
    const res = await fetch(`https://www.instagram.com/${username}/?__a=1&__d=dis`);
    const json = await res.json();
    return json.graphql && json.graphql.user && json.graphql.user.profile_pic_url_hd || null;
  } catch (e) { return null; }
}

async function getKickAvatar(username) {
  try {
    const res = await fetch(`https://kick.com/api/v2/channels/${username}`);
    const json = await res.json();
    return json && json.user && json.user.profile_pic || null;
  } catch (e) { return null; }
}

(async () => {
  const results = [];
  for (const c of creators) {
    const row = { name: c.name };
    if (c.tiktok) row.tiktok = await getTikTokAvatar(c.tiktok);
    if (c.instagram) row.instagram = await getInstagramAvatar(c.instagram);
    if (c.youtube) row.youtube = await getYouTubeAvatar(c.youtube);
    if (c.kick) row.kick = await getKickAvatar(c.kick);
    results.push(row);
  }
  fs.writeFileSync('avatar_scrape_results_v3.json', JSON.stringify(results, null, 2));
  console.log(results);
})();
