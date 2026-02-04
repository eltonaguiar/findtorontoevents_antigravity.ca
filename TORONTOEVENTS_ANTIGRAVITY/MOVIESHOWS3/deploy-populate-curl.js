const ftp = require('basic-ftp');
const path = require('path');

async function deploy() {
    const client = new ftp.Client();

    try {
        await client.access({
            host: 'ftps2.50webs.com',
            user: 'ejaguiar1',
            password: '$a^FzN7BqKapSQMsZxD&^FeTJ',
            secure: false
        });

        await client.cd('/findtorontoevents.ca/MOVIESHOWS3');
        await client.uploadFrom(path.join(__dirname, 'populate-curl.php'), 'populate-curl.php');
        console.log('✅ populate-curl.php uploaded!');
        console.log('🌐 Run: https://findtorontoevents.ca/MOVIESHOWS3/populate-curl.php');

    } catch (err) {
        console.error('❌ Error:', err.message);
    } finally {
        client.close();
    }
}

deploy();
