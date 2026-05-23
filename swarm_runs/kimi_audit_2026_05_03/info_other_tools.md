# AI CLI Tools Research: Local Agent Swarm Candidates

> **Research date:** 2026-05-03  
> **Scope:** Verify existence, official sources, installation, headless mode, JSON output, programmatic invocation, and security concerns for 5 AI CLI tools.  
> **Methodology:** Web search, official docs, GitHub repos, npm registry verification. All claims flagged as verified or unverified.

---

## 1. Freebuff / FreeBuff CLI

### Verification Status: VERIFIED — Real tool, but limited transparency

| Attribute | Finding |
|---|---|
| **Official repo** | [github.com/CodebuffAI/codebuff](https://github.com/CodebuffAI/codebuff) (monorepo; `freebuff/` subdir) |
| **npm package** | [`freebuff`](https://www.npmjs.com/package/freebuff) — v0.0.56, MIT license, ~3,575 weekly downloads |
| **Install command** | `npm install -g freebuff` |
| **Publisher** | CodebuffAI (jahooma, brandonatcodebuff, charleslien) |
| **Website** | [codebuff.com](https://codebuff.com) |

### Capabilities
- Terminal-based AI coding agent (natural language → code edits).
- Built-in web research and browser use.
- Connects to a **cloud backend** with "models optimized for fast, high-quality assistance."
- File mentions (`@filename`), agent mentions (`@AgentName`), bash mode (`!command`), chat history (`/history`), knowledge files (`knowledge.md`).

### Headless Mode
- **NO documented headless / non-interactive mode.**
- **NO documented JSON output mode.**
- Tool appears designed exclusively for interactive terminal use.

### Programmatic Invocation
- **Not supported.** No CLI flags for single-shot execution or structured output.

### Security / Transparency Concerns
- **Ad-supported free tier:** CLI displays ads to support free usage. This may inject unexpected content into the terminal.
- **Closed-source backend:** Connects to a proprietary cloud backend. Exact model providers, data handling, and request routing are opaque.
- **Privacy claim:** FAQ states "No. We only use model providers that do not train on our requests. Your code stays yours." — this is an **unverified claim** (no third-party audit cited).
- **Monorepo context:** Freebuff is a thin CLI wrapper around the larger Codebuff platform. The backend API is not open source.

### Swarm Suitability
- **Poor.** Lacks headless mode, JSON output, and local endpoint support. Cloud dependency and ad model make it unsuitable for autonomous agent swarms.

---

## 2. OpenClaude by Gitlawb

### Verification Status: VERIFIED — Third-party open-source fork

| Attribute | Finding |
|---|---|
| **GitHub repo** | [github.com/Gitlawb/openclaude](https://github.com/Gitlawb/openclaude) |
| **npm package** | `@gitlawb/openclaude` |
| **Install command** | `npm install -g @gitlawb/openclaude` |
| **Stars / Forks** | ~25.6k stars, ~8.3k forks (as of 2026-05-03) |
| **License** | Other (not standard OSI; see repo LICENSE file) |
| **Website** | [openclaude.gitlawb.com](https://openclaude.gitlawb.com) |

### Origin & Trust Context
- **Third-party / community fork.** Descended from a clean-room rewrite ("Claw Code") after Anthropic allegedly leaked Claude Code source via npm source maps in March 2026.
- Expanded to support **200+ models** via OpenAI-compatible APIs, Gemini, GitHub Models, Codex OAuth, Ollama, Atomic Chat, and others.
- **Treat as untrusted third-party until independently audited.** Large star count does not equate to security audit or official endorsement.

### Capabilities
- Terminal-first coding agent with bash, file read/write/edit, grep, glob, agents, tasks, MCP, slash commands.
- Streaming responses and multi-step tool loops.
- Image inputs (URL/base64) for vision-capable models.
- Web search (DuckDuckGo default; Firecrawl configurable).
- Provider profiles saved in `.openclaude-profile.json`.
- **Agent routing:** Different agent roles can be mapped to different backends/models via `~/.claude/settings.json` `agentModels` + `agentRouting`.

### Headless Mode
- **YES — gRPC server mode.**
  ```bash
  npm run dev:grpc        # Start headless gRPC server on localhost:50051
  npm run dev:grpc:cli    # Test CLI client that talks to gRPC server
  ```
- Environment variables: `GRPC_PORT` (default 50051), `GRPC_HOST` (default `localhost`).
- Bidirectional streaming over gRPC: text chunks, tool calls, and permission requests (`action_required` events).
- **Proto file:** `src/proto/openclaude.proto` — can generate clients in Python, Go, Rust, etc.

### JSON Output
- **Via gRPC:** Native structured messages over the wire.
- **No standalone `--output-format json` CLI flag** documented for the main interactive CLI (unlike Claude Code proper).

### Programmatic Invocation
- **gRPC server integration** into CI/CD pipelines, custom UIs, or external applications.
- VS Code extension included in repo for editor integration.
- Supports agent swarms: "Spawn sub-agents to parallelize tasks in isolated contexts" (per Android fork docs).

### Local Model Support
| Backend | Configuration |
|---|---|
| **Ollama** | `export CLAUDE_CODE_USE_OPENAI=1; export OPENAI_BASE_URL=http://localhost:11434/v1; export OPENAI_MODEL=qwen2.5-coder:7b` or `ollama launch openclaude --model <name>` |
| **LM Studio** | `OPENAI_BASE_URL=http://localhost:1234/v1` |
| **OpenRouter / DeepSeek / Groq / etc.** | Set `OPENAI_BASE_URL` to provider's `/v1` endpoint |
| **Atomic Chat** | Local provider; auto-detects loaded models |

### Security Concerns
- **API key storage:** Provider credentials stored in plaintext in profile/settings files. This is a **documented limitation**.
- **Third-party code:** No known independent security audit. Origin story involves leaked source code — supply chain risk should be considered.
- **Auto-updates:** Not mentioned; but typical npm global packages can update silently.
- **Non-Anthropic provider quality:** "Tool quality depends heavily on the selected model. Smaller local models can struggle with long multi-step tool flows."

### Swarm Suitability
- **Good.** gRPC headless mode, multi-provider support, local endpoint compatibility, and explicit subagent/swarm features make it a viable worker node. **Caveat:** Evaluate trust posture before production use.

---

## 3. GitHub Copilot CLI

### Verification Status: VERIFIED — Official GitHub product (technical preview)

| Attribute | Finding |
|---|---|
| **GitHub repo** | [github.com/github/copilot-cli](https://github.com/github/copilot-cli) |
| **npm package** | `@github/copilot` |
| **Install commands** | `npm install -g @github/copilot` (Node ≥22) <br> `winget install GitHub.Copilot` (Windows) <br> `brew install copilot-cli` (macOS/Linux) <br> `curl -fsSL https://gh.io/copilot-install \| bash` |
| **Prerelease** | `npm install -g @github/copilot@prerelease` |
| **Docs** | [docs.github.com/copilot/how-tos/set-up/install-copilot-cli](https://docs.github.com/copilot/how-tos/set-up/install-copilot-cli) |
| **SDK docs** | [docs.github.com/copilot/how-tos/copilot-sdk](https://docs.github.com/copilot/how-tos/copilot-sdk) |

### Capabilities
- AI-powered terminal assistant with agentic workflows (bash, file edits, web fetch, MCP servers, skills).
- Slash commands, autopilot mode, custom agents via `.github/agents/` and `~/.copilot/agents/`.
- Subagents with built-in types (Explore, Task) and custom `.agent.md` profiles.
- Session history, file tracking, `/chronicle`, remote sessions, research mode.
- ACP (Agent Client Protocol) support for integration with editors like Zed.

### Headless Mode
- **YES — Official headless server mode.**
  ```bash
  copilot --headless --port 4321
  copilot --headless          # Auto-picks random port, prints URL
  ```
- Designed for backend services, APIs, CI/CD. SDK connects over TCP (`cliUrl`).
- Docker/systemd deployment examples in official docs.
- **Known bug (verified):** Progressive latency degradation across sessions in headless mode even after `delete_session()`. Workaround is kill-and-restart. See [github/copilot-cli#2755](https://github.com/github/copilot-cli/issues/2755).
- **Breaking change history:** `--headless --stdio` was removed without deprecation in v0.0.410+, breaking SDK users. Now uses `--acp --stdio` or `--headless --port`. See [github/copilot-cli#1606](https://github.com/github/copilot-cli/issues/1606).

### JSON Output
- **YES — Added in v0.0.422 (2026-03-05).**
  - `--output-format json` emits **JSONL** in prompt mode (`-p`) for programmatic integrations.
  - This is confirmed in the official changelog: "Add --output-format json flag to emit JSONL in prompt mode for programmatic integrations."
- Prior to this, JSON output was a requested feature ([github/copilot-cli#52](https://github.com/github/copilot-cli/issues/52)).

### Programmatic Invocation
- **Shell scripting:** `copilot -p "your prompt" -s` (`-s` = silent/stream). See [docs](https://docs.github.com/en/copilot/how-tos/copilot-cli/automate-copilot-cli/run-cli-programmatically).
- **SDK:** `@github/copilot-sdk` (technical preview) with `CopilotClient`, `createSession`, `sendAndWait`.
- **Headless server + SDK** is the recommended architecture for production backends.
- **Permission flags for automation:**
  - `--allow-all-tools` (dangerous; container-only recommended)
  - `--mode`, `--autopilot`, `--plan` flags to start in specific agent modes
  - `client_credentials` OAuth grant for fully headless MCP auth (v1.0.40)

### Security Concerns
- **Requires active GitHub Copilot subscription** (Pro, Pro+, Business, Enterprise). Organization admins can disable CLI access.
- **Auto-updates:** The CLI auto-updates itself, which has caused breaking changes without deprecation (see issue #1606).
- **Headless session state leak:** Confirmed bug where session context accumulates across `delete_session()` calls, degrading performance and potentially leaking conversation state.
- **Proxy issues:** Corporate proxy support for headless SDK mode is buggy/regressed in recent versions. See [github/copilot-cli#2978](https://github.com/github/copilot-cli/issues/2978).
- **Permission model:** Use `--allow-all-tools` with extreme caution. Prefer scoped allowlists.

### Swarm Suitability
- **Good to Moderate.** Official support, JSONL output, headless SDK, and Docker deployment make it viable. **Caveats:** Subscription requirement, auto-update fragility, headless latency degradation bug, and lack of local model support (GitHub-hosted models only, unless using BYOK provider configs in SDK).

---

## 4. Claude Code Subagents (Anthropic)

### Verification Status: VERIFIED — Official Anthropic product

| Attribute | Finding |
|---|---|
| **Product** | Claude Code (closed-source CLI, distributed via npm / install script) |
| **Docs** | [code.claude.com/docs](https://code.claude.com/docs) |
| **Install** | `npm install -g @anthropic-ai/claude-code` (or official install script) |

### Subagent Definition: `.claude/agents/*.md`

Subagents are **Markdown files with YAML frontmatter**.

**File locations (priority order):**

| Location | Scope | Priority |
|---|---|---|
| Managed settings | Organization-wide | 1 (highest) |
| `--agents` CLI flag | Current session | 2 |
| `.claude/agents/` | Current project | 3 |
| `~/.claude/agents/` | All projects | 4 |
| Plugin `agents/` directory | Where plugin enabled | 5 (lowest) |

**Example `.claude/agents/code-reviewer.md`:**

```markdown
---
name: code-reviewer
description: Reviews code for quality and best practices
tools: Read, Glob, Grep
model: sonnet
permissionMode: default
---

You are a code reviewer. When invoked, analyze the code and provide
specific, actionable feedback on quality, security, and best practices.
```

**Available frontmatter fields (verified from official docs):**

| Field | Type | Description |
|---|---|---|
| `name` | string | Agent identifier |
| `description` | string | Natural language trigger description |
| `tools` | string[] | **Allowlist** — only these tools available to subagent |
| `disallowedTools` | string[] | **Denylist** — remove specific tools |
| `model` | string | Model alias: `sonnet`, `opus`, `haiku`, `inherit`, or full model ID |
| `permissionMode` | string | Permission mode for this agent |
| `maxTurns` | number | Max agentic turns before stopping |
| `background` | boolean | Run as non-blocking background task |
| `skills` | string[] | Available skills |
| `mcpServers` | string/object[] | MCP servers for this agent |
| `hooks` | object | Lifecycle hooks |
| `memory` | enum | Context memory scope |
| `effort` | enum | Reasoning effort (`low`/`medium`/`high`) |
| `isolation` | enum | `worktree` for isolated repo copy |

**Important:** The `tools` field is a **hard constraint**, not a prompt suggestion. A subagent with `tools: Read, Grep, Glob` physically cannot write files.

### Invoking Subagents
- **Natural language:** "Use the code-reviewer subagent to check auth changes"
- **@mention (guaranteed):** `@agent-code-reviewer` or `@"code-reviewer (agent)"`
- **Session-wide:** `claude --agent code-reviewer` (replaces default system prompt)
- **Programmatic (SDK):** Define in `agents` parameter of `query()` options

### Non-Interactive / Headless Mode (`--print`)

| Flag | Purpose |
|---|---|
| `--print` | Non-interactive mode; outputs result to stdout and exits |
| `--output-format json` | Clean JSON object output (no TUI) |
| `--output-format stream-json` | JSONL streaming events (requires `--verbose`) |
| `--input-format stream-json` | JSONL input for messages |
| `--verbose` | Required for `stream-json` output |
| `--include-partial-messages` | Stream chunks as they arrive |
| `--json-schema` | Enforce structured JSON schema on output |
| `--dangerously-skip-permissions` | Bypass all permission prompts (container/CI only) |
| `--allowedTools` | Allowlist tools for the session |
| `--disallowedTools` | Denylist tools for the session |
| `--permission-mode` | `default`, `acceptEdits`, `plan`, `auto`, `dontAsk`, `bypassPermissions` |
| `--max-turns` | Limit automation scope |
| `--no-session-persistence` | Don't save sessions to disk |
| `--exclude-dynamic-system-prompt-sections` | Strip `CLAUDE.md` / git status for prompt cache hits in CI |

**Example programmatic call:**
```bash
claude --print --output-format=json \
  --model sonnet \
  --allowedTools "Read,Edit,Bash(git:*)" \
  --dangerously-skip-permissions \
  "Refactor all console.log statements to use the logger module"
```

**Example JSON output:**
```json
{
  "type": "result",
  "subtype": "success",
  "result": "The actual response text with proper \\n escaping",
  "session_id": "uuid-here",
  "total_cost_usd": 0.001234,
  "usage": {
    "input_tokens": 10,
    "output_tokens": 50,
    "cache_read_input_tokens": 1000
  },
  "duration_ms": 2500
}
```

### Tool Permissions / Allowlists & Denylists

**Settings file:** `.claude/settings.json` or `~/.claude/settings.json`

```json
{
  "permissions": {
    "allow": ["Bash(git diff *)", "Read", "Edit"],
    "ask": ["Bash(git push *)"],
    "deny": ["WebFetch", "Bash(curl *)", "Read(./.env)", "Agent(Explore)"]
  }
}
```

- **Rule precedence:** Deny → Ask → Allow. First match wins.
- **MCP tool patterns:** `mcp__puppeteer`, `mcp__puppeteer__puppeteer_navigate`
- **Agent rules:** `Agent(Explore)`, `Agent(Plan)`, `Agent(my-custom-agent)`
- **Managed settings:** Organization admins can set `allowManagedPermissionRulesOnly: true` and `disableBypassPermissionsMode: "disable"`.

**CLI equivalents:**
- `--allowedTools` → maps to `permissions.allow`
- `--disallowedTools` → maps to `permissions.deny`

### Security Concerns
- **Closed source:** Binary is closed source. Anthropic blocked OAuth token extraction for external API use in Jan 2026.
- `--dangerously-skip-permissions` is powerful and dangerous. Use only in containers/CI.
- **Bypass mode can be disabled** by org admins via managed settings.
- **Sandboxing:** macOS Seatbelt, Linux bubblewrap + socat for OS-level isolation of Bash commands.

### Swarm Suitability
- **Excellent.** Native subagent system with hard tool constraints, `--print` headless mode, JSON + stream-json output, SDK support, and session management. Best-in-class for building agent swarms where the orchestrator spawns Claude Code workers.

---

## 5. Local Model Endpoints (Ollama, LM Studio, vLLM-MLX)

### Verification Status: VERIFIED — All three are established, actively maintained

### 5.1 Ollama

| Attribute | Finding |
|---|---|
| **Website** | [ollama.com](https://ollama.com) |
| **GitHub** | [github.com/ollama/ollama](https://github.com/ollama/ollama) |
| **Install** | `curl -fsSL https://ollama.com/install.sh \| sh` (macOS/Linux) <br> Download from ollama.com/download/windows |
| **License** | MIT |

**OpenAI-compatible API:**
```bash
# Base URL
http://localhost:11434/v1

# Example with OpenAI Python SDK
from openai import OpenAI
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
```

**Endpoints:** `/v1/chat/completions`, `/v1/embeddings`, `/v1/models`
**Tool calling:** Officially supported for models like Mistral, Llama 3.1/3.2, Qwen2.5. **Limitations:** No streaming tool calls, no `tool_choice` parameter.

**Swarm worker config pattern:**
```bash
export OPENAI_BASE_URL=http://localhost:11434/v1
export OPENAI_API_KEY=ollama          # placeholder, not validated
export OPENAI_MODEL=llama3.1:8b
```

### 5.2 LM Studio

| Attribute | Finding |
|---|---|
| **Website** | [lmstudio.ai](https://lmstudio.ai) |
| **License** | Proprietary (free for personal use) |
| **Install** | Download GUI installer from lmstudio.ai |

**OpenAI-compatible API:**
1. Open LM Studio → "Developer" tab
2. Select model → Enable server toggle
3. Default endpoint: `http://localhost:1234/v1`

```bash
export OPENAI_BASE_URL=http://localhost:1234/v1
export OPENAI_MODEL=your-model-name
# export OPENAI_API_KEY=lmstudio   # optional dummy key if auth errors
```

**Tool calling:** Experimental (v0.2.9+). Beta quality — good for testing, not production.
**Best for:** GUI exploration, prototyping, single-user workflows.

### 5.3 vLLM-MLX (Apple Silicon)

| Attribute | Finding |
|---|---|
| **GitHub** | [github.com/waybarrios/vllm-mlx](https://github.com/waybarrios/vllm-mlx) |
| **PyPI** | `pip install vllm-mlx` or `uv tool install vllm-mlx` |
| **License** | MIT |

**Quick start:**
```bash
pip install vllm-mlx
vllm-mlx serve mlx-community/Llama-3.2-3B-Instruct-4bit --port 8000 --continuous-batching
```

**OpenAI-compatible API:**
```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8000/v1", api_key="not-needed")
```

**Key features for swarm workers:**
- **Continuous batching** + **Paged KV cache** for concurrent requests
- **Prefix caching** (trie-based, shared across requests)
- **SSD-tiered KV cache** for long-context agents (`--ssd-cache-dir`)
- **MCP Tool Calling** with 12 parsers (OpenAI, Anthropic, Gemini, Qwen, DeepSeek, etc.)
- **Structured output** via `response_format` (lm-format-enforcer)
- **Prometheus metrics** endpoint (`--metrics`)
- **Multimodal:** text + image + video + audio + native TTS + STT (Whisper)

**Also worth noting — mlx-openai-server (alternative):**
- [github.com/cubist38/mlx-openai-server](https://github.com/cubist38/mlx-openai-server) (PyPI: `mlx-openai-server`)
- Supports multiple model types: `lm`, `multimodal`, `image-generation`, `image-edit`, `embeddings`, `whisper`

### Comparison Table for Swarm Workers

| Feature | Ollama | LM Studio | vLLM-MLX |
|---|---|---|---|
| **OpenAI API** | ✅ `/v1` | ✅ `/v1` | ✅ `/v1` + Anthropic `/v1/messages` |
| **Tool calling** | ✅ (non-streaming) | ⚠️ Experimental | ✅ MCP + 12 parsers |
| **Concurrent requests** | Moderate | Single-user | ✅ Continuous batching |
| **Production readiness** | Good | Prototype/testing | Excellent (Apple Silicon) |
| **Headless/server** | Background daemon | GUI + server toggle | CLI server only |
| **Metrics/observability** | Basic | Basic | ✅ Prometheus |
| **Best use case** | CLI-first dev workflows | GUI exploration | High-throughput Apple Silicon swarm |

### Security & Best Practices for Swarm Workers
1. **Bind to localhost only** (`127.0.0.1`) unless behind a reverse proxy with auth.
2. **Use dummy API keys** where required (Ollama, vLLM-MLX don't validate them).
3. **Nginx reverse proxy** for SSL termination; set `proxy_buffering off` for streaming.
4. **Docker + GPU passthrough** (NVIDIA Container Toolkit) for vLLM on Linux; vLLM-MLX is macOS/Apple Silicon native.
5. **Model capability metadata:** Not all local models support tool calling. Maintain an allowlist of tested models (e.g., Llama 3.1, Qwen2.5, Mistral).
6. **Context length:** Probe or pre-configure context lengths rather than relying on error-based probing.

---

## Summary: Swarm Builder Decision Matrix

| Tool | Verified | Headless | JSON Output | Programmatic | Local Models | Security Notes |
|---|---|---|---|---|---|---|
| **Freebuff** | ✅ | ❌ | ❌ | ❌ | ❌ | Ad-supported, closed backend |
| **OpenClaude** | ✅ | ✅ gRPC | ✅ (gRPC) | ✅ SDK/gRPC | ✅ | Third-party; plaintext key storage |
| **GitHub Copilot CLI** | ✅ | ✅ `--headless` | ✅ JSONL (v0.0.422+) | ✅ SDK + `-p` | ❌ (BYOK only) | Auto-update fragility; session leak bug |
| **Claude Code** | ✅ | ✅ `--print` | ✅ JSON/stream-json | ✅ SDK + CLI | ❌ (cloud only) | Best subagent primitives; closed source |
| **Ollama** | ✅ | ✅ Daemon | ✅ REST JSON | ✅ OpenAI SDK | N/A (is endpoint) | Open source; MIT |
| **LM Studio** | ✅ | ✅ Server | ✅ REST JSON | ✅ OpenAI SDK | N/A (is endpoint) | Proprietary GUI; exp. tool calling |
| **vLLM-MLX** | ✅ | ✅ Server | ✅ REST JSON | ✅ OpenAI SDK | N/A (is endpoint) | Apple Silicon optimized; metrics |

### Recommended Architecture for Local Agent Swarm

1. **Orchestrator:** Claude Code (`--print --output-format json`) or custom Node/Python harness.
2. **Worker dispatch:** Spawn Claude Code instances with `--agent <role>` + `--allowedTools` for task-specific workers.
3. **Local model backend:** vLLM-MLX (Apple Silicon) or Ollama (general purpose) providing OpenAI-compatible endpoints.
4. **Cross-platform workers:** OpenClaude in gRPC headless mode for non-Anthropic model routing or Android/mobile agents.
5. **Avoid:** Freebuff for swarm use (no automation surface). GitHub Copilot CLI only if you accept subscription dependency and headless latency workarounds.

---

*All URLs verified as of 2026-05-03. Flag any unverified claims inline. Tools and versions change rapidly — re-verify before production deployment.*
