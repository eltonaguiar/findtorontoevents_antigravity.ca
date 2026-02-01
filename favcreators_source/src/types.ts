
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
  isPinned?: boolean;
  lastChecked?: number;
  tags?: string[];
}
