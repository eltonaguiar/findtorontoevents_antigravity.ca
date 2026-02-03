/**
 * Populate database with 200+ movies/TV series per year
 * Starting with 2025/2026, working backwards
 * Uses TMDB API for comprehensive metadata
 */

const axios = require('axios');
require('dotenv').config();

const TMDB_API_KEY = process.env.TMDB_API_KEY;
const TMDB_BASE_URL = 'https://api.themoviedb.org/3';
const API_URL = 'https://findtorontoevents.ca/MOVIESHOWS/api';

const MOVIES_PER_YEAR = 200;
const START_YEAR = 2026;
const END_YEAR = 2015; // Extended to 2015 for comprehensive catalog

/**
 * Discover popular movies for a specific year
 */
async function discoverMoviesByYear(year, page = 1) {
    try {
        const response = await axios.get(`${TMDB_BASE_URL}/discover/movie`, {
            params: {
                api_key: TMDB_API_KEY,
                language: 'en-US',
                sort_by: 'popularity.desc',
                include_adult: false,
                include_video: false,
                page: page,
                primary_release_year: year,
                'vote_count.gte': 10 // At least 10 votes for quality
            }
        });

        return response.data;
    } catch (error) {
        console.error(`Error discovering movies for ${year}:`, error.message);
        return { results: [], total_pages: 0 };
    }
}

/**
 * Discover popular TV series for a specific year
 */
async function discoverTVByYear(year, page = 1) {
    try {
        const response = await axios.get(`${TMDB_BASE_URL}/discover/tv`, {
            params: {
                api_key: TMDB_API_KEY,
                language: 'en-US',
                sort_by: 'popularity.desc',
                include_adult: false,
                page: page,
                first_air_date_year: year,
                'vote_count.gte': 10
            }
        });

        return response.data;
    } catch (error) {
        console.error(`Error discovering TV for ${year}:`, error.message);
        return { results: [], total_pages: 0 };
    }
}

/**
 * Get detailed info for movie/TV show
 */
async function getDetails(tmdbId, type = 'movie') {
    try {
        const endpoint = type === 'tv_series' ? `tv/${tmdbId}` : `movie/${tmdbId}`;
        const response = await axios.get(`${TMDB_BASE_URL}/${endpoint}`, {
            params: {
                api_key: TMDB_API_KEY,
                language: 'en-US',
                append_to_response: 'videos,images,credits'
            }
        });

        return response.data;
    } catch (error) {
        console.error(`Error getting details for ${type} ${tmdbId}:`, error.message);
        return null;
    }
}

/**
 * Add movie/TV to database
 */
async function addToDatabase(item, type = 'movie') {
    try {
        const details = await getDetails(item.id, type);

        if (!details) {
            return null;
        }

        // Prepare movie data
        const movieData = {
            title: type === 'movie' ? details.title : details.name,
            type: type,
            release_year: details.release_date ? new Date(details.release_date).getFullYear() :
                details.first_air_date ? new Date(details.first_air_date).getFullYear() : null,
            genre: details.genres ? details.genres.map(g => g.name).join(', ') : null,
            description: details.overview || null,
            tmdb_id: details.id,
            imdb_id: details.imdb_id || null,
            source: 'tmdb_bulk'
        };

        // Prepare thumbnails
        const thumbnails = [];
        if (details.poster_path) {
            thumbnails.push({
                url: `https://image.tmdb.org/t/p/w500${details.poster_path}`,
                source: 'tmdb',
                priority: 10,
                width: 500,
                height: 750
            });
        }

        if (details.backdrop_path) {
            thumbnails.push({
                url: `https://image.tmdb.org/t/p/w780${details.backdrop_path}`,
                source: 'tmdb',
                priority: 5,
                width: 780,
                height: 439
            });
        }

        // Prepare trailers
        const trailers = [];
        if (details.videos && details.videos.results) {
            const youtubeTrailers = details.videos.results
                .filter(v => v.site === 'YouTube' && (v.type === 'Trailer' || v.type === 'Teaser'))
                .slice(0, 3);

            youtubeTrailers.forEach((trailer, index) => {
                trailers.push({
                    youtube_id: trailer.key,
                    title: trailer.name,
                    priority: 10 - index,
                    source: 'tmdb',
                    view_count: 0
                });
            });
        }

        // Add to database
        const response = await axios.post(`${API_URL}/movies.php`, {
            ...movieData,
            thumbnails,
            trailers
        });

        return response.data;

    } catch (error) {
        if (error.response && error.response.status === 409) {
            // Already exists, skip
            return null;
        }
        throw error;
    }
}

/**
 * Populate year with movies and TV shows
 */
async function populateYear(year) {
    console.log(`\n${'='.repeat(60)}`);
    console.log(`Populating ${year}`);
    console.log('='.repeat(60));

    let added = 0;
    let skipped = 0;
    let errors = 0;
    const target = MOVIES_PER_YEAR;

    // Mix of movies and TV shows (70% movies, 30% TV)
    const movieTarget = Math.floor(target * 0.7);
    const tvTarget = target - movieTarget;

    // Add movies
    console.log(`\nAdding movies (target: ${movieTarget})...`);
    let page = 1;

    while (added < movieTarget && page <= 10) { // Max 10 pages
        const data = await discoverMoviesByYear(year, page);

        for (const movie of data.results) {
            if (added >= movieTarget) break;

            try {
                const result = await addToDatabase(movie, 'movie');

                if (result && result.id) {
                    added++;
                    console.log(`  [${added}/${target}] ✓ ${movie.title} (${year})`);
                } else {
                    skipped++;
                }

                // Rate limiting
                await new Promise(resolve => setTimeout(resolve, 300));

            } catch (error) {
                errors++;
                console.error(`  ✗ Error: ${movie.title} - ${error.message}`);
            }
        }

        page++;
    }

    // Add TV shows
    console.log(`\nAdding TV series (target: ${tvTarget})...`);
    page = 1;

    while (added < target && page <= 10) {
        const data = await discoverTVByYear(year, page);

        for (const tv of data.results) {
            if (added >= target) break;

            try {
                const result = await addToDatabase(tv, 'tv_series');

                if (result && result.id) {
                    added++;
                    console.log(`  [${added}/${target}] ✓ ${tv.name} (${year}) [TV]`);
                } else {
                    skipped++;
                }

                // Rate limiting
                await new Promise(resolve => setTimeout(resolve, 300));

            } catch (error) {
                errors++;
                console.error(`  ✗ Error: ${tv.name} - ${error.message}`);
            }
        }

        page++;
    }

    console.log(`\n${year} Summary:`);
    console.log(`  Added: ${added}`);
    console.log(`  Skipped: ${skipped}`);
    console.log(`  Errors: ${errors}`);

    return { added, skipped, errors };
}

/**
 * Main bulk population function
 */
async function bulkPopulate() {
    console.log('MovieShows Bulk Content Population');
    console.log('==================================\n');
    console.log(`Target: ${MOVIES_PER_YEAR} items per year`);
    console.log(`Years: ${START_YEAR} → ${END_YEAR}\n`);

    if (!TMDB_API_KEY) {
        console.error('✗ TMDB_API_KEY not set in .env file');
        process.exit(1);
    }

    const stats = {
        totalAdded: 0,
        totalSkipped: 0,
        totalErrors: 0
    };

    // Process each year
    for (let year = START_YEAR; year >= END_YEAR; year--) {
        const result = await populateYear(year);

        stats.totalAdded += result.added;
        stats.totalSkipped += result.skipped;
        stats.totalErrors += result.errors;

        // Pause between years
        console.log('\nPausing before next year...');
        await new Promise(resolve => setTimeout(resolve, 2000));
    }

    // Final summary
    console.log(`\n${'='.repeat(60)}`);
    console.log('BULK POPULATION COMPLETE');
    console.log('='.repeat(60));
    console.log(`Total Added: ${stats.totalAdded}`);
    console.log(`Total Skipped: ${stats.totalSkipped}`);
    console.log(`Total Errors: ${stats.totalErrors}`);
    console.log(`Years Processed: ${START_YEAR - END_YEAR + 1}`);
    console.log(`Average per Year: ${Math.round(stats.totalAdded / (START_YEAR - END_YEAR + 1))}`);
}

// Run if executed directly
if (require.main === module) {
    bulkPopulate()
        .then(() => {
            console.log('\n✓ Bulk population complete!');
            process.exit(0);
        })
        .catch(error => {
            console.error('\n✗ Bulk population failed:', error);
            process.exit(1);
        });
}

module.exports = { bulkPopulate, populateYear };
