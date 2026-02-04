const https = require('https');

const API_KEY = 'b84ff7bfe35ffad8779b77bcbbda317f';
const BASE_URL = 'https://findtorontoevents.ca/MOVIESHOWS/populate_tmdb.php';

function makeRequest(url) {
    return new Promise((resolve, reject) => {
        https.get(url, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => resolve(data));
        }).on('error', reject);
    });
}

async function populateYear(year, type) {
    const url = `${BASE_URL}?action=populate&api_key=${API_KEY}&year=${year}&type=${type}&limit=100`;
    console.log(`\n${'='.repeat(60)}`);
    console.log(`Populating ${year} ${type}s...`);
    console.log('='.repeat(60));

    try {
        const response = await makeRequest(url);
        console.log(response);
        return true;
    } catch (error) {
        console.error(`Error: ${error.message}`);
        return false;
    }
}

async function populateAllYears() {
    console.log('\n🎬 STARTING DATABASE POPULATION');
    console.log('Target: 100 movies + 100 TV shows per year (2015-2027)\n');

    const startYear = 2027;
    const endYear = 2015;
    let totalInserted = 0;

    for (let year = startYear; year >= endYear; year--) {
        console.log(`\n\n${'█'.repeat(60)}`);
        console.log(`█  YEAR ${year}  █`);
        console.log('█'.repeat(60));

        // Movies
        console.log('\n📽️  MOVIES');
        await populateYear(year, 'movie');

        // Small delay between requests
        await new Promise(resolve => setTimeout(resolve, 1000));

        // TV Shows
        console.log('\n📺 TV SHOWS');
        await populateYear(year, 'tv');

        // Delay between years
        await new Promise(resolve => setTimeout(resolve, 2000));
    }

    console.log('\n\n' + '='.repeat(60));
    console.log('✅ POPULATION COMPLETE!');
    console.log('='.repeat(60));

    // Final inspection
    console.log('\n📊 Final Database State:\n');
    const inspectUrl = `${BASE_URL}?action=inspect`;
    const finalState = await makeRequest(inspectUrl);
    console.log(finalState);
}

// Run the population
populateAllYears()
    .then(() => {
        console.log('\n🎉 All done! Database has been enhanced.');
        process.exit(0);
    })
    .catch(error => {
        console.error('\n❌ Error:', error);
        process.exit(1);
    });
