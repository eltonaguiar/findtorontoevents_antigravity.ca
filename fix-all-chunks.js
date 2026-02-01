const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const chunksDir = 'e:/findtorontoevents.ca/_next/static/chunks';
const files = fs.readdirSync(chunksDir);

for (const file of files) {
    if (file.endsWith('.js')) {
        const filePath = path.join(chunksDir, file);
        try {
            execSync(`node -c "${filePath}"`, { stdio: 'ignore' });
        } catch (e) {
            console.log(`❌ CORRUPTED: ${file}`);

            // Try to fix it if it has the known corruption pattern
            let content = fs.readFileSync(filePath, 'utf8');
            const endPattern = 'e.s(["default",()=>a])}]);';
            const index = content.indexOf(endPattern);
            if (index !== -1) {
                const cleaned = content.substring(0, index + endPattern.length);
                fs.writeFileSync(filePath, cleaned);
                console.log(`   ✅ Cleaned ${file}. New length: ${cleaned.length}`);

                // Verify again
                try {
                    execSync(`node -c "${filePath}"`, { stdio: 'ignore' });
                    console.log(`   ✅ Verification successful.`);
                } catch (vErr) {
                    console.log(`   ⚠️ Cleaning didn't fix it fully. Still has syntax errors.`);
                }
            } else {
                console.log(`   ⚠️ Could not find end pattern in ${file}.`);
            }
        }
    }
}
