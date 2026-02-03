const ftp = require('basic-ftp');
const path = require('path');

async function deploy() {
    const client = new ftp.Client();
    client.ftp.verbose = true;

    try {
        console.log('🚀 Deploying MOVIESHOWS2...\n');
        console.log('🔌 Connecting to FTP...');

        await client.access({
            host: 'ftps2.50webs.com',
            user: 'ejaguiar1',
            password: '$a^FzN7BqKapSQMsZxD&^FeTJ',
            secure: false
        });

        console.log('✅ Connected!\n');

        console.log('📁 Navigating to /findtorontoevents.ca/MOVIESHOWS2...');
        await client.cd('/findtorontoevents.ca/MOVIESHOWS2');
        console.log('✅ In MOVIESHOWS2 directory!\n');

        console.log('📤 Uploading index.html...');
        await client.uploadFrom(path.join(__dirname, 'index.html'), 'index.html');
        console.log('✅ index.html uploaded!\n');

        console.log('📤 Uploading play.html...');
        await client.uploadFrom(path.join(__dirname, 'play.html'), 'play.html');
        console.log('✅ play.html uploaded!\n');

        console.log('🎉 Deployment successful!');
        console.log('🌐 Live at: https://findtorontoevents.ca/MOVIESHOWS2/\n');
        console.log('🎬 Player at: https://findtorontoevents.ca/MOVIESHOWS2/play.html\n');

    } catch (err) {
        console.error('❌ Error:', err.message);
        process.exit(1);
    } finally {
        client.close();
    }
}

deploy();
