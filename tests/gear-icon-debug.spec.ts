import { test } from '@playwright/test';

/**
 * Debug test: find which CSS rule sets display:none on the gear button.
 */
test('debug gear button display:none source', async ({ page }) => {
  await page.goto('https://findtorontoevents.ca/', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(8000);

  const result = await page.evaluate(() => {
    const btn = document.querySelector('[title="Configuration Settings (Always Accessible)"]') as HTMLElement;
    if (!btn) return { error: 'Button not found' };

    // Check inline style
    const inlineDisplay = btn.style.display;

    // Check all applied CSS rules
    const sheets = document.styleSheets;
    const matchingRules: string[] = [];

    for (let i = 0; i < sheets.length; i++) {
      try {
        const rules = sheets[i].cssRules || sheets[i].rules;
        if (!rules) continue;
        for (let j = 0; j < rules.length; j++) {
          const rule = rules[j] as CSSStyleRule;
          if (!rule.selectorText) continue;
          try {
            if (btn.matches(rule.selectorText)) {
              const display = rule.style?.display;
              const visibility = rule.style?.visibility;
              if (display || visibility) {
                matchingRules.push(`${rule.selectorText} { display: ${display || 'unset'}; visibility: ${visibility || 'unset'} } [sheet ${i}]`);
              }
            }
          } catch (e) {
            // skip invalid selectors
          }
        }
      } catch (e) {
        // CORS restriction on external sheets
        matchingRules.push(`[sheet ${i}: CORS blocked]`);
      }
    }

    // Check if parent has any hiding
    const parent = btn.parentElement;
    const parentInlineDisplay = parent?.style.display;

    // Also check the outerHTML snippet
    const parentHTML = parent?.outerHTML.substring(0, 500);

    return {
      inlineDisplay,
      parentInlineDisplay,
      matchingRules,
      parentHTML,
      btnOuterHTML: btn.outerHTML.substring(0, 300),
    };
  });

  console.log('=== DISPLAY:NONE SOURCE ===');
  console.log(JSON.stringify(result, null, 2));
});
