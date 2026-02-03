/**
 * Test database content population
 * Verifies that database has sufficient content before running full bulk population
 */

const axios = require('axios');

const API_URL = 'https://findtorontoevents.ca/MOVIESHOWS/api';

async function testDatabaseContent() {
    console.log('MovieShows Database Content Test');
    console.log('=================================\n');

    try {
        // Test API connectivity
        console.log('Testing API connectivity...');
        const response = await axios.get(`${API_URL}/movies.php`);

        if (response.data && response.data.movies) {
            const movies = response.data.movies;
            const count = response.data.count;

            console.log(`✓ API accessible`);
            console.log(`✓ Total movies in database: ${count}\n`);

            // Analyze by year
            const byYear = {};
            const byType = { movie: 0, tv_series: 0 };

            movies.forEach(movie => {
                const year = movie.release_year || 'Unknown';
                byYear[year] = (byYear[year] || 0) + 1;
                byType[movie.type] = (byType[movie.type] || 0) + 1;
            });

            console.log('Content by Year:');
            Object.keys(byYear)
                .sort((a, b) => b - a)
                .forEach(year => {
                    const status = byYear[year] >= 200 ? '✓' : '⚠';
                    console.log(`  ${status} ${year}: ${byYear[year]} items`);
                });

            console.log('\nContent by Type:');
            console.log(`  Movies: ${byType.movie || 0}`);
            console.log(`  TV Series: ${byType.tv_series || 0}`);

            // Check target years
            console.log('\nTarget Coverage (2026-2015):');
            let needsPopulation = false;

            for (let year = 2026; year >= 2015; year--) {
                const yearCount = byYear[year] || 0;
                const status = yearCount >= 200 ? '✓' : '✗';
                const message = yearCount >= 200 ? 'Complete' : `Needs ${200 - yearCount} more`;

                console.log(`  ${status} ${year}: ${yearCount}/200 - ${message}`);

                if (yearCount < 200) {
                    needsPopulation = true;
                }
            }

            console.log('\n' + '='.repeat(50));

            if (needsPopulation) {
                console.log('⚠ Database needs population');
                console.log('Run: npm run movies:bulk');
            } else {
                console.log('✓ Database is fully populated!');
            }

            return {
                total: count,
                byYear,
                byType,
                needsPopulation
            };

        } else {
            console.error('✗ Unexpected API response format');
            return null;
        }

    } catch (error) {
        if (error.response && error.response.status === 404) {
            console.error('✗ API not found - Database may not be initialized');
            console.log('\nNext steps:');
            console.log('1. Upload PHP files to server');
            console.log('2. Visit: https://findtorontoevents.ca/MOVIESHOWS/database/init-db.php');
            console.log('3. Run: npm run movies:bulk');
        } else {
            console.error('✗ Error:', error.message);
        }
        return null;
    }
}

// Run if executed directly
if (require.main === module) {
    testDatabaseContent()
        .then(() => {
            console.log('\n✓ Test complete!');
            process.exit(0);
        })
        .catch(error => {
            console.error('\n✗ Test failed:', error);
            process.exit(1);
        });
}

module.exports = { testDatabaseContent };
