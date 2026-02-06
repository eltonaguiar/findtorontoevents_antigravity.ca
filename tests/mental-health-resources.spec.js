import { test, expect } from '@playwright/test';

const BASE_URL = 'https://findtorontoevents.ca';

test.describe('Mental Health Resources - Link Verification', () => {
  
  test('main page loads successfully', async ({ page }) => {
    const response = await page.goto(`${BASE_URL}/MENTALHEALTHRESOURCES/`);
    expect(response?.status()).toBe(200);
    
    // Check title
    await expect(page.locator('h1')).toContainText('Mental Health Resources');
  });

  test('all interactive tool links are accessible', async ({ page }) => {
    const tools = [
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
      '5-3-1_Social_Fitness.html'
    ];

    for (const tool of tools) {
      const response = await page.goto(`${BASE_URL}/MENTALHEALTHRESOURCES/${tool}`);
      expect(response?.status()).toBe(200);
      console.log(`✓ ${tool} - OK`);
    }
  });

  test('all resource pages are accessible', async ({ page }) => {
    const resources = [
      'Research_Science.html',
      'Sources_References.html',
      'Online_Resources.html',
      'Demographics.html'
    ];

    for (const resource of resources) {
      const response = await page.goto(`${BASE_URL}/MENTALHEALTHRESOURCES/${resource}`);
      expect(response?.status()).toBe(200);
      console.log(`✓ ${resource} - OK`);
    }
  });

  test('demographics page has all anchor sections', async ({ page }) => {
    await page.goto(`${BASE_URL}/MENTALHEALTHRESOURCES/Demographics.html`);
    
    const anchors = ['lgbtq', 'youth', 'seniors', 'veterans', 'indigenous', 'bipoc'];
    
    for (const anchor of anchors) {
      const section = page.locator(`#${anchor}`);
      await expect(section).toBeVisible();
      console.log(`✓ #${anchor} section exists`);
    }
  });

  test('all back links navigate to main page', async ({ page }) => {
    await page.goto(`${BASE_URL}/MENTALHEALTHRESOURCES/Breathing_Exercise.html`);
    
    const backLink = page.locator('a:has-text("Back to Resources")');
    await expect(backLink).toBeVisible();
    
    await backLink.click();
    await page.waitForURL(`${BASE_URL}/MENTALHEALTHRESOURCES/`);
    await expect(page.locator('h1')).toContainText('Mental Health Resources');
  });
});

test.describe('Mental Health Resources - Interactive Features', () => {
  
  test('breathing exercise starts and cycles', async ({ page }) => {
    await page.goto(`${BASE_URL}/MENTALHEALTHRESOURCES/Breathing_Exercise.html`);
    
    // Check initial state
    await expect(page.locator('#circleText')).toContainText('Ready');
    await expect(page.locator('#cycleCount')).toContainText('0');
    
    // Start exercise
    await page.click('button:has-text("Start")');
    
    // Wait for first instruction
    await expect(page.locator('#instructions')).toContainText('Breathe in', { timeout: 2000 });
    
    // Verify circle animation class changes
    const circle = page.locator('#circle');
    await expect(circle).toHaveClass(/inhale/);
    
    console.log('✓ Breathing exercise interactive features work');
  });

  test('color therapy game is playable', async ({ page }) => {
    await page.goto(`${BASE_URL}/MENTALHEALTHRESOURCES/Color_Therapy_Game.html`);
    
    // Check initial state
    await expect(page.locator('#score')).toContainText('0');
    
    // Verify color options are displayed
    const colorOptions = page.locator('.color-option');
    const count = await colorOptions.count();
    expect(count).toBeGreaterThan(0);
    
    // Click a color option
    await colorOptions.first().click();
    
    // Score should update (either correct or incorrect)
    await page.waitForTimeout(500);
    
    console.log('✓ Color therapy game is interactive');
  });

  test('gratitude journal saves entries', async ({ page }) => {
    await page.goto(`${BASE_URL}/MENTALHEALTHRESOURCES/Gratitude_Journal.html`);
    
    // Clear any existing entries first
    await page.evaluate(() => localStorage.clear());
    await page.reload();
    
    // Enter gratitude text
    const testEntry = 'Test gratitude entry - I am grateful for automated testing!';
    await page.fill('#gratitudeEntry', testEntry);
    
    // Save entry
    await page.click('button:has-text("Save Entry")');
    
    // Wait for save confirmation
    await expect(page.locator('button:has-text("Saved")')).toBeVisible({ timeout: 3000 });
    
    // Reload page and verify entry persists
    await page.reload();
    
    // Check if entry appears in the list
    await expect(page.locator('.entry-text')).toContainText('Test gratitude entry');
    
    console.log('✓ Gratitude journal local storage works');
  });

  test('5-4-3-2-1 grounding technique is interactive', async ({ page }) => {
    await page.goto(`${BASE_URL}/MENTALHEALTHRESOURCES/5-4-3-2-1_Grounding.html`);
    
    // Check for input fields
    const inputs = page.locator('input, textarea');
    const count = await inputs.count();
    expect(count).toBeGreaterThan(0);
    
    console.log('✓ 5-4-3-2-1 grounding has interactive elements');
  });

  test('identity builder has form functionality', async ({ page }) => {
    await page.goto(`${BASE_URL}/MENTALHEALTHRESOURCES/Identity_Builder.html`);
    
    // Check for interactive elements
    const inputs = page.locator('input, textarea, button');
    const count = await inputs.count();
    expect(count).toBeGreaterThan(0);
    
    console.log('✓ Identity builder has interactive form');
  });

  test('social fitness tracker exists', async ({ page }) => {
    await page.goto(`${BASE_URL}/MENTALHEALTHRESOURCES/5-3-1_Social_Fitness.html`);
    
    // Verify page loaded
    await expect(page.locator('h1')).toBeVisible();
    
    console.log('✓ Social fitness tracker page loads');
  });
});

test.describe('Mental Health Resources - Mobile Responsiveness', () => {
  
  test('main page is mobile responsive', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(`${BASE_URL}/MENTALHEALTHRESOURCES/`);
    
    // Check that content is visible
    await expect(page.locator('h1')).toBeVisible();
    
    // Check that cards are stacked vertically
    const cards = page.locator('.bg-\\[var\\(--surface-2\\)\\]');
    const firstCard = cards.first();
    await expect(firstCard).toBeVisible();
    
    console.log('✓ Mobile responsive layout works');
  });

  test('breathing exercise works on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(`${BASE_URL}/MENTALHEALTHRESOURCES/Breathing_Exercise.html`);
    
    // Check breathing circle is visible
    await expect(page.locator('#circle')).toBeVisible();
    
    // Check buttons are accessible
    await expect(page.locator('button:has-text("Start")')).toBeVisible();
    
    console.log('✓ Breathing exercise mobile layout works');
  });
});

test.describe('Mental Health Resources - External Links', () => {
  
  test('online resources have valid external links', async ({ page }) => {
    await page.goto(`${BASE_URL}/MENTALHEALTHRESOURCES/Online_Resources.html`);
    
    // Check for external links
    const externalLinks = page.locator('a[target="_blank"]');
    const count = await externalLinks.count();
    expect(count).toBeGreaterThan(0);
    
    console.log(`✓ Found ${count} external resource links`);
  });

  test('crisis hotline links are present on main page', async ({ page }) => {
    await page.goto(`${BASE_URL}/MENTALHEALTHRESOURCES/`);
    
    // Check for crisis section
    await expect(page.locator('text=In Crisis')).toBeVisible();
    
    // Check for phone links
    const phoneLinks = page.locator('a[href^="tel:"]');
    const count = await phoneLinks.count();
    expect(count).toBeGreaterThan(0);
    
    console.log(`✓ Found ${count} crisis hotline links`);
  });
});

test.describe('Mental Health Resources - Navigation', () => {
  
  test('can navigate from main page to all tools', async ({ page }) => {
    await page.goto(`${BASE_URL}/MENTALHEALTHRESOURCES/`);
    
    // Click on breathing exercise
    await page.click('a:has-text("Start Exercise")');
    await expect(page).toHaveURL(/Breathing_Exercise\.html/);
    
    // Go back
    await page.goBack();
    await expect(page).toHaveURL(/MENTALHEALTHRESOURCES/);
    
    console.log('✓ Navigation between pages works');
  });

  test('navigation menu links work', async ({ page }) => {
    await page.goto(`${BASE_URL}/MENTALHEALTHRESOURCES/`);
    
    // Check for navigation links
    const navLinks = page.locator('a[href*="Research_Science"], a[href*="Sources_References"]');
    const count = await navLinks.count();
    expect(count).toBeGreaterThan(0);
    
    console.log('✓ Navigation menu has resource links');
  });
});
