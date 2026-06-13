# SNIPE — very-short-term spike entries with a 30-minute self-grading loop (design)

**Status:** DESIGN (pre-registered as H-113 before any data is touched) · **Date:** 2026-06-12
**Operator ask:** "a script to 'snipe' day trading, very short term skyrockets, get in and get out quickly, then make a prediction and test it in 30 minutes to see if you were right, and create a machine learning algorithm around this."

## 0. The elephant in the room: C006

We have already PROVEN that naively buying short-term skyrockets in CRYPTO is an
adverse-selection trap: `volume_spike_breakout` ran n=78 at **WR 16.7%, PF 0.014,
win/loss ratio 0.072** (C006, 2026-05-18) — wins capped at +0.04%, losses to −2.5%.
"Skyrocket + chase" = buying retail FOMO at the local top. Any snipe design that
ignores this gets killed by the do-not-relitigate list, correctly.

**Therefore the experiment is TWO-ARMED by design** — the same trigger fires both:
- **CHASE arm:** enter WITH the spike direction (the operator's intuition).
- **FADE arm:** enter AGAINST it (the C006-implied edge, same shape as H-112
  liquidation-cascade reversal).

Either arm can win; the data decides. This converts a previously-refuted idea into
a falsifiable pair instead of re-litigating it.

## 1. Trigger (SINGLE pre-chosen spec — no threshold fishing, M-107)

On 1-minute bars (Binance klines, failover chain per CLAUDE.md):
- **Spike event:** 5-minute rolling return ≥ **+2.0%** (or ≤ −2.0% for down-spikes)
  AND 5-min volume ≥ **5×** its trailing 2-hour median.
- Universe: top-100 USDT perp/spot symbols by 24h volume (snapshotted daily).
- Cooldown: one event per symbol per 2 hours (first-touch wins).
- Both arms enter at the FIRST 1-min close after the event bar (no look-ahead).

Geometry (both arms): TP +1.0% / SL −0.7% from entry, hard time-exit at **30
minutes** at market (the operator's test horizon IS the time-stop). Costs: 16bp RT.
Break-even WR at this geometry+costs ≈ 47% — graded against that, not 50%.

## 2. The 30-minute self-grading loop (the resolver ships AT BIRTH)

Rule learned 7× today: **a lane without a resolution driver is not an experiment**
(pead 0-signals, swarm book 91% unresolved, A/B no-data, picks-now frozen...).
The snipe loop grades itself:

```
snipe_loop.py (single process or 30-min cron):
  t=0   detect events → write predictions (both arms) to snipe_shadow_log.jsonl
        {event_id, symbol, spike_dir, arm, entry, tp, sl, predicted_at}
  t+30m fetch the 1-min bars for [t, t+30], FIRST-TOUCH replay (SL-wins-ties,
        ambiguous flagged), append outcome to the SAME row. No row unresolved
        >40 min — a staleness assertion fails loudly if so.
```

SHADOW-ONLY: writes its own JSONL (+ optional at_signal_outcomes rows tagged
`source_system='snipe_shadow'`, `forward_test_only=1` so every gate exempts it).
Never sized; never in active_picks.

## 3. Replay leg (velocity — runs FIRST, before any live loop)

180d × 1h bars exist, but this needs 1-min granularity → replay window is whatever
1-min history Binance gives per symbol (~30d). Pipeline:
`tools/replay_harness.py` pattern on the trigger events: dedup (symbol, arm,
hour), net 16bp, R1 time-split, R2 concentration <35%, monkey-P95 (1-min monkey
variant), `pf_ci_lower` cluster bootstrap. **Replay nominates ONE arm (or none).**
If both arms fail CI-LB > 1.0 → family CLOSED, the live loop never starts.

## 4. ML layer (LAST, not first)

Only after ≥500 graded events exist: features at event time (spike magnitude,
volume ratio, spread, BTC beta-5m, time-of-day, funding, prior-30m drift) →
gradient-boosted classifier predicting TP-before-SL **per arm**, walk-forward by
day, leakage rule: features strictly pre-event. The ML gets judged by the same
CI-LB bar, vs the un-ML'd arm as baseline (must BEAT it, not just be positive).
No ML before data exists — the graveyard of 24 stale ML surfaces (audit
2026-06-12) is what "ML first" produces.

## 5. Pre-registration → H-113 (registered alongside this doc)

Family `snipe_spike_30m` — acceptance per arm: replay CI-LB>1.0 at n_eff≥80 +
monkey-P95 + both R1 halves → live shadow loop; live: WR vs 47% breakeven,
CI-LB>1.15 at n≥150 graded events → probation. Falsification: both arms below
breakeven at n=300 events, or trigger fires <5×/day across the universe (too
rare to ever reach n), or 1-min data coverage <80% → CLOSED. The trigger spec in
§1 is frozen — tuning it = new family, full FDR accounting.

## 6. Build order (each step shippable alone)

1. `tools/snipe/spike_event_scan.py` — historical 1-min event extraction (replay input)
2. replay both arms through the harness → registry verdict (GATE: stop here if null)
3. `tools/snipe/snipe_loop.py` — live 30-min predict/grade loop (shadow JSONL + staleness assertion)
4. cron workflow (every 30 min, market-hours aware for non-crypto later; crypto 24/7)
5. ML layer at ≥500 events (separate pre-registered comparison)

## 7. What this is NOT
- Not sized capital — shadow until the full ladder passes (master loop lifecycle).
- Not a re-litigation of volume_spike_breakout: that strategy chased 1h-bar spikes
  with no fade arm, no 30-min stop, no event cooldown; the DNR ban on it stands.
- Not "ML finds the edge" — ML refines a measured edge or dies by the same referee.
