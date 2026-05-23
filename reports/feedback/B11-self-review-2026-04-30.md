# B11 Multi-AI Feedback — Self-Review (autonomous loop, 2026-05-01)

## A. Confirmed assumptions

1. **Existing strategy code ready.** `alpha_engine/etf_strategies.py::etf_sector_momentum`
   implements Faber 10-month SMA + 3-month sector momentum across SPDR sector ETFs
   (XLK, XLF, XLE, XLV, IWM, TLT, HYG). This is exactly the "SPDR sector-ETF
   rotation feed" named in the spec. No new strategy code needed.

2. **Wire-Up Rule: opt-in sidecar pattern.** The emitter will write to
   `alpha_engine/data/etf_sector_picks.json` and be registered in
   `JSON_PICK_SOURCES`. Since this is a new source with no track record, marking
   it as opt-in sidecar with a 14-day shadow run before any gate promotion.

3. **Schema compatible with `_extract_picks`.** Uses top-level `"picks"` key (line
   6382 in dashboard_generator.py). Same format as `leveraged_etf_decay_picks.json`.

4. **`_now_iso()` helper already in etf_strategies.py.** Emitter can import directly.

5. **B3 prereq is "B2 in flight"** — B2 is now in-flight (PR #588). B3 can
   proceed in parallel after B11 (or in a later loop iteration).

## B. Surfaced contradictions / blockers

1. **Market data requires yfinance.** The `etf_sector_momentum` strategy needs
   200-day OHLCV data. The emitter will call `yfinance.download()` — requires
   network access. The CI workflow must handle yfinance failures gracefully (empty
   output, not a crash).

2. **ETF active book currently 0 picks.** The kimi 86.8% concentration cited in the
   spec was from an earlier snapshot. Today's ETF active book is empty. This means
   B11's first impact is getting ANY ETF picks into the dashboard, not "diversifying
   away from kimi." This is still valuable.

3. **`etf_emitter_spike.py` already exists but is draft-only.** Production emitter
   should be a new `tools/etf_sector_emitter.py` (clean, gate-aware) rather than
   upgrading the spike.

## C. Recommended deltas

- Create `tools/etf_sector_emitter.py` (production) + `alpha_engine/data/etf_sector_picks.json` (placeholder)
- Register in `JSON_PICK_SOURCES` as opt-in sidecar
- Wiring plan in PR body: target caller = `JSON_PICK_SOURCES` (already the production
  path — picks reach the dashboard immediately on next rebuild)
- yfinance failures → empty picks array (warn, don't crash)

## D. Net verdict

**Ready to ship** as opt-in sidecar. Wire-Up Rule satisfied: registered in
`JSON_PICK_SOURCES` = production caller path (picks reach /audit on next
dashboard rebuild after the emitter cron runs).
