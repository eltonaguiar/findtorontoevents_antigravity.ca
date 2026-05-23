# B20 Multi-AI Review — Codebuff Proxy Review (2026-05-02)

Item: **B20 — Wire fresh penny_picks feed into JSON_PICK_SOURCES**

## A. Confirmed assumptions

1. File hook point `audit_trail/dashboard_generator.py` line ~3931 (after UEPS entry)
   is correct. The pattern `JSON_PICK_SOURCES.append((name, path, None))` matches
   the skyrocket_detector and UEPS entries verbatim.

2. `_extract_picks` function at line 6769 is the correct modification point. Adding
   `"top_picks"` to the recognized keys (line ~6805 tuple) is the minimal change.

3. Wire-Up Rule check: `penny_screener` picks will be consumed by `_load_active_picks`
   (line 6969 loop) → `_normalize_pick` → `active.append(normalized)`. Production
   caller confirmed. Not an orphan.

4. No closed-pick path needed (third tuple element = None). Outcomes will settle via
   universal resolver matching on `source_system="penny_screener"` once the resolver
   is configured to watch for the source. This is acceptable for initial registration.

5. Existing test pattern at `tests/test_skyrocket_detector_wireup.py` and
   `tests/test_ueps_dashboard_wireup.py` provides the template. Test file name
   `tests/test_penny_picks_wireup.py` is consistent with the project convention.

## B. Surfaced contradictions / blockers

1. **Schema mismatch (`top_picks` vs `picks`)**: The doc says "verify the JSON schema
   (top-level `picks` key or similar)" but the file actually uses `top_picks`.
   The acceptance criteria notes "modulo quality gates filter them" — the real gate
   is getting `_extract_picks` to return a non-empty list. Must fix.

2. **No `asset_class` on penny picks** — `derive_asset_class` in `_normalize_pick`
   should infer EQUITY from the exchange field (TSX-V, NYSE, NASDAQ). But the
   inference may not recognize `TSX-V`. Recommend: set `asset_class="EQUITY"`
   in the extraction normalization step as a default for penny_screener picks.

3. **No `id` field** — the pick won't have a stable ID. The dashboard generator
   should synthesize one. `_normalize_pick` does produce an ID from
   `{source_system}::{symbol}::{timestamp}` if `id` is absent.

## C. Recommended deltas

- Add `asset_class="EQUITY"` default in `top_picks` normalization (TSX-V picks
  otherwise may get classified as unknown).
- Add `"top_picks"` to the recognized keys with normalization.
- Confirm `_normalize_pick` synthesizes an ID when none is provided.

## D. Net verdict

**ready-to-ship** with the additions above. Confidence: high. The `top_picks` key
fix is the single blocker; the normalization improvements are defensive.
