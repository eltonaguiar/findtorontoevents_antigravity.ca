# P2-1 / P2-2 remediation verification — 2026-11-20

Branch `zoo/p0-recovery-2026-11-20` @ `fbf1d20f00c`. Nothing pushed; no workflow triggered; no git mutation.

Every claim is tagged **[observed]** (I ran/read it here) or **[inferred]** (deduced from code, not executed).

---

## P2-1 — Panel rendered in a real browser at two widths

### Setup

- **Browser availability [observed]:** `npx playwright --version` → `Version 1.58.2`; `python3 -c "import playwright"` succeeds; Chromium builds present in `~/.cache/ms-playwright` (`chromium-1117`, `chromium-1243`, …).
- **Server [observed]:** `tools/serve_local.py` only routes the `/audit/` prefix (`grep -n audit tools/serve_local.py` → lines 264–274: `/audit`, `/audit/`, `/audit/<sub>`). It has no `/audit2` route. I therefore served a staging copy from `/tmp/p2render` with `python3 -m http.server 8765` (HTTP 200 for `audit2.html`) rather than patching the server.
- **Payload [observed]:** `audit_dashboard/data/audit3_ledger.json` (582,343 bytes) does **not** contain `per_class_verdicts` — top-level keys are `cells, classes, conventions, coverage, denylist_hits, doctrine, forward_gate, generated_at, hypotheses, kill_tribunal, multiplicity, not_money_ready_disclaimer, persistence, provenance, schema, segments, selection_alpha, source, source_families, source_generated_at` and a membership check returned `False`.
- **Synthesized-for-render payload [observed]:** copied the ledger to `/tmp/p2render/audit3_ledger.json` (the real file was never written — its mtime stayed `Nov 20 03:40`), then ran
  `python3 tools/build_audit2_per_class_panel.py --ledger /tmp/p2render/audit3_ledger.json --payload audit_dashboard/data/dashboard_data.json`
  → `per_class_verdicts: 7 classes from payload_slice_canonical_predicate (3500 rows)`.
  The `--rows` sidecar (`resolved_closed_picks_net.json`) does not exist here, so the payload branch ran. **The rendered page used a synthesized payload, not the on-disk ledger.**

### Render (Playwright + Chromium, headless)

| Width | Screenshot | Size |
|---|---|---|
| 1280px desktop | `reports/screenshots/audit2-desktop-1280px.png` | 592,553 bytes |
| 375px mobile (after fix) | `reports/screenshots/audit2-mobile-375px.png` | 625,930 bytes |

### Assertions

- **Panel renders [observed]:** 7 rows in `#pcRows`, caption populated: `Ledger 2026-11-20T01:57:23.798364+00:00 · denominator mode canonical · rows counted 3500 from payload_slice_canonical_predicate. …`. No JS exception (`pageerror` never fired).
- **Console errors [observed, verbatim]:**
  ```
  error: Failed to load resource: the server responded with a status of 404 (File not found)
  error: Failed to load resource: the server responded with a status of 404 (File not found)
  ```
  These are the two sibling fetches for `audit2_pods.json` and `audit2_forward.json` — I did not copy those into the render directory. The files exist at `audit_dashboard/data/audit2_pods.json` / `audit2_forward.json` and the deploy step uploads them to `/audit2/`, so this is a **harness artifact, not a page defect** [inferred: the fetches succeed when the files sit next to the HTML, as in production].
- **Mobile overflow [observed] — defect:**
  - Before: at 375px viewport, `document.documentElement.scrollWidth = 680`, table width ≈ 569px, and `overflow-x` was `visible` on the section, the card and the body — i.e. the 8-column table pushed the whole document wide with **no scroll container**.
  - Fix applied: one line in `audit_dashboard/audit2.html:17` — `.card{…;overflow-x:auto}`.
  - After re-render: `scrollWidth = 375` (no document overflow), card `overflow-x: auto`, table still 569px and scrolls inside its card. Desktop unchanged (`scrollWidth = 1280`, table 1094px).
- **`inconclusive` for thin classes [observed]:**
  - `COMMODITY  inconclusive  n=9 < 20 — too few rows to judge  9  -0.1176  [-5.542, -2.017]  1.0320  50.00%  8 (1)`
  - `FUTURES    inconclusive  n=1 < 20 — too few rows to judge  1  -0.6246  [-2.948, 5.519]  0.0000  0.00%   1 (0)`
- **Provenance `<details>` [observed]:** opens (set `open = true`, content present) and lists the per-column sources (`mean_cost_bps — class_rollup …`, `n — class_rollup (resolved_closed_view) over the canonical r…`).
- **Badge classes [observed]:** the CRYPTO row's `.v-KILL` cell resolves to `rgb(248, 81, 73)` (the `--bad` red) — styled, not unstyled. `inconclusive` maps to `.v-INSUFFICIENT_N`, which is styled muted (`audit_dashboard/audit2.html:27`) [inferred from the mapping in `verdictClass()` at `audit_dashboard/audit2.js:144`].

---

## P2-2 — CI steps verified statically

- **Valid YAML [observed]:** parsed with `yaml.safe_load` — no error. **14 steps** in the single `ledger` job.

| # | Step | continue-on-error |
|---|---|---|
| 1 | Checkout | — |
| 2 | Fetch live closed-pick ledger | — |
| 3 | Fetch canonical resolved view (optional) | true |
| 4 | Backfill price tables (bounded, best-effort) | true |
| 5 | Selection alpha (optional — needs the price tables) | true |
| 6 | Build audit2 pods sidecar | — |
| 7 | Build audit2 forward summary | — |
| 8 | Build audit3 ledger | — |
| 9 | Edge hunt (alpha vs beta, PIT replay) — advisory | true |
| 10 | Upload edge hunt report | — (`if: always()`) |
| 11 | Build audit2 per-class verdict panel | — |
| 12 | Assert the denylist is armed and recent | — |
| 13 | Commit ledger (data only, [skip ci]) | — |
| 14 | Deploy /audit3 to findtorontoevents.ca | — |

- **Ordering [observed]:** the panel step (11) runs after the ledger build (8) — correct; it edits `audit_dashboard/data/audit3_ledger.json` in place, so it must come after.
- **Script path and flags [observed]:** `tools/build_audit2_per_class_panel.py` defines `--ledger` (required), `--payload`, `--rows` (`argparse`, lines 193–197). The workflow passes exactly `--ledger`, `--payload` and conditionally `--rows`. **No flag mismatch.**
- **Edge-hunt idiom [observed]:** step 9 is `continue-on-error: true`, runs `set +e`, captures `rc`, and `exit 0`s on failure — it cannot fail the job, same shape as the selection-alpha step (5). It is ordered after the ledger build deliberately (comment at `:222`–`:229`).
- **Artifact block [observed]:** step 10 is well-formed — `actions/upload-artifact@v4`, `name: audit3-edge-hunt`, `path: /tmp/audit3/edge_hunt.json`, `if-no-files-found: warn`. If edge hunt fails, the file may not exist, but `warn` means the step does not fail; it just uploads nothing.
- **Sidecar branch [observed + inferred]:** step 11 uses `--rows /tmp/audit3/resolved_closed_picks_net.json` only if that file exists. In this checkout it does not (`/tmp/audit3` is gone; no `resolved_closed_picks_net.json` anywhere), so locally the `--payload` branch would run against `/tmp/audit3/dashboard_data.json` — which also does not exist locally. In CI, step 2 hard-fails unless `/tmp/audit3/dashboard_data.json` was fetched, so the `--payload` path is guaranteed present there [inferred from the step's `exit 1` guard at `:48`–`:51`]; the `--rows` branch depends on step 3's optional fetch of the live sidecar succeeding.
- **Run history [observed]:** `gh` is authenticated as `eltonaguiar`. `gh run list --workflow=audit3-ledger.yml --limit 5` → five recent runs, all `completed success` on `main` (latest `44736699783`, schedule, 2026-11-20T12:32:58Z, 2m32s). These are runs of the workflow as it exists on `main` — **not** of this branch's version, which has never been pushed [inferred: `main` does not contain `fbf1d20f00c`].

---

## Integrity

- No git mutation: no commit, checkout, push, or workflow trigger was issued.
- `sha256sum alpha_engine/audit3_tribunal.py` → `f5b0446e5252332f5f3a934443038e73e765f7def2583e5da4e2c68072211674` (unchanged).
- `audit_dashboard/data/audit3_ledger.json` was not overwritten.
- Only edit made: `overflow-x:auto` on `.card` in `audit_dashboard/audit2.html:17`.
