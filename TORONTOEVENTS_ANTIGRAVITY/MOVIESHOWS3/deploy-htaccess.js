const ftp = require('basic-ftp');
const path = require('path');

async function deployHtaccess() {
    const client = new ftp.Client();
    client.ftp.verbose = true;

    try {
        console.log('🚀 Deploying .htaccess for MOVIESHOWS3...\n');
        console.log('🔌 Connecting to FTP...');

        await client.access({
            host: 'ftps2.50webs.com',
            user: 'ejaguiar1',
            password: '$a^FzN7BqKapSQMsZxD&^FeTJ',
            secure: false
        });

        console.log('✅ Connected!\n');

        // Navigate to MOVIESHOWS3 directory
        console.log('📁 Navigating to /findtorontoevents.ca/MOVIESHOWS3...');
        await client.cd('/findtorontoevents.ca/MOVIESHOWS3');
        console.log('✅ Directory found!\n');

        // Upload .htaccess
        console.log('📤 Uploading .htaccess...');
        await client.uploadFrom(path.join(__dirname, '.htaccess'), '.htaccess');
        console.log('✅ .htaccess uploaded!\n');

        console.log('🎉 Deployment successful!');
        console.log('🌐 Test URLs:');
        console.log('   - https://findtorontoevents.ca/MOVIESHOWS3/');
        console.log('   - https://findtorontoevents.ca/movieshows3/');
        console.log('\n✨ Both URLs should now work and redirect properly!\n');

    } catch (err) {
        console.error('❌ Error:', err.message);
        process.exit(1);
    } finally {
        client.close();
    }
}

deployHtaccess();
