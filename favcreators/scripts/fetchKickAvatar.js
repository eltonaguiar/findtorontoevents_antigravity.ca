// scripts/fetchKickAvatar.js
// Usage: node scripts/fetchKickAvatar.js <kick_username>
// Note: As of early 2026, Kick does not have a public OAuth API for user info like Twitch.
// This script fetches the profile image by scraping the public Kick user API.

const fetch = require('node-fetch');

async function getKickAvatar(username) {
  // Kick's public API endpoint for user info
  const apiUrl = `https://kick.com/api/v2/channels/${username}`;
  const resp = await fetch(apiUrl);
  if (!resp.ok) throw new Error(`Failed to fetch Kick user: ${resp.status}`);
  const data = await resp.json();
  if (data && data.user && data.user.profile_pic) {
    return data.user.profile_pic;
  }
  throw new Error('No avatar found for user: ' + username);
}

async function main() {
  const username = process.argv[2];
  if (!username) {
    console.error('Usage: node scripts/fetchKickAvatar.js <kick_username>');
    process.exit(1);
  }
  try {
    const avatar = await getKickAvatar(username);
    console.log(`Avatar for ${username}: ${avatar}`);
  } catch (e) {
    console.error(e);
    process.exit(1);
  }
}

main();
