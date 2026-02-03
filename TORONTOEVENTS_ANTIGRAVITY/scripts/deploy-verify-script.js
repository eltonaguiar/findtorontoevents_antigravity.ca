/**
 * Deploy Verification Script
 */

const ftp = require('basic-ftp');
const path = require('path');

const REMOTE_BASE = '/findtorontoevents.ca/MOVIESHOWS';
const LOCAL_BASE = 'E:/findtorontoevents_antigravity.ca/TORONTOEVENTS_ANTIGRAVITY';

async function deployVerifyScript() {
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

        console.log('✅ Connected\n');

        const localPath = path.join(LOCAL_BASE, 'MOVIESHOWS/verify-database.php');
        const remotePath = `${REMOTE_BASE}/verify-database.php`;

        console.log(`📁 Uploading: verify-database.php`);
        await client.uploadFrom(localPath, remotePath);
        console.log('   ✅ Uploaded\n');

        console.log('🎉 Done!');
        console.log('Visit: https://findtorontoevents.ca/MOVIESHOWS/verify-database.php');

    } catch (error) {
        console.error('❌ Failed:', error.message);
        throw error;
    } finally {
        client.close();
    }
}

deployVerifyScript()
    .then(() => process.exit(0))
    .catch(error => {
        console.error(error);
        process.exit(1);
    });
