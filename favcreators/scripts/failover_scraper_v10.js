import axios from 'axios';

const PROXIES = [
    (url) => `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`,
    (url) => `https://r.jina.ai/${url}`,
    (url) => `https://corsproxy.io/?${encodeURIComponent(url)}`,
    (url) => `https://api.codetabs.com/v1/proxy?url=${encodeURIComponent(url)}`,
];

async function fetchViaProxy(targetUrl) {
    for (const proxyFn of PROXIES) {
        try {
            const proxyUrl = proxyFn(targetUrl);
            const response = await axios.get(proxyUrl, { timeout: 10000 });
            if (response.status === 200 && response.data) {
                // If it's a string, return it. If it's objects (like allorigins might return sometimes depending on headers), handle it.
                return typeof response.data === 'string' ? response.data : JSON.stringify(response.data);
            }
        } catch (e) {
            // console.warn(`Proxy failed: ${targetUrl}`);
        }
    }
    return null;
}

const CREATORS = [
    {
        name: "Adin Ross",
        accounts: [
            { platform: "kick", username: "adinross", url: "https://kick.com/adinross" },
            { platform: "youtube", username: "adinross", url: "https://youtube.com/@adinross" }
        ]
    },
    {
        name: "Starfireara",
        accounts: [
            { platform: "tiktok", username: "starfireara", url: "https://www.tiktok.com/@starfireara" }
        ]
    },
    {
        name: "Clavicular",
        accounts: [
            { platform: "kick", username: "clavicular", url: "https://kick.com/clavicular" },
            { platform: "twitch", username: "clavicular", url: "https://www.twitch.tv/clavicular" }
        ]
    },
    {
        name: "WTFPreston",
        accounts: [
            { platform: "tiktok", username: "wtfprestonlive", url: "https://www.tiktok.com/@wtfprestonlive" },
            { platform: "youtube", username: "wtfprestonlive", url: "https://www.youtube.com/@wtfprestonlive" }
        ]
    },
    {
        name: "Zarthestar",
        accounts: [
            { platform: "tiktok", username: "zarthestarcomedy", url: "https://www.tiktok.com/@zarthestarcomedy" },
            { platform: "instagram", username: "zar.the.star", url: "https://www.instagram.com/zar.the.star" }
        ]
    },
    {
        name: "Chavcriss",
        accounts: [
            { platform: "tiktok", username: "chavcriss", url: "https://www.tiktok.com/@chavcriss" },
            { platform: "instagram", username: "chavcriss", url: "https://www.instagram.com/chavcriss" },
            { platform: "youtube", username: "chavcriss", url: "https://www.youtube.com/@chavcriss" }
        ]
    }
];

async function scrapeAvatar(creator) {
    const results = {
        name: creator.name,
        foundUrl: null,
        method: null
    };

    // Method 1: Platform Specific APIs
    for (const acc of creator.accounts) {
        if (acc.platform === 'twitch') {
            try {
                const resp = await axios.get(`https://decapi.me/twitch/avatar/${acc.username}`);
                if (resp.status === 200 && resp.data.startsWith('http')) {
                    results.foundUrl = resp.data.trim();
                    results.method = "Twitch DecAPI";
                    return results;
                }
            } catch (e) { }
        }

        if (acc.platform === 'kick') {
            try {
                const apiContent = await fetchViaProxy(`https://kick.com/api/v2/channels/${acc.username}`);
                if (apiContent) {
                    const data = JSON.parse(apiContent);
                    const avatar = data.user?.profile_picture || data.user?.profile_pic;
                    if (avatar) {
                        results.foundUrl = avatar;
                        results.method = "Kick API (Proxy)";
                        return results;
                    }
                }
            } catch (e) { }
        }
    }

    // Method 2: Unavatar.io (Highly reliable public cache)
    for (const acc of creator.accounts) {
        let unavatarUrl = null;
        if (acc.platform === 'youtube') unavatarUrl = `https://unavatar.io/youtube/${acc.username}`;
        else if (acc.platform === 'twitch') unavatarUrl = `https://unavatar.io/twitch/${acc.username}`;
        else if (acc.platform === 'tiktok') unavatarUrl = `https://unavatar.io/tiktok/${acc.username}`;
        else if (acc.platform === 'instagram') unavatarUrl = `https://unavatar.io/instagram/${acc.username}`;

        if (unavatarUrl) {
            try {
                // Verify unavatar actually has something
                const resp = await axios.head(unavatarUrl, { timeout: 5000 });
                if (resp.status === 200) {
                    results.foundUrl = unavatarUrl;
                    results.method = `Unavatar (${acc.platform})`;
                    return results;
                }
            } catch (e) { }
        }
    }

    // Method 3: Scraping (Jina AI)
    for (const acc of creator.accounts) {
        try {
            const jinaUrl = `https://r.jina.ai/${acc.url}`;
            const html = await fetchViaProxy(acc.url); // This will try multiple proxies
            if (html) {
                const ogImageMatch = html.match(/<meta[^>]+(?:property|name)=["']og:image["'][^>]*content=["']([^"']+)["']/i);
                if (ogImageMatch && ogImageMatch[1]) {
                    results.foundUrl = ogImageMatch[1].split('?')[0];
                    results.method = `OG:Image Scrape (${acc.platform})`;
                    return results;
                }
            }
        } catch (e) { }
    }

    results.foundUrl = `https://api.dicebear.com/7.x/pixel-art/svg?seed=${encodeURIComponent(creator.name)}`;
    results.method = "Dicebear Fallback";
    return results;
}

async function run() {
    console.log("=== FAILOVER V10 AVATAR SCRAPER REPORT ===");
    console.log(`Timestamp: ${new Date().toISOString()}\n`);

    for (const creator of CREATORS) {
        process.stdout.write(`Scraping ${creator.name.padEnd(15)}... `);
        const res = await scrapeAvatar(creator);
        console.log(`DONE [via ${res.method}]`);
        console.log(`URL: ${res.foundUrl}\n`);
    }
}

run();
