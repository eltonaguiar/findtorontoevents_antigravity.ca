const ftp = require('basic-ftp');
const fs = require('fs');
const path = require('path');

async function deployFix() {
  const client = new ftp.Client();
  client.ftp.verbose = true;

  try {
    console.log('=== Deploying Mercy Trailer Fix ===\n');

    // Read credentials from environment or config
    const host = process.env.FTP_HOST || 'ftp.findtorontoevents.ca';
    const user = process.env.FTP_USER || 'findtorontoevents.ca';
    const password = process.env.FTP_PASS;

    if (!password) {
      console.error('❌ FTP password not set. Set FTP_PASS environment variable.');
      process.exit(1);
    }

    console.log(`Connecting to ${host}...`);
    await client.access({
      host,
      user,
      password,
      secure: false
    });

    console.log('✅ Connected\n');

    // Navigate to MOVIESHOWS3 directory
    console.log('Navigating to MOVIESHOWS3...');
    await client.cd('MOVIESHOWS3');
    console.log('✅ In MOVIESHOWS3 directory\n');

    // Backup current index.html
    const timestamp = Date.now();
    const backupName = `index.html.backup_${timestamp}`;
    console.log(`Creating backup: ${backupName}`);
    await client.rename('index.html', backupName);
    console.log('✅ Backup created\n');

    // Upload fixed index.html
    const localPath = path.join(__dirname, 'fte_clone/TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/index.html');
    console.log('Uploading fixed index.html...');
    await client.uploadFrom(localPath, 'index.html');
    console.log('✅ Fixed index.html uploaded\n');

    // Verify upload
    const size = await client.size('index.html');
    console.log(`✅ Uploaded file size: ${size} bytes\n`);

    console.log('=== Deployment Complete ===');
    console.log('\nThe Mercy trailer fix has been deployed.');
    console.log('Test by:');
    console.log('1. Going to https://findtorontoevents.ca/MOVIESHOWS3/');
    console.log('2. Clicking the magnifying glass (search)');
    console.log('3. Typing "Mercy"');
    console.log('4. Clicking on the Mercy movie card');
    console.log('\nThe trailer should now play correctly!');

  } catch (err) {
    console.error('❌ Deployment failed:', err.message);
    process.exit(1);
  } finally {
    client.close();
  }
}

deployFix();
