/**
 * Deploy MovieShows database files to FTP server
 * Enhanced with better error handling and connection retry
 */

const SftpClient = require('ssh2-sftp-client');
const path = require('path');
const fs = require('fs');
require('dotenv').config();

const FTP_CONFIG = {
    host: process.env.FTP_SERVER || 'ftps2.50webs.com',
    port: 22,
    username: process.env.FTP_USERNAME,
    password: process.env.FTP_PASSWORD,
    retries: 3,
    retry_factor: 2,
    retry_minTimeout: 2000
};

const REMOTE_BASE = '/findtorontoevents.ca/MOVIESHOWS';
const LOCAL_BASE = path.join(__dirname, '../MOVIESHOWS');

const FILES_TO_DEPLOY = [
    { local: 'api/db-config.php', remote: 'api/db-config.php' },
    { local: 'api/movies.php', remote: 'api/movies.php' },
    { local: 'api/trailers.php', remote: 'api/trailers.php' },
    { local: 'api/queue.php', remote: 'api/queue.php' },
    { local: 'api/preferences.php', remote: 'api/preferences.php' },
    { local: 'api/playlists.php', remote: 'api/playlists.php' },
    { local: 'database/init-db.php', remote: 'database/init-db.php' },
    { local: '../database/schema.sql', remote: 'database/schema.sql' },
    { local: 'DATABASE_README.md', remote: 'DATABASE_README.md' },
    { local: 'SAFE_DEPLOYMENT.md', remote: 'SAFE_DEPLOYMENT.md' }
];

async function deployMovieShowsDatabase() {
    const sftp = new SftpClient();

    console.log('MovieShows Database Deployment');
    console.log('==============================\n');

    try {
        console.log(`Connecting to ${FTP_CONFIG.host}:${FTP_CONFIG.port}...`);
        console.log(`Username: ${FTP_CONFIG.username}\n`);

        await sftp.connect(FTP_CONFIG);
        console.log('✓ Connected successfully!\n');

        // Ensure directories exist
        console.log('Creating directories...');
        await ensureDir(sftp, `${REMOTE_BASE}/api`);
        await ensureDir(sftp, `${REMOTE_BASE}/database`);
        console.log('✓ Directories ready\n');

        // Upload files
        console.log('Uploading files...\n');
        let uploaded = 0;
        let failed = 0;
        let skipped = 0;

        for (const file of FILES_TO_DEPLOY) {
            const localPath = path.join(LOCAL_BASE, file.local);
            const remotePath = `${REMOTE_BASE}/${file.remote}`;

            try {
                if (!fs.existsSync(localPath)) {
                    console.log(`  ⊘ Skipped (not found): ${file.local}`);
                    skipped++;
                    continue;
                }

                const stats = fs.statSync(localPath);
                const sizeKB = (stats.size / 1024).toFixed(2);

                await sftp.put(localPath, remotePath);
                console.log(`  ✓ Uploaded: ${file.remote} (${sizeKB} KB)`);
                uploaded++;

            } catch (error) {
                console.error(`  ✗ Failed: ${file.remote}`);
                console.error(`    Error: ${error.message}`);
                failed++;
            }
        }

        console.log(`\n✓ Deployment complete!`);
        console.log(`  Uploaded: ${uploaded}`);
        console.log(`  Failed: ${failed}`);
        console.log(`  Skipped: ${skipped}`);

        if (uploaded > 0) {
            console.log(`\n📋 Next steps:`);
            console.log(`  1. Initialize database: https://findtorontoevents.ca/MOVIESHOWS/database/init-db.php`);
            console.log(`  2. Test API: https://findtorontoevents.ca/MOVIESHOWS/api/movies.php`);
            console.log(`  3. Add content: npm run movies:add`);
            console.log(`  4. Scrape Cineplex: npm run movies:scrape`);
            console.log(`  5. Discover trailers: npm run movies:discover`);
        }

    } catch (error) {
        console.error('\n✗ Deployment error:', error.message);

        if (error.message.includes('connect')) {
            console.error('\nConnection troubleshooting:');
            console.error('  - Verify FTP credentials in .env file');
            console.error('  - Check if server is accessible');
            console.error('  - Try manual FTP upload instead');
        }

        throw error;
    } finally {
        await sftp.end();
    }
}

async function ensureDir(sftp, dir) {
    try {
        await sftp.mkdir(dir, true);
    } catch (error) {
        // Directory might already exist, ignore error
        if (error.code !== 4) {
            throw error;
        }
    }
}

// Run if executed directly
if (require.main === module) {
    deployMovieShowsDatabase()
        .then(() => {
            console.log('\n✓ All done!');
            process.exit(0);
        })
        .catch(error => {
            console.error('\n✗ Deployment failed');
            console.error('See SAFE_DEPLOYMENT.md for manual upload instructions');
            process.exit(1);
        });
}

module.exports = { deployMovieShowsDatabase };
