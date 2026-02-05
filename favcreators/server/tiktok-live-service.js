import express from "express";
import { WebcastPushConnection } from "tiktok-live-connector";
import cors from "cors";

const app = express();
const PORT = process.env.PORT || 3001;

// Enable CORS for FavCreators frontend
app.use(cors());

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

        // Check if the user is live
        const isLive = await connection.getAvailableGifts()
            .then(() => true)
            .catch(() => false);

        // Alternative: Some versions have a direct isLive() method
        // const isLive = await connection.isLive();

        return isLive;
    } catch (error) {
        console.error(`Error checking live status for ${username}:`, error.message);
        return false;
    }
}

/**
 * GET /api/live-status/tiktok/:username
 * Returns the live status of a TikTok user
 */
app.get("/api/live-status/tiktok/:username", async (req, res) => {
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
});

/**
 * POST /api/live-status/tiktok/batch
 * Check multiple TikTok users at once
 * Body: { usernames: ["user1", "user2", ...] }
 */
app.post("/api/live-status/tiktok/batch", express.json(), async (req, res) => {
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
});

/**
 * GET /health
 * Health check endpoint
 */
app.get("/health", (req, res) => {
    res.json({ status: "ok", service: "tiktok-live-status", uptime: process.uptime() });
});

// Clear cache periodically to prevent memory leaks
setInterval(() => {
    const now = Date.now();
    for (const [username, data] of cache.entries()) {
        if (now - data.timestamp > CACHE_TTL * 2) {
            cache.delete(username);
        }
    }
}, CACHE_TTL);

app.listen(PORT, () => {
    console.log(`🚀 TikTok Live Status Service running on port ${PORT}`);
    console.log(`📡 Endpoint: http://localhost:${PORT}/api/live-status/tiktok/:username`);
});
