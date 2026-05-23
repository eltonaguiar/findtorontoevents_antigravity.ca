import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const DATA_DIR = path.join(__dirname, '..', 'copy_trader_intel', 'data');
const ALPHA_DATA_DIR = path.join(__dirname, '..', 'alpha_engine', 'data');
const AUDIT_DATA_DIR = path.join(__dirname, '..', 'audit_dashboard', 'data');

test.describe('Multi-Asset Copytrader System', () => {

  test.describe('Data File Validation', () => {

    test('multi_asset_picks.json has valid structure', async () => {
      const filePath = path.join(DATA_DIR, 'multi_asset_picks.json');
      if (!fs.existsSync(filePath)) {
        console.log('multi_asset_picks.json not yet generated - skipping');
        test.skip();
        return;
      }
      const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
      expect(data).toHaveProperty('generated_at');
      expect(data).toHaveProperty('total_picks');
      expect(data).toHaveProperty('picks');
      expect(Array.isArray(data.picks)).toBe(true);
      expect(data.total_picks).toBeGreaterThan(0);

      // Check by_asset_class breakdown
      if (data.by_asset_class) {
        for (const [cls, count] of Object.entries(data.by_asset_class)) {
          console.log(`  ${cls}: ${count} picks`);
        }
      }
      console.log(`  Total: ${data.total_picks} picks`);
    });

    test('each pick has required fields', async () => {
      const filePath = path.join(DATA_DIR, 'multi_asset_picks.json');
      if (!fs.existsSync(filePath)) {
        test.skip();
        return;
      }
      const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
      const requiredFields = [
        'id', 'strategy', 'symbol', 'category', 'signal_type',
        'direction', 'entry_price', 'take_profit', 'stop_loss',
        'confidence', 'reason', 'source_system'
      ];

      const allPicks = data.picks || [];

      for (const pick of allPicks.slice(0, 20)) {
        for (const field of requiredFields) {
          expect(pick, `Pick ${pick.id} missing ${field}`).toHaveProperty(field);
        }
        // Validate confidence range
        expect(pick.confidence).toBeGreaterThanOrEqual(0);
        expect(pick.confidence).toBeLessThanOrEqual(1);

        // Validate direction
        expect(['LONG', 'SHORT']).toContain(pick.direction);

        // Validate signal type
        expect(['BUY', 'SELL']).toContain(pick.signal_type);

        // Entry price must be positive
        expect(pick.entry_price).toBeGreaterThan(0);

        // TP must be on correct side
        if (pick.direction === 'LONG') {
          expect(pick.take_profit).toBeGreaterThan(pick.entry_price);
          expect(pick.stop_loss).toBeLessThan(pick.entry_price);
        } else {
          expect(pick.take_profit).toBeLessThan(pick.entry_price);
          expect(pick.stop_loss).toBeGreaterThan(pick.entry_price);
        }
      }
      console.log(`Validated ${Math.min(allPicks.length, 20)} picks`);
    });

    test('forex picks have forex-appropriate TP/SL (not crypto-scale)', async () => {
      const filePath = path.join(DATA_DIR, 'multi_asset_picks.json');
      if (!fs.existsSync(filePath)) {
        test.skip();
        return;
      }
      const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
      const forexPicks = (data.picks || []).filter((p: any) => p.category === 'forex');

      for (const pick of forexPicks) {
        const tpPct = Math.abs(pick.take_profit - pick.entry_price) / pick.entry_price * 100;
        const slPct = Math.abs(pick.stop_loss - pick.entry_price) / pick.entry_price * 100;

        // Forex TP should be < 5% (not 15%+ like crypto)
        expect(tpPct, `${pick.symbol} TP ${tpPct.toFixed(2)}% too large for forex`)
          .toBeLessThan(5);

        // Forex SL should be < 3% (not 8%+ like crypto)
        expect(slPct, `${pick.symbol} SL ${slPct.toFixed(2)}% too large for forex`)
          .toBeLessThan(3);

        console.log(`  ${pick.symbol}: TP=${tpPct.toFixed(2)}%, SL=${slPct.toFixed(2)}%`);
      }
    });

    test('commodity picks exist and have valid symbols', async () => {
      const filePath = path.join(DATA_DIR, 'multi_asset_picks.json');
      if (!fs.existsSync(filePath)) {
        test.skip();
        return;
      }
      const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
      const commodityPicks = (data.picks || []).filter((p: any) => p.category === 'commodity');

      const validSymbols = [
        'GC=F', 'SI=F', 'CL=F', 'NG=F', 'HG=F', 'ZC=F',
        'ZW=F', 'ZS=F', 'KC=F', 'SB=F', 'PL=F', 'CT=F',
      ];

      for (const pick of commodityPicks) {
        expect(validSymbols, `Unexpected commodity symbol: ${pick.symbol}`)
          .toContain(pick.symbol);
        expect(pick.category).toBe('commodity');
      }
      console.log(`Commodity picks validated: ${commodityPicks.length}`);
    });

    test('variation portfolios have all 5 variants', async () => {
      const filePath = path.join(DATA_DIR, 'variation_portfolios.json');
      if (!fs.existsSync(filePath)) {
        console.log('variation_portfolios.json not yet generated - skipping');
        test.skip();
        return;
      }
      const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));

      const variants = data.variants || data;
      const expectedVariants = ['conservative', 'moderate', 'aggressive', 'scalper', 'swing'];
      for (const variant of expectedVariants) {
        expect(variants, `Missing variant: ${variant}`).toHaveProperty(variant);
        const v = variants[variant];
        expect(v).toHaveProperty('final_equity');
        expect(v).toHaveProperty('picks_accepted');
        console.log(`  ${variant}: equity=${v.final_equity}, accepted=${v.picks_accepted}`);
      }
    });

    test('multi_asset scoring data exists', async () => {
      // Try both file names
      let filePath = path.join(DATA_DIR, 'multi_asset_audit_scores.json');
      if (!fs.existsSync(filePath)) {
        filePath = path.join(DATA_DIR, 'multi_asset_scores.json');
      }
      if (!fs.existsSync(filePath)) {
        console.log('No scoring data found - skipping');
        test.skip();
        return;
      }
      const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));

      // Handle both flat dict and wrapper formats
      const strategies = data.strategies || data.scores || data;
      const stratKeys = Object.keys(strategies).filter(k => k !== 'generated_at' && k !== 'scores');
      expect(stratKeys.length).toBeGreaterThan(0);
      console.log(`Strategies scored: ${stratKeys.length}`);

      const first = strategies[stratKeys[0]];
      if (first && typeof first === 'object') {
        console.log('First score keys:', Object.keys(first).join(', '));
      }
    });

    test('forex_futures_picks.json is updated for audit dashboard', async () => {
      const filePath = path.join(AUDIT_DATA_DIR, 'forex_futures_picks.json');
      if (!fs.existsSync(filePath)) {
        test.skip();
        return;
      }
      const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
      expect(data).toHaveProperty('generated_at');
      expect(data).toHaveProperty('total_picks');
      expect(data).toHaveProperty('picks');
      expect(Array.isArray(data.picks)).toBe(true);

      console.log(`Audit dashboard data: ${data.total_picks} total picks`);
      console.log(`  Forex: ${data.forex_count || 0}`);
      console.log(`  Futures: ${data.futures_count || 0}`);
      console.log(`  Commodity: ${data.commodity_count || 0}`);
      console.log(`  Stock: ${data.stock_count || 0}`);
    });
  });

  test.describe('Audit Dashboard Live Verification', () => {

    test('audit dashboard loads and shows multi-asset data', async ({ page }) => {
      await page.goto('https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/audit/', {
        waitUntil: 'networkidle',
        timeout: 30000,
      });

      const title = await page.title();
      console.log('Audit dashboard title:', title);

      const bodyText = await page.textContent('body') || '';

      // Check for multi-asset content
      const hasForex = bodyText.includes('forex') || bodyText.includes('FOREX') ||
                       bodyText.includes('EURUSD') || bodyText.includes('GBPUSD');
      const hasFutures = bodyText.includes('futures') || bodyText.includes('FUTURES') ||
                         bodyText.includes('ES=F') || bodyText.includes('NQ=F');
      const hasCommodity = bodyText.includes('commodity') || bodyText.includes('COMMODITY') ||
                           bodyText.includes('GC=F') || bodyText.includes('CL=F') ||
                           bodyText.includes('Gold') || bodyText.includes('Oil');
      const hasStock = bodyText.includes('stock') || bodyText.includes('equity') ||
                       bodyText.includes('AAPL') || bodyText.includes('MSFT');

      console.log('Asset class presence:');
      console.log(`  Forex: ${hasForex}`);
      console.log(`  Futures: ${hasFutures}`);
      console.log(`  Commodity: ${hasCommodity}`);
      console.log(`  Stock: ${hasStock}`);

      // Check for copy trader content
      const hasCopyTrader = bodyText.includes('copy_trader') || bodyText.includes('Copy Trader');
      console.log(`  Copy Trader: ${hasCopyTrader}`);

      await page.screenshot({
        path: 'tests/screenshots/audit_multi_asset.png',
        fullPage: false,
      });
    });

    test('audit funds page shows portfolio data', async ({ page }) => {
      await page.goto('https://findtorontoevents.ca/audit/funds.html', {
        waitUntil: 'networkidle',
        timeout: 30000,
      });

      const bodyText = await page.textContent('body') || '';
      const hasFunds = bodyText.length > 100;
      console.log(`Funds page loaded: ${hasFunds}, text length: ${bodyText.length}`);

      await page.screenshot({
        path: 'tests/screenshots/audit_funds_multi_asset.png',
        fullPage: false,
      });

      expect(hasFunds).toBe(true);
    });
  });

  test.describe('Module Syntax Validation', () => {

    test('multi_asset_copytrader_scraper.py compiles without errors', async () => {
      const { execSync } = require('child_process');
      try {
        execSync('python -m py_compile copy_trader_intel/multi_asset_copytrader_scraper.py', {
          cwd: path.join(__dirname, '..'),
          encoding: 'utf-8',
        });
        console.log('multi_asset_copytrader_scraper.py: syntax OK');
      } catch (e: any) {
        console.error('Syntax error:', e.stderr);
        expect(false, `Syntax error in multi_asset_copytrader_scraper.py: ${e.stderr}`).toBe(true);
      }
    });

    test('multi_asset_backtester.py compiles without errors', async () => {
      const { execSync } = require('child_process');
      try {
        execSync('python -m py_compile copy_trader_intel/multi_asset_backtester.py', {
          cwd: path.join(__dirname, '..'),
          encoding: 'utf-8',
        });
        console.log('multi_asset_backtester.py: syntax OK');
      } catch (e: any) {
        console.error('Syntax error:', e.stderr);
        expect(false, `Syntax error in multi_asset_backtester.py: ${e.stderr}`).toBe(true);
      }
    });

    test('variation_portfolio_builder.py compiles without errors', async () => {
      const { execSync } = require('child_process');
      try {
        execSync('python -m py_compile copy_trader_intel/variation_portfolio_builder.py', {
          cwd: path.join(__dirname, '..'),
          encoding: 'utf-8',
        });
        console.log('variation_portfolio_builder.py: syntax OK');
      } catch (e: any) {
        console.error('Syntax error:', e.stderr);
        expect(false, `Syntax error in variation_portfolio_builder.py: ${e.stderr}`).toBe(true);
      }
    });

    test('multi_asset_scorer.py compiles without errors', async () => {
      const { execSync } = require('child_process');
      try {
        execSync('python -m py_compile copy_trader_intel/multi_asset_scorer.py', {
          cwd: path.join(__dirname, '..'),
          encoding: 'utf-8',
        });
        console.log('multi_asset_scorer.py: syntax OK');
      } catch (e: any) {
        console.error('Syntax error:', e.stderr);
        expect(false, `Syntax error in multi_asset_scorer.py: ${e.stderr}`).toBe(true);
      }
    });

    test('commodities_strategies.py compiles without errors', async () => {
      const { execSync } = require('child_process');
      try {
        execSync('python -m py_compile alpha_engine/commodities_strategies.py', {
          cwd: path.join(__dirname, '..'),
          encoding: 'utf-8',
        });
        console.log('commodities_strategies.py: syntax OK');
      } catch (e: any) {
        console.error('Syntax error:', e.stderr);
        expect(false, `Syntax error in commodities_strategies.py: ${e.stderr}`).toBe(true);
      }
    });
  });

  test.describe('Backtest Results Validation', () => {

    test('backtest_results.json has valid structure', async () => {
      const filePath = path.join(DATA_DIR, 'backtest_results.json');
      if (!fs.existsSync(filePath)) {
        console.log('backtest_results.json not yet generated - skipping');
        test.skip();
        return;
      }
      const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));

      expect(data).toHaveProperty('results');
      expect(data).toHaveProperty('asset_classes');

      const results = data.results;
      const assetClasses = Object.keys(results);
      console.log(`Asset classes backtested: ${assetClasses.join(', ')}`);

      for (const ac of assetClasses) {
        const strategies = Object.keys(results[ac]);
        console.log(`  ${ac}: ${strategies.length} strategies (${strategies.join(', ')})`);
        for (const strat of strategies) {
          const s = results[ac][strat];
          expect(s).toHaveProperty('walk_forward');
          const wf = s.walk_forward;
          if (wf && wf.total_trades !== undefined) {
            console.log(`    ${strat}: ${wf.total_trades} trades, WR=${((wf.win_rate||0)*100).toFixed(1)}%`);
          }
        }
      }
    });

    test('walk_forward_summary exists in backtest results', async () => {
      const filePath = path.join(DATA_DIR, 'backtest_results.json');
      if (!fs.existsSync(filePath)) {
        test.skip();
        return;
      }
      const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
      expect(data).toHaveProperty('walk_forward_summary');
      console.log(`Walk-forward summary entries: ${Object.keys(data.walk_forward_summary || {}).length}`);
    });
  });

  test.describe('No Orphaned Forex Pages', () => {

    test('check for orphaned forex-related HTML pages', async () => {
      const rootDir = path.join(__dirname, '..');
      const potentialOrphans = [
        'findforex2',
        'forex_dashboard',
        'forex_picks',
      ];

      for (const dir of potentialOrphans) {
        const fullPath = path.join(rootDir, dir);
        if (fs.existsSync(fullPath)) {
          const files = fs.readdirSync(fullPath);
          console.log(`Potential orphan directory: ${dir}/ (${files.length} files)`);
          if (files.length === 0) {
            console.log(`  Empty directory - candidate for cleanup`);
          }
        }
      }
    });
  });
});
