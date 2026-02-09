#!/usr/bin/env node
/**
 * Validate JavaScript syntax of all <script> blocks in HTML files.
 *
 * Usage:
 *   node tools/check_syntax.js path/to/file.html          — check one file
 *   node tools/check_syntax.js vr/game-arena/              — check all .html in directory (recursive)
 *   node tools/check_syntax.js                             — check common game/VR HTML files
 *
 * Exit code 0 = all OK, exit code 1 = syntax errors found.
 * Skips <script type="importmap"> blocks.
 * Parses <script type="module"> as ES module, all others as script.
 */
const fs = require('fs');
const path = require('path');
const acorn = require('acorn');

// ── Collect files ──────────────────────────────────────────────────────────
function collectHtmlFiles(target) {
    const stat = fs.statSync(target);
    if (stat.isFile()) return [target];
    const results = [];
    for (const entry of fs.readdirSync(target, { withFileTypes: true })) {
        const full = path.join(target, entry.name);
        if (entry.isDirectory() && entry.name !== 'node_modules') {
            results.push(...collectHtmlFiles(full));
        } else if (entry.isFile() && /\.html?$/i.test(entry.name)) {
            results.push(full);
        }
    }
    return results;
}

// Default paths to check when no argument given
const DEFAULT_DIRS = ['vr/', 'updates/', 'stats/'];

let files = [];
const args = process.argv.slice(2);
if (args.length === 0) {
    for (const d of DEFAULT_DIRS) {
        if (fs.existsSync(d)) files.push(...collectHtmlFiles(d));
    }
    // Also check root index.html
    if (fs.existsSync('index.html')) files.push('index.html');
} else {
    for (const a of args) {
        if (!fs.existsSync(a)) { console.log(`Not found: ${a}`); continue; }
        files.push(...collectHtmlFiles(a));
    }
}

if (files.length === 0) { console.log('No HTML files to check.'); process.exit(0); }

// ── Parse ──────────────────────────────────────────────────────────────────
let totalErrors = 0;
let totalFiles = 0;
let totalBlocks = 0;

for (const file of files) {
    const html = fs.readFileSync(file, 'utf8');
    const re = /<script([^>]*)>([\s\S]*?)<\/script>/g;
    let match;
    let blockIdx = 0;
    let fileErrors = 0;
    const fileLabel = path.relative(process.cwd(), file).replace(/\\/g, '/');

    while ((match = re.exec(html)) !== null) {
        blockIdx++;
        const attrs = match[1];
        const code = match[2];
        if (!code.trim()) continue;

        // Skip importmap
        if (attrs.includes('importmap')) continue;

        const isModule = attrs.includes('module');
        const sourceType = isModule ? 'module' : 'script';

        totalBlocks++;

        try {
            acorn.parse(code, { ecmaVersion: 2022, sourceType });
        } catch (e) {
            fileErrors++;
            totalErrors++;
            // Compute HTML-file line number
            const scriptStart = match.index + match[0].indexOf('>') + 1;
            const htmlBeforeScript = html.substring(0, scriptStart);
            const scriptStartLine = htmlBeforeScript.split('\n').length;
            const errorLineInScript = e.loc ? e.loc.line : '?';
            const errorLineInFile = typeof errorLineInScript === 'number'
                ? scriptStartLine + errorLineInScript - 1 : '?';
            console.log(`  FAIL  ${fileLabel}  script#${blockIdx} (${sourceType})  line ${errorLineInFile}`);
            console.log(`        ${e.message}`);
        }
    }

    if (fileErrors === 0 && blockIdx > 0) {
        console.log(`  OK    ${fileLabel}  (${blockIdx} script block${blockIdx > 1 ? 's' : ''})`);
    }
    if (blockIdx > 0) totalFiles++;
}

console.log(`\nChecked ${totalBlocks} script blocks in ${totalFiles} files.`);
if (totalErrors > 0) {
    console.log(`FAILED: ${totalErrors} syntax error(s) found.`);
    process.exit(1);
} else {
    console.log('ALL OK — zero syntax errors.');
    process.exit(0);
}
