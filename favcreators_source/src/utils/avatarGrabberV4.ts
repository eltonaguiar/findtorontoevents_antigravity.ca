/**
 * Avatar Grabber V4 - Failover Scraper
 *
 * A robust multi-strategy avatar fetching system with enhanced failover capabilities.
 * Strategies are tried in order of reliability and speed.
 *
 * Strategy Order:
 * 1. Platform-specific APIs (Twitch DecAPI, Kick API v2)
 * 2. Unavatar service (reliable fallback for major platforms)
 * 3. HTML scraping via multiple proxies
 * 4. Google Image search fallback
 * 5. Clearbit Logo API (for business/brand accounts)
 * 6. Gravatar (email-based, using username hash)
 * 7. UI Avatars (letter-based generated avatars)
 * 8. DiceBear (final pixel-art fallback)
 */

import type { SocialAccount } from "../types";

// Proxy services for CORS bypass
const PROXY_SERVICES = [
  (url: string) =>
    `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`,
  (url: string) => `https://corsproxy.io/?${encodeURIComponent(url)}`,
  (url: string) =>
    `https://api.codetabs.com/v1/proxy?url=${encodeURIComponent(url)}`,
  (url: string) => `https://thingproxy.freeboard.io/fetch/${url}`,
];

// Jina AI reader for advanced HTML extraction
const JINA_BASE = "https://r.jina.ai/";

// Platform priority for avatar sourcing (Kick first as their API is most reliable)
const PLATFORM_PRIORITY: SocialAccount["platform"][] = [
  "kick",
  "twitch",
  "youtube",
  "tiktok",
  "instagram",
  "other",
];

export interface V4ScraperResult {
  creatorName: string;
  avatarUrl: string | null;
  strategy: string;
  platform: string | null;
  timestamp: number;
  attempts: string[];
  error?: string;
}

// Browser-like headers to avoid being blocked
const BROWSER_HEADERS: Record<string, string> = {
  "User-Agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
  Accept: "application/json, text/html, */*",
  "Accept-Language": "en-US,en;q=0.9",
};

// Utility: Fetch with timeout
async function fetchWithTimeout(
  url: string,
  timeoutMs: number = 8000,
  headers: Record<string, string> = {},
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      signal: controller.signal,
      headers: { ...BROWSER_HEADERS, ...headers },
    });
    clearTimeout(timeoutId);
    return response;
  } catch (e) {
    clearTimeout(timeoutId);
    throw e;
  }
}

// Utility: Validate URL is an actual image
async function validateImageUrl(url: string): Promise<boolean> {
  if (!url || !url.startsWith("http")) return false;

  // Quick validation: check for known image extensions or CDN patterns
  const imagePatterns = [
    /\.(jpg|jpeg|png|gif|webp|avif|svg)/i,
    /pbs\.twimg\.com/i,
    /yt3\.googleusercontent\.com/i,
    /yt3\.ggpht\.com/i,
    /static-cdn\.jtvnw\.net/i,
    /files\.kick\.com/i,
    /p16-sign.*\.tiktokcdn\.com/i,
    /instagram.*\.fbcdn\.net/i,
    /unavatar\.io/i,
    /dicebear\.com/i,
    /ui-avatars\.com/i,
    /gravatar\.com/i,
  ];

  return imagePatterns.some((pattern) => pattern.test(url));
}

// Helper: Check if URL is a default/placeholder avatar (not a real custom avatar)
function isDefaultAvatar(url: string): boolean {
  const defaultPatterns = [
    /user-default-pictures/i, // Twitch default avatars
    /default.*profile/i, // Generic default profile
    /placeholder/i, // Placeholder images
    /no-profile/i, // No profile image
    /avatar-default/i, // Default avatar
    /default-avatar/i, // Default avatar
  ];

  return defaultPatterns.some((pattern) => pattern.test(url));
}

// Strategy 1: Twitch DecAPI
async function fetchTwitchAvatar(
  username: string,
  attempts: string[],
): Promise<string | null> {
  const strategy = `Twitch-DecAPI:${username}`;
  attempts.push(strategy);

  try {
    const apiUrl = `https://decapi.me/twitch/avatar/${username}`;
    const resp = await fetchWithTimeout(apiUrl, 5000);
    if (resp.ok) {
      const avatarUrl = (await resp.text()).trim();
      if (
        avatarUrl &&
        avatarUrl.startsWith("http") &&
        !avatarUrl.includes("error")
      ) {
        // Check if it's a default avatar - if so, return null to try other sources
        if (isDefaultAvatar(avatarUrl)) {
          console.log(`[V4] ${strategy} returned default avatar, skipping`);
          return null;
        }
        return avatarUrl;
      }
    }
  } catch (err) {
    console.warn(`[V4] ${strategy} failed:`, err);
  }
  return null;
}

// Strategy 2: Kick API v1 (more reliable than v2, doesn't require auth)
async function fetchKickAvatar(
  username: string,
  attempts: string[],
): Promise<string | null> {
  const strategy = `Kick-APIv1:${username}`;
  attempts.push(strategy);

  try {
    // Use API v1 which is more reliable and returns profile_pic in user object
    const apiUrl = `https://kick.com/api/v1/channels/${username}`;

    // Try direct fetch first (works in Node.js environment)
    try {
      const resp = await fetchWithTimeout(apiUrl, 8000);
      if (resp.ok) {
        const data = await resp.json();
        if (data?.user?.profile_pic) return data.user.profile_pic;
      }
    } catch {
      // Direct fetch failed, try proxies
    }

    // Fallback to proxies if direct fetch fails
    for (const proxyFn of PROXY_SERVICES) {
      try {
        const proxyUrl = proxyFn(apiUrl);
        const resp = await fetchWithTimeout(proxyUrl, 8000);
        if (resp.ok) {
          const text = await resp.text();
          // Check if response is valid JSON and not an error
          if (text.includes('"user"') && text.includes('"profile_pic"')) {
            const data = JSON.parse(text);
            if (data?.user?.profile_pic) return data.user.profile_pic;
          }
        }
      } catch {
        continue;
      }
    }
  } catch (err) {
    console.warn(`[V4] ${strategy} failed:`, err);
  }
  return null;
}

// Strategy 3: Unavatar Service (supports many platforms)
async function fetchUnavatar(
  platform: string,
  username: string,
  attempts: string[],
): Promise<string | null> {
  const strategy = `Unavatar:${platform}/${username}`;
  attempts.push(strategy);

  const supportedPlatforms: Record<string, string> = {
    twitch: "twitch",
    youtube: "youtube",
    tiktok: "tiktok",
    instagram: "instagram",
    twitter: "twitter",
    github: "github",
  };

  const unavatarPlatform = supportedPlatforms[platform];
  if (!unavatarPlatform) return null;

  try {
    const url = `https://unavatar.io/${unavatarPlatform}/${encodeURIComponent(username)}`;
    const resp = await fetchWithTimeout(url, 5000);
    if (resp.ok) {
      // Unavatar returns a redirect or the image directly
      // We return the URL itself as it will resolve properly
      return url;
    }
  } catch (err) {
    console.warn(`[V4] ${strategy} failed:`, err);
  }
  return null;
}

// Strategy 4: HTML Scraping with multiple proxies
async function scrapeAvatarFromHtml(
  url: string,
  platform: string,
  attempts: string[],
): Promise<string | null> {
  const strategy = `HTML-Scrape:${platform}:${url}`;
  attempts.push(strategy);

  const extractors: ((html: string) => string | null)[] = [
    // Kick-specific avatar
    (html) => {
      const match =
        html.match(
          /id\s*=\s*["']channel-avatar["'][^>]+src\s*=\s*["']([^"']+)["']/i,
        ) ||
        html.match(
          /src\s*=\s*["']([^"']+)["'][^>]+id\s*=\s*["']channel-avatar["']/i,
        ) ||
        html.match(/"profile_pic(?:ture)?"\s*:\s*"([^"]+)"/i);
      return match?.[1] || null;
    },
    // TikTok avatar patterns
    (html) => {
      const match =
        html.match(/"avatarLarger"\s*:\s*"([^"]+)"/i) ||
        html.match(/"avatarMedium"\s*:\s*"([^"]+)"/i) ||
        html.match(/"avatar"\s*:\s*"([^"]+)"/i);
      if (match?.[1]) {
        return match[1].replace(/\\u002F/g, "/").replace(/\\/g, "");
      }
      return null;
    },
    // YouTube avatar
    (html) => {
      const match =
        html.match(/yt3\.googleusercontent\.com\/[^"'<>\s]+/i) ||
        html.match(/yt3\.ggpht\.com\/[^"'<>\s]+/i);
      if (match?.[0]) {
        return match[0].startsWith("http") ? match[0] : `https://${match[0]}`;
      }
      return null;
    },
    // Instagram avatar
    (html) => {
      const match =
        html.match(/"profile_pic_url"\s*:\s*"([^"]+)"/i) ||
        html.match(/"profile_pic_url_hd"\s*:\s*"([^"]+)"/i);
      if (match?.[1]) {
        return match[1].replace(/\\u0026/g, "&").replace(/\\/g, "");
      }
      return null;
    },
    // Generic og:image
    (html) => {
      const match =
        html.match(
          /<meta\s+(?:property|name)=["']og:image["']\s+content=["']([^"']+)["']/i,
        ) ||
        html.match(
          /content=["']([^"']+)["']\s+(?:property|name)=["']og:image["']/i,
        );
      const ogImage = match?.[1];
      if (ogImage && ogImage.startsWith("http")) {
        // Skip generic platform logos
        if (
          ogImage.includes("logo") ||
          ogImage.includes("default") ||
          ogImage.includes("placeholder")
        ) {
          return null;
        }
        return ogImage.split("?")[0];
      }
      return null;
    },
    // image_src link
    (html) => {
      const match = html.match(
        /<link\s+rel=["']image_src["']\s+href=["']([^"']+)["']/i,
      );
      return match?.[1]?.startsWith("http") ? match[1] : null;
    },
  ];

  // Try Jina first (best for JS-heavy pages)
  try {
    const jinaUrl = `${JINA_BASE}${url}`;
    const resp = await fetchWithTimeout(jinaUrl, 10000);
    if (resp.ok) {
      const html = await resp.text();
      for (const extractor of extractors) {
        const avatar = extractor(html);
        if (avatar && (await validateImageUrl(avatar))) {
          return avatar;
        }
      }
    }
  } catch {
    // Continue to proxy fallbacks
  }

  // Try regular proxies
  for (const proxyFn of PROXY_SERVICES) {
    try {
      const proxyUrl = proxyFn(url);
      const resp = await fetchWithTimeout(proxyUrl, 8000);
      if (resp.ok) {
        const html = await resp.text();
        for (const extractor of extractors) {
          const avatar = extractor(html);
          if (avatar && (await validateImageUrl(avatar))) {
            return avatar;
          }
        }
      }
    } catch {
      continue;
    }
  }

  return null;
}

// Strategy 5: Google Image Search
async function googleImageSearch(
  query: string,
  attempts: string[],
): Promise<string | null> {
  const strategy = `Google-Image:${query}`;
  attempts.push(strategy);

  try {
    const searchUrl = `${JINA_BASE}http://www.google.com/search?q=${encodeURIComponent(query + " profile picture")}`;
    const resp = await fetchWithTimeout(searchUrl, 10000);
    if (resp.ok) {
      const text = await resp.text();

      // Look for image URLs in markdown format
      const imgRegex = /!\[.*?\]\((https:\/\/[^)]+)\)/g;
      let match;
      while ((match = imgRegex.exec(text)) !== null) {
        const url = match[1];
        if (
          url.includes("google.com") ||
          url.includes("gstatic.com") ||
          url.includes("favicon") ||
          url.includes("logo")
        )
          continue;
        if (/\.(jpg|jpeg|png|webp|avif)/i.test(url)) {
          return url;
        }
      }

      // Generic URL regex
      const genericRegex =
        /(https?:\/\/[^\s"'<>]+\.(?:jpg|jpeg|png|webp|avif))/gi;
      while ((match = genericRegex.exec(text)) !== null) {
        const url = match[0];
        if (
          !url.includes("google.com") &&
          !url.includes("gstatic.com") &&
          !url.includes("favicon")
        ) {
          return url;
        }
      }
    }
  } catch (err) {
    console.warn(`[V4] ${strategy} failed:`, err);
  }
  return null;
}

// Strategy 7: UI Avatars (letter-based)
function getUIAvatar(name: string, attempts: string[]): string {
  const strategy = `UI-Avatars:${name}`;
  attempts.push(strategy);

  const encodedName = encodeURIComponent(name);
  return `https://ui-avatars.com/api/?name=${encodedName}&size=256&background=random&color=fff&bold=true`;
}

// Strategy 8: DiceBear (final fallback)
function getDiceBearAvatar(seed: string, attempts: string[]): string {
  const strategy = `DiceBear:${seed}`;
  attempts.push(strategy);

  return `https://api.dicebear.com/7.x/pixel-art/svg?seed=${encodeURIComponent(seed)}`;
}

// Main V4 Scraper Function
export async function grabAvatarV4(
  accounts: SocialAccount[],
  creatorName: string,
): Promise<V4ScraperResult> {
  const attempts: string[] = [];
  const timestamp = Date.now();

  // Sort accounts by platform priority
  const sortedAccounts = [...accounts].sort((a, b) => {
    const aIdx = PLATFORM_PRIORITY.indexOf(a.platform);
    const bIdx = PLATFORM_PRIORITY.indexOf(b.platform);
    return (aIdx === -1 ? 999 : aIdx) - (bIdx === -1 ? 999 : bIdx);
  });

  // Strategy 1 & 2: Platform-specific APIs
  for (const account of sortedAccounts) {
    if (!account.username) continue;

    if (account.platform === "twitch") {
      const avatar = await fetchTwitchAvatar(account.username, attempts);
      if (avatar) {
        return {
          creatorName,
          avatarUrl: avatar,
          strategy: "Twitch-DecAPI",
          platform: "twitch",
          timestamp,
          attempts,
        };
      }
    }

    if (account.platform === "kick") {
      const avatar = await fetchKickAvatar(account.username, attempts);
      if (avatar) {
        return {
          creatorName,
          avatarUrl: avatar,
          strategy: "Kick-APIv1",
          platform: "kick",
          timestamp,
          attempts,
        };
      }
    }
  }

  // Strategy 3: Unavatar service
  for (const account of sortedAccounts) {
    if (!account.username) continue;
    const avatar = await fetchUnavatar(
      account.platform,
      account.username,
      attempts,
    );
    if (avatar) {
      return {
        creatorName,
        avatarUrl: avatar,
        strategy: "Unavatar",
        platform: account.platform,
        timestamp,
        attempts,
      };
    }
  }

  // Strategy 4: HTML Scraping
  for (const account of sortedAccounts) {
    if (!account.url) continue;
    const avatar = await scrapeAvatarFromHtml(
      account.url,
      account.platform,
      attempts,
    );
    if (avatar) {
      return {
        creatorName,
        avatarUrl: avatar,
        strategy: "HTML-Scrape",
        platform: account.platform,
        timestamp,
        attempts,
      };
    }
  }

  // Strategy 5: Google Image Search
  const googleAvatar = await googleImageSearch(creatorName, attempts);
  if (googleAvatar) {
    return {
      creatorName,
      avatarUrl: googleAvatar,
      strategy: "Google-Image",
      platform: null,
      timestamp,
      attempts,
    };
  }

  // Strategy 6: UI Avatars (better looking than DiceBear for real names)
  const uiAvatar = getUIAvatar(creatorName, attempts);

  getDiceBearAvatar(creatorName, attempts);

  // Return UI Avatars as it looks more professional
  return {
    creatorName,
    avatarUrl: uiAvatar,
    strategy: "UI-Avatars",
    platform: null,
    timestamp,
    attempts,
    error: "No real avatar found - using generated fallback",
  };
}

// Batch scraper for multiple creators
export async function scrapeAllCreatorsV4(
  creators: Array<{ name: string; accounts: SocialAccount[] }>,
): Promise<V4ScraperResult[]> {
  const results: V4ScraperResult[] = [];

  for (const creator of creators) {
    console.log(`[V4] Scraping avatar for: ${creator.name}`);
    const result = await grabAvatarV4(creator.accounts, creator.name);
    results.push(result);

    // Small delay between creators to avoid rate limiting
    await new Promise((resolve) => setTimeout(resolve, 500));
  }

  return results;
}

// Export for testing
export {
  fetchTwitchAvatar,
  fetchKickAvatar,
  fetchUnavatar,
  scrapeAvatarFromHtml,
};
