/**
 * Utility for tracking and retrieving streamer "last seen" status.
 * This allows faster UI updates by using cached live status from other users' checks.
 */

const API_BASE = import.meta.env.VITE_FC_API_BASE || '/fc';

export interface StreamerLastSeen {
  id: number;
  creator_id: string;
  creator_name: string;
  platform: string;
  username: string;
  account_url: string;
  is_live: boolean;
  last_seen_online: string | null;
  last_checked: string;
  stream_title: string;
  viewer_count: number;
  check_count: number;
  first_seen_by: string;
}

export interface LastSeenStats {
  total_tracked: number;
  currently_live: number;
  unique_creators: number;
  last_check_time: string | null;
}

export interface LastSeenResponse {
  ok: boolean;
  streamers: StreamerLastSeen[];
  stats: LastSeenStats;
  query: {
    creator_id: string | null;
    platform: string | null;
    live_only: boolean;
    since_minutes: number;
  };
}

/**
 * Fetch recently checked streamers from the last_seen tracking database.
 * Use this to quickly show "likely live" indicators before doing live checks.
 */
export async function getStreamerLastSeen(options?: {
  creator_id?: string;
  platform?: string;
  live_only?: boolean;
  since_minutes?: number;
}): Promise<LastSeenResponse> {
  const params = new URLSearchParams();
  
  if (options?.creator_id) params.append('creator_id', options.creator_id);
  if (options?.platform) params.append('platform', options.platform);
  if (options?.live_only) params.append('live_only', '1');
  if (options?.since_minutes) params.append('since_minutes', String(options.since_minutes));
  
  const url = `${API_BASE}/public/api/get_streamer_last_seen.php?${params.toString()}`;
  
  const response = await fetch(url, {
    headers: {
      'Accept': 'application/json'
    }
  });
  
  if (!response.ok) {
    throw new Error(`Failed to fetch last seen: ${response.status} ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Update the last_seen tracking when a streamer is checked.
 * Call this after checking live status to share the result with other users.
 */
export async function updateStreamerLastSeen(data: {
  creator_id: string;
  creator_name: string;
  platform: string;
  username: string;
  account_url?: string;
  is_live: boolean;
  stream_title?: string;
  viewer_count?: number;
  checked_by?: string;
}): Promise<{
  ok: boolean;
  action?: string;
  record_id?: number;
  error?: string;
}> {
  const url = `${API_BASE}/public/api/update_streamer_last_seen.php`;
  
  const payload = {
    ...data,
    checked_by: data.checked_by || 'anonymous'
  };
  
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  
  if (!response.ok) {
    const errorText = await response.text();
    console.warn('[LastSeen] Failed to update:', errorText);
    return { ok: false, error: errorText };
  }
  
  return response.json();
}

/**
 * Batch update multiple streamers' last_seen status.
 * More efficient for syncing many streamers at once.
 */
export async function batchUpdateStreamerLastSeen(
  updates: Array<{
    creator_id: string;
    creator_name: string;
    platform: string;
    username: string;
    account_url?: string;
    is_live: boolean;
    stream_title?: string;
    viewer_count?: number;
  }>,
  checked_by?: string
): Promise<{
  ok: boolean;
  processed?: number;
  total_received?: number;
  results?: Array<{
    creator_id: string;
    platform: string;
    action: string;
    is_live: boolean;
  }>;
  error?: string;
}> {
  const url = `${API_BASE}/public/api/batch_update_streamer_last_seen.php`;
  
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    },
    body: JSON.stringify({
      updates,
      checked_by: checked_by || 'anonymous'
    })
  });
  
  if (!response.ok) {
    const errorText = await response.text();
    console.warn('[LastSeen] Batch update failed:', errorText);
    return { ok: false, error: errorText };
  }
  
  return response.json();
}

/**
 * Check if a streamer was recently seen live based on last_seen tracking.
 * Returns the cached status if available and recent, null otherwise.
 */
export async function getCachedLiveStatus(
  creator_id: string,
  platform: string,
  max_age_minutes: number = 15
): Promise<StreamerLastSeen | null> {
  try {
    const response = await getStreamerLastSeen({
      creator_id,
      platform,
      since_minutes: max_age_minutes
    });
    
    if (response.ok && response.streamers.length > 0) {
      return response.streamers[0];
    }
    
    return null;
  } catch (error) {
    console.warn('[LastSeen] Failed to get cached status:', error);
    return null;
  }
}

/**
 * Get all currently live streamers from the cache.
 * Useful for showing "Trending Live" or similar features.
 */
export async function getCurrentlyLiveStreamers(): Promise<StreamerLastSeen[]> {
  try {
    const response = await getStreamerLastSeen({
      live_only: true,
      since_minutes: 60 // Last hour
    });
    
    if (response.ok) {
      return response.streamers;
    }
    
    return [];
  } catch (error) {
    console.warn('[LastSeen] Failed to get live streamers:', error);
    return [];
  }
}

/**
 * Format the "last seen" time into a human-readable string.
 */
export function formatLastSeen(last_seen_online: string | null): string {
  if (!last_seen_online) return 'Never';
  
  const lastSeen = new Date(last_seen_online);
  const now = new Date();
  const diffMs = now.getTime() - lastSeen.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);
  
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

/**
 * Determine if we should skip a live check based on recent last_seen data.
 * Returns true if we have recent data indicating the streamer is NOT live.
 */
export function shouldSkipLiveCheck(
  lastSeen: StreamerLastSeen | null,
  offline_cache_minutes: number = 10
): boolean {
  if (!lastSeen) return false;
  
  // If marked as live recently, we might want to verify
  if (lastSeen.is_live) return false;
  
  // Check if we checked recently and they were offline
  const lastChecked = new Date(lastSeen.last_checked);
  const now = new Date();
  const diffMins = (now.getTime() - lastChecked.getTime()) / 60000;
  
  return diffMins < offline_cache_minutes;
}