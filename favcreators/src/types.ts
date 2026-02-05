
export type Platform =
  | "youtube"
  | "tiktok"
  | "instagram"
  | "kick"
  | "twitch"
  | "spotify"
  | "other";

export interface SocialAccount {
  id: string;
  platform: Platform;
  username: string;
  url: string;
  followers?: string;
  isLive?: boolean;
  lastChecked?: number;
  /** User-specific: check this account for live status. Per-user preference. */
  checkLive?: boolean;
  /** Account status: active, not_found (404), banned, error, unknown */
  accountStatus?: 'active' | 'not_found' | 'banned' | 'error' | 'unknown';
  /** When the account status was last checked */
  statusLastChecked?: number;
  /** When to check this account again (for banned/404 accounts) */
  nextCheckDate?: number;
  /** TikTok: Has active story (posted in last 24h) */
  hasStory?: boolean;
  /** TikTok: Number of videos in current story */
  storyCount?: number;
  /** TikTok: When the story was posted (Unix timestamp) */
  storyPostedAt?: number;
  /** When the live stream started (Unix timestamp) */
  liveStartedAt?: number;
  /** Live stream title (if available from API) */
  streamTitle?: string;
  /** Current viewer count (if available from API) */
  viewerCount?: number;
  /** Method used to check live status (for debugging) */
  checkMethod?: string;
}

export interface Creator {
  id: string;
  category?: string; // Category of the creator
  name: string;
  bio: string;
  avatarUrl: string;
  accounts: SocialAccount[];
  isFavorite: boolean;
  addedAt: number;
  isLive?: boolean;
  reason?: string;
  note?: string;
  /** Secondary note: extended notes for links, favorite content, etc. */
  secondaryNote?: string;
  isPinned?: boolean;
  lastChecked?: number;
  tags?: string[];
  /** User-specific: treat as live streamer; which accounts to check is per-account checkLive. */
  isLiveStreamer?: boolean;
  /** Optional: Track which source the user selected for their avatar (e.g., "kick_api", "twitch_decapi") */
  selectedAvatarSource?: string;
}

export interface LiveCreator {
  creator: Creator;
  platform: string;
  accountUrl: string;
  status: 'live' | 'story';
  startedAt?: number;
  storyCount?: number;
  postedAt?: number;
}
