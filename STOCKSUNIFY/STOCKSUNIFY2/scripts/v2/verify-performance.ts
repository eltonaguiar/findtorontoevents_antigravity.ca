#!/usr/bin/env tsx
/**
 * STOCKSUNIFY2: Performance Verification Script
 * 
 * "Life-on-the-line" Truth Engine.
 * This script looks back at archived picks and verifies their performance.
 */

import * as fs from 'fs';
import * as path from 'path';
import { fetchStockData } from '../lib/stock-data-fetcher-enhanced';

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

    // We only verify picks that are older than X days (e.g. 7 days or 1 month)
    const today = new Date();

    for (const entry of index) {
        const pickDate = new Date(entry.date);
        const daysPassed = Math.floor((today.getTime() - pickDate.getTime()) / (1000 * 60 * 60 * 24));

        if (daysPassed >= 7) { // 7-day horizon check
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
        console.log(`  ↪ Checking ${pick.symbol}...`);
        const currentData = await fetchStockData(pick.symbol);

        if (currentData) {
            const entryPrice = pick.metrics.price || pick.price; // Fallback to recorded price
            const exitPrice = currentData.price;
            const realizedReturn = ((exitPrice - entryPrice) / entryPrice) * 100;

            verifiedPicks.push({
                ...pick,
                exitPrice,
                realizedReturn,
                verifiedAt: new Date().toISOString()
            });
        }
    }

    const resultsPath = path.join(process.cwd(), 'data', 'v2', 'performance', `${dateStr}-audit.json`);
    fs.writeFileSync(resultsPath, JSON.stringify({
        date: dateStr,
        totalPicks: verifiedPicks.length,
        avgReturn: verifiedPicks.reduce((acc, p) => acc + p.realizedReturn, 0) / verifiedPicks.length,
        picks: verifiedPicks
    }, null, 2));

    console.log(`📊 Result for ${dateStr}: ${verifiedPicks.length} verified. Stats written to disk.`);
}

main();
