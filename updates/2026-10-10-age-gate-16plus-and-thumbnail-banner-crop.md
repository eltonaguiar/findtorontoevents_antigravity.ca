# 2026-10-10 — Card thumbnail "flat colour block" fix + strict 16+ age gate

Two operator-reported problems on findtorontoevents.ca, fixed together:

1. **Event pictures looked "cut off"** — e.g. the TPL *EarlyON Family Fun Time*
   card showed a single random colour instead of the artwork.
2. **Under-16 events in the feed** — the operator wants a **16+ minimum age**;
   if an age cannot be determined the event stays.

---

## Part 1 — Why the pictures were cut off

### Report
> "for https://tpl.bibliocommons.com/v2/events/6a59177f9943bdf31e9f5799 EarlyON
> Family Fun Time event, the picture seems 'cut off' … we are showing a mini
> version of the picture, it's too large and we just see a random color"

### Diagnosis (Playwright + pixel math)

`tools/debug_card_images.js` loads the live site and, for every injected
`.card-thumbnail`, records natural size, box size, computed `object-fit` /
`object-position` and the exact source rectangle that gets painted.

Findings (43 rendered cards):

| | |
|---|---|
| TPL source art | **3925 × 980** (aspect 4.01) "icon banner" JPEGs |
| card box | 284 × 180 (aspect 1.58) |
| `object-fit` | `cover`, `object-position: 50% 50%` (centred) |
| source window actually shown | **30.3% → 69.7% of the width — the dead centre** |

The TPL banner is a mostly-empty gradient with the artwork only in the
right-most ~17% of the frame. Pixel probe of the exact region the browser
paints for the EarlyON banner (`TPLIconBanners-ReadingPrograms&Storytimes.jpg`):

```
whole image    stddev = [ 6.9, 32.6, 21.6]
visible window stddev = [ 2.6, 12.3,  5.1]   mean RGB = [205, 33, 93]  ← flat magenta
right 39%      stddev = [10.2, 45.7, 33.0]   ← where the artwork lives
```

Column-wise detail map of the banner (24 buckets, value = mean stddev):

```
 5 6 8 9 10 11 10 10 9 8 7 6 5 4 2 1 0 0 0 0 0 27 19 0
 5 6 8 9 10 11 10 10 9 8 7 6 5 4 2 0 0 0 0 48 59 63 64 0
 5 6 8 9 10 11 10 10 9 9 8 6 5 4 2 0 0 0 0 64 63 66 68 0
```

So the card was painting a **flat magenta rectangle** — the "random colour"
in the report. It is not a broken image and not a small image being
upscaled: the image loads at 200 OK at full 3925 px resolution; the crop
was landing on the empty part of the art.

The 150 × 150 `thumbnail` variant is no better — it is a squashed copy of the
same banner (mean/stddev match the full image), so switching URL variants
would not help.

### Fix — `TORONTOEVENTS_ANTIGRAVITY/index.html`

* CSS: `.card-thumbnail.card-thumbnail-wide { object-position: right center; }`
* JS: `flagWideThumb(img)` adds that class when `naturalWidth/naturalHeight >= 2.2`
  (and `naturalWidth >= 320`, so tiny icons are ignored).
* `applyThumbnails()` now attaches `onload`/`onerror` **before** assigning
  `src`, and also checks `thumb.complete` for already-cached images.

Normal photos (16:9, 4:5, portrait) are untouched — they keep the centred
`cover` crop.

Alternatives considered and rejected:

* `object-fit: contain` (recommended in `FIXBLANKIMAGES.MD`) letterboxes the
  4:1 banner into a 71 px strip inside the 180 px box — it is no longer cut
  off, but 60 % of the card becomes empty letterbox and the artwork shrinks
  to a few dozen pixels. Worse-looking, not better.
* Switching to the `thumbnail` (150 × 150) variant — squashed, blurry at 1.9×.

### Verification

`tools/verify_thumbnail_fix.js` serves the **patched** `index.html` at the live
origin via `page.route()` (everything else — Next.js chunks, `/next/events.json`
— still comes from production), then asserts:

```
$ node tools/verify_thumbnail_fix.js https://findtorontoevents.ca/
verdict: PASS | total: 43 | wide: 18 | normal: 3 | zeroNatural: 22
failures: 0 | injection errors: []
```

* 18/18 ultra-wide images carry `.card-thumbnail-wide` with computed
  `object-position: 100% 50%` (= `right center`)
* 3/3 normal images keep `50% 50%`
* no new JS errors (the React #418 hydration warning was reproduced on the
  untouched live page too — pre-existing, not from this change)
* screenshot of a wide TPL card: `/tmp/thumbnail_fix_after.png`

Diagnostic script kept at `tools/debug_card_images.js`
(`node tools/debug_card_images.js <url> [titleFilter]`).

---

## Part 2 — Strict 16+ age gate

### Policy (operator decision, 2026-10-10)

> "we have certain events that are actually for ages 4-12 … let's keep our
> events at a minimum age of 16+. If an age cannot be determined then the
> event can stay."

Asked how strict, the operator chose **"Strict 16+"** over the softer
kids-only / kids+teens variants — i.e. an event is dropped when its audience
can be determined to include *anyone* under 16, **including** `Teens (13-17)`,
`Youth`, `Family` and `All Ages` audiences.

Measured impact on the live 22 151-event feed:

| policy | dropped |
|---|---|
| kids-only (audience tops out below 16) | 7 294 (32.9 %) |
| kids + teens/youth | 10 703 (48.3 %) |
| **strict 16+ (chosen)** | **10 989 (49.6 %)** |

### Implementation — `tools/scrapers/age_gate.py`

`age_gate_reason(event)` returns a reason string (for auditing) or `None` to
keep. Evidence, in order:

1. **Structured audience tags** — `Preschool Children (0-5)`,
   `School Age Children (6-12)`, `Children`, `Kids` (under-16);
   `Teens (13-17)`, `Youth` (floor is 13); `Family`, `All Ages` (strict mode).
2. **Categories** — `Family`, *unless* an explicit adult tag
   (`Adults (18+)`, `Older Adults`, `Younger Adults (18-24)`) is present. The
   keyword categoriser files `Gentle Group Exercise for Seniors` and
   `Public Speaking for Newcomers` under `Family`, so the category rule yields
   to an explicit adult audience.
3. **Numeric ages in title/description** — `Ages 0 to 6`, `ages 4-12`,
   `ages 13 and up`, `4 to 12 years`, `up to 8 years old`. Any lower bound
   below 16 drops the event; `Ages 16-18` / `18+` stay.
4. **Grades / early years** — `Grade 1`…`Grade 10` drop; `Grade 11`/`12`
   (16-18) stay; `kindergarten`, `JK`, `SK`, `preschool` drop.
5. **Narrow title keywords** — `EarlyON`, `toddler`, `storytime`, `baby time`,
   `for kids`, `teens`, `youth`. Deliberately narrow: scanning the 4 480 feed
   events with no audience tag, broad words matched nightlife/adult talks
   (`Bi-Bi-Baby: Bi's Gone WILD`, `Therapeutic Support for Adult Survivors of
   Child Sexual Abuse`) — the narrow set does not.

`apply_age_gate(events, log_path=None)` returns `(kept, summary)` with drop
counts per reason plus sample titles; every dropped event can be appended as
JSONL when `AGE_GATE_LOG=/path/file.jsonl` is set. `format_summary()` prints
the audit trail to stdout (visible in the workflow log).

### Wiring (both feed writers)

* `tools/scrape_and_sync_events.py` — gate runs on the **merged** set, before
  `events.json` / `next/events.json` are written, so legacy rows are cleaned
  too and `--dry-run` reports gated counts. This is the command the daily
  `Scrape events` workflow runs.
* `add_missing_events.py` — gate re-applied after manual overrides merge, so a
  hand-curated override cannot push an under-16 event back in.

### Verification

```
$ python3 -m pytest tests/test_age_gate.py -q            25 passed
$ python3 -m pytest tests/test_add_missing_events.py \
      tests/test_tpl_singles_scrapers.py \
      tests/test_events_metadata.py -q                   24 passed
$ python3 tools/scrapers/age_gate.py /tmp/live_events.json
[age-gate] 16+ filter: 10989 dropped / 22151 in (11162 kept)
$ python3 tools/scrape_and_sync_events.py --dry-run      (age-gate summary in log)
```

False-positive/negative audit against the live feed:

* Sampled every `category: Family` hit — seniors/adult workshops are kept by
  the adult-tag override.
* Only 9 kept events have a kid word in the title, and all are correct adult
  events (`LEGO botanicals bloom bar`, `Bi-Bi-Baby: Bi's Gone WILD`,
  `Is the French Immersion Program Right for Your Child?`, …).
* False negatives (kids events that stayed) were not found.

### Notes / limits

* Local `events.json` / `next/events.json` in this checkout are from 2026-06-21
  and were **not** rewritten — they are overwritten by the daily CI scrape,
  and sweeping a 4-month-old copy here would only risk deploying stale data.
  The live feed gets gated on the next `Scrape events` run + deploy.
* Nothing was pushed or deployed; these are local changes only.

## Files changed

| file | change |
|---|---|
| `TORONTOEVENTS_ANTIGRAVITY/index.html` | `.card-thumbnail-wide` CSS + `flagWideThumb()` + handler ordering |
| `tools/scrapers/age_gate.py` | new — strict 16+ gate |
| `tools/scrape_and_sync_events.py` | gate on the merged feed |
| `add_missing_events.py` | gate after manual overrides |
| `tests/test_age_gate.py` | new — 25 tests |
| `tools/debug_card_images.js` | new — Playwright image diagnostic |
| `tools/verify_thumbnail_fix.js` | new — Playwright fix verifier |
