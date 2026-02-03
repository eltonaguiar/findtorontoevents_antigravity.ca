/**
 * Verify Remote FTP Files
 * Lists all files in the MOVIESHOWS directory to verify deployment
 */

const ftp = require('basic-ftp');

const REMOTE_BASE = '/findtorontoevents.ca/MOVIESHOWS';

async function verifyRemoteFiles() {
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
        console.log('📂 Listing remote files...\n');

        // List root directory
        console.log(`\n=== ${REMOTE_BASE} ===`);
        const rootFiles = await client.list(REMOTE_BASE);
        rootFiles.forEach(file => {
            console.log(`  ${file.isDirectory ? '📁' : '📄'} ${file.name} (${file.size} bytes)`);
        });

        // List api directory
        console.log(`\n=== ${REMOTE_BASE}/api ===`);
        try {
            const apiFiles = await client.list(`${REMOTE_BASE}/api`);
            apiFiles.forEach(file => {
                console.log(`  ${file.isDirectory ? '📁' : '📄'} ${file.name} (${file.size} bytes)`);
            });
        } catch (err) {
            console.log(`  ❌ Directory not found or empty`);
        }

        // List database directory
        console.log(`\n=== ${REMOTE_BASE}/database ===`);
        try {
            const dbFiles = await client.list(`${REMOTE_BASE}/database`);
            dbFiles.forEach(file => {
                console.log(`  ${file.isDirectory ? '📁' : '📄'} ${file.name} (${file.size} bytes)`);
            });
        } catch (err) {
            console.log(`  ❌ Directory not found or empty`);
        }

        console.log('\n✅ Verification complete!');

    } catch (error) {
        console.error('❌ Verification failed:', error.message);
        throw error;
    } finally {
        client.close();
    }
}

// Run verification
verifyRemoteFiles()
    .then(() => {
        console.log('\n🎉 Remote file verification successful!');
        process.exit(0);
    })
    .catch(error => {
        console.error('\n💥 Verification failed:', error);
        process.exit(1);
    });
