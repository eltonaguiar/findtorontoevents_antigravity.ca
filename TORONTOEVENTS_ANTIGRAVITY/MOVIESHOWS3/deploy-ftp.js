const ftp = require('basic-ftp');
const path = require('path');

async function deploy() {
    const client = new ftp.Client();
    client.ftp.verbose = true;

    try {
        console.log('🚀 Deploying MOVIESHOWS3...\n');
        console.log('🔌 Connecting to FTP...');

        await client.access({
            host: 'ftps2.50webs.com',
            user: 'ejaguiar1',
            password: '$a^FzN7BqKapSQMsZxD&^FeTJ',
            secure: false
        });

        console.log('✅ Connected!\n');

        // Deploy to /findtorontoevents.ca/MOVIESHOWS3
        console.log('📁 Creating /findtorontoevents.ca/MOVIESHOWS3 directory...');
        try {
            await client.ensureDir('/findtorontoevents.ca/MOVIESHOWS3');
            console.log('✅ Directory ready!\n');
        } catch (e) {
            console.log('Directory might already exist, continuing...\n');
        }

        await client.cd('/findtorontoevents.ca/MOVIESHOWS3');

        console.log('📤 Uploading index.html...');
        await client.uploadFrom(path.join(__dirname, 'index.html'), 'index.html');
        console.log('✅ index.html uploaded!\n');

        console.log('📤 Uploading play.html...');
        await client.uploadFrom(path.join(__dirname, 'play.html'), 'play.html');
        console.log('✅ play.html uploaded!\n');

        console.log('📤 Uploading app.html (main TikTok-style interface)...');
        await client.uploadFrom(path.join(__dirname, 'app.html'), 'app.html');
        console.log('✅ app.html uploaded!\n');

        console.log('📤 Uploading .htaccess...');
        await client.uploadFrom(path.join(__dirname, '.htaccess'), '.htaccess');
        console.log('✅ .htaccess uploaded!\n');

        console.log('📤 Uploading favicon.ico...');
        await client.uploadFrom(path.join(__dirname, 'favicon.ico'), 'favicon.ico');
        console.log('✅ favicon.ico uploaded!\n');

        console.log('📤 Uploading init-database.php...');
        await client.uploadFrom(path.join(__dirname, 'init-database.php'), 'init-database.php');
        console.log('✅ init-database.php uploaded!\n');

        console.log('📤 Uploading verify-database.php...');
        await client.uploadFrom(path.join(__dirname, 'verify-database.php'), 'verify-database.php');
        console.log('✅ verify-database.php uploaded!\n');

        console.log('📁 Uploading _next directory...');
        await client.uploadFromDir(path.join(__dirname, '_next'), '_next');
        console.log('✅ _next directory uploaded!\n');

        console.log('📁 Uploading api directory...');
        await client.uploadFromDir(path.join(__dirname, 'api'), 'api');
        console.log('✅ api directory uploaded!\n');

        console.log('🎉 Deployment successful!');
        console.log('🌐 Live at: https://findtorontoevents.ca/MOVIESHOWS3/\n');
        console.log('🎬 TikTok-style player: https://findtorontoevents.ca/MOVIESHOWS3/app.html\n');
        console.log('🗄️  Initialize DB: https://findtorontoevents.ca/MOVIESHOWS3/init-database.php\n');

    } catch (err) {
        console.error('❌ Error:', err.message);
        process.exit(1);
    } finally {
        client.close();
    }
}

deploy();
