# Anonymous AI Council — Source Benchmark Report
**Date:** 2026-05-19  
**Run by:** GitHub Copilot (proof of concept) + Claude Code (continuation)  
**Scripts:** `tools/anon_ai_council/probe_source_manifest.py`, `tools/anon_ai_council/deep_probe_from_manifest.py`  
**Artifacts:** `swarm_runs/deep_probe_full102_non_tor_2026-05-19.json`, `swarm_runs/ai_council_v2_20260519T*/`

---

## Source Coverage

| Metric | Value |
|--------|-------|
| Total sources tested | 102 |
| Successful (returned usable content) | 6 (5.9%) |
| Login-gated / auth-wall | 46 (45.1%) |
| Timeout / selector missing | 37 (36.3%) |
| No reliable answer extracted | 10 (9.8%) |
| Other failures | 3 (2.9%) |

---

## Working Sources (Anonymous / Guest Mode)

| Source | URL | Elapsed | Counsel Quality | Notes |
|--------|-----|---------|-----------------|-------|
| eye2.ai | https://eye2.ai | 9.85s | **HIGH** — returned actual Python prediction code | Only source with production-usable content |
| chatgot.io | https://chatgot.io | 10.21s | MEDIUM — code snippet (truncated, some typos) | Class-based pipeline structure, usable as template |
| Pollinations.ai | https://text.pollinations.ai | ~10s | HIGH — clean strategy ideas (Jegadeesh-Titman momentum, carry trade) | Free API endpoint, no browser needed |
| Perplexity.ai | https://www.perplexity.ai | variable | HIGH — cross-sectional momentum + carry trade with citations | Requires non-Tor direct connection |
| andisearch.com | https://www.andisearch.com | 10.25s | LOW — search-style response, no direct strategy | Links to Reddit algotrading threads |
| notegpt.io/ai-chat | https://notegpt.io/ai-chat | 10.35s | LOW — marketing landing page content | Technically "success" but no direct answer |
| blackbox.ai | https://blackbox.ai | 10.22s | LOW — product marketing page | Not a direct AI chat response |
| api.venice.ai | https://api.venice.ai | 10.41s | INFRA — API docs page (OpenAI-compatible endpoint) | Use as API provider, not as web chat |

---

## IP Anonymity Status

| Mode | Outbound IP | Status |
|------|-------------|--------|
| Direct (no proxy) | 142.198.176.179 | Exposed — real residential/commercial IP |
| Tor (socks5h://127.0.0.1:9050) | N/A | ERR_NO_SUPPORTED_PROXIES / ERR_PROXY_CONNECTION_FAILED — Tor not running or blocked by Playwright |

**Conclusion:** No anonymity in the current setup. Tor is either not running or Playwright cannot route through it. Sources that return content do so against the real IP, which means rate limits / fingerprinting are in effect.

---

## Actionable Sources for /consult-webscrape

**Tier 1 — Real AI counsel, anonymous, no login:**
1. **Pollinations.ai** — `GET https://text.pollinations.ai/<url-encoded-prompt>` — returns real LLM text, free, no key
2. **eye2.ai** — Playwright, ~10s, returns Python code + strategy text
3. **Perplexity.ai** — Playwright, works direct, login wall appears intermittently

**Tier 2 — Partial (login inconsistent):**
4. **chatgot.io** — echoes prompt + truncated code, useful for code templates

**Skip (not usable for counsel):**
- blackbox.ai, notegpt.io, andisearch.com — marketing/search pages
- api.venice.ai — use as API provider (OpenAI-compatible), not web chat

---

## Failure Mode Summary

| Failure | Root Cause | Fix Path |
|---------|------------|----------|
| Tor proxy failures | Playwright WebKit/Chromium cannot route through SOCKS5h | Use `--proxy` with `requests` (not Playwright) for HTTP API sources; Playwright needs `--proxy-server` in launch args |
| Login walls (46 sources) | These sites detect headless browsers and force OAuth | No fix without accounts; skip these sources |
| Timeouts (37 sources) | Sites load JS-heavy pages that never expose an input | Increase timeout or add custom selectors per source |
| No reliable answer (10) | Page returned content but no AI response was extractable | Improve selector heuristics in `deep_probe_from_manifest.py` |

---

## Benchmark vs. Prior Copilot Run

Copilot's first probe (40 sources): 6/40 success = 15%  
Full probe (102 sources): 6/102 success = 5.9%  
→ The 6 working sources are stable; additional sources mostly fail due to login walls.
