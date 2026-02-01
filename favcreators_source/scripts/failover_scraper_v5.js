import fs from "fs";
import axios from "axios";

const PROXIES = [
  (url) => `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`,
  (url) => `https://r.jina.ai/${url}`,
  (url) => `https://corsproxy.io/?${encodeURIComponent(url)}`,
  (url) => `https://api.codetabs.com/v1/proxy?url=${encodeURIComponent(url)}`,
  (url) => `https://thingproxy.freeboard.io/fetch/${url}`,
];

const PLATFORM_PRIORITY = ["instagram", "youtube", "tiktok", "twitch", "kick", "other"];

const CREATORS = [
  {
    name: "WTFPreston",
    accounts: [
      { platform: "tiktok", username: "wtfprestonlive", url: "https://www.tiktok.com/@wtfprestonlive" },
      { platform: "youtube", username: "wtfprestonlive", url: "https://www.youtube.com/@wtfprestonlive" },
      { platform: "instagram", username: "wtfprestonlive", url: "https://www.instagram.com/wtfprestonlive" },
    ],
  },
  {
    name: "Clavicular",
    accounts: [
      { platform: "kick", username: "clavicular", url: "https://kick.com/clavicular" },
      { platform: "twitch", username: "clavicular", url: "https://www.twitch.tv/clavicular" },
    ],
  },
  {
    name: "Zarthestar",
    accounts: [
      { platform: "tiktok", username: "zarthestarcomedy", url: "https://www.tiktok.com/@zarthestarcomedy" },
      { platform: "instagram", username: "zar.the.star", url: "https://www.instagram.com/zar.the.star/?hl=en" },
      { platform: "twitch", username: "zarthestar", url: "https://twitch.tv/zarthestar" },
      { platform: "youtube", username: "zarthestarcomedy", url: "https://www.youtube.com/@zarthestarcomedy" },
      { platform: "other", username: "linktr.ee/zarthestar", url: "https://linktr.ee/zarthestar" },
    ],
  },
  {
    name: "Adin Ross",
    accounts: [
      { platform: "kick", username: "adinross", url: "https://kick.com/adinross" },
      { platform: "youtube", username: "adinross", url: "https://youtube.com/@adinross" },
      { platform: "other", username: "linktr.ee/adinrosss", url: "https://linktr.ee/adinrosss" },
    ],
  },
  {
    name: "Starfireara",
    accounts: [
      { platform: "tiktok", username: "starfireara", url: "https://www.tiktok.com/@starfireara" },
      { platform: "other", username: "linktr.ee/starfiire", url: "https://linktr.ee/starfiire" },
    ],
  },
];

const isImageUrl = (candidate) => {
  if (!candidate || typeof candidate !== "string") return false;
  const lower = candidate.toLowerCase();
  if (!lower.startsWith("http")) return false;
  if (lower.includes("google.com")) return false;
  if (lower.includes("gstatic.com")) return false;
  if (lower.includes("favicon") || lower.includes("logo") || lower.includes("sprite") || lower.includes("pixel")) return false;
  return /\.(jpg|jpeg|png|webp|avif)(?:\?|#|$)/i.test(candidate) ||
    lower.includes("twimg.com/profile_images") ||
    lower.includes("yt3.ggpht.com");
};

const buildUnavatarCandidate = (account) => {
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

const extractAvatarFromHtml = (html) => {
  if (!html) return null;
  const kickMatch = html.match(/id\s*=\s*["']channel-avatar["'][^>]+src\s*=\s*["']([^"']+)["']/i) ||
    html.match(/src\s*=\s*["']([^"']+)["'][^>]+id\s*=\s*["']channel-avatar["']/i);
  if (kickMatch && kickMatch[1]) return kickMatch[1];

  const ogMatch = html.match(/<meta\s+(?:property|name)=["']og:image["']\s+content=["']([^"']+)["']/i);
  if (ogMatch && ogMatch[1]) {
    const value = ogMatch[1].split("?")[0];
    if (isImageUrl(value)) return value;
  }

  const linkMatch = html.match(/<link\s+rel=["']image_src["']\s+href=["']([^"']+)["']/i);
  if (linkMatch && linkMatch[1] && isImageUrl(linkMatch[1])) return linkMatch[1];

  return null;
};

async function fetchViaProxy(targetUrl, timeoutMs = 10000) {
  for (const proxyFn of PROXIES) {
    const proxyUrl = proxyFn(targetUrl);
    try {
      const response = await axios.get(proxyUrl, {
        timeout: timeoutMs,
        responseType: "text",
        maxRedirects: 5,
      });
      if (response.status === 200 && response.data) {
        const text = typeof response.data === "string" ? response.data : JSON.stringify(response.data);
        if (text.length > 10) return text;
      }
    } catch (error) {
      // ignore and try next proxy
    }
  }
  return null;
}

async function fetchAvatarFromUrl(url, platform, username) {
  if (!url) return null;

  if (platform === "twitch" && username) {
    try {
      const resp = await axios.get(`https://decapi.me/twitch/avatar/${encodeURIComponent(username)}`, {
        timeout: 8000,
        responseType: "text",
      });
      const avatar = resp.data?.trim();
      if (avatar && avatar.startsWith("http")) {
        return { url: avatar, method: "Twitch DecAPI" };
      }
    } catch (error) {
      console.warn("Twitch API lookup failed", error.message);
    }
  }

  if (platform === "kick" && username) {
    try {
      const jsonText = await fetchViaProxy(`https://kick.com/api/v2/channels/${encodeURIComponent(username)}`);
      if (jsonText) {
        const data = JSON.parse(jsonText);
        const avatar = data?.user?.profile_picture || data?.user?.profile_pic;
        if (avatar) {
          return { url: avatar, method: "Kick API (proxy)" };
        }
      }
    } catch (error) {
      console.warn("Kick API lookup failed", error.message);
    }
  }

  if ((platform === "tiktok" || platform === "instagram") && url) {
    try {
      const jinaUrl = `https://r.jina.ai/${url}`;
      const resp = await axios.get(jinaUrl, { timeout: 12000, responseType: "text" });
      if (resp.data) {
        const avatar = extractAvatarFromHtml(resp.data);
        if (avatar) {
          return { url: avatar, method: `${platform.charAt(0).toUpperCase() + platform.slice(1)} OG via Jina` };
        }
      }
    } catch (error) {
      console.warn(`Jina HTML scrape failed for ${platform}`, error.message);
    }
  }

  try {
    const html = await fetchViaProxy(url);
    if (html) {
      const avatar = extractAvatarFromHtml(html);
      if (avatar) {
        const label = platform ? `${platform.toUpperCase()} OG scrape` : "OG scrape";
        return { url: avatar, method: label };
      }
    }
  } catch (error) {
    console.warn("Generic OG scrape failed", error.message);
  }

  return null;
}

async function googleImageFailover(name) {
  if (!name) return null;
  const queryTerms = [
    `${name} profile picture`,
    `${name} headshot`,
    `${name} avatar`,
    `${name} "profile photo"`,
  ];

  for (const term of queryTerms) {
    const searchUrl = `https://r.jina.ai/http://www.google.com/search?tbm=isch&q=${encodeURIComponent(term)}&num=5&gl=us&hl=en`;
    try {
      const html = await fetchViaProxy(searchUrl, 12000);
      if (!html) continue;
      let match;
      const markdownMatch = /!\[.*?\]\((https:\/\/[^)]+)\)/g;
      while ((match = markdownMatch.exec(html)) !== null) {
        if (isImageUrl(match[1])) return match[1];
      }
      const genericMatch = /(https?:\/\/[^\s"'<>]+\.(?:jpg|jpeg|png|webp|avif))(?:\?|#|$)/gi;
      while ((match = genericMatch.exec(html)) !== null) {
        if (isImageUrl(match[1])) return match[1];
      }
    } catch (error) {
      console.warn("Google image proxy search failed", error.message);
    }
  }

  return null;
}

async function grabAvatarFromAccounts(accounts, fallbackName) {
  for (const platform of PLATFORM_PRIORITY) {
    const matches = accounts.filter((account) => account.platform === platform && account.url);
    for (const account of matches) {
      const result = await fetchAvatarFromUrl(account.url, account.platform, account.username);
      if (result) return result;
    }
  }

  for (const platform of PLATFORM_PRIORITY) {
    const matches = accounts.filter((account) => account.platform === platform);
    for (const account of matches) {
      const candidate = buildUnavatarCandidate(account);
      if (candidate) return { url: candidate, method: `Unavatar (${account.platform || "link"})` };
    }
  }

  if (fallbackName) {
    const googleAvatar = await googleImageFailover(fallbackName);
    if (googleAvatar) return { url: googleAvatar, method: "Google image fallback" };
  }

  const dicebear = `https://api.dicebear.com/7.x/pixel-art/svg?seed=${encodeURIComponent(fallbackName || "favcreator")}`;
  return { url: dicebear, method: "Dicebear fallback" };
}

(async () => {
  console.log("=== FAILOVER V5 AVATAR SCRAPER ===");
  const results = [];
  for (const creator of CREATORS) {
    process.stdout.write(`Processing ${creator.name}... `);
    const { url, method } = await grabAvatarFromAccounts(creator.accounts, creator.name);
    results.push({ name: creator.name, url, method });
    console.log(`done (${method})`);
    console.log(`  → ${url}`);
  }

  const outPath = "scripts/failover_v5_results.json";
  fs.writeFileSync(outPath, JSON.stringify(results, null, 2));
  console.log(`Saved ${results.length} rows to ${outPath}`);
})();
