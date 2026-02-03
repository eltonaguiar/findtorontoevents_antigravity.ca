#!/usr/bin/env node

const SftpClient = require('ssh2-sftp-client');
const path = require('path');

const sftp = new SftpClient();

const config = {
    host: 'ftps2.50webs.com',
    port: 22,
    username: 'ejaguiar1',
    password: '$a^FzN7BqKapSQMsZxD&^FeTJ',
    readyTimeout: 30000,
    retries: 3
};

const localPath = path.join(__dirname, 'index.html');
const remotePath = '/findtorontoevents.ca/MOVIESHOWS2';

console.log('🚀 Deploying MOVIESHOWS2...\n');

async function deploy() {
    try {
        console.log('🔌 Connecting...');
        await sftp.connect(config);
        console.log('✅ Connected!\n');

        console.log('📁 Creating MOVIESHOWS2 directory...');
        await sftp.mkdir(remotePath, true);
        console.log('✅ Directory created!\n');

        console.log('📤 Uploading index.html...');
        await sftp.put(localPath, `${remotePath}/index.html`);
        console.log('✅ Upload complete!\n');

        await sftp.end();

        console.log('🎉 Deployment successful!');
        console.log('🌐 Live at: https://findtorontoevents.ca/MOVIESHOWS2/\n');

    } catch (err) {
        console.error('❌ Error:', err.message);
        process.exit(1);
    }
}

deploy();
