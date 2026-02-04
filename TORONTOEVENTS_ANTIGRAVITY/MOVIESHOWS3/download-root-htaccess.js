const ftp = require('basic-ftp');
const path = require('path');
const fs = require('fs');

async function downloadRootHtaccess() {
    const client = new ftp.Client();
    client.ftp.verbose = true;

    try {
        console.log('📥 Downloading root .htaccess from server...\n');
        console.log('🔌 Connecting to FTP...');

        await client.access({
            host: 'ftps2.50webs.com',
            user: 'ejaguiar1',
            password: '$a^FzN7BqKapSQMsZxD&^FeTJ',
            secure: false
        });

        console.log('✅ Connected!\n');

        // Navigate to root directory
        console.log('📁 Navigating to /findtorontoevents.ca/...');
        await client.cd('/findtorontoevents.ca');
        console.log('✅ In root directory!\n');

        // Download .htaccess
        console.log('📥 Downloading .htaccess...');
        const localPath = path.join(__dirname, 'downloaded_root_htaccess.txt');
        await client.downloadTo(localPath, '.htaccess');
        console.log('✅ .htaccess downloaded!\n');

        // Read and display the contents
        const contents = fs.readFileSync(localPath, 'utf8');
        console.log('📄 Contents of .htaccess on server:');
        console.log('=====================================');
        console.log(contents);
        console.log('=====================================\n');

    } catch (err) {
        console.error('❌ Error:', err.message);
        process.exit(1);
    } finally {
        client.close();
    }
}

downloadRootHtaccess();
