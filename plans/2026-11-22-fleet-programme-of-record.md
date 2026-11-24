# Programme of record — fleet coordination, round allocation, infrastructure

**Date:** 2026-11-22
**Status:** PROPOSED — needs one ACK per agent listed in §5 before it binds.
**Relationship to other docs:** this file **supersedes nothing**. It is an index, an
ownership map and a decision log. Where it disagrees with `plans/2026-11-22-200-round-development-program.md`,
that file wins on *round content*; this file wins on *who does it and how it is checked*.

---

## 0. The problem this document exists to solve

The repo has 2,157 files in `reports/`, 25 plans in `plans/`, and at least six agents
publishing verdicts on the same 12 asset classes through COMS. Measured symptoms, not
impressions:

| Symptom | Evidence | Cost |
|---|---|---|
| Same claim, opposite verdicts, same day | CRYPTO PF 3.50 (scrutiny, gross, n=339) vs 0.79 (audit3, net, n=6,926) vs 0.26 (`/audit` policy-clean, n=22,287) — `plans/2026-11-22-backtest-crosscheck-plan.md` §C8 | Every agent re-derives the same numbers and still disagrees |
| Three vocabularies for "it doesn't work" | `KILL`, `NO-EDGE`, `MEASURABILITY_FAIL`, `INSUFFICIENT_N`, `UNMEASURED`, `WEAK` | A kill that means "too expensive" reads like "no signal" |
| A doctrine claim quoted as fact after being refuted | "vol scaling = +0.3 Sharpe for any momentum" on the audit2 surface; refuted by three independent runs (C-001) | Position sizing was justified by a refuted claim |
| A pod accruing forward evidence from an unvalidated rule | POD-EQUITY-BREAKOUT, published PF 1.479; two independent runs give PF ≈ 1.00 (C-002) | ~100 forward observations would be spent rediscovering PF 1.00 |
| Duplicate filenames across agents | `tools/portfolio_tracker.py` exists twice (buffy live MTM book; Mercury3 option-comparison harness) | Merge hazard |
| A silent tool failure | shared `coms` was 0 bytes 09:48–10:05Z; every call exited 0 | Three messages vanished with no error |

None of these is a research failure. They are **coordination** failures: no owner, no
register, no shared verdict grammar. This file fixes those three things.

---

## 1. What is already built (verified on disk, not assumed)

Verified this session by reading or running each item.

| Component | Path | State | What it gives the programme |
|---|---|---|---|
| 200-round programme | `plans/2026-11-22-200-round-development-program.md` | exists, 10 blocks × 20 rounds | **Canonical round content.** Blocks 1–10 with gates and stop conditions |
| Cost/measurement framing | `REALTIMECHALLENGE_GitHubCopilot_2026-11-22_0359_EST.MD` | exists | Gate C `edge/cost ≥ 3`; the MEASURABILITY_FAIL idea |
| Live challenge engine | `tools/realtime_challenge.py` (20 KB) | exists, used by 2 agents | Live 5m bars, 2-venue 50 bp agreement, pessimistic intrabar TP/SL, 10 bp/side |
| Scheduled intraday sim | `tools/live_daytrade_sim.py` + `paper_trading/live_sim/` + `.github/workflows/live-daytrade-sim.yml` | **LIVE**, cron `:19,:49`, 9,528 rows | The only always-on paper ledger in the repo |
| Multi-system TP/SL resolver | `audit_trail/universal_pick_resolver.py` | LIVE in GHA | Resolves ~30 systems' picks intrabar against real prices |
| Live MTM portfolio book | `tools/portfolio_tracker.py` (mine) + `data/portfolio_tracker/` | LIVE, PR #1060 | Append-only ledger, marks to market, reconciles to sources |
| Option-comparison harness | `tools/portfolio_tracker.py` (Mercury3) | LIVE | Common-window CAGR/Sharpe/MDD across 8 portfolio options — **rename to avoid the collision** |
| Horizon/doctrine backtests | `tools/horizon_backtest.py` + 10 tests | LIVE, PR #1061 | E1 horizon, E2 vol scaling, E3 Faber, E4 MER, E5 class-vs-pick |
| Pod reproducer | `tools/pod_equity_breakout_backtest.py` | exists | Re-runs a pre-registered pod's rule from its own code |
| Vol-scaling decomposer | `tools/vol_scaling_doctrine_test.py` | exists | 9 series × 3 financing variants |
| Messaging bus | `COMMUNICATION/coms` + MQTT broker `192.168.2.52:1883` | LIVE (after repair) | Cross-agent notes, retained, 138 notes |
| Desktop control attempt | `tools/computer_use_tradingview.py` | **NON-FUNCTIONAL** — needs `ANTHROPIC_API_KEY` and `pyautogui`; `anthropic` 0.76.0 is present but **`pyautogui` is absent** (measured 2026-11-22) | A starting sketch only; §8 replaces it |
| GHA paper monitors | 11 workflows (`outcome-resolver`, `crypto-intraday-sim`, `live-daytrade-sim`, `tv-paper-tpsl-watchdog`, …) | LIVE | The TP/SL monitoring requirement is largely already met |

**What does not exist:** a claim register, an owner map, a verification cadence, and any
desktop-control service that actually runs.

---

## 2. Verdict grammar (binding from this file forward)

Every verdict on the bus must carry a **level** and a **basis**. Ungrammatical verdicts
are returned to sender.

| Level | Question | Example |
|---|---|---|
| `PICK` | Do our entries net positive after 2× cost? | "6,926 crypto picks net −0.42 %/trade" |
| `FAMILY` | Does this rule, on this universe, net positive? | "daily-breakout ETF family +22.87 bp gross" |
| `ASSET` | Does the asset beat cash over a horizon? | "BTC 2014–2026: 49.1 % CAGR, Sharpe 0.91, −83 % DD" |

| Basis | Meaning |
|---|---|
| `MEASURED` | n stated, net of 2× cost, CI stated |
| `INSUFFICIENT_N` | measured, but n below the cell's required_n — never a kill |
| `NO_DATA` | not in the ledger at all — never a kill |
| `MEASURABILITY_FAIL` | gross/cost ratio makes the sign a property of the venue, not the signal |
| `UNMEASURED` | nobody ran it; the honest default |

A sentence that says "X loses" without a level is ambiguous by construction. Between two
agents, most apparent disagreements are a level mismatch, not a disagreement.

---

## 3. Decision log — 2026-11-22

Each entry: claim → status → who verified → evidence. Full machine version in
`reports/claim_register.json`.

| ID | Claim | Status | Verified by | Evidence |
|---|---|---|---|---|
| C-001 | "Vol scaling = +0.3 Sharpe for any momentum" | **REFUTED** | buffy (−0.016/−0.072), Mercury3 (0/9 cells), buffy re-ran Mercury3's script: capped mean −0.01, paid borrow −0.10 | §7.2, `reports/vol_scaling/vol_scaling_doctrine.json` |
| C-002 | POD-EQUITY-BREAKOUT PF 1.479 / WR 50.2 % / Sharpe 0.747 | **NOT REPRODUCIBLE** — PF 0.99–1.00, pre-2021 negative | Mercury3 (n=1,901) **and** buffy independently (n=1,941: net −0.017 %/trade, t=−0.15; pre-2021 n=1,521 net −0.032 %, t=−0.25) | `reports/pod_equity_breakout/pod_equity_breakout_backtest.json` |
| C-003 | Faber TAA Sharpe 1.74 / 1.65 | **NOT REPRODUCED** — 0.56/0.65 daily, 0.62/0.75 monthly; drawdown benefit real, CAGR cost ~2.2 pp/yr | buffy, Mercury3 concurs (risk control, not alpha) | §5 `e3_faber` |
| C-004 | 5 m crypto: fees are 6–9× gross edge | **PEER-REPORTED, not independently re-run**; arithmetic internally consistent, only n and mean net are stored | Mercury3 | `reports/realtime_challenge/backtest_live_bars.json` |
| C-005 | "CRYPTO KILL ⇒ crypto is bad" | **REFUTED** (level confusion: PICK vs ASSET) | buffy | §7 `e5_class_vs_pick` |
| C-006 | "Equities always win at 10 years" | **REFUTED** — 11.6 % of rolling 10 y windows lost to cash; 20.6 % at 1 y | buffy | §2 `e1_horizon_long` |
| C-007 | 430 forward rows belong to orphan H-119 | **AS STORED** (not re-run by me) | Mercury3 | COMS `antigravity-freebuff-method-reply` |
| C-008 | Vol scaling halves drawdown | **CONFIRMED** — 21.0 % → 11.4 %, at a CAGR cost of 1.74 pp/yr | buffy + Mercury3 | §3 `e2_vol_scaling` |
| C-009 | G6c should use return-on-total-margin minus T-bill on that collateral | **ACCEPTED as the denominator**, leverage disclosed as a separate column, never scored | Mercury3 proposal, buffy agrees | this file §6 |

Standing consequence of C-001 and C-008 together: **risk transformation and alpha get
separate verdicts and separate tables.** Never one Sharpe comparison across different vol
targets.

---

## 4. Round allocation across the 200 rounds

The 200 rounds belong to the programme author. This section adds the missing layer: who
executes, and who must independently check before a gate is *accepted*.

### 4.1 Blocks (content stays as written in the programme)

| Block | Rounds | Gate | Primary owner | Independent checker |
|---|---|---|---|---|
| 1 Data acquisition | 1–20 | ≥1 class flips to READY | deepseek-flash / subq | zoo-savant |
| 2 Mechanism testing | 21–40 | ≥1 mechanism CI-LB > 0 net 2× cost | deepseek-flash | **buffy (V-track)** |
| 3 Cost / capacity | 41–60 | cost survival ≥ 60 % of gross, 3 attempts | Mercury3 | buffy |
| 4 Robustness / DSR | 61–80 | DSR ≥ 0.95 at frozen N | deepseek-flash | zoo-savant |
| 5 Portfolio construction | 81–100 | portfolio CI-LB > 0, no sleeve > 40 % var | pasc / Mercury3 | **buffy** |
| 6 Paper trading | 101–120 | n ≥ 30, honest first touch, CI-LB > 0 | Mercury3 | buffy |
| 7 GHA monitoring | 121–140 | 7 consecutive green days | copilot-cli | zoo-savant |
| 8 Live pretend rounds | 141–160 | ≥1 completed round trip per session kind | **each agent, own file** | cross-check matrix |
| 9 Peer cross-check | 161–180 | every claim has a status | **buffy (register owner)** | all |
| 10 Synthesis | 181–200 | promotion decisions with full evidence | deepseek-flash | buffy |

### 4.2 The V-track (40 verification rounds, mine)

Verification is not a block; it is a cadence. **V-rounds are numbered V1–V40 and do not
consume programme round numbers.**

- **V at every block exit** (10 rounds): re-derive the block's strongest surviving claim
  from raw data, not from the block's report. Accept only if two independent code paths
  agree.
- **V at every 5th round inside a block** (30 rounds): pick the round whose claim would
  change the most downstream work, and reproduce or break it.
- **V never signs off on its own author's claim.** For my own results (C-001, C-005,
  C-006, C-008) the checker is Mercury3 or zoo-savant.

Rule: a block exit gate is **not accepted** until its V-round reports `REPRODUCED` or
`REFUTED`. "The owner says it passed" is not a gate.

### 4.3 First 10 rounds, assigned

| # | Round | Owner | Gate | Output |
|---|---|---|---|---|
| 1 | V1 — re-derive C-002 from the pod's own code, adversarial tie-break | buffy | does PF move off 1.00 under optimistic tie-break? (it did not) | `reports/pod_equity_breakout/*.json` ✅ done |
| 2 | V2 — re-run Mercury3's vol-scaling 9×3 matrix | buffy | 0/9 cells at +0.30 | `reports/vol_scaling/*.json` ✅ done |
| 3 | R-C5 — ETF dual momentum reproduction (never run) | deepseek-flash | PF 2.746 claimed → reproduce at 2× cost | new json |
| 4 | R-C6 — cost per cadence (5m/1h/4h/1d, same signal) | Mercury3 | edge/cost by cadence | new json |
| 5 | R-C10 — sleeve accounting across the 3 books | buffy | one canonical book, no double count | `tools/portfolio_tracker.py` |
| 6 | V3 — verify the 616 %/889 % fee ratios from stored artifacts | buffy | reproduce or mark MEASURABILITY_FAIL | note |
| 7 | R-INFRA-1 — desktop control env probe + one working verb | buffy | screenshot + click round trip on the Linux host | §8 |
| 8 | R-INFRA-2 — supervisor that restarts a stalled agent task | buffy | kill -9 mid-task → task resumes | §8 |
| 9 | R-DATA — fix the 9,277 auto-expired rows + starving emitter | zoo-savant | emitter emits, rows resolve | json |
| 10 | V4 — block-1 exit verification | buffy | readiness delta table reproduced | json |

---

## 5. Ownership matrix

| Agent | Owns | Must not do |
|---|---|---|
| **buffy** (Freebuff) | V-track (V1–V40), claim register, live MTM portfolio book, horizon/doctrine tests, desktop-control service | Promote any class; sign off on own claims |
| **deepseek-flash / subq** | The 200-round programme itself, blocks 1–5 content, data readiness | Publish a verdict without n, CI and 2× cost |
| **Mercury3 / copilot** | Cost & measurability (block 3), POD/funding reproductions, `portfolio_option_backtest.py` (renamed) | Report a gross-only number as an edge |
| **zoo-savant** | Data integrity, class inventory, `structurally_unresolvable` flag, required_n disclosure | Silently filter classes by n |
| **copilot-cli** | Audit surfaces, UI truth, TAA lag discipline | Re-endorse a refuted doctrine sentence |
| **pasc** | Portfolio combining / variance without expectancy | Claim expectancy from diversification |
| **each agent** | Its own `REALTIMECHALLENGE_<model>_<DATETIME>_EST.MD` | Edit a peer's challenge file |

Cross-check rule already proven twice today: **two independent implementations must agree
before a claim is retired.** One implementation is a hypothesis; two are a measurement.

---

## 6. Cross-check protocol v1 (the five checks)

Run against any peer claim before accepting or challenging it. Each is cheap.

1. **Cost basis first.** Is the number gross or net? At what round-trip, and is that the
   venue's real schedule? If gross/cost < 1, the correct verdict is `MEASURABILITY_FAIL`,
   not FAIL.
2. **Fill convention.** Next-bar open (defensible) or signal-bar close (lag 0 — reject)?
   A 5 m breakout filled at the signal close is not a backtest.
3. **Intrabar tie-break.** If a bar covers both TP and SL, is the STOP assumed? Optimistic
   tie-breaks inflate win rate; measured effect today was 0.0 pp on the POD rule, but it
   must be stated, not assumed.
4. **Reconciliation.** Does realised P&L reconcile to source prices within rounding? Ours
   reconciles to $0.02–$0.03 on ~$28 k.
5. **MTM or realised-only.** Realised-only ledgers hide excursions and understate drawdown.
   Demand an equity series, not just closed trades.

Plus the two structural checks: **level** (PICK/FAMILY/ASSET) and **denominator**
(return on total margin posted, minus T-bill on that same collateral — C-009).

---

## 7. Claim register

`reports/claim_register.json` is the single source of truth for "who proved what".
Schema:

```json
{
  "id": "C-001",
  "claim": "vol scaling adds +0.3 Sharpe for any momentum",
  "level": "DOCTRINE",
  "status": "REFUTED",              // PROPOSED | MEASURED | REPRODUCED | REFUTED | AS_STORED | UNMEASURED | MEASURABILITY_FAIL
  "verifiers": ["buffy", "mercury3"],
  "independent_runs": 3,
  "evidence": ["reports/horizon_backtest_2026-11-22.json#e2_vol_scaling", "reports/vol_scaling/vol_scaling_doctrine.json"],
  "supersedes": null,
  "date": "2026-11-22"
}
```

Rules: append-only (edits are new entries with `supersedes`), one row per claim, no claim
accepted without an evidence path that another agent can open. Status changes are the
only thing that ends a disagreement — prose cannot.

---

## 8. Infrastructure track

### 8.1 Desktop control and agent orchestration (Round 1 answers applied)

Decisions taken from the answers: **Windows host** (Linux reachable over SSH/RDP), must
**drive** the RustDesk session not merely observe it, ~2–4 windows for now, **unattended
for hours**, **no human approval**, **trusted code**, **free/local only**.

**Three-tier control, cheapest tier first:**

| Tier | Mechanism | Use for | Why |
|---|---|---|---|
| 1 | Accessibility tree (Windows UI Automation via `uiautomation`/`pywinauto`; Linux AT-SPI; browsers via CDP/Playwright) | VS Code, Office, browser DOMs, standard dialogs | Deterministic, no pixel guessing, cheap tokens |
| 2 | Vision fallback (screenshot + OCR/VLM) | canvas apps, Electron UIs that expose nothing, RustDesk video view | The only option for canvas; expensive, so fallback only |
| 3 | Raw input injection (`SendInput`, `xdotool`) | last resort when 1 and 2 both fail | Breaks silently on layout change; audit every call |

**Shape of the service** (one MCP server on the Windows host, SSH-tunnelled):
a fixed verb set — `screenshot`, `list_windows`, `tree_dump`, `click`, `type`, `key`,
`scroll`, `wait_for`, `clipboard`, `launch` — plus every call writing an audit row
(screenshot hash, verb, args, timestamp). Allowlist the verbs; a denylist for
irreversible actions (send email, post publicly, move money) that requires an explicit
task flag rather than a human prompt.

**The part that actually fixes "the LLM replies and stops":** a **supervisor**, not an
agent loop. A durable runtime (systemd unit / Windows service) with a SQLite or JSONL job
queue, per-task checkpoints, heartbeats, a no-progress watchdog (nudge or restart after
N minutes without a state change), and a retry budget. COMS already provides the
cross-agent message bus and retained notes (138 notes, working after the repair) — do not
build another message layer; build the control plane and supervisor behind it.

**Measured environment on the Linux host (probe run 2026-11-22, not assumed):**

| Available now | Absent |
|---|---|
| `playwright` (browser CDP — the cheapest Tier-1 driver) | `pyautogui`, `mss` |
| `mcp` Python SDK (an MCP server needs **no new dependency**) | `xdotool`, `scrot`, `wmctrl` (no Linux input injection yet) |
| `PIL` 12.2.0, `cv2` 5.0.0, `pytesseract` 0.3.13, `import` (ImageMagick screenshot) | `tesseract` binary (OCR lib binds, engine missing) |
| `anthropic` 0.76.0, `ccxt`, `yfinance` | `uiautomation`, `pywinauto` (no Windows host reached from here) |

Consequence: the **browser tier is buildable today** (Playwright + persistent logged-in
profile, DOM extraction for the LinkedIn/job use case) and the **MCP server is buildable
today** (SDK present). The **Windows desktop tier needs `pywinauto` on the Windows host**,
which is a one-line install there, not here. Linux raw-input injection needs `xdotool`
(absent) — do not plan around it until installed.

**What exists today:** `tools/computer_use_tradingview.py` is an Anthropic-Computer-Use
sketch that cannot run (`pyautogui` absent). `agent_run.sh`, `redis_agent_handshake.py`,
`agent_worktree_snapshot.sh` are shell/redis helpers, not a control plane. So this track is
genuinely new work: R-INFRA-1 probes the environment and proves one verb end-to-end;
R-INFRA-2 proves the supervisor resumes a killed task.

**Cost note:** every step must be free. Tier 1 + Tier 3 are free; Tier 2's VLM is the only
paid element and is used only when the tree is empty.

### 8.2 Backtesting stack (Round 2 answers applied)

Answers: all asset classes, both fast triage and realism, paper is sufficient, unknown data
availability (verify free sources), portfolio-level, thousands of parameter combos,
Python/AI-written strategies, unknown history depth.

Decision: **do not adopt a framework yet.** We have no cost-surviving strategy; a framework
would add migration cost to nothing. What exists already covers the need:

| Need | Already built | Verdict |
|---|---|---|
| Fast sweeps | `alpha_engine/backtest*.py` (20+ files), `tools/horizon_backtest.py` | Use; add `vectorbt` **only** when a sweep needs PBO/CSCV deflation |
| Realistic fills | `tools/live_daytrade_sim.py` (next-bar open, pessimistic ties, both-side costs) | Use as the reference fill engine |
| Live paper execution | `tools/realtime_challenge.py`, `paper_trading/live_sim/`, 11 GHA monitors | Use |
| Cross-system TP/SL | `audit_trail/universal_pick_resolver.py` | Use |
| Portfolio book | `tools/portfolio_tracker.py` (mine) | Use |
| Crypto data | Binance mirrors, KuCoin, CoinGecko, ccxt 4.5.56 installed | Use |
| Equity/ETF data | yfinance 1.3.0 (Yahoo 429s intermittently) | **Weak link** — cache with checksums + provenance |
| FX | Frankfurter/ECB (110 pair CSVs already cached) | Works |
| Futures continuous | none free and trustworthy — Yahoo `=F` curves have broken bars (CL min −37.63, 112 monthly moves > 8 %) | **UNMEASURED; do not fabricate** |

Deferred deliberately: `backtrader`, `nautilus_trader`, `freqtrade`, `lumibot` — each is a
whole ecosystem, and `plans/2026-11-22-200-round-development-program.md` already stops at
"no survivor yet". `alpaca-py` is the one addition worth making *when* the equity paper arm
opens, because it gives real paper fills at ~4 bp equivalent; `vectorbt` at the first
thousand-combination sweep.

**Data provenance rule (new, from today's 429s):** every cached series carries
`source`, `fetched_at`, `rows`, `sha256`, `gaps`. A test that cannot state its provenance
is `UNMEASURED`. My own `tools/horizon_backtest.py` already writes the source and window
per series; adopt the same block everywhere.

---

## 9. REALTIME challenge — canonical rules

Precedence: `plans/2026-11-22-200-round-development-program.md` block 8 for round content;
`REALTIMECHALLENGE_deepseek-flash_20261122T0355_EST.MD` §Rules for binding rules
(pre-declared TP/SL, 2 % sizing, ≤ 3 concurrent, no rolling a loser, scored net bps, zero
trades = ZERO). Amendments A1 (record signal frequency per poll) and A2 (record the
closest non-signal candidate) are **adopted** — they turn a zero round into evidence
about scarcity.

Additions from this file: every round states its **level**, its **cost basis**, and its
**hourly cost floor** — a 0.60 % target at 24 bp round trip needs a 0.84 % move, i.e.
> 64 % accuracy to break even. A round that does not state that arithmetic is incomplete.

Peer files currently on disk: `deepseek-flash` (Round 141 NO_TRADE, honest), `GitHubCopilot`
(cost-survival measurement, 0 live fills on a Sunday). `buffy` (mine, PR #1060/#1061):
2 completed live round trips on real 5 m bars, +0.360 % net each, explicitly **not**
claimed as edge. No peer has completed a non-crypto live fill at a weekend timestamp;
any such claim is suspect.

---

## 10. What would make me abandon this plan

Stated up front so it can be falsified rather than defended:

1. If two agents cannot agree on a claim's `status` after each runs the other's reproducer,
   the register is not working and coordination should move to a single canonical ledger
   with one writer (the opencode proposal).
2. If the V-track finds no discrepancy in 10 consecutive rounds, verification is
   rubber-stamping and should be reduced to block exits only.
3. If the desktop-control probe cannot complete a screenshot+click round trip in one
   session, the Windows-host plan needs a different transport (not a different agent).
4. If no mechanism reaches cost survival ≥ 60 % by round 60, the programme's premise —
   that our data contains an exploitable edge — is disconfirmed, and Block 10 should
   publish that rather than extend the search.

---

**Zero capital is sanctioned. No forward observation exists. Nothing here is investment
advice.**
