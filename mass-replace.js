const fs = require('fs');
const path = require('path');

const source = 'e:/findtorontoevents.ca/_next/static/chunks/a2ac3a6616d60872.js';
const root = 'e:/findtorontoevents.ca';

function walk(dir) {
    const files = fs.readdirSync(dir);
    for (const file of files) {
        const fullPath = path.join(dir, file);
        if (fs.statSync(fullPath).isDirectory()) {
            if (file !== 'backups' && file !== 'node_modules' && file !== '.git') {
                walk(fullPath);
            }
        } else if (file === 'a2ac3a6616d60872.js') {
            if (fullPath.toLowerCase() !== source.toLowerCase()) {
                console.log(`Replacing: ${fullPath}`);
                fs.copyFileSync(source, fullPath);
            }
        }
    }
}

walk(root);
console.log("Done.");
