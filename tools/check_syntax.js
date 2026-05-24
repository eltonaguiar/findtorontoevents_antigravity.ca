#!/usr/bin/env node
// Static syntax checker for inline non-module scripts in HTML files.
const fs = require('fs');
const path = require('path');
const acorn = require('acorn');

function extractScripts(html) {
  const scripts = [];
  const re = /<script\b([^>]*)>([\s\S]*?)<\/script>/gi;
  let m;
  while ((m = re.exec(html)) !== null) {
    const attrs = m[1] || '';
    const typeMatch = attrs.match(/\btype\s*=\s*["']?([^"'\s>]+)/i);
    const type = typeMatch ? typeMatch[1].toLowerCase() : '';
    const jsTypes = {
      '': true,
      'text/javascript': true,
      'application/javascript': true,
      'application/ecmascript': true,
      'text/ecmascript': true
    };
    if (!jsTypes[type]) continue;
    const startLine = html.slice(0, m.index).split(/\r\n|\r|\n/).length;
    scripts.push({ code: m[2], startLine });
  }
  return scripts;
}

function checkFile(file) {
  const html = fs.readFileSync(file, 'utf8');
  const scripts = extractScripts(html);
  let ok = true;
  for (let i = 0; i < scripts.length; i++) {
    const script = scripts[i];
    try {
      acorn.parse(script.code, { ecmaVersion: 2022, sourceType: 'script' });
    } catch (err) {
      ok = false;
      const line = script.startLine + (err.loc ? err.loc.line - 1 : 0);
      const col = err.loc ? err.loc.column : 0;
      console.error(`${file}:${line}:${col}: script ${i + 1}: ${err.message}`);
    }
  }
  if (ok) console.log(`${file}: OK (${scripts.length} script blocks)`);
  return ok;
}

function walk(target) {
  const stat = fs.statSync(target);
  if (!stat.isDirectory()) return [target];
  const out = [];
  for (const name of fs.readdirSync(target)) {
    if (name === 'node_modules' || name === '.git') continue;
    const child = path.join(target, name);
    const childStat = fs.statSync(child);
    if (childStat.isDirectory()) out.push(...walk(child));
    else if (name.endsWith('.html')) out.push(child);
  }
  return out;
}

const args = process.argv.slice(2);
if (args.length === 0) {
  console.error('Usage: node tools/check_syntax.js <file-or-dir> [...]');
  process.exit(2);
}

let ok = true;
for (const arg of args) {
  for (const file of walk(arg)) {
    if (file.endsWith('.html')) ok = checkFile(file) && ok;
  }
}
process.exit(ok ? 0 : 1);
