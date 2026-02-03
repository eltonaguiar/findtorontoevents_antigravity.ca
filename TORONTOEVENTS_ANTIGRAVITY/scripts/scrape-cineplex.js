/**
 * Scrape Cineplex Toronto theatres for currently playing movies
 * Uses Puppeteer to scrape movie listings
 */

const puppeteer = require('puppeteer');
const axios = require('axios');

const CINEPLEX_TORONTO_URL = 'https://www.cineplex.com/Showtimes/any-movie/cineplex-cinemas-yonge-dundas-and-vip?Date=';
const API_URL = 'https://findtorontoevents.ca/MOVIESHOWS/api/movies.php';

async function scrapeCineplexToronto() {
    console.log('Scraping Cineplex Toronto theatres...\n');

    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    try {
        const page = await browser.newPage();
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36');

        // Get today's date in the format Cineplex expects
        const today = new Date().toISOString().split('T')[0];
        const url = CINEPLEX_TORONTO_URL + today;

        console.log(`Fetching: ${url}`);
        await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });

        // Wait for movie listings to load
        await page.waitForSelector('.movie-details, .movie-title, [class*="movie"]', { timeout: 10000 }).catch(() => {
            console.log('Movie selector not found, trying alternative...');
        });

        // Extract movie information
        const movies = await page.evaluate(() => {
            const movieElements = document.querySelectorAll('[class*="movie"]');
            const results = [];

            movieElements.forEach(element => {
                const titleEl = element.querySelector('[class*="title"], h2, h3, .movie-name');
                const genreEl = element.querySelector('[class*="genre"], .genre');
                const ratingEl = element.querySelector('[class*="rating"], .rating');

                if (titleEl && titleEl.textContent.trim()) {
                    const title = titleEl.textContent.trim();

                    // Skip duplicates
                    if (!results.find(m => m.title === title)) {
                        results.push({
                            title: title,
                            genre: genreEl ? genreEl.textContent.trim() : null,
                            rating: ratingEl ? ratingEl.textContent.trim() : null
                        });
                    }
                }
            });

            return results;
        });

        console.log(`Found ${movies.length} movies\n`);

        // Add movies to database
        let added = 0;
        let skipped = 0;

        for (const movie of movies) {
            try {
                // Check if movie already exists
                const checkResponse = await axios.get(API_URL);
                const existingMovies = checkResponse.data.movies || [];
                const exists = existingMovies.some(m =>
                    m.title.toLowerCase() === movie.title.toLowerCase()
                );

                if (exists) {
                    console.log(`⊘ Skipped (exists): ${movie.title}`);
                    skipped++;
                    continue;
                }

                // Add new movie
                const response = await axios.post(API_URL, {
                    title: movie.title,
                    type: 'movie',
                    release_year: new Date().getFullYear(),
                    genre: movie.genre,
                    source: 'cineplex_toronto'
                });

                console.log(`✓ Added: ${movie.title}`);
                added++;

            } catch (error) {
                console.error(`✗ Error adding ${movie.title}:`, error.message);
            }
        }

        console.log(`\nSummary: ${added} added, ${skipped} skipped`);

    } catch (error) {
        console.error('Scraping error:', error.message);
    } finally {
        await browser.close();
    }
}

// Run if executed directly
if (require.main === module) {
    scrapeCineplexToronto()
        .then(() => process.exit(0))
        .catch(error => {
            console.error('Fatal error:', error);
            process.exit(1);
        });
}

module.exports = { scrapeCineplexToronto };
