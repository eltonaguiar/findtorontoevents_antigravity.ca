/**
 * Sync Existing Movies to Database
 * Reads from current movies.json and populates database
 */

const fs = require('fs').promises;
const path = require('path');

const API_BASE = 'https://findtorontoevents.ca/MOVIESHOWS/api';

async function syncMoviesToDatabase() {
    console.log('🔄 Syncing Movies to Database\n');

    try {
        // Read current movies data
        const moviesPath = path.join(__dirname, '../MOVIESHOWS/data/movies.json');
        console.log(`📖 Reading: ${moviesPath}`);

        const moviesData = JSON.parse(await fs.readFile(moviesPath, 'utf8'));
        const movies = moviesData.movies || [];

        console.log(`✓ Found ${movies.length} movies\n`);

        let added = 0;
        let failed = 0;

        for (const movie of movies) {
            process.stdout.write(`Adding: ${movie.title.substring(0, 40).padEnd(40)} ... `);

            try {
                const response = await fetch(`${API_BASE}/movies.php`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        title: movie.title,
                        type: movie.type || 'movie',
                        release_year: movie.releaseYear || movie.release_year,
                        genre: movie.genre,
                        description: movie.description,
                        tmdb_id: movie.tmdbId || movie.tmdb_id,
                        imdb_id: movie.imdbId || movie.imdb_id,
                        source: movie.source || 'existing',
                        trailers: movie.trailers ? movie.trailers.map(t => ({
                            youtube_id: t.youtubeId || t.youtube_id || t.id,
                            title: t.title,
                            priority: t.priority || 0,
                            source: t.source || 'existing'
                        })) : [],
                        thumbnails: movie.thumbnails ? movie.thumbnails.map(t => ({
                            url: t.url,
                            source: t.source || 'existing',
                            priority: t.priority || 0
                        })) : []
                    })
                });

                if (response.ok) {
                    console.log('✓');
                    added++;
                } else {
                    const error = await response.text();
                    console.log(`✗ ${response.status}`);
                    failed++;
                }
            } catch (error) {
                console.log(`✗ ${error.message}`);
                failed++;
            }

            // Rate limit
            await new Promise(resolve => setTimeout(resolve, 100));
        }

        console.log(`\n✅ Sync complete!`);
        console.log(`   Added: ${added}`);
        console.log(`   Failed: ${failed}`);

    } catch (error) {
        console.error('❌ Sync failed:', error.message);
        process.exit(1);
    }
}

syncMoviesToDatabase();
