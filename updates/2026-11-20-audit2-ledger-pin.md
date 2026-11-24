# /audit2 — pin the ledger to the canonical copy and disclose which copy rendered

**Date:** 2026-11-20
**File changed:** `audit_dashboard/audit2.js`
**Surface:** `https://findtorontoevents.ca/audit/audit2.html` (also served at `/audit2/audit2.html`)

---

## What was broken

`audit2.js` located its ledger through a four-entry fallback array, keyed on HTTP 404:

```js
var LEDGER_PATHS = ["audit3_ledger.json", "../audit3/audit3_ledger.json",
                    "../audit/data/audit3_ledger.json", "data/audit3_ledger.json"];
```

Two defects fell out of that ordering.

**1. The first path is permanently dead, so every page load wasted a request.**

`audit3_ledger.json` resolves relative to the page. On `/audit/audit2.html` it becomes `/audit/audit3_ledger.json`. Measured live:

```
404  https://findtorontoevents.ca/audit/audit3_ledger.json
200  https://findtorontoevents.ca/audit3/audit3_ledger.json
200  https://findtorontoevents.ca/audit/data/audit3_ledger.json
```

So `LEDGER_PATHS[0]` could never succeed. The client 404'd on it every load before falling through to a copy that exists.

**2. The render never disclosed which copy it read.**

More than one copy of `audit3_ledger.json` is reachable at the same time. `renderLedger()` printed generator / input-sha / git-sha / generated-at, but not the path. Provenance fields cannot distinguish the copies, because each copy is internally consistent and correctly describes its own population. The only thing that identifies which population a reader is looking at is the URL it came from, and that was thrown away by the fallback chain.

This is the client-side half of the same defect `tools/assert_surface_parity.py` was written for server-side, whose docstring records the 2026-11-19 incident:

```
/audit/data/audit3_ledger.json    627,649 B  generated 18:32:40Z  8,613 rows
/audit3/audit3_ledger.json        665,028 B  generated 21:02:25Z  8,621 rows
--- 2h30m and 8 rows apart, and neither page disclosed which copy it rendered.
```

At the time of this fix the two copies happened to be byte-identical (sha256 `812f035e…`, both `generated_at 2026-11-20T06:37:23Z`, both 8,649 rows). The hazard was latent, not currently firing — nothing enforced that it stayed that way.

---

## What changed

**Canonical copy moved to the front of the chain**, so a normal load reads the authoritative copy on the first request:

```js
var LEDGER_PATHS = ["../audit3/audit3_ledger.json",   // canonical
                    "../audit/data/audit3_ledger.json",
                    "audit3_ledger.json",
                    "data/audit3_ledger.json"];
```

`loadLedger()` now records the path that actually answered:

```js
LEDGER_SERVED_FROM = LEDGER_PATHS[i];
```

and `renderLedger()` leads the provenance line with it, warning when the render did not come from the canonical copy:

```js
var copyWarn = (LEDGER_SERVED_FROM && LEDGER_SERVED_FROM !== LEDGER_PATHS[0])
  ? ' <strong style="color:var(--warn)">Served from fallback copy <code>'+esc(LEDGER_SERVED_FROM)+'</code>, not the canonical copy.</strong>'
  : "";
el("provenance").innerHTML =
  "ledger <code>"+esc(LEDGER_SERVED_FROM||"—")+"</code> · "+ ...
```

The fallback array was kept rather than replaced with a single hard-coded path, because the page is mounted under both `/audit/` and `/audit2/` and a relative path has more than one place to resolve. The fallback is now *ordered and disclosed* instead of *silent*.

No other behaviour changed. Nothing was removed — in particular the prod-only `v.gate.reasons[0]` status display present on `main` is untouched.

---

## How it was verified

Verified against a prod-shaped local fixture (`/audit/audit2.html` + `/audit3/audit3_ledger.json`), using the **real** live ledger (633,608 B) rather than a hand-written stub, with `python3 -m http.server` access logging so requests could be counted. Differential: same fixture, same ledger, only `audit2.js` swapped.

**Original `audit2.js`, canonical present — wastes a request:**

```
GET /audit/audit3_ledger.json          404     <-- dead path[0]
GET /audit3/audit3_ledger.json         200
```

**New `audit2.js`, canonical present — one request, correct copy:**

```
GET /audit3/audit3_ledger.json         200
```

**New `audit2.js`, canonical hidden — falls back and says so:**

```
GET /audit3/audit3_ledger.json         404
GET /audit/data/audit3_ledger.json     200
```

Rendered provenance in that state:

```
ledger ../audit/data/audit3_ledger.json · generator audit3.v2 · input sha 52e0e1a1…
  · git 846b81aca630 · generated 2026-11-20T06:37:23Z
  Served from fallback copy ../audit/data/audit3_ledger.json, not the canonical copy.
```

Rendered provenance with the canonical copy present:

```
ledger ../audit3/audit3_ledger.json · generator audit3.v2 · input sha 52e0e1a1…
  · git 846b81aca630 · generated 2026-11-20T06:37:23Z
```

No fallback warning, and the page still reports `scores 8649 of 14687 closed picks (58.9%). Denominator: canonical.`

`node --check audit_dashboard/audit2.js` → clean.

---

## Note for whoever owns the parity gate

`tools/assert_surface_parity.py` and `.github/workflows/surface-parity.yml` are **not on `origin/main`**. They exist only as untracked files in local worktrees. Until they are committed, the ledger-parity assertion runs nowhere in CI — the two copies being byte-identical today is a convention, not an enforced guarantee.

Related unmerged branch: `origin/chore/single-publisher-audit3-ledger` (`cbf9094cb51`, *"stop audit-dashboard.yml republishing a stale audit3_ledger.json"*) addresses the server-side half and is **not merged**. It is not this agent's work and was left alone.

---

## Scope

Client-side pinning and disclosure only. This changes **visibility**, not data. It does not make the audit3 verdicts any more or less trustworthy, and it should not be read as evidence for any strategy.
