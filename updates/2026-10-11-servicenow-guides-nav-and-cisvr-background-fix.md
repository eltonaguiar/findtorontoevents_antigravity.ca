# 2026-10-11 — ServiceNow guide nav highlighting + CIS-VR background fix

## What was broken

1. **Top navigation highlighted the wrong guide.**
   Every ServiceNow learning guide (`AIFeaturesOct2026`, `CIS-CSM`, `CIS-VR`)
   carried `aria-current="page"` on the *JavaScript Reference* link instead of
   on its own link. The result was that the header always showed the JavaScript
   guide as the active page, regardless of which guide was open.

2. **CIS-VR page rendered with a white background.**
   The CIS-VR page's stylesheet had lost its `:root` variable block, so the
   light-theme variables it still referenced (`--paper`, `--card`, `--ink`,
   `--line`, `--muted`, `--brand`, `--brand-soft`, `--shadow`) resolved to
   nothing. `body { background: … var(--paper) }` therefore became an invalid
   declaration and the browser fell back to the default white canvas. The
   aurora/orbit background layers existed in markup but were being hidden
   behind a white document background, so the page looked unstyled.

## What was changed

### Navigation (`aria-current`)

Moved `aria-current="page"` off the JavaScript Reference link and onto each
guide's own link:

- `TORONTOEVENTS_ANTIGRAVITY/servicenow/AIFeaturesOct2026/index.html` → AI Features Guide
- `findtorontoevents.ca/CIS-CSM/index.html` → CIS-CSM Study Briefing
- `.worktrees/cis-vr-coding-guide/findtorontoevents.ca/CIS-VR/index.html` → CIS-VR Study Briefing

The existing CSS rule
`.sn-lnav-links a[aria-current="page"] { color:#62f5c7; background:rgba(98,245,199,0.10); }`
then highlights the correct pill.

### CIS-VR background and aesthetics

`.worktrees/cis-vr-coding-guide/findtorontoevents.ca/CIS-VR/index.html`:

- Restored a proper `:root` block with the shared dark-aurora design tokens
  (`#080c14` base, teal-green `#62f5c7` accent, slate-blue `#7aa2ff`), plus
  the legacy light-theme variable names mapped onto dark values so every
  existing rule keeps working.
- Set `html`/`body` to the near-black navy base and removed the broken
  `var(--paper)` gradient/`text-shadow` body rule that produced the white page.
- Added dark glass (`backdrop-filter` + translucent navy) overrides for
  `.hero`, `article`, `.toc`, `.concept`, `.course-card`, `.checklist`,
  `.notice`, `.top-nav`, `.flow`, `.table-map th` and `.code-sample` so the
  page matches the JavaScript reference and AI Features guides.
- Changed the in-page `.top-nav` from `position:sticky` to `position:static`
  so it no longer overlaps the sticky `.sn-lnav` guide switcher.
- Added `aria-hidden="true"` to the decorative background layers and added the
  native CSS `scroll-progress` reading bar used by the other guides.

## How it was verified

- Served the worktree locally (`python3 -m http.server 8111`) and inspected
  the rendered page with browser devtools:
  - `getComputedStyle(document.body).backgroundColor` → `rgb(8, 12, 20)`
  - `.bg-aurora` / `.bg-orbit` layers present and animating
  - `document.querySelector('.sn-lnav-links a[aria-current="page"]').textContent`
    → `CIS‑VR Study Briefing`
  - No console errors or JS exceptions.
- After deploying with `upload_aifeatures.py`, `upload_cisvr.py`,
  `upload_csism.py`, re-fetched the live pages with `curl` and confirmed:
  - `aria-current="page"` is on the correct link on all three guides.
  - The live CIS-VR HTML contains the restored `:root` tokens
    (`--paper:#080c14`) and the `.bg-scene` / `.bg-aurora` layers.

## Deploy

Uploaded via the project's FTP helper scripts (remote base
`findtorontoevents.ca`):

- `python3 upload_aifeatures.py`
- `python3 upload_cisvr.py`
- `python3 upload_csism.py`
