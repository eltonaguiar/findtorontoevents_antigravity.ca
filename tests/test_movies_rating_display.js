const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { execFileSync } = require('node:child_process');
const { test } = require('node:test');
const acorn = require('acorn');

const root = path.resolve(__dirname, '..');
const ms2 = path.join(root, 'TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2');
const scrollSource = fs.readFileSync(path.join(ms2, 'scroll-fix.js'), 'utf8');
const ast = acorn.parse(scrollSource, { ecmaVersion: 'latest' });

function findNode(node, predicate) {
    if (!node || typeof node !== 'object') return null;
    if (predicate(node)) return node;
    for (const value of Object.values(node)) {
        for (const child of Array.isArray(value) ? value : [value]) {
            const found = findNode(child, predicate);
            if (found) return found;
        }
    }
    return null;
}

function transform(movie) {
    const node = findNode(ast, n => n.type === 'FunctionDeclaration' && n.id.name === 'transformDbMovie');
    return vm.runInNewContext(`(${scrollSource.slice(node.start, node.end)})`)(movie);
}

function ratingBadge(movie) {
    const render = findNode(ast, n => n.type === 'FunctionDeclaration' && n.id.name === 'createSlide');
    const node = findNode(render, n => n.type === 'VariableDeclarator' && n.id.name === 'rating');
    return vm.runInNewContext(scrollSource.slice(node.init.start, node.init.end), { movie });
}

test('default MS2 feed uses newest titles, not the ten perfect-score outliers', () => {
    const source = fs.readFileSync(path.join(ms2, 'api/get-movies.php'), 'utf8');
    const sql = source.match(/\$pdo->query\("([\s\S]*?)"\)/)[1];
    const result = JSON.parse(execFileSync('python3', ['-c', `
import json, sqlite3, sys
db = sqlite3.connect(':memory:')
db.row_factory = sqlite3.Row
db.executescript("""
CREATE TABLE movies (id INTEGER, title TEXT, type TEXT, genre TEXT, description TEXT,
 release_year INTEGER, imdb_rating REAL, imdb_id TEXT, tmdb_id INTEGER, runtime INTEGER, created_at TEXT);
CREATE TABLE trailers (id INTEGER, movie_id INTEGER, youtube_id TEXT, is_active INTEGER);
CREATE TABLE thumbnails (movie_id INTEGER, url TEXT, is_primary INTEGER);
""")
for i in range(14):
    rating = 10.0 if i < 10 else [6.4, 7.2, 8.1, 7.8][i - 10]
    db.execute("INSERT INTO movies VALUES (?, ?, 'movie', 'Drama', '', 2026, ?, '', ?, 90, ?)",
               (i, 'Title ' + str(i), rating, i, '2026-10-' + str(i + 1).zfill(2)))
    db.execute("INSERT INTO trailers VALUES (?, ?, ?, 1)", (i, i, 'trailer-' + str(i)))
rows = [dict(row) for row in db.execute(sys.stdin.read())]
print(json.dumps(rows))
`], { input: sql, encoding: 'utf8' }));
    assert.equal(result.length, 14);
    assert.equal(result[0].id, 13);
    assert.ok(new Set(result.slice(0, 10).map(m => m.imdb_rating)).size > 1);
    assert.equal(result.filter(m => m.imdb_rating === 10).length, 10, 'real tens must not be clamped away');
});

test('database badges identify TMDB rather than falsely claiming IMDb verification', () => {
    assert.equal(ratingBadge(transform({ imdb_rating: '7.2' })), 'TMDB 7.2');
    assert.equal(ratingBadge(transform({ imdb_rating: '10.0' })), 'TMDB 10.0');
    assert.equal(ratingBadge({ rating: '8.5' }), 'Rating 8.5', 'unattributed static data is not IMDb-verified');
});

test('database mapping preserves the real rating distribution', () => {
    const ratings = ['0.0', '6.4', '7.2', '8.1', '10.0', null];
    assert.deepEqual(ratings.map(imdb_rating => transform({ imdb_rating }).rating),
        ['0.0', '6.4', '7.2', '8.1', '10.0', '']);
    assert.equal(ratingBadge(transform({ imdb_rating: null })), 'TBD');
});

test('both get-movies APIs document the legacy field source and ten-point scale', () => {
    for (const app of ['MOVIESHOWS2', 'MOVIESHOWS3']) {
        const source = fs.readFileSync(path.join(root, 'TORONTOEVENTS_ANTIGRAVITY', app, 'api/get-movies.php'), 'utf8');
        assert.ok(/'rating_source'\s*=>\s*'TMDB'/.test(source), `${app}: missing TMDB rating provenance`);
        assert.ok(/'rating_scale'\s*=>\s*10/.test(source), `${app}: missing ten-point scale`);
        assert.match(source, /m\.imdb_rating/, 'keep the backwards-compatible column');
    }
});

test('background pagination follows the same newest ordering without changing top-rated callers', () => {
    const source = fs.readFileSync(path.join(ms2, 'api/movies.php'), 'utf8');
    assert.ok(source.includes("$_GET['sort'] === 'newest'"), 'list API needs opt-in newest sorting');
    assert.ok(source.includes("'m.created_at DESC, m.id DESC'"), 'newest tie-breaker must match get-movies');
    assert.ok(source.includes("'m.imdb_rating DESC, m.created_at DESC'"), 'preserve default top-rated lists');
    assert.ok(scrollSource.includes("&sort=newest"), 'background pages must match the initial query');
});

test('real slide DOM renders varied scores and retains a genuine ten', async () => {
    const { chromium } = require('playwright');
    const browser = await chromium.launch({ headless: true });
    try {
        const page = await browser.newPage();
        await page.route('**/*', route => route.abort());
        const functions = ['transformDbMovie', 'createSlide'].map(name => {
            const node = findNode(ast, n => n.type === 'FunctionDeclaration' && n.id.name === name);
            return scrollSource.slice(node.start, node.end);
        }).join('\n');
        await page.addScriptTag({ content: `function getYouTubeEmbedUrl() { return 'about:blank'; }\n${functions}` });
        const badges = await page.evaluate(() => {
            for (const imdb_rating of ['6.4', '7.2', '8.1', '10.0', null]) {
                document.body.appendChild(createSlide(transformDbMovie({ title: 'Fixture', imdb_rating })));
            }
            return [...document.querySelectorAll('.bg-yellow-500')].map(el => el.textContent);
        });
        assert.deepEqual(badges, ['TMDB 6.4', 'TMDB 7.2', 'TMDB 8.1', 'TMDB 10.0', 'TBD']);
    } finally {
        await browser.close();
    }
});
