// scripts/fetchTwitchAvatar.js
// Usage: node scripts/fetchTwitchAvatar.js <twitch_username>
// Requires: node-fetch (npm install node-fetch@2)

const fetch = require('node-fetch');

const CLIENT_ID = 'vowdmej43crbuq3o6bu7edrv9wmyd5';
const CLIENT_SECRET = 'ixckc8kqhk51h0bqgj2fko90bjrnrf';

async function getOAuthToken() {
  const resp = await fetch('https://id.twitch.tv/oauth2/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: `client_id=${CLIENT_ID}&client_secret=${CLIENT_SECRET}&grant_type=client_credentials`
  });
  const data = await resp.json();
  if (!data.access_token) throw new Error('Failed to get access token: ' + JSON.stringify(data));
  return data.access_token;
}

async function getTwitchAvatar(username, token) {
  const resp = await fetch(`https://api.twitch.tv/helix/users?login=${username}`, {
    headers: {
      'Client-ID': CLIENT_ID,
      'Authorization': `Bearer ${token}`
    }
  });
  const data = await resp.json();
  if (data.data && data.data[0] && data.data[0].profile_image_url) {
    return data.data[0].profile_image_url;
  }
  throw new Error('No avatar found for user: ' + username);
}

async function main() {
  const username = process.argv[2];
  if (!username) {
    console.error('Usage: node scripts/fetchTwitchAvatar.js <twitch_username>');
    process.exit(1);
  }
  try {
    const token = await getOAuthToken();
    const avatar = await getTwitchAvatar(username, token);
    console.log(`Avatar for ${username}: ${avatar}`);
  } catch (e) {
    console.error(e);
    process.exit(1);
  }
}

main();
