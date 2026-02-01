import type { Creator } from "../types";

const DEFAULT_AVATAR_BASE = "https://api.dicebear.com/7.x/pixel-art/svg?seed=";

const buildAvatarSeed = (creator: Creator) => {
  const base = creator.name || creator.id || "favcreator";
  return encodeURIComponent(base.trim() || "favcreator");
};

export const buildFallbackAvatar = (creator: Creator): string =>
  `${DEFAULT_AVATAR_BASE}${buildAvatarSeed(creator)}`;

export const ensureAvatarUrl = (creator: Creator): Creator => {
  const hasUrl = typeof creator.avatarUrl === "string" && creator.avatarUrl.trim().length > 0;
  if (hasUrl) {
    return creator;
  }
  return {
    ...creator,
    avatarUrl: buildFallbackAvatar(creator),
  };
};

export const ensureAvatarForCreators = (creators: Creator[]): Creator[] =>
  creators.map((creator) => ensureAvatarUrl(creator));

const buildUnavatarCandidates = (creator: Creator): string[] => {
  const candidates: string[] = [];
  for (const account of creator.accounts ?? []) {
    const username = account.username?.trim();
    const url = account.url?.trim();

    if (username) {
      switch (account.platform) {
        case "youtube":
          candidates.push(`https://unavatar.io/youtube/${encodeURIComponent(username)}`);
          break;
        case "twitch":
          candidates.push(`https://unavatar.io/twitch/${encodeURIComponent(username)}`);
          break;
        case "tiktok":
          candidates.push(`https://unavatar.io/tiktok/${encodeURIComponent(username)}`);
          break;
        case "instagram":
          candidates.push(`https://unavatar.io/instagram/${encodeURIComponent(username)}`);
          break;
        default:
          break;
      }
    }

    if (url) {
      candidates.push(`https://unavatar.io/${encodeURIComponent(url)}`);
    }
  }
  return Array.from(new Set(candidates));
};

export const buildAvatarCandidates = (creator: Creator): string[] => {
  const trimmed = creator.avatarUrl?.trim();
  const candidates: string[] = [];
  if (trimmed) {
    candidates.push(trimmed);
  }
  candidates.push(...buildUnavatarCandidates(creator));
  candidates.push(buildFallbackAvatar(creator));
  return Array.from(new Set(candidates));
};
