// Quick debug script: test parseNLQuery on production portfolio2
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  const jsErrors = [];
  page.on('pageerror', (err) => {
    jsErrors.push(`PageError: ${err.message}`);
  });
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      jsErrors.push(`Console: ${msg.text().slice(0, 200)}`);
    }
  });

  console.log('Navigating to portfolio2...');
  await page.goto('https://findtorontoevents.ca/findstocks/portfolio2/', {
    waitUntil: 'networkidle',
    timeout: 30000,
  });
  console.log('Page loaded.');

  // Check for JS errors on page load
  if (jsErrors.length > 0) {
    console.log('JS errors on load:');
    jsErrors.forEach((e) => console.log('  ' + e));
  }

  // Check if parseNLQuery exists
  const fnExists = await page.evaluate(() => typeof parseNLQuery === 'function');
  console.log('parseNLQuery exists:', fnExists);

  const runExists = await page.evaluate(() => typeof runWhatIf === 'function');
  console.log('runWhatIf exists:', runExists);

  // Type the query
  await page.fill('#nl-query', 'day trader buying stocks and holding for max 2 days with 10% profit target');
  console.log('Filled NL query.');

  // Check form elements exist
  const elements = await page.evaluate(() => {
    return {
      wiTp: !!document.getElementById('wi-tp'),
      wiSl: !!document.getElementById('wi-sl'),
      wiHold: !!document.getElementById('wi-hold'),
      wiCapital: !!document.getElementById('wi-capital'),
      wiComm: !!document.getElementById('wi-comm'),
      wiSlip: !!document.getElementById('wi-slip'),
      btnRunWhatif: !!document.getElementById('btn-run-whatif'),
    };
  });
  console.log('Form elements:', JSON.stringify(elements));

  // Clear error log before clicking
  jsErrors.length = 0;

  // Click Analyze Query button
  console.log('Clicking Analyze Query...');
  await page.click('button:has-text("Analyze Query")');

  // Wait for potential API response
  await page.waitForTimeout(5000);

  // Check for new errors
  if (jsErrors.length > 0) {
    console.log('JS errors after clicking:');
    jsErrors.forEach((e) => console.log('  ' + e));
  } else {
    console.log('No JS errors after clicking.');
  }

  // Check if form values were updated
  const formValues = await page.evaluate(() => {
    return {
      tp: document.getElementById('wi-tp')?.value,
      sl: document.getElementById('wi-sl')?.value,
      hold: document.getElementById('wi-hold')?.value,
    };
  });
  console.log('Form values after parse:', JSON.stringify(formValues));

  // Check if results appeared
  const resultsVisible = await page.evaluate(() => {
    var el = document.getElementById('wi-results');
    return el ? el.style.display : 'element-not-found';
  });
  console.log('Results display:', resultsVisible);

  // Check the button state
  const btnState = await page.evaluate(() => {
    var btn = document.getElementById('btn-run-whatif');
    return btn ? { text: btn.textContent, disabled: btn.disabled } : 'not-found';
  });
  console.log('Button state:', JSON.stringify(btnState));

  await browser.close();
  console.log('Done.');
})();
