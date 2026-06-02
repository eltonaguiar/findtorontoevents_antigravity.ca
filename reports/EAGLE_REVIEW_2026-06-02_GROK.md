# EAGLE Family Review — All Recent Plans (2026-06-02)

**Author:** Grok (Cursor)  
**Date:** 2026-06-02  
**Purpose:** Deduped review of every recent `EAGLE*.MD` in-repo; canonical execution path for Goal #1.  
**Canonical plans (Grok):** [`EAGLE_2026-06-02_GROK.md`](EAGLE_2026-06-02_GROK.md) (root cause + pipeline + monitoring + mutation) · [`EAGLE2_2026-06-02_GROK.md`](EAGLE2_2026-06-02_GROK.md) (workstreams A–E + §9–12).

---

## 1. Executive consensus (all models agree)

| Theme | Consensus |
|-------|-----------|
| Not “wait longer” for main book | CRYPTO/EQUITY/FOREX have enough n; PF still &lt; 1 at policy-clean |
| Wait for forward n | **ETF dual momentum**, crypto VWAP/Bollinger pilots, Faber |
| Research ≠ production | Tournament / funnel / swarm ≠ `money_ready_verdict` |
| Portfolio not empty | 81 PF keys, 66 with opens; `deepseek_v4__aggressive` has 11 opens |
| Edge location | Tournament (deepseek_v4) + lab sleeves — **not** main Smart Picks aggregate |
| Fix order | Honesty → admissibility CLI → emitter diet → tournament bridge |

**Live numbers (2026-06-02 `money_ready_verdict.json`):** 0/9 `MONEY_READY`; CRYPTO PF **0.89** n=374; EQUITY PF **0.33** n=52; FOREX PF **0.48** n=32.

---

## 2. File inventory (June 2026 — review these, not May-27 duplicates)

| File | Model | Role | Keep? |
|------|-------|------|-------|
| `reports/EAGLE_2026-06-02_GROK.md` | Grok | **Root cause + how-to** (audit + leaderboard + pipeline §D–F) | **Canonical** |
| `reports/EAGLE2_2026-06-02_GROK.md` | Grok | **Execution backlog** A–E + quant synthesis §9–12 | **Canonical** |
| `reports/EAGLE_JUNE2_GROK.md` | Grok | Earlier full quant review | Superseded by EAGLE + EAGLE2 |
| `reports/EAGLE2_2026-06-02_COMPOSER.md` | Composer | Same architecture, M-108 refs | Peer — align to EAGLE2_GROK |
| `reports/EAGLE2_2026-06-02_CLAUDE_CODE.MD` | Claude Code | Workstream parity | Peer |
| `reports/EAGLE2_2026-06-02_GPT5_3_CODEX.MD` | GPT-5.3 Codex | Workstream parity | Peer |
| `reports/EAGLE2_2026-06-02_deepseek_v4.MD` | DeepSeek v4 (Mercury) | 12-week ops timeline + Grafana | Peer — see §4 |
| `mercury2/EAGLE2_2026-06-02_deepseek_v4.MD` | DeepSeek | Duplicate of above (plain text) | Archive → use `reports/` copy |
| `EAGLE2_2026-06-02_deepseek_v4_flash.MD` | DeepSeek flash | Variant | Optional |
| `EAGLE3_2026-06-02_minimax-m3-free.MD` | MiniMax | Tournament pick-level matrix | **Use for D-workstream only** — warns tournament ≠ production |
| `EAGLE2_JUNE2_MIMO_V2_5_PRO.MD` | Mimo | Peer plan | Optional |
| `EAGLE2_2026-06-02_CLAUDE_OPUS_4_7.MD` | Opus 4.7 | Peer plan | Optional |
| `EAGLE.MD` (root) | Legacy | Pre-June | **Do not cite** for sizing |
| `.qwen/worktrees/.../EAGLE*.md` | Various | Stale copies | Ignore — use shortest `reports/` path |

**Rule:** For capital decisions, cite only `money_ready_verdict.json` + `reports/EAGLE_2026-06-02_GROK.md` / `EAGLE2_2026-06-02_GROK.md`.

---

## 3. `/audit` vs `ai_leaderboard.html` — unified root cause

### `/audit` (production)

1. **Emitter dilution** — `emitter_census_latest.json`: CRYPTO top source `battleground_luxalgo` 43%; EQUITY/STOCKS `regime_terminal` / `multi_asset_copytrader` 58–100%. Raw closed_picks PF looks “OK” while policy-clean PF is sub-1.  
2. **Wrong promotion layer** — Smart/VA tiles vs `money_ready_verdict`.  
3. **Lab not dominant** — verified sleeves opt-in (`production_scanner` 3b-VFD).  
4. **Concentration** — CRYPTO `top_source_share` 54.6% → verdict capped.  
5. **Resolver** — FOREX high WR / low PF pattern.

### `ai_leaderboard.html`

1. **Universe** — `swarm_picks.json` ≠ production.  
2. **Stale FTP** (was 2026-05-16) — mitigated: daily CI + local rebuild 2026-06-02.  
3. **Misleading PF** — e.g. claude-opus-4-7 EQUITY cell PF 2.15 vs production PF 0.33.  
4. **No money-ready filter** — banner + live MR strip added 2026-06-02.

---

## 4. DeepSeek (Mercury) plan — what to adopt / reject

**Adopt:** 12-week phasing (resolver weeks 1–2, pipeline 3–4, WF 5–6, shadow 7); HHI &gt; 0.25 alert; resolver dispute &gt; 2%; emit-culling OOS PF ≥ 0.6.

**Reject or defer:** Fictional owner names; “WR ≤ 0.6” success typo (likely PF/WR band); Grafana-first before existing JSON pulse works.

**Copied to:** `reports/EAGLE2_2026-06-02_deepseek_v4.MD` (formatted header).

---

## 5. Implementation status (this session)

| EAGLE2 ID | Status | Artifact |
|-----------|--------|----------|
| A1 Capital lock | **Done** | `quality_gates.py`, `money_ready_verdict.py` |
| A2 Nav matrix MR overlay | **Done** | `build_nav_surface_matrix.py` + regen when `dashboard_data.json` present |
| A3 Admissibility JSON | **Done** | `strategy_admissibility_report.py` + CI |
| A4 pf.html | **Partial** | Unicode strip existed; **research banner added** |
| B1 strategy_admit | **Done** | `tools/strategy_admit.py` |
| C1 emitter census | **Done** | `tools/emitter_census.py` |
| L1 Leaderboard cron | **Done** | daily workflow + honesty banner |
| Monitoring HHI proxy | **Done** | `pick_quality_pulse.py` concentration_alerts |

**Still open:** FTP deploy; `strategy_admit` WF rows when `WALKFORWARD_REPORT.json` committed; pick_funnel HTML “discovery not capital” labels; tournament→production bridge (D1–D4).

---

## 6. Commands (operator)

```bash
python3 tools/strategy_admissibility_report.py --write
python3 tools/emitter_census.py
python3 tools/pick_quality_pulse.py
python3 tools/strategy_admit.py --strategy etf_dual_momentum --asset-class ETF --write
python3 tools/ai_attribution/build_ai_leaderboard.py
curl -fsS -o audit_dashboard/data/dashboard_data.json \
  'https://findtorontoevents.ca/audit/data/dashboard_data.json'
python3 tools/audit_pick_funnel/build_nav_surface_matrix.py
python3 tools/deploy_audit_files.py --only pick_funnel,ai_portfolios
```

---

## 7. Where to read next

| Question | Document |
|----------|----------|
| Why no profit per class? | `EAGLE_2026-06-02_GROK.md` Part A |
| Pipeline code steps | `EAGLE_2026-06-02_GROK.md` Part D / `EAGLE2` §10 |
| Monitoring thresholds | `EAGLE_2026-06-02_GROK.md` Part E / `EAGLE2` §11 |
| Mutation tools | `EAGLE_2026-06-02_GROK.md` Part F / `EAGLE2` §12 |
| PR order | `EAGLE2_2026-06-02_GROK.md` §3, §8 |

**NFA.**