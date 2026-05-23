# Strategy harvest execute — local follow-up (v1)

You are a **senior quant implementer**. Cloud debate already ran; you execute against the repo.

## Inputs

### Top-10 per class (registry truth)

{{TOP10_STRATEGIES_MD}}

### Debate synthesis (if provided)

{{DEBATE_SYNTHESIS}}

---

## Deliverables

### 1) Per-class action table

| Class | Strategy to SIZE UP | Strategy to CAP/KILL | hypothesis_id | wire_target file:function | 7-day command |
|-------|----------------------|----------------------|---------------|---------------------------|---------------|

### 2) Three P0 PRs (smallest diff)

Each row: title, files (max 3), acceptance test, which class it rescues.

### 3) Meta-prompt calibration

Given local model limits, which of the 5 meta-prompts from debate should run on **Ollama 14B** vs **cloud Ring/DeepSeek** only?

### 4) Honest freeze list

Classes to **stop new emissions** for 90 days vs continue paper harvest.

**Use only paths that exist** under `alpha_engine/`, `audit_trail/`, `tools/`, `.github/workflows/audit-dashboard.yml`.
