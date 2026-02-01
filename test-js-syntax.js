const https = require('https');
const vm = require('vm');

const url = 'https://findtorontoevents.ca/_next/static/chunks/a2ac3a6616d60872.js';

https.get(url, (res) => {
    let data = '';
    res.on('data', (chunk) => { data += chunk; });
    res.on('end', () => {
        try {
            new vm.Script(data, { filename: 'remote-js.js', displayErrors: true });
            console.log("✅ JavaScript is valid");
        } catch (e) {
            console.error("❌ ERROR:");
            console.error(e.message);
            console.error(e.stack);

            // Log the first few line endings and suspicious characters
            console.log("Length:", data.length);
            console.log("Hex of first 20 bytes:", Buffer.from(data.substring(0, 20)).toString('hex'));
        }
    });
});
