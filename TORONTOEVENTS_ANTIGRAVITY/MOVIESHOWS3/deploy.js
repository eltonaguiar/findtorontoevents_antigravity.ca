#!/usr/bin/env node

/**
 * Deploy MOVIESHOWS2 to findtorontoevents.ca via SFTP
 */

const SftpClient = require('ssh2-sftp-client');
const path = require('path');
const fs = require('fs');
require('dotenv').config();

const sftp = new SftpClient();

const config = {
    host: process.env.FTP_SERVER || 'ftps2.50webs.com',
    port: 22,
    username: process.env.FTP_USERNAME || 'ejaguiar1',
    password: process.env.FTP_PASSWORD?.replace(/"/g, '') || '',
    readyTimeout: 30000,
    retries: 2,
    retry_minTimeout: 2000
};

const localPath = path.join(__dirname, 'index.html');
const remotePath = '/findtorontoevents.ca/movieshows2';

console.log('🚀 Deploying MOVIESHOWS2 to findtorontoevents.ca...\n');
console.log('📋 Configuration:');
console.log(`   Host: ${config.host}`);
console.log(`   User: ${config.username}`);
console.log(`   Remote: ${remotePath}`);
console.log(`   Local: ${localPath}\n`);

async function deploy() {
    try {
        console.log('🔌 Connecting to SFTP server...');
        await sftp.connect(config);
        console.log('✅ Connected!\n');

        // Check if MOVIESHOWS2 directory exists, create if not
        console.log('📁 Checking remote directory...');
        const exists = await sftp.exists(remotePath);

        if (!exists) {
            console.log('📁 Creating MOVIESHOWS2 directory...');
            await sftp.mkdir(remotePath, true);
            console.log('✅ Directory created!\n');
        } else {
            console.log('✅ Directory exists!\n');
        }

        // Upload index.html
        console.log('📤 Uploading index.html...');
        const remoteFile = `${remotePath}/index.html`;
        await sftp.put(localPath, remoteFile);
        console.log('✅ Upload complete!\n');

        // Verify upload
        console.log('🔍 Verifying upload...');
        const fileExists = await sftp.exists(remoteFile);
        if (fileExists) {
            const stat = await sftp.stat(remoteFile);
            console.log(`✅ File verified! Size: ${stat.size} bytes\n`);
        }

        await sftp.end();

        console.log('🎉 Deployment successful!\n');
        console.log('🌐 Your site is now live at:');
        console.log('   https://findtorontoevents.ca/MOVIESHOWS2/\n');
        console.log('📝 Next steps:');
        console.log('   1. Visit the URL above to verify');
        console.log('   2. Test the tooltip on "v1.0 (Original)" link');
        console.log('   3. Check that links to /MOVIESHOWS work');
        console.log('   4. Test pricing cards and feature interactions\n');
        console.log('✨ Done!');

    } catch (err) {
        console.error('❌ Deployment failed:', err.message);
        if (err.code === 'ECONNREFUSED') {
            console.error('\n💡 Connection refused. Please check:');
            console.error('   - FTP server is accessible');
            console.error('   - Port 22 is not blocked by firewall');
            console.error('   - Credentials are correct');
        }
        process.exit(1);
    }
}

// Run deployment
deploy();
