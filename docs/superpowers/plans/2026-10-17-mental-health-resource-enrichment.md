# Mental Health Resource Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich every existing recommended book, video/channel, app, and podcast on the Sources & References page with accessible media, sourced context, and reliable fallbacks.

**Architecture:** Keep the page as dependency-free static HTML. Replace only the compact Recommended Resources lists with four responsive card sections; use remote authorized artwork, short attributed excerpts, static episode metadata, and a small click-to-load YouTube handler so third-party players do not load until requested.

**Tech Stack:** Static HTML/CSS/JavaScript, Playwright, Open Library Covers, YouTube privacy-enhanced embeds, official app-store/podcast pages, FTP deployment.

---

## File map

- Modify `MENTALHEALTHRESOURCES/Sources_References.html`: resource-card CSS,
  enriched resource markup, media fallbacks, and click-to-load video logic.
- Modify `tests/mental-health-resources.spec.ts`: focused structure,
  accessibility, media-loading, and fallback assertions.
- Create `updates/2026-10-17-mental-health-sources-media-enrichment.md`:
  implementation, sourcing, and verification record.

### Task 1: Add failing resource-page tests

**Files:**
- Modify: `tests/mental-health-resources.spec.ts`

- [ ] **Step 1: Add a test for all enriched categories**

Append inside the existing `Mental Health Resources` describe block:

```ts
test('Sources page presents enriched resource cards', async ({ page }) => {
  await page.goto(`${BASE_URL}/Sources_References.html`);

  for (const id of ['books', 'videos', 'apps', 'podcast']) {
    await expect(page.locator(`[data-resource-section="${id}"]`)).toBeVisible();
  }

  await expect(page.locator('[data-resource-type="book"]')).toHaveCount(4);
  await expect(page.locator('[data-resource-type="video"]')).toHaveCount(4);
  await expect(page.locator('[data-resource-type="app"]')).toHaveCount(3);
  await expect(page.locator('[data-resource-type="podcast"]')).toHaveCount(1);
  await expect(page.locator('[data-podcast-episode]')).toHaveCount(3);
});
```

- [ ] **Step 2: Add accessibility and sourcing assertions**

```ts
test('enriched resources expose media alternatives and sources', async ({ page }) => {
  await page.goto(`${BASE_URL}/Sources_References.html`);

  const images = page.locator('.resource-card img');
  expect(await images.count()).toBeGreaterThanOrEqual(8);
  for (let i = 0; i < await images.count(); i++) {
    await expect(images.nth(i)).toHaveAttribute('alt', /.+/);
    await expect(images.nth(i)).toHaveAttribute('loading', 'lazy');
  }

  await expect(page.locator('.professional-review a')).toHaveCount(4);
  await expect(page.locator('.review-summary time')).toHaveCount(3);
  await expect(page.locator('.resource-card a[target="_blank"]')).toHaveAttribute(
    'rel',
    /noopener/
  );
});
```

- [ ] **Step 3: Add click-to-load video assertions**

```ts
test('sample videos load only after user interaction', async ({ page }) => {
  await page.goto(`${BASE_URL}/Sources_References.html`);

  await expect(page.locator('iframe[src*="youtube"]')).toHaveCount(0);
  const trigger = page.locator('.video-load-button').first();
  await expect(trigger).toBeVisible();
  await trigger.click();
  await expect(page.locator('iframe[src*="youtube-nocookie.com"]')).toHaveCount(1);
  await expect(page.locator('.video-direct-link').first()).toBeVisible();
});
```

- [ ] **Step 4: Run the focused tests and confirm failure**

Run:

```bash
npx playwright test tests/mental-health-resources.spec.ts --project="Desktop Chrome" --grep "Sources page|enriched resources|sample videos"
```

Expected: three failures because the resource sections and controls do not yet
exist.

- [ ] **Step 5: Commit the failing tests**

```bash
git add tests/mental-health-resources.spec.ts
git commit -m "test: cover enriched mental health resources

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 2: Research and record source material

**Files:**
- Create: `updates/2026-10-17-mental-health-sources-media-enrichment.md`

- [ ] **Step 1: Verify book artwork and professional-review sources**

Use official publisher/author pages and Open Library ISBN cover endpoints for:

```text
Feeling Good — ISBN 9780380810338
Atomic Habits — ISBN 9780735211292
The Body Keeps the Score — ISBN 9780143127741
Lost Connections — ISBN 9781632868305
```

Record one professional publication or named professional endorsement per
book. Copy no more than one short sentence and save its exact source URL.

- [ ] **Step 2: Select one representative video per channel**

Verify one public YouTube video ID for each:

```text
Huberman Lab
HealthyGamerGG
Therapy in a Nutshell
TED mental health
```

Select practical introductory videos rather than diagnosis or crisis content.
Record title, video ID, channel, and direct watch URL.

- [ ] **Step 3: Verify app review themes**

For Headspace, Calm, and Wysa, inspect their current Apple App Store and Google
Play listings. Record:

```text
retrieval date
official artwork URL
pricing model
two recurring positive themes
two recurring critical themes
both store listing URLs
```

Do not average store ratings or present review themes as clinical evidence.

- [ ] **Step 4: Verify three current Happiness Lab episodes**

Use the official show site or Apple Podcasts listing. Record the newest three
episode titles, publication dates, official URLs, and one-sentence summaries.

- [ ] **Step 5: Write the evidence table**

Create the update document with headings:

```markdown
# Mental Health Sources Media Enrichment

## What changed
## Book media and excerpt sources
## Video selections
## App review sources and retrieval date
## Podcast episodes and retrieval date
## Verification
```

- [ ] **Step 6: Commit the research record**

```bash
git add updates/2026-10-17-mental-health-sources-media-enrichment.md
git commit -m "docs: record mental health resource sources

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 3: Build the responsive resource cards

**Files:**
- Modify: `MENTALHEALTHRESOURCES/Sources_References.html`
- Test: `tests/mental-health-resources.spec.ts`

- [ ] **Step 1: Add the resource-card CSS**

Add after the existing `.recommended-resources` styles:

```css
.resource-section { margin-top: 2rem; }
.resource-section-header { margin-bottom: 1rem; }
.resource-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}
.resource-card {
  display: grid;
  grid-template-columns: 112px minmax(0, 1fr);
  gap: 1rem;
  min-width: 0;
  padding: 1rem;
  background: var(--surface-1);
  border: 1px solid rgba(255,255,255,.1);
  border-radius: .75rem;
}
.resource-card-media {
  width: 112px;
  min-height: 112px;
  border-radius: .5rem;
  overflow: hidden;
  background: var(--surface-3);
}
.resource-card-media img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.resource-card-body { min-width: 0; }
.resource-card h5 { color: var(--text-1); margin-bottom: .35rem; }
.resource-card p { margin-bottom: .65rem; }
.professional-review {
  margin: .75rem 0;
  padding-left: .75rem;
  border-left: 3px solid var(--pk-500);
  color: var(--text-2);
  font-size: .82rem;
}
.resource-actions { display: flex; flex-wrap: wrap; gap: .5rem; }
.resource-actions a {
  padding: .45rem .7rem;
  border-radius: .4rem;
  background: rgba(236,72,153,.12);
  color: #f9a8d4;
}
.app-logo { object-fit: contain !important; padding: .5rem; }
.review-summary { font-size: .82rem; }
.media-fallback { display: none; padding: 1rem; color: var(--text-2); }
@media (max-width: 720px) {
  .resource-grid { grid-template-columns: 1fr; }
}
@media (max-width: 440px) {
  .resource-card { grid-template-columns: 78px minmax(0, 1fr); }
  .resource-card-media { width: 78px; min-height: 96px; }
}
```

- [ ] **Step 2: Replace the three compact resource lists**

Replace the existing Books, Videos & Channels, and Apps & Podcasts list markup
with four sections:

```html
<section class="resource-section" data-resource-section="books" aria-labelledby="books-title">
  <h4 id="books-title" class="resource-section-header">Books</h4>
  <div class="resource-grid">
    <!-- Insert the four fully sourced book cards recorded in Task 2. -->
  </div>
</section>
```

Repeat with `videos`, `apps`, and `podcast`. Every card uses
`<article class="resource-card" data-resource-type="...">`, sourced text from
Task 2, and remote images with `width`, `height`, `loading="lazy"`, and a
specific `alt`.

- [ ] **Step 3: Add non-destructive image fallbacks**

On every external image:

```html
onerror="this.hidden=true;this.nextElementSibling.style.display='block'"
```

Place this immediately after it:

```html
<span class="media-fallback" aria-hidden="true">Resource image unavailable</span>
```

- [ ] **Step 4: Run the structure and accessibility tests**

Run:

```bash
npx playwright test tests/mental-health-resources.spec.ts --project="Desktop Chrome" --grep "Sources page|enriched resources"
```

Expected: both tests pass; click-to-load video test still fails.

- [ ] **Step 5: Commit the cards**

```bash
git add MENTALHEALTHRESOURCES/Sources_References.html tests/mental-health-resources.spec.ts
git commit -m "feat: enrich mental health resource cards

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 4: Add privacy-enhanced sample videos

**Files:**
- Modify: `MENTALHEALTHRESOURCES/Sources_References.html`
- Test: `tests/mental-health-resources.spec.ts`

- [ ] **Step 1: Add video placeholder CSS**

```css
.video-placeholder {
  position: relative;
  aspect-ratio: 16 / 9;
  border-radius: .6rem;
  overflow: hidden;
  background: #09090b;
}
.video-placeholder img { width: 100%; height: 100%; object-fit: cover; }
.video-load-button {
  position: absolute;
  inset: 0;
  width: 100%;
  border: 0;
  color: white;
  background: rgba(0,0,0,.38);
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}
.video-frame { width: 100%; aspect-ratio: 16 / 9; border: 0; }
```

- [ ] **Step 2: Add a placeholder to each video card**

Use these oEmbed-verified official uploads:

```text
Huberman Lab — qUz93CyNIz0 — Tools for Managing Stress & Anxiety
HealthyGamerGG — DhNcClbtcRg — What's a Healthy Amount of Gaming?
Therapy in a Nutshell — aexBCHZxjvw — Coping Skills for Anxiety or Depression 13/30
TED — yzm4gpAKrBk — Mental Health for All by Involving All
```

The Huberman card markup is:

```html
<div class="video-placeholder" data-video-id="qUz93CyNIz0">
  <img src="https://i.ytimg.com/vi/qUz93CyNIz0/hqdefault.jpg"
       alt="Thumbnail for Tools for Managing Stress and Anxiety"
       width="480" height="360" loading="lazy">
  <button class="video-load-button" type="button"
          aria-label="Play Tools for Managing Stress and Anxiety">Play sample video</button>
</div>
<a class="video-direct-link" href="https://www.youtube.com/watch?v=qUz93CyNIz0"
   target="_blank" rel="noopener noreferrer">Watch directly on YouTube</a>
```

The HealthyGamerGG card markup is:

```html
<div class="video-placeholder" data-video-id="DhNcClbtcRg">
  <img src="https://i.ytimg.com/vi/DhNcClbtcRg/hqdefault.jpg"
       alt="Thumbnail for What's a Healthy Amount of Gaming?"
       width="480" height="360" loading="lazy">
  <button class="video-load-button" type="button"
          aria-label="Play What's a Healthy Amount of Gaming?">Play sample video</button>
</div>
<a class="video-direct-link" href="https://www.youtube.com/watch?v=DhNcClbtcRg"
   target="_blank" rel="noopener noreferrer">Watch directly on YouTube</a>
```

The Therapy in a Nutshell card markup is:

```html
<div class="video-placeholder" data-video-id="aexBCHZxjvw">
  <img src="https://i.ytimg.com/vi/aexBCHZxjvw/hqdefault.jpg"
       alt="Thumbnail for Coping Skills for Anxiety or Depression"
       width="480" height="360" loading="lazy">
  <button class="video-load-button" type="button"
          aria-label="Play Coping Skills for Anxiety or Depression">Play sample video</button>
</div>
<a class="video-direct-link" href="https://www.youtube.com/watch?v=aexBCHZxjvw"
   target="_blank" rel="noopener noreferrer">Watch directly on YouTube</a>
```

The TED card markup is:

```html
<div class="video-placeholder" data-video-id="yzm4gpAKrBk">
  <img src="https://i.ytimg.com/vi/yzm4gpAKrBk/hqdefault.jpg"
       alt="Thumbnail for Mental Health for All by Involving All"
       width="480" height="360" loading="lazy">
  <button class="video-load-button" type="button"
          aria-label="Play Mental Health for All by Involving All">Play sample video</button>
</div>
<a class="video-direct-link" href="https://www.youtube.com/watch?v=yzm4gpAKrBk"
   target="_blank" rel="noopener noreferrer">Watch directly on YouTube</a>
```

- [ ] **Step 3: Add the shared click handler before `</body>`**

```html
<script>
  document.addEventListener('click', function (event) {
    var button = event.target.closest('.video-load-button');
    if (!button) return;
    var placeholder = button.closest('.video-placeholder');
    var videoId = placeholder.getAttribute('data-video-id');
    if (!/^[A-Za-z0-9_-]{11}$/.test(videoId)) return;
    var iframe = document.createElement('iframe');
    iframe.className = 'video-frame';
    iframe.src = 'https://www.youtube-nocookie.com/embed/' + videoId + '?autoplay=1';
    iframe.title = button.getAttribute('aria-label').replace(/^Play /, '');
    iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture';
    iframe.allowFullscreen = true;
    placeholder.replaceWith(iframe);
  });
</script>
```

- [ ] **Step 4: Run the focused video test**

Run:

```bash
npx playwright test tests/mental-health-resources.spec.ts --project="Desktop Chrome" --grep "sample videos"
```

Expected: pass with zero initial iframes and one privacy-enhanced iframe after
click.

- [ ] **Step 5: Commit the video behavior**

```bash
git add MENTALHEALTHRESOURCES/Sources_References.html tests/mental-health-resources.spec.ts
git commit -m "feat: add private click-to-load resource videos

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 5: Run full validation and deploy

**Files:**
- Modify: `updates/2026-10-17-mental-health-sources-media-enrichment.md`

- [ ] **Step 1: Run the complete reliable mental-health suite**

```bash
npx playwright test tests/mental-health-resources.spec.ts --project="Desktop Chrome"
```

Expected: all tests pass.

- [ ] **Step 2: Check HTML for insecure or missing media references**

```bash
! grep -n 'src=\"http://' MENTALHEALTHRESOURCES/Sources_References.html
grep -c 'data-resource-type=\"book\"' MENTALHEALTHRESOURCES/Sources_References.html
grep -c 'data-resource-type=\"video\"' MENTALHEALTHRESOURCES/Sources_References.html
grep -c 'data-resource-type=\"app\"' MENTALHEALTHRESOURCES/Sources_References.html
grep -c 'data-podcast-episode' MENTALHEALTHRESOURCES/Sources_References.html
```

Expected counts: `4`, `4`, `3`, and `3`.

- [ ] **Step 3: Update the verification record**

Record each exact command and pass/fail result in
`updates/2026-10-17-mental-health-sources-media-enrichment.md`.

- [ ] **Step 4: Commit the verified implementation**

```bash
git add MENTALHEALTHRESOURCES/Sources_References.html \
  tests/mental-health-resources.spec.ts \
  updates/2026-10-17-mental-health-sources-media-enrichment.md
git commit -m "feat: complete mental health resource enrichment

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

- [ ] **Step 5: Deploy through the repository-approved mental-health FTP path**

Deploy only the changed mental-health page and update document. Do not run a
broad site upload. If no dedicated helper exists, use the existing FTP
deployment utility with explicit file paths and locally configured credentials.

- [ ] **Step 6: Verify production with cache busting**

```bash
curl -fsSL "https://findtorontoevents.ca/MENTALHEALTHRESOURCES/Sources_References.html?_=$(date +%s)" \
  | grep -q 'data-resource-section=\"books\"'
curl -fsSL "https://findtorontoevents.ca/MENTALHEALTHRESOURCES/Sources_References.html?_=$(date +%s)" \
  | grep -q 'youtube-nocookie.com'
```

Expected: both commands exit `0`.
