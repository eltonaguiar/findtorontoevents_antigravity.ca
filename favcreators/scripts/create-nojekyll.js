import fs from 'fs';
import path from 'path';

const docsDir = path.resolve('docs');
const nojekyllPath = path.join(docsDir, '.nojekyll');

if (fs.existsSync(docsDir)) {
    fs.writeFileSync(nojekyllPath, '');
    console.log('.nojekyll file created in docs/');
} else {
    console.error('docs directory not found. Run build first.');
    process.exit(1);
}
