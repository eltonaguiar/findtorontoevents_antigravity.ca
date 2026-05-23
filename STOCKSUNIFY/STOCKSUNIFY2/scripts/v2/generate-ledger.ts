#!/usr/bin/env tsx
/**
 * STOCKSUNIFY2: Daily Ledger Generator
 * 
 * This is the core "Scientific" generation script.
 * Rules:
 * 1. Every pick is timestamped and versioned.
 * 2. Data is saved in a deep-nested date structure for immutable archiving.
 * 3. A "current" pointer is created for the live site.
 */

import * as fs from 'fs';
import * as path from 'path';
import { generateScientificPicks } from './lib/v2-engine';


async function main() {
    console.log('🔬 STOCKSUNIFY2: Initializing Deep Research Audit...');

    const timestamp = new Date();
    const dateStr = timestamp.toISOString();
    const [datePortion] = dateStr.split('T'); // YYYY-MM-DD
    const [year, month, day] = datePortion.split('-');

    try {
        // 1. Generate Picks using the V2 Engine
        const { picks, regime } = await generateScientificPicks();

        const auditObject = {
            version: '2.0.0-alpha',
            date: datePortion,
            timestamp: dateStr,
            regime,
            metadata: {
                engine: 'STOCKSUNIFY2-Scientific',
                system: process.platform,
                checksPerformed: ['Purging', 'Slippage-Stress', 'Regime-Detection']
            },
            picks: picks.map((p: any) => ({
                ...p,
                audit_id: `v2-${p.symbol}-${timestamp.getTime()}`
            }))

        };

        // 2. Immutable Archiving
        const historyDir = path.join(process.cwd(), 'data', 'v2', 'history', year, month);
        if (!fs.existsSync(historyDir)) {
            fs.mkdirSync(historyDir, { recursive: true });
        }

        const historyPath = path.join(historyDir, `${day}.json`);
        fs.writeFileSync(historyPath, JSON.stringify(auditObject, null, 2));
        console.log(`✅ Immutable Ledger created: ${historyPath}`);

        // 3. Live Site Synchronization
        const livePath = path.join(process.cwd(), 'public', 'data', 'v2', 'current.json');
        const liveDir = path.dirname(livePath);
        if (!fs.existsSync(liveDir)) {
            fs.mkdirSync(liveDir, { recursive: true });
        }
        fs.writeFileSync(livePath, JSON.stringify(auditObject, null, 2));
        console.log(`✅ Live Site Synchronized: ${livePath}`);

        // 4. Update the verification index (optional but recommended)
        updateVerificationIndex(auditObject);

    } catch (error) {
        console.error('❌ CRITICAL: Audit Generation Failed', error);
        process.exit(1);
    }
}

function updateVerificationIndex(audit: any) {
    const indexPath = path.join(process.cwd(), 'data', 'v2', 'ledger-index.json');
    let index = [];
    if (fs.existsSync(indexPath)) {
        index = JSON.parse(fs.readFileSync(indexPath, 'utf8'));
    }

    index.push({
        date: audit.timestamp.split('T')[0],
        count: audit.picks.length,
        version: audit.version
    });

    // Keep only last 30 days in index for lightness
    if (index.length > 30) index.shift();

    fs.writeFileSync(indexPath, JSON.stringify(index, null, 2));
}

main();
