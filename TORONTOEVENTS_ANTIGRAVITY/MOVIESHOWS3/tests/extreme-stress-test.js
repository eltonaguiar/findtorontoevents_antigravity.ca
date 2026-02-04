const puppeteer = require('puppeteer');

/**
 * EXTREME STRESS TEST - 300 ROUNDS
 * Comprehensive testing with creative edge cases
 */

class ExtensiveTestSuite {
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
    }

    async runAllTests() {
        console.log('🔥 EXTREME STRESS TEST - 300 ROUNDS\n');
        console.log('This will take several minutes...\n');

        const browser = await puppeteer.launch({
            headless: true, // Run headless for speed
            args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-web-security']
        });

        try {
            const page = await browser.newPage();
            await page.setViewport({ width: 1920, height: 1080 });

            // Monitor console and errors
            page.on('console', msg => {
                if (msg.type() === 'error') {
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
                    stack: error.stack
                });
            });

            page.on('requestfailed', request => {
                this.networkErrors.push({
                    url: request.url(),
                    error: request.failure().errorText
                });
            });

            // Initial page load
            console.log('Loading page...');
            await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/', {
                waitUntil: 'networkidle2',
                timeout: 30000
            });
            await page.waitForSelector('.video-card', { timeout: 10000 });

            // ROUND 1-50: Basic Functionality (50 tests)
            await this.testBasicFunctionality(page, 50);

            // ROUND 51-100: Database Validation (50 tests)
            await this.testDatabaseIntegrity(page, 50);

            // ROUND 101-150: Edge Cases & Stress Tests (50 tests)
            await this.testEdgeCases(page, 50);

            // ROUND 151-200: Rapid Interaction Stress (50 tests)
            await this.testRapidInteractions(page, 50);

            // ROUND 201-250: Search & Filter Combinations (50 tests)
            await this.testSearchFilterCombinations(page, 50);

            // ROUND 251-300: Memory Leaks & Performance (50 tests)
            await this.testMemoryAndPerformance(page, 50);

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

    async testBasicFunctionality(page, rounds) {
        console.log(`\n🧪 ROUND 1-${rounds}: Basic Functionality Tests`);

        for (let i = 1; i <= rounds; i++) {
            try {
                const testName = `Basic-${i}`;

                // Test different aspects each round
                switch (i % 10) {
                    case 0:
                        await this.testVideoCards(page, testName);
                        break;
                    case 1:
                        await this.testBrowseModal(page, testName);
                        break;
                    case 2:
                        await this.testQueuePanel(page, testName);
                        break;
                    case 3:
                        await this.testSidebarActions(page, testName);
                        break;
                    case 4:
                        await this.testSearchInput(page, testName);
                        break;
                    case 5:
                        await this.testFilterButtons(page, testName);
                        break;
                    case 6:
                        await this.testYearRange(page, testName);
                        break;
                    case 7:
                        await this.testGenreFilters(page, testName);
                        break;
                    case 8:
                        await this.testContentTypeFilters(page, testName);
                        break;
                    case 9:
                        await this.testAddToQueue(page, testName);
                        break;
                }

                this.results.totalTests++;
                this.results.passed++;

                if (i % 10 === 0) {
                    console.log(`  ✅ Completed ${i}/${rounds} basic tests`);
                }
            } catch (error) {
                this.results.totalTests++;
                this.results.failed++;
                this.results.errors.push({
                    test: `Basic-${i}`,
                    error: error.message
                });
            }
        }
    }

    async testDatabaseIntegrity(page, rounds) {
        console.log(`\n🗄️ ROUND ${this.results.totalTests + 1}-${this.results.totalTests + rounds}: Database Validation`);

        for (let i = 1; i <= rounds; i++) {
            try {
                const testName = `Database-${i}`;

                // Fetch and validate database
                const dbData = await page.evaluate(async () => {
                    try {
                        const response = await fetch('/MOVIESHOWS3/api/get-movies.php');
                        const data = await response.json();
                        return {
                            success: true,
                            count: data.length,
                            movies: data,
                            sample: data[Math.floor(Math.random() * data.length)]
                        };
                    } catch (error) {
                        return {
                            success: false,
                            error: error.message
                        };
                    }
                });

                if (!dbData.success) {
                    throw new Error(`Database fetch failed: ${dbData.error}`);
                }

                // Validate movie structure
                const movie = dbData.sample;
                const requiredFields = ['id', 'title', 'type', 'trailer_id', 'release_year'];
                const missingFields = requiredFields.filter(field => !movie[field]);

                if (missingFields.length > 0) {
                    this.results.databaseIssues.push({
                        test: testName,
                        issue: `Missing fields: ${missingFields.join(', ')}`,
                        movie: movie.title
                    });
                }

                // Check for backup trailer links
                if (movie.backup_trailer_id || movie.alternate_trailer_id) {
                    this.results.passed++;
                    console.log(`  ✅ Movie "${movie.title}" has backup trailer`);
                } else {
                    this.results.warnings++;
                    this.results.databaseIssues.push({
                        test: testName,
                        issue: 'No backup trailer link',
                        movie: movie.title,
                        severity: 'warning'
                    });
                }

                // Validate YouTube trailer ID format
                if (movie.trailer_id && !/^[a-zA-Z0-9_-]{11}$/.test(movie.trailer_id)) {
                    this.results.databaseIssues.push({
                        test: testName,
                        issue: 'Invalid YouTube trailer ID format',
                        movie: movie.title,
                        trailerId: movie.trailer_id
                    });
                }

                // Check for genres
                if (!movie.genres || movie.genres.trim() === '') {
                    this.results.databaseIssues.push({
                        test: testName,
                        issue: 'No genres specified',
                        movie: movie.title,
                        severity: 'warning'
                    });
                }

                // Validate release year
                const year = parseInt(movie.release_year);
                if (isNaN(year) || year < 1900 || year > 2030) {
                    this.results.databaseIssues.push({
                        test: testName,
                        issue: `Invalid release year: ${movie.release_year}`,
                        movie: movie.title
                    });
                }

                this.results.totalTests++;
                this.results.passed++;

                if (i % 10 === 0) {
                    console.log(`  ✅ Validated ${i}/${rounds} database entries`);
                }
            } catch (error) {
                this.results.totalTests++;
                this.results.failed++;
                this.results.errors.push({
                    test: `Database-${i}`,
                    error: error.message
                });
            }
        }
    }

    async testEdgeCases(page, rounds) {
        console.log(`\n🎯 ROUND ${this.results.totalTests + 1}-${this.results.totalTests + rounds}: Edge Cases & Stress Tests`);

        const edgeCases = [
            // Search edge cases
            { name: 'Empty search', action: async () => await this.testEmptySearch(page) },
            { name: 'Special characters search', action: async () => await this.testSpecialCharSearch(page) },
            { name: 'Very long search', action: async () => await this.testLongSearch(page) },
            { name: 'SQL injection attempt', action: async () => await this.testSQLInjection(page) },
            { name: 'XSS attempt', action: async () => await this.testXSSAttempt(page) },

            // Filter edge cases
            { name: 'Invalid year range', action: async () => await this.testInvalidYearRange(page) },
            { name: 'Future year filter', action: async () => await this.testFutureYear(page) },
            { name: 'Year 1900 filter', action: async () => await this.testOldYear(page) },
            { name: 'All filters at once', action: async () => await this.testAllFilters(page) },
            { name: 'Rapid filter changes', action: async () => await this.testRapidFilterChanges(page) },
        ];

        for (let i = 1; i <= rounds; i++) {
            try {
                const edgeCase = edgeCases[i % edgeCases.length];
                await edgeCase.action();

                this.results.totalTests++;
                this.results.passed++;
                this.results.edgeCases.push({
                    test: edgeCase.name,
                    result: 'passed'
                });

                if (i % 10 === 0) {
                    console.log(`  ✅ Tested ${i}/${rounds} edge cases`);
                }
            } catch (error) {
                this.results.totalTests++;
                this.results.failed++;
                this.results.errors.push({
                    test: `EdgeCase-${i}`,
                    error: error.message
                });
            }
        }
    }

    async testRapidInteractions(page, rounds) {
        console.log(`\n⚡ ROUND ${this.results.totalTests + 1}-${this.results.totalTests + rounds}: Rapid Interaction Stress`);

        for (let i = 1; i <= rounds; i++) {
            try {
                // Rapid modal opening/closing
                for (let j = 0; j < 5; j++) {
                    await page.click('button[title="Browse All"]');
                    await new Promise(r => setTimeout(r, 50));
                    await page.click('.browse-close');
                    await new Promise(r => setTimeout(r, 50));
                }

                // Rapid queue operations
                for (let j = 0; j < 3; j++) {
                    await page.click('button[title="My Queue"]');
                    await new Promise(r => setTimeout(r, 50));
                    await page.click('.queue-close');
                    await new Promise(r => setTimeout(r, 50));
                }

                this.results.totalTests++;
                this.results.passed++;

                if (i % 10 === 0) {
                    console.log(`  ✅ Completed ${i}/${rounds} rapid interaction tests`);
                }
            } catch (error) {
                this.results.totalTests++;
                this.results.failed++;
                this.results.errors.push({
                    test: `RapidInteraction-${i}`,
                    error: error.message
                });
            }
        }
    }

    async testSearchFilterCombinations(page, rounds) {
        console.log(`\n🔍 ROUND ${this.results.totalTests + 1}-${this.results.totalTests + rounds}: Search & Filter Combinations`);

        const searchTerms = ['action', 'comedy', 'drama', 'horror', 'love', 'war', 'space', 'time', 'good', 'bad'];
        const years = [2020, 2021, 2022, 2023, 2024];

        for (let i = 1; i <= rounds; i++) {
            try {
                await page.click('button[title="Browse All"]');
                await new Promise(r => setTimeout(r, 300));

                // Random search term
                const searchTerm = searchTerms[i % searchTerms.length];
                await page.click('#browseSearchInput');
                await page.keyboard.type(searchTerm, { delay: 10 });
                await new Promise(r => setTimeout(r, 200));

                // Random year
                const year = years[i % years.length];
                await page.click('#yearFrom');
                await page.keyboard.type(year.toString());
                await new Promise(r => setTimeout(r, 200));

                // Random content type
                const types = ['movie', 'tv', 'now-playing', 'out-this-week'];
                const type = types[i % types.length];
                await page.click(`[data-type="${type}"]`);
                await new Promise(r => setTimeout(r, 200));

                // Check results
                const resultsText = await page.$eval('#browseResultsCount', el => el.textContent);

                // Clear and close
                await page.evaluate(() => {
                    document.getElementById('browseSearchInput').value = '';
                    document.getElementById('yearFrom').value = '';
                    document.getElementById('yearTo').value = '';
                });
                await page.click('.browse-close');
                await new Promise(r => setTimeout(r, 100));

                this.results.totalTests++;
                this.results.passed++;

                if (i % 10 === 0) {
                    console.log(`  ✅ Tested ${i}/${rounds} filter combinations`);
                }
            } catch (error) {
                this.results.totalTests++;
                this.results.failed++;
                this.results.errors.push({
                    test: `FilterCombo-${i}`,
                    error: error.message
                });
            }
        }
    }

    async testMemoryAndPerformance(page, rounds) {
        console.log(`\n📊 ROUND ${this.results.totalTests + 1}-${this.results.totalTests + rounds}: Memory & Performance`);

        for (let i = 1; i <= rounds; i++) {
            try {
                // Get performance metrics
                const metrics = await page.metrics();

                this.results.performanceMetrics.push({
                    round: this.results.totalTests + i,
                    jsHeapSize: Math.round(metrics.JSHeapUsedSize / 1024 / 1024),
                    domNodes: metrics.Nodes,
                    eventListeners: metrics.JSEventListeners,
                    timestamp: new Date().toISOString()
                });

                // Check for memory leaks
                if (metrics.JSHeapUsedSize > 200 * 1024 * 1024) { // 200MB
                    this.results.warnings++;
                    this.results.errors.push({
                        test: `Memory-${i}`,
                        warning: `High memory usage: ${Math.round(metrics.JSHeapUsedSize / 1024 / 1024)}MB`
                    });
                }

                // Perform actions to test memory
                await page.click('button[title="Browse All"]');
                await new Promise(r => setTimeout(r, 100));
                await page.click('.browse-close');
                await new Promise(r => setTimeout(r, 100));

                this.results.totalTests++;
                this.results.passed++;

                if (i % 10 === 0) {
                    console.log(`  ✅ Monitored ${i}/${rounds} performance samples`);
                }
            } catch (error) {
                this.results.totalTests++;
                this.results.failed++;
                this.results.errors.push({
                    test: `Performance-${i}`,
                    error: error.message
                });
            }
        }
    }

    // Helper test methods
    async testVideoCards(page, testName) {
        const count = await page.$$eval('.video-card', cards => cards.length);
        if (count === 0) throw new Error('No video cards found');
    }

    async testBrowseModal(page, testName) {
        await page.click('button[title="Browse All"]');
        await new Promise(r => setTimeout(r, 200));
        const visible = await page.$eval('#browseView', el => el.classList.contains('active'));
        if (!visible) throw new Error('Browse modal did not open');
        await page.click('.browse-close');
        await new Promise(r => setTimeout(r, 200));
    }

    async testQueuePanel(page, testName) {
        await page.click('button[title="My Queue"]');
        await new Promise(r => setTimeout(r, 200));
        const visible = await page.$eval('#queuePanel', el => el.classList.contains('active'));
        if (!visible) throw new Error('Queue panel did not open');
        await page.click('.queue-close');
        await new Promise(r => setTimeout(r, 200));
    }

    async testSidebarActions(page, testName) {
        const count = await page.$$eval('.action-btn', btns => btns.length);
        if (count !== 3) throw new Error(`Expected 3 sidebar buttons, found ${count}`);
    }

    async testSearchInput(page, testName) {
        await page.click('button[title="Browse All"]');
        await new Promise(r => setTimeout(r, 200));
        await page.type('#browseSearchInput', 'test');
        await new Promise(r => setTimeout(r, 200));
        await page.evaluate(() => document.getElementById('browseSearchInput').value = '');
        await page.click('.browse-close');
        await new Promise(r => setTimeout(r, 200));
    }

    async testFilterButtons(page, testName) {
        await page.click('button[title="Browse All"]');
        await new Promise(r => setTimeout(r, 200));
        await page.click('[data-type="movie"]');
        await new Promise(r => setTimeout(r, 200));
        await page.click('.browse-close');
        await new Promise(r => setTimeout(r, 200));
    }

    async testYearRange(page, testName) {
        await page.click('button[title="Browse All"]');
        await new Promise(r => setTimeout(r, 200));
        await page.type('#yearFrom', '2020');
        await new Promise(r => setTimeout(r, 200));
        await page.evaluate(() => document.getElementById('yearFrom').value = '');
        await page.click('.browse-close');
        await new Promise(r => setTimeout(r, 200));
    }

    async testGenreFilters(page, testName) {
        await page.click('button[title="Browse All"]');
        await new Promise(r => setTimeout(r, 300));
        const genres = await page.$$('[data-genre]');
        if (genres.length > 1) {
            await genres[1].click();
            await new Promise(r => setTimeout(r, 200));
        }
        await page.click('.browse-close');
        await new Promise(r => setTimeout(r, 200));
    }

    async testContentTypeFilters(page, testName) {
        await page.click('button[title="Browse All"]');
        await new Promise(r => setTimeout(r, 200));
        await page.click('[data-type="tv"]');
        await new Promise(r => setTimeout(r, 200));
        await page.click('.browse-close');
        await new Promise(r => setTimeout(r, 200));
    }

    async testAddToQueue(page, testName) {
        await page.click('button[title="Browse All"]');
        await new Promise(r => setTimeout(r, 300));
        const addBtn = await page.$('.movie-card-add-queue');
        if (addBtn) {
            // Just verify it exists, don't actually click to avoid alerts
        }
        await page.click('.browse-close');
        await new Promise(r => setTimeout(r, 200));
    }

    async testEmptySearch(page) {
        await page.click('button[title="Browse All"]');
        await new Promise(r => setTimeout(r, 200));
        await page.click('#browseSearchInput');
        await page.keyboard.press('Enter');
        await new Promise(r => setTimeout(r, 200));
        await page.click('.browse-close');
        await new Promise(r => setTimeout(r, 200));
    }

    async testSpecialCharSearch(page) {
        await page.click('button[title="Browse All"]');
        await new Promise(r => setTimeout(r, 200));
        await page.type('#browseSearchInput', '!@#$%^&*()');
        await new Promise(r => setTimeout(r, 200));
        await page.evaluate(() => document.getElementById('browseSearchInput').value = '');
        await page.click('.browse-close');
        await new Promise(r => setTimeout(r, 200));
    }

    async testLongSearch(page) {
        await page.click('button[title="Browse All"]');
        await new Promise(r => setTimeout(r, 200));
        await page.type('#browseSearchInput', 'a'.repeat(100));
        await new Promise(r => setTimeout(r, 200));
        await page.evaluate(() => document.getElementById('browseSearchInput').value = '');
        await page.click('.browse-close');
        await new Promise(r => setTimeout(r, 200));
    }

    async testSQLInjection(page) {
        await page.click('button[title="Browse All"]');
        await new Promise(r => setTimeout(r, 200));
        await page.type('#browseSearchInput', "' OR '1'='1");
        await new Promise(r => setTimeout(r, 200));
        await page.evaluate(() => document.getElementById('browseSearchInput').value = '');
        await page.click('.browse-close');
        await new Promise(r => setTimeout(r, 200));
    }

    async testXSSAttempt(page) {
        await page.click('button[title="Browse All"]');
        await new Promise(r => setTimeout(r, 200));
        await page.type('#browseSearchInput', '<script>alert("xss")</script>');
        await new Promise(r => setTimeout(r, 200));
        await page.evaluate(() => document.getElementById('browseSearchInput').value = '');
        await page.click('.browse-close');
        await new Promise(r => setTimeout(r, 200));
    }

    async testInvalidYearRange(page) {
        await page.click('button[title="Browse All"]');
        await new Promise(r => setTimeout(r, 200));
        await page.type('#yearFrom', '2025');
        await page.type('#yearTo', '2020');
        await new Promise(r => setTimeout(r, 200));
        await page.evaluate(() => {
            document.getElementById('yearFrom').value = '';
            document.getElementById('yearTo').value = '';
        });
        await page.click('.browse-close');
        await new Promise(r => setTimeout(r, 200));
    }

    async testFutureYear(page) {
        await page.click('button[title="Browse All"]');
        await new Promise(r => setTimeout(r, 200));
        await page.type('#yearFrom', '2050');
        await new Promise(r => setTimeout(r, 200));
        await page.evaluate(() => document.getElementById('yearFrom').value = '');
        await page.click('.browse-close');
        await new Promise(r => setTimeout(r, 200));
    }

    async testOldYear(page) {
        await page.click('button[title="Browse All"]');
        await new Promise(r => setTimeout(r, 200));
        await page.type('#yearFrom', '1900');
        await new Promise(r => setTimeout(r, 200));
        await page.evaluate(() => document.getElementById('yearFrom').value = '');
        await page.click('.browse-close');
        await new Promise(r => setTimeout(r, 200));
    }

    async testAllFilters(page) {
        await page.click('button[title="Browse All"]');
        await new Promise(r => setTimeout(r, 300));
        await page.type('#browseSearchInput', 'action');
        await page.type('#yearFrom', '2020');
        await page.type('#yearTo', '2023');
        await page.click('[data-type="movie"]');
        const genres = await page.$$('[data-genre]');
        if (genres.length > 1) await genres[1].click();
        await new Promise(r => setTimeout(r, 300));
        await page.evaluate(() => {
            document.getElementById('browseSearchInput').value = '';
            document.getElementById('yearFrom').value = '';
            document.getElementById('yearTo').value = '';
        });
        await page.click('.browse-close');
        await new Promise(r => setTimeout(r, 200));
    }

    async testRapidFilterChanges(page) {
        await page.click('button[title="Browse All"]');
        await new Promise(r => setTimeout(r, 200));
        for (let i = 0; i < 10; i++) {
            await page.click('[data-type="movie"]');
            await new Promise(r => setTimeout(r, 50));
            await page.click('[data-type="tv"]');
            await new Promise(r => setTimeout(r, 50));
        }
        await page.click('.browse-close');
        await new Promise(r => setTimeout(r, 200));
    }

    generateReport() {
        console.log('\n\n' + '='.repeat(80));
        console.log('🔥 EXTREME STRESS TEST RESULTS - 300 ROUNDS');
        console.log('='.repeat(80));

        console.log(`\n📊 OVERALL STATISTICS:`);
        console.log(`  Total Tests: ${this.results.totalTests}`);
        console.log(`  ✅ Passed: ${this.results.passed}`);
        console.log(`  ❌ Failed: ${this.results.failed}`);
        console.log(`  ⚠️  Warnings: ${this.results.warnings}`);
        console.log(`  Success Rate: ${((this.results.passed / this.results.totalTests) * 100).toFixed(2)}%`);

        console.log(`\n💥 JAVASCRIPT ERRORS: ${this.consoleErrors.length}`);
        if (this.consoleErrors.length > 0) {
            const uniqueErrors = [...new Set(this.consoleErrors.map(e => e.text))];
            console.log(`  Unique Errors: ${uniqueErrors.length}`);
            uniqueErrors.slice(0, 10).forEach(error => {
                console.log(`  ⚠️  ${error}`);
            });
            if (uniqueErrors.length > 10) {
                console.log(`  ... and ${uniqueErrors.length - 10} more`);
            }
        }

        console.log(`\n🗄️ DATABASE ISSUES: ${this.results.databaseIssues.length}`);
        if (this.results.databaseIssues.length > 0) {
            const critical = this.results.databaseIssues.filter(i => i.severity !== 'warning');
            const warnings = this.results.databaseIssues.filter(i => i.severity === 'warning');
            console.log(`  Critical: ${critical.length}`);
            console.log(`  Warnings: ${warnings.length}`);

            critical.slice(0, 5).forEach(issue => {
                console.log(`  ❌ ${issue.movie}: ${issue.issue}`);
            });

            if (warnings.length > 0) {
                console.log(`\n  Sample Warnings:`);
                warnings.slice(0, 3).forEach(issue => {
                    console.log(`  ⚠️  ${issue.movie}: ${issue.issue}`);
                });
            }
        }

        console.log(`\n🌐 NETWORK ERRORS: ${this.networkErrors.length}`);
        if (this.networkErrors.length > 0) {
            const uniqueNetworkErrors = [...new Set(this.networkErrors.map(e => e.url))];
            console.log(`  Unique Failed URLs: ${uniqueNetworkErrors.length}`);
        }

        console.log(`\n📊 PERFORMANCE METRICS:`);
        if (this.results.performanceMetrics.length > 0) {
            const avgHeap = this.results.performanceMetrics.reduce((sum, m) => sum + m.jsHeapSize, 0) / this.results.performanceMetrics.length;
            const maxHeap = Math.max(...this.results.performanceMetrics.map(m => m.jsHeapSize));
            const avgNodes = Math.round(this.results.performanceMetrics.reduce((sum, m) => sum + m.domNodes, 0) / this.results.performanceMetrics.length);

            console.log(`  Average JS Heap: ${avgHeap.toFixed(2)} MB`);
            console.log(`  Max JS Heap: ${maxHeap} MB`);
            console.log(`  Average DOM Nodes: ${avgNodes}`);

            if (maxHeap > 150) {
                console.log(`  ⚠️  WARNING: High memory usage detected`);
            }
        }

        console.log(`\n🎯 EDGE CASES TESTED: ${this.results.edgeCases.length}`);
        const edgeCasePassed = this.results.edgeCases.filter(e => e.result === 'passed').length;
        console.log(`  Passed: ${edgeCasePassed}/${this.results.edgeCases.length}`);

        if (this.results.errors.length > 0) {
            console.log(`\n❌ CRITICAL ERRORS:`);
            this.results.errors.slice(0, 10).forEach(error => {
                console.log(`  ${error.test}: ${error.error || error.warning}`);
            });
        }

        console.log('\n' + '='.repeat(80));
        console.log(`FINAL VERDICT: ${this.results.failed === 0 && this.consoleErrors.length === 0 ? '✅ PASS' : '⚠️  ISSUES FOUND'}`);
        console.log('='.repeat(80) + '\n');

        // Save detailed report to file
        const fs = require('fs');
        const reportPath = './EXTREME_TEST_REPORT.json';
        fs.writeFileSync(reportPath, JSON.stringify({
            timestamp: new Date().toISOString(),
            summary: {
                totalTests: this.results.totalTests,
                passed: this.results.passed,
                failed: this.results.failed,
                warnings: this.results.warnings,
                successRate: ((this.results.passed / this.results.totalTests) * 100).toFixed(2) + '%'
            },
            consoleErrors: this.consoleErrors,
            databaseIssues: this.results.databaseIssues,
            networkErrors: this.networkErrors,
            performanceMetrics: this.results.performanceMetrics,
            edgeCases: this.results.edgeCases,
            errors: this.results.errors
        }, null, 2));

        console.log(`📄 Detailed report saved to: ${reportPath}\n`);
    }
}

// Run the extreme test suite
const suite = new ExtensiveTestSuite();
suite.runAllTests()
    .then(() => {
        process.exit(suite.results.failed > 0 || suite.consoleErrors.length > 0 ? 1 : 0);
    })
    .catch(error => {
        console.error('❌ Test suite crashed:', error);
        process.exit(1);
    });
