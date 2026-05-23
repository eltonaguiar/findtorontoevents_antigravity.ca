# Action Items — Status Snapshot (2026-05-01)

Broadcast to repo peers. Live as of 2026-05-01 23:25 UTC.

## ✅ COMPLETED THIS SESSION

### P0 — System bug + tooling (PR #597 — investigate/usdchf-concentration-2026-05-01)

| # | Item | Evidence |
|---|---|---|
| **P0-1** | **rapid_fire pair-blocklist bypass closed** | `alpha_engine/isolated_signal_integrator.py` now imports + calls `is_blocked_pick({strategy, source_system})`. Catches `_RETIRED_SYSTEM_STRATEGY_PAIRS` like `("rapid_fire","macd_rsi_confluence")` that the bare-name `kill_list` missed. Pre-fix: 2 BANNED-tier picks (SOLVUSDT/ORCAUSDT) leaked 11h post-kill on 2026-04-30 per `reports/24h_verification_2026_04_30.md` §C. Post-fix verified by `is_blocked_pick({"strategy":"macd_rsi_confluence","source_system":"rapid_fire"}) == True`. **5 regression tests** pin the gate. |
| **P0-2** | **USDCHF=X concentration FALSIFIED** | Read-only investigation by sub-agent: actual share = **0.99% of book PnL** (not 261% as 7-day-commit-review subagent claimed). PF with USDCHF: 1.293, ex-USDCHF: 1.291. Same strategy `forex_rsi2_mean_reversion` works across 12 FX pairs (no single-symbol overfit). Toxic-concentration auto-flag (≥70% share) actually fires for `multi_asset_cot::CT=F` (96.4%) and `mercury2_fast::BTCUSDT` (91.7%) — **not** USDCHF. Recommendation: keep as-is. Side-finding logged: `KIMI_RISEOFTHECLAW/data/closed_picks.json` resolves some SL_HIT as WON for USDCHF (separate ticket). Full report: `updates/2026-05-01-usdchf-concentration-investigation.md`. |
| **P0-3** | **Pick revalidator module** | New `alpha_engine/pick_revalidator.py` exposing `revalidate_pick(pick, live_price)` and `filter_picks_by_live_quote(picks_with_quotes)`. Pure-function gate that re-anchors R:R to live price, returns OK / PLAYED_OUT_TP / PLAYED_OUT_SL / R_R_DEGRADED / MISSING_FIELDS / BAD_DIRECTION. IC-anti-pred cutoff at R:R ≥ 3.0 (per `elite_scorer.py:1731`). **14 tests** cover all verdict branches. **Sidecar / not yet wired** into `smart_picks_engine.py` — separate wire-up PR per CLAUDE.md Wire-Up Rule. Addresses the recurring null-trade pattern documented in `updates/2026-05-01-portfolio-update-synthesis.md` (4 nights of every-gate-passing-pick failing at trader-read-time). |

### Tests + commits
- 19 new tests across 2 files, all pass on Python 3.14
- Commits: `ae31b43979` (P0 fixes) + `520cfb92f1` (USDCHF report) on PR #597
- PR title + body updated to reflect multi-purpose scope

### Reports added
- `updates/2026-05-01-portfolio-update-synthesis.md` — audit per-asset-class + 7-day commit review + portfolio state
- `updates/2026-05-01-usdchf-concentration-investigation.md` — USDCHF deep-dive (FALSIFIED)
- `THEASK.md` — top-level consolidated fixes doc (existed prior, referenced)

## 📋 REMAINING — P1 / P2 (deferred to follow-ups)

### P1 — Verify or kill the shelfware
| Item | Why it matters | Owner |
|---|---|---|
| Wire `pick_revalidator.py` into `smart_picks_engine.py:_filter_pick()` | Sidecar is dead weight until production caller exists. Per CLAUDE.md "Wire-Up Rule," needs separate PR with named caller. Insertion point: lines 776-850, near existing `tp_already_hit` / `too_stale` gates. | Open |
| Flag-flip-or-kill exercise: PR #525/#526/#530/#543/#544 | All default-off env flags nobody flipped. Each week, pick one and either flip-and-measure or admit it's dead. Per `reports/24h_verification_2026_04_30.md` §A, zero of these flags appeared in any workflow. | Open |
| Post-merge measurement docs for #539 (HC gate), #521 (JNJ blacklist), #519/#522/#523 (dormant unblocks) | All landed with no measurable outcome doc. CLAUDE.md "Wire-Up Rule" requires "## Wiring Plan" with measurable outcome. | Open |
| Side-finding: KIMI_RISEOFTHECLAW resolver mislabels SL_HIT as WON for USDCHF | Found during P0-2 investigation. Not folded into dashboard headline so doesn't affect PF 0.98, but separate fix needed. | Open |

### P2 — Asset-class focus
| Item | Why | Owner |
|---|---|---|
| Kill or rename ETF + FUTURES | PF 0.28 (ETF) / 6.3% WR (FUTURES) ≠ "phenomenal." MAJOR GOAL #1 banner is aspirational, not realized. | Open |
| HYROTRADER subpage: populate or add PRE-LAUNCH badge | All performance tables empty ("Loading…" / "—"). Visitors think empty state is a bug. | Open |
| Investigate the actual 261%-of-PnL concentration claim source | The 7-day-commit-review subagent quoted "261% of total PnL" for USDCHF. P0-2 falsified that on `recent_closed` (n=3,500). Either it came from a different ledger (e.g., headline `valid_closed_picks=8919` population) or was a hallucination. Worth knowing for confidence in future subagent claims. | Open |

### P3 — Trading discipline
| Item | Why | Owner |
|---|---|---|
| Don't force trades when nothing passes live re-validation | Tonight's no-trade was the right call. Pattern recurring across 4 nights. | Behavioral, no PR needed |
| Add SHORT exposure when picker emits a fresh, live-actionable SHORT | Both books are 100% LONG in fear regime. System data favors SHORTs in fear (66% WR vs LONGs 44%) but no SHORT signal has lived long enough at fresh prices. Will trigger naturally once pick_revalidator is wired and emits live-revalidated SHORTs. | Behavioral / depends on P1 wire-up |

## 🤖 SCHEDULED REMOTE AGENTS (5 queued)

| ID | Fires (UTC) | Purpose |
|---|---|---|
| `trig_016BGfrAUFFo1D4K22kVCVEh` | 2026-05-05 14:00 | Value screener v1.1 week-1 review |
| `trig_01T9LHbKMV1qfnfua1EWyVDT` | 2026-05-06 18:00 | ml_enhanced track-record gate prediction verify |
| `trig_01T1t4DwhJh7biPB44ieWf2j` | **2026-05-08 23:00** | **Rapid_fire pair-block fix verify** (NEW — verifies P0-1 holds in next 7d window) |

(Earlier agents already fired: UEPS verify 2026-04-29 + V4 shortlist 2026-04-30.)

## 🔗 KEY ARTIFACTS

- **PR #597** — https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/597 (P0 fixes + USDCHF investigation)
- **THEASK.md** — top-level consolidated fixes doc
- **`alpha_engine/ml_enhanced_track_record_gate.py`** — earlier session work (PF 0.75 → 1.58 backtest), separate PR pending
- **`alpha_engine/pick_revalidator.py`** — this session, sidecar pending wire-up
- **Memory updates** in this session: documented in tonight's edits to `memory/` per auto-memory protocol

## 📞 COORDINATION NOTE TO PEERS

If you're working on:
- **smart_picks_engine.py** — heads up that `pick_revalidator.py` is ready to wire in. Insertion at the existing gate chain.
- **Resolver thresholds / vol-target work** (peer 9u6zld76) — no overlap with my files. Separate concerns.
- **Anything claiming "USDCHF=X carries N% of PnL"** — re-derive from current data; the 261% figure was wrong by 2 orders of magnitude.
- **rapid_fire BANNED picks** — should now be blocked at integrator level per PR #597. If you see new `(rapid_fire, macd_rsi_confluence)` picks in `recent_closed` after 2026-05-01 23:00 UTC, the gate has regressed; ping me.

— Claude Opus 4.7 session 2026-05-01
