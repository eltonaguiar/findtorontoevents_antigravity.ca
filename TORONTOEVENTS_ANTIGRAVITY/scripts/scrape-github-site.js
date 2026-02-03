/**
 * UPDATE #8: Scrape Existing MovieShows Site and Populate Database
 * Extracts movies from the live site and adds to database
 */

const cheerio = require('cheerio');

const SITE_URL = 'https://eltonaguiar.github.io/MOVIESHOWS2_CURSORNOSCROLLINGBUG/?v37test';
const API_BASE = 'https://findtorontoevents.ca/MOVIESHOWS/api';

async function scrapeAndPopulate() {
    console.log('🔍 Scraping MovieShows site...\n');

    try {
        const response = await fetch(SITE_URL);
        const html = await response.text();
        const $ = cheerio.load(html);

        // Extract movie data from the page
        const movies = [];

        // Look for YouTube embeds
        $('iframe[src*="youtube.com/embed"]').each((i, elem) => {
            const src = $(elem).attr('src');
            const youtubeId = src.match(/embed\/([^?]+)/)?.[1];

            if (youtubeId) {
                // Try to find associated title/metadata
                const container = $(elem).closest('[data-title], .movie, .video-container');
                const title = container.attr('data-title') ||
                    container.find('h1, h2, h3, .title').first().text().trim() ||
                    `Movie ${i + 1}`;

                const genre = container.attr('data-genre') ||
                    container.find('.genre').text().trim() ||
                    'Unknown';

                const year = container.attr('data-year') ||
                    container.find('.year').text().trim() ||
                    new Date().getFullYear();

                movies.push({
                    title,
                    type: 'movie',
                    release_year: parseInt(year) || new Date().getFullYear(),
                    genre,
                    source: 'scraped_github',
                    trailers: [{
                        youtube_id: youtubeId,
                        title: `${title} Trailer`,
                        priority: 10,
                        source: 'scraped'
                    }]
                });
            }
        });

        // Also check for data in script tags
        $('script').each((i, elem) => {
            const scriptContent = $(elem).html();

            // Look for movie data patterns
            const movieMatches = scriptContent?.matchAll(/\{[^}]*title[^}]*youtube[^}]*\}/g);
            if (movieMatches) {
                for (const match of movieMatches) {
                    try {
                        const movieData = JSON.parse(match[0]);
                        if (movieData.title && movieData.youtubeId) {
                            movies.push({
                                title: movieData.title,
                                type: movieData.type || 'movie',
                                release_year: movieData.releaseYear || movieData.year || new Date().getFullYear(),
                                genre: movieData.genre || 'Unknown',
                                description: movieData.description,
                                source: 'scraped_github',
                                trailers: [{
                                    youtube_id: movieData.youtubeId,
                                    title: movieData.trailerTitle || `${movieData.title} Trailer`,
                                    priority: 10,
                                    source: 'scraped'
                                }],
                                thumbnails: movieData.thumbnail ? [{
                                    url: movieData.thumbnail,
                                    source: 'scraped',
                                    priority: 10
                                }] : []
                            });
                        }
                    } catch (e) {
                        // Skip invalid JSON
                    }
                }
            }
        });

        console.log(`✓ Found ${movies.length} movies\n`);

        if (movies.length === 0) {
            console.log('⚠️  No movies found. Trying alternative extraction...\n');

            // Fallback: extract any YouTube URLs
            const youtubeUrls = html.match(/youtube\.com\/embed\/([a-zA-Z0-9_-]+)/g) || [];
            youtubeUrls.forEach((url, i) => {
                const youtubeId = url.match(/embed\/([a-zA-Z0-9_-]+)/)?.[1];
                if (youtubeId) {
                    movies.push({
                        title: `Movie ${i + 1}`,
                        type: 'movie',
                        release_year: new Date().getFullYear(),
                        genre: 'Unknown',
                        source: 'scraped_github_fallback',
                        trailers: [{
                            youtube_id: youtubeId,
                            title: `Trailer ${i + 1}`,
                            priority: 10,
                            source: 'scraped'
                        }]
                    });
                }
            });

            console.log(`✓ Extracted ${movies.length} YouTube videos\n`);
        }

        // Add to database
        let added = 0;
        let failed = 0;

        for (const movie of movies) {
            process.stdout.write(`${movie.title.substring(0, 40).padEnd(40)} ... `);

            try {
                const response = await fetch(`${API_BASE}/movies.php`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(movie)
                });

                if (response.ok) {
                    console.log('✓');
                    added++;
                } else {
                    const error = await response.text();
                    console.log(`✗ ${response.status}`);
                    if (response.status !== 404) {
                        console.log(`  ${error.substring(0, 100)}`);
                    }
                    failed++;
                }
            } catch (error) {
                console.log(`✗ ${error.message}`);
                failed++;
            }

            await new Promise(r => setTimeout(r, 100));
        }

        console.log(`\n✅ Scraping complete!`);
        console.log(`   Added: ${added}`);
        console.log(`   Failed: ${failed}`);

    } catch (error) {
        console.error('❌ Scraping failed:', error.message);
        process.exit(1);
    }
}

scrapeAndPopulate();
