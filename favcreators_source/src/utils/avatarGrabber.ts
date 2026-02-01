import { fetchViaProxy, fetchWithTimeout } from "./proxyFetch";
import type { SocialAccount } from "../types";
import { googleSearchImage } from "./googleSearch";

const PLATFORM_PRIORITY: SocialAccount["platform"][] = [
  "instagram",
  "youtube",
  "tiktok",
  "kick",
  "twitch",
  "other",
];

const DEFAULT_AVATAR_PATTERNS = [
  /user-default-pictures/i,
  /default-profile_image/i,
  /default-user-image/i,
  /static-cdn\.jtvnw\.net\//i,
];

const isPlaceholderAvatar = (url: string | null | undefined): boolean => {
  if (!url) return false;
  return DEFAULT_AVATAR_PATTERNS.some((pattern) => pattern.test(url));
};

const normalizeCandidate = (url?: string | null): string | null => {
  if (!url) return null;
  const trimmed = url.trim();
  if (!trimmed || !trimmed.startsWith("http")) return null;
  if (isPlaceholderAvatar(trimmed)) return null;
  return trimmed;
};

const buildUnavatarCandidate = (account: SocialAccount): string | null => {
  const username = account.username?.trim();
  const url = account.url?.trim();

  if (username) {
    switch (account.platform) {
      case "youtube":
        return `https://unavatar.io/youtube/${encodeURIComponent(username)}`;
      case "twitch":
        return `https://unavatar.io/twitch/${encodeURIComponent(username)}`;
      case "tiktok":
        return `https://unavatar.io/tiktok/${encodeURIComponent(username)}`;
      case "instagram":
        return `https://unavatar.io/instagram/${encodeURIComponent(username)}`;
      default:
        break;
    }
  }

  if (url) {
    return `https://unavatar.io/${encodeURIComponent(url)}`;
  }

  return null;
};

const extractAvatarFromHtml = (html: string): string | null => {
  // 1. Try Kick specific ID first (common for Kick profiles)
  const kickAvatarMatch = html.match(/id\s*=\s*["']channel-avatar["'][^>]+src\s*=\s*["']([^"']+)["']/i) ||
    html.match(/src\s*=\s*["']([^"']+)["'][^>]+id\s*=\s*["']channel-avatar["']/i);
  if (kickAvatarMatch && kickAvatarMatch[1]) {
    return kickAvatarMatch[1];
  }

  // 2. Try og:image
  const metaMatch =
    html.match(/<meta\s+(?:property|name)=["']og:image["']\s+content=["']([^"']+)["']/i);
  if (metaMatch && metaMatch[1]) {
    const url = metaMatch[1].split("?")[0];
    if (url.startsWith("http")) {
      return url;
    }
  }

  // 3. Try image_src link
  const linkMatch = html.match(/<link\s+rel=["']image_src["']\s+href=["']([^"']+)["']/i);
  if (linkMatch && linkMatch[1] && linkMatch[1].startsWith("http")) {
    return linkMatch[1];
  }

  return null;
};

const fetchAvatarFromUrl = async (url: string, platform?: string, username?: string): Promise<string | null> => {
  // 1. Try platform-specific API for Twitch
  if (platform === "twitch" && username) {
    try {
      // Use Twitch public API
      const apiUrl = `https://decapi.me/twitch/avatar/${username}`;
      const resp = await fetchWithTimeout(apiUrl);
      if (resp.ok) {
        const avatarUrl = await resp.text();
        const candidate = normalizeCandidate(avatarUrl);
        if (candidate) return candidate;
      }
    } catch (err) {
      console.warn("Twitch API avatar fetch failed", err);
    }
  }

  // 2. Try platform-specific API for Kick
  if (platform === "kick" && username) {
    try {
      const apiUrl = `https://kick.com/api/v2/channels/${username}`;
      const json = await fetchViaProxy(apiUrl);
      if (json) {
        const data = JSON.parse(json);
        if (data && data.user) {
          const avatarUrl = data.user.profile_picture || data.user.profile_pic;
          const candidate = normalizeCandidate(
            typeof avatarUrl === "string" ? avatarUrl : null,
          );
          if (candidate) return candidate;
        }
      }
    } catch (err) {
      console.warn("Kick API avatar fetch failed", err);
    }
  }

  // 3. Special handling for TikTok/Instagram (Harder to scrape)
  if (platform === "tiktok" || platform === "instagram") {
    try {
      // Use Jina directly for these as it's the most reliable for Cloudflare/Auth walls
      const jinaUrl = `https://r.jina.ai/${url}`;
      const resp = await fetchWithTimeout(jinaUrl, 12000);
      if (resp.ok) {
        const html = await resp.text();
        const avatar = extractAvatarFromHtml(html);
        const candidate = normalizeCandidate(avatar);
        if (candidate) return candidate;
      }
    } catch (err) {
      console.warn(`${platform} Jina scrape failed`, err);
    }
  }

  // 4. Default scraping HTML using centralized proxy fetch
  try {
    const html = await fetchViaProxy(url);
    if (html) {
      const avatar = extractAvatarFromHtml(html);
      const candidate = normalizeCandidate(avatar);
      if (candidate) return candidate;
    }
  } catch (error) {
    console.warn("Scraping avatar failed", url, error);
  }

  return null;
}

export async function grabAvatarFromAccounts(
  accounts: SocialAccount[],
  fallbackName?: string
): Promise<string | null> {
  // 1. Try to get avatar from social media profiles
  for (const platform of PLATFORM_PRIORITY) {
    const platformAccounts = accounts.filter(
      (account) => account.platform === platform && account.url,
    );
    for (const account of platformAccounts) {
      try {
        const avatar = await fetchAvatarFromUrl(account.url, account.platform, account.username);
        if (avatar) return avatar;
      } catch (err) {
        console.warn(`Failed to fetch avatar from ${account.platform}`, err);
      }
    }
  }

  for (const platform of PLATFORM_PRIORITY) {
    const platformAccounts = accounts.filter(
      (account) => account.platform === platform,
    );
    for (const account of platformAccounts) {
      const unavatar = buildUnavatarCandidate(account);
      if (unavatar) return unavatar;
    }
  }

  if (fallbackName) {
    console.log(`No avatar found for ${fallbackName} from social links. Trying Google Image failover...`);
    try {
      const googleAvatar = await googleSearchImage(fallbackName);
      if (googleAvatar) {
        console.log(`Successfully found failover avatar for ${fallbackName}:`, googleAvatar);
        return googleAvatar;
      }
    } catch (err) {
      console.warn("Google Image failover failed", err);
    }
  }

  if (fallbackName) {
    return `https://api.dicebear.com/7.x/pixel-art/svg?seed=${encodeURIComponent(fallbackName.trim())}`;
  }
  return "https://api.dicebear.com/7.x/pixel-art/svg?seed=favcreator";
}
