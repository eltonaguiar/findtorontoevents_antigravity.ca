# SPEC.md — AI Agent Swarm Orchestrator

## 1. Overview

A local/hybrid CLI orchestrator that enables Claude Code (or a custom coordinator) to dispatch tasks to multiple AI coding tools — KiloCode, OpenCode, Gemini CLI, Claude Code, and direct API endpoints (Ollama, DeepSeek, xAI, etc.) — in parallel "swarm" formations or one-shot interactive sessions.

**Name:** `ai-swarm`  
**Language:** Python 3.10+  
**Package:** Installable via `pip install -e .` or `uv pip install -e .`

---

## 2. Architecture

```
ai-swarm/
├── cli.py              # Main entry point (Click or argparse)
├── config.py           # Config loader, validation, env resolution
├── orchestrator.py     # Core dispatch and coordination logic
├── swarm_engine.py     # Parallel worker dispatch, result aggregation
├── session_manager.py  # Interactive/follow-up session persistence
├── safety.py           # Read-only enforcement, evidence contracts
├── adapters/           # One module per tool
│   ├── __init__.py
│   ├── base.py         # Abstract adapter interface
│   ├── kilocode.py
│   ├── opencode.py
│   ├── gemini.py
│   ├── claude_code.py
│   ├── openai_api.py   # Generic OpenAI-compatible (Ollama, LM Studio, vLLM, DeepSeek, xAI, etc.)
│   └── copilot.py      # GitHub Copilot CLI (optional, gated)
├── models/             # Pydantic data models
│   ├── __init__.py
│   ├── config.py
│   ├── task.py
│   └── result.py
├── prompts/            # Default swarm prompt templates
│   ├── pr_review.md
│   ├── code_audit.md
│   └── red_team.md
├── examples/           # Example swarm configurations
│   ├── pr_review_swarm.yaml
│   └── multi_model_qa.yaml
└── tests/
```

---

## 3. Core Interfaces

### 3.1 Adapter Interface (`adapters/base.py`)

Every tool adapter implements:

```python
class BaseAdapter(ABC):
    name: str                    # Unique identifier, e.g. "kilocode"
    supports_parallel: bool      # Can run multiple instances concurrently
    supports_interactive: bool   # Supports follow-up sessions
    supports_json_output: bool   # Has structured output mode
    
    def __init__(self, config: ToolConfig):
        self.config = config
    
    @abstractmethod
    async def run_once(self, prompt: str, ctx: RunContext) -> WorkerResult:
        """Execute a single prompt, return structured result."""
        pass
    
    @abstractmethod
    async def start_session(self, prompt: str, ctx: RunContext) -> SessionHandle:
        """Start an interactive session, return handle for follow-ups."""
        pass
    
    @abstractmethod
    async def follow_up(self, handle: SessionHandle, prompt: str) -> WorkerResult:
        """Send follow-up in an existing session."""
        pass
    
    @abstractmethod
    def validate_config(self) -> list[str]:
        """Return list of validation errors; empty if valid."""
        pass
```

### 3.2 Data Models (`models/`)

```python
# models/config.py
class ToolConfig(BaseModel):
    name: str                       # Human-readable name
    adapter: str                    # Adapter class to use
    command: str | None             # CLI command path (if applicable)
    env_prefix: str | None          # Environment variable prefix for isolation
    api_key: str | None             # API key (or {ENV_VAR} reference)
    base_url: str | None            # For API-based adapters
    model: str | None               # Default model for this tool
    extra_args: list[str] = []      # Additional CLI flags
    allowed_tools: list[str] | None = None   # Tool allowlist (safety)
    disallowed_tools: list[str] | None = None # Tool denylist (safety)
    timeout: int = 300              # Seconds
    max_turns: int | None = None
    headless: bool = True          # Prefer headless/non-interactive
    json_output: bool = True       # Request structured output
    read_only: bool = False        # If true, deny all write operations

class SwarmConfig(BaseModel):
    version: str = "1.0"
    orchestrator: str = "claude"   # Which tool acts as default orchestrator
    tools: dict[str, ToolConfig]   # Key = tool alias, e.g. "kilo", "gemini"
    default_safety: SafetyConfig
    env_file: str | None = None    # Path to .env file for API keys

class SafetyConfig(BaseModel):
    require_evidence: bool = True          # Every claim must cite evidence
    read_only_default: bool = False        # Default workers to read-only
    isolate_env: bool = True              # Per-worker env isolation
    allow_git_write: bool = False          # Workers can push/merge/comment?
    max_workers: int = 10
    red_team_enabled: bool = True          # Run red-team verification pass
```

```python
# models/task.py
class RunContext(BaseModel):
    tool_alias: str
    session_id: str | None = None
    working_dir: str | None = None
    files: list[str] = []          # Files to attach
    json_schema: dict | None = None # Structured output schema
    timeout: int = 300
    max_turns: int | None = None

class SwarmTask(BaseModel):
    id: str                        # Unique task ID
    prompt: str
    worker_assignments: list[str]  # Tool aliases to dispatch to
    mode: Literal["parallel", "sequential", "voting"] = "parallel"
    aggregation_prompt: str | None = None  # Prompt for merge-captain
    red_team_prompt: str | None = None   # Prompt for red-team verification
    require_consensus: bool = False
    min_confidence: str = "MEDIUM"  # LOW, MEDIUM, HIGH
```

```python
# models/result.py
class WorkerResult(BaseModel):
    task_id: str
    tool_alias: str
    status: Literal["success", "error", "timeout", "fabrication_risk"]
    raw_output: str
    structured_output: dict | None = None
    evidence: list[EvidenceItem] = []
    cost_usd: float | None = None
    tokens: TokenUsage | None = None
    duration_ms: int
    session_id: str | None = None  # For follow-up
    error_message: str | None = None

class EvidenceItem(BaseModel):
    claim: str
    source: str           # "diff", "file", "test", "dashboard", "command"
    reference: str        # file:line, command output, PR number, etc.
    verified: bool = False

class SwarmResult(BaseModel):
    task: SwarmTask
    worker_results: list[WorkerResult]
    aggregated_result: WorkerResult | None = None
    red_team_result: WorkerResult | None = None
    final_verdict: str | None = None
    confidence: str = "LOW"
```

---

## 4. Execution Modes

### 4.1 One-Shot Mode
```bash
ai-swarm run --tool kilo --prompt "Review this PR for security issues"
```
- Single prompt, single tool, immediate result to stdout.
- Supports `--json` for machine-readable output.
- Supports `--file` to attach context files.

### 4.2 Parallel Swarm Mode
```bash
ai-swarm swarm --config pr_review_swarm.yaml --task "Review PR #669"
```
- Reads SwarmTask definition from config or CLI args.
- Dispatches to N workers in parallel (asyncio.gather).
- Collects results.
- Runs optional aggregation agent (merge-captain).
- Runs optional red-team verifier.
- Outputs unified JSON or Markdown report.

### 4.3 Interactive / Follow-Up Mode
```bash
ai-swarm session start --tool gemini --prompt "Explain this codebase"
# Returns session ID

ai-swarm session follow-up --id <session-id> --prompt "Now refactor the auth module"

ai-swarm session list
ai-swarm session show <session-id>
```
- Adapters with `supports_interactive=True` implement session persistence.
- For CLI tools: use their native session features (`kilo run -c`, `opencode run --continue`, Claude Code sessions).
- For API tools: maintain conversation history locally.
- Sessions stored in SQLite at `~/.ai-swarm/sessions.db`.

---

## 5. Adapter Specifications

### 5.1 KiloCode Adapter
```python
async def run_once(self, prompt, ctx):
    cmd = [
        "kilo", "run", "--auto", "--format", "json",
        "-m", self.config.model or "anthropic/claude-sonnet-4",
        *self.config.extra_args,
        prompt
    ]
    # Spawn subprocess, capture JSONL, parse final result
    # Handle timeout via asyncio.wait_for
    # Parse kilo JSONL into WorkerResult
```

### 5.2 OpenCode Adapter
```python
async def run_once(self, prompt, ctx):
    cmd = [
        "opencode", "run", "--format", "json",
        "--model", self.config.model or "anthropic/claude-sonnet-4",
        *self.config.extra_args,
        prompt
    ]
    # JSONL parsing similar to KiloCode
```

### 5.3 Gemini CLI Adapter
```python
async def run_once(self, prompt, ctx):
    cmd = [
        "gemini", "-p", prompt,
        "--output-format", "json",
        "-m", self.config.model or "gemini-2.5-pro",
        *self.config.extra_args
    ]
    # Single JSON output (not JSONL)
    # Must set GEMINI_TRUST_WORKSPACE=true in env
    # Must enforce version >= 0.39.1 for security
```

### 5.4 Claude Code Adapter
```python
async def run_once(self, prompt, ctx):
    cmd = [
        "claude", "--print", "--output-format=json",
        "--model", self.config.model or "sonnet",
        *self.build_tool_flags(),  # --allowedTools, --disallowedTools
        *self.config.extra_args,
        prompt
    ]
    # JSON output parsing
```

### 5.5 OpenAI-Compatible API Adapter (Ollama, LM Studio, vLLM, DeepSeek, xAI, etc.)
```python
async def run_once(self, prompt, ctx):
    # Uses openai.AsyncClient with custom base_url and api_key
    # Supports tool calling via OpenAI SDK
    # No subprocess needed — direct HTTP
    client = AsyncOpenAI(base_url=self.config.base_url, api_key=self.resolve_api_key())
    response = await client.chat.completions.create(
        model=self.config.model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"} if ctx.json_schema else None,
        timeout=ctx.timeout,
    )
    # Parse into WorkerResult
```

---

## 6. Safety & Security Model

### 6.1 Environment Isolation
```python
# safety.py
async def run_isolated(cmd: list[str], env_vars: dict, timeout: int) -> subprocess.Result:
    """Run command with isolated environment, only whitelisted env vars passed."""
    env = {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", "")}
    env.update(env_vars)
    # Never pass full parent env to prevent key leakage
    return await asyncio.create_subprocess_exec(*cmd, env=env, ...)
```

### 6.2 Read-Only Enforcement
- Adapters check `config.read_only`.
- For CLI tools: append `--disallowedTools Edit,Bash(rm:*)`, etc.
- For API tools: inject system prompt: "You are read-only. Do not modify files."
- Safety layer verifies no edits occurred post-run (git status check).

### 6.3 Evidence Contract
- Post-processing parser extracts claims from structured output.
- Requires `evidence` array in structured JSON.
- Red-team agent tries to disprove every claim.
- Unverified claims downgraded to "speculation".

### 6.4 GitHub Token Segregation
- Read-only token for reviewers: `GITHUB_TOKEN_READONLY`
- Write token only for comment-poster: `GITHUB_TOKEN_WRITE`
- Never both in same worker environment.

---

## 7. Swarm Patterns

### 7.1 PR Review Swarm (Primary Use Case)
```yaml
# examples/pr_review_swarm.yaml
swarm:
  name: "pr-review"
  task_template: "prompts/pr_review.md"
  workers:
    - tool: claude
      agent: pr-reviewer
      model: sonnet
      read_only: true
    - tool: gemini
      agent: pr-reviewer
      model: gemini-2.5-pro
      read_only: true
    - tool: opencode
      agent: pr-reviewer
      model: anthropic/claude-haiku-4
      read_only: true
  aggregation:
    tool: claude
    model: opus
    prompt: "prompts/merge_reviews.md"
  red_team:
    enabled: true
    tool: claude
    model: sonnet
    prompt: "prompts/red_team.md"
```

### 7.2 Multi-Model QA (Voting Pattern)
```yaml
swarm:
  name: "voting-qa"
  mode: voting
  workers:
    - tool: claude
    - tool: gemini
    - tool: deepseek  # via openai_api adapter
    - tool: kilo
  consensus_threshold: 0.75
```

### 7.3 Sequential Pipeline
```yaml
swarm:
  name: "code-pipeline"
  mode: sequential
  stages:
    - name: architect
      tool: claude
      model: opus
    - name: implement
      tool: kilo
      depends_on: [architect]
    - name: review
      tool: gemini
      read_only: true
      depends_on: [implement]
    - name: test
      tool: opencode
      depends_on: [implement]
```

---

## 8. Configuration Schema

```yaml
# ~/.ai-swarm/config.yaml
version: "1.0"

# Global orchestrator settings
orchestrator:
  default_tool: claude
  max_parallel_workers: 8
  default_timeout: 300

# Tool definitions
tools:
  claude:
    adapter: claude_code
    command: claude
    model: sonnet
    env_prefix: ANTHROPIC
    api_key: "${ANTHROPIC_API_KEY}"
    extra_args: ["--max-turns", "12"]
    allowed_tools: ["Read", "Grep", "Glob", "Bash(gh pr view:*)", "Bash(gh pr diff:*)"]
    read_only: false

  kilo:
    adapter: kilocode
    command: kilo
    model: anthropic/claude-sonnet-4
    env_prefix: KILO
    api_key: "${ANTHROPIC_API_KEY}"
    extra_args: ["--auto"]

  opencode:
    adapter: opencode
    command: opencode
    model: anthropic/claude-sonnet-4
    env_prefix: OPENCODE
    api_key: "${ANTHROPIC_API_KEY}"
    extra_args: ["--format", "json"]

  gemini:
    adapter: gemini
    command: gemini
    model: gemini-2.5-pro
    env_prefix: GEMINI
    api_key: "${GEMINI_API_KEY}"
    extra_args: ["--approval-mode", "auto_edit"]

  ollama:
    adapter: openai_api
    base_url: http://localhost:11434/v1
    model: llama3.1:8b
    api_key: "ollama"  # dummy

  deepseek:
    adapter: openai_api
    base_url: https://api.deepseek.com/v1
    model: deepseek-chat
    api_key: "${DEEPSEEK_API}"

  xai:
    adapter: openai_api
    base_url: https://api.x.ai/v1
    model: grok-2
    api_key: "${X_AI_KEY}"

  inception:
    adapter: openai_api
    base_url: https://api.inception.ai/v1
    model: inception-latest
    api_key: "${INCEPTION_AI_KEY}"

# Safety defaults
safety:
  require_evidence: true
  read_only_default: true
  isolate_env: true
  allow_git_write: false
  max_workers: 10
  red_team_enabled: true
```

---

## 9. CLI Commands

```bash
# Global options
ai-swarm --config ~/.ai-swarm/config.yaml --verbose

# One-shot execution
ai-swarm run --tool <alias> --prompt "..." [--file FILE] [--json] [--read-only]

# Swarm execution
ai-swarm swarm --config <swarm.yaml> [--task "..."] [--output json|md]

# Session management
ai-swarm session start --tool <alias> --prompt "..."
ai-swarm session follow-up --id <sid> --prompt "..."
ai-swarm session list
ai-swarm session show <sid>
ai-swarm session export <sid> > session.json

# Tool inspection
ai-swarm tools list
ai-swarm tools test <alias>          # Test connectivity / one echo prompt
ai-swarm tools validate              # Validate all tool configs

# Safety / audit
ai-swarm safety check --tool <alias>  # Verify read-only constraints
ai-swarm safety evidence --result <file>  # Validate evidence contract

# Init config
ai-swarm init                        # Interactive config setup
```

---

## 10. Testing Strategy

- **Unit tests:** Adapter mocking with `pytest-asyncio`
- **Integration tests:** Spin up Ollama locally, run real one-shot prompt
- **Safety tests:** Verify read-only workers cannot write files (temp dir test)
- **Config validation tests:** Schema compliance
- **End-to-end:** PR-review swarm against a real GitHub repo (read-only)

---

## 11. Dependencies

```txt
pydantic>=2.0
pyyaml>=6.0
click>=8.0
httpx>=0.27
openai>=1.30
python-dotenv>=1.0
pytest>=8.0
pytest-asyncio>=0.23
rich>=13.0        # Terminal formatting
aiofiles>=23.0    # Async file operations
```

---

## 12. Non-Goals (Out of Scope)

- Web UI / dashboard (this is a CLI-first tool)
- True distributed swarm across network nodes (local-only)
- Built-in model training or fine-tuning
- Commercial deployment or SaaS hosting

## 13. Future Extensions

- MCP (Model Context Protocol) server mode for `ai-swarm`
- Docker sandbox wrapper for each worker
- Plugin system for custom adapters
- TUI monitoring dashboard (optional, `ai-swarm monitor`)
