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
        await client.uploadFrom(path.join(__dirname, 'test-db.php'), 'test-db.php');
        console.log('✅ test-db.php uploaded!');
        console.log('🌐 Test: https://findtorontoevents.ca/MOVIESHOWS3/test-db.php');

    } catch (err) {
        console.error('❌ Error:', err.message);
    } finally {
        client.close();
    }
}

deploy();
