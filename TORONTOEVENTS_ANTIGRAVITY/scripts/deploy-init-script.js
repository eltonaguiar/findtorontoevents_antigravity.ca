/**
 * Deploy Database Initialization Script
 */

const ftp = require('basic-ftp');
const path = require('path');

const REMOTE_BASE = '/findtorontoevents.ca/MOVIESHOWS';
const LOCAL_BASE = 'E:/findtorontoevents_antigravity.ca/TORONTOEVENTS_ANTIGRAVITY';

async function deployInitScript() {
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

        const localPath = path.join(LOCAL_BASE, 'MOVIESHOWS/init-database.php');
        const remotePath = `${REMOTE_BASE}/init-database.php`;

        console.log(`📁 Uploading: init-database.php`);
        console.log(`   Local:  ${localPath}`);
        console.log(`   Remote: ${remotePath}`);

        await client.uploadFrom(localPath, remotePath);
        console.log('   ✅ Uploaded successfully\n');

        console.log('🎉 Deployment complete!');
        console.log('\n📋 Next step:');
        console.log('Visit: https://findtorontoevents.ca/MOVIESHOWS/init-database.php');

    } catch (error) {
        console.error('❌ Deployment failed:', error.message);
        throw error;
    } finally {
        client.close();
    }
}

deployInitScript()
    .then(() => {
        console.log('\n✅ Success!');
        process.exit(0);
    })
    .catch(error => {
        console.error('\n💥 Failed:', error);
        process.exit(1);
    });
