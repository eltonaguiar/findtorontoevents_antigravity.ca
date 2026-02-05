// src/utils/socialProfileVerifier.ts
// Given a username and platform, attempt to verify and return the correct profile URL for all major platforms.
// Optionally, use Google search as fallback for ambiguous cases.

import { googleSearchYoutubeChannel } from './googleSearch';

export async function getOfficialProfileUrl(platform: string, username: string): Promise<string | null> {
  const clean = username.trim().replace(/^@/, '');
  switch (platform) {
    case 'youtube': {
      // Try handle first, fallback to Google search
      const handleUrl = `https://www.youtube.com/@${clean}`;
      // Optionally, verify existence via fetch (HEAD or GET)
      // If not found, fallback to Google search
      // For now, always prefer handle, but allow override for known exceptions
      if (/zarthestar|z star tv|zstartv/i.test(clean)) {
        return 'https://www.youtube.com/@zarthestarcomedy';
      }
      // TODO: Add more exceptions as needed
      // Optionally, verify handle exists (not 404)
      return handleUrl;
    }
    case 'tiktok':
      return `https://www.tiktok.com/@${clean}`;
    case 'instagram':
      return `https://www.instagram.com/${clean}`;
    case 'twitch':
      return `https://www.twitch.tv/${clean}`;
    case 'kick':
      return `https://kick.com/${clean}`;
    default:
      // Fallback: try Google search for the username and platform
      if (platform && clean) {
        const query = `${clean} official ${platform}`;
        if (platform === 'youtube') {
          return await googleSearchYoutubeChannel(query);
        }
        // For other platforms, you could implement similar search logic
      }
      return null;
  }
}
