# Audit — Data Pipeline Gap Checks (2026-04-20)

Companion to the Cursor-run Phases 1-8 (`audit_data_health_pipeline_2285d804.plan.md`).
Cursor covers `dashboard_data.json` structural / cross-field / per-tab audits; this
document covers the **upstream / blocklist / field-population / asset-class / schema**
gaps that the plan did not include. Snapshot: `audit_dashboard/data/dashboard_data.json`
generated ~9 min before audit.

---

## 1. Upstream source-file health

Scan of every non-backup / non-worktree `active_picks.json`. `closed_picks.json` is a
single canonical file at `alpha_engine/data/closed_picks.json`.

| File | Size | Rows | mtime age | JSON OK | Notes |
|---|---:|---:|---:|:---:|---|
| `alpha_engine/data/closed_picks.json` | 13.0 MB | 4818 | 0.2 h | yes | canonical history |
| `alpha_engine/data/active_picks.json` | 252 KB | 108 | 0.0 h | yes | freshest / primary |
| `ml_crypto_predictor/.../live_picks/active_picks.json` | 8.4 KB | 24 | 0.0 h | yes | fresh |
| `multi_asset/data/active_picks.json` | 125 KB | 46 | 0.2 h | yes | fresh |
| `crypto_ml_edge/data/active_picks.json` | 162 KB | 13 | 0.2 h | yes | fresh |
| `copy_trader_intel/data/active_picks.json` | 29 KB | 10 | 0.2 h | yes | fresh |
| `riseoftheclaw/data/active_picks.json` | 28 KB | 6 | 0.2 h | yes | fresh |
| `KIMI_RISEOFTHECLAW/data/active_picks.json` | 28 KB | 6 | 0.2 h | yes | duplicate of riseoftheclaw |
| `mercury2/data/active_picks.json` | 9 KB | 6 | 0.2 h | yes | fresh |
| `smart_money/data/active_picks.json` | 4 KB | 5 | 0.2 h | yes | fresh |
| `battleground/data/active_picks.json` | 2 KB | 5 | 0.2 h | yes | fresh |
| `ml_battleground/system_f_clawsofdoom/data/active_picks.json` | 7 KB | 6 | 0.2 h | yes | fresh |
| **`ml_gatekeeper/data/active_picks.json`** | 43 KB | 50 | **72 h** | yes | **STALE** |
| **`ml_consensus/data/active_picks.json`** | 12 KB | 13 | **119 h** | yes | **STALE, still merged (2 active)** |
| `rl_agent/data/active_picks.json` | 1.5 KB | 5 | 193 h | yes | stale, not in merged output |
| `paper_trading/data/active_picks.json` | 28 KB | 29 | 193 h | yes | stale |
| `KIMI_CLAW_RESEARCH_FEB162026/data/active_picks.json` | 10 KB | 2 | 193 h | yes | stale |
| `ml_battleground/system_{a..e}/.../active_picks.json` | 2 B | 0 | 193 h | yes | empty files, dead feeds |
| `breakout_arena/approach_{a,c}/.../active_picks.json` | 2 B | 0 | 21-193 h | yes | empty |

**Findings**
- Zero JSON-parse failures.
- **`ml_consensus`** feed is 119 h stale yet contributes 2 picks to the live merged
  output (`source_system: ml_consensus` in `picks.active`). Either the writer is
  broken or the merger is reading from a mirrored path. Raise P1.
- `ml_gatekeeper` is 72 h stale; no merged-output picks carry that system tag,
  so dormant but not visible.
- 7 feeds at exactly 193 h (~8 days) implies a mass-dormancy event on/around
  2026-04-12 — worth confirming against a scheduler change that day.

---

## 2. Blocklist cross-reference on `picks.recent_closed` (n=3500)

| Category | 7-day | 30-day | All-time |
|---|---:|---:|---:|
| `_RETIRED_STRATEGIES` picks | 278 | 278 | 278 |
| `_PAPER_ONLY_STRATEGIES` picks | 904 | 910 | 914 |
| `_RETIRED_SYSTEM_STRATEGY_PAIRS` (kimi_signal_tracking/default) | 0 | 0 | 0 |

Note: `recent_closed` timestamps collapse — 99 %+ of entries are within 30 d of
generation, so 7 d ≈ 30 d. A real time-series decay test needs `closed_picks.json`
(4818 rows) not the dashboard's truncated recent_closed.

### Top blocked strategies by closed-pick count (historical damage proxy)

| Rank | Strategy | Category | Closed count |
|---:|---|---|---:|
| 1 | `st_fear_greed_contrarian` | paper-only | **640** |
| 2 | `copy_hl_lb_None` | retired | **278** |
| 3 | `luxalgo_confluence` | paper-only | 157 |
| 4 | `st_obv_support_divergence` | paper-only | 87 |
| 5 | `crypto_mtf_ema_slope_alignment_v1` | paper-only | 15 |
| 6 | `intermarket-flow-scout` | paper-only | 15 |

**Findings**
- Composite pair `kimi_signal_tracking/default` shows **0** in `recent_closed` —
  either the block is fully effective OR (more likely) recent_closed is truncated
  to the last ~N picks and older bleed is hidden. Must re-run on
  `closed_picks.json` to verify.
- `st_fear_greed_contrarian` (640) dwarfs the hard-retired `fear_greed_contrarian`
  — confirms Gemini's 2026-04-19 finding that the `st_`-prefix variant slipped
  past the retired entry. Currently paper-flagged; consider retiring.
- All four RETIRED strategies still present in `recent_closed` means the output
  table has not yet been pruned of pre-block history — **expected**, but a UX
  mitigation should tag them with the block reason in the dashboard rendering.

---

## 3. `forward_wr` vs `strat_fwd_wr` population

Across current dashboard snapshot:

| Pool | n | `forward_win_rate` | `forward_wr` | `strat_fwd_wr` | Disagree > 10 pp |
|---|---:|---:|---:|---:|---:|
| `picks.active` | 31 | **0** | 31 (100 %) | 26 (83.9 %) | 1 |
| `picks.recent_closed` | 3500 | **0** | 3500 (100 %) | 3499 (100.0 %) | **430 (12.3 %)** |

**Findings**
- `forward_win_rate` is fully dead — 0/3531 populated. Safe to remove from any
  remaining reader code per `POST_GEMINI_ACTIONS_2026_04_19.md`.
- `forward_wr` is the only field that is 100 % populated in both pools →
  **canonical**.
- `strat_fwd_wr` has 12.3 % hard disagreement in closed history. Interpretation:
  `forward_wr` is per-pick / per-symbol rolling; `strat_fwd_wr` is strategy-wide.
  Both legitimate but must not be used interchangeably in alerts/scoring.
  Recommend the dashboard show both side-by-side and flag divergence, rather
  than picking one.

---

## 4. Asset-class distribution (active)

Active picks n=31:

```
crypto     : ############################## 21 (67.7%)
equity     : ######## 6 (19.4%)
forex      : ### 2 (6.5%)
commodity  : ### 2 (6.5%)
etf        : 0
bond       : 0
futures    : 0
other      : 0
```

**Crypto 67.7 %** — below the 85 % alert threshold; **PASS**. However etf / bond /
futures are at **0**, which is notable given ~25 paper-flagged strategies across
those classes waiting on validation. Non-crypto breadth exists only via equity
(6) + forex (2) + commodity (2). Log this as baseline for future drift checks.

---

## 5. Schema drift

Six representative active-pick systems sampled.

- **Universal keys:** 134 (across sampled systems)
- **Variable keys:** 58 (present in some systems, absent in others)

System-unique fields (only that system emits them):

| System | Unique keys |
|---|---|
| `polymarket_signals` | `_clamped_to_range` |
| `battleground` | `_opposing_penalty`, `_original_score` |
| `multi_asset_copytrader` | `_score_from_safety_net`, `high_conviction_gate_passed` |
| `tsmom_strategy` | `ml_enrichment` |
| `alpha_engine` | `_opposing_killed` |
| `ml_consensus` | `_cross_asset_confluence` |

PnL-family keys present (no typos, but heterogeneous):
`forward_pnl`, `history_avg_pnl`, `pnl_pct`, `recent_pnl`,
`strat_pnl_ex_top_symbol`, `strategy_top_symbol_pnl_pct`, `sym_track_pnl`.

**Findings**
- No misspellings (`stragegy`, `pnl_percent`, etc.) detected.
- The `_`-prefixed scoring-internal fields (`_opposing_penalty`, `_opposing_killed`,
  `_clamped_to_range`, `_score_from_safety_net`, `_original_score`) are
  leaking into the merged output. They look intended as producer-internal
  debug; the merger should either strip them or the schema should promote them.
- Canonical pnl field is `pnl_pct`; the others are per-domain enrichments.
  Downstream consumers filtering on the wrong one will silently mis-count.

---

## 6. Recommendations — external-AI cross-checks

Coordination prompts to route to peer AIs (they are NOT tasks for us):

1. **Kimi** — Re-run Spearman(`smart_score`, `pnl_pct`) on
   `alpha_engine/data/closed_picks.json` (n=4818) with a piecewise filter at
   smart_score = 0.70 to isolate whether the correlation flips in the top
   quintile. Cursor's Phase-6 counterfactual runs on the dashboard truncation
   (3500), so the full-history signal may be obscured.
2. **Gemini** — Re-verify the `kimi_signal_tracking/default` composite block is
   effective by scanning `closed_picks.json` filtered to `closed_at > 2026-04-19`
   and report count. My `recent_closed` scan shows 0, but the slice may be
   truncated.
3. **Copilot** — Audit the merger that is pulling 2 picks tagged
   `source_system: ml_consensus` into the merged output while the
   `ml_consensus/data/active_picks.json` feed is 119 h stale. Find the reader
   path and whether it's reading a stale cache or a different canonical file.
4. **Kimi** — Run a field-coherence check: for every closed pick where
   `forward_wr` and `strat_fwd_wr` differ by >10 pp (n=430), compute WR vs
   realized `pnl_pct` and tell us which field correlates better with outcome.
   This settles the canonical-field debate empirically.
5. **Gemini** — Sweep the `st_`-prefix family in `closed_picks.json` for
   strategies whose unprefixed form is RETIRED. `st_fear_greed_contrarian`
   (640 picks) is one instance; find the others before they accumulate more
   bleed.

---

**No remediation commits performed.** This is a read-only gap-check.
