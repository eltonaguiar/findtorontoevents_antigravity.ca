/**
 * Backup remote MOVIESHOWS directory before deployment
 * Downloads all files from /findtorontoevents.ca/MOVIESHOWS/ to local backup
 */

const SftpClient = require('ssh2-sftp-client');
const path = require('path');
const fs = require('fs');
require('dotenv').config();

const FTP_CONFIG = {
    host: process.env.FTP_SERVER || 'ftps2.50webs.com',
    port: process.env.FTP_PORT || 22,
    username: process.env.FTP_USERNAME,
    password: process.env.FTP_PASSWORD
};

const REMOTE_PATH = '/findtorontoevents.ca/MOVIESHOWS';
const today = new Date().toISOString().split('T')[0]; // YYYY-MM-DD
const BACKUP_DIR = path.join(__dirname, `../backups/movieshows-backup-${today}`);

async function backupRemoteMovieShows() {
    const sftp = new SftpClient();

    console.log('MovieShows Remote Backup');
    console.log('========================\n');
    console.log(`Backup directory: ${BACKUP_DIR}\n`);

    try {
        // Create backup directory
        if (!fs.existsSync(BACKUP_DIR)) {
            fs.mkdirSync(BACKUP_DIR, { recursive: true });
            console.log('✓ Created backup directory\n');
        }

        console.log(`Connecting to ${FTP_CONFIG.host}...`);
        await sftp.connect(FTP_CONFIG);
        console.log('✓ Connected\n');

        // Check if remote directory exists
        const exists = await sftp.exists(REMOTE_PATH);

        if (!exists) {
            console.log('⊘ Remote MOVIESHOWS directory does not exist yet');
            console.log('   This is normal for first-time deployment\n');
            await sftp.end();
            return;
        }

        console.log('Downloading remote files...\n');

        // Download entire directory recursively
        await sftp.downloadDir(REMOTE_PATH, BACKUP_DIR);

        console.log('\n✓ Backup complete!');
        console.log(`  Location: ${BACKUP_DIR}`);

        // List what was backed up
        const files = getAllFiles(BACKUP_DIR);
        console.log(`  Files backed up: ${files.length}\n`);

        if (files.length > 0) {
            console.log('Backed up files:');
            files.forEach(file => {
                const relativePath = path.relative(BACKUP_DIR, file);
                const stats = fs.statSync(file);
                const sizeKB = (stats.size / 1024).toFixed(2);
                console.log(`  - ${relativePath} (${sizeKB} KB)`);
            });
        }

    } catch (error) {
        console.error('Backup error:', error.message);
        throw error;
    } finally {
        await sftp.end();
    }
}

/**
 * Recursively get all files in a directory
 */
function getAllFiles(dir, fileList = []) {
    const files = fs.readdirSync(dir);

    files.forEach(file => {
        const filePath = path.join(dir, file);
        if (fs.statSync(filePath).isDirectory()) {
            getAllFiles(filePath, fileList);
        } else {
            fileList.push(filePath);
        }
    });

    return fileList;
}

// Run if executed directly
if (require.main === module) {
    backupRemoteMovieShows()
        .then(() => {
            console.log('\n✓ Backup successful!');
            console.log('You can now safely deploy new files.\n');
            process.exit(0);
        })
        .catch(error => {
            console.error('\n✗ Backup failed:', error);
            process.exit(1);
        });
}

module.exports = { backupRemoteMovieShows };
