const mysql = require('mysql2/promise');
const https = require('https');

const DB_CONFIG = {
    host: 'mysql.50webs.com',
    user: 'ejaguiar1_tvmoviestrailers',
    password: 'virus2016',
    database: 'ejaguiar1_tvmoviestrailers'
};

const TMDB_API_KEY = ''; // Will need to get this from environment or user

// TMDB API helper
function fetchTMDB(url) {
    return new Promise((resolve, reject) => {
        https.get(url, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                try {
                    resolve(JSON.parse(data));
                } catch (e) {
                    reject(e);
                }
            });
        }).on('error', reject);
    });
}

async function inspectDatabase() {
    const connection = await mysql.createConnection(DB_CONFIG);

    try {
        console.log('=== DATABASE INSPECTION ===\n');

        // Get tables
        const [tables] = await connection.query('SHOW TABLES');
        console.log('Tables:', tables);

        // Get movies table structure
        const [columns] = await connection.query('DESCRIBE movies');
        console.log('\nMovies table structure:');
        columns.forEach(col => {
            console.log(`  - ${col.Field} (${col.Type}) ${col.Null} ${col.Key}`);
        });

        // Get current counts
        const [counts] = await connection.query('SELECT COUNT(*) as total FROM movies');
        console.log(`\nTotal records: ${counts[0].total}`);

        // Get counts by year and type
        const [yearCounts] = await connection.query(`
      SELECT release_year, type, COUNT(*) as count 
      FROM movies 
      GROUP BY release_year, type 
      ORDER BY release_year DESC
    `);
        console.log('\nCounts by year and type:');
        yearCounts.forEach(row => {
            console.log(`  ${row.release_year}: ${row.type} = ${row.count}`);
        });

        // Sample data
        const [samples] = await connection.query('SELECT * FROM movies ORDER BY release_year DESC LIMIT 5');
        console.log('\nSample records:');
        samples.forEach(row => {
            console.log(`  ${row.id}: ${row.title} (${row.type}, ${row.release_year})`);
        });

    } finally {
        await connection.end();
    }
}

async function populateDatabase(apiKey) {
    const connection = await mysql.createConnection(DB_CONFIG);

    try {
        console.log('\n=== POPULATING DATABASE ===\n');

        const TARGET_PER_YEAR = 100; // 100 movies + 100 shows per year
        const START_YEAR = 2027;
        const END_YEAR = 2015;

        for (let year = START_YEAR; year >= END_YEAR; year--) {
            console.log(`\nProcessing year ${year}...`);

            // Check existing counts for this year
            const [existing] = await connection.query(
                'SELECT type, COUNT(*) as count FROM movies WHERE release_year = ? GROUP BY type',
                [year]
            );

            const existingMovies = existing.find(r => r.type === 'movie')?.count || 0;
            const existingShows = existing.find(r => r.type === 'tv')?.count || 0;

            console.log(`  Existing: ${existingMovies} movies, ${existingShows} shows`);

            // Fetch movies
            if (existingMovies < TARGET_PER_YEAR) {
                const needed = TARGET_PER_YEAR - existingMovies;
                console.log(`  Fetching ${needed} movies...`);
                await fetchAndInsert(connection, 'movie', year, needed, apiKey);
            }

            // Fetch TV shows
            if (existingShows < TARGET_PER_YEAR) {
                const needed = TARGET_PER_YEAR - existingShows;
                console.log(`  Fetching ${needed} TV shows...`);
                await fetchAndInsert(connection, 'tv', year, needed, apiKey);
            }
        }

        console.log('\n=== POPULATION COMPLETE ===');

    } finally {
        await connection.end();
    }
}

async function fetchAndInsert(connection, type, year, count, apiKey) {
    const endpoint = type === 'movie' ? 'discover/movie' : 'discover/tv';
    const yearParam = type === 'movie' ? 'primary_release_year' : 'first_air_date_year';

    let inserted = 0;
    let page = 1;

    while (inserted < count && page <= 50) { // TMDB limits to 500 pages
        const url = `https://api.themoviedb.org/3/${endpoint}?api_key=${apiKey}&${yearParam}=${year}&page=${page}&sort_by=popularity.desc`;

        try {
            const data = await fetchTMDB(url);

            if (!data.results || data.results.length === 0) break;

            for (const item of data.results) {
                if (inserted >= count) break;

                // Check if already exists
                const [existing] = await connection.query(
                    'SELECT id FROM movies WHERE tmdb_id = ? AND type = ?',
                    [item.id, type]
                );

                if (existing.length > 0) continue;

                const title = item.title || item.name;
                const releaseYear = year;
                const description = item.overview;
                const tmdbId = item.id;
                const genre = item.genre_ids ? item.genre_ids.join(',') : null;
                const rating = item.vote_average || null;

                await connection.query(
                    `INSERT INTO movies (title, type, genre, description, release_year, imdb_rating, tmdb_id) 
           VALUES (?, ?, ?, ?, ?, ?, ?)`,
                    [title, type, genre, description, releaseYear, rating, tmdbId]
                );

                inserted++;
                if (inserted % 10 === 0) {
                    process.stdout.write(`    Inserted ${inserted}/${count}...\r`);
                }
            }

            page++;

            // Rate limiting
            await new Promise(resolve => setTimeout(resolve, 250));

        } catch (error) {
            console.error(`    Error fetching page ${page}:`, error.message);
            break;
        }
    }

    console.log(`    Inserted ${inserted}/${count} ${type}s for ${year}`);
}

// Main execution
async function main() {
    const args = process.argv.slice(2);
    const command = args[0];

    if (command === 'inspect') {
        await inspectDatabase();
    } else if (command === 'populate') {
        const apiKey = args[1] || process.env.TMDB_API_KEY;
        if (!apiKey) {
            console.error('Error: TMDB API key required. Usage: node populate_db.js populate YOUR_API_KEY');
            process.exit(1);
        }
        await populateDatabase(apiKey);
    } else {
        console.log('Usage:');
        console.log('  node populate_db.js inspect');
        console.log('  node populate_db.js populate YOUR_TMDB_API_KEY');
    }
}

main().catch(console.error);
