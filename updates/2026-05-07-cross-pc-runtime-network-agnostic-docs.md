# 2026-05-07 - Cross-PC Protocol Docs Updated For Runtime/Network Agnosticism

## What was improved

Updated protocol prompt/documentation so operators can run the same workflow regardless of:

- Claude/Cursor vs Hermes runtime
- Windows PowerShell vs cmd.exe vs WSL/bash
- same LAN vs different-network deployments

## Files updated

- `.claude/skills/cross-pc-protocol-debug-first/SKILL.md`
- `docs/cross_pc_protocol_runbook.md`
- `docs/cross_pc_protocol_v1.md`

## Key additions

1. Runtime-agnostic operator prompt template for consistent execution and reporting.
2. Shell-specific command matrix with correct payload quoting for:
   - PowerShell
   - cmd.exe
   - WSL/bash
3. Multi-network topology guidance:
   - LAN direct connection
   - VPN/Tailscale
   - SSH tunnel fallback
   - explicit endpoint mode when discovery is unavailable
4. Troubleshooting additions for cross-network and WSL/Windows boundary issues.
5. Explicit WS-first then HTTP-fallback endpoint selection rules in spec.

## Verification

- Documentation-only update; no code behavior changed.
- Existing protocol test suite remains green from prior run:
  - `python -m pytest tests/test_cross_pc_protocol.py -q` (4 passed)
