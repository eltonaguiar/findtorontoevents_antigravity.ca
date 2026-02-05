import type { SocialAccount } from "../types";
import {
    fetchTwitchAvatar,
    fetchKickAvatar,
    fetchUnavatar,
    scrapeAvatarFromHtml,
} from "./avatarGrabberV4";

/**
 * Avatar Option - Represents a single avatar URL from a specific source
 */
export interface AvatarOption {
    url: string;
    platform: string;
    source: string; // "kick_api", "twitch_decapi", "unavatar", "html_scrape"
    isValid: boolean;
    isPrimary?: boolean; // True if this is the currently selected avatar
}

/**
 * Fetch avatars from ALL social accounts (not just the first successful one)
 * Returns an array of avatar options for the user to choose from
 */
export async function fetchAllAvatars(
    accounts: SocialAccount[],
    _creatorName: string,
    currentAvatarUrl?: string,
): Promise<AvatarOption[]> {
    const avatarOptions: AvatarOption[] = [];
    const seenUrls = new Set<string>();
    const attempts: string[] = [];

    // Helper to add avatar if unique and valid
    const addAvatar = (
        url: string | null,
        platform: string,
        source: string,
    ) => {
        if (!url) return;

        // Normalize URL (remove query params for deduplication)
        const normalizedUrl = url.split("?")[0];

        // Skip if we've seen this URL before
        if (seenUrls.has(normalizedUrl)) return;

        // Skip default/placeholder avatars
        if (
            url.includes("dicebear.com") ||
            url.includes("ui-avatars.com") ||
            url.includes("default-avatar") ||
            url.includes("placeholder")
        ) {
            return;
        }

        seenUrls.add(normalizedUrl);
        avatarOptions.push({
            url,
            platform,
            source,
            isValid: true, // We'll validate later
            isPrimary: currentAvatarUrl === url,
        });
    };

    // Fetch avatars from each platform in parallel
    const fetchPromises = accounts.map(async (account) => {
        const { platform, username } = account;

        // Strategy 1: Platform-specific APIs
        if (platform === "twitch") {
            const twitchAvatar = await fetchTwitchAvatar(username, attempts);
            addAvatar(twitchAvatar, platform, "twitch_decapi");
        }

        if (platform === "kick") {
            const kickAvatar = await fetchKickAvatar(username, attempts);
            addAvatar(kickAvatar, platform, "kick_api");
        }

        // Strategy 2: Unavatar service (supports multiple platforms)
        const unavatarResult = await fetchUnavatar(platform, username, attempts);
        addAvatar(unavatarResult, platform, "unavatar");

        // Strategy 3: HTML scraping (fallback)
        if (account.url) {
            const scrapedAvatar = await scrapeAvatarFromHtml(
                account.url,
                platform,
                attempts,
            );
            addAvatar(scrapedAvatar, platform, "html_scrape");
        }
    });

    // Wait for all fetches to complete
    await Promise.allSettled(fetchPromises);

    // Validate all avatar URLs
    const validationPromises = avatarOptions.map(async (option) => {
        try {
            const response = await fetch(option.url, { method: "HEAD" });
            option.isValid = response.ok;
        } catch {
            option.isValid = false;
        }
    });

    await Promise.allSettled(validationPromises);

    // Filter out invalid avatars
    const validAvatars = avatarOptions.filter((opt) => opt.isValid);

    // Sort: Primary first, then by platform priority
    const platformPriority = ["kick", "twitch", "youtube", "tiktok", "instagram"];
    validAvatars.sort((a, b) => {
        if (a.isPrimary && !b.isPrimary) return -1;
        if (!a.isPrimary && b.isPrimary) return 1;

        const aPriority = platformPriority.indexOf(a.platform);
        const bPriority = platformPriority.indexOf(b.platform);
        return aPriority - bPriority;
    });

    return validAvatars;
}

/**
 * Fetch a single best avatar from all accounts (wrapper for backward compatibility)
 */
export async function fetchBestAvatar(
    accounts: SocialAccount[],
    creatorName: string,
): Promise<string | null> {
    const avatars = await fetchAllAvatars(accounts, creatorName);
    return avatars.length > 0 ? avatars[0].url : null;
}
