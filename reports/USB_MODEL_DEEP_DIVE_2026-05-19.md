# USB drive (H:) model deep dive — money-ready per asset class

**Date:** 2026-05-19  
**USB path:** `H:\ollama\models` (~203 GB blobs, 29 tagged models)  
**Prompt:** `docs/swarm_prompts/CODEBASE_NARROW_v1.md` (same as local/cloud rounds)  
**Benchmark tool:** `tools/usb_ollama_benchmark.py`  
**Run outputs:** `swarm_runs/usb-model-grill/20260519T211201Z/`

---

## Inventory summary

| Metric | USB (H:) | Local (`%USERPROFILE%\.ollama`) |
|--------|----------|----------------------------------|
| Blob files | 119 (~203 GB) | 118 (~186 GB) |
| Shared SHA256 weights | **59** (~81 GB on USB) | same hashes |
| USB-only model tags (by name) | **18** | — |
| Name collision (both libraries) | **11** | e.g. `qwen3:14b`, `deepseek-r1:14b` |

**Other drives:** `F:\Models\Ollama_GGUFs` has 18 `.gguf` symlinks (already imported to local Ollama). `G:\` / `J:\` — no additional GGUF trees found in quick scan.

**USB-only tags not yet benchmarked** (candidates for next pass):

`qwen2.5:32b`, `qwen2.5:7b`, `qwen2.5:0.5b`, `qwen2.5:1.5b`, `qwen2.5-coder:14b`, `mixtral:8x7b`, `llama3.1:8b`, `gemma:latest`

**Skip (size/cloud):** `gpt-oss:120b-cloud`, `artiku348/loker.v2.1-cld-cdr-480b` (480B-class custom manifest on USB)

---

## Benchmark results (13 runs)

| Model | Type | OK | Time | Intel | Notes |
|-------|------|-----|------|-------|-------|
| **gemma3:12b** | USB-only | Y | 20s | **4** | **Best new USB find** — strong per-class narrowing |
| **mistral-small:24b** | USB-only | Y | 116s | **4** | Best 24B on USB; hybrid OK |
| **qwen2.5-coder:32b** | USB-only | Y | 232s | **4** | Aligns with H-035 intraday / walk-forward |
| **gemma3:1b** | USB-only | Y | 16s | **4** | Fast smoke only |
| mistral-nemo:12b | USB-only | Y | 18s | 3 | Different blob than local `mistral-nemo:latest` (12B vs Nemo) |
| qwen2.5:14b | USB-only | Y | 21s | 3 | Extra Qwen2.5 family member |
| phi4:14b | USB-only | Y | 21s | 3 | Microsoft stack variety |
| deepseek-r1:8b | USB-only | Y | 8s | 3 | Fast reasoning screen |
| mistral:7b | USB-only | Y | 6s | 3 | Quick breadth |
| deepseek-r1:14b | **duplicate** | Y | 25s | 3 | Same blob SHA as local — USB path OK |
| gemma3:4b | **duplicate** | Y | 9s | 3 | Same blob as local |
| qwen3.5:27b | USB-only | N | 250s | 0 | Empty/short output @ 16GB — batch only |
| qwen3:14b | **duplicate** | N | 21s | 0 | USB re-bench failed — **use local `qwen3:14b`** |

**11/13 OK** — duplicates are **same weights** as C: drive; no quality gain from reading H: for `qwen3:14b` if local path works.

---

## Duplicate vs USB-only — what to do

### Duplicates (same blob SHA on H: and C:)

Re-benchmarking from `H:\ollama\models\blobs\...` does **not** change model behavior — only I/O path. Use local Ollama tags for speed (`qwen3:14b`, `deepseek-r1:14b`, `gemma3:4b`).

**Exception:** keep weights on USB to save C: disk; import via Modelfile `FROM H:/ollama/models/blobs/sha256-...` (see `tools/usb_ollama_benchmark.py`).

### USB-only models worth pulling to local SSD

| Priority | Tag | Size | Why |
|----------|-----|------|-----|
| **P0** | `gemma3:12b` | ~7.6 GB | Best intel=4 USB-only; fits 12GB VRAM |
| **P1** | `mistral-small:24b` | ~13.4 GB | Strong methodology output; ~2 min/prompt |
| **P1** | `qwen2.5:14b` | ~8.4 GB | Extra generalist between 7B and coder |
| **P2** | `phi4:14b` | ~8.4 GB | Diversity for second-opinion screens |
| **P2** | `mistral-nemo:12b` | ~6.6 GB | Not identical to local Nemo tag — compare before merge |
| Overnight | `qwen3.5:27b` | ~16.2 GB | Failed interactive — retry `num_ctx=2048`, `num_predict≥900` |

```powershell
# Example: register gemma3:12b from USB without copying blob
python tools/usb_ollama_benchmark.py  # creates usb-* tags; or:
# ollama create gemma3-12b-usb -f swarm_runs/ollama-modelfiles/Modelfile-usb-gemma3-12b
```

---

## Key insights per asset class (merged: USB + cloud + local)

*Posture unchanged:* **11/11 daily-bar killed · paper-only · emitter whitelist shadow mode.*

### CRYPTO

| Insight | Source | Action |
|---------|--------|--------|
| Only funded new family = **tick/intraday** (H-035, Binance aggTrade) | Qwen2.5-coder-32b USB, DeepSeek cloud, Ring | Pre-register + fetcher |
| Stop `quan_engine`, on-chain counts, funding arb | All rounds | `EMITTER_WHITELIST_ENFORCE` |
| Stop tick tables until H-035 gated | Qwen2.5-coder-32b | Don’t emit tick picks before harness |
| Real GHA: `mercury2-scan.yml`, `crypto-ml-edge.yml`, `audit-dashboard.yml` | Verified repo | Don’t invent `crypto_picks.yml` |

### EQUITY

| Insight | Action |
|---------|--------|
| No new daily scanners until n≥100 forward clean | Freeze M-107 daily families |
| DNA mutation on **horizon/universe** only (H-032, E1) after pre-reg | `tools/mutation_analysis.py` |
| Real GHA: `growth-stock-screener-daily.yml`, `momentum-tracker.yml`, equity blocks in `audit-dashboard.yml` | |
| Gemma3:12b USB suggested momentum scanners — **reject** without harness | |

### COMMODITY

| Insight | Action |
|---------|--------|
| Block `cta_replicator`; keep cot/copytrader whitelist slices | T2-02 |
| Seasonality / term-structure mutation (not raw CTA) | Qwen cloud r3 |
| `incubator-strategies.yml` + audit-dashboard commodity env | |

### ETF

| Insight | Action |
|---------|--------|
| Ring/cloud: **ETF relative-value** highest P(T2) among classes — still paper | Harness + `etf-bond-scanner.yml` |
| Stop until n≥100 | No live promotion |

### FOREX

| Insight | Action |
|---------|--------|
| `cta_replicator` slice only; block copytrader | Whitelist |
| Mutation-before-kill per `MUTATION_THREE_AXIS_PROTOCOL.md` | Deep-dive gate |
| Shadow rescue env in `audit-dashboard.yml` (not new YAML) | |

### BOND

| Insight | Action |
|---------|--------|
| Paper via `etf-bond-scanner.yml` only | n too small for Tier-2 |
| Stop yield-curve PEAD variants | Killed families |

### Cross-cutting (strategy / backtest / mutation / APIs)

| Question | Answer |
|----------|--------|
| New strategies? | **No** daily-bar; **one** CRYPTO intraday probe |
| More backtesting? | **Yes** — `ejaguiar1_backtests`, genome/incubator |
| Better backtesting? | **Yes** — walk-forward, costs, FDR, dedup |
| DNA mutation? | **After** toxic pairs blocked; per-class axes |
| More free APIs? | **Binance aggTrade only** (CRYPTO); not API sprawl |

---

## Repo-grounded P0 ideas (synthesized)

| ID | wire_target | 60d acceptance |
|----|-------------|----------------|
| `EMITTER_WHITELIST_ENFORCE` | `alpha_engine/emitter_whitelist.py` | 0 emissions from toxic pairs |
| `H035_BINANCE_INTRADAY` | new `tools/binance_aggtrade_fetcher.py` + `hypothesis_registry.json` | Harness pre-reg + n≥30 paper |
| `USB_GEMMA3_12B_SCREEN` | local tag from H: blob | 2nd-opinion harvest @ &lt;25s/prompt |
| `HARNESS_FDR_GATE` | `tools/fdr_control.py` + `edge_stability_harness.py` | FDR≤0.10 before “proven” |
| `AUDIT_CANONICAL_PF` | `audit_trail/dashboard_generator.py` | Tiles within 0.15 of `pf_registry` |

---

## Recommended local stack after USB pass

| Role | Model | Location |
|------|--------|----------|
| Fast screen | `mistral:7b` (USB) or `mistral-nemo` (local) | |
| **New: best USB import** | **`gemma3:12b`** | H: blob → `ollama create` |
| Deep 24B | `mistral-small:24b` | USB hybrid ~116s |
| Code-aware 32B | `qwen2.5-coder:32b` | USB or local (same family) |
| Verdict | DeepSeek / Grok cloud | `reports/CLOUD_FIVE_ROUNDS_2026-05-19.md` |
| Avoid | `qwen3.5:27b` USB interactive, `qwen3:8b` | empty generations |

---

## Commands

```powershell
cd e:\findtorontoevents_antigravity.ca
python tools/usb_ollama_inventory.py
python tools/usb_ollama_benchmark.py
python tools/model_grill_sequential.py --wave local_variety --prompt narrow
```

## Related reports

- `reports/LOCAL_LLM_ROUND2_CODEBASE_NARROW_2026-05-19.md`
- `reports/CLOUD_FIVE_ROUNDS_2026-05-19.md`
- `reports/HARVEST_CONSTRUCTIVE_MONEY_READY_2026-05-19.md`
- `reports/MERGED_ACTION_PLAN_2026-05-19.md`
- `reports/usb_ollama_inventory.json`
