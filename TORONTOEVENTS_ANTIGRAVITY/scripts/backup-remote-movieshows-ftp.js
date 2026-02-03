/**
 * Backup Remote MovieShows Files via FTP
 * Creates a timestamped backup of all files before deployment
 */

const ftp = require('basic-ftp');
const fs = require('fs').promises;
const path = require('path');
require('dotenv').config();

const BACKUP_DIR = `remote_backup_movieshows/2026-02-03`;
const REMOTE_PATH = '/findtorontoevents.ca/MOVIESHOWS';

async function backupRemoteFiles() {
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

        console.log(`✅ Connected to ${process.env.FTP_SERVER}`);
        console.log(`📂 Backing up: ${REMOTE_PATH}`);
        console.log(`💾 Backup location: ${BACKUP_DIR}\n`);

        // Create local backup directory
        await fs.mkdir(BACKUP_DIR, { recursive: true });

        // Download entire MOVIESHOWS directory
        await client.downloadToDir(BACKUP_DIR, REMOTE_PATH);

        console.log('\n✅ Backup complete!');
        console.log(`📁 Files saved to: ${BACKUP_DIR}`);

        // List backed up files
        const files = await fs.readdir(BACKUP_DIR, { recursive: true });
        console.log(`\n📊 Backed up ${files.length} files/directories`);

    } catch (error) {
        console.error('❌ Backup failed:', error.message);
        throw error;
    } finally {
        client.close();
    }
}

// Run backup
backupRemoteFiles()
    .then(() => {
        console.log('\n🎉 Remote backup successful!');
        process.exit(0);
    })
    .catch(error => {
        console.error('\n💥 Backup failed:', error);
        process.exit(1);
    });
