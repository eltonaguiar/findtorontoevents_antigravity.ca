# Mental Health Resource Enrichment Design

Date: 2026-10-17

## Goal

Enrich every book, video/channel, app, and podcast already listed on
`MENTALHEALTHRESOURCES/Sources_References.html` so visitors can understand the
resource before leaving the site. Preserve the page's evidence-focused tone,
crisis information, medical disclaimer, accessibility, and performance.

## Scope

### Books

- Feeling Good by David D. Burns
- Atomic Habits by James Clear
- The Body Keeps the Score by Bessel van der Kolk
- Lost Connections by Johann Hari

Each book card includes:

- Lazy-loaded cover with descriptive alt text and a visual fallback.
- Author, purpose, and a concise "why it may help" summary.
- One short professional-review excerpt or endorsement with named source and
  an outbound source link.
- Existing purchase/reference link.

Quotes must be brief, accurately transcribed, and attributed. The page must not
invent testimonials or imply that popularity is clinical evidence.

### Videos and channels

- Huberman Lab
- HealthyGamerGG
- Therapy in a Nutshell
- TED mental-health talks

Each card includes:

- Channel title and concise scope summary.
- One representative video selected for relevance and accessibility.
- Thumbnail and play control that replaces itself with a
  `youtube-nocookie.com` iframe only after user interaction.
- Direct YouTube link as a no-JavaScript fallback.

No YouTube iframe loads during initial page load.

### Apps

- Headspace
- Calm
- Wysa

Each app card includes:

- Official logo or stable official/app-store artwork with fallback.
- Main use case, supported platforms, and pricing-model caveat.
- A dated summary of recurring positive and critical themes from current App
  Store and Google Play reviews.
- Direct links to the official site and review listings.

Review summaries must distinguish recurring themes from verified clinical
evidence. Do not calculate an aggregate rating across stores.

### Podcast

- The Happiness Lab with Dr. Laurie Santos

The podcast card includes:

- Podcast artwork and show summary.
- Three recent episodes available at implementation time, including title,
  publication date, short official-description summary, and direct episode
  link.
- A visible "episodes checked" date.

Episode data is stored statically in the HTML. This avoids client-side RSS
proxies, CORS failures, and surprise changes. Updates are manual.

## Layout

Use balanced resource cards inside four clearly labeled subsections: Books,
Videos, Apps, and Podcast. Cards use the existing dark/pink visual system and
responsive grid.

- Desktop: two-column cards where content permits.
- Mobile: one column, full-width controls, no horizontal scrolling.
- Covers and logos have fixed aspect-ratio containers to prevent layout shift.
- Quotations are visually secondary to summaries and attribution.
- Embedded media uses a 16:9 responsive container.

The existing Key References list remains intact. The enhanced Recommended
Resources area replaces its current compact lists.

## Data and media sourcing

- Prefer official publisher, author, channel, app-store, and podcast pages.
- Prefer Open Library cover images when a stable ISBN cover is available.
- Use official YouTube thumbnails for the selected video.
- Link every professional excerpt, review synthesis, rating statement, and
  episode to a source.
- Record retrieval dates for volatile review and episode information.
- Do not download or commit third-party media when a stable authorized remote
  image is available.

## Accessibility and safety

- Every meaningful image receives specific alt text; decorative fallbacks use
  empty alt text.
- Play controls are native buttons with accessible labels.
- Keyboard activation must load videos.
- Cards preserve visible focus indicators and sufficient contrast.
- Video iframes receive descriptive titles.
- External links retain `target="_blank"` and
  `rel="noopener noreferrer"`.
- App descriptions include a reminder that wellness apps do not replace
  professional care.
- Crisis and medical-disclaimer content is not moved below the enriched
  catalog.

## Error handling

- Image failures reveal a branded text fallback without collapsing the card.
- YouTube embed failure leaves the direct video link available.
- Missing current review data results in a transparent "review summary not
  available" note rather than an unsourced default.
- Missing podcast episode metadata leaves the show-level link usable.

## Performance

- Add `loading="lazy"` and explicit dimensions to covers, logos, artwork, and
  thumbnails.
- Use click-to-load video embeds.
- Avoid new frameworks and external JavaScript dependencies.
- Keep enhancement JavaScript small and inline with the existing static page.

## Validation

- Run the existing mental-health Playwright suite.
- Add page-specific assertions for all four enhanced sections, image alt text,
  source links, and direct video fallbacks.
- Verify that no iframe exists before interaction and one
  `youtube-nocookie.com` iframe appears after activation.
- Check mobile layout at the existing Playwright device sizes.
- Run an HTML/link sanity check and confirm no mixed-content URLs.
- Verify the deployed page with a cache-busting request after FTP deployment.

## Deployment

Update only `MENTALHEALTHRESOURCES/Sources_References.html` plus the mandatory
`updates/` implementation note and focused tests. Use the repository's
documented FTP deployment path for mental-health pages, then verify the live
URL.
