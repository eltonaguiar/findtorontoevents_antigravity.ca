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
        await client.uploadFrom(path.join(__dirname, 'populate-more.php'), 'populate-more.php');
        console.log('✅ populate-more.php uploaded!');
        console.log('🌐 Run: https://findtorontoevents.ca/MOVIESHOWS3/populate-more.php');

    } catch (err) {
        console.error('❌ Error:', err.message);
    } finally {
        client.close();
    }
}

deploy();
