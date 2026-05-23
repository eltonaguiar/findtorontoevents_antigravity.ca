// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Database Provider Audit via Live APIs', () => {

    test('MOVIESHOWS3 get-movies API - audit server-side provider data', async ({ request }) => {
        // This API returns movies with their streaming_providers from the DATABASE
        // (not the client-side TMDB Discover cache)
        const response = await request.get('https://findtorontoevents.ca/MOVIESHOWS3/api/get-movies.php');
        expect(response.ok()).toBeTruthy();

        const data = await response.json();
        expect(data.success).toBe(true);

        const movies = data.movies;
        console.log(`\n========================================`);
        console.log(`   MOVIESHOWS3 DATABASE PROVIDER AUDIT`);
        console.log(`========================================\n`);
        console.log(`Total movies returned from DB: ${data.count}`);

        // Analyze provider coverage
        let withProviders = 0;
        let withoutProviders = 0;
        const providerCounts = {};
        const missingProviderSamples = [];
        const hasProviderSamples = [];

        for (const movie of movies) {
            const providers = movie.providers || [];
            if (providers.length > 0) {
                withProviders++;
                for (const p of providers) {
                    providerCounts[p.name] = (providerCounts[p.name] || 0) + 1;
                }
                if (hasProviderSamples.length < 15) {
                    hasProviderSamples.push({
                        title: movie.title,
                        type: movie.type,
                        year: movie.release_year,
                        providers: providers.map(p => p.name).join(', '),
                    });
                }
            } else {
                withoutProviders++;
                if (missingProviderSamples.length < 30) {
                    missingProviderSamples.push({
                        id: movie.id,
                        title: movie.title,
                        type: movie.type,
                        year: movie.release_year,
                        tmdb_id: movie.tmdb_id,
                    });
                }
            }
        }

        const coverage = Math.round(withProviders / movies.length * 100);

        console.log(`\nPROVIDER COVERAGE FROM DATABASE (streaming_providers table):`);
        console.log(`  With providers: ${withProviders} (${coverage}%)`);
        console.log(`  Without providers: ${withoutProviders} (${100 - coverage}%)`);

        console.log(`\nProvider distribution (from streaming_providers table):`);
        const sorted = Object.entries(providerCounts).sort((a, b) => b[1] - a[1]);
        for (const [name, count] of sorted) {
            console.log(`  ${name}: ${count}`);
        }

        console.log(`\nSample movies WITH providers:`);
        for (const m of hasProviderSamples) {
            console.log(`  "${m.title}" (${m.type}, ${m.year}) -> ${m.providers}`);
        }

        console.log(`\nSample movies WITHOUT providers (first 30):`);
        for (const m of missingProviderSamples) {
            console.log(`  [${m.id}] "${m.title}" (${m.type}, ${m.year}) tmdb:${m.tmdb_id}`);
        }
    });

    test('MOVIESHOWS2 get-movies API - check if providers are included', async ({ request }) => {
        const response = await request.get('https://findtorontoevents.ca/MOVIESHOWS2/api/get-movies.php');
        expect(response.ok()).toBeTruthy();

        const data = await response.json();
        expect(data.success).toBe(true);

        const movies = data.movies;
        console.log(`\n========================================`);
        console.log(`   MOVIESHOWS2 DATABASE API COMPARISON`);
        console.log(`========================================\n`);
        console.log(`Total movies returned: ${data.count}`);

        // Check if MOVIESHOWS2 API returns providers at all
        let hasProvidersField = 0;
        let withProviders = 0;
        const sample = movies.slice(0, 5);

        for (const movie of movies) {
            if ('providers' in movie) {
                hasProvidersField++;
                if (movie.providers && movie.providers.length > 0) withProviders++;
            }
        }

        console.log(`Movies with 'providers' field: ${hasProvidersField} out of ${movies.length}`);
        console.log(`Movies with actual provider data: ${withProviders}`);
        console.log(`\nSample movie data structure:`);
        console.log(JSON.stringify(sample[0], null, 2));

        console.log(`\n*** KEY FINDING ***`);
        if (hasProvidersField === 0) {
            console.log(`MOVIESHOWS2 API does NOT return providers at all!`);
            console.log(`This means MOVIESHOWS2 relies ENTIRELY on client-side TMDB Discover cache.`);
            console.log(`The streaming_providers table data is NOT being served to MOVIESHOWS2.`);
        } else {
            console.log(`MOVIESHOWS2 API does return providers field.`);
            console.log(`${withProviders} out of ${movies.length} have actual provider data.`);
        }
    });

    test('Compare MOVIESHOWS2 vs MOVIESHOWS3 API data for The Wrecking Crew', async ({ request }) => {
        console.log(`\n========================================`);
        console.log(`   THE WRECKING CREW - CROSS-API CHECK`);
        console.log(`========================================\n`);

        // Check MOVIESHOWS3 API
        const ms3Response = await request.get('https://findtorontoevents.ca/MOVIESHOWS3/api/get-movies.php');
        const ms3Data = await ms3Response.json();

        const ms3WreckingCrew = ms3Data.movies?.filter(m =>
            m.title?.toLowerCase().includes('wrecking crew')
        );

        if (ms3WreckingCrew?.length > 0) {
            for (const m of ms3WreckingCrew) {
                console.log(`MOVIESHOWS3 - "${m.title}":`);
                console.log(`  ID: ${m.id}, Type: ${m.type}, Year: ${m.release_year}`);
                console.log(`  TMDB ID: ${m.tmdb_id}, IMDB ID: ${m.imdb_id}`);
                console.log(`  Providers: ${JSON.stringify(m.providers)}`);
                console.log(`  Trailer: ${m.trailer_id}`);
            }
        } else {
            console.log(`MOVIESHOWS3: "The Wrecking Crew" NOT FOUND in API response`);
        }

        // Check MOVIESHOWS2 API
        const ms2Response = await request.get('https://findtorontoevents.ca/MOVIESHOWS2/api/get-movies.php');
        const ms2Data = await ms2Response.json();

        const ms2WreckingCrew = ms2Data.movies?.filter(m =>
            m.title?.toLowerCase().includes('wrecking crew')
        );

        if (ms2WreckingCrew?.length > 0) {
            for (const m of ms2WreckingCrew) {
                console.log(`\nMOVIESHOWS2 - "${m.title}":`);
                console.log(`  ID: ${m.id}, Type: ${m.type}, Year: ${m.release_year}`);
                console.log(`  TMDB ID: ${m.tmdb_id}, IMDB ID: ${m.imdb_id}`);
                console.log(`  Has providers field: ${'providers' in m}`);
                console.log(`  Providers: ${JSON.stringify(m.providers || 'NOT PRESENT')}`);
                console.log(`  Trailer: ${m.trailer_id}`);
            }
        } else {
            console.log(`MOVIESHOWS2: "The Wrecking Crew" NOT FOUND in API response (limit 500)`);
        }
    });

    test('Audit provider-coverage-stats API endpoint', async ({ request }) => {
        // Try the provider coverage stats endpoint
        const response = await request.get('https://findtorontoevents.ca/MOVIESHOWS3/api/provider-coverage-stats.php');

        console.log(`\n========================================`);
        console.log(`   LIVE PROVIDER COVERAGE STATS`);
        console.log(`========================================\n`);

        if (response.ok()) {
            const text = await response.text();
            console.log(text);
        } else {
            console.log(`Failed to fetch provider-coverage-stats: ${response.status()}`);
        }
    });

    test('Audit provider gaps API endpoint', async ({ request }) => {
        const response = await request.get('https://findtorontoevents.ca/MOVIESHOWS3/api/audit-provider-gaps.php');

        console.log(`\n========================================`);
        console.log(`   LIVE PROVIDER GAP AUDIT`);
        console.log(`========================================\n`);

        if (response.ok()) {
            const text = await response.text();
            console.log(text);
        } else {
            console.log(`Failed to fetch audit-provider-gaps: ${response.status()}`);
        }
    });

    test('Check database-audit API for full picture', async ({ request }) => {
        const response = await request.get('https://findtorontoevents.ca/MOVIESHOWS3/api/database-audit.php');

        console.log(`\n========================================`);
        console.log(`   FULL DATABASE AUDIT`);
        console.log(`========================================\n`);

        if (response.ok()) {
            const text = await response.text();
            console.log(text.substring(0, 5000));
        } else {
            console.log(`Failed to fetch database-audit: ${response.status()}`);
        }
    });

    test('Known titles - check DB provider data vs client-side TMDB cache', async ({ request }) => {
        const KNOWN_TITLES = [
            'Wrecking Crew', 'Stranger Things', 'The Boys', 'Reacher',
            'Wednesday', 'Squid Game', 'Mandalorian', 'Loki', 'Severance',
            'Ted Lasso', 'White Lotus', 'Last of Us', 'Succession',
            'Bear', 'Yellowjackets', 'Queen Charlotte', 'Citadel', 'Ahsoka',
            'Only Murders', 'Fallout', 'Oppenheimer', 'Barbie', 'Dune'
        ];

        const ms3Response = await request.get('https://findtorontoevents.ca/MOVIESHOWS3/api/get-movies.php');
        const ms3Data = await ms3Response.json();

        console.log(`\n========================================`);
        console.log(`   KNOWN TITLES - DB PROVIDER CHECK`);
        console.log(`========================================\n`);

        let foundWithProvider = 0;
        let foundWithoutProvider = 0;
        let notFound = 0;

        for (const search of KNOWN_TITLES) {
            const matches = ms3Data.movies?.filter(m =>
                m.title?.toLowerCase().includes(search.toLowerCase())
            );

            if (matches?.length > 0) {
                const movie = matches[0];
                const providers = movie.providers || [];
                if (providers.length > 0) {
                    foundWithProvider++;
                    console.log(`[DB HAS] "${movie.title}" -> ${providers.map(p => p.name).join(', ')}`);
                } else {
                    foundWithoutProvider++;
                    console.log(`[DB MISSING] "${movie.title}" (${movie.type}, ${movie.release_year})`);
                }
            } else {
                notFound++;
                console.log(`[NOT IN API] "${search}" - not returned by get-movies.php`);
            }
        }

        console.log(`\n--- SUMMARY ---`);
        console.log(`Found with DB providers: ${foundWithProvider}`);
        console.log(`Found WITHOUT DB providers: ${foundWithoutProvider}`);
        console.log(`Not in API response: ${notFound}`);
        console.log(`DB provider coverage for known titles: ${Math.round(foundWithProvider / (foundWithProvider + foundWithoutProvider) * 100)}%`);
    });
});
