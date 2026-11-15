# 2026-11-15 — FOREX gate live-read, VIX rule combos, data-freshness audit

Follow-up to `2026-11-15-etf-short-gate-headline-and-catalyst-features.md` (already committed as `74a15c46a38`).

## 1. FOREX gate: the switch ignored its own env var

Two pre-existing failures in `tests/test_quality_gates.py` were real defects, not flakes.

**Defect A — import-time read.** `passes_active_gate()` compared against
`_ae_config.FOREX_HARD_DISABLE`, a module attribute frozen at import:

```python
if str(asset_class).upper() == "FOREX" and _ae_config.FOREX_HARD_DISABLE and ...
```

Setting `FOREX_HARD_DISABLE=1` in a running process did nothing. A kill-switch that cannot be
flipped without a restart is not a kill-switch, and in a test it silently produced
`reason=''` (the gate never ran, so nothing was stamped) — which is exactly the failure
`TestForexCopytradeBypas::test_gate_on_still_blocks_other_forex_sources` reported.

**Fix:** read the env live, config value as the default only.

```python
_forex_hard_disable = _truthy(
    os.environ.get("FOREX_HARD_DISABLE"),
    "1" if _ae_config.FOREX_HARD_DISABLE else "0",
)
```

**Defect B — comment contradicted the code.** `alpha_engine/config.py` defaulted the flag to
`"0"` (OFF) but the comment said *"Kill-switch: set env FOREX_HARD_DISABLE=0 to re-enable"* — the
inverse of what the code does. Corrected to "set `FOREX_HARD_DISABLE=1` to RE-DISABLE (the
default is `"0"`/OFF since the re-enable above)", and noted that the gate reads it live.

**Test reconciliation (not weakening).** `TestM044GateParity::test_forex_hard_disable_default_on`
asserted the *2026-05-15* policy (default ON). The policy changed on **2026-06-05**: the class was
re-enabled after `reports/forex_carry_backtest_extended_20260606.json` (PF 1.593 / WR 60.4% /
n=197), which is documented in the config itself, and per-source FOREX losers stayed blocked via
`BLOCKED_SOURCES`. The old test encoded a policy that no longer exists.

The rewritten test is stronger, not looser:

1. asserts `alpha_engine.config.FOREX_HARD_DISABLE is False`, so config drift fails CI (the old
   test asserted the opposite of shipped behaviour, which is why it was quarantined for months);
2. asserts a FOREX pick is **not** tagged `ns_e_forex_hard_disable` under the default policy;
3. `test_forex_hard_disable_env_is_read_live` (new) proves `FOREX_HARD_DISABLE=1` set at call time
   both blocks the pick **and** stamps the reason — the exact regression in Defect A.

Verification: `pytest tests/test_quality_gates.py` → **129 passed** (was **127 passed, 2 failed**);
`pytest tests/test_quality_gates.py -k "forex or M044"` → 16 passed; `tests/test_etf_short_gate.py`
→ 7 passed.

## 2. Combined VIX rules — the regime does interact with breakout

Added six combos to `tools/hours_skyrocket_reverse_engineer.py` next to their candle-only parents,
then re-ran the harness (324,653 hourly bars, base rate 14.52%, EDGAR filings 29, option chains 10).

| pattern | signals | test precision | test lift | avg fwd |
|---|---|---|---|---|
| **VIX>25 + breakout** | 246 | **24.14%** | **1.80x** | **+1.04%** |
| VIX>25 + oversold (RSI<30) | 1,855 | 18.93% | 1.41x | +0.431% |
| VIX>25 + vol surge >1.5x | 3,340 | 18.67% | 1.39x | +0.257% |
| VIX > 25 alone (parent) | 17,182 | 18.61% | 1.39x | +0.410% |
| VIX>25 + squeeze | 4,678 | 18.53% | 1.38x | +0.326% |
| breakout + squeeze (parent) | 4,205 | 17.92% | 1.33x | +0.131% |
| VIX rising (r1>0) + breakout | 2,486 | 17.84% | 1.33x | −0.040% |
| oversold snap alone (parent) | 19,415 | 17.69% | 1.32x | +0.412% |
| 20-bar breakout alone (parent) | 8,962 | 17.16% | 1.28x | +0.112% |
| VIX calm (<18) + squeeze + breakout | 4,068 | 14.38% | 1.07x | −0.003% |

What the combinations actually say:

- **Breakout is where VIX adds value.** Breakout alone 1.28x → VIX>25 + breakout **1.80x**, and it
  is the only top rule with a *positive* forward return (+1.04% against +0.11% for breakout alone).
  That is an interaction, not relabelling: VIX>25 by itself is 1.39x.
- **Squeeze adds nothing.** VIX>25 + squeeze 1.38x vs VIX>25 alone 1.39x — the squeeze condition
  only shrinks the sample from 17,182 to 4,678.
- **Level matters, slope does not.** VIX *rising* + breakout is 1.33x and slightly negative forward,
  against 1.80x for VIX>25 + breakout. It is stress, not direction.
- **Calm regime kills the edge.** VIX<18 + squeeze + breakout is 1.07x with negative forward.

Caveats: n=246 for the winner is small, the sample is one 730-day window, and nothing here is
forward-validated — it is a rule candidate, not a signal. Compare with the filing rule
(`filing + breakout` 1.45x but avg fwd **−0.30%**), which lifted precision while losing money; the
VIX combo is the first hours-scale rule found in this study that lifts *and* pays.

## 3. Data-freshness audit — what was real, what was the panel lying about

Checked every tile against the deployed files. Summary of the operator report:

| tile | reported | reality | verdict |
|---|---|---|---|
| Dashboard Data | 24m ago | live payload fresh | **OK** |
| Edge Stability | 21h 45m | `edge_stability_index.json` + 9 class files regenerated today 08:44Z, internal `as_of` Nov 14 20:03 EST | **AGING (yellow), not stale** |
| AI Leaderboard | 13h 31m | `ai_leaderboard/ai_leaderboard_index.json` 09:23Z today | **OK** |
| Money Ready Verdict | "No data available · unknown" | live file **HTTP 200** with `generated_at: 2026-11-15T22:23:46Z` and a 42 KB payload | **PANEL BUG** |
| Swarm Paper Picks | 162d 18h, red STALE | decommissioned 2026-06-12 (`reports/swarm_paper_picks_decommission_2026-06-12.md`); local files renamed `*_OLD.json`; live file frozen | **RETIRED, mislabelled as stale** |
| Strategy IC Analysis | "failed to load — may be unreachable or missing" | live file **HTTP 200**, `generated_at: 2026-05-29` | **reachable but 170 days old; no generator in repo** |
| DB health caption | "ghost rows 0, status mismatch 0" (static) | live DB-health check reports 22,947 ghost rows / 10 cohorts and 130/24,158 PnL mismatches | **static claim stale, contradicted live check** |
| Per-class rows | ETF/active 3d 4h, BOND/recent_closed 5d 8h | consistent with the same page's own producer warnings: `bond_scanner` no pick 56h, `forward_signals` 82h, `growth_stock_screener` 56h | **real emitter gap, not a display bug** |

Fixes made:

1. **`audit_dashboard/dashboard_freshness.js`** — the Money Ready tile accepted only
   `generated_at`/`generated_date`; it now falls back through `as_of`, `summary.generated_at` and
   `metadata.generated_at`. The most likely cause of the blank tile was a mid-write read (the
   workflow rewrites that file every 15 minutes, and the page was loaded at 22:09Z while the file
   now carries 22:23Z) — a truncated JSON parse yields `null`, which renders as "No data
   available". The fallbacks remove the key-drift failure mode; the race itself is inherent to
   fetching a file that is rewritten under you.
2. **Same file** — `swarm-picks` is marked `decommissioned: true`: rendered grey as
   **DECOMMISSIONED** and excluded from the `hasStale` verdict, so a retired feed no longer makes
   the whole panel announce "STALE SOURCES DETECTED" forever.
3. **`audit_dashboard/template.html`** — IC panel: added a "Frozen feed: generated N days ago … no
   builder exists in the repo" banner when `generated_at` is >72h old, and replaced the
   "unreachable or missing" error with an accurate one (fetch/render failure, explicitly *not*
   evidence the file is missing — it returns 200).
4. **`audit_dashboard/template.html`** — the DB-health caption no longer asserts "ghost rows 0"; it
   points at the live check, because the 2026-05-31 cleanup did not hold and the live check now
   reports ghost cohorts again.

Not fixed (needs producer work, outside this change):

- ETF `active` and BOND `recent_closed` have no new picks in >72h. The page's own monitor already
  names the likely culprits (`bond_scanner` 56h, `forward_signals` 82h, `growth_stock_screener`
  56h). Fixing those means changing scheduler health, not the dashboard.
- `strategy_ic_analysis.json` has no generator in the tree — the panel is now honest about being a
  2026-05 snapshot, but restoring it needs the missing builder.
- Ghost rows / PnL-integrity mismatches are DB-level; the caption no longer lies about them, but the
  rows themselves are untouched.

Note for future debugging: the **local** `audit_dashboard/data/dashboard_data.json` is a
2026-10-23 snapshot (23 days old) while the deployed copy is minutes old. Checking freshness against
the local file will always look stale; check the live URL or the writer's schedule.

## Verification performed

- `pytest tests/test_quality_gates.py` → 129 passed (0 failed; was 127/2).
- `pytest tests/test_etf_short_gate.py` → 7 passed.
- `python3 tools/hours_skyrocket_reverse_engineer.py` → exit 0, 324,653 bars, 109-line report,
  filings 29, option chains 10.
- `node --check audit_dashboard/dashboard_freshness.js` and a `node --check` on the edited template
  script block.
- Live HTTP: `money_ready_verdict.json` 200 with `generated_at` 2026-11-15T22:23:46Z;
  `strategy_ic_analysis.json` 200 with `generated_at` 2026-05-29T11:45:56Z.
- `git show --stat 74a15c46a38` → 16 files, 2,206 insertions (the ETF gate, whole-ledger card,
  harness features, Mercury aliases, research tooling and their docs).
