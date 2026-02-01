const fs = require('fs');

function cleanFile(path) {
    let content = fs.readFileSync(path, 'utf8');
    console.log(`Cleaning ${path}...`);

    // The corruption seems to be that a piece of the file was appended.
    // The real end should be the first index of the pattern that ends the push() call.
    // In Turbopack chunks, this is often "]);"

    // BUT, we have multiple modules inside. Each has its own ");" or similar.
    // The final one corresponds to the (globalThis.TURBOPACK... ).push([...]);

    // Let's find the first occurrence of the repetition.
    // We saw "or Toronto • Antigravity Systems v0.5.0" repeated.
    const pattern = '}]);or Toronto \u2022 Antigravity Systems v0.5.0';
    const index = content.indexOf(pattern);

    if (index !== -1) {
        // The real end is at the "}]]);" part before the repetition.
        // Wait, the pattern starts with "}]);"
        const cleaned = content.substring(0, index + 4); // Include the "}]);"

        // Check if it's now valid
        try {
            const vm = require('vm');
            new vm.Script(cleaned);
            console.log("✅ FIXED!");
            fs.writeFileSync(path, cleaned);
        } catch (e) {
            console.log("❌ Partial fix failed syntax check:", e.message);

            // Try another approach: find the first "]);" after 50% of the file
            const mid = Math.floor(content.length / 2);
            const patterns = [
                'e.s(["default",()=>a])}]);',
                'e.s(["default",()=>n])}]);'
            ];

            for (let p of patterns) {
                const idx = content.indexOf(p);
                if (idx !== -1) {
                    const cleaned2 = content.substring(0, idx + p.length);
                    try {
                        new vm.Script(cleaned2);
                        console.log(`✅ FIXED with pattern ${p}`);
                        fs.writeFileSync(path, cleaned2);
                        return;
                    } catch (e2) { }
                }
            }
        }
    } else {
        console.log("Pattern not found.");
    }
}

cleanFile('e:/findtorontoevents.ca/_next/static/chunks/a2ac3a6616d60872.js');
