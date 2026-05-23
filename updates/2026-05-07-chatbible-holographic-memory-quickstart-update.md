# 2026-05-07 - CHATBIBLE Holographic Memory + Agent Guidance Update

## What changed

Updated `CHATBIBLE.MD` with:

1. A new quick-start section for holographic memory task-sharing.
2. Concrete command flow for task add/claim/start/done across PCs.
3. Memory-topic broadcast examples (`memory.task_claim`, `memory.task_done`).
4. A practical "Suggestions for other agents" checklist:
   - verify actual ws/http ports
   - use runtime identity
   - poll the correct queue (`all` vs direct peer)
   - handle off-network connectivity (VPN/tunnel/firewall)
   - publish handoff breadcrumbs with IDs

## Why

Cross-PC collaboration needs both:

- low-latency protocol messaging, and
- durable ownership/state memory.

This update makes the main quick-start explicit for both.
