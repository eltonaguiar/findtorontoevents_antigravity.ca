const ftp = require('basic-ftp');
const fs = require('fs');
const path = require('path');

async function deployPopulateScript() {
    const client = new ftp.Client();
    client.ftp.verbose = true;

    try {
        console.log('📡 Connecting to FTP server...');
        await client.access({
            host: 'ftps2.50webs.com',
            user: 'ejaguiar1',
            password: '$a^FzN7BqKapSQMsZxD&^FeTJ',
            secure: false
        });

        console.log('✓ Connected to FTP server\n');

        // Navigate to MOVIESHOWS directory
        const remotePath = '/findtorontoevents.ca/MOVIESHOWS';
        console.log(`📁 Navigating to ${remotePath}...`);
        await client.ensureDir(remotePath);
        console.log('✓ Directory ready\n');

        // Upload populate_tmdb.php
        const localFile = path.join(__dirname, 'populate_tmdb.php');
        const remoteFile = 'populate_tmdb.php';

        console.log(`📤 Uploading ${remoteFile}...`);
        await client.uploadFrom(localFile, remoteFile);
        console.log('✓ Upload complete\n');

        console.log('✅ Deployment successful!\n');
        console.log('Next steps:');
        console.log('1. Inspect database:');
        console.log('   https://findtorontoevents.ca/MOVIESHOWS/populate_tmdb.php?action=inspect');
        console.log('');
        console.log('2. Populate all years (2015-2027):');
        console.log('   https://findtorontoevents.ca/MOVIESHOWS/populate_tmdb.php?action=populate_all&api_key=b84ff7bfe35ffad8779b77bcbbda317f');
        console.log('');
        console.log('3. Or populate year by year:');
        console.log('   https://findtorontoevents.ca/MOVIESHOWS/populate_tmdb.php?action=populate&api_key=b84ff7bfe35ffad8779b77bcbbda317f&year=2027&type=movie&limit=100');
        console.log('');

    } catch (error) {
        console.error('❌ Deployment failed:', error.message);
        throw error;
    } finally {
        client.close();
    }
}

deployPopulateScript()
    .then(() => {
        console.log('🎉 Done!');
        process.exit(0);
    })
    .catch(error => {
        console.error('💥 Error:', error);
        process.exit(1);
    });
