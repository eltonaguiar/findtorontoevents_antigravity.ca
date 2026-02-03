/**
 * Test API Endpoints
 */

const endpoints = [
    'https://findtorontoevents.ca/MOVIESHOWS/api/movies.php',
    'https://findtorontoevents.ca/MOVIESHOWS/api/trailers.php',
    'https://findtorontoevents.ca/MOVIESHOWS/api/queue.php',
    'https://findtorontoevents.ca/MOVIESHOWS/api/preferences.php',
    'https://findtorontoevents.ca/MOVIESHOWS/api/playlists.php',
    'https://findtorontoevents.ca/MOVIESHOWS/verify-database.php',
];

async function testEndpoints() {
    console.log('Testing API Endpoints\n');

    for (const url of endpoints) {
        const name = url.split('/').pop();
        process.stdout.write(`${name.padEnd(30)} ... `);

        try {
            const response = await fetch(url);
            const status = response.status;
            const text = await response.text();

            if (status === 200) {
                console.log(`✓ ${status} (${text.length} bytes)`);
            } else if (status === 401) {
                console.log(`✓ ${status} (auth required - working!)`);
            } else {
                console.log(`✗ ${status}`);
                if (text.length < 200) console.log(`  ${text.substring(0, 100)}`);
            }
        } catch (error) {
            console.log(`✗ ${error.message}`);
        }
    }
}

testEndpoints();
