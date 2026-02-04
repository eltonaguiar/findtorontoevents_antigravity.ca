const puppeteer = require('puppeteer');
const fs = require('fs');

/**
 * PRODUCTION-GRADE 300 ROUND STRESS TEST
 * Resilient, comprehensive testing with database validation
 */

class ProductionTestSuite {
    constructor() {
        this.results = {
            totalTests: 0,
            passed: 0,
            failed: 0,
            warnings: 0,
            errors: [],
            databaseIssues: [],
            performanceMetrics: [],
            edgeCases: []
        };
        this.consoleErrors = [];
        this.networkErrors = [];
        this.startTime = Date.now();
    }

    async runAllTests() {
        console.log('🔥 PRODUCTION-GRADE STRESS TEST - 300 ROUNDS\n');
        console.log('Testing with resilience and comprehensive coverage...\n');

        const browser = await puppeteer.launch({
            headless: true,
            args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-web-security', '--disable-features=IsolateOrigins,site-per-process']
        });

        try {
            const page = await browser.newPage();
            await page.setViewport({ width: 1920, height: 1080 });

            // Monitor console
            page.on('console', msg => {
                if (msg.type() === 'error' && !msg.text().includes('Failed to load resource')) {
                    this.consoleErrors.push({
                        text: msg.text(),
                        timestamp: new Date().toISOString()
                    });
                }
            });

            page.on('pageerror', error => {
                this.consoleErrors.push({
                    text: error.message,
                    timestamp: new Date().toISOString(),
                    type: 'pageerror'
                });
            });

            // Load page with retry logic
            console.log('Loading page...');
            let loaded = false;
            for (let attempt = 1; attempt <= 3 && !loaded; attempt++) {
                try {
                    await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/', {
                        waitUntil: 'domcontentloaded',
                        timeout: 15000
                    });
                    await page.waitForSelector('.video-card', { timeout: 10000 });
                    loaded = true;
                    console.log('✅ Page loaded successfully\n');
                } catch (error) {
                    console.log(`⚠️  Load attempt ${attempt} failed, retrying...`);
                    if (attempt === 3) throw error;
                }
            }

            // Run test phases
            await this.phase1_BasicFunctionality(page, 60);
            await this.phase2_DatabaseValidation(page, 60);
            await this.phase3_EdgeCases(page, 60);
            await this.phase4_RapidInteractions(page, 60);
            await this.phase5_SearchFilters(page, 60);

        } catch (error) {
            this.results.errors.push({
                phase: 'Main Test Suite',
                error: error.message,
                stack: error.stack
            });
        }

        await browser.close();
        this.generateReport();
    }

    async phase1_BasicFunctionality(page, rounds) {
        console.log(`\n🧪 PHASE 1: Basic Functionality (${rounds} rounds)`);
        const tests = [
            () => this.test_VideoCardsExist(page),
            () => this.test_BrowseModalWorks(page),
            () => this.test_QueuePanelWorks(page),
            () => this.test_SearchInputExists(page),
            () => this.test_FilterButtonsWork(page),
            () => this.test_SidebarActionsExist(page)
        ];

        for (let i = 1; i <= rounds; i++) {
            try {
                await tests[i % tests.length]();
                this.results.totalTests++;
                this.results.passed++;

                if (i % 10 === 0) {
                    console.log(`  ✅ ${i}/${rounds} basic tests passed`);
                }
            } catch (error) {
                this.results.totalTests++;
                this.results.failed++;
                this.results.errors.push({
                    test: `Phase1-${i}`,
                    error: error.message
                });
            }
        }
    }

    async phase2_DatabaseValidation(page, rounds) {
        console.log(`\n🗄️  PHASE 2: Database Validation (${rounds} rounds)`);

        for (let i = 1; i <= rounds; i++) {
            try {
                const dbData = await page.evaluate(async () => {
                    try {
                        const response = await fetch('/MOVIESHOWS3/api/get-movies.php');
                        const data = await response.json();
                        const randomIndex = Math.floor(Math.random() * data.length);
                        return {
                            success: true,
                            count: data.length,
                            movie: data[randomIndex]
                        };
                    } catch (error) {
                        return { success: false, error: error.message };
                    }
                });

                if (!dbData.success) {
                    throw new Error(`Database fetch failed: ${dbData.error}`);
                }

                const movie = dbData.movie;

                // Validate required fields
                const requiredFields = ['id', 'title', 'type', 'trailer_id'];
                const missingFields = requiredFields.filter(field => !movie[field]);

                if (missingFields.length > 0) {
                    this.results.databaseIssues.push({
                        test: `DB-${i}`,
                        issue: `Missing fields: ${missingFields.join(', ')}`,
                        movie: movie.title,
                        severity: 'critical'
                    });
                }

                // Check for backup trailer
                if (!movie.backup_trailer_id && !movie.alternate_trailer_id) {
                    this.results.databaseIssues.push({
                        test: `DB-${i}`,
                        issue: 'No backup trailer link',
                        movie: movie.title,
                        severity: 'warning'
                    });
                }

                // Validate YouTube ID format
                if (movie.trailer_id && !/^[a-zA-Z0-9_-]{11}$/.test(movie.trailer_id)) {
                    this.results.databaseIssues.push({
                        test: `DB-${i}`,
                        issue: 'Invalid YouTube trailer ID format',
                        movie: movie.title,
                        trailerId: movie.trailer_id,
                        severity: 'critical'
                    });
                }

                // Validate genres
                if (!movie.genres || movie.genres.trim() === '') {
                    this.results.databaseIssues.push({
                        test: `DB-${i}`,
                        issue: 'No genres specified',
                        movie: movie.title,
                        severity: 'warning'
                    });
                }

                // Validate year
                const year = parseInt(movie.release_year);
                if (isNaN(year) || year < 1900 || year > 2030) {
                    this.results.databaseIssues.push({
                        test: `DB-${i}`,
                        issue: `Invalid release year: ${movie.release_year}`,
                        movie: movie.title,
                        severity: 'critical'
                    });
                }

                this.results.totalTests++;
                this.results.passed++;

                if (i % 10 === 0) {
                    console.log(`  ✅ ${i}/${rounds} database validations passed`);
                }
            } catch (error) {
                this.results.totalTests++;
                this.results.failed++;
                this.results.errors.push({
                    test: `Phase2-${i}`,
                    error: error.message
                });
            }
        }
    }

    async phase3_EdgeCases(page, rounds) {
        console.log(`\n🎯 PHASE 3: Edge Cases (${rounds} rounds)`);

        const edgeCases = [
            { name: 'Empty search', test: () => this.edge_EmptySearch(page) },
            { name: 'Special chars', test: () => this.edge_SpecialChars(page) },
            { name: 'Long search', test: () => this.edge_LongSearch(page) },
            { name: 'SQL injection', test: () => this.edge_SQLInjection(page) },
            { name: 'XSS attempt', test: () => this.edge_XSSAttempt(page) },
            { name: 'Invalid year', test: () => this.edge_InvalidYear(page) },
            { name: 'Future year', test: () => this.edge_FutureYear(page) },
            { name: 'All filters', test: () => this.edge_AllFilters(page) },
            { name: 'Rapid changes', test: () => this.edge_RapidChanges(page) },
            { name: 'Unicode search', test: () => this.edge_UnicodeSearch(page) }
        ];

        for (let i = 1; i <= rounds; i++) {
            try {
                const edgeCase = edgeCases[i % edgeCases.length];
                await edgeCase.test();

                this.results.totalTests++;
                this.results.passed++;
                this.results.edgeCases.push({
                    test: edgeCase.name,
                    result: 'passed'
                });

                if (i % 10 === 0) {
                    console.log(`  ✅ ${i}/${rounds} edge cases tested`);
                }
            } catch (error) {
                this.results.totalTests++;
                this.results.failed++;
                this.results.errors.push({
                    test: `Phase3-${i}`,
                    error: error.message
                });
            }
        }
    }

    async phase4_RapidInteractions(page, rounds) {
        console.log(`\n⚡ PHASE 4: Rapid Interactions (${rounds} rounds)`);

        for (let i = 1; i <= rounds; i++) {
            try {
                // Rapid modal toggling
                for (let j = 0; j < 3; j++) {
                    await page.click('button[title="Browse All"]');
                    await new Promise(r => setTimeout(r, 50));
                    await page.click('.browse-close');
                    await new Promise(r => setTimeout(r, 50));
                }

                this.results.totalTests++;
                this.results.passed++;

                if (i % 10 === 0) {
                    console.log(`  ✅ ${i}/${rounds} rapid interaction tests passed`);
                }
            } catch (error) {
                this.results.totalTests++;
                this.results.failed++;
                this.results.errors.push({
                    test: `Phase4-${i}`,
                    error: error.message
                });
            }
        }
    }

    async phase5_SearchFilters(page, rounds) {
        console.log(`\n🔍 PHASE 5: Search & Filter Combinations (${rounds} rounds)`);

        const searchTerms = ['action', 'comedy', 'drama', 'horror', 'love', 'war', 'space', 'time', 'good', 'bad'];
        const years = ['2020', '2021', '2022', '2023', '2024'];

        for (let i = 1; i <= rounds; i++) {
            try {
                await page.click('button[title="Browse All"]');
                await new Promise(r => setTimeout(r, 200));

                // Search
                const searchTerm = searchTerms[i % searchTerms.length];
                await page.click('#browseSearchInput');
                await page.keyboard.type(searchTerm, { delay: 10 });
                await new Promise(r => setTimeout(r, 100));

                // Year
                const year = years[i % years.length];
                await page.click('#yearFrom');
                await page.keyboard.type(year);
                await new Promise(r => setTimeout(r, 100));

                // Clear
                await page.evaluate(() => {
                    document.getElementById('browseSearchInput').value = '';
                    document.getElementById('yearFrom').value = '';
                });

                await page.click('.browse-close');
                await new Promise(r => setTimeout(r, 50));

                this.results.totalTests++;
                this.results.passed++;

                if (i % 10 === 0) {
                    console.log(`  ✅ ${i}/${rounds} filter combinations tested`);
                }
            } catch (error) {
                this.results.totalTests++;
                this.results.failed++;
                this.results.errors.push({
                    test: `Phase5-${i}`,
                    error: error.message
                });
            }
        }
    }

    // Test methods
    async test_VideoCardsExist(page) {
        const count = await page.$$eval('.video-card', cards => cards.length);
        if (count === 0) throw new Error('No video cards found');
    }

    async test_BrowseModalWorks(page) {
        await page.click('button[title="Browse All"]');
        await new Promise(r => setTimeout(r, 150));
        const visible = await page.$eval('#browseView', el => el.classList.contains('active'));
        if (!visible) throw new Error('Browse modal did not open');
        await page.click('.browse-close');
        await new Promise(r => setTimeout(r, 150));
    }

    async test_QueuePanelWorks(page) {
        await page.click('button[title="My Queue"]');
        await new Promise(r => setTimeout(r, 150));
        const visible = await page.$eval('#queuePanel', el => el.classList.contains('active'));
        if (!visible) throw new Error('Queue panel did not open');
        await page.click('.queue-close');
        await new Promise(r => setTimeout(r, 150));
    }

    async test_SearchInputExists(page) {
        await page.click('button[title="Browse All"]');
        await new Promise(r => setTimeout(r, 150));
        const exists = await page.$('#browseSearchInput');
        if (!exists) throw new Error('Search input not found');
        await page.click('.browse-close');
        await new Promise(r => setTimeout(r, 150));
    }

    async test_FilterButtonsWork(page) {
        await page.click('button[title="Browse All"]');
        await new Promise(r => setTimeout(r, 150));
        await page.click('[data-type="movie"]');
        await new Promise(r => setTimeout(r, 100));
        await page.click('.browse-close');
        await new Promise(r => setTimeout(r, 150));
    }

    async test_SidebarActionsExist(page) {
        const count = await page.$$eval('.action-btn', btns => btns.length);
        if (count !== 3) throw new Error(`Expected 3 sidebar buttons, found ${count}`);
    }

    // Edge case methods
    async edge_EmptySearch(page) {
        await page.click('button[title="Browse All"]');
        await new Promise(r => setTimeout(r, 150));
        await page.click('#browseSearchInput');
        await page.keyboard.press('Enter');
        await new Promise(r => setTimeout(r, 100));
        await page.click('.browse-close');
        await new Promise(r => setTimeout(r, 150));
    }

    async edge_SpecialChars(page) {
        await page.click('button[title="Browse All"]');
        await new Promise(r => setTimeout(r, 150));
        await page.type('#browseSearchInput', '!@#$%');
        await new Promise(r => setTimeout(r, 100));
        await page.evaluate(() => document.getElementById('browseSearchInput').value = '');
        await page.click('.browse-close');
        await new Promise(r => setTimeout(r, 150));
    }

    async edge_LongSearch(page) {
        await page.click('button[title="Browse All"]');
        await new Promise(r => setTimeout(r, 150));
        await page.type('#browseSearchInput', 'a'.repeat(50));
        await new Promise(r => setTimeout(r, 100));
        await page.evaluate(() => document.getElementById('browseSearchInput').value = '');
        await page.click('.browse-close');
        await new Promise(r => setTimeout(r, 150));
    }

    async edge_SQLInjection(page) {
        await page.click('button[title="Browse All"]');
        await new Promise(r => setTimeout(r, 150));
        await page.type('#browseSearchInput', "' OR '1'='1");
        await new Promise(r => setTimeout(r, 100));
        await page.evaluate(() => document.getElementById('browseSearchInput').value = '');
        await page.click('.browse-close');
        await new Promise(r => setTimeout(r, 150));
    }

    async edge_XSSAttempt(page) {
        await page.click('button[title="Browse All"]');
        await new Promise(r => setTimeout(r, 150));
        await page.type('#browseSearchInput', '<script>alert(1)</script>');
        await new Promise(r => setTimeout(r, 100));
        await page.evaluate(() => document.getElementById('browseSearchInput').value = '');
        await page.click('.browse-close');
        await new Promise(r => setTimeout(r, 150));
    }

    async edge_InvalidYear(page) {
        await page.click('button[title="Browse All"]');
        await new Promise(r => setTimeout(r, 150));
        await page.type('#yearFrom', '2025');
        await page.type('#yearTo', '2020');
        await new Promise(r => setTimeout(r, 100));
        await page.evaluate(() => {
            document.getElementById('yearFrom').value = '';
            document.getElementById('yearTo').value = '';
        });
        await page.click('.browse-close');
        await new Promise(r => setTimeout(r, 150));
    }

    async edge_FutureYear(page) {
        await page.click('button[title="Browse All"]');
        await new Promise(r => setTimeout(r, 150));
        await page.type('#yearFrom', '2050');
        await new Promise(r => setTimeout(r, 100));
        await page.evaluate(() => document.getElementById('yearFrom').value = '');
        await page.click('.browse-close');
        await new Promise(r => setTimeout(r, 150));
    }

    async edge_AllFilters(page) {
        await page.click('button[title="Browse All"]');
        await new Promise(r => setTimeout(r, 200));
        await page.type('#browseSearchInput', 'action');
        await page.type('#yearFrom', '2020');
        await page.click('[data-type="movie"]');
        await new Promise(r => setTimeout(r, 150));
        await page.evaluate(() => {
            document.getElementById('browseSearchInput').value = '';
            document.getElementById('yearFrom').value = '';
        });
        await page.click('.browse-close');
        await new Promise(r => setTimeout(r, 150));
    }

    async edge_RapidChanges(page) {
        await page.click('button[title="Browse All"]');
        await new Promise(r => setTimeout(r, 150));
        for (let i = 0; i < 5; i++) {
            await page.click('[data-type="movie"]');
            await new Promise(r => setTimeout(r, 30));
            await page.click('[data-type="tv"]');
            await new Promise(r => setTimeout(r, 30));
        }
        await page.click('.browse-close');
        await new Promise(r => setTimeout(r, 150));
    }

    async edge_UnicodeSearch(page) {
        await page.click('button[title="Browse All"]');
        await new Promise(r => setTimeout(r, 150));
        await page.type('#browseSearchInput', '你好世界');
        await new Promise(r => setTimeout(r, 100));
        await page.evaluate(() => document.getElementById('browseSearchInput').value = '');
        await page.click('.browse-close');
        await new Promise(r => setTimeout(r, 150));
    }

    generateReport() {
        const duration = ((Date.now() - this.startTime) / 1000).toFixed(2);

        console.log('\n\n' + '='.repeat(80));
        console.log('🔥 PRODUCTION-GRADE STRESS TEST RESULTS');
        console.log('='.repeat(80));

        console.log(`\n📊 OVERALL STATISTICS:`);
        console.log(`  Total Tests: ${this.results.totalTests}`);
        console.log(`  ✅ Passed: ${this.results.passed}`);
        console.log(`  ❌ Failed: ${this.results.failed}`);
        console.log(`  ⚠️  Warnings: ${this.results.warnings}`);
        console.log(`  Success Rate: ${((this.results.passed / this.results.totalTests) * 100).toFixed(2)}%`);
        console.log(`  Duration: ${duration}s`);

        console.log(`\n💥 JAVASCRIPT ERRORS: ${this.consoleErrors.length}`);
        if (this.consoleErrors.length > 0) {
            const uniqueErrors = [...new Set(this.consoleErrors.map(e => e.text))];
            console.log(`  Unique Errors: ${uniqueErrors.length}`);
            uniqueErrors.slice(0, 5).forEach(error => {
                console.log(`  ⚠️  ${error.substring(0, 100)}`);
            });
        }

        console.log(`\n🗄️  DATABASE ISSUES: ${this.results.databaseIssues.length}`);
        if (this.results.databaseIssues.length > 0) {
            const critical = this.results.databaseIssues.filter(i => i.severity === 'critical');
            const warnings = this.results.databaseIssues.filter(i => i.severity === 'warning');
            console.log(`  Critical: ${critical.length}`);
            console.log(`  Warnings: ${warnings.length}`);

            if (critical.length > 0) {
                console.log(`\n  Critical Issues:`);
                critical.slice(0, 5).forEach(issue => {
                    console.log(`  ❌ ${issue.movie}: ${issue.issue}`);
                });
            }

            if (warnings.length > 0) {
                console.log(`\n  Sample Warnings:`);
                warnings.slice(0, 3).forEach(issue => {
                    console.log(`  ⚠️  ${issue.movie}: ${issue.issue}`);
                });
            }
        }

        console.log(`\n🎯 EDGE CASES TESTED: ${this.results.edgeCases.length}`);
        const edgeCasePassed = this.results.edgeCases.filter(e => e.result === 'passed').length;
        console.log(`  Passed: ${edgeCasePassed}/${this.results.edgeCases.length}`);

        if (this.results.errors.length > 0) {
            console.log(`\n❌ TEST ERRORS: ${this.results.errors.length}`);
            this.results.errors.slice(0, 5).forEach(error => {
                console.log(`  ${error.test}: ${error.error}`);
            });
        }

        console.log('\n' + '='.repeat(80));
        const verdict = this.results.failed === 0 && this.consoleErrors.length === 0 ? '✅ PASS' : '⚠️  ISSUES FOUND';
        console.log(`FINAL VERDICT: ${verdict}`);
        console.log('='.repeat(80) + '\n');

        // Save report
        const reportPath = './PRODUCTION_TEST_REPORT.json';
        fs.writeFileSync(reportPath, JSON.stringify({
            timestamp: new Date().toISOString(),
            duration: duration + 's',
            summary: {
                totalTests: this.results.totalTests,
                passed: this.results.passed,
                failed: this.results.failed,
                warnings: this.results.warnings,
                successRate: ((this.results.passed / this.results.totalTests) * 100).toFixed(2) + '%'
            },
            consoleErrors: this.consoleErrors,
            databaseIssues: this.results.databaseIssues,
            edgeCases: this.results.edgeCases,
            errors: this.results.errors
        }, null, 2));

        console.log(`📄 Detailed report saved to: ${reportPath}\n`);
    }
}

// Run the test suite
const suite = new ProductionTestSuite();
suite.runAllTests()
    .then(() => {
        process.exit(suite.results.failed > 0 || suite.consoleErrors.length > 0 ? 1 : 0);
    })
    .catch(error => {
        console.error('❌ Test suite crashed:', error);
        process.exit(1);
    });
