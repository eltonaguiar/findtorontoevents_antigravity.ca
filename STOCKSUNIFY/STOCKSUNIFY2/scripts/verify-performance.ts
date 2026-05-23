#!/usr/bin/env tsx
/**
 * STOCKSUNIFY2: Performance Verification Script
 */

import * as fs from 'fs';
import * as path from 'path';
import { fetchStockData } from './lib/stock-data-fetcher-enhanced';

async function main() {
    console.log('🏁 STOCKSUNIFY2: Truth Engine Initializing...');

    const indexPath = path.join(process.cwd(), 'data', 'v2', 'ledger-index.json');
    if (!fs.existsSync(indexPath)) {
        console.error('❌ Ledger index missing. Nothing to verify.');
        return;
    }

    const index = JSON.parse(fs.readFileSync(indexPath, 'utf8'));
    const performanceDir = path.join(process.cwd(), 'data', 'v2', 'performance');
    if (!fs.existsSync(performanceDir)) {
        fs.mkdirSync(performanceDir, { recursive: true });
    }

    const today = new Date();

    // Check last 7 days of index
    for (const entry of index.slice(0, 7)) {
        const pickDate = new Date(entry.date);
        const daysPassed = Math.floor((today.getTime() - pickDate.getTime()) / (1000 * 60 * 60 * 24));

        if (daysPassed >= 1) { // We can verify even 1 day later
            console.log(`🔍 Verifying picks from ${entry.date} (${daysPassed} days ago)...`);
            await verifyLedger(entry.date);
        }
    }
}

async function verifyLedger(dateStr: string) {
    const [year, month, day] = dateStr.split('-');
    const ledgerPath = path.join(process.cwd(), 'data', 'v2', 'history', year, month, `${day}.json`);

    if (!fs.existsSync(ledgerPath)) return;

    const ledger = JSON.parse(fs.readFileSync(ledgerPath, 'utf8'));
    const verifiedPicks = [];

    for (const pick of ledger.picks) {
        process.stdout.write(`  ↪ Checking ${pick.symbol}... `);
        const currentData = await fetchStockData(pick.symbol);

        if (currentData) {
            const entryPrice = pick.price;
            const exitPrice = currentData.price;
            const realizedReturn = ((exitPrice - entryPrice) / entryPrice) * 100;

            verifiedPicks.push({
                ...pick,
                exitPrice,
                realizedReturn,
                verifiedAt: new Date().toISOString()
            });
            console.log(`${realizedReturn.toFixed(2)}%`);
        } else {
            console.log(`Failed (API Skip)`);
        }
    }

    const resultsPath = path.join(process.cwd(), 'data', 'v2', 'performance', `${dateStr}-audit.json`);
    fs.writeFileSync(resultsPath, JSON.stringify({
        date: dateStr,
        totalPicks: verifiedPicks.length,
        avgReturn: verifiedPicks.length > 0 ? verifiedPicks.reduce((acc, p) => acc + p.realizedReturn, 0) / verifiedPicks.length : 0,
        picks: verifiedPicks
    }, null, 2));

    console.log(`📊 Result for ${dateStr}: ${verifiedPicks.length} verified.`);
}

main();
