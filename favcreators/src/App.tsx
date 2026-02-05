import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import "./App.css";
import type { Creator, SocialAccount, Platform } from "./types";
import CreatorCard from "./components/CreatorCard";
import CreatorForm from "./components/CreatorForm";
import EditCreatorModal from "./components/EditCreatorModal";
import MyLinkLists from "./components/MyLinkLists";
import LiveSummary from "./components/LiveSummary";
import AdSense from "./components/AdSense";
import type { LiveCreator } from "./types";
import { googleSearchYoutubeChannel } from "./utils/googleSearch";
import {
  fetchMe,
  getAuthBase,
  resolveAuthBase,
  loginWithPassword,
  logout as logoutAuth,
  registerWithPassword,
  
  type AuthUser,
} from "./utils/auth";
import { grabAvatarV4 } from "./utils/avatarGrabberV4";
import { grabAvatarFromAccounts } from "./utils/avatarGrabber";
import { extractYoutubeUsername } from "./utils/youtube";
import {
  ensureAvatarForCreators,
  ensureAvatarUrl,
  buildAvatarCandidates,
  buildFallbackAvatar,
} from "./utils/avatar";
import {
  fetchWithTimeout as fetchWithTimeoutInternal,
} from "./utils/proxyFetch";
import { fcApiFetch, getApiLog, subscribeToApiLog, clearApiLog, type ApiLogEntry } from "./utils/apiLog";
import { getCachedLiveStatus, updateStreamerLastSeen } from "./utils/streamerLastSeen";

// Guest mode detection
const isGuestMode =
  typeof window !== "undefined" &&
  window.location &&
  window.location.hash.includes("/guest");

const PUBLIC_CREATORS_STORAGE_KEY = "fav_creators_public";
const AUTH_USER_STORAGE_KEY = "fav_creators_auth_user";

// Using centralized proxy fetch from utils/proxyFetch.ts
const fetchWithTimeout = fetchWithTimeoutInternal;

const mergeCreatorsById = (
  existing: Creator[],
  incoming: Creator[],
): Creator[] => {
  const existingIds = new Set(existing.map((creator) => creator.id));
  const merged = [...existing];
  incoming.forEach((creator) => {
    if (!existingIds.has(creator.id)) {
      merged.push(creator);
      existingIds.add(creator.id);
    }
  });
  return merged;
};

// Helper to get best avatar using multiple strategies (V4, V1, V10 Failovers)
const getBestAvatar = async (
  name: string,
  accounts: SocialAccount[],
): Promise<string | null> => {
  const normalized = name.toLowerCase().trim();
  const baseUrl = import.meta.env.BASE_URL || "/";

  // 1. Hardcoded Local Caches (Absolute Top Priority & Offline-Safe)
  if (normalized === "clavicular") {
    return `${baseUrl}avatars/clavicular.webp`;
  }
  if (normalized === "zarthestar" || normalized === "zarthestarcomedy") {
    return `${baseUrl}avatars/zarthestar.jpg`;
  }
  if (normalized === "starfireara") {
    return `${baseUrl}avatars/starfireara.jpg`;
  }

  try {
    // 2. Strategy 1: V4 Scraper (Includes 8 internal sub-strategies: API, Unavatar, HTML Scrape, etc.)
    const v4Result = await grabAvatarV4(accounts, name);
    if (v4Result && v4Result.avatarUrl && !v4Result.avatarUrl.includes("dicebear.com") && !v4Result.avatarUrl.includes("ui-avatars.com")) {
      return v4Result.avatarUrl;
    }

    // 3. Strategy 2: Original Scraper (Specific platform fallbacks)
    const v1Result = await grabAvatarFromAccounts(accounts, name);
    if (v1Result && !v1Result.includes("dicebear.com")) {
      return v1Result;
    }

    // 4. Strategy 3: Direct Unavatar Fallback (Safe check)
    if (accounts.length > 0) {
      const firstWithUser = accounts.find((a) => a.username);
      if (firstWithUser) {
        return `https://unavatar.io/${firstWithUser.platform}/${firstWithUser.username}`;
      }
    }
  } catch (err) {
    console.warn("Avatar strategies failed", err);
  }

  return null;
};

const checkLiveStatus = async (
  platform: string,
  username: string,
  creatorId?: string,
): Promise<{ isLive: boolean; accountStatus: string; hasStory?: boolean; storyCount?: number; storyPostedAt?: number } | null> => {
  // TLC.php supports: tiktok, twitch, kick, youtube
  const tlcSupportedPlatforms = ["tiktok", "twitch", "kick", "youtube"];

  // First, check cached live status for faster response (if creatorId provided)
  if (creatorId && tlcSupportedPlatforms.includes(platform)) {
    try {
      const cached = await getCachedLiveStatus(creatorId, platform, 10); // 10 min cache
      if (cached) {
        console.log(`[CACHE] ${username}: ${cached.is_live ? 'LIVE' : 'offline'} (cached ${cached.last_checked})`);
        return {
          isLive: cached.is_live,
          accountStatus: cached.is_live ? 'live' : 'offline',
        };
      }
    } catch (e) {
      // Ignore cache errors, fall through to live check
      console.warn(`[CACHE] Failed to get cached status for ${username}:`, e);
    }
  }

  if (tlcSupportedPlatforms.includes(platform)) {
    // Use the enhanced multi-platform TLC.php endpoint
    // Supports TikTok, Twitch, Kick, YouTube with platform-specific detection methods
    // See TLC_IMPLEMENTATION.md for full documentation
    try {
      const tlcUrl = `https://findtorontoevents.ca/fc/TLC.php?user=${username}&platform=${platform}`;
      const response = await fetchWithTimeout(tlcUrl, 20000); // 20s timeout for slower platforms like YouTube

      if (response.ok) {
        const data = await response.json();
        if (data && typeof data.live === 'boolean') {
          console.log(`[TLC ${platform}] ${username}: ${data.live ? 'LIVE' : 'offline'} (method: ${data.method || 'unknown'}, status: ${data.account_status || 'unknown'})`);

          const result: any = {
            isLive: data.live,
            accountStatus: data.account_status || 'unknown'
          };

          // Include story data for TikTok
          if (platform === 'tiktok' && data.has_story) {
            result.hasStory = true;
            result.storyCount = data.story_count || 0;
            result.storyPostedAt = data.story_posted_at || 0;
          }

          return result;
        }
      }
    } catch (e) {
      console.warn(`[TLC ${platform}] Failed to check ${username}:`, e);
    }

    // Fallback for TikTok only: Try static status file (Server-side generated status)
    if (platform === "tiktok") {
      const baseUrl = import.meta.env.BASE_URL || "/";
      try {
        const staticFile = await fetchWithTimeout(`${baseUrl}tiktok_live_${username}_playwright.json`, 2000);
        if (staticFile.ok) {
          const data = await staticFile.json();
          if (data && typeof data.is_live === 'boolean') {
            console.log(`[TLC FALLBACK] ${username}: ${data.is_live ? 'LIVE' : 'offline'} (static file)`);
            return {
              isLive: data.is_live,
              accountStatus: 'unknown' // Fallback doesn't provide status
            };
          }
        }
      } catch {
        // Ignore fallback failure
      }
    }

    return null;
  }

  // For unsupported platforms (Instagram, etc.), return null
  return null;
};

const INITIAL_DATA: Creator[] = ensureAvatarForCreators([
  {
    id: "wtfpreston-1",
    name: "WTFPreston",
    bio: "Comedy musician and streamer dropping weird, funny songs and live bits.",
    avatarUrl: "",
    isFavorite: false,
    addedAt: Date.now() - 4000,
    lastChecked: Date.now() - 3000,
    category: "Other",
    reason: "He makes funny songs.",
    tags: ["COMEDY", "MUSIC", "LOVE THEIR CONTENT"],
    accounts: [
      {
        id: "wtfpreston-tiktok",
        platform: "tiktok",
        username: "wtfprestonlive",
        url: "https://www.tiktok.com/@wtfprestonlive",
        followers: "330K",
        lastChecked: Date.now() - 3000,
      },
      {
        id: "wtfpreston-youtube",
        platform: "youtube",
        username: "wtfprestonlive",
        url: "https://www.youtube.com/@wtfprestonlive",
        lastChecked: Date.now() - 3000,
      },
      {
        id: "wtfpreston-instagram",
        platform: "instagram",
        username: "wtfprestonlive",
        url: "https://www.instagram.com/wtfprestonlive",
        lastChecked: Date.now() - 3000,
      },
      {
        id: "wtfpreston-spotify",
        platform: "spotify",
        username: "wtfprestonlive",
        url: "https://open.spotify.com/artist/5Ho2sjbNmEkALWz8hbNBUH",
        lastChecked: Date.now() - 3000,
      },
      {
        id: "wtfpreston-applemusic",
        platform: "other",
        username: "WTFPreston",
        url: "https://music.apple.com/us/artist/wtfpreston/1851052017",
        lastChecked: Date.now() - 3000,
      },
    ],
  },
  {
    id: "clavicular-1",
    name: "Clavicular",
    bio: "Talented streamer and creator. Requested by the community.",
    avatarUrl: "",
    isFavorite: false,
    addedAt: Date.now() - 1500,
    lastChecked: Date.now() - 1500,
    category: "Other",
    accounts: [
      {
        id: "clavicular-kick",
        platform: "kick",
        username: "clavicular",
        url: "https://kick.com/clavicular",
        lastChecked: Date.now() - 1500,
      },
      {
        id: "clavicular-twitch",
        platform: "twitch",
        username: "clavicular",
        url: "https://www.twitch.tv/clavicular",
        lastChecked: Date.now() - 1500,
      },
      {
        id: "clavicular-linktree",
        platform: "other",
        username: "linktr.ee/clavicular0",
        url: "https://linktr.ee/clavicular0",
        lastChecked: Date.now() - 1500,
      },
    ],
  },
  {
    id: "thebenjishow-1",
    name: "The Benji Show",
    bio: "Hilarious skits and comedy bits.",
    avatarUrl: "",
    isFavorite: false,
    isPinned: false,
    addedAt: Date.now() - 1400,
    lastChecked: Date.now() - 1400,
    category: "Hilarious Skits",
    tags: ["COMEDY", "SKITS"],
    accounts: [
      {
        id: "thebenjishow-tiktok",
        platform: "tiktok",
        username: "thebenjishow",
        url: "https://www.tiktok.com/@thebenjishow?lang=en",
        lastChecked: Date.now() - 1400,
      },
    ],
  },
  {
    id: "zarthestar-1",
    name: "Zarthestar",
    bio: "Cosmic content creator and explorer of the digital universe. TikTok comedy & lifestyle.",
    avatarUrl: "",
    isFavorite: false,
    addedAt: Date.now() - 2000,
    lastChecked: Date.now() - 1500,
    category: "Other",
    accounts: [
      {
        id: "zarthestar-tiktok",
        platform: "tiktok",
        username: "zarthestarcomedy",
        url: "https://www.tiktok.com/@zarthestarcomedy",
        followers: "125K",
        lastChecked: Date.now() - 1500,
      },
      {
        id: "zarthestar-instagram",
        platform: "instagram",
        username: "zar.the.star",
        url: "https://www.instagram.com/zar.the.star/?hl=en",
        followers: "45K",
        lastChecked: Date.now() - 1500,
      },
      {
        id: "zarthestar-twitch",
        platform: "twitch",
        username: "zarthestar",
        url: "https://twitch.tv/zarthestar",
        followers: "2.3K",
        lastChecked: Date.now() - 1500,
      },
      {
        id: "zarthestar-youtube",
        platform: "youtube",
        username: "zarthestarcomedy",
        url: "https://www.youtube.com/@zarthestarcomedy",
        followers: "800",
        lastChecked: Date.now() - 1500,
      },
      {
        id: "zarthestar-linktree",
        platform: "other",
        username: "linktr.ee/zarthestar",
        url: "https://linktr.ee/zarthestar",
        lastChecked: Date.now() - 1500,
      },
      {
        id: "zarthestar-msha",
        platform: "other",
        username: "msha.ke/zarthestar",
        url: "https://msha.ke/zarthestar",
        lastChecked: Date.now() - 1500,
      },
    ],
  },
  {
    id: "3",
    name: "Adin Ross",
    bio: "Kick's No. 1 Creator | Live every day.",
    avatarUrl: "", // TODO: Set AdinRoss avatar URL here
    isFavorite: true,
    isPinned: true,
    addedAt: Date.now() - 50000,
    lastChecked: Date.now() - 45000,
    category: "Favorites",
    accounts: [
      {
        id: "3a",
        platform: "kick",
        username: "adinross",
        url: "https://kick.com/adinross",
        followers: "1.9M",
        lastChecked: Date.now() - 47000,
      },
      {
        id: "3b",
        platform: "youtube",
        username: "adinross",
        url: "https://youtube.com/@adinross",
        followers: "4.6M",
        lastChecked: Date.now() - 47000,
      },
      {
        id: "adinross-linktree",
        platform: "other",
        username: "linktr.ee/adinrosss",
        url: "https://linktr.ee/adinrosss",
        lastChecked: Date.now() - 47000,
      },
    ],
  },
  {
    id: "6",
    name: "Starfireara",
    bio: "Content creator and visionary.",
    avatarUrl: "https://p16-sign-va.tiktokcdn.com/tos-maliva-avt-0068/7b5c9a5a4df3ab57b62df377dd526aa1~tplv-tiktokx-cropcenter:1080:1080.jpeg?dr=14579&refresh_token=febc5422&x-expires=1770044400&x-signature=nKafWAOhYHb6mzLmOQtwMiOccJE%3D&t=4d5b0474&ps=13740610&shp=a5d48078&shcp=81f88b70&idc=my",
    isFavorite: true,
    isPinned: true,
    addedAt: Date.now() - 5000,
    reason: "Motivational speaker",
    lastChecked: Date.now() - 4000,
    category: "Favorites",
    accounts: [
      {
        id: "6b",
        platform: "tiktok",
        username: "starfireara",
        url: "https://www.tiktok.com/@starfireara",
        followers: "247.3K",
        lastChecked: Date.now() - 4000,
      },
      {
        id: "starfireara-linktree",
        platform: "other",
        username: "linktr.ee/starfiire",
        url: "https://linktr.ee/starfiire",
        lastChecked: Date.now() - 4000,
      },
    ],
  },
  {
    id: "gabbyvn3-1",
    name: "Gabbyvn3",
    bio: "TikTok creator and streamer.",
    avatarUrl: "",
    isFavorite: true,
    isPinned: false,
    addedAt: Date.now() - 2000,
    lastChecked: Date.now() - 2000,
    category: "Streamers",
    reason: "Testing live status detection",
    tags: ["TIKTOK", "STREAMER"],
    accounts: [
      {
        id: "gabbyvn3-tiktok",
        platform: "tiktok",
        username: "gabbyvn3",
        url: "https://www.tiktok.com/@gabbyvn3",
        lastChecked: Date.now() - 2000,
      },
      {
        id: "gabbyvn3-kick",
        platform: "kick",
        username: "gabbyvn3",
        url: "https://kick.com/gabbyvn3",
        lastChecked: Date.now() - 2000,
      },
    ],
  },
  {
    id: "chavcriss-1",
    name: "Chavcriss",
    bio: "Fitness and comedy influencer. Inspiring and entertaining with every post!",
    avatarUrl: "",
    isFavorite: true,
    isPinned: false,
    addedAt: Date.now() - 1000,
    lastChecked: Date.now() - 1000,
    category: "Fitness",
    reason: "Fitness & comedy inspiration.",
    tags: ["FITNESS", "COMEDY", "INSPIRATION"],
    accounts: [
      {
        id: "chavcriss-tiktok",
        platform: "tiktok",
        username: "chavcriss",
        url: "https://www.tiktok.com/@chavcriss",
        lastChecked: Date.now() - 1000,
      },
      {
        id: "chavcriss-instagram",
        platform: "instagram",
        username: "chavcriss",
        url: "https://www.instagram.com/chavcriss",
        lastChecked: Date.now() - 1000,
      },
      {
        id: "chavcriss-youtube",
        platform: "youtube",
        username: "chavcriss",
        url: "https://www.youtube.com/@chavcriss",
        lastChecked: Date.now() - 1000,
      }
    ],
  },

  {
    id: "jubalfresh-1",
    name: "Jubal Fresh",
    bio: "Prank phone calls and radio bits.",
    avatarUrl: "",
    isFavorite: false,
    isPinned: false,
    addedAt: Date.now() - 1000,
    lastChecked: Date.now() - 1000,
    category: "Prank Phone Calls",
    tags: ["PRANK CALLS", "COMEDY"],
    accounts: [
      {
        id: "jubalfresh-youtube",
        platform: "youtube",
        username: "jubalfresh",
        url: "https://www.youtube.com/@jubalfresh",
        lastChecked: Date.now() - 1000,
      },
      {
        id: "jubalfresh-tiktok",
        platform: "tiktok",
        username: "jubalfresh",
        url: "https://www.tiktok.com/@jubalfresh",
        lastChecked: Date.now() - 1000,
      },
      {
        id: "jubalfresh-instagram",
        platform: "instagram",
        username: "jubalfresh",
        url: "https://www.instagram.com/jubalfresh",
        lastChecked: Date.now() - 1000,
      },
    ],
  },

  {
    id: "brooke-and-jeffrey-1",
    name: "Brooke & Jeffrey",
    bio: "Phone Tap archives and featured prank call segments.",
    avatarUrl: "",
    isFavorite: false,
    isPinned: false,
    addedAt: Date.now() - 1000,
    lastChecked: Date.now() - 1000,
    category: "Other Content",
    tags: ["PRANK CALLS", "RADIO"],
    accounts: [
      {
        id: "brooke-and-jeffrey-phone-tap",
        platform: "other",
        username: "brookeandjeffrey.com Phone Tap",
        url: "https://www.brookeandjeffrey.com/featured/phone-tap-bjitm/",
        lastChecked: Date.now() - 1000,
      },
    ],
  },
  {
    id: "clip2prankmain-1",
    name: "Clip2prankmain",
    bio: "TikTok creator.",
    avatarUrl: "",
    isFavorite: false,
    isPinned: false,
    addedAt: Date.now() - 1000,
    lastChecked: Date.now() - 1000,
    category: "Entertainment",
    tags: ["LOVE THEIR CONTENT"],
    accounts: [
      {
        id: "clip2prankmain-tiktok",
        platform: "tiktok",
        username: "clip2prankmain",
        url: "https://www.tiktok.com/@clip2prankmain",
        lastChecked: Date.now() - 1000,
      },
    ],
  },
]);

const DATA_VERSION = "14.0"; // Increment this to force reset localStorage
const QUICK_ADD_DEFAULT_TAGS = ["LOVE THEIR CONTENT"];

/** Parse a pasted social URL (e.g. https://www.tiktok.com/@sunnystoktik) into platform + username + url. */
function parseSocialUrl(input: string): { platform: Platform; username: string; url: string } | null {
  const trimmed = input.trim();
  if (!trimmed) return null;
  let url: URL;
  try {
    url = new URL(trimmed.startsWith("http") ? trimmed : "https://" + trimmed);
  } catch {
    return null;
  }
  const host = url.hostname.toLowerCase().replace(/^www\./, "");
  const path = url.pathname.replace(/\/$/, "").split("?")[0];

  if (host === "tiktok.com" && path.startsWith("/@")) {
    const username = path.slice(2).split("/")[0] || "";
    if (!username) return null;
    return { platform: "tiktok", username, url: `https://www.tiktok.com/@${username}` };
  }
  if ((host === "youtube.com" || host === "youtu.be")) {
    let username = "";
    if (path.startsWith("/@")) username = path.slice(2).split("/")[0] || "";
    else if (path.startsWith("/channel/")) username = path.split("/")[2] || "";
    else if (path.startsWith("/c/")) username = path.slice(3).split("/")[0] || "";
    if (!username) return null;
    const canonical = host === "youtu.be" ? `https://youtube.com/@${username}` : url.toString();
    return { platform: "youtube", username, url: canonical };
  }
  if (host === "instagram.com" && path.length > 1) {
    const username = path.slice(1).split("/")[0] || "";
    if (!username) return null;
    return { platform: "instagram", username, url: `https://instagram.com/${username}` };
  }
  if (host === "kick.com" && path.length > 1) {
    const username = path.slice(1).split("/")[0] || "";
    if (!username) return null;
    return { platform: "kick", username, url: `https://kick.com/${username}` };
  }
  if (host === "twitch.tv" && path.length > 1) {
    const username = path.slice(1).split("/")[0] || "";
    if (!username) return null;
    return { platform: "twitch", username, url: `https://twitch.tv/${username}` };
  }
  return null;
}

const DEFAULT_CATEGORIES = [
  "Favorites",
  "Other",
  "Hilarious Skits",
  "Prank Phone Calls",
  "Other Content",
  "Education",
  "Entertainment",
  "Gaming",
  "Music",
  "Tech",
  "Lifestyle",
];

function App() {
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  /** True after first auth check (fetchMe or cached). Used so we don't fetch guest notes (user_id=0) when user is actually logged in. */
  const [authChecked, setAuthChecked] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [registerName, setRegisterName] = useState("");
  const [registerEmail, setRegisterEmail] = useState("");
  const [registerPassword, setRegisterPassword] = useState("");
  const [authLoading, setAuthLoading] = useState(false);
  const [showLoginForm, setShowLoginForm] = useState(false);
  /** Debug: backend/DB connectivity so users know if notes & list persist */
  const [backendStatus, setBackendStatus] = useState<"checking" | "connected" | "disconnected">("checking");
  const [backendStatusDetail, setBackendStatusDetail] = useState<{
    read_ok?: boolean;
    starfireara_note?: string | null;
    error?: string;
    statusUrl?: string;
  } | null>(null);

  // Auto-redirect to Guest Mode if not logged in and not in guest mode
  useEffect(() => {
    // Redirect to guest mode if not authenticated and not already on guest/lastdetectedcontent/updates routes
    if (!window.location.hash.includes("/guest") && !window.location.hash.includes("#/") && !window.location.hash.includes("/updates") && !window.location.hash.includes("/lastdetectedcontent") && !localStorage.getItem(AUTH_USER_STORAGE_KEY)) {
      console.log("Redirecting to guest mode");
      window.location.hash = "#/guest";
      window.location.reload();
    }
  }, []);

  const [apiLogEntries, setApiLogEntries] = useState<ApiLogEntry[]>([]);
  const [apiLogOpen, setApiLogOpen] = useState(false);

  const [creators, setCreators] = useState<Creator[]>(() => {
    try {
      if (isGuestMode) return INITIAL_DATA;
      const savedVersion = localStorage.getItem("fav_creators_version");
      // Reset data if version mismatch (categories changed)
      if (savedVersion !== DATA_VERSION) {
        localStorage.setItem("fav_creators_version", DATA_VERSION);
        localStorage.removeItem("fav_creators");
        return INITIAL_DATA;
      }
      const saved = localStorage.getItem("fav_creators");
      return saved ? ensureAvatarForCreators(JSON.parse(saved)) : INITIAL_DATA;
    } catch (e) {
      console.error("Failed to parse creators from localStorage", e);
      return INITIAL_DATA;
    }
  });

  const hasLoadedMineRef = useRef(false);
  /** When true, the save effect must not POST to save_creators — we just loaded from API and must not overwrite DB (e.g. with cached or stale list that misses Brunitarte). */
  const skipSaveAfterLoadRef = useRef(false);
  /** Current auth user (ref so async loadFromServer can check "did user log in while we were fetching?" and avoid overwriting their list). */
  const authUserRef = useRef<AuthUser | null>(null);
  useEffect(() => {
    authUserRef.current = authUser;
  }, [authUser]);

  useEffect(() => {
    const refresh = () => setApiLogEntries(getApiLog());
    refresh();
    return subscribeToApiLog(refresh);
  }, []);

  // Handle Social Login (Google) Callback
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const userStr = params.get("login_user");
    if (userStr) {
      try {
        const user = JSON.parse(decodeURIComponent(userStr));
        setAuthUser(user);
        localStorage.setItem(AUTH_USER_STORAGE_KEY, JSON.stringify(user));
        // Clear URL
        window.history.replaceState({}, document.title, window.location.pathname);
      } catch (e) {
        console.error("Failed to parse login user", e);
      }
    }

    // Also check for PHP Session (Google Auth) when auth base is configured
    const base = getAuthBase();
    if (base) {
      fcApiFetch(`${base}/get_me.php`, { credentials: "include" })
        .then(res => res.text())
        .then((text) => {
          try {
            const data = text ? JSON.parse(text) : {};
            if (typeof data === "object" && data !== null && data.user) {
              setAuthUser(data.user);
              localStorage.setItem(AUTH_USER_STORAGE_KEY, JSON.stringify(data.user));
              window.history.replaceState({}, document.title, window.location.pathname);
            }
          } catch {
            // Non-JSON (e.g. raw PHP when server doesn't run PHP) — ignore
          }
        })
        .catch((e) => console.warn("Session check failed", e));
    }

  }, []);

  const [isFormOpen, setIsFormOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [viewMode, setViewMode] = useState<"list" | "dropdown" | "table">("list");
  const [quickAddValue, setQuickAddValue] = useState("");
  const [autoExpandSecondaryNotes, setAutoExpandSecondaryNotes] = useState<boolean>(() => {
    try {
      return localStorage.getItem("fav_creators_auto_expand_notes") === "true";
    } catch {
      return false;
    }
  });
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkApplyCategory, setBulkApplyCategory] = useState("");
  const [editingCreator, setEditingCreator] = useState<Creator | null>(null);

  // Admin: creators followed by all users (for impact visibility)
  type FollowedCreator = { creator_id: string; name: string; follower_count: number; in_guest_list: boolean };
  const [allFollowedCreators, setAllFollowedCreators] = useState<FollowedCreator[]>([]);
  const [allFollowedLoading, setAllFollowedLoading] = useState(false);
  const [showAdminFollowed, setShowAdminFollowed] = useState(false);

  /** Update text under Quick Add: success (creator + platforms), error, or loading. Clears after 8s (except loading). */
  const [quickAddUpdate, setQuickAddUpdate] = useState<{ type: "success" | "error" | "loading"; message: string } | null>(null);

  // Custom Categories State
  const [categories, setCategories] = useState<string[]>(() => {
    try {
      const saved = localStorage.getItem("fav_creators_categories");
      return saved ? JSON.parse(saved) : DEFAULT_CATEGORIES;
    } catch {
      return DEFAULT_CATEGORIES;
    }
  });

  // Live Summary State
  const [liveCreators, setLiveCreators] = useState<LiveCreator[]>([]);
  const [isCheckingLiveStatus, setIsCheckingLiveStatus] = useState<boolean>(true);
  const [liveCheckProgress, setLiveCheckProgress] = useState<{ current: number; total: number; currentCreator: string } | null>(null);
  const [showLiveSummary, setShowLiveSummary] = useState<boolean>(() => {
    try {
      return localStorage.getItem('fav_creators_show_live_summary') !== 'false';
    } catch {
      return true;
    }
  });
  const [selectedLivePlatform, setSelectedLivePlatform] = useState<string>('all');
  const [liveStatusLastUpdated, setLiveStatusLastUpdated] = useState<number | undefined>(undefined);
  const [isManualRefreshing, setIsManualRefreshing] = useState<boolean>(false);
  const [creatorsLoadedFromApi, setCreatorsLoadedFromApi] = useState<boolean>(false);

  // Persist live summary visibility
  useEffect(() => {
    localStorage.setItem('fav_creators_show_live_summary', showLiveSummary ? 'true' : 'false');
  }, [showLiveSummary]);

  // Toast notification state - supports queue for multiple notifications
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [toastQueue, setToastQueue] = useState<string[]>([]);
  const [liveFoundToasts, setLiveFoundToasts] = useState<{ name: string; platform: string; timestamp: number }[]>([]);

  // Auto-hide toast after 3 seconds
  useEffect(() => {
    if (toastMessage) {
      const timer = setTimeout(() => {
        setToastMessage(null);
        // Check if there are queued messages
        if (toastQueue.length > 0) {
          const [next, ...rest] = toastQueue;
          setToastMessage(next);
          setToastQueue(rest);
        }
      }, 3000);
      return () => clearTimeout(timer);
    } else if (toastQueue.length > 0) {
      // If no current toast but queue has items, show next
      const [next, ...rest] = toastQueue;
      setToastMessage(next);
      setToastQueue(rest);
    }
  }, [toastMessage, toastQueue]);

  // Auto-remove live found toasts after 5 seconds
  useEffect(() => {
    if (liveFoundToasts.length > 0) {
      const timer = setTimeout(() => {
        const now = Date.now();
        setLiveFoundToasts(prev => prev.filter(t => now - t.timestamp < 5000));
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [liveFoundToasts]);

  // Helper to add live found toast
  const addLiveFoundToast = useCallback((name: string, platform: string) => {
    setLiveFoundToasts(prev => {
      // Avoid duplicates
      if (prev.some(t => t.name === name && t.platform === platform)) return prev;
      return [...prev, { name, platform, timestamp: Date.now() }];
    });
  }, []);

  // Update liveCreators whenever creators change
  useEffect(() => {
    const live: LiveCreator[] = [];
    creators.forEach(creator => {
      creator.accounts.forEach(account => {
        if (account.isLive || account.hasStory) {
          live.push({
            creator,
            platform: account.platform,
            accountUrl: account.url,
            status: account.isLive ? 'live' : 'story',
            storyCount: account.storyCount,
            postedAt: account.storyPostedAt
          });
        }
      });
    });
    setLiveCreators(live);
  }, [creators]);



  // Persist live summary visibility
  // useEffect(() => {
  //   localStorage.setItem('fav_creators_show_live_summary', showLiveSummary ? 'true' : 'false');
  // }, [showLiveSummary]);

  // Persist Categories
  useEffect(() => {
    localStorage.setItem("fav_creators_categories", JSON.stringify(categories));
  }, [categories]);

  // Persist auto-expand notes setting
  useEffect(() => {
    localStorage.setItem("fav_creators_auto_expand_notes", autoExpandSecondaryNotes ? "true" : "false");
  }, [autoExpandSecondaryNotes]);

  // Clear Quick Add update message after 8s (but not loading messages)
  useEffect(() => {
    if (!quickAddUpdate || quickAddUpdate.type === "loading") return;
    const t = setTimeout(() => setQuickAddUpdate(null), 8000);
    return () => clearTimeout(t);
  }, [quickAddUpdate]);

  const creatorsRef = useRef<Creator[]>(creators);

  const realAvatarCount = useMemo(
    () =>
      creators.filter(
        (creator) =>
          creator.avatarUrl &&
          !creator.avatarUrl.includes("dicebear.com"),
      ).length,
    [creators],
  );

  useEffect(() => {
    creatorsRef.current = creators;
  }, [creators]);

  // TEMPORARILY COMMENTED OUT - Incomplete LiveSummary feature from another agent
  // Compute live creators from account data
  // const computedLiveCreators = useMemo(() => {
  //   const live: LiveCreator[] = [];
  //
  //   creators.forEach(creator => {
  //     creator.accounts.forEach(account => {
  //       // Add live streams
  //       if (account.isLive) {
  //         live.push({
  //           creator,
  //           platform: account.platform,
  //           accountUrl: account.url,
  //           status: 'live',
  //           startedAt: account.liveStartedAt
  //         });
  //       }
  //       // Add TikTok stories
  //       if (account.hasStory && account.platform === 'tiktok') {
  //         live.push({
  //           creator,
  //           platform: account.platform,
  //           accountUrl: account.url,
  //           status: 'story',
  //           postedAt: account.storyPostedAt,
  //           storyCount: account.storyCount
  //         });
  //       }
  //     });
  //   });
  //
  //   return live;
  // }, [creators]);
  //
  // // Update live creators state when computed value changes
  // useEffect(() => {
  //   setLiveCreators(computedLiveCreators);
  // }, [computedLiveCreators]);

  useEffect(() => {
    let isMounted = true;

    const loadDefaultCreatorPacks = async () => {
      // Use BASE_URL for correct path in development and production
      const baseUrl = import.meta.env.BASE_URL || "/";
      const packUrls = [`${baseUrl}clavicular.json`];
      try {
        const responses = await Promise.all(
          packUrls.map((url) => fetch(url).then((res) => (res.ok ? res.json() : null))),
        );

        const incomingCreators = responses
          .filter(Boolean)
          .flatMap((data) => (Array.isArray(data) ? data : [data]))
          .filter((creator): creator is Creator =>
            creator && typeof creator.id === "string" && Array.isArray(creator.accounts),
          );

        if (incomingCreators.length && isMounted) {
          const sanitized = ensureAvatarForCreators(incomingCreators);
          setCreators((current) => mergeCreatorsById(current, sanitized));
        }
      } catch (error) {
        console.warn("Failed to load default creator packs", error);
      }
    };

    loadDefaultCreatorPacks();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    let isMounted = true;

    const fixAllAvatars = async () => {
      const snapshot = creatorsRef.current;
      for (const creator of snapshot) {
        if (!isMounted) return;
        const avatarUrl = creator.avatarUrl || "";
        const isLocalAvatar = avatarUrl.startsWith("/avatars/");
        const shouldFetch = isGuestMode || (!isLocalAvatar && avatarUrl.includes("dicebear.com"));
        if (shouldFetch) {
          console.log(`[AVATAR] Fetching avatar for ${creator.name} (${creator.id})...`);
          try {
            const avatar = await getBestAvatar(creator.name, creator.accounts);
            if (avatar && avatar !== creator.avatarUrl && isMounted) {
              console.log(`[AVATAR] Updated avatar for ${creator.name}: ${avatar}`);
              setCreators((oldCreators) =>
                oldCreators.map((c) =>
                  c.id === creator.id ? { ...c, avatarUrl: avatar } : c,
                ),
              );
            }
          } catch (err) {
            console.error(`[AVATAR] Error fetching avatar for ${creator.name}:`, err);
          }
        }
      }
    };

    fixAllAvatars();
    const interval = setInterval(fixAllAvatars, 600000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  // Sign-of-life: check backend/DB with status.php (read test + Starfireara note). Resolve API base first (e.g. /findevents/fc/api fallback).
  useEffect(() => {
    const checkBackend = async () => {
      await resolveAuthBase();
      const base = getAuthBase();
      if (!base) {
        setBackendStatus("disconnected");
        setBackendStatusDetail({ error: "No API base (getAuthBase empty)", statusUrl: "" });
        return;
      }
      const statusUrl = `${base}/status.php`;
      try {
        const res = await fcApiFetch(statusUrl);
        const text = await res.text();
        if (typeof window !== "undefined") {
          console.log("[BACKEND] status.php:", res.status, "body length:", text.length, text.length <= 200 ? text : text.slice(0, 200) + "...");
        }
        if (!res.ok) {
          setBackendStatus("disconnected");
          setBackendStatusDetail({ error: `status.php ${res.status} (PHP not running or file missing?)`, statusUrl });
          return;
        }
        try {
          const data = text ? (JSON.parse(text) as { ok?: boolean; read_ok?: boolean; starfireara_note?: string | null; error?: string }) : {};
          if (data.ok === true && data.read_ok === true) {
            setBackendStatus("connected");
            setBackendStatusDetail({
              read_ok: true,
              starfireara_note: data.starfireara_note ?? null,
              statusUrl,
            });
            // Apply notes from status (sign of life) so Starfireara etc. show immediately
            const sample = (data as { get_notes_sample?: Record<string, string> }).get_notes_sample;
            if (sample && typeof sample === "object" && Object.keys(sample).length > 0) {
              setCreators((prev) => prev.map((c) => (sample[c.id] ? { ...c, note: sample[c.id] } : c)));
            }
            return;
          }
          setBackendStatus("disconnected");
          setBackendStatusDetail({
            read_ok: data.read_ok,
            starfireara_note: data.starfireara_note ?? null,
            error: data.error ?? "status.php returned ok=false",
            statusUrl,
          });
        } catch {
          setBackendStatus("disconnected");
          setBackendStatusDetail({ error: "status.php returned non-JSON", statusUrl });
        }
      } catch (e) {
        console.warn("Backend check failed", e);
        setBackendStatus("disconnected");
        setBackendStatusDetail({ error: String(e instanceof Error ? e.message : e), statusUrl });
      }
    };
    void checkBackend();
  }, []);

  useEffect(() => {
    // Fetch stored notes from MySQL. user_id=0 is the guest account; wait for auth to be checked so we don't request guest notes when logged in.
    if (!authChecked) return;
    const fetchRemoteNotes = async () => {
      try {
        await resolveAuthBase();
        const base = getAuthBase();
        if (!base) {
          if (typeof window !== "undefined") console.warn("[NOTES] No API base (getAuthBase empty), skipping get_notes");
          return;
        }
        const uid = authUser ? authUser.id : 0;
        const url = `${base}/get_notes.php?user_id=${uid}`;
        if (typeof window !== "undefined") {
          console.log(uid === 0 ? "[NOTES] Fetching (guest user_id=0):" : `[NOTES] Fetching (user ${uid}):`, url);
        }
        const res = await fcApiFetch(url);
        let text = await res.text();
        if (typeof window !== "undefined") {
          console.log("[NOTES] Response:", res.status, "body length:", text.length, text.length <= 120 ? text : text.slice(0, 120) + "...");
        }
        if (!res.ok) {
          if (typeof window !== "undefined") {
            console.warn(`get_notes failed: ${res.status} ${res.statusText} — ${url}. Guest notes come from /fc/api/get_notes.php; if 404, deploy PHP to /fc/api/ or enable PHP there.`);
          }
          return;
        }
        if (!text.trim()) {
          text = "{}";
        }
        try {
          const parsed = JSON.parse(text);
          // Support new format { notes, secondaryNotes } and old format (just notes object)
          const notes: Record<string, string> = parsed.notes ?? (typeof parsed === "object" && !parsed.secondaryNotes ? parsed : {});
          const secondaryNotes: Record<string, string> = parsed.secondaryNotes ?? {};
          if (typeof notes === "object" && notes !== null) {
            const keys = Object.keys(notes).filter((k) => notes[k] && k !== "_debug");
            setCreators(prev => prev.map(c => ({
              ...c,
              ...(notes[c.id] ? { note: notes[c.id] } : {}),
              ...(secondaryNotes[c.id] ? { secondaryNote: secondaryNotes[c.id] } : {}),
            })));
            if (keys.length > 0 && typeof window !== "undefined") {
              console.log(`[NOTES] Loaded ${keys.length} note(s), ${Object.keys(secondaryNotes).length} secondary note(s)`);
            }
          }
        } catch {
          if (typeof window !== "undefined" && !(window as unknown as { _getNotesWarned?: boolean })._getNotesWarned) {
            (window as unknown as { _getNotesWarned?: boolean })._getNotesWarned = true;
            console.warn("get_notes returned non-JSON. On localhost:5173 run 'python tools/serve_local.py' from project root so the API returns JSON.");
          }
        }
      } catch (e) {
        console.error("Failed to fetch notes", e);
      }
    };
    fetchRemoteNotes();
  }, [authUser, authChecked]);

  // Load my list from DB when logged in
  useEffect(() => {
    if (!authUser) return;
    const loadMyList = async () => {
      skipSaveAfterLoadRef.current = true; // prevent save effect from overwriting DB with this loaded list (avoids wiping server-only entries like Brunitarte)
      try {
        const base = getAuthBase();
        if (!base) return;
        const res = await fcApiFetch(`${base}/get_my_creators.php?user_id=${authUser.id}`);
        if (!res.ok) return;
        const text = await res.text();
        let data: { creators?: unknown[] };
        try {
          data = (text ? JSON.parse(text) : {}) as { creators?: unknown[] };
        } catch {
          return;
        }
        const list = data.creators && Array.isArray(data.creators) ? data.creators : [];
        if (list.length > 0) {
          console.log("Loaded creators from DB:", list.length);
          setCreators(ensureAvatarForCreators(list as Creator[]));
          setCreatorsLoadedFromApi(true);
        } else if (authUser.id === 0) {
          // Admin (user_id 0): no saved list yet → show default so Quick Add additions are visible
          setCreators(INITIAL_DATA);
          setCreatorsLoadedFromApi(true);
        }
        // Apply notes (e.g. Starfireara creator_id 6) after list is set so they are not overwritten
        try {
          const notesRes = await fcApiFetch(`${base}/get_notes.php?user_id=${authUser.id}`);
          const notesText = await notesRes.text();
          if (notesRes.ok && notesText.trim()) {
            const parsed = JSON.parse(notesText);
            const notes: Record<string, string> = parsed.notes ?? (typeof parsed === "object" && !parsed.secondaryNotes ? parsed : {});
            const secondaryNotes: Record<string, string> = parsed.secondaryNotes ?? {};
            if (typeof notes === "object" && notes !== null) {
              setCreators((prev) =>
                prev.map((c) => ({
                  ...c,
                  ...(notes[c.id] ? { note: notes[c.id] } : {}),
                  ...(secondaryNotes[c.id] ? { secondaryNote: secondaryNotes[c.id] } : {}),
                }))
              );
            }
          }
        } catch {
          // ignore
        }
        // Allow save again after we've finished applying load (prevents debounced save from overwriting DB)
        setTimeout(() => { skipSaveAfterLoadRef.current = false; }, 2500);
      } catch (e) {
        console.error("Failed to load remote list", e);
        skipSaveAfterLoadRef.current = false;
      }
    };
    loadMyList();
  }, [authUser]);

  useEffect(() => {
    // Save to localStorage for ALL users (including guests)
    localStorage.setItem("fav_creators", JSON.stringify(creators));

    // Save to MySQL if Logged In — but NOT when we just loaded from API (would overwrite DB and e.g. remove Brunitarte)
    if (authUser && !skipSaveAfterLoadRef.current) {
      const timer = setTimeout(async () => {
        if (skipSaveAfterLoadRef.current) return;
        try {
          const base = getAuthBase();
          if (!base) return;
          await fcApiFetch(`${base}/save_creators.php`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: authUser.id, creators }),
          });
          if (authUser.provider === "admin") {
            await fcApiFetch(`${base}/save_creators.php`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ user_id: 0, creators }),
            });
          }
        } catch (e) {
          console.error("Failed to save to DB", e);
        }
      }, 1000); // 1s debounce
      return () => clearTimeout(timer);
    }
  }, [creators, authUser]);

  /* loadMine removed as backend endpoint does not exist yet */
  /*
  useEffect(() => {
    const loadMine = async () => { ... }
    ...
  }, [authUser]);
  */

  useEffect(() => {
    const persist = async () => {
      if (!authUser) return;
      try {
        if (authUser.provider === "admin") {
          try {
            const base = getAuthBase();
            if (!base) return;
            await fcApiFetch(`${base}/creators/bulk`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              credentials: "include",
              body: JSON.stringify({ creators }),
            });
          } catch {
            localStorage.setItem(PUBLIC_CREATORS_STORAGE_KEY, JSON.stringify(creators));
          }
          return;
        }

        const base = getAuthBase();
        if (!base) return;
        await fcApiFetch(`${base}/creators/mine`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ creators }),
        });
      } catch (e) {
        console.warn("Failed to persist creators", e);
      }
    };

    if (isGuestMode && authUser?.provider !== "admin") return;
    if (!authUser) return;
    if (authUser.provider !== "admin" && !hasLoadedMineRef.current) return;

    const timeoutId = window.setTimeout(() => {
      void persist();
    }, 800);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [creators, authUser]);

  useEffect(() => {
    const loadUser = async () => {
      const cached = (() => {
        try {
          const raw = localStorage.getItem(AUTH_USER_STORAGE_KEY);
          if (!raw) return null;
          return JSON.parse(raw) as AuthUser;
        } catch {
          return null;
        }
      })();

      if (cached?.provider === "admin") {
        setAuthUser(cached);
        setAuthChecked(true);
        return;
      }

      try {
        const user = await fetchMe();
        setAuthUser(user);
        if (user) {
          localStorage.setItem(AUTH_USER_STORAGE_KEY, JSON.stringify(user));
        } else {
          localStorage.removeItem(AUTH_USER_STORAGE_KEY);
        }
      } catch (error) {
        if (cached) {
          setAuthUser(cached);
        }
        console.warn("Auth check failed", error);
      } finally {
        setAuthChecked(true);
      }
    };

    void loadUser();
  }, []);

  const fetchAllFollowedCreators = useCallback(async () => {
    if (authUser?.provider !== "admin") return;
    setAllFollowedLoading(true);
    try {
      await resolveAuthBase();
      const base = getAuthBase();
      if (!base) return;
      const res = await fcApiFetch(`${base}/get_all_followed_creators.php`, { credentials: "include" });
      if (!res.ok) return;
      const data = (await res.json()) as { creators?: FollowedCreator[] };
      if (Array.isArray(data.creators)) setAllFollowedCreators(data.creators);
    } catch {
      setAllFollowedCreators([]);
    } finally {
      setAllFollowedLoading(false);
    }
  }, [authUser?.provider]);

  useEffect(() => {
    if (authUser?.provider === "admin") void fetchAllFollowedCreators();
  }, [authUser?.provider, fetchAllFollowedCreators]);

  useEffect(() => {
    const loadFromServer = async () => {
      try {
        await resolveAuthBase();
        const base = getAuthBase();
        if (!base) return;
        // Ensure creators table and tables exist; seed from initial_creators.json if guest list empty (one-time)
        try {
          await fcApiFetch(`${base}/sync_creators_table.php`);
        } catch {
          /* ignore */
        }
        // Guest list is stored in MySQL as user_id 0 (admin can update it via Quick Add)
        const res = await fcApiFetch(`${base}/get_my_creators.php?user_id=0`);
        if (!res.ok) return;
        type GuestApiCreator = Record<string, unknown> & {
          id?: string; name?: string; bio?: string; avatar_url?: string; avatarUrl?: string;
          is_favorite?: boolean; isFavorite?: boolean; is_pinned?: boolean; isPinned?: boolean;
          category?: string; reason?: string; note?: string; tags?: string | string[];
          accounts?: string | SocialAccount[]; added_at?: number; addedAt?: number;
          last_checked?: number; lastChecked?: number;
        };
        const text = await res.text();
        let data: { creators?: GuestApiCreator[] };
        try {
          data = (text ? JSON.parse(text) : {}) as { creators?: GuestApiCreator[] };
        } catch {
          return;
        }
        if (Array.isArray(data.creators) && data.creators.length > 0) {
          const normalized = data.creators.map((c: GuestApiCreator) => ({
            id: c.id ?? "",
            name: c.name ?? "",
            bio: (c.bio as string) || "",
            avatarUrl: (c.avatar_url ?? c.avatarUrl) as string || "",
            isFavorite: Boolean(c.is_favorite ?? c.isFavorite),
            isPinned: Boolean(c.is_pinned ?? c.isPinned),
            category: (c.category as string) || "",
            reason: (c.reason as string) || "",
            note: (c.note as string) || "",
            tags: (() => {
              try {
                return typeof c.tags === "string" ? JSON.parse(c.tags) : (c.tags as string[]) || [];
              } catch {
                return [];
              }
            })(),
            accounts: (() => {
              try {
                return typeof c.accounts === "string" ? JSON.parse(c.accounts) : (c.accounts as SocialAccount[]) || [];
              } catch {
                return [];
              }
            })(),
            addedAt: (c.added_at ?? c.addedAt ?? Date.now()) as number,
            lastChecked: (c.last_checked ?? c.lastChecked ?? Date.now()) as number,
          })) as Creator[];

          // Merge in notes from get_notes so guest always sees real notes (get_my_creators may not include them)
          const notesRes = await fcApiFetch(`${base}/get_notes.php?user_id=0`);
          const notesText = notesRes.ok ? await notesRes.text() : "";
          let withNotes = ensureAvatarForCreators(normalized);
          if (notesText.trim()) {
            try {
              const parsed = JSON.parse(notesText);
              const notes: Record<string, string> = parsed.notes ?? (typeof parsed === "object" && !parsed.secondaryNotes ? parsed : {});
              const secondaryNotes: Record<string, string> = parsed.secondaryNotes ?? {};
              if (typeof notes === "object" && notes !== null) {
                withNotes = withNotes.map((c) => ({
                  ...c,
                  ...(notes[c.id] ? { note: notes[c.id] } : {}),
                  ...(secondaryNotes[c.id] ? { secondaryNote: secondaryNotes[c.id] } : {}),
                }));
              }
            } catch {
              /* ignore */
            }
          }
          // Only apply guest list if user did NOT log in while we were fetching (otherwise we overwrite their list and e.g. Brunitarte disappears)
          if (!authUserRef.current || authUserRef.current.id === 0) {
            setCreators(withNotes);
            setCreatorsLoadedFromApi(true);
          }
        } else {
          // Guest list empty or missing: still fetch notes and apply to current list (INITIAL_DATA) so Starfireara note shows
          if (!authUserRef.current || authUserRef.current.id === 0) {
            setCreatorsLoadedFromApi(true);
            const notesRes = await fcApiFetch(`${base}/get_notes.php?user_id=0`);
            const notesText = notesRes.ok ? await notesRes.text() : "";
            if (notesText.trim()) {
              try {
                const parsed = JSON.parse(notesText);
                const notes: Record<string, string> = parsed.notes ?? (typeof parsed === "object" && !parsed.secondaryNotes ? parsed : {});
                const secondaryNotes: Record<string, string> = parsed.secondaryNotes ?? {};
                if (typeof notes === "object" && notes !== null && Object.keys(notes).some((k) => notes[k])) {
                  setCreators((prev) => prev.map((c) => ({
                    ...c,
                    ...(notes[c.id] ? { note: notes[c.id] } : {}),
                    ...(secondaryNotes[c.id] ? { secondaryNote: secondaryNotes[c.id] } : {}),
                  })));
                }
              } catch {
                /* ignore */
              }
            }
          }
        }
      } catch (e) {
        console.warn("Failed to load guest creators from server", e);
      }
    };

    // Only load guest list when we've confirmed there is no logged-in user (prevents race: guest load overwriting user list before get_me returns).
    if (isGuestMode && authChecked && !authUser) {
      void loadFromServer();
    }
  }, [isGuestMode, authUser, authChecked]);

  // No longer checking for shared pack in URL

  const updateAllLiveStatuses = useCallback(async () => {
    const creatorCount = creatorsRef.current.length;
    console.log(`[Live Check] Starting updateAllLiveStatuses with ${creatorCount} creators`);
    
    setIsCheckingLiveStatus(true);
    setLiveCheckProgress({ current: 0, total: creatorCount, currentCreator: 'Starting...' });

    try {
      // Get current creators
      const currentCreators = [...creatorsRef.current];
      console.log(`[Live Check] Processing ${currentCreators.length} creators for live status`);
      
      // Warn if we're checking only the default 11 (indicates race condition)
      if (currentCreators.length <= 11 && authUser) {
        console.warn(`[Live Check] WARNING: Only ${currentCreators.length} creators to check for logged-in user. Expected more.`);
      }
      
      const updatedCreators: Creator[] = [];

      // Process creators sequentially with small delays to avoid overwhelming proxy
      for (let i = 0; i < currentCreators.length; i++) {
        const c = currentCreators[i];
        const now = Date.now();

        // Update progress
        setLiveCheckProgress({ current: i + 1, total: currentCreators.length, currentCreator: c.name });

        // Add delay between creators (except first one)
        if (i > 0) {
          await new Promise((resolve) => setTimeout(resolve, 500));
        }

        // Only check accounts the user marked for live (checkLive === true); backward compat: if none set, check all
        const toCheck = c.accounts.filter((acc) => acc.checkLive === true);
        const accountsToCheck = toCheck.length > 0 ? toCheck : c.accounts;

        const updatedAccounts = await Promise.all(
          c.accounts.map(async (acc) => {
            const shouldCheck = accountsToCheck.some((a) => a.id === acc.id);
            if (!shouldCheck) {
              console.log(`[SKIP] ${c.name} - ${acc.platform}:${acc.username} (checkLive: ${acc.checkLive})`);
              return { ...acc, isLive: false, lastChecked: now };
            }

            // Check if we should skip due to nextCheckDate (retry scheduling)
            if (acc.nextCheckDate && now < acc.nextCheckDate) {
              const retryDate = new Date(acc.nextCheckDate).toLocaleDateString();
              console.log(`[SKIP] ${c.name} - ${acc.platform}:${acc.username} (retry scheduled for ${retryDate})`);
              return { ...acc, lastChecked: now };
            }

            const liveResult = await checkLiveStatus(acc.platform, acc.username, c.id);

            if (!liveResult) {
              return { ...acc, isLive: false, lastChecked: now };
            }

            // Show toast notification when live creator is found!
            if (liveResult.isLive) {
              addLiveFoundToast(c.name, acc.platform);
            }

            // Track live status in database for faster checks & analytics
            updateStreamerLastSeen({
              creator_id: c.id,
              creator_name: c.name,
              platform: acc.platform,
              username: acc.username,
              account_url: acc.url || '',
              is_live: liveResult.isLive ?? false,
              checked_by: authUser?.email || 'anonymous'
            }).catch(err => console.warn('[LastSeen] Failed to update:', err));

            const updates: Partial<SocialAccount> = {
              isLive: liveResult.isLive,
              lastChecked: now,
              accountStatus: liveResult.accountStatus as any,
              statusLastChecked: now
            };

            // Include TikTok story data if available
            if (liveResult.hasStory !== undefined) {
              updates.hasStory = liveResult.hasStory;
              updates.storyCount = liveResult.storyCount;
              updates.storyPostedAt = liveResult.storyPostedAt;
            }

            // Schedule retry for banned/404 accounts (1 week)
            if (liveResult.accountStatus === 'not_found' || liveResult.accountStatus === 'banned') {
              const oneWeek = 7 * 24 * 60 * 60 * 1000;
              updates.nextCheckDate = now + oneWeek;
              console.log(`[STATUS] ${c.name} - ${acc.platform}:${acc.username} marked as ${liveResult.accountStatus}, retry in 1 week`);
            } else {
              updates.nextCheckDate = undefined;
            }

            return { ...acc, ...updates };
          }),
        );

        // Debug logging for loltyler1
        if (c.name.toLowerCase().includes('tyler1')) {
          console.log(`[DEBUG] ${c.name} updatedAccounts:`, updatedAccounts.map(a => ({
            platform: a.platform,
            username: a.username,
            isLive: a.isLive,
            checkLive: a.checkLive
          })));
        }

        const anyAccountLive = updatedAccounts.some((acc) => acc.isLive === true);
        updatedCreators.push({
          ...c,
          isLive: anyAccountLive,
          accounts: updatedAccounts,
          lastChecked: now,
        });
      }

      // Build live creators list for LiveSummary
      const newLiveCreators: LiveCreator[] = [];
      updatedCreators.forEach(creator => {
        creator.accounts.forEach(account => {
          if (account.isLive) {
            newLiveCreators.push({
              creator,
              platform: account.platform,
              accountUrl: account.url,
              status: 'live',
              startedAt: account.liveStartedAt
            });
          }
          if (account.hasStory) {
            newLiveCreators.push({
              creator,
              platform: account.platform,
              accountUrl: account.url,
              status: 'story',
              storyCount: account.storyCount,
              postedAt: account.storyPostedAt
            });
          }
        });
      });

      setLiveCreators(newLiveCreators);

      // Debug: Log what we're about to set
      const liveCount = updatedCreators.filter(c => c.isLive).length;
      console.log(`[DEBUG] About to update state with ${liveCount} live creators out of ${updatedCreators.length} total`);

      // Log specific creators that are live
      updatedCreators.filter(c => c.isLive).forEach(c => {
        const liveAccounts = c.accounts.filter(a => a.isLive);
        console.log(`[DEBUG LIVE] ${c.name} is live on:`, liveAccounts.map(a => `${a.platform} (${a.username})`));
      });

      setCreators(updatedCreators);

      // Sync live status to database cache for quick retrieval
      syncLiveStatusToDatabase(updatedCreators).catch(err => {
        console.warn('[Live Sync] Failed to sync to database:', err);
      });

      // Update the last updated timestamp
      setLiveStatusLastUpdated(Date.now());
      setIsManualRefreshing(false);

      // Return the updated creators for immediate use (e.g., in completion toast)
      return updatedCreators;
    } catch (error) {
      console.error('[Live Check] Error in updateAllLiveStatuses:', error);
      setIsManualRefreshing(false);
      // Return current creators if there's an error
      return creatorsRef.current;
    } finally {
      // Always set isChecking to false, even if there's an error
      setIsCheckingLiveStatus(false);
    }
  }, [addLiveFoundToast, authUser]);

  // Sync live status to database cache
  const syncLiveStatusToDatabase = useCallback(async (creatorsToSync: Creator[]) => {
    try {
      const payload = {
        creators: creatorsToSync.map(c => ({
          id: c.id,
          name: c.name,
          avatarUrl: c.avatarUrl,
          accounts: c.accounts.map(a => ({
            platform: a.platform,
            username: a.username,
            isLive: a.isLive,
            streamTitle: a.streamTitle,
            viewerCount: a.viewerCount,
            startedAt: a.liveStartedAt,
            checkMethod: a.checkMethod,
            nextCheckDate: a.nextCheckDate
          }))
        }))
      };

      const base = getAuthBase();
      if (!base) return;

      const response = await fcApiFetch(`${base}/sync_live_status.php`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        const result = await response.json();
        console.log(`[Live Sync] Synced ${result.updated} accounts to database`);
      }
    } catch (e) {
      console.error('[Live Sync] Error:', e);
    }
  }, []);

  // Load cached live status from database on initial load
  const loadCachedLiveStatus = useCallback(async () => {
    try {
      const base = getAuthBase();
      if (!base) {
        console.warn('[Live Cache] No API base available');
        return;
      }

      console.log('[Live Cache] Fetching cached live status from:', `${base}/get_live_cached.php`);
      const response = await fcApiFetch(`${base}/get_live_cached.php`);
      
      if (!response.ok) {
        console.warn('[Live Cache] Failed to fetch:', response.status, response.statusText);
        return;
      }

      const data = await response.json();
      console.log('[Live Cache] Response:', data);
      
      if (data.ok && data.liveNow && data.liveNow.length > 0) {
        // Convert cached data to LiveCreator format
        const cachedLiveCreators: LiveCreator[] = [];

        data.liveNow.forEach((creator: any) => {
          if (creator.platforms && Array.isArray(creator.platforms)) {
            creator.platforms.forEach((platform: any) => {
              // Try to find full creator data from current creators list
              const fullCreator = creatorsRef.current.find(c => c.id === creator.id) || {
                id: creator.id,
                name: creator.name,
                avatarUrl: creator.avatarUrl || '',
                bio: '',
                accounts: [],
                isFavorite: false,
                addedAt: Date.now()
              };

              cachedLiveCreators.push({
                creator: fullCreator,
                platform: platform.platform,
                status: 'live',
                accountUrl: platform.platform === 'kick'
                  ? `https://kick.com/${platform.username}`
                  : platform.platform === 'twitch'
                    ? `https://twitch.tv/${platform.username}`
                    : platform.platform === 'youtube'
                      ? `https://youtube.com/@${platform.username}`
                      : `https://tiktok.com/@${platform.username}`,
                startedAt: platform.startedAt ? new Date(platform.startedAt).getTime() / 1000 : undefined
              });
            });
          }
        });

        if (cachedLiveCreators.length > 0) {
          setLiveCreators(cachedLiveCreators);
          console.log(`[Live Cache] Loaded ${cachedLiveCreators.length} live streams from database`);
          
          // Also update creator isLive status based on cached data
          setCreators(prev => prev.map(c => {
            const liveEntry = data.liveNow.find((l: any) => l.id === c.id);
            if (liveEntry && liveEntry.isLive) {
              return { ...c, isLive: true };
            }
            return c;
          }));
        }
      } else {
        console.log('[Live Cache] No live creators in cache or cache empty');
      }
    } catch (e) {
      console.warn('[Live Cache] Could not load cached status:', e);
    }
    // Note: Don't set isCheckingLiveStatus to false here
    // Let updateAllLiveStatuses handle it after the real check completes
  }, []);

  // Auto-check live status on mount - wait for creators to be loaded from API
  useEffect(() => {
    // Don't start live checking until creators are loaded from API
    // This prevents checking only the INITIAL_DATA (11 creators) when user has more
    if (!creatorsLoadedFromApi) {
      console.log('[Live Check] Waiting for creators to load from API...');
      return;
    }

    console.log(`[Live Check] Creators loaded: ${creatorsRef.current.length}. Starting live checks...`);

    // First load cached status from database for instant display
    loadCachedLiveStatus();

    // Then do a fresh check after a delay
    const timer = setTimeout(() => {
      console.log(`[Live Check] Starting check with ${creatorsRef.current.length} creators`);
      updateAllLiveStatuses();
    }, 2000);

    const interval = setInterval(() => {
      console.log(`[Live Check] Auto-refresh with ${creatorsRef.current.length} creators`);
      updateAllLiveStatuses();
    }, 180000); // Check every 3 mins

    return () => {
      clearTimeout(timer);
      clearInterval(interval);
    };
  }, [updateAllLiveStatuses, loadCachedLiveStatus, creatorsLoadedFromApi]);

  // Data Migration: Ensure all existing accounts have follower counts
  useEffect(() => {
    const baseCreators = creatorsRef.current;
    let needsUpdate = false;

    const migrated = baseCreators.map((creator) => {
      let creatorUpdated = false;
      const newAccounts = creator.accounts.map((acc) => {
        if (!acc.followers) {
          creatorUpdated = true;
          needsUpdate = true;
          const randomFollowers = (Math.random() * 10 + 1).toFixed(1) + "M";
          return { ...acc, followers: randomFollowers };
        }
        return acc;
      });
      return creatorUpdated ? { ...creator, accounts: newAccounts } : creator;
    });

    if (needsUpdate) {
      setCreators(ensureAvatarForCreators(migrated));
    }
  }, []);

  /** Persist creators to MySQL for the logged-in user; when admin, also save to guest (user_id 0). */
  const saveCreatorsToBackend = useCallback(
    async (list: Creator[]) => {
      if (!authUser) return;
      const base = getAuthBase();
      if (!base) return;
      try {
        await fcApiFetch(`${base}/save_creators.php`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: authUser.id, creators: list }),
        });
        if (authUser.provider === "admin") {
          await fcApiFetch(`${base}/save_creators.php`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: 0, creators: list }),
          });
        }
      } catch (e) {
        console.error("Failed to save creators to DB", e);
      }
    },
    [authUser],
  );

  const handleQuickAdd = async () => {
    if (!quickAddValue.trim()) return;
    // Prevent duplicate submissions while already loading
    if (quickAddUpdate?.type === "loading") return;

    // Show loading message while we query social media accounts
    setQuickAddUpdate({ type: "loading", message: "Searching social media accounts..." });

    // If user pasted a URL (e.g. https://www.tiktok.com/@sunnystoktik), parse and add that single account
    const parsedUrl = parseSocialUrl(quickAddValue);
    if (parsedUrl) {
      const stableId = `${parsedUrl.username}-${parsedUrl.platform}`;
      if (creators.some((c) => c.id === stableId)) {
        setQuickAddUpdate({ type: "error", message: "Already in list." });
        setQuickAddValue("");
        return;
      }
      const now = Date.now();
      const nameFromUsername = parsedUrl.username
        .split(/[-_.]/)
        .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
        .join(" ");
      const account: SocialAccount = {
        id: crypto.randomUUID(),
        platform: parsedUrl.platform,
        username: parsedUrl.username,
        url: parsedUrl.url,
        lastChecked: now,
      };
      let avatarResult: string | null = null;
      try {
        avatarResult = await getBestAvatar(nameFromUsername, [account]);
      } catch (error) {
        console.warn("Avatar grabber failed after quick add URL", error);
      }
      const newCreator: Creator = {
        id: stableId,
        name: nameFromUsername,
        bio: `Added from ${parsedUrl.platform} link`,
        avatarUrl: avatarResult || buildFallbackAvatar({ name: nameFromUsername } as Creator),
        accounts: [account],
        isFavorite: false,
        isPinned: false,
        note: "",
        category: "Other",
        reason: "",
        addedAt: now,
        lastChecked: now,
        tags: [...QUICK_ADD_DEFAULT_TAGS],
      };
      const withAvatar = ensureAvatarUrl(newCreator);
      const newList = [withAvatar, ...creators];
      setCreators(newList);
      setQuickAddValue("");
      const platformLabel = parsedUrl.platform.charAt(0).toUpperCase() + parsedUrl.platform.slice(1);
      try {
        await saveCreatorsToBackend(newList);
        setQuickAddUpdate({
          type: "success",
          message: `Added ${nameFromUsername} with 1 platform: ${platformLabel}.`,
        });
      } catch (e) {
        console.error("Quick add save failed", e);
        setQuickAddUpdate({
          type: "error",
          message: "Creator added locally but could not save to server. Check connection and try again.",
        });
      }
      return;
    }

    const parts = quickAddValue.split(":").map((p) => p.trim());
    const name = parts[0];
    let requestedPlatforms = parts.slice(1);

    if (!name) return;

    // Auto-find logic: if no platforms specified, search all major ones
    if (requestedPlatforms.length === 0) {
      requestedPlatforms = ["kick", "twitch", "youtube", "tiktok", "instagram"];
    }

    let youtubeSearchResult: string | null = null;
    if (requestedPlatforms.includes("youtube")) {
      try {
        youtubeSearchResult = await googleSearchYoutubeChannel(
          `${name} official youtube`,
        );
      } catch (error) {
        console.warn("Quick add YouTube search failed", error);
      }
    }

    const accounts: SocialAccount[] = [];
    const now = Date.now();

    requestedPlatforms.forEach((p) => {
      const platform = p.toLowerCase() as Platform;
      const id = crypto.randomUUID();
      let cleanUsername = name.toLowerCase().replace(/\s+/g, "");
      const dummyFollowers = (Math.random() * 5 + 0.5).toFixed(1) + "M";

      // Specialized matching for specific creators
      if (cleanUsername === "zarthestar") {
        if (platform === "tiktok" || platform === "youtube") cleanUsername = "zarthestarcomedy";
        if (platform === "instagram") cleanUsername = "zar.the.star";
      }

      const baseAccount = {
        id,
        platform,
        username: cleanUsername,
        followers: dummyFollowers,
        lastChecked: now,
      };

      if (platform === "kick") {
        accounts.push({
          ...baseAccount,
          url: `https://kick.com/${cleanUsername}`,
        });
      } else if (platform === "twitch") {
        accounts.push({
          ...baseAccount,
          url: `https://twitch.tv/${cleanUsername}`,
        });
      } else if (platform === "youtube") {
        const url = youtubeSearchResult || `https://youtube.com/@${cleanUsername}`;
        const username = extractYoutubeUsername(url) || cleanUsername;
        accounts.push({
          ...baseAccount,
          url,
          username,
        });
      } else if (platform === "tiktok") {
        accounts.push({
          ...baseAccount,
          url: `https://tiktok.com/@${cleanUsername}`,
        });
      } else if (platform === "instagram") {
        accounts.push({
          ...baseAccount,
          url: `https://instagram.com/${cleanUsername}`,
        });
      }
    });

    let avatarResult: string | null = null;
    if (accounts.length > 0) {
      try {
        avatarResult = await getBestAvatar(name, accounts);
      } catch (error) {
        console.warn("Avatar grabber failed after quick add", error);
      }
    }

    const newCreator: Creator = {
      id: crypto.randomUUID(),
      name: name
        .split(" ")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" "),
      bio: `Auto-found social accounts for ${name}`,
      avatarUrl:
        avatarResult || buildFallbackAvatar({ name } as Creator),
      accounts,
      isFavorite: false,
      isPinned: false,
      note: "",
      category: "Other",
      reason: "",
      addedAt: now,
      lastChecked: now,
      tags: [...QUICK_ADD_DEFAULT_TAGS],
    };

    const withAvatar = ensureAvatarUrl(newCreator);
    const newList = [withAvatar, ...creators];
    setCreators(newList);
    setQuickAddValue("");
    const platformsList = [...new Set(accounts.map((a) => a.platform))].map((p) => p.charAt(0).toUpperCase() + p.slice(1)).join(", ");
    try {
      await saveCreatorsToBackend(newList);
      setQuickAddUpdate({
        type: "success",
        message: `Added ${newCreator.name} with platforms: ${platformsList}.`,
      });
    } catch (e) {
      console.error("Quick add save failed", e);
      setQuickAddUpdate({
        type: "error",
        message: "Creator added locally but could not save to server. Check connection and try again.",
      });
    }
  };

  const handleExport = () => {
    const dataStr = JSON.stringify(creators, null, 2);
    const dataUri =
      "data:application/json;charset=utf-8," + encodeURIComponent(dataStr);

    const exportFileDefaultName = "fav-creators-export.json";

    const linkElement = document.createElement("a");
    linkElement.setAttribute("href", dataUri);
    linkElement.setAttribute("download", exportFileDefaultName);
    linkElement.click();
  };

  // Cookie helpers for settings persistence
  const setCookie = (name: string, value: string, days: number = 365) => {
    const expires = new Date();
    expires.setTime(expires.getTime() + days * 24 * 60 * 60 * 1000);
    document.cookie = `${name}=${encodeURIComponent(value)};expires=${expires.toUTCString()};path=/;SameSite=Strict`;
  };

  const getCookie = (name: string): string | null => {
    const nameEQ = name + "=";
    const ca = document.cookie.split(";");
    for (let c of ca) {
      c = c.trim();
      if (c.indexOf(nameEQ) === 0) {
        return decodeURIComponent(c.substring(nameEQ.length));
      }
    }
    return null;
  };

  // Save all settings to cookie
  const handleSaveSettings = () => {
    const settings = {
      creators,
      categoryFilter,
      viewMode,
      searchQuery,
      savedAt: Date.now(),
    };
    try {
      setCookie("favcreators_settings", JSON.stringify(settings));
      alert("Settings saved to browser cookies!");
    } catch (e) {
      console.error("Failed to save settings:", e);
      alert("Failed to save settings. Try exporting to JSON instead.");
    }
  };

  // Load settings from cookie on mount
  useEffect(() => {
    const savedSettings = getCookie("favcreators_settings");
    if (savedSettings) {
      try {
        const settings = JSON.parse(savedSettings);
        if (settings.creators) {
          // Don't auto-load from cookie, just keep localStorage as primary
          console.log(
            "Cookie settings found, last saved:",
            new Date(settings.savedAt).toLocaleString(),
          );
        }
      } catch (e) {
        console.error("Failed to parse cookie settings:", e);
      }
    }
  }, []);

  // Export settings to JSON file
  const handleExportSettings = () => {
    const settings = {
      creators,
      categoryFilter,
      viewMode,
      exportedAt: new Date().toISOString(),
      version: DATA_VERSION,
    };
    const dataStr = JSON.stringify(settings, null, 2);
    const dataUri =
      "data:application/json;charset=utf-8," + encodeURIComponent(dataStr);
    const exportFileDefaultName = `favcreators-settings-${new Date().toISOString().split("T")[0]}.json`;
    const linkElement = document.createElement("a");
    linkElement.setAttribute("href", dataUri);
    linkElement.setAttribute("download", exportFileDefaultName);
    linkElement.click();
  };

  // Import settings from JSON file
  const handleImportSettings = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json";
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = (event) => {
        try {
          const content = event.target?.result as string;
          const parsed = JSON.parse(content);

          if (Array.isArray(parsed)) {
            // Legacy/Simple Import
            if (window.confirm(`Found ${parsed.length} creators. Overwrite existing list?`)) {
              setCreators(ensureAvatarForCreators(parsed));
            }
          } else if (parsed.creators) {
            // Settings Import
            if (window.confirm(`Import settings from ${parsed.exportedAt || 'file'}?`)) {
              setCreators(ensureAvatarForCreators(parsed.creators));
              if (parsed.viewMode) setViewMode(parsed.viewMode);
              if (parsed.categoryFilter) setCategoryFilter(parsed.categoryFilter);
            }
          } else {
            alert("Invalid file format.");
          }
        } catch (e) {
          console.error(e);
          alert("Failed to parse file.");
        }
      };
      reader.readAsText(file);
    };
    input.click();
  };

  const handleWipeAll = () => {
    if (window.confirm("⚠️ DANGER: Are you sure you want to WIPE ALL creators?\n\nThis cannot be undone.")) {
      setCreators([]);
      localStorage.removeItem("fav_creators");
    }
  };

  const handleRenameCategory = () => {
    const oldName = prompt("Enter the category name to rename:");
    if (!oldName || !categories.includes(oldName)) {
      if (oldName) alert("Category not found.");
      return;
    }
    const newName = prompt(`Rename '${oldName}' to:`);
    if (!newName || newName === oldName) return;

    // Update List
    setCategories(prev => prev.map(c => c === oldName ? newName : c));

    // Update Creators
    setCreators(prev => prev.map(c => c.category === oldName ? { ...c, category: newName } : c));
  };

  const handleAddCategory = () => {
    const newCat = prompt("Enter new category name:");
    if (newCat && newCat.trim()) {
      const trimmed = newCat.trim();
      if (!categories.includes(trimmed)) {
        setCategories(prev => [...prev, trimmed]);
      } else {
        alert("Category already exists.");
      }
    }
  };


  const handleCheckCreatorStatus = async (id: string) => {
    const creator = creators.find((c) => c.id === id);
    if (!creator) return;

    // Show toast notification
    setToastMessage(`⚡ Checking live status for ${creator.name}...`);

    const toCheck = creator.accounts.filter((acc) => acc.checkLive === true);
    const accountsToCheck = toCheck.length > 0 ? toCheck : creator.accounts;

    const now = Date.now();
    const updatedAccounts = await Promise.all(
      creator.accounts.map(async (acc) => {
        const shouldCheck = accountsToCheck.some((a) => a.id === acc.id);
        if (!shouldCheck) {
          console.log(`[SKIP] ${creator.name} - ${acc.platform}:${acc.username} (checkLive: ${acc.checkLive})`);
          return { ...acc, isLive: false, lastChecked: now };
        }

        // Check if we should skip due to nextCheckDate (retry scheduling)
        if (acc.nextCheckDate && now < acc.nextCheckDate) {
          const retryDate = new Date(acc.nextCheckDate).toLocaleDateString();
          console.log(`[SKIP] ${creator.name} - ${acc.platform}:${acc.username} (retry scheduled for ${retryDate})`);
          return { ...acc, lastChecked: now };
        }

        const liveResult = await checkLiveStatus(acc.platform, acc.username);

        if (!liveResult) {
          return { ...acc, isLive: false, lastChecked: now };
        }

        // Track live status in database for faster checks & analytics
        updateStreamerLastSeen({
          creator_id: creator.id,
          creator_name: creator.name,
          platform: acc.platform,
          username: acc.username,
          account_url: acc.url || '',
          is_live: liveResult.isLive ?? false,
          checked_by: authUser?.email || 'anonymous'
        }).catch(err => console.warn('[LastSeen] Failed to update:', err));

        const updates: Partial<SocialAccount> = {
          isLive: liveResult.isLive,
          lastChecked: now,
          accountStatus: liveResult.accountStatus as any,
          statusLastChecked: now
        };

        // Include TikTok story data if available
        if (liveResult.hasStory !== undefined) {
          updates.hasStory = liveResult.hasStory;
          updates.storyCount = liveResult.storyCount;
          updates.storyPostedAt = liveResult.storyPostedAt;
        }

        // Schedule retry for banned/404 accounts (1 week)
        if (liveResult.accountStatus === 'not_found' || liveResult.accountStatus === 'banned') {
          const oneWeek = 7 * 24 * 60 * 60 * 1000;
          updates.nextCheckDate = now + oneWeek;
          console.log(`[STATUS] ${creator.name} - ${acc.platform}:${acc.username} marked as ${liveResult.accountStatus}, retry in 1 week`);
        } else {
          updates.nextCheckDate = undefined;
        }

        return { ...acc, ...updates };
      }),
    );

    const anyAccountLive = updatedAccounts.some((acc) => acc.isLive === true);
    const updatedCreatorsList = creators.map((c) =>
      c.id === id
        ? {
          ...c,
          isLive: anyAccountLive,
          accounts: updatedAccounts,
          lastChecked: now,
        }
        : c,
    );

    setCreators(updatedCreatorsList);

    // Update live creators list
    const newLiveCreators: LiveCreator[] = [];
    updatedCreatorsList.forEach(creator => {
      creator.accounts.forEach(account => {
        if (account.isLive) {
          newLiveCreators.push({
            creator,
            platform: account.platform,
            accountUrl: account.url,
            status: 'live',
            startedAt: account.liveStartedAt
          });
        }
        if (account.hasStory) {
          newLiveCreators.push({
            creator,
            platform: account.platform,
            accountUrl: account.url,
            status: 'story',
            storyCount: account.storyCount,
            postedAt: account.storyPostedAt
          });
        }
      });
    });
    setLiveCreators(newLiveCreators);
  };

  const handleRefreshStatus = async () => {
    setToastMessage("⚡ Checking live status for all creators...");
    const updatedCreators = await updateAllLiveStatuses();

    // Show completion toast with live count from the returned updated creators
    const liveCount = updatedCreators.filter(c => c.isLive).length;
    const message = liveCount > 0
      ? `✅ Live check complete! ${liveCount} creator${liveCount > 1 ? 's' : ''} currently live`
      : "✅ Live check complete! No creators are currently live";

    setToastMessage(message);
  };

  const handleResetDatabase = () => {
    if (
      window.confirm(
        "This will reset your entire list to the latest official creator data. Continue?",
      )
    ) {
      setCreators(INITIAL_DATA);
    }
  };

  const handleGoogleLogin = () => {
    const base = getAuthBase();
    if (!base) {
      alert("Auth not configured. Set VITE_AUTH_BASE_URL for production.");
      return;
    }
    window.location.href = `${base}/google_auth.php`;
  };

  const handleLogin = async () => {
    setAuthLoading(true);
    setAuthError(null);
    try {
      const loginUser = await loginWithPassword(loginEmail, loginPassword);
      const user = loginUser ?? (await fetchMe());
      setAuthUser(user);
      if (user) {
        localStorage.setItem(AUTH_USER_STORAGE_KEY, JSON.stringify(user));
      }
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Login failed");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleRegister = async () => {
    setAuthLoading(true);
    setAuthError(null);
    try {
      await registerWithPassword(registerEmail, registerPassword, registerName);
      const user = await fetchMe();
      setAuthUser(user);
      if (user) {
        localStorage.setItem(AUTH_USER_STORAGE_KEY, JSON.stringify(user));
      }
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Registration failed");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = async () => {
    await logoutAuth();
    setAuthUser(null);
    localStorage.removeItem(AUTH_USER_STORAGE_KEY);
  };

  const handleSaveCreator = (newCreator: Creator) => {
    setCreators([ensureAvatarUrl(newCreator), ...creators]);
    setIsFormOpen(false);
  };

  const handleDeleteCreator = (id: string) => {
    if (window.confirm("Are you sure you want to remove this creator?")) {
      setCreators(creators.filter((c) => c.id !== id));
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  };

  const toggleTableSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAllInTable = (visibleIds: string[]) => {
    setSelectedIds((prev) => {
      const allSelected = visibleIds.length > 0 && visibleIds.every((id) => prev.has(id));
      if (allSelected) {
        const next = new Set(prev);
        visibleIds.forEach((id) => next.delete(id));
        return next;
      }
      return new Set([...prev, ...visibleIds]);
    });
  };

  const clearTableSelection = () => setSelectedIds(new Set());

  const handleBulkApplyCategory = (category: string) => {
    if (!category.trim()) return;
    const ids = Array.from(selectedIds);
    setCreators((prev) =>
      prev.map((c) => (ids.includes(c.id) ? { ...c, category: category.trim() } : c))
    );
    setSelectedIds(new Set());
  };

  const handleBulkDelete = () => {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) return;
    if (!window.confirm(`Remove ${ids.length} selected creator(s)? This cannot be undone.`)) return;
    setCreators((prev) => prev.filter((c) => !ids.includes(c.id)));
    setSelectedIds(new Set());
  };

  const handleToggleFavorite = (id: string) => {
    const next = creators.map((c) =>
      c.id === id ? { ...c, isFavorite: !c.isFavorite } : c,
    );
    setCreators(next);
    void saveCreatorsToBackend(next);
  };

  const handleTogglePin = (id: string) => {
    const next = creators.map((c) => (c.id === id ? { ...c, isPinned: !c.isPinned } : c));
    setCreators(next);
    void saveCreatorsToBackend(next);
  };

  const handleSaveNote = async (id: string, note: string) => {
    try {
      if (!authUser) {
        alert("Please login to save notes remotely.");
        return;
      }

      const authBase = getAuthBase();
      if (!authBase) {
        alert("Auth not configured. Notes cannot be saved remotely.");
        return;
      }
      const res = await fcApiFetch(`${authBase}/save_note.php`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          creator_id: id,
          note: note,
          user_id: authUser.id
        })
      });

      const text = await res.text();
      let data: { status?: string; error?: string } = {};
      if (text && text.trim()) {
        try {
          data = JSON.parse(text) as { status?: string; error?: string };
        } catch {
          console.warn("Save note: server returned non-JSON", text.slice(0, 200));
        }
      }
      if (data.status === "success") {
        alert("Note saved to database!");
      } else if (data.error) {
        alert("Failed to save: " + data.error);
      } else if (!res.ok || !text.trim()) {
        const tip = typeof window !== "undefined" && /localhost|127\.0\.0\.1/.test(window.location?.hostname || "")
          ? " For local dev, run: python tools/serve_local.py (from project root), then use http://localhost:5173/fc/#/guest"
          : " Use a backend with save_note.php for persistence.";
        alert("Note save failed: server returned an empty or invalid response (often 404)." + tip);
      } else {
        alert("Failed to save: " + (data.error || "Unknown error"));
      }
    } catch (e) {
      console.error(e);
      alert("Error saving note: " + (e instanceof Error ? e.message : String(e)));
    }
  };

  const handleUpdateNote = (id: string, note: string) => {
    setCreators(creators.map((c) => (c.id === id ? { ...c, note } : c)));
  };

  const handleUpdateSecondaryNote = (id: string, secondaryNote: string) => {
    setCreators(creators.map((c) => (c.id === id ? { ...c, secondaryNote } : c)));
  };

  const handleSaveSecondaryNote = async (id: string, secondaryNote: string) => {
    try {
      if (!authUser) {
        alert("Please login to save secondary notes remotely.");
        return;
      }
      const authBase = getAuthBase();
      if (!authBase) {
        alert("Auth not configured. Secondary notes cannot be saved remotely.");
        return;
      }
      const res = await fcApiFetch(`${authBase}/save_secondary_note.php`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          creator_id: id,
          secondary_note: secondaryNote,
          user_id: authUser.id,
        }),
      });
      const text = await res.text();
      let data: { status?: string; error?: string } = {};
      if (text && text.trim()) {
        try {
          data = JSON.parse(text) as { status?: string; error?: string };
        } catch {
          console.warn("Save secondary note: server returned non-JSON", text.slice(0, 200));
        }
      }
      if (data.status === "success") {
        alert("Secondary note saved!");
      } else if (data.error) {
        alert("Failed to save secondary note: " + data.error);
      } else if (!res.ok || !text.trim()) {
        alert("Secondary note save failed: server returned empty/invalid response.");
      }
    } catch (e) {
      console.error(e);
      alert("Error saving secondary note: " + (e instanceof Error ? e.message : String(e)));
    }
  };

  const handleUpdateCreator = (
    creatorId: string,
    updates: { category?: string; accounts: SocialAccount[]; note?: string; isLiveStreamer?: boolean; avatarUrl?: string; selectedAvatarSource?: string },
  ) => {
    const next = creators.map((c) =>
      c.id === creatorId
        ? {
          ...c,
          ...(updates.category !== undefined && { category: updates.category }),
          ...(updates.accounts !== undefined && { accounts: updates.accounts }),
          ...(updates.note !== undefined && { note: updates.note, reason: updates.note }),
          ...(updates.isLiveStreamer !== undefined && { isLiveStreamer: updates.isLiveStreamer }),
          ...(updates.avatarUrl !== undefined && { avatarUrl: updates.avatarUrl }),
          ...(updates.selectedAvatarSource !== undefined && { selectedAvatarSource: updates.selectedAvatarSource }),
        }
        : c,
    );
    setCreators(next);
    void saveCreatorsToBackend(next);
  };

  const handleRemoveAccount = (creatorId: string, accountId: string) => {
    setCreators(
      creators.map((c) =>
        c.id === creatorId
          ? { ...c, accounts: c.accounts.filter((acc) => acc.id !== accountId) }
          : c,
      ),
    );
  };

  const handleRefreshAvatar = async (id: string) => {
    const creator = creators.find((c) => c.id === id);
    if (!creator) return;
    const avatar = await getBestAvatar(creator.name, creator.accounts);
    setCreators((oldCreators) =>
      oldCreators.map((c) =>
        c.id === id
          ? {
            ...c,
            avatarUrl:
              avatar && !avatar.includes("dicebear.com")
                ? avatar
                : buildFallbackAvatar(c),
          }
          : c
      )
    );
  };

  // Render view mode toggle
  const renderViewModeToggle = () => (
    <div
      style={{
        display: "flex",
        gap: "0.5rem",
        marginBottom: "1rem",
        flexWrap: "wrap",
      }}
    >
      <button
        type="button"
        className={`btn-secondary ${viewMode === "list" ? "view-active" : ""}`}
        onClick={() => setViewMode("list")}
        style={{
          padding: "0.5rem 1rem",
          background: viewMode === "list" ? "var(--accent)" : "rgb(30, 41, 59)",
          color: "white",
          border: "none",
          borderRadius: "6px",
          cursor: "pointer",
        }}
      >
        List View
      </button>
      <button
        type="button"
        className={`btn-secondary ${viewMode === "dropdown" ? "view-active" : ""}`}
        onClick={() => setViewMode("dropdown")}
        style={{
          padding: "0.5rem 1rem",
          background:
            viewMode === "dropdown" ? "var(--accent)" : "rgb(30, 41, 59)",
          color: "white",
          border: "none",
          borderRadius: "6px",
          cursor: "pointer",
        }}
      >
        Dropdown View
      </button>
      <button
        type="button"
        className={`btn-secondary ${viewMode === "table" ? "view-active" : ""}`}
        onClick={() => setViewMode("table")}
        style={{
          padding: "0.5rem 1rem",
          background: viewMode === "table" ? "var(--accent)" : "rgb(30, 41, 59)",
          color: "white",
          border: "none",
          borderRadius: "6px",
          cursor: "pointer",
        }}
      >
        Tabular View
      </button>
    </div>
  );

  return (
    <div className="app-container">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="toast-notification">
          {toastMessage}
        </div>
      )}
      
      {/* Live Found Toasts - Stack in bottom right during checking */}
      {liveFoundToasts.length > 0 && (
        <div className="live-found-toasts" style={{
          position: 'fixed',
          bottom: '20px',
          right: '20px',
          zIndex: 1001,
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
          maxHeight: '300px',
          overflow: 'hidden'
        }}>
          {liveFoundToasts.slice(-5).map((toast) => (
            <div
              key={`${toast.name}-${toast.platform}-${toast.timestamp}`}
              className="live-found-toast"
              style={{
                padding: '12px 16px',
                backgroundColor: toast.platform === 'tiktok' ? 'rgba(255, 0, 80, 0.95)' :
                                 toast.platform === 'twitch' ? 'rgba(145, 70, 255, 0.95)' :
                                 toast.platform === 'kick' ? 'rgba(83, 252, 24, 0.95)' :
                                 toast.platform === 'youtube' ? 'rgba(255, 0, 0, 0.95)' :
                                 'rgba(99, 102, 241, 0.95)',
                color: toast.platform === 'kick' ? '#000' : '#fff',
                borderRadius: '8px',
                boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
                fontWeight: 600,
                fontSize: '0.9rem',
                animation: 'slideInRight 0.3s ease-out',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              <span style={{ fontSize: '1.1rem' }}>🔴</span>
              <span>{toast.name}</span>
              <span style={{ 
                fontSize: '0.75rem', 
                opacity: 0.9,
                textTransform: 'uppercase',
                fontWeight: 700
              }}>
                LIVE on {toast.platform}!
              </span>
            </div>
          ))}
        </div>
      )}
      {/* Debug: backend/DB connectivity so users know if notes & list persist */}
      {backendStatus !== "checking" && (
        <div
          role="status"
          aria-live="polite"
          style={{
            padding: "0.5rem 1rem",
            fontSize: "0.85rem",
            fontWeight: 500,
            textAlign: "center",
            background: backendStatus === "connected"
              ? "rgba(34, 197, 94, 0.2)"
              : "rgba(239, 68, 68, 0.2)",
            color: backendStatus === "connected"
              ? "rgb(34, 197, 94)"
              : "rgb(239, 68, 68)",
            borderBottom: `1px solid ${backendStatus === "connected" ? "rgb(34, 197, 94)" : "rgb(239, 68, 68)"}`,
          }}
        >
          {backendStatus === "connected"
            ? (backendStatusDetail?.starfireara_note
              ? `Database: Connected — read ok. Starfireara note: "${backendStatusDetail.starfireara_note.slice(0, 40)}${backendStatusDetail.starfireara_note.length > 40 ? "…" : ""}"`
              : "Database: Connected — read ok. Notes and list are saved to and loaded from the backend.")
            : (backendStatusDetail?.error
              ? `Database: Not connected — ${backendStatusDetail.error}`
              : typeof window !== "undefined" && /localhost|127\.0\.0\.1/.test(window.location?.hostname || "")
                ? "Database: Not connected — On localhost run 'python tools/serve_local.py' and open http://localhost:5173/fc/#/guest"
                : "Database: Not connected — Deploy /fc/api/ (status.php, get_notes.php, save_note.php) to a PHP host.")}
        </div>
      )}
      <header>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            flexWrap: "wrap",
            gap: "1rem",
          }}
        >
          <div>
            <h1>FavCreators</h1>
            <p className="subtitle">
              Ever watched a TikTok or an Instagram reel and wished you could get back to the creator or content?
              Ever wished you knew if your favorite streamer was live and on what platform?
            </p>
          </div>
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            <div className="auth-panel">
              <div className="auth-panel__header">
                <span>Account</span>
                {authUser ? (
                  <button className="auth-link" onClick={handleLogout}>
                    Sign out
                  </button>
                ) : (
                  isGuestMode ? (
                    <span className="auth-status">Guest mode</span>
                  ) : (
                    <button
                      className="btn-secondary"
                      style={{ marginTop: 8, marginBottom: 8 }}
                      onClick={() => {
                        const base = import.meta.env.BASE_URL || "/";
                        window.location.href = `${base}#/guest`;
                      }}
                    >
                      Continue as Guest
                    </button>
                  )
                )}
              </div>
              {authUser ? (
                <div className="auth-user">
                  <div className="auth-user__name">
                    {authUser.display_name || authUser.email || "Signed in"}
                  </div>
                  <div className="auth-user__meta">
                    {authUser.provider ? `Provider: ${authUser.provider}` : ""}
                  </div>
                </div>
              ) : (
                isGuestMode ? (
                  <div className="auth-actions">
                    <div className="auth-hint">
                      You are browsing as a guest. To save or customize, please log in or create an account.
                    </div>
                    <button
                      className="btn-secondary"
                      onClick={() => setShowLoginForm((prev) => !prev)}
                    >
                      {showLoginForm ? "Hide login" : "Login"}
                    </button>
                    {showLoginForm && (
                      <div className="login-form">
                        <button className="btn-google" onClick={handleGoogleLogin}>
                          Continue with Google
                        </button>
                        <div className="auth-divider">or use email</div>
                        <input
                          type="email"
                          placeholder="Email"
                          value={loginEmail}
                          onChange={(e) => setLoginEmail(e.target.value)}
                          className="w-full bg-[#111] bor text-white px-4 py-3 rounded-xl mb-2 focus:ring-2 focus:ring-[var(--pk-500)] outline-none"
                        />
                        <input
                          type="password"
                          placeholder="Password"
                          value={loginPassword}
                          onChange={(e) => setLoginPassword(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") handleLogin();
                          }}
                          className="w-full bg-[#111] bor text-white px-4 py-3 rounded-xl mb-3 focus:ring-2 focus:ring-[var(--pk-500)] outline-none"
                        />
                        <button
                          onClick={() => void handleLogin()}
                          disabled={authLoading}
                          className="glass-button w-full py-3 mb-2"
                        >
                          Email login
                        </button>
                        <div className="text-center">
                          <span className="text-xs text-white/40">new here?</span>
                        </div>
                        <input
                          type="text"
                          placeholder="Display name"
                          value={registerName}
                          onChange={(e) => setRegisterName(e.target.value)}
                          className="w-full bg-[#111] bor text-white px-4 py-3 rounded-xl mb-2 mt-2 focus:ring-2 focus:ring-[var(--pk-500)] outline-none"
                        />
                        <input
                          type="email"
                          placeholder="Email"
                          value={registerEmail}
                          onChange={(e) => setRegisterEmail(e.target.value)}
                        />
                        <input
                          type="password"
                          placeholder="Password (12+ chars incl. upper/lower/digit/symbol)"
                          value={registerPassword}
                          onChange={(e) => setRegisterPassword(e.target.value)}
                        />
                        <button
                          className="btn-secondary"
                          onClick={() => void handleRegister()}
                          disabled={authLoading}
                        >
                          Create account
                        </button>
                        {authError && <div className="auth-error">{authError}</div>}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="auth-actions">
                    <button className="btn-google" onClick={handleGoogleLogin}>
                      Continue with Google
                    </button>
                    <div className="auth-divider">or use email</div>
                    <input
                      type="email"
                      placeholder="Email"
                      value={loginEmail}
                      onChange={(e) => setLoginEmail(e.target.value)}
                    />
                    <input
                      type="password"
                      placeholder="Password"
                      value={loginPassword}
                      onChange={(e) => setLoginPassword(e.target.value)}
                    />
                    <button
                      className="btn-secondary"
                      onClick={() => void handleLogin()}
                      disabled={authLoading}
                    >
                      Email login
                    </button>
                    <div className="auth-divider">new here?</div>
                    <input
                      type="text"
                      placeholder="Display name"
                      value={registerName}
                      onChange={(e) => setRegisterName(e.target.value)}
                    />
                    <input
                      type="email"
                      placeholder="Email"
                      value={registerEmail}
                      onChange={(e) => setRegisterEmail(e.target.value)}
                    />
                    <input
                      type="password"
                      placeholder="Password (12+ chars incl. upper/lower/digit/symbol)"
                      value={registerPassword}
                      onChange={(e) => setRegisterPassword(e.target.value)}
                    />
                    <button
                      className="btn-secondary"
                      onClick={() => void handleRegister()}
                      disabled={authLoading}
                    >
                      Create account
                    </button>
                    {authError && <div className="auth-error">{authError}</div>}
                    <div className="auth-hint">
                      Guest mode stays available for browsing default creators.
                    </div>
                  </div>
                )
              )}
            </div>
            {!isGuestMode && (
              <>
                <button
                  onClick={handleSaveSettings}
                  title="Save settings to browser cookies"
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    padding: "0.5rem 1rem",
                    background: "var(--accent)",
                    color: "white",
                    border: "none",
                    borderRadius: "6px",
                    cursor: "pointer",
                    fontWeight: 500,
                  }}
                >
                  💾 Save
                </button>
                <button
                  onClick={handleExportSettings}
                  title="Export settings to JSON file"
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    padding: "0.5rem 1rem",
                    background: "var(--card-bg)",
                    color: "var(--text)",
                    border: "1px solid var(--border)",
                    borderRadius: "6px",
                    cursor: "pointer",
                  }}
                >
                  📤 Export
                </button>
              </>
            )}
            <button
              onClick={handleImportSettings}
              title="Import creators/settings from JSON file"
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                padding: "0.5rem 1rem",
                background: "var(--card-bg)",
                color: "var(--text)",
                border: "1px solid var(--border)",
                borderRadius: "6px",
                cursor: "pointer",
              }}
            >
              📥 Import Settings
            </button>
            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "0.5rem 1rem",
                background: "rgba(147, 51, 234, 0.1)",
                border: "1px solid rgba(147, 51, 234, 0.3)",
                borderRadius: "6px",
                cursor: "pointer",
                fontSize: "0.85rem",
                color: "#c4b5fd",
              }}
              title="Auto-expand extra notes/links section on all creator cards"
            >
              <input
                type="checkbox"
                checked={autoExpandSecondaryNotes}
                onChange={(e) => setAutoExpandSecondaryNotes(e.target.checked)}
                style={{ accentColor: "#9333ea" }}
              />
              Auto-expand notes
            </label>
          </div>
        </div>
      </header>
      <div className="avatar-status" aria-live="polite">
        <span>Real avatars fetched:</span>
        <strong>{realAvatarCount}</strong>
        <span> of </span>
        <strong>{creators.length}</strong>
      </div>

      {renderViewModeToggle()}

      {/* Live Summary - show live streams and recent stories */}
      <LiveSummary
        liveCreators={liveCreators}
        onToggle={() => setShowLiveSummary(!showLiveSummary)}
        isCollapsed={!showLiveSummary}
        isChecking={isCheckingLiveStatus}
        checkProgress={liveCheckProgress}
        selectedPlatform={selectedLivePlatform}
        onPlatformChange={setSelectedLivePlatform}
        lastUpdated={liveStatusLastUpdated}
        onRefresh={() => {
          setIsManualRefreshing(true);
          updateAllLiveStatuses();
        }}
        isRefreshing={isManualRefreshing}
      />

      {/* Ad Slot 1 - Below Live Summary */}
      <AdSense slot="9876543210" format="horizontal" className="my-4" />

      <div className="quick-add-group" style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <input
            className="quick-add-input"
            placeholder="Quick add: paste URL (e.g. tiktok.com/@user) or name:platforms"
            value={quickAddValue}
            onChange={(e) => setQuickAddValue(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && quickAddUpdate?.type !== "loading" && void handleQuickAdd()}
            disabled={quickAddUpdate?.type === "loading"}
          />
          <button
            className="quick-add-btn"
            onClick={() => void handleQuickAdd()}
            disabled={quickAddUpdate?.type === "loading"}
            style={quickAddUpdate?.type === "loading" ? { opacity: 0.6, cursor: "not-allowed" } : undefined}
          >
            {quickAddUpdate?.type === "loading" ? "Adding..." : "Quick Add"}
          </button>
        </div>
        {quickAddUpdate && (
          <div
            role="status"
            aria-live="polite"
            style={{
              fontSize: "0.875rem",
              padding: "6px 10px",
              borderRadius: "6px",
              background:
                quickAddUpdate.type === "success"
                  ? "rgba(34, 197, 94, 0.15)"
                  : quickAddUpdate.type === "loading"
                    ? "rgba(99, 102, 241, 0.15)"
                    : "rgba(239, 68, 68, 0.15)",
              border: `1px solid ${quickAddUpdate.type === "success"
                ? "rgba(34, 197, 94, 0.4)"
                : quickAddUpdate.type === "loading"
                  ? "rgba(99, 102, 241, 0.4)"
                  : "rgba(239, 68, 68, 0.4)"
                }`,
              color:
                quickAddUpdate.type === "success"
                  ? "#86efac"
                  : quickAddUpdate.type === "loading"
                    ? "#a5b4fc"
                    : "#fca5a5",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            {quickAddUpdate.type === "success" ? (
              "✓ "
            ) : quickAddUpdate.type === "loading" ? (
              <span
                style={{
                  display: "inline-block",
                  width: "14px",
                  height: "14px",
                  border: "2px solid rgba(99, 102, 241, 0.3)",
                  borderTopColor: "#a5b4fc",
                  borderRadius: "50%",
                  animation: "spin 1s linear infinite",
                }}
              />
            ) : (
              "⚠ "
            )}
            {quickAddUpdate.message}
          </div>
        )}
      </div>

      {/* My Favourite Creator Content - only for logged-in users */}
      {authUser && <MyLinkLists userId={authUser.id} />}

      {/* TEMPORARILY COMMENTED OUT - Incomplete LiveSummary feature from another agent */}
      {/* Live Summary - show live streams and recent stories */}
      {/* {liveCreators.length > 0 && (
        <LiveSummary
          liveCreators={liveCreators}
          onToggle={() => setShowLiveSummary(!showLiveSummary)}
          isCollapsed={!showLiveSummary}
        />
      )} */}

      {authUser?.provider === "admin" && (
        <div
          className="admin-followed-section"
          style={{
            marginBottom: "1rem",
            background: "var(--card-bg)",
            borderRadius: "8px",
            border: "1px solid var(--glass-border)",
            overflow: "hidden",
          }}
        >
          <button
            type="button"
            onClick={() => setShowAdminFollowed((prev) => !prev)}
            style={{
              width: "100%",
              padding: "10px 14px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              background: "rgba(255,255,255,0.04)",
              border: "none",
              color: "inherit",
              cursor: "pointer",
              fontSize: "0.95rem",
              fontWeight: 600,
            }}
          >
            <span>Creators followed by users on our platform</span>
            <span style={{ opacity: 0.7 }}>{showAdminFollowed ? "▼" : "▶"}</span>
          </button>
          {showAdminFollowed && (
            <div style={{ padding: "12px 14px" }}>
              <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "8px" }}>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => void fetchAllFollowedCreators()}
                  disabled={allFollowedLoading}
                  style={{ fontSize: "0.8rem" }}
                >
                  {allFollowedLoading ? "Loading…" : "Refresh"}
                </button>
              </div>
              {allFollowedLoading && allFollowedCreators.length === 0 ? (
                <div style={{ color: "var(--text-muted)" }}>Loading…</div>
              ) : !allFollowedLoading && allFollowedCreators.length === 0 ? (
                <div style={{ color: "var(--text-muted)" }}>No data yet.</div>
              ) : (
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.15)" }}>
                        <th style={{ textAlign: "left", padding: "8px" }}>Creator</th>
                        <th style={{ textAlign: "right", padding: "8px" }}># users following</th>
                        <th style={{ textAlign: "center", padding: "8px" }}>In guest list</th>
                        <th style={{ padding: "8px" }} />
                      </tr>
                    </thead>
                    <tbody>
                      {allFollowedCreators.map((row) => (
                        <tr key={row.creator_id} style={{ borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
                          <td style={{ padding: "8px" }}>{row.name}</td>
                          <td style={{ textAlign: "right", padding: "8px" }}>{row.follower_count}</td>
                          <td style={{ textAlign: "center", padding: "8px" }}>
                            {row.in_guest_list ? "✓ Yes" : "No"}
                          </td>
                          <td style={{ padding: "8px" }}>
                            {!row.in_guest_list && (
                              <div
                                title={`${row.follower_count} user(s) on our platform follow this creator. Changes to this profile could impact all of them.`}
                                style={{
                                  display: "inline-flex",
                                  alignItems: "center",
                                  gap: "6px",
                                  padding: "4px 10px",
                                  background: "rgba(234, 179, 8, 0.2)",
                                  border: "1px solid rgba(234, 179, 8, 0.5)",
                                  borderRadius: "6px",
                                  color: "#facc15",
                                  fontSize: "0.8rem",
                                  cursor: "help",
                                }}
                              >
                                ⚠ {row.follower_count} user{row.follower_count !== 1 ? "s" : ""} could be impacted
                              </div>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <div className="controls">
        <div
          className="search-bar"
          style={{ display: "flex", gap: "1rem", alignItems: "center" }}
        >
          <input
            type="text"
            placeholder="Search creators..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="filter-dropdown"
          >
            <option value="">All Categories</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>

          {/* View mode toggle */}
          <div
            className="view-mode-toggle"
            style={{
              display: "flex",
              gap: "4px",
              backgroundColor: "rgba(255,255,255,0.05)",
              padding: "4px",
              borderRadius: "8px",
            }}
          >
            <button
              type="button"
              className={`btn-secondary ${viewMode === "list" ? "view-active" : ""}`}
              onClick={() => setViewMode("list")}
              style={{ padding: "0.4rem 0.8rem", fontSize: "0.85rem" }}
            >
              List with headers
            </button>
            <button
              type="button"
              className={`btn-secondary ${viewMode === "dropdown" ? "view-active" : ""}`}
              onClick={() => setViewMode("dropdown")}
              style={{ padding: "0.4rem 0.8rem", fontSize: "0.85rem" }}
            >
              Dropdown filter
            </button>
          </div>
        </div>
        <div style={{ display: "flex", gap: "0.8rem" }}>
          <button
            className="btn-secondary"
            onClick={handleResetDatabase}
            title="Reset to official data"
          >
            🔄 Reset
          </button>
          <button
            className="btn-secondary"
            onClick={handleExport}
            title="Export to JSON"
          >
            📤 Export
          </button>
          <button
            className="btn-secondary"
            onClick={handleRefreshStatus}
            title="Check all live statuses"
          >
            📡 Check All Live Status
          </button>

          <button
            className="btn-secondary"
            onClick={handleImportSettings}
            title="Import JSON"
          >
            📥 Import
          </button>
          <button
            className="btn-secondary"
            onClick={handleAddCategory}
            title="Create New Category"
          >
            ➕ New Cat
          </button>
          <button
            className="btn-secondary"
            onClick={handleRenameCategory}
            title="Rename a Category"
          >
            🏷️ Rename Cat
          </button>
          <button
            className="btn-secondary"
            onClick={handleWipeAll}
            style={{ borderColor: '#ef4444', color: '#ef4444' }}
            title="Wipe Data"
          >
            ⚠️ Wipe
          </button>

          <button className="btn-add" onClick={() => setIsFormOpen(true)}>
            <span>+</span> Add Creator
          </button>
        </div>
      </div>


      {/* Main Content Area */}
      <div className="main-content-display" style={{ marginTop: "2rem" }}>
        {viewMode === "list" && (
          <>
            {/* List Mode with Headers */}
            {/* Pinned Creators Section */}
            {creators
              .filter(
                (c) =>
                  c.isPinned &&
                  (!categoryFilter || c.category === categoryFilter) &&
                  c.name
                    .toLowerCase()
                    .replace(/\s+/g, "")
                    .includes(searchQuery.toLowerCase().replace(/\s+/g, "")),
              )
              .map((creator) => (
                <div key={creator.id} className="creator-section-featured">
                  <CreatorCard
                    creator={creator}
                    onToggleFavorite={handleToggleFavorite}
                    onDelete={handleDeleteCreator}
                    onRemoveAccount={handleRemoveAccount}
                    onCheckStatus={handleCheckCreatorStatus}
                    onTogglePin={handleTogglePin}
                    onUpdateNote={handleUpdateNote}
                    onSaveNote={handleSaveNote}
                    onUpdateSecondaryNote={handleUpdateSecondaryNote}
                    onSaveSecondaryNote={handleSaveSecondaryNote}
                    onRefreshAvatar={handleRefreshAvatar}
                    onEditCreator={setEditingCreator}
                    autoExpandSecondaryNotes={autoExpandSecondaryNotes}
                  />
                </div>
              ))}

            {/* Other Creators Header - only show if there are unpinned creators matching filter */}
            {creators.some((c) =>
              !c.isPinned &&
              (!categoryFilter || c.category === categoryFilter) &&
              c.name.toLowerCase().replace(/\s+/g, "").includes(searchQuery.toLowerCase().replace(/\s+/g, ""))
            ) && (
              <h2
                id="other-creators-section"
                style={{
                  marginTop: "3rem",
                  marginBottom: "1.5rem",
                  color: "var(--text-muted)",
                  fontSize: "1.5rem",
                  borderBottom: "1px solid rgba(255,255,255,0.1)",
                  paddingBottom: "0.5rem",
                }}
              >
                Other Creators
              </h2>
            )}

            {/* Other Creators Grid */}
            <div className="creator-grid">
              {creators
                .filter(
                  (c) =>
                    !c.isPinned &&
                    (!categoryFilter || c.category === categoryFilter) &&
                    c.name
                      .toLowerCase()
                      .replace(/\s+/g, "")
                      .includes(searchQuery.toLowerCase().replace(/\s+/g, "")),
                )
                .map((creator) => (
                  <CreatorCard
                    key={creator.id}
                    creator={creator}
                    onToggleFavorite={handleToggleFavorite}
                    onDelete={handleDeleteCreator}
                    onRemoveAccount={handleRemoveAccount}
                    onCheckStatus={handleCheckCreatorStatus}
                    onTogglePin={handleTogglePin}
                    onUpdateNote={handleUpdateNote}
                    onSaveNote={handleSaveNote}
                    onUpdateSecondaryNote={handleUpdateSecondaryNote}
                    onSaveSecondaryNote={handleSaveSecondaryNote}
                    onRefreshAvatar={handleRefreshAvatar}
                    onEditCreator={setEditingCreator}
                    autoExpandSecondaryNotes={autoExpandSecondaryNotes}
                  />
                ))}
            </div>
          </>
        )}

        {viewMode === "dropdown" && (
          /* Dropdown Filter Mode */
          <div className="creator-grid">
            {creators
              .filter((c) => {
                const search = searchQuery.toLowerCase().replace(/\s+/g, "");
                const matchesSearch = c.name
                  .toLowerCase()
                  .replace(/\s+/g, "")
                  .includes(search);
                const matchesCategory =
                  !categoryFilter || c.category === categoryFilter;

                return matchesSearch && matchesCategory;
              })
              .map((creator) => (
                <CreatorCard
                  key={creator.id}
                  creator={creator}
                  onToggleFavorite={handleToggleFavorite}
                  onDelete={handleDeleteCreator}
                  onRemoveAccount={handleRemoveAccount}
                  onCheckStatus={handleCheckCreatorStatus}
                  onTogglePin={handleTogglePin}
                  onUpdateNote={handleUpdateNote}
                  onSaveNote={handleSaveNote}
                  onUpdateSecondaryNote={handleUpdateSecondaryNote}
                  onSaveSecondaryNote={handleSaveSecondaryNote}
                  onRefreshAvatar={handleRefreshAvatar}
                  onEditCreator={setEditingCreator}
                  autoExpandSecondaryNotes={autoExpandSecondaryNotes}
                />
              ))}
          </div>
        )}

        {viewMode === "table" && (() => {
          const filteredCreators = creators.filter((c) => {
            const search = searchQuery.toLowerCase().replace(/\s+/g, "");
            const matchesSearch = c.name
              .toLowerCase()
              .replace(/\s+/g, "")
              .includes(search);
            const matchesCategory =
              !categoryFilter || c.category === categoryFilter;
            return matchesSearch && matchesCategory;
          });
          const visibleIds = filteredCreators.map((c) => c.id);
          const allVisibleSelected =
            visibleIds.length > 0 && visibleIds.every((id) => selectedIds.has(id));
          return (
            <>
              {selectedIds.size > 0 && (
                <div
                  className="bulk-action-bar"
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "12px",
                    flexWrap: "wrap",
                    padding: "10px 14px",
                    marginBottom: "12px",
                    background: "var(--card-bg)",
                    borderRadius: "8px",
                    border: "1px solid var(--glass-border)",
                  }}
                >
                  <span style={{ fontWeight: 600 }}>
                    {selectedIds.size} selected
                  </span>
                  <select
                    className="filter-dropdown"
                    style={{ minWidth: "140px" }}
                    value={bulkApplyCategory}
                    onChange={(e) => setBulkApplyCategory(e.target.value)}
                  >
                    <option value="">— Category —</option>
                    {categories.map((cat) => (
                      <option key={cat} value={cat}>
                        {cat}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => {
                      if (bulkApplyCategory.trim()) handleBulkApplyCategory(bulkApplyCategory.trim());
                      else alert("Choose a category first.");
                    }}
                  >
                    Apply category
                  </button>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={handleBulkDelete}
                    style={{ borderColor: "rgba(239,68,68,0.5)", color: "#f87171" }}
                  >
                    Delete selected
                  </button>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={clearTableSelection}
                  >
                    Clear selection
                  </button>
                </div>
              )}
              <div className="table-container" style={{ overflowX: "auto" }}>
                <table className="creator-table">
                  <thead>
                    <tr>
                      <th style={{ width: "40px" }}>
                        <input
                          type="checkbox"
                          checked={allVisibleSelected}
                          onChange={() => toggleSelectAllInTable(visibleIds)}
                          title="Select all visible"
                        />
                      </th>
                      <th>Creator</th>
                      <th>Status</th>
                      <th>Channels</th>
                      <th>Note</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredCreators.map((creator) => (
                      <tr key={creator.id}>
                        <td>
                          <input
                            type="checkbox"
                            checked={selectedIds.has(creator.id)}
                            onChange={() => toggleTableSelect(creator.id)}
                          />
                        </td>
                        <td style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                          <img
                            src={creator.avatarUrl || buildFallbackAvatar(creator)}
                            alt=""
                            style={{ width: "32px", height: "32px", borderRadius: "50%", objectFit: "cover" }}
                            onError={(e) => {
                              const target = e.target as HTMLImageElement;
                              const candidates = buildAvatarCandidates(creator);
                              const currentIndex = Number(target.dataset.avatarIndex ?? "0");
                              const nextIndex = currentIndex + 1;
                              if (nextIndex < candidates.length) {
                                target.dataset.avatarIndex = String(nextIndex);
                                target.src = candidates[nextIndex];
                                return;
                              }
                              const fallback = buildFallbackAvatar(creator);
                              if (target.src !== fallback) target.src = fallback;
                            }}
                          />
                          <div style={{ fontWeight: 600 }}>{creator.name}</div>
                        </td>
                        <td>
                          {creator.isLive ? (
                            <span
                              className="badge-live"
                              title={`Live on: ${creator.accounts
                                .filter(acc => acc.isLive)
                                .map(acc => acc.platform.toUpperCase())
                                .join(', ') || 'Unknown'}`}
                            >
                              LIVE
                            </span>
                          ) : (
                            <span className="badge-offline">Offline</span>
                          )}
                        </td>
                        <td>
                          <div style={{ display: "flex", gap: "8px" }}>
                            {creator.accounts.map((acc) => (
                              <a
                                key={acc.id}
                                href={acc.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                title={`${acc.platform}: ${acc.username}`}
                              >
                                <img
                                  src={`https://www.google.com/s2/favicons?sz=32&domain=${new URL(acc.url).hostname}`}
                                  alt={acc.platform}
                                  style={{ width: "16px", height: "16px" }}
                                />
                              </a>
                            ))}
                          </div>
                        </td>
                        <td>
                          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                            <input
                              type="text"
                              value={creator.note || ""}
                              onChange={(e) => handleUpdateNote(creator.id, e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") {
                                  e.preventDefault();
                                  if (authUser) void handleSaveNote(creator.id, creator.note || "");
                                }
                              }}
                              placeholder="Add note..."
                              className="table-note-input"
                              style={{
                                background: "transparent",
                                border: "none",
                                color: "var(--text)",
                                fontSize: "0.85rem",
                                flex: 1,
                                minWidth: 0,
                                padding: "4px"
                              }}
                            />
                            <button
                              type="button"
                              className="btn-secondary"
                              onClick={() => void handleSaveNote(creator.id, creator.note || "")}
                              title="Save note to database"
                              style={{
                                padding: "4px 8px",
                                fontSize: "0.75rem",
                                whiteSpace: "nowrap"
                              }}
                            >
                              Save
                            </button>
                          </div>
                        </td>
                        <td>
                          <div style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" }}>
                            <button
                              type="button"
                              onClick={() => setEditingCreator(creator)}
                              className="btn-secondary"
                              title="Edit category, note & links"
                              style={{ padding: "4px 8px", fontSize: "0.75rem", whiteSpace: "nowrap" }}
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => handleToggleFavorite(creator.id)}
                              style={{ background: "none", border: "none", cursor: "pointer", fontSize: "1.2rem" }}
                            >
                              {creator.isFavorite ? "⭐" : "☆"}
                            </button>
                            <button
                              onClick={() => handleDeleteCreator(creator.id)}
                              style={{ background: "none", border: "none", cursor: "pointer", fontSize: "1.1rem" }}
                            >
                              🗑️
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          );
        })()}
      </div>

      {isFormOpen && (
        <CreatorForm
          onSave={(newCreator) => {
            handleSaveCreator(newCreator);
            // Add category if new
            const cat = newCreator.category;
            if (cat && !categories.includes(cat)) {
              setCategories(prev => [...prev, cat]);
            }
          }}
          onCancel={() => setIsFormOpen(false)}
          availableCategories={categories}
        />
      )}

      {editingCreator && (
        <EditCreatorModal
          creator={editingCreator}
          categories={categories}
          onSave={(updates) => {
            handleUpdateCreator(editingCreator.id, updates);
            setEditingCreator(null);
          }}
          onClose={() => setEditingCreator(null)}
        />
      )}

      {/* On-page API / DB query log for debugging */}
      <div
        style={{
          marginTop: "1.5rem",
          border: "1px solid rgba(255,255,255,0.2)",
          borderRadius: "8px",
          overflow: "hidden",
          background: "rgba(0,0,0,0.3)",
        }}
      >
        <button
          type="button"
          onClick={() => setApiLogOpen(!apiLogOpen)}
          style={{
            width: "100%",
            padding: "0.5rem 1rem",
            textAlign: "left",
            background: "rgba(255,255,255,0.06)",
            border: "none",
            color: "var(--text-2)",
            fontSize: "0.85rem",
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span>API / DB query log ({apiLogEntries.length})</span>
          <span style={{ fontSize: "0.75rem" }}>{apiLogOpen ? "▼" : "▶"}</span>
        </button>
        {apiLogOpen && (
          <div
            style={{
              maxHeight: "280px",
              overflowY: "auto",
              padding: "0.5rem",
              fontFamily: "ui-monospace, monospace",
              fontSize: "0.75rem",
              lineHeight: 1.5,
            }}
          >
            <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "0.25rem" }}>
              <button
                type="button"
                onClick={clearApiLog}
                style={{
                  padding: "0.2rem 0.5rem",
                  fontSize: "0.7rem",
                  background: "rgba(239,68,68,0.2)",
                  border: "1px solid rgba(239,68,68,0.5)",
                  borderRadius: "4px",
                  color: "#fca5a5",
                  cursor: "pointer",
                }}
              >
                Clear log
              </button>
            </div>
            {apiLogEntries.length === 0 ? (
              <div style={{ color: "var(--text-muted)" }}>No requests yet.</div>
            ) : (
              apiLogEntries.map((e) => (
                <div
                  key={e.id}
                  style={{
                    padding: "0.2rem 0",
                    borderBottom: "1px solid rgba(255,255,255,0.06)",
                    color: e.error ? "#fca5a5" : e.ok === false ? "#fcd34d" : "var(--text-2)",
                  }}
                >
                  <span style={{ color: "var(--text-muted)", marginRight: "0.5rem" }}>{e.time}</span>
                  <span style={{ fontWeight: 600 }}>{e.method}</span>{" "}
                  <span style={{ wordBreak: "break-all" }}>{e.url}</span>
                  {e.status != null && (
                    <span style={{ marginLeft: "0.5rem", color: e.ok ? "#86efac" : "#fcd34d" }}>
                      → {e.status} {e.ok ? "OK" : "FAIL"}
                    </span>
                  )}
                  {e.error != null && (
                    <span style={{ marginLeft: "0.5rem", color: "#fca5a5" }}>→ {e.error}</span>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </div>

      <footer
        style={{
          marginTop: "5rem",
          textAlign: "center",
          color: "var(--text-muted)",
          fontSize: "0.8rem",
        }}
      >
        <p>© 2026 FavCreators. Built with ❤️ for creators. v1.7.5-Production</p>
      </footer>
    </div>
  );
}

export default App;
