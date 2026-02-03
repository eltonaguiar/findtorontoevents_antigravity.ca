/**
 * Deploy MovieShows Files via FTP
 * Uploads new API files and updated schema to production
 */

const ftp = require('basic-ftp');
const path = require('path');

const REMOTE_BASE = '/findtorontoevents.ca/MOVIESHOWS';
const LOCAL_BASE = 'E:/findtorontoevents_antigravity.ca/TORONTOEVENTS_ANTIGRAVITY';

const FILES_TO_DEPLOY = [
    { local: 'MOVIESHOWS/api/queue.php', remote: `${REMOTE_BASE}/api/queue.php` },
    { local: 'MOVIESHOWS/api/preferences.php', remote: `${REMOTE_BASE}/api/preferences.php` },
    { local: 'MOVIESHOWS/api/playlists.php', remote: `${REMOTE_BASE}/api/playlists.php` },
    { local: 'database/schema.sql', remote: `${REMOTE_BASE}/database/schema.sql` }
];

async function deployFiles() {
    const client = new ftp.Client();
    client.ftp.verbose = true;

    try {
        console.log('🔗 Connecting to FTP server...');
        await client.access({
            host: 'ftps2.50webs.com',
            user: 'ejaguiar1',
            password: '$a^FzN7BqKapSQMsZxD&^FeTJ',
            secure: false
        });

        console.log('✅ Connected to FTP server\n');

        // Ensure directories exist
        console.log('📁 Ensuring directories exist...');
        try {
            await client.ensureDir(`${REMOTE_BASE}/api`);
            await client.ensureDir(`${REMOTE_BASE}/database`);
            console.log('✅ Directories ready\n');
        } catch (err) {
            console.log('⚠️  Directory creation skipped (may already exist)\n');
        }

        console.log('📤 Deploying files...\n');

        for (const file of FILES_TO_DEPLOY) {
            const localPath = path.join(LOCAL_BASE, file.local);
            console.log(`📁 Uploading: ${file.local}`);
            console.log(`   Local:  ${localPath}`);
            console.log(`   Remote: ${file.remote}`);

            try {
                await client.uploadFrom(localPath, file.remote);
                console.log('   ✅ Uploaded successfully\n');
            } catch (uploadErr) {
                console.error(`   ❌ Failed: ${uploadErr.message}`);
                console.log(`   Trying alternative path...\n`);

                // Try without leading slash
                const altRemote = file.remote.replace(/^\//, '');
                await client.uploadFrom(localPath, altRemote);
                console.log('   ✅ Uploaded successfully (alternative path)\n');
            }
        }

        console.log('🎉 All files deployed successfully!');
        console.log('\n📋 Next steps:');
        console.log('1. Visit: https://findtorontoevents.ca/MOVIESHOWS/database/init-db.php');
        console.log('2. Verify new tables are created');
        console.log('3. Test API endpoints');

    } catch (error) {
        console.error('❌ Deployment failed:', error.message);
        console.error('Full error:', error);
        throw error;
    } finally {
        client.close();
    }
}

// Run deployment
deployFiles()
    .then(() => {
        console.log('\n✅ Deployment complete!');
        process.exit(0);
    })
    .catch(error => {
        console.error('\n💥 Deployment failed:', error);
        process.exit(1);
    });
