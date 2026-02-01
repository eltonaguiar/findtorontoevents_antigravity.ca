const fs = require('fs');
const content = fs.readFileSync('e:/findtorontoevents.ca/_next/static/chunks/a2ac3a6616d60872.js', 'utf8');
console.log("Total length:", content.length);
console.log("START:", content.substring(0, 200));
console.log("---");
console.log("END:", content.substring(content.length - 500));
