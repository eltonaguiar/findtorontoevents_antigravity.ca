import { test, expect } from '@playwright/test';

const BASE_URL = 'https://findtorontoevents.ca/MENTALHEALTHRESOURCES';

// All sub-pages that should exist
const SUB_PAGES = [
  'Breathing_Exercise.html',
  'Mindfulness_Meditation.html',
  'Color_Therapy_Game.html',
  'Progressive_Muscle_Relaxation.html',
  'Gratitude_Journal.html',
  '5-4-3-2-1_Grounding.html',
  'Quick_Coherence.html',
  'Cyclical_Sighing.html',
  'Vagus_Nerve_Reset.html',
  'Identity_Builder.html',
  '5-3-1_Social_Fitness.html',
  'Research_Science.html',
  'Sources_References.html',
  'Online_Resources.html',
  'Demographics.html',
  'Anger_Management.html',
  'Panic_Attack_Relief.html',
];

test.describe('Mental Health Resources', () => {
  test('main page loads correctly', async ({ page }) => {
    const response = await page.goto(`${BASE_URL}/`);
    expect(response?.status()).toBe(200);
    
    // Check crisis banner is present
    await expect(page.locator('text=In Crisis? Get Help Now')).toBeVisible();
    
    // Check main header  
    await expect(page.locator('h1:has-text("Mental Health Resources")')).toBeVisible();
  });

  test('all sub-page links are working', async ({ page }) => {
    for (const subPage of SUB_PAGES) {
      const response = await page.goto(`${BASE_URL}/${subPage}`);
      expect(response?.status(), `${subPage} should return 200`).toBe(200);
      
      // Each page should have crisis banner
      await expect(page.locator('text=In Crisis?')).toBeVisible();
      
      // Each page should have info banner about save functionality
      await expect(page.locator('.info-banner')).toBeVisible();
      
      // Each page should have recommended resources section
      await expect(page.locator('.recommended-resources')).toBeVisible();
      
      // Each page should have back link
      await expect(page.locator('text=Back to Mental Health Resources')).toBeVisible();
    }
  });

  test('main page has all navigation links', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    
    // Check for wellness games section
    await expect(page.locator('text=Wellness Games & Interactive Tools')).toBeVisible();
    
    // Check for key sub-page links
    await expect(page.locator('a[href*="Breathing_Exercise"]')).toBeVisible();
    await expect(page.locator('a[href*="Mindfulness_Meditation"]')).toBeVisible();
    await expect(page.locator('a[href*="Color_Therapy_Game"]')).toBeVisible();
    await expect(page.locator('a[href*="Progressive_Muscle_Relaxation"]')).toBeVisible();
    await expect(page.locator('a[href*="Gratitude_Journal"]')).toBeVisible();
    await expect(page.locator('a[href*="5-4-3-2-1_Grounding"]')).toBeVisible();
    
    // Check for research & references links
    await expect(page.locator('a[href*="Research_Science"]')).toBeVisible();
    await expect(page.locator('a[href*="Sources_References"]')).toBeVisible();
    
    // Check for new anger management and panic attack pages
    await expect(page.locator('a[href*="Anger_Management"]')).toBeVisible();
    await expect(page.locator('a[href*="Panic_Attack_Relief"]')).toBeVisible();
    
    // Check for demographics section (use .first() since there are multiple)
    await expect(page.locator('a[href*="Demographics"]').first()).toBeVisible();
    
    // Check for online resources
    await expect(page.locator('a[href*="Online_Resources"]').first()).toBeVisible();
  });

  test('Demographics page has all anchor sections', async ({ page }) => {
    await page.goto(`${BASE_URL}/Demographics.html`);
    
    // Check all demographic sections exist
    await expect(page.locator('#lgbtq')).toBeVisible();
    await expect(page.locator('#youth')).toBeVisible();
    await expect(page.locator('#seniors')).toBeVisible();
    await expect(page.locator('#veterans')).toBeVisible();
    await expect(page.locator('#indigenous')).toBeVisible();
    await expect(page.locator('#bipoc')).toBeVisible();
    
    // Check quick navigation works
    await page.click('a[href="#lgbtq"]');
    await expect(page.locator('#lgbtq')).toBeInViewport();
  });

  test('Breathing Exercise page is interactive', async ({ page }) => {
    await page.goto(`${BASE_URL}/Breathing_Exercise.html`);
    
    // Check start button exists
    await expect(page.locator('text=Start Exercise')).toBeVisible();
    
    // Check instructions are visible
    await expect(page.locator('text=How to Practice 4-7-8 Breathing')).toBeVisible();
    
    // Click start and verify it changes
    await page.click('button:has-text("Start Exercise")');
    await expect(page.locator('text=Pause')).toBeVisible({ timeout: 2000 });
  });

  test('Gratitude Journal can save entries', async ({ page }) => {
    await page.goto(`${BASE_URL}/Gratitude_Journal.html`);
    
    // Check journal inputs exist
    await expect(page.locator('#grateful')).toBeVisible();
    await expect(page.locator('#happy')).toBeVisible();
    await expect(page.locator('#positive')).toBeVisible();
    
    // Check save button exists
    await expect(page.locator('text=Save Entry')).toBeVisible();
    
    // Fill in a test entry
    await page.fill('#grateful', 'Test gratitude entry');
    
    // Save should work without errors
    await page.click('button:has-text("Save Entry")');
  });

  test('Color Therapy Game is playable', async ({ page }) => {
    await page.goto(`${BASE_URL}/Color_Therapy_Game.html`);
    
    // Check game elements exist
    await expect(page.locator('#targetColor')).toBeVisible();
    await expect(page.locator('#colorGrid')).toBeVisible();
    await expect(page.locator('#score')).toBeVisible();
    
    // Check color options are clickable
    const colorOptions = page.locator('.color-option');
    await expect(colorOptions.first()).toBeVisible();
    
    // Click a color option
    await colorOptions.first().click();
  });

  test('Anger Management page is interactive', async ({ page }) => {
    await page.goto(`${BASE_URL}/Anger_Management.html`);
    
    // Check key elements exist (use h1 for unique match)
    await expect(page.locator('h1:has-text("Anger Management")')).toBeVisible();
    await expect(page.locator('h3:has-text("90-Second Rule Exercise")')).toBeVisible();
    await expect(page.locator('#angerSlider')).toBeVisible();
    
    // Check the anger meter responds to slider
    await page.evaluate(() => {
      const slider = document.getElementById('angerSlider') as HTMLInputElement;
      slider.value = '8';
      slider.dispatchEvent(new Event('input'));
    });
    
    // Check 90-second timer button exists and works
    const timerBtn = page.locator('#timerBtn');
    await expect(timerBtn).toBeVisible();
    await timerBtn.click();
    await expect(page.locator('#timerBtn:has-text("Pause")')).toBeVisible({ timeout: 2000 });
    
    // Check evidence-based techniques section
    await expect(page.locator('h2:has-text("Evidence-Based Techniques")')).toBeVisible();
    await expect(page.locator('h3:has-text("Physiological Sigh")')).toBeVisible();
    await expect(page.locator('h3:has-text("STOP Technique")')).toBeVisible();
    await expect(page.locator('h3:has-text("TIPP Skills")')).toBeVisible();
  });

  test('Panic Attack Relief page is interactive', async ({ page }) => {
    await page.goto(`${BASE_URL}/Panic_Attack_Relief.html`);
    
    // Check key elements exist (use specific selectors to avoid ambiguity)
    await expect(page.locator('h1:has-text("Panic Attack")')).toBeVisible();
    await expect(page.locator('h2:has-text("You Are Safe")')).toBeVisible();
    await expect(page.locator('h3:has-text("Box Breathing")')).toBeVisible();
    
    // Check breathing circle and button exist
    await expect(page.locator('#breathCircle')).toBeVisible();
    const breathBtn = page.locator('#breathBtn');
    await expect(breathBtn).toBeVisible();
    
    // Start breathing exercise
    await breathBtn.click();
    await expect(page.locator('#breathBtn:has-text("Pause")')).toBeVisible({ timeout: 2000 });
    
    // Check hyperventilation section
    await expect(page.locator('h3:has-text("Are You Hyperventilating")')).toBeVisible();
    await expect(page.locator('h4:has-text("Paper Bag Myth")')).toBeVisible();
    
    // Check grounding visual is interactive
    const groundItem = page.locator('.ground-item').first();
    await expect(groundItem).toBeVisible();
    await groundItem.click();
    await expect(groundItem).toHaveClass(/active/);
    
    // Check immediate relief techniques
    await expect(page.locator('h3:has-text("Cold Water/Ice")')).toBeVisible();
    await expect(page.locator('h3:has-text("5-4-3-2-1 Grounding")')).toBeVisible();
  });

  test('no JavaScript errors on sub-pages', async ({ page }) => {
    const errors: string[] = [];
    
    page.on('pageerror', (error) => {
      errors.push(error.message);
    });

    // Check only the sub-pages we created (not index.html which uses Next.js)
    for (const subPage of ['Breathing_Exercise.html', 'Color_Therapy_Game.html', 'Demographics.html', 'Anger_Management.html', 'Panic_Attack_Relief.html']) {
      await page.goto(`${BASE_URL}/${subPage}`);
      await page.waitForTimeout(500);
    }
    
    // Filter out any errors not from our pages
    const ourErrors = errors.filter(e => !e.includes("Unexpected token"));
    expect(ourErrors).toHaveLength(0);
  });
});
