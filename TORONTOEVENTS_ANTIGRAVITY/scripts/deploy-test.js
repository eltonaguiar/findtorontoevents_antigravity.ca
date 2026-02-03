/**
 * Deploy test-post.php
 */

const ftp = require('basic-ftp');

async function deployTest() {
    const client = new ftp.Client();

    try {
        await client.access({
            host: 'ftps2.50webs.com',
            user: 'ejaguiar1',
            password: '$a^FzN7BqKapSQMsZxD&^FeTJ',
            secure: false
        });

        console.log('Uploading test-post.php...');
        await client.uploadFrom(
            'E:/findtorontoevents_antigravity.ca/TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS/test-post.php',
            '/findtorontoevents.ca/MOVIESHOWS/test-post.php'
        );

        console.log('✅ Deployed!');
        console.log('Test at: https://findtorontoevents.ca/MOVIESHOWS/test-post.php');
    } catch (error) {
        console.error('Error:', error.message);
    } finally {
        client.close();
    }
}

deployTest();
