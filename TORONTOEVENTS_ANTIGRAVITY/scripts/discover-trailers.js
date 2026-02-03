/**
 * Discover YouTube trailers for movies
 * Searches YouTube and adds multiple trailer options to database
 */

const axios = require('axios');

// You'll need to add your YouTube API key to .env
const YOUTUBE_API_KEY = process.env.YOUTUBE_API_KEY || '';
const YOUTUBE_SEARCH_URL = 'https://www.googleapis.com/youtube/v3/search';
const YOUTUBE_VIDEO_URL = 'https://www.googleapis.com/youtube/v3/videos';
const API_URL = 'https://findtorontoevents.ca/MOVIESHOWS/api';

/**
 * Search YouTube for movie trailers
 */
async function searchYouTubeTrailers(movieTitle, maxResults = 5) {
    if (!YOUTUBE_API_KEY) {
        console.warn('⚠ YouTube API key not set, skipping YouTube search');
        return [];
    }

    try {
        const searchQuery = `${movieTitle} official trailer`;

        const searchResponse = await axios.get(YOUTUBE_SEARCH_URL, {
            params: {
                part: 'snippet',
                q: searchQuery,
                type: 'video',
                maxResults: maxResults,
                key: YOUTUBE_API_KEY,
                videoCategoryId: '24', // Entertainment category
                order: 'relevance'
            }
        });

        const videoIds = searchResponse.data.items.map(item => item.id.videoId);

        if (videoIds.length === 0) {
            return [];
        }

        // Get detailed video information
        const videoResponse = await axios.get(YOUTUBE_VIDEO_URL, {
            params: {
                part: 'snippet,statistics,contentDetails',
                id: videoIds.join(','),
                key: YOUTUBE_API_KEY
            }
        });

        return videoResponse.data.items.map((video, index) => ({
            youtube_id: video.id,
            title: video.snippet.title,
            view_count: parseInt(video.statistics.viewCount) || 0,
            duration: parseDuration(video.contentDetails.duration),
            priority: maxResults - index, // Higher priority for more relevant results
            source: 'youtube_api'
        }));

    } catch (error) {
        console.error(`Error searching YouTube for "${movieTitle}":`, error.message);
        return [];
    }
}

/**
 * Parse ISO 8601 duration to seconds
 */
function parseDuration(isoDuration) {
    const match = isoDuration.match(/PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/);
    if (!match) return null;

    const hours = parseInt(match[1]) || 0;
    const minutes = parseInt(match[2]) || 0;
    const seconds = parseInt(match[3]) || 0;

    return hours * 3600 + minutes * 60 + seconds;
}

/**
 * Discover and add trailers for a specific movie
 */
async function discoverTrailersForMovie(movieId, movieTitle) {
    console.log(`\nDiscovering trailers for: ${movieTitle}`);

    const trailers = await searchYouTubeTrailers(movieTitle);

    if (trailers.length === 0) {
        console.log(`  No trailers found`);
        return 0;
    }

    let added = 0;

    for (const trailer of trailers) {
        try {
            await axios.post(`${API_URL}/trailers.php`, {
                movie_id: movieId,
                ...trailer
            });

            console.log(`  ✓ Added trailer: ${trailer.title.substring(0, 50)}... (${trailer.view_count.toLocaleString()} views)`);
            added++;

        } catch (error) {
            if (error.response && error.response.status === 409) {
                console.log(`  ⊘ Trailer already exists`);
            } else {
                console.error(`  ✗ Error adding trailer:`, error.message);
            }
        }
    }

    return added;
}

/**
 * Discover trailers for all movies without trailers
 */
async function discoverAllTrailers() {
    console.log('Discovering trailers for all movies...\n');

    try {
        // Get all movies
        const response = await axios.get(`${API_URL}/movies.php`);
        const movies = response.data.movies || [];

        let totalAdded = 0;

        for (const movie of movies) {
            // Skip if movie already has trailers
            if (movie.trailers && movie.trailers.length > 0) {
                console.log(`⊘ Skipping ${movie.title} (already has ${movie.trailers.length} trailers)`);
                continue;
            }

            const added = await discoverTrailersForMovie(movie.id, movie.title);
            totalAdded += added;

            // Rate limiting - wait 1 second between requests
            await new Promise(resolve => setTimeout(resolve, 1000));
        }

        console.log(`\n✓ Total trailers added: ${totalAdded}`);

    } catch (error) {
        console.error('Error discovering trailers:', error.message);
    }
}

// Run if executed directly
if (require.main === module) {
    const movieId = process.argv[2];
    const movieTitle = process.argv[3];

    if (movieId && movieTitle) {
        discoverTrailersForMovie(parseInt(movieId), movieTitle)
            .then(() => process.exit(0))
            .catch(error => {
                console.error('Fatal error:', error);
                process.exit(1);
            });
    } else {
        discoverAllTrailers()
            .then(() => process.exit(0))
            .catch(error => {
                console.error('Fatal error:', error);
                process.exit(1);
            });
    }
}

module.exports = { discoverTrailersForMovie, discoverAllTrailers, searchYouTubeTrailers };
