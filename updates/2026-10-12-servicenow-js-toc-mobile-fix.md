# ServiceNow JS guide — TOC sidebar mobile fix (2026-10-12)

## Symptom

User report: the Contents (TOC) sidebar menu "gets cut-off and overlaps other
text" on `https://findtorontoevents.ca/servicenow/javascript/`.

## Diagnosis (measured, not assumed)

Playwright measurements on the live page at 1380/1100/1024/900/768/390px:

- Desktop was fine: `position: sticky`, constrained to 811px, internal scroll,
  grid reserves the 300px column, **no overlap at any width at load**.
- The real defect was a **CSS source-order bug**: the `≤1024px` media query
  that made the TOC `position: static; max-height: none; width: 100%` sat
  BEFORE the base `nav.toc` rule in the stylesheet. Same specificity, later
  rule wins → the mobile override was **dead code** at every viewport. Phones
  therefore got the full sticky treatment: a ~644–700px sticky box (40% of an
  844px screen) with the 2,365px / 53-link list clipped inside it — the
  reported "cut-off" — which then sticks around while the article scrolls,
  reading as overlap.

## Fix

`findtorontoevents.ca/servicenow/javascript/index.html`:

1. Removed the dead `nav.toc { … }` fragment from the early one-line media
   query (kept its `.layout { grid-template-columns: 1fr; }` part).
2. Added a proper `@media (max-width: 1024px)` block **after** the base
   `nav.toc` rule: `position: static; width: 100%; max-height: 40vh;
   overflow-y: auto; overscroll-behavior: contain` — the TOC becomes a
   compact scrollable Contents box at the top of the article on narrow
   screens instead of a sticky sidebar-in-one-column. A code comment warns
   future editors not to move it above the base rule.

## Verification

- Local (Playwright): 390/768/900px → `position: static`, `max-height:
  360px` (40vh), internally scrollable, `overlap: false`; 1380px unchanged
  (`sticky`, 811px).
- Live after FTP deploy: 390×844 → `LIVE 390px: { pos: "static", maxH:
  "337.6px", tocH: 338, scrollable: true, overlap: false }` + screenshot
  showing the compact Contents box above the article, nothing bleeding.
- Pre-fix live re-measurement during the run confirmed the bug
  (`pos: "sticky", maxH: "644px"` on a 390px phone).

## Deployment / git notes

- Redeployed `index.html` to `/servicenow/javascript/` over FTP; live page
  was byte-identical to the working tree before this edit (no clobbering).
- The file also contains a concurrent session's large uncommitted work (11
  diff hunks, mostly content additions already live). To avoid committing
  another agent's in-flight changes, this fix was **deployed but not
  committed**; only this documentation file is committed. If/when the other
  session commits that file, this fix rides along automatically (it is in
  the working tree and on the server).
