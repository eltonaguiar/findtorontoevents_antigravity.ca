/**
 * Utility for tracking and retrieving creator status updates across platforms.
 * Extends the existing streamerLastSeen pattern to cover ALL content types
 * (posts, stories, streams, tweets, VODs, etc.) across 7+ platforms.
 *
 * Supported platforms: twitch, kick, tiktok, instagram, twitter, reddit, youtube, spotify
 * Supported types: post, story, stream, vod, tweet, comment, video, short, reel
 */

const API_BASE = import.meta.env.VITE_FC_API_BASE || '/fc';

export type StatusPlatform =
  | 'twitch'
  | 'kick'
  | 'tiktok'
  | 'instagram'
  | 'twitter'
  | 'reddit'
  | 'youtube'
  | 'spotify';

export type UpdateType =
  | 'post'
  | 'story'
  | 'stream'
  | 'vod'
  | 'tweet'
  | 'comment'
  | 'video'
  | 'short'
  | 'reel';

export interface CreatorStatusUpdate {
  id: number;
  creator_id: string;
  creator_name: string;
  platform: StatusPlatform;
  username: string;
  account_url: string;
  update_type: UpdateType;
  content_title: string;
  content_url: string;
  content_preview: string;
  content_thumbnail: string;
  content_id: string;
  is_live: boolean;
  viewer_count: number;
  like_count: number;
  comment_count: number;
  content_published_at: string | null;
  last_checked: string;
  last_updated: string;
  check_count: number;
  error_message: string;
}

export interface StatusUpdatesStats {
  total_tracked: number;
  unique_creators: number;
  platforms_tracked: number;
  currently_live: number;
  last_check_time: string | null;
}

export interface PlatformBreakdown {
  [platform: string]: {
    tracked: number;
    live: number;
  };
}

export interface StatusUpdatesResponse {
  ok: boolean;
  updates: CreatorStatusUpdate[];
  count: number;
  stats: StatusUpdatesStats;
  platform_breakdown: PlatformBreakdown;
  query: {
    creator_id: string | null;
    platform: string | null;
    user: string | null;
    type: string | null;
    live_only: boolean;
    since_hours: number;
    limit: number;
  };
  supported_platforms: string[];
}

export interface PlatformFetchResult {
  ok: boolean;
  platform: StatusPlatform;
  username: string;
  account_url: string;
  found: boolean;
  is_live: boolean;
  updates: Array<{
    update_type: UpdateType;
    content_title: string;
    content_url: string;
    content_preview?: string;
    content_thumbnail?: string;
    content_id?: string;
    is_live?: boolean;
    viewer_count?: number;
    like_count?: number;
    comment_count?: number;
    content_published_at?: string | null;
  }>;
  error: string | null;
  response_time_ms: number;
  saved?: boolean;
}

/**
 * Fetch stored status updates from the database.
 * Use this to display cached creator activity across all platforms.
 */
export async function getStatusUpdates(options?: {
  creator_id?: string;
  platform?: StatusPlatform;
  user?: string;
  type?: UpdateType;
  live_only?: boolean;
  since_hours?: number;
  limit?: number;
}): Promise<StatusUpdatesResponse> {
  const params = new URLSearchParams();

  if (options?.creator_id) params.append('creator_id', options.creator_id);
  if (options?.platform) params.append('platform', options.platform);
  if (options?.user) params.append('user', options.user);
  if (options?.type) params.append('type', options.type);
  if (options?.live_only) params.append('live_only', '1');
  if (options?.since_hours) params.append('since_hours', String(options.since_hours));
  if (options?.limit) params.append('limit', String(options.limit));

  const url = `${API_BASE}/public/api/status_updates.php?${params.toString()}`;

  const response = await fetch(url, {
    headers: { 'Accept': 'application/json' }
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch status updates: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

/**
 * Save a creator status update to the database.
 * Call this after detecting new content from a creator on any platform.
 */
export async function saveStatusUpdate(data: {
  creator_id: string;
  creator_name: string;
  platform: StatusPlatform;
  username: string;
  account_url?: string;
  update_type?: UpdateType;
  content_title?: string;
  content_url?: string;
  content_preview?: string;
  content_thumbnail?: string;
  content_id?: string;
  is_live?: boolean;
  viewer_count?: number;
  like_count?: number;
  comment_count?: number;
  content_published_at?: string;
  checked_by?: string;
}): Promise<{
  ok: boolean;
  processed?: number;
  results?: Array<{
    action: string;
    record_id: number;
    creator_id: string;
    platform: string;
    update_type: string;
  }>;
  errors?: Array<{ error: string }>;
}> {
  const url = `${API_BASE}/public/api/update_creator_status.php`;

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    },
    body: JSON.stringify({
      ...data,
      checked_by: data.checked_by || 'anonymous'
    })
  });

  if (!response.ok) {
    const errorText = await response.text();
    console.warn('[StatusUpdates] Failed to save:', errorText);
    return { ok: false, errors: [{ error: errorText }] };
  }

  return response.json();
}

/**
 * Batch save multiple status updates at once.
 */
export async function batchSaveStatusUpdates(
  updates: Array<{
    creator_id: string;
    creator_name: string;
    platform: StatusPlatform;
    username: string;
    account_url?: string;
    update_type?: UpdateType;
    content_title?: string;
    content_url?: string;
    is_live?: boolean;
    viewer_count?: number;
  }>,
  checked_by?: string
): Promise<{
  ok: boolean;
  processed?: number;
  errors?: Array<{ error: string; index: number }>;
}> {
  const url = `${API_BASE}/public/api/update_creator_status.php`;

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    },
    body: JSON.stringify({
      updates: updates.map(u => ({
        ...u,
        checked_by: checked_by || 'anonymous'
      }))
    })
  });

  if (!response.ok) {
    const errorText = await response.text();
    console.warn('[StatusUpdates] Batch save failed:', errorText);
    return { ok: false, errors: [{ error: errorText, index: -1 }] };
  }

  return response.json();
}

/**
 * Live-fetch the latest status for a creator on a specific platform.
 * This calls the actual platform APIs (Twitch, Kick, Reddit, etc.) in real-time.
 * Optionally saves the result to the DB for caching.
 */
export async function fetchPlatformStatus(
  platform: StatusPlatform,
  username: string,
  options?: {
    save?: boolean;
    creator_id?: string;
    creator_name?: string;
  }
): Promise<PlatformFetchResult> {
  const params = new URLSearchParams();
  params.append('platform', platform);
  params.append('user', username);

  if (options?.save) params.append('save', '1');
  if (options?.creator_id) params.append('creator_id', options.creator_id);
  if (options?.creator_name) params.append('creator_name', options.creator_name);

  const url = `${API_BASE}/public/api/fetch_platform_status.php?${params.toString()}`;

  const response = await fetch(url, {
    headers: { 'Accept': 'application/json' }
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch platform status: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get all recently active creators across all platforms.
 * Useful for a "Recent Activity" feed.
 */
export async function getRecentActivity(hours: number = 24): Promise<CreatorStatusUpdate[]> {
  try {
    const response = await getStatusUpdates({
      since_hours: hours,
      limit: 50
    });
    return response.ok ? response.updates : [];
  } catch (error) {
    console.warn('[StatusUpdates] Failed to get recent activity:', error);
    return [];
  }
}

/**
 * Get the latest update for a specific creator on a specific platform.
 * Returns null if no cached data exists.
 */
export async function getCreatorPlatformStatus(
  creator_id: string,
  platform: StatusPlatform
): Promise<CreatorStatusUpdate | null> {
  try {
    const response = await getStatusUpdates({
      creator_id,
      platform,
      limit: 1
    });
    return (response.ok && response.updates.length > 0) ? response.updates[0] : null;
  } catch (error) {
    console.warn('[StatusUpdates] Failed to get creator platform status:', error);
    return null;
  }
}

/**
 * Format the content published time into a human-readable relative string.
 */
export function formatContentAge(published_at: string | null): string {
  if (!published_at) return 'Unknown';

  const published = new Date(published_at);
  const now = new Date();
  const diffMs = now.getTime() - published.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);
  const diffWeeks = Math.floor(diffDays / 7);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffWeeks < 4) return `${diffWeeks}w ago`;
  return published.toLocaleDateString();
}

/**
 * Get a human-readable label for an update type.
 */
export function getUpdateTypeLabel(type: UpdateType): string {
  const labels: Record<UpdateType, string> = {
    post: 'Post',
    story: 'Story',
    stream: 'Live Stream',
    vod: 'VOD',
    tweet: 'Tweet',
    comment: 'Comment',
    video: 'Video',
    short: 'Short',
    reel: 'Reel'
  };
  return labels[type] || type;
}

/**
 * Get the platform's display name.
 */
export function getPlatformDisplayName(platform: StatusPlatform): string {
  const names: Record<StatusPlatform, string> = {
    twitch: 'Twitch',
    kick: 'Kick',
    tiktok: 'TikTok',
    instagram: 'Instagram',
    twitter: 'Twitter/X',
    reddit: 'Reddit',
    youtube: 'YouTube',
    spotify: 'Spotify'
  };
  return names[platform] || platform;
}

/**
 * Get the platform's profile URL from a username.
 */
export function getPlatformProfileUrl(platform: StatusPlatform, username: string): string {
  const templates: Record<StatusPlatform, string> = {
    twitch: `https://twitch.tv/${username}`,
    kick: `https://kick.com/${username}`,
    tiktok: `https://www.tiktok.com/@${username}`,
    instagram: `https://www.instagram.com/${username}/`,
    twitter: `https://x.com/${username}`,
    reddit: `https://www.reddit.com/user/${username}`,
    youtube: `https://www.youtube.com/@${username}`,
    spotify: `https://open.spotify.com/artist/${username}`
  };
  return templates[platform] || '#';
}
