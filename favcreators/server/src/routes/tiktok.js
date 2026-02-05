import { WebcastPushConnection } from "tiktok-live-connector";

/**
 * TikTok Live Status Route Handler
 * Uses tiktok-live-connector to check if a user is currently live
 */

// In-memory cache to avoid hammering TikTok
const cache = new Map();
const CACHE_TTL = 90000; // 90 seconds

/**
 * Check if a TikTok user is currently live using the WebCast API
 * @param {string} username - TikTok username (unique_id)
 * @returns {Promise<boolean>} - true if live, false if offline
 */
async function isTikTokUserLive(username) {
    try {
        const connection = new WebcastPushConnection(username, {
            processInitialData: false,
            enableExtendedGiftInfo: false,
            enableWebsocketUpgrade: false,
            requestPollingIntervalMs: 1000,
        });

        // The library will throw if the user is not live
        // We can use this to determine live status
        try {
            await connection.connect();
            await connection.disconnect();
            return true;
        } catch (connectError) {
            // If connection fails, user is likely offline
            if (connectError.message?.includes("LIVE has ended") ||
                connectError.message?.includes("not available")) {
                return false;
            }
            throw connectError;
        }
    } catch (error) {
        console.error(`Error checking live status for ${username}:`, error.message);
        return false;
    }
}

/**
 * GET /api/tiktok/live/:username
 * Returns the live status of a TikTok user
 */
export async function getTikTokLiveStatus(req, res) {
    const { username } = req.params;

    if (!username) {
        return res.status(400).json({ error: "Username is required" });
    }

    // Check cache first
    const cached = cache.get(username);
    if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
        return res.json({
            username,
            is_live: cached.isLive,
            cached: true,
            checked_at: new Date(cached.timestamp).toISOString(),
        });
    }

    // Check live status
    try {
        const isLive = await isTikTokUserLive(username);

        // Update cache
        cache.set(username, {
            isLive,
            timestamp: Date.now(),
        });

        res.json({
            username,
            is_live: isLive,
            cached: false,
            checked_at: new Date().toISOString(),
        });
    } catch (error) {
        console.error(`Failed to check live status for ${username}:`, error);
        res.status(500).json({
            error: "Failed to check live status",
            username,
            is_live: false,
        });
    }
}

/**
 * POST /api/tiktok/live/batch
 * Check multiple TikTok users at once
 * Body: { usernames: ["user1", "user2", ...] }
 */
export async function getTikTokLiveStatusBatch(req, res) {
    const { usernames } = req.body;

    if (!Array.isArray(usernames)) {
        return res.status(400).json({ error: "usernames must be an array" });
    }

    const results = await Promise.all(
        usernames.map(async (username) => {
            // Check cache first
            const cached = cache.get(username);
            if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
                return {
                    username,
                    is_live: cached.isLive,
                    cached: true,
                };
            }

            // Check live status
            try {
                const isLive = await isTikTokUserLive(username);
                cache.set(username, { isLive, timestamp: Date.now() });
                return { username, is_live: isLive, cached: false };
            } catch (error) {
                return { username, is_live: false, error: error.message };
            }
        })
    );

    res.json({ results, checked_at: new Date().toISOString() });
}

// Clear cache periodically to prevent memory leaks
setInterval(() => {
    const now = Date.now();
    for (const [username, data] of cache.entries()) {
        if (now - data.timestamp > CACHE_TTL * 2) {
            cache.delete(username);
        }
    }
}, CACHE_TTL);
