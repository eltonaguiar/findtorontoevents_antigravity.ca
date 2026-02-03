/**
 * UPDATE #21: Fix All PHP 5.x Compatibility Issues
 * Converts all short array syntax to array() for PHP 5.x
 */

const fs = require('fs').promises;
const path = require('path');

async function fixPhpSyntax() {
    console.log('🔧 Fixing PHP 5.x Compatibility\n');

    const files = [
        'MOVIESHOWS/api/movies.php',
        'MOVIESHOWS/api/queue.php',
        'MOVIESHOWS/api/preferences.php',
        'MOVIESHOWS/api/playlists.php',
        'MOVIESHOWS/api/db-config.php'
    ];

    let totalFixed = 0;

    for (const file of files) {
        const filePath = path.join(__dirname, '..', file);
        console.log(`Processing: ${file}`);

        try {
            let content = await fs.readFile(filePath, 'utf8');
            const original = content;

            // Fix short array syntax: ['key' => 'value'] to array('key' => 'value')
            // Match patterns like ['...'] or ["..."] but not inside strings
            content = content.replace(/(\W)\[([^\]]*=>)/g, '$1array($2');
            content = content.replace(/\]/g, (match, offset) => {
                // Check if this ] closes an array
                const before = content.substring(Math.max(0, offset - 100), offset);
                if (before.includes('array(') && !before.includes(')')) {
                    return ')';
                }
                return match;
            });

            if (content !== original) {
                await fs.writeFile(filePath, content, 'utf8');
                console.log(`  ✓ Fixed\n`);
                totalFixed++;
            } else {
                console.log(`  - No changes needed\n`);
            }
        } catch (error) {
            console.log(`  ✗ Error: ${error.message}\n`);
        }
    }

    console.log(`\n✅ Fixed ${totalFixed} files`);
}

fixPhpSyntax();
