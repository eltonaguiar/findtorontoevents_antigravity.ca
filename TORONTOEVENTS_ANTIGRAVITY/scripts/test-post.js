/**
 * UPDATE #34: Debug POST endpoint
 * Test what's causing the 500 error
 */

const API_BASE = 'https://findtorontoevents.ca/MOVIESHOWS/api';

async function testPost() {
    console.log('🔍 Testing POST endpoint...\n');

    const testMovie = {
        title: "Test Movie",
        type: "movie",
        release_year: 2024,
        genre: "Action",
        description: "Test description",
        source: "test"
    };

    try {
        const response = await fetch(`${API_BASE}/movies.php`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(testMovie)
        });

        console.log('Status:', response.status);
        console.log('Headers:', Object.fromEntries(response.headers.entries()));

        const text = await response.text();
        console.log('Response:', text);

        if (response.ok) {
            console.log('\n✅ POST working!');
        } else {
            console.log('\n❌ POST failed');
            console.log('Response body:', text);
        }
    } catch (error) {
        console.error('❌ Error:', error.message);
    }
}

testPost();
