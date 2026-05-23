# Kronos Overlay -- Research & Optimization Notes

## Open research questions (none answered yet -- needs forward eval)

1. **Variant selection.** Default load is `Kronos-small` (24.7M).
   Does `Kronos-base` (102.3M) / `Kronos-large` (499.2M) deliver
   meaningfully better directional accuracy on our specific symbol
   universe (BTC/ETH/majors + 8K-row CRYPTO firehose), or is the
   marginal lift smaller than the inference-latency cost?

2. **`pred_len` sweep.** Currently fixed at 24 bars (24 hours when
   feeding hourly OHLCV). Worth a 6 / 12 / 24 / 48 / 72 grid: short
   horizons are noisier but match our pick TTLs better; long
   horizons absorb noise but may forecast across regime shifts.

3. **Multiplier curve calibration.** The 1.2 / 1.1 / 1.0 / 0.8 / 0.6
   ladder is hand-picked. Once we have >=200 forward picks per cell
   (agree-high / agree-low / disagree-low / disagree-high), recalibrate
   each step against realized WR delta vs the no-overlay baseline.

4. **Per-asset-class thresholds.** `NEUTRAL_THRESHOLD_PCT=0.005` and
   `HIGH_CONVICTION_PCT=0.02` are global. CRYPTO 24h moves dwarf
   FOREX 24h moves -- a 2% Kronos forecast on EURUSD is a tail event
   while on BTCUSDT it's noise. Class-specific thresholds (e.g.
   FOREX 0.5% high-conviction, CRYPTO 3% high-conviction) likely
   needed before per-asset-class wire-up.

5. **Sample-count averaging.** Currently `sample_count=1` (greedy /
   single sample). Kronos's stochastic decoder supports `sample_count>1`
   averaged for variance reduction. Worth a 1 / 4 / 16 sweep on
   inference latency vs forecast stability.

6. **Cache TTL semantics.** LRU keyed on `(symbol, last_bar_ts, pred_len)`
   so within a single scan we never re-infer. Across scans the cache
   re-warms naturally. Question: should we evict on regime-flip events
   (e.g. BTC 4h color flip) even if `last_bar_ts` hasn't advanced?

## Optimizations already applied

- **Lazy import.** `torch` / `kronos` import is wrapped in `try/except`
  at module top; `HAVE_KRONOS=False` if either is absent. Module
  imports cleanly on a vanilla Python + numpy + pandas install.
- **In-memory LRU.** 512 entries, OrderedDict-based, `move_to_end` on
  hit. Cache hit count exposed via `_CACHE.hits` for telemetry.
- **Predictor injection.** `set_predictor()` lets tests + offline
  backtests bypass the real kronos load entirely.
- **DRY_RUN env.** Lets us shadow-eval without touching `confidence`,
  so we can collect a clean delta vs the no-overlay baseline.

## Wire-up criteria (gate before turning on in production)

Before flipping `KRONOS_OVERLAY_ENABLED=1` in `feed_hygiene.py`:

- [ ] >=500 picks scored in DRY_RUN mode across >=2 weeks
- [ ] WR(agree-high-conv picks) >= WR(baseline) + 5pp on >=100 closed trades
- [ ] WR(disagree-high-conv picks) <= WR(baseline) - 5pp on >=100 closed trades
       (i.e. proves the dampener is well-targeted, not just adding noise)
- [ ] No latency regression > 200ms p95 added to `feed_hygiene` step
- [ ] `performance-report.json` updated with the above numbers + commit SHA
       of the report-generating cycle

## References

- Kronos repo: https://github.com/shiyu-coder/Kronos
- Kronos model card (HF): https://huggingface.co/NeoQuasar (org hosting Kronos-* checkpoints)
- Internal: `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (used if forward eval shows the overlay HURTS rather than helps -- mutate before kill)
