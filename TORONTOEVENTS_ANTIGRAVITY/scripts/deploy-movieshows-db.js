/**
 * Deploy MovieShows database files to FTP server
 * Uploads PHP API files and database scripts to /findtorontoevents.ca/MOVIESHOWS
 */

const SftpClient = require('ssh2-sftp-client');
const path = require('path');
const fs = require('fs');
require('dotenv').config();

const FTP_CONFIG = {
    host: process.env.FTP_HOST || 'findtorontoevents.ca',
    port: process.env.FTP_PORT || 22,
    username: process.env.FTP_USER,
    password: process.env.FTP_PASS
};

const REMOTE_BASE = '/findtorontoevents.ca/MOVIESHOWS';
const LOCAL_BASE = path.join(__dirname, '../MOVIESHOWS');

const FILES_TO_DEPLOY = [
    { local: 'api/db-config.php', remote: 'api/db-config.php' },
    { local: 'api/movies.php', remote: 'api/movies.php' },
    { local: 'api/trailers.php', remote: 'api/trailers.php' },
    { local: 'database/init-db.php', remote: 'database/init-db.php' },
    { local: '../database/schema.sql', remote: 'database/schema.sql' },
    { local: 'DATABASE_README.md', remote: 'DATABASE_README.md' }
];

async function deployMovieShowsDatabase() {
    const sftp = new SftpClient();

    console.log('MovieShows Database Deployment');
    console.log('==============================\n');

    try {
        console.log(`Connecting to ${FTP_CONFIG.host}...`);
        await sftp.connect(FTP_CONFIG);
        console.log('✓ Connected\n');

        // Ensure directories exist
        console.log('Creating directories...');
        await ensureDir(sftp, `${REMOTE_BASE}/api`);
        await ensureDir(sftp, `${REMOTE_BASE}/database`);
        console.log('✓ Directories ready\n');

        // Upload files
        console.log('Uploading files...');
        let uploaded = 0;
        let failed = 0;

        for (const file of FILES_TO_DEPLOY) {
            const localPath = path.join(LOCAL_BASE, file.local);
            const remotePath = `${REMOTE_BASE}/${file.remote}`;

            try {
                if (!fs.existsSync(localPath)) {
                    console.log(`  ⊘ Skipped (not found): ${file.local}`);
                    continue;
                }

                await sftp.put(localPath, remotePath);
                console.log(`  ✓ Uploaded: ${file.remote}`);
                uploaded++;
            } catch (error) {
                console.error(`  ✗ Failed: ${file.remote} - ${error.message}`);
                failed++;
            }
        }

        console.log(`\n✓ Deployment complete!`);
        console.log(`  Uploaded: ${uploaded}`);
        console.log(`  Failed: ${failed}`);

        console.log(`\n📋 Next steps:`);
        console.log(`  1. Initialize database: https://findtorontoevents.ca/MOVIESHOWS/database/init-db.php`);
        console.log(`  2. Test API: https://findtorontoevents.ca/MOVIESHOWS/api/movies.php`);
        console.log(`  3. Run: npm run movies:add`);
        console.log(`  4. Run: npm run movies:scrape`);

    } catch (error) {
        console.error('Deployment error:', error.message);
        throw error;
    } finally {
        await sftp.end();
    }
}

async function ensureDir(sftp, dir) {
    try {
        await sftp.mkdir(dir, true);
    } catch (error) {
        // Directory might already exist
        if (error.code !== 4) { // 4 = Failure
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
            console.error('\n✗ Deployment failed:', error);
            process.exit(1);
        });
}

module.exports = { deployMovieShowsDatabase };
