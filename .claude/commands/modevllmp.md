---
description: Show FREE vs PAID mode health for the LiteLLM proxy. Per-group upstream count, healthy/cooled, recent request volume.
---

Report the FREE/PAID mode breakdown of the LiteLLM proxy. Run:

```
python3 tools/vllmp_mode_status.py
```

The script outputs:
- Whether the proxy is up (PID line)
- Per-virtual-model-group table: UPSTREAMS / HEALTHY / COOLED / 60m-reqs / STATUS
- Categories of currently-cooled upstreams (dead_key / quota / etc.)
- Mode-selection guide for the operator

Pass the table verbatim back to the user. If any group shows STATUS=DEGRADED or ALL COOLED, surface that prominently and recommend `/tailvllmp` to inspect why.

The four key groups to highlight:
- `free-mode` — $0 / free-tier pool (target: HEALTHY with >=10 upstreams)
- `free-mode-large` — long-context free fallback
- `paid-mode` — premium frontier (Anthropic / DeepSeek / Moonshot / Hypereal)
- `hybrid-model` — backward-compat alias for free-mode
