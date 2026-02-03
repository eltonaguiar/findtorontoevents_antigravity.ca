/**
 * Check Remote File Structure via FTP
 */

const ftp = require('basic-ftp');

async function checkRemoteStructure() {
    const client = new ftp.Client();

    try {
        await client.access({
            host: 'ftps2.50webs.com',
            user: 'ejaguiar1',
            password: '$a^FzN7BqKapSQMsZxD&^FeTJ',
            secure: false
        });

        console.log('📂 Remote Structure:\n');

        const paths = [
            '/findtorontoevents.ca/MOVIESHOWS',
            '/findtorontoevents.ca/MOVIESHOWS/api',
            '/findtorontoevents.ca/MOVIESHOWS/database'
        ];

        for (const path of paths) {
            console.log(`\n=== ${path} ===`);
            try {
                const files = await client.list(path);
                files.forEach(f => {
                    console.log(`  ${f.isDirectory ? '📁' : '📄'} ${f.name} (${f.size} bytes)`);
                });
            } catch (e) {
                console.log(`  ❌ Not found or empty`);
            }
        }

    } catch (error) {
        console.error('Error:', error.message);
    } finally {
        client.close();
    }
}

checkRemoteStructure();
