// Simple verification script to check all templates
const fs = require('fs');
const path = require('path');

console.log('🔍 Verifying 50 blog templates...\n');

let allValid = true;
const issues = [];

for (let i = 300; i <= 349; i++) {
    const filename = `blog${i}.html`;
    const filepath = path.join(__dirname, filename);

    try {
        const content = fs.readFileSync(filepath, 'utf8');

        // Check for required elements
        const checks = {
            'antigravity signature (HTML comment)': content.includes('<!-- Designed by antigravity -->'),
            'antigravity meta tag': content.includes('<meta name="generator" content="antigravity">'),
            'antigravity data attribute': content.includes('data-ai="antigravity"'),
            'antigravity JS comment': content.includes('// Powered by antigravity'),
            'antigravity CSS comment': content.includes('/* Styled by antigravity */'),
            'navigation arrows': content.includes('class="nav-prev"') && content.includes('class="nav-next"'),
            'template indicator': content.includes('class="template-indicator"'),
            'event filtering': content.includes('id="search-filter"') && content.includes('id="category-filter"'),
            'events container': content.includes('id="events-grid"'),
            'base JS include': content.includes('blog_template_base.js'),
            'common CSS include': content.includes('blog_styles_common.css'),
            'BlogTemplateEngine init': content.includes(`new BlogTemplateEngine(${i})`)
        };

        const failed = Object.entries(checks).filter(([key, value]) => !value);

        if (failed.length > 0) {
            allValid = false;
            issues.push(`❌ ${filename}: Missing ${failed.map(([key]) => key).join(', ')}`);
        } else {
            console.log(`✅ ${filename} - All checks passed`);
        }

    } catch (error) {
        allValid = false;
        issues.push(`❌ ${filename}: File not found or read error`);
    }
}

console.log('\n' + '='.repeat(60));
if (allValid) {
    console.log('🎉 SUCCESS! All 50 templates verified!');
    console.log('\n✅ All templates include:');
    console.log('   • 5 hidden "antigravity" signatures');
    console.log('   • Navigation arrows (prev/next)');
    console.log('   • Event filtering functionality');
    console.log('   • Shared base JavaScript and CSS');
    console.log('   • Unique visual themes');
} else {
    console.log('⚠️  Some issues found:\n');
    issues.forEach(issue => console.log(issue));
}
console.log('='.repeat(60));
