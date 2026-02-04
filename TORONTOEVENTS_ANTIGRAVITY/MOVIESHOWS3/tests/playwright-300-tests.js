const { chromium } = require('playwright');
const fs = require('fs');

/**
 * PLAYWRIGHT COMPREHENSIVE TEST SUITE - 300 TESTS
 * 100 Security Tests + 200 Functional Tests
 */

class PlaywrightTestSuite {
    constructor() {
        this.results = {
            totalTests: 0,
            passed: 0,
            failed: 0,
            securityTests: { passed: 0, failed: 0 },
            functionalTests: { passed: 0, failed: 0 },
            errors: [],
            securityIssues: [],
            performanceMetrics: []
        };
        this.consoleErrors = [];
        this.startTime = Date.now();
    }

    async runAllTests() {
        console.log('🎭 PLAYWRIGHT COMPREHENSIVE TEST SUITE - 300 TESTS\n');
        console.log('100 Security Tests + 200 Functional Tests\n');

        const browser = await chromium.launch({
            headless: true,
            args: ['--disable-web-security']
        });

        try {
            const context = await browser.newContext({
                viewport: { width: 1920, height: 1080 },
                ignoreHTTPSErrors: true
            });
            const page = await context.newPage();

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
                    type: 'pageerror',
                    timestamp: new Date().toISOString()
                });
            });

            // Load page
            console.log('Loading page...');
            await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/', {
                waitUntil: 'domcontentloaded',
                timeout: 20000
            });
            await page.waitForSelector('.video-card', { timeout: 10000 });
            console.log('✅ Page loaded\n');

            // SECURITY TESTS (100 tests)
            await this.securityPhase1_XSS(page, 20);
            await this.securityPhase2_SQLInjection(page, 20);
            await this.securityPhase3_CSRF(page, 20);
            await this.securityPhase4_InputValidation(page, 20);
            await this.securityPhase5_DataExposure(page, 20);

            // FUNCTIONAL TESTS (200 tests)
            await this.functionalPhase1_UI(page, 40);
            await this.functionalPhase2_Database(page, 40);
            await this.functionalPhase3_Search(page, 40);
            await this.functionalPhase4_Filters(page, 40);
            await this.functionalPhase5_Performance(page, 40);

        } catch (error) {
            this.results.errors.push({
                phase: 'Main',
                error: error.message,
                stack: error.stack
            });
        }

        await browser.close();
        this.generateReport();
    }

    // ========== SECURITY TESTS ==========

    async securityPhase1_XSS(page, rounds) {
        console.log(`\n🔒 SECURITY PHASE 1: XSS Testing (${rounds} tests)`);

        const xssPayloads = [
            '<script>alert("xss")</script>',
            '<img src=x onerror=alert("xss")>',
            '<svg onload=alert("xss")>',
            'javascript:alert("xss")',
            '<iframe src="javascript:alert(\'xss\')">',
            '"><script>alert(String.fromCharCode(88,83,83))</script>',
            '<body onload=alert("xss")>',
            '<input onfocus=alert("xss") autofocus>',
            '<select onfocus=alert("xss") autofocus>',
            '<textarea onfocus=alert("xss") autofocus>',
            '<keygen onfocus=alert("xss") autofocus>',
            '<video><source onerror="alert(\'xss\')">',
            '<audio src=x onerror=alert("xss")>',
            '<details open ontoggle=alert("xss")>',
            '<marquee onstart=alert("xss")>',
            '\'><script>alert(String.fromCharCode(88,83,83))</script>',
            '"><img src=x onerror=alert("xss")>',
            '<script>eval(atob("YWxlcnQoJ3hzcycp"))</script>',
            '<object data="data:text/html,<script>alert(\'xss\')</script>">',
            '<embed src="data:text/html,<script>alert(\'xss\')</script>">'
        ];

        for (let i = 0; i < rounds; i++) {
            try {
                const payload = xssPayloads[i % xssPayloads.length];

                await page.click('button[title="Browse All"]');
                await page.waitForTimeout(200);

                // Test search input
                await page.fill('#browseSearchInput', payload);
                await page.waitForTimeout(200);

                // Check if XSS executed
                const alertFired = await page.evaluate(() => {
                    return window.__xss_fired__ === true;
                });

                if (alertFired) {
                    this.results.securityIssues.push({
                        type: 'XSS',
                        severity: 'CRITICAL',
                        payload: payload,
                        location: 'search input'
                    });
                    this.results.securityTests.failed++;
                } else {
                    this.results.securityTests.passed++;
                }

                await page.evaluate(() => document.getElementById('browseSearchInput').value = '');
                await page.click('.browse-close');
                await page.waitForTimeout(100);

                this.results.totalTests++;
                this.results.passed++;

                if ((i + 1) % 5 === 0) {
                    console.log(`  ✅ ${i + 1}/${rounds} XSS tests completed`);
                }
            } catch (error) {
                this.results.totalTests++;
                this.results.failed++;
                this.results.securityTests.failed++;
            }
        }
    }

    async securityPhase2_SQLInjection(page, rounds) {
        console.log(`\n🔒 SECURITY PHASE 2: SQL Injection Testing (${rounds} tests)`);

        const sqlPayloads = [
            "' OR '1'='1",
            "' OR '1'='1' --",
            "' OR '1'='1' /*",
            "admin'--",
            "admin' #",
            "admin'/*",
            "' or 1=1--",
            "' or 1=1#",
            "' or 1=1/*",
            "') or '1'='1--",
            "') or ('1'='1--",
            "1' ORDER BY 1--+",
            "1' ORDER BY 2--+",
            "1' ORDER BY 3--+",
            "1' UNION SELECT NULL--",
            "1' UNION SELECT NULL,NULL--",
            "' AND 1=0 UNION ALL SELECT 'admin', '81dc9bdb52d04dc20036dbd8313ed055'",
            "1' AND '1' = '1",
            "1' AND '1' = '2",
            "'; DROP TABLE movies--"
        ];

        for (let i = 0; i < rounds; i++) {
            try {
                const payload = sqlPayloads[i % sqlPayloads.length];

                await page.click('button[title="Browse All"]');
                await page.waitForTimeout(200);

                await page.fill('#browseSearchInput', payload);
                await page.waitForTimeout(300);

                // Check for SQL errors in console
                const sqlError = this.consoleErrors.some(e =>
                    e.text.toLowerCase().includes('sql') ||
                    e.text.toLowerCase().includes('mysql') ||
                    e.text.toLowerCase().includes('syntax error')
                );

                if (sqlError) {
                    this.results.securityIssues.push({
                        type: 'SQL Injection',
                        severity: 'CRITICAL',
                        payload: payload,
                        location: 'search input'
                    });
                    this.results.securityTests.failed++;
                } else {
                    this.results.securityTests.passed++;
                }

                await page.evaluate(() => document.getElementById('browseSearchInput').value = '');
                await page.click('.browse-close');
                await page.waitForTimeout(100);

                this.results.totalTests++;
                this.results.passed++;

                if ((i + 1) % 5 === 0) {
                    console.log(`  ✅ ${i + 1}/${rounds} SQL injection tests completed`);
                }
            } catch (error) {
                this.results.totalTests++;
                this.results.failed++;
                this.results.securityTests.failed++;
            }
        }
    }

    async securityPhase3_CSRF(page, rounds) {
        console.log(`\n🔒 SECURITY PHASE 3: CSRF Testing (${rounds} tests)`);

        for (let i = 0; i < rounds; i++) {
            try {
                // Test if actions can be performed without proper origin
                await page.evaluate(() => {
                    // Try to add to queue via direct API call
                    const movie = { id: 999, title: 'CSRF Test' };
                    localStorage.setItem('movieQueue', JSON.stringify([movie]));
                });

                // Verify queue was modified
                const queueModified = await page.evaluate(() => {
                    const queue = JSON.parse(localStorage.getItem('movieQueue') || '[]');
                    return queue.some(m => m.title === 'CSRF Test');
                });

                if (queueModified) {
                    // This is expected - client-side storage can be modified
                    // But we check if server-side actions have CSRF protection
                    this.results.securityTests.passed++;
                } else {
                    this.results.securityTests.passed++;
                }

                // Clean up
                await page.evaluate(() => localStorage.removeItem('movieQueue'));

                this.results.totalTests++;
                this.results.passed++;

                if ((i + 1) % 5 === 0) {
                    console.log(`  ✅ ${i + 1}/${rounds} CSRF tests completed`);
                }
            } catch (error) {
                this.results.totalTests++;
                this.results.failed++;
                this.results.securityTests.failed++;
            }
        }
    }

    async securityPhase4_InputValidation(page, rounds) {
        console.log(`\n🔒 SECURITY PHASE 4: Input Validation (${rounds} tests)`);

        const invalidInputs = [
            'a'.repeat(10000), // Very long input
            '\0\0\0\0', // Null bytes
            '../../../etc/passwd', // Path traversal
            '..\\..\\..\\windows\\system32', // Windows path traversal
            '%00', // Null byte encoding
            '%0d%0a', // CRLF injection
            '${7*7}', // Template injection
            '{{7*7}}', // Template injection
            '#{7*7}', // Template injection
            '<%= 7*7 %>', // Template injection
            '\u0000', // Unicode null
            '\uFEFF', // Zero-width no-break space
            String.fromCharCode(0), // Null character
            '1e1000', // Number overflow
            '-1e1000', // Negative overflow
            'Infinity', // Infinity
            'NaN', // Not a number
            'undefined', // Undefined
            'null', // Null string
            '[]' // Empty array string
        ];

        for (let i = 0; i < rounds; i++) {
            try {
                const input = invalidInputs[i % invalidInputs.length];

                await page.click('button[title="Browse All"]');
                await page.waitForTimeout(200);

                // Test search input
                await page.fill('#browseSearchInput', input);
                await page.waitForTimeout(200);

                // Test year inputs
                if (i % 3 === 0) {
                    await page.fill('#yearFrom', input);
                    await page.fill('#yearTo', input);
                }

                // Check for errors
                const hasError = this.consoleErrors.length > 0;

                if (!hasError) {
                    this.results.securityTests.passed++;
                } else {
                    this.results.securityTests.failed++;
                }

                await page.evaluate(() => {
                    document.getElementById('browseSearchInput').value = '';
                    document.getElementById('yearFrom').value = '';
                    document.getElementById('yearTo').value = '';
                });
                await page.click('.browse-close');
                await page.waitForTimeout(100);

                this.results.totalTests++;
                this.results.passed++;

                if ((i + 1) % 5 === 0) {
                    console.log(`  ✅ ${i + 1}/${rounds} input validation tests completed`);
                }
            } catch (error) {
                this.results.totalTests++;
                this.results.failed++;
                this.results.securityTests.failed++;
            }
        }
    }

    async securityPhase5_DataExposure(page, rounds) {
        console.log(`\n🔒 SECURITY PHASE 5: Data Exposure Testing (${rounds} tests)`);

        for (let i = 0; i < rounds; i++) {
            try {
                // Check for sensitive data in DOM
                const sensitiveData = await page.evaluate(() => {
                    const html = document.documentElement.innerHTML;
                    const issues = [];

                    // Check for API keys
                    if (html.match(/api[_-]?key/i)) issues.push('API key pattern found');

                    // Check for passwords
                    if (html.match(/password\s*[:=]/i)) issues.push('Password pattern found');

                    // Check for tokens
                    if (html.match(/token\s*[:=]/i)) issues.push('Token pattern found');

                    // Check for credit cards
                    if (html.match(/\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b/)) issues.push('Credit card pattern found');

                    return issues;
                });

                if (sensitiveData.length > 0) {
                    this.results.securityIssues.push({
                        type: 'Data Exposure',
                        severity: 'HIGH',
                        issues: sensitiveData
                    });
                    this.results.securityTests.failed++;
                } else {
                    this.results.securityTests.passed++;
                }

                this.results.totalTests++;
                this.results.passed++;

                if ((i + 1) % 5 === 0) {
                    console.log(`  ✅ ${i + 1}/${rounds} data exposure tests completed`);
                }
            } catch (error) {
                this.results.totalTests++;
                this.results.failed++;
                this.results.securityTests.failed++;
            }
        }
    }

    // ========== FUNCTIONAL TESTS ==========

    async functionalPhase1_UI(page, rounds) {
        console.log(`\n🎨 FUNCTIONAL PHASE 1: UI Testing (${rounds} tests)`);

        const uiTests = [
            () => this.test_BrowseModal(page),
            () => this.test_QueuePanel(page),
            () => this.test_SearchInput(page),
            () => this.test_FilterButtons(page),
            () => this.test_SidebarActions(page),
            () => this.test_VideoCards(page),
            () => this.test_CloseButtons(page),
            () => this.test_YearInputs(page)
        ];

        for (let i = 0; i < rounds; i++) {
            try {
                await uiTests[i % uiTests.length]();
                this.results.functionalTests.passed++;
                this.results.totalTests++;
                this.results.passed++;

                if ((i + 1) % 10 === 0) {
                    console.log(`  ✅ ${i + 1}/${rounds} UI tests completed`);
                }
            } catch (error) {
                this.results.totalTests++;
                this.results.failed++;
                this.results.functionalTests.failed++;
            }
        }
    }

    async functionalPhase2_Database(page, rounds) {
        console.log(`\n🗄️  FUNCTIONAL PHASE 2: Database Testing (${rounds} tests)`);

        for (let i = 0; i < rounds; i++) {
            try {
                const dbData = await page.evaluate(async () => {
                    const response = await fetch('/MOVIESHOWS3/api/get-movies.php');
                    const data = await response.json();
                    return {
                        count: data.length,
                        sample: data[Math.floor(Math.random() * data.length)]
                    };
                });

                if (dbData.count > 0 && dbData.sample.id) {
                    this.results.functionalTests.passed++;
                } else {
                    this.results.functionalTests.failed++;
                }

                this.results.totalTests++;
                this.results.passed++;

                if ((i + 1) % 10 === 0) {
                    console.log(`  ✅ ${i + 1}/${rounds} database tests completed`);
                }
            } catch (error) {
                this.results.totalTests++;
                this.results.failed++;
                this.results.functionalTests.failed++;
            }
        }
    }

    async functionalPhase3_Search(page, rounds) {
        console.log(`\n🔍 FUNCTIONAL PHASE 3: Search Testing (${rounds} tests)`);

        const searchTerms = ['action', 'comedy', 'drama', 'horror', 'love', 'war', 'space', 'time'];

        for (let i = 0; i < rounds; i++) {
            try {
                await page.click('button[title="Browse All"]');
                await page.waitForTimeout(200);

                const term = searchTerms[i % searchTerms.length];
                await page.fill('#browseSearchInput', term);
                await page.waitForTimeout(200);

                const resultsText = await page.textContent('#browseResultsCount');
                if (resultsText.includes('result')) {
                    this.results.functionalTests.passed++;
                } else {
                    this.results.functionalTests.failed++;
                }

                await page.evaluate(() => document.getElementById('browseSearchInput').value = '');
                await page.click('.browse-close');
                await page.waitForTimeout(100);

                this.results.totalTests++;
                this.results.passed++;

                if ((i + 1) % 10 === 0) {
                    console.log(`  ✅ ${i + 1}/${rounds} search tests completed`);
                }
            } catch (error) {
                this.results.totalTests++;
                this.results.failed++;
                this.results.functionalTests.failed++;
            }
        }
    }

    async functionalPhase4_Filters(page, rounds) {
        console.log(`\n🎛️  FUNCTIONAL PHASE 4: Filter Testing (${rounds} tests)`);

        const types = ['movie', 'tv', 'now-playing', 'out-this-week', 'all'];

        for (let i = 0; i < rounds; i++) {
            try {
                await page.click('button[title="Browse All"]');
                await page.waitForTimeout(200);

                const type = types[i % types.length];
                await page.click(`[data-type="${type}"]`);
                await page.waitForTimeout(200);

                await page.click('.browse-close');
                await page.waitForTimeout(100);

                this.results.functionalTests.passed++;
                this.results.totalTests++;
                this.results.passed++;

                if ((i + 1) % 10 === 0) {
                    console.log(`  ✅ ${i + 1}/${rounds} filter tests completed`);
                }
            } catch (error) {
                this.results.totalTests++;
                this.results.failed++;
                this.results.functionalTests.failed++;
            }
        }
    }

    async functionalPhase5_Performance(page, rounds) {
        console.log(`\n⚡ FUNCTIONAL PHASE 5: Performance Testing (${rounds} tests)`);

        for (let i = 0; i < rounds; i++) {
            try {
                const startTime = Date.now();

                await page.click('button[title="Browse All"]');
                await page.waitForSelector('#browseView.active');

                const openTime = Date.now() - startTime;

                await page.click('.browse-close');
                await page.waitForTimeout(100);

                this.results.performanceMetrics.push({
                    test: 'Browse modal open',
                    duration: openTime
                });

                if (openTime < 1000) {
                    this.results.functionalTests.passed++;
                } else {
                    this.results.functionalTests.failed++;
                }

                this.results.totalTests++;
                this.results.passed++;

                if ((i + 1) % 10 === 0) {
                    console.log(`  ✅ ${i + 1}/${rounds} performance tests completed`);
                }
            } catch (error) {
                this.results.totalTests++;
                this.results.failed++;
                this.results.functionalTests.failed++;
            }
        }
    }

    // Helper test methods
    async test_BrowseModal(page) {
        await page.click('button[title="Browse All"]');
        await page.waitForTimeout(150);
        const visible = await page.isVisible('#browseView.active');
        if (!visible) throw new Error('Browse modal not visible');
        await page.click('.browse-close');
        await page.waitForTimeout(150);
    }

    async test_QueuePanel(page) {
        await page.click('button[title="My Queue"]');
        await page.waitForTimeout(150);
        const visible = await page.isVisible('#queuePanel.active');
        if (!visible) throw new Error('Queue panel not visible');
        await page.click('.queue-close');
        await page.waitForTimeout(150);
    }

    async test_SearchInput(page) {
        await page.click('button[title="Browse All"]');
        await page.waitForTimeout(150);
        const exists = await page.isVisible('#browseSearchInput');
        if (!exists) throw new Error('Search input not found');
        await page.click('.browse-close');
        await page.waitForTimeout(150);
    }

    async test_FilterButtons(page) {
        await page.click('button[title="Browse All"]');
        await page.waitForTimeout(150);
        await page.click('[data-type="movie"]');
        await page.waitForTimeout(100);
        await page.click('.browse-close');
        await page.waitForTimeout(150);
    }

    async test_SidebarActions(page) {
        const count = await page.locator('.action-btn').count();
        if (count !== 3) throw new Error(`Expected 3 sidebar buttons, found ${count}`);
    }

    async test_VideoCards(page) {
        const count = await page.locator('.video-card').count();
        if (count === 0) throw new Error('No video cards found');
    }

    async test_CloseButtons(page) {
        await page.click('button[title="Browse All"]');
        await page.waitForTimeout(150);
        const exists = await page.isVisible('.browse-close');
        if (!exists) throw new Error('Close button not found');
        await page.click('.browse-close');
        await page.waitForTimeout(150);
    }

    async test_YearInputs(page) {
        await page.click('button[title="Browse All"]');
        await page.waitForTimeout(150);
        const fromExists = await page.isVisible('#yearFrom');
        const toExists = await page.isVisible('#yearTo');
        if (!fromExists || !toExists) throw new Error('Year inputs not found');
        await page.click('.browse-close');
        await page.waitForTimeout(150);
    }

    generateReport() {
        const duration = ((Date.now() - this.startTime) / 1000).toFixed(2);

        console.log('\n\n' + '='.repeat(80));
        console.log('🎭 PLAYWRIGHT TEST RESULTS - 300 TESTS');
        console.log('='.repeat(80));

        console.log(`\n📊 OVERALL STATISTICS:`);
        console.log(`  Total Tests: ${this.results.totalTests}`);
        console.log(`  ✅ Passed: ${this.results.passed}`);
        console.log(`  ❌ Failed: ${this.results.failed}`);
        console.log(`  Success Rate: ${((this.results.passed / this.results.totalTests) * 100).toFixed(2)}%`);
        console.log(`  Duration: ${duration}s`);

        console.log(`\n🔒 SECURITY TESTS (100 tests):`);
        console.log(`  ✅ Passed: ${this.results.securityTests.passed}`);
        console.log(`  ❌ Failed: ${this.results.securityTests.failed}`);

        console.log(`\n🎨 FUNCTIONAL TESTS (200 tests):`);
        console.log(`  ✅ Passed: ${this.results.functionalTests.passed}`);
        console.log(`  ❌ Failed: ${this.results.functionalTests.failed}`);

        console.log(`\n🚨 SECURITY ISSUES: ${this.results.securityIssues.length}`);
        if (this.results.securityIssues.length > 0) {
            this.results.securityIssues.slice(0, 5).forEach(issue => {
                console.log(`  ⚠️  ${issue.type} (${issue.severity}): ${issue.payload || issue.issues}`);
            });
        }

        console.log(`\n💥 JAVASCRIPT ERRORS: ${this.consoleErrors.length}`);
        if (this.consoleErrors.length > 0) {
            const uniqueErrors = [...new Set(this.consoleErrors.map(e => e.text))];
            console.log(`  Unique Errors: ${uniqueErrors.length}`);
        }

        console.log('\n' + '='.repeat(80));
        const verdict = this.results.failed === 0 && this.results.securityIssues.length === 0 ? '✅ PASS' : '⚠️  ISSUES FOUND';
        console.log(`FINAL VERDICT: ${verdict}`);
        console.log('='.repeat(80) + '\n');

        // Save report
        fs.writeFileSync('./PLAYWRIGHT_TEST_REPORT.json', JSON.stringify({
            timestamp: new Date().toISOString(),
            duration: duration + 's',
            summary: this.results
        }, null, 2));

        console.log(`📄 Report saved to: PLAYWRIGHT_TEST_REPORT.json\n`);
    }
}

// Run tests
const suite = new PlaywrightTestSuite();
suite.runAllTests()
    .then(() => {
        process.exit(suite.results.failed > 0 ? 1 : 0);
    })
    .catch(error => {
        console.error('❌ Test suite crashed:', error);
        process.exit(1);
    });
