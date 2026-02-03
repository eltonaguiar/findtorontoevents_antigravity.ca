/**
 * UPDATE #62: YouTube Trailer Service
 * Search and embed YouTube trailers
 */

const YOUTUBE_API_KEY = 'YOUR_API_KEY'; // User should add their key
const YOUTUBE_API_BASE = 'https://www.googleapis.com/youtube/v3';

interface YouTubeVideo {
    id: { videoId: string };
    snippet: {
        title: string;
        description: string;
        thumbnails: {
            default: { url: string };
            medium: { url: string };
            high: { url: string };
        };
    };
}

class YouTubeService {
    private apiKey: string;

    constructor(apiKey: string = YOUTUBE_API_KEY) {
        this.apiKey = apiKey;
    }

    async searchTrailers(movieTitle: string, year?: number): Promise<YouTubeVideo[]> {
        const query = year ? `${movieTitle} ${year} official trailer` : `${movieTitle} official trailer`;

        const url = new URL(`${YOUTUBE_API_BASE}/search`);
        url.searchParams.set('part', 'snippet');
        url.searchParams.set('q', query);
        url.searchParams.set('type', 'video');
        url.searchParams.set('maxResults', '5');
        url.searchParams.set('key', this.apiKey);

        const response = await fetch(url.toString());
        if (!response.ok) {
            throw new Error('YouTube API error');
        }

        const data = await response.json();
        return data.items || [];
    }

    getEmbedUrl(videoId: string): string {
        return `https://www.youtube.com/embed/${videoId}?autoplay=1&rel=0`;
    }

    getThumbnailUrl(videoId: string, quality: 'default' | 'medium' | 'high' = 'high'): string {
        const qualityMap = {
            default: 'default',
            medium: 'mqdefault',
            high: 'hqdefault'
        };
        return `https://img.youtube.com/vi/${videoId}/${qualityMap[quality]}.jpg`;
    }

    getWatchUrl(videoId: string): string {
        return `https://www.youtube.com/watch?v=${videoId}`;
    }
}

export const youtubeService = new YouTubeService();

/**
 * Fallback: Extract YouTube ID from various URL formats
 */
export function extractYouTubeId(url: string): string | null {
    const patterns = [
        /(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)/,
        /youtube\.com\/embed\/([^&\n?#]+)/,
        /youtube\.com\/v\/([^&\n?#]+)/
    ];

    for (const pattern of patterns) {
        const match = url.match(pattern);
        if (match && match[1]) {
            return match[1];
        }
    }

    return null;
}
