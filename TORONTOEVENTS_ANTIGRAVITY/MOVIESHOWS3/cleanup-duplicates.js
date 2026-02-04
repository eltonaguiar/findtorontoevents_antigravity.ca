const ftp = require('basic-ftp');
const path = require('path');

async function cleanup() {
    const client = new ftp.Client();
    client.ftp.verbose = true;

    try {
        console.log('🧹 Cleaning up duplicate folders...\n');

        await client.access({
            host: 'ftps2.50webs.com',
            user: 'ejaguiar1',
            password: '$a^FzN7BqKapSQMsZxD&^FeTJ',
            secure: false
        });

        console.log('✅ Connected!\n');

        // Check if lowercase /movieshows3 exists
        try {
            await client.cd('/findtorontoevents.ca/movieshows3');
            console.log('⚠️  Found /movieshows3 (lowercase) - removing...\n');
            await client.removeDir('/findtorontoevents.ca/movieshows3');
            console.log('✅ Removed /movieshows3\n');
        } catch (e) {
            console.log('✅ No lowercase /movieshows3 found (good!)\n');
        }

        // Upload updated .htaccess to MOVIESHOWS3
        await client.cd('/findtorontoevents.ca/MOVIESHOWS3');
        await client.uploadFrom(path.join(__dirname, '.htaccess'), '.htaccess');
        console.log('✅ Updated .htaccess with redirect rules\n');

        console.log('🎉 Cleanup complete!\n');
        console.log('🌐 Both /movieshows3 and /MOVIESHOWS3 now redirect to /MOVIESHOWS3/\n');

    } catch (err) {
        console.error('❌ Error:', err.message);
        process.exit(1);
    } finally {
        client.close();
    }
}

cleanup();
