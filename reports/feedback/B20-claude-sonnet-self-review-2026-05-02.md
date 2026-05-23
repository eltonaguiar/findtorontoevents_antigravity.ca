# B20 Multi-AI Review — Claude Sonnet Self-Review (2026-05-02)

Item: **B20 — Wire fresh penny_picks feed into JSON_PICK_SOURCES**

## A. Confirmed assumptions

1. `findstocks/portfolio2/data/penny_picks_latest.json` exists, is fresh (2d age),
   and is updated by `.github/workflows/penny-stock-picks.yml` on a weekday 12:00 UTC cron.
   Confirmed: `ls -la findstocks/portfolio2/data/penny_picks_latest.json` → 15132 bytes, May 2.

2. The file uses `top_picks` as its pick-list key (not `picks`). `top_picks` is NOT
   currently in `_extract_picks`'s recognized-keys loop (lines 6805-6862 of
   `audit_trail/dashboard_generator.py`). This is the blocker.

3. Pick schema (`top_picks[0]`): `symbol`, `name`, `price`, `score`, `rating`,
   `exchange`, `country`, `rrsp_eligible`, `z_score`, `f_score`, `rsi`, `mom_3m`,
   `stop_loss`, `take_profit`. Missing: `direction`, `strategy`, `id`, `timestamp`.

4. `_normalize_pick()` at line 6092 handles:
   - `symbol` ✅ (direct map)
   - `price` as `entry_price` fallback ✅ (line 6124)
   - `take_profit`, `stop_loss` ✅ (direct map)
   - `direction` inferred from TP>entry ✅ (lines 6108-6122) — all BUY picks have
     `take_profit > price`, so all infer LONG correctly.

5. Wire-Up Rule: penny_screener will produce picks that flow through quality gates
   before hitting the dashboard. No gate bypass. Additive only. Wire-Up Rule satisfied
   (production caller = `_load_active_picks` via `JSON_PICK_SOURCES`).

## B. Surfaced contradictions / blockers

1. **`top_picks` key missing from `_extract_picks`** — must add it. Risk: None (additive).

2. **No `strategy` field** — `_normalize_pick` will produce empty strategy. Need to
   set `strategy="penny_stock_screener"` in extraction so the pick is labelled
   correctly on /audit. Risk: None.

3. **No `generated_at` / `timestamp` on individual picks** — only at the top level.
   The existing timestamp-propagation logic in `_extract_picks` handles this, but
   only for keys in the recognized loop. Need to apply the same pattern to `top_picks`.

4. **`rating` field not mapped to `direction`** — direction inference via TP>price
   covers all STRONG_BUY/BUY picks correctly. For any SELL picks (not expected from
   this screener but defensive), add explicit `rating` → `direction` mapping.

## C. Recommended deltas

- Add `"top_picks"` to the `_extract_picks` recognized-keys tuple.
- In `_extract_picks`, when `key == "top_picks"`, normalize:
  - Set `p["strategy"] = "penny_stock_screener"` if not already set.
  - Map `rating` → `direction`: BUY/STRONG_BUY → LONG, SELL/STRONG_SELL → SHORT.
  - Apply parent timestamp propagation (same pattern as other keys).
- Register `("penny_screener", "findstocks/portfolio2/data/penny_picks_latest.json", None)`
  in `JSON_PICK_SOURCES` after the UEPS entry.
- Tests: pin `penny_screener` in JSON_PICK_SOURCES, verify `_extract_picks` with
  the real schema, assert direction + strategy normalization.

## D. Net verdict

**ready-to-ship** with the above deltas. LOW risk — additive registration, no gate
changes, quality filters will handle legitimacy assessment separately.
