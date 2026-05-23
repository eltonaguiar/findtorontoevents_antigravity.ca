import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

/**
 * Comprehensive end-to-end test for the audit dashboard Excel export.
 * Validates that:
 *   1. Dashboard loads with data
 *   2. Export buttons exist and are clickable
 *   3. Active picks CSV has all 34 audit columns
 *   4. Closed picks CSV has all 26 audit columns
 *   5. Every pick has a non-empty Entry Reason, Direction Reason, Score Breakdown
 *   6. Consensus picks have per-system explanations
 *   7. Score and Grade columns are populated and consistent
 *   8. No JS errors during export
 */

const ACTIVE_HEADERS = [
  'Symbol','Direction','Direction Reason','System','Strategy',
  'Entry Price','Live Price','PnL%','TP','SL','R:R',
  'Score','Grade','Score Breakdown (English)',
  'Confidence','Trust Tier','Trust Reason',
  'Forward WR','Forward Trades','Forward Validated',
  'Confluence Count','Consensus System Reasons',
  'Entry Reason (Raw)','Entry Reason (Full Audit)',
  'Market Regime','Regime Sentinel','Regime Adjustment',
  'Strategy Description','System Description',
  'Status','Asset Class','Timeframe','Age (hours)','Picked At'
];

const CLOSED_HEADERS = [
  'Symbol','Direction','Direction Reason','System','Strategy',
  'Entry Price','Exit Price','PnL%','Exit Reason',
  'Score','Grade','Score Breakdown (English)',
  'Trust Tier','Trust Reason',
  'Forward WR','Forward Trades',
  'Confluence Count','Consensus System Reasons',
  'Entry Reason (Raw)','Entry Reason (Full Audit)',
  'Strategy Description','System Description',
  'Asset Class','Timeframe','Entry Time','Exit Time'
];

function parseCSV(content: string): string[][] {
  // Simple CSV parser that handles quoted fields with commas
  const lines = content.split('\n').filter(l => l.trim());
  return lines.map(line => {
    const row: string[] = [];
    let current = '';
    let inQuotes = false;
    for (let i = 0; i < line.length; i++) {
      const ch = line[i];
      if (ch === '"') {
        if (inQuotes && line[i + 1] === '"') {
          current += '"';
          i++;
        } else {
          inQuotes = !inQuotes;
        }
      } else if (ch === ',' && !inQuotes) {
        row.push(current);
        current = '';
      } else {
        current += ch;
      }
    }
    row.push(current);
    return row;
  });
}

test.describe('Audit Dashboard Export — Comprehensive Validation', () => {
  test.setTimeout(60000);

  test('Active picks export has all audit columns and populated fields', async ({ page }) => {
    const jsErrors: string[] = [];
    page.on('pageerror', err => jsErrors.push(err.message));

    // Navigate to dashboard
    await page.goto('/audit_dashboard/index.html', { waitUntil: 'networkidle' });

    // Wait for data to load
    await page.waitForFunction(() => {
      return document.querySelector('.stat-card .value') !== null;
    }, { timeout: 15000 });

    // Check export button exists
    const exportBtn = page.locator('#btn-export-excel');
    await expect(exportBtn).toBeVisible();

    // Set up download listener
    const downloadPromise = page.waitForEvent('download', { timeout: 15000 });
    await exportBtn.click();
    const download = await downloadPromise;

    // Save file and read contents
    const filePath = path.join('test-results', download.suggestedFilename());
    await download.saveAs(filePath);
    const content = fs.readFileSync(filePath, 'utf-8').replace(/^\uFEFF/, ''); // strip BOM
    const rows = parseCSV(content);

    // 1. Validate headers
    const headers = rows[0];
    console.log(`Active export: ${headers.length} columns, ${rows.length - 1} data rows`);
    for (const expected of ACTIVE_HEADERS) {
      expect(headers, `Missing header: ${expected}`).toContain(expected);
    }

    // 2. Validate each data row
    const dataRows = rows.slice(1);
    expect(dataRows.length).toBeGreaterThan(0);

    const symbolIdx = headers.indexOf('Symbol');
    const dirIdx = headers.indexOf('Direction');
    const dirReasonIdx = headers.indexOf('Direction Reason');
    const scoreIdx = headers.indexOf('Score');
    const gradeIdx = headers.indexOf('Grade');
    const scoreBreakdownIdx = headers.indexOf('Score Breakdown (English)');
    const trustIdx = headers.indexOf('Trust Tier');
    const consensusIdx = headers.indexOf('Consensus System Reasons');
    const rawReasonIdx = headers.indexOf('Entry Reason (Raw)');
    const fullAuditIdx = headers.indexOf('Entry Reason (Full Audit)');
    const regimeIdx = headers.indexOf('Market Regime');

    let emptyDirReasons = 0;
    let emptyScoreBreakdowns = 0;
    let emptyConsensusReasons = 0;
    let emptyFullAudit = 0;
    let scoreGradeMismatches = 0;

    for (let i = 0; i < dataRows.length; i++) {
      const row = dataRows[i];
      const symbol = row[symbolIdx] || '(unknown)';

      // Direction Reason should never be empty
      if (!row[dirReasonIdx]?.trim()) emptyDirReasons++;

      // Score Breakdown should never be empty
      if (!row[scoreBreakdownIdx]?.trim()) emptyScoreBreakdowns++;

      // Consensus reasons should never be empty
      if (!row[consensusIdx]?.trim()) emptyConsensusReasons++;

      // Full audit reason should never be empty
      if (!row[fullAuditIdx]?.trim()) emptyFullAudit++;

      // Score and grade consistency
      const score = parseInt(row[scoreIdx] || '0');
      const grade = row[gradeIdx] || '';
      if (score >= 80 && grade !== 'A') scoreGradeMismatches++;
      else if (score >= 70 && score < 80 && grade !== 'B') scoreGradeMismatches++;
      else if (score >= 55 && score < 70 && grade !== 'C') scoreGradeMismatches++;
      else if (score >= 40 && score < 55 && grade !== 'D') scoreGradeMismatches++;
      else if (score < 40 && grade !== 'F') scoreGradeMismatches++;

      // Score breakdown should contain expected markers
      const bd = row[scoreBreakdownIdx] || '';
      if (bd) {
        expect(bd, `Pick ${symbol}: breakdown missing Strategy component`).toContain('Strategy:');
        expect(bd, `Pick ${symbol}: breakdown missing Signal component`).toContain('Signal:');
        expect(bd, `Pick ${symbol}: breakdown missing Freshness component`).toContain('Freshness:');
        expect(bd, `Pick ${symbol}: breakdown missing FINAL SCORE`).toContain('FINAL SCORE:');
        expect(bd, `Pick ${symbol}: breakdown missing Trust`).toContain('Trust:');
        expect(bd, `Pick ${symbol}: breakdown missing Time decay`).toContain('Time decay:');
      }

      // Log first 3 picks for manual review
      if (i < 3) {
        console.log(`\n--- Pick ${i + 1}: ${symbol} ${row[dirIdx]} ---`);
        console.log(`  Score: ${score}${grade} | Trust: ${row[trustIdx]}`);
        console.log(`  Dir Reason: ${(row[dirReasonIdx] || '').substring(0, 120)}...`);
        console.log(`  Score Breakdown: ${(bd).substring(0, 200)}...`);
        console.log(`  Consensus: ${(row[consensusIdx] || '').substring(0, 150)}...`);
        console.log(`  Full Audit: ${(row[fullAuditIdx] || '').substring(0, 150)}...`);
        console.log(`  Regime: ${row[regimeIdx]}`);
      }
    }

    // Summary assertions
    console.log(`\n=== Active Export Summary ===`);
    console.log(`Total picks: ${dataRows.length}`);
    console.log(`Empty direction reasons: ${emptyDirReasons}`);
    console.log(`Empty score breakdowns: ${emptyScoreBreakdowns}`);
    console.log(`Empty consensus reasons: ${emptyConsensusReasons}`);
    console.log(`Empty full audit: ${emptyFullAudit}`);
    console.log(`Score/grade mismatches: ${scoreGradeMismatches}`);

    // Core audit requirements: EVERY pick must have these
    expect(emptyScoreBreakdowns, 'Score breakdowns should be populated for all picks').toBe(0);
    expect(emptyConsensusReasons, 'Consensus reasons should be populated for all picks').toBe(0);
    expect(emptyFullAudit, 'Full audit reasons should be populated for all picks').toBe(0);
    expect(scoreGradeMismatches, 'Score/grade should be consistent').toBe(0);

    // Direction reason can fallback to default text, so allow some flexibility
    expect(emptyDirReasons, 'Direction reasons should be populated').toBe(0);

    // No JS errors
    expect(jsErrors, 'No JS errors during export').toEqual([]);
  });

  test('Closed picks export has all audit columns and populated fields', async ({ page }) => {
    const jsErrors: string[] = [];
    page.on('pageerror', err => jsErrors.push(err.message));

    await page.goto('/audit_dashboard/index.html', { waitUntil: 'networkidle' });
    await page.waitForFunction(() => document.querySelector('.stat-card .value') !== null, { timeout: 15000 });

    const exportBtn = page.locator('#btn-export-closed');
    await expect(exportBtn).toBeVisible();

    const downloadPromise = page.waitForEvent('download', { timeout: 15000 });
    await exportBtn.click();
    const download = await downloadPromise;

    const filePath = path.join('test-results', download.suggestedFilename());
    await download.saveAs(filePath);
    const content = fs.readFileSync(filePath, 'utf-8').replace(/^\uFEFF/, '');
    const rows = parseCSV(content);

    const headers = rows[0];
    console.log(`Closed export: ${headers.length} columns, ${rows.length - 1} data rows`);

    for (const expected of CLOSED_HEADERS) {
      expect(headers, `Missing closed header: ${expected}`).toContain(expected);
    }

    const dataRows = rows.slice(1);
    if (dataRows.length === 0) {
      console.log('No closed picks to validate — skipping field checks');
      return;
    }

    const symbolIdx = headers.indexOf('Symbol');
    const scoreBreakdownIdx = headers.indexOf('Score Breakdown (English)');
    const consensusIdx = headers.indexOf('Consensus System Reasons');
    const fullAuditIdx = headers.indexOf('Entry Reason (Full Audit)');

    let emptyBreakdowns = 0;
    let emptyConsensus = 0;
    for (const row of dataRows) {
      if (!row[scoreBreakdownIdx]?.trim()) emptyBreakdowns++;
      if (!row[consensusIdx]?.trim()) emptyConsensus++;
    }

    console.log(`\n=== Closed Export Summary ===`);
    console.log(`Total closed picks: ${dataRows.length}`);
    console.log(`Empty score breakdowns: ${emptyBreakdowns}`);
    console.log(`Empty consensus reasons: ${emptyConsensus}`);

    // Log sample
    if (dataRows.length > 0) {
      const row = dataRows[0];
      console.log(`\nSample closed pick: ${row[symbolIdx]}`);
      console.log(`  Score Breakdown: ${(row[scoreBreakdownIdx] || '').substring(0, 200)}`);
      console.log(`  Consensus: ${(row[consensusIdx] || '').substring(0, 150)}`);
    }

    expect(emptyBreakdowns, 'All closed picks need score breakdown').toBe(0);
    expect(emptyConsensus, 'All closed picks need consensus reasons').toBe(0);
    expect(jsErrors).toEqual([]);
  });

  test('No JS console errors on dashboard load', async ({ page }) => {
    const jsErrors: string[] = [];
    page.on('pageerror', err => jsErrors.push(err.message));

    await page.goto('/audit_dashboard/index.html', { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    if (jsErrors.length > 0) {
      console.log('JS ERRORS:', jsErrors);
    }
    expect(jsErrors).toEqual([]);
  });
});
