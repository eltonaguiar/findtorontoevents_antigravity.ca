const fs = require('fs');
const content = fs.readFileSync('e:/findtorontoevents.ca/_next/static/chunks/a2ac3a6616d60872.js', 'utf8');

const lastIndex = content.lastIndexOf(']);');
if (lastIndex !== -1) {
    const cleaned = content.substring(0, lastIndex + 3);
    fs.writeFileSync('e:/findtorontoevents.ca/a2ac_cleaned.js', cleaned);
    console.log(`Cleaned file saved. New length: ${cleaned.length}`);
} else {
    console.log("Could not find ']);'");
}
