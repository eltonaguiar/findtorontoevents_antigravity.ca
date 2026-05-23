#!/usr/bin/env tsx
/**
 * STOCKSUNIFY2: Daily Ledger Generator
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
        const { picks, regime } = await generateScientificPicks();

        const auditObject = {
            version: '2.0.0',
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

        // 1. Immutable Archiving
        const historyDir = path.join(process.cwd(), 'data', 'v2', 'history', year, month);
        if (!fs.existsSync(historyDir)) {
            fs.mkdirSync(historyDir, { recursive: true });
        }

        const historyPath = path.join(historyDir, `${day}.json`);
        fs.writeFileSync(historyPath, JSON.stringify(auditObject, null, 2));
        console.log(`✅ Immutable Ledger created: ${historyPath}`);

        // 2. Update Index
        const indexPath = path.join(process.cwd(), 'data', 'v2', 'ledger-index.json');
        let index = [];
        if (fs.existsSync(indexPath)) {
            index = JSON.parse(fs.readFileSync(indexPath, 'utf8'));
        }

        // Remove old entry for today if exists, then add new one
        index = index.filter((e: any) => e.date !== datePortion);
        index.unshift({
            date: datePortion,
            count: picks.length,
            version: '2.0.0'
        });

        fs.writeFileSync(indexPath, JSON.stringify(index.slice(0, 31), null, 2)); // Keep 31 days in index

    } catch (error) {
        console.error('❌ CRITICAL: Audit Generation Failed', error);
        process.exit(1);
    }
}

main();
