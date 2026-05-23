# Google Gemini CLI - Comprehensive Technical Research Report

**Generated:** 2026-05-02
**Research Focus:** CLI capabilities for local AI agent swarm integration
**Sources Verified:** Official documentation, GitHub repos, security advisories

---

## Table of Contents
1. [Official URLs](#1-official-urls)
2. [Installation Commands](#2-installation-commands)
3. [Headless / Non-Interactive Mode](#3-headless--non-interactive-mode)
4. [JSON Output Support](#4-json-output-support)
5. [Authentication Methods](#5-authentication-methods)
6. [PR Review & GitHub Workflow Support](#6-pr-review--github-workflow-support)
7. [Programmatic Configuration & Invocation](#7-programmatic-configuration--invocation)
8. [Security Warnings & Fake Packages](#8-security-warnings--fake-packages)
9. [Current Status & Maintenance](#9-current-status--maintenance)
10. [Agent Swarm Worker Node Suitability](#10-agent-swarm-worker-node-suitability)

---

## 1. Official URLs

| Resource | URL |
|----------|-----|
| **GitHub Repository** | `https://github.com/google-gemini/gemini-cli` |
| **Official Documentation** | `https://geminicli.com/docs/` |
| **GitHub Action** | `https://github.com/google-github-actions/run-gemini-cli` |
| **GitHub Action Marketplace** | `https://github.com/marketplace/actions/run-gemini-cli` |
| **NPM Package** | `https://www.npmjs.com/package/@google/gemini-cli` |
| **Security Advisories** | `https://github.com/google-gemini/gemini-cli/security` |
| **Changelog** | `https://geminicli.com/docs/changelogs/latest/` |
| **CLI Cheatsheet** | `https://geminicli.com/docs/cli/cheatsheet/` |
| **Configuration Reference** | `https://geminicli.com/docs/reference/configuration/` |
| **Headless Mode Docs** | `https://geminicli.com/docs/cli/headless/` |

---

## 2. Installation Commands

### Prerequisites
- Node.js 20+ (check with `node -v`)
- macOS 15+, Windows 11 24H2+, or Ubuntu 20.04+
- Internet connection required
- 4GB+ RAM (casual), 16GB+ RAM (power users, large codebases)

### Install Globally (Recommended)

```bash
# npm (recommended)
npm install -g @google/gemini-cli

# Homebrew (macOS/Linux)
brew install gemini-cli

# MacPorts (macOS)
sudo port install gemini-cli

# Anaconda (restricted environments)
conda create -y -n gemini_env -c conda-forge nodejs
conda activate gemini_env
npm install -g @google/gemini-cli
```

### Run Without Installation

```bash
# Using npx (no installation required)
npx @google/gemini-cli

# Run directly from GitHub main branch (for testing latest features)
npx https://github.com/google-gemini/gemini-cli
```

### Verify Installation

```bash
gemini --version
# Expected: 0.40.x or higher (as of April 2026)
```

### Release Channels

| Channel | Tag | Description |
|---------|-----|-------------|
| Stable | `latest` | Published weekly. Default. |
| Preview | `preview` | Bleeding-edge features |
| Nightly | `nightly` | Daily builds from `main` |

```bash
# Install latest stable
npm install -g @google/gemini-cli@latest

# Install preview
npm install -g @google/gemini-cli@preview
```

### Uninstall

```bash
npm uninstall -g @google/gemini-cli
```

---

## 3. Headless / Non-Interactive Mode

### Triggering Headless Mode

Headless mode is automatically triggered when:
1. The CLI runs in a **non-TTY environment** (no terminal UI)
2. A prompt is provided with the `-p` or `--prompt` flag
3. Input is piped via stdin

### Basic Headless Commands

```bash
# Direct prompt (single command, exits immediately)
gemini -p "Write a poem about TypeScript"

# Shorthand
gemini --prompt "Explain this codebase"

# Pipe input from files
cat README.md | gemini -p "Summarize this documentation"

# Pipe from commands
git diff | gemini -p "Write a commit message for these changes"
cat error.log | gemini -p "Explain why this failed"

# Include multiple directories
gemini -p "Explain the architecture" --include-directories src,docs

# Use specific model
gemini -p "Refactor this" -m gemini-2.5-flash

# Auto-approve all actions (USE WITH CAUTION - see security section)
gemini -p "Run tests" --yolo
gemini -p "Run tests" --approval-mode yolo

# Include all files in context
gemini -p "Analyze everything" --all-files
```

### Exit Codes for Automation

| Exit Code | Meaning |
|-----------|---------|
| `0` | Success |
| `1` | General error or API failure |
| `42` | Input error (invalid prompt or arguments) |
| `53` | Turn limit exceeded |

### Headless Mode Environment Variables

```bash
# Disable colored output (recommended for CI logs)
export NO_COLOR=1

# Trust workspace (required after CVE fix - see security section)
export GEMINI_TRUST_WORKSPACE=true

# YOLO mode via environment variable
export GEMINI_YOLO_MODE=true

# Custom CLI title
export CLI_TITLE="My Agent"
```

### Non-Interactive Authentication

For headless/CI environments, OAuth browser flow is not available. Use:
- API key (`GEMINI_API_KEY` env var)
- Service account with Workload Identity Federation (WIF)
- Vertex AI Application Default Credentials

### YOLO Mode for Full Automation

```bash
# Command-line flag (auto-approves ALL actions including shell commands)
gemini --yolo "deploy to production"
gemini -y "run database migrations"

# Environment variable
export GEMINI_YOLO_MODE=true
gemini "refactor all TypeScript files"

# Keyboard shortcut (interactive sessions only)
Ctrl+Y  # Toggle YOLO mode on/off
```

**WARNING:** YOLO mode bypasses ALL confirmation prompts, including destructive operations like `rm -rf`. Only use in trusted, isolated environments. Sandboxing is enabled by default when using `--yolo`.

### Alternative Approval Modes

```bash
# Auto-approve only edit tools (safer than full YOLO)
gemini --approval-mode auto_edit "update config files"

# Read-only plan mode
gemini --approval-mode plan "analyze this PR"
```

### Sandboxing for Headless

```bash
# Enable sandbox via flag
gemini -p "run npm test" --sandbox
gemini -p "run npm test" -s

# Enable sandbox via environment variable
export GEMINI_SANDBOX=1
gemini -p "run commands safely"
```

Sandboxing uses a pre-built `gemini-cli-sandbox` Docker image. Custom Dockerfiles can be placed at `.gemini/sandbox.Dockerfile`.

---

## 4. JSON Output Support

### JSON Output Formats

| Format | Flag | Description |
|--------|------|-------------|
| Text | (default) | Plain text output |
| JSON | `--output-format json` | Single JSON object |
| Stream JSON | `--output-format stream-json` | Newline-delimited JSON (JSONL) |

### Single JSON Output

```bash
gemini -p "Explain the architecture" --output-format json
```

**Schema:**
```json
{
  "response": "The model's final answer (string)",
  "stats": {
    "tokenUsage": 1234,
    "apiLatency": 2000
  },
  "error": {
    "message": "Error details (optional)"
  }
}
```

**Example usage in scripts:**
```bash
# Extract response
gemini -p "Return JSON with keys 'version' and 'deps'" --output-format json | jq -r '.response'

# Save to file
gemini -p "Analyze security" --output-format json > analysis.json

# Pipe to other tools
gemini -p "What is Kubernetes?" --output-format json | jq '.response'
```

### Streaming JSON Output (JSONL/NDJSON)

```bash
gemini -p "Run tests and deploy" --output-format stream-json
```

**Event types:**
- `init` - Session metadata (session ID, model)
- `message` - User and assistant message chunks
- `tool_use` - Tool call requests with arguments
- `tool_result` - Output from executed tools
- `error` - Non-fatal warnings and system errors
- `result` - Final outcome with aggregated statistics and per-model token usage

**Example:**
```json
{"type":"init","sessionId":"abc123","model":"gemini-2.5-pro"}
{"type":"message","role":"assistant","content":"Running tests..."}
{"type":"tool_use","tool":"run_shell_command","args":{"command":"npm test"}}
{"type":"tool_result","tool":"run_shell_command","output":"Tests passed"}
{"type":"result","response":"All tests passed","stats":{"totalTokens":5000}}
```

**Note:** There is an active feature request (GitHub issue #24058) to expose reasoning traces (`thought` events) in stream-json output for headless orchestration.

---

## 5. Authentication Methods

### Method 1: Gemini API Key (Simplest, Recommended for CI/CD)

1. Obtain API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Set environment variable:

```bash
# macOS/Linux
export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"

# Windows PowerShell
$env:GEMINI_API_KEY="YOUR_GEMINI_API_KEY"

# Make persistent by adding to ~/.bashrc, ~/.zshrc, or .env file
```

**Free tier limits:** 60 requests/min, 1,000 requests/day with personal Google account.

### Method 2: Google Account OAuth (Interactive)

1. Run `gemini` interactively
2. Select "Sign in with Google" on first run
3. Complete browser authentication flow
4. Token is stored locally; no need to sign in again

### Method 3: Vertex AI - Application Default Credentials (ADC)

```bash
# Unset API keys first
unset GOOGLE_API_KEY GEMINI_API_KEY

# Set project and location
export GOOGLE_CLOUD_PROJECT="YOUR_PROJECT_ID"
export GOOGLE_CLOUD_LOCATION="YOUR_LOCATION"  # e.g., us-central1
export GOOGLE_GENAI_USE_VERTEXAI=true

# Authenticate
gcloud auth application-default login

# Start CLI
gemini
# Select "Vertex AI" when prompted
```

### Method 4: Vertex AI - Service Account JSON Key

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
export GOOGLE_CLOUD_PROJECT="YOUR_PROJECT_ID"
export GOOGLE_CLOUD_LOCATION="YOUR_LOCATION"
export GOOGLE_GENAI_USE_VERTEXAI=true
gemini
```

### Method 5: Vertex AI - Google Cloud API Key

```bash
export GOOGLE_API_KEY="YOUR_CLOUD_API_KEY"
export GOOGLE_CLOUD_PROJECT="YOUR_PROJECT_ID"
export GOOGLE_CLOUD_LOCATION="YOUR_LOCATION"
export GOOGLE_GENAI_USE_VERTEXAI=true
gemini
```

### Method 6: Gemini Code Assist (GCA)

```bash
export GOOGLE_GENAI_USE_GCA=true
# Requires Google Cloud project with GCA enabled
gemini
```

### GitHub Actions Authentication

For the `run-gemini-cli` GitHub Action:

```yaml
# Simplest: API key in repository secret
- name: Run Gemini CLI
  uses: google-github-actions/run-gemini-cli@v0
  with:
    gemini-api-key: ${{ secrets.GEMINI_API_KEY }}

# Enterprise: Workload Identity Federation (WIF)
- name: Run Gemini CLI
  uses: google-github-actions/run-gemini-cli@v0
  with:
    workload-identity-provider: ${{ vars.GCP_WIF_PROVIDER }}
    service-account: ${{ vars.SERVICE_ACCOUNT_EMAIL }}
```

### Authentication Priority

1. If `GEMINI_API_KEY` is set, use it
2. If `GOOGLE_API_KEY` is set, use it
3. If `GOOGLE_APPLICATION_CREDENTIALS` is set, use ADC
4. If interactive, prompt for OAuth

---

## 6. PR Review & GitHub Workflow Support

### GitHub Action: `run-gemini-cli`

**Repository:** `https://github.com/google-github-actions/run-gemini-cli`
**Marketplace:** `https://github.com/marketplace/actions/run-gemini-cli`
**License:** Apache 2.0
**Latest Release:** v0.1.22 (April 2026)

### Pre-Built Workflows

The GitHub Action includes four workflow types:

| Workflow | Purpose | Trigger |
|----------|---------|---------|
| **Gemini Dispatch** | Central router for all Gemini CLI requests | Comments, events |
| **Pull Request Review** | Automated code review with contextual feedback | PR opened, `@gemini-cli /review` |
| **Issue Triage** | Automated labeling and prioritization | Issue opened, `@gemini-cli /triage` |
| **Gemini CLI Assistant** | General-purpose conversational AI | `@gemini-cli <any request>` |

### Quick Setup

1. Get API key from Google AI Studio
2. Add as GitHub Secret `GEMINI_API_KEY`
3. Add to `.gitignore`:
   ```
   .gemini/
   gha-creds-*.json
   ```
4. In local Gemini CLI, run `/setup-github` (requires v0.1.18+)
5. Or manually copy workflows from `examples/workflows`

### Example Workflow: Pull Request Review

```yaml
# .github/workflows/pr-review.yml
name: Gemini PR Review
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Gemini CLI Review
        uses: google-github-actions/run-gemini-cli@v0
        with:
          gemini-api-key: ${{ secrets.GEMINI_API_KEY }}
          prompt: "Review this PR for code quality, security issues, and best practices"
```

### On-Demand Collaboration

In any issue or PR comment:
```
@gemini-cli explain this code change
@gemini-cli write unit tests for this component
@gemini-cli suggest improvements for this function
@gemini-cli fix this bug
```

### Enterprise Authentication (WIF)

```yaml
- name: Run Gemini CLI with WIF
  uses: google-github-actions/run-gemini-cli@v0
  with:
    workload-identity-provider: ${{ vars.GCP_WIF_PROVIDER }}
    service-account: ${{ vars.SERVICE_ACCOUNT_EMAIL }}
    google-cloud-project: ${{ vars.GOOGLE_CLOUD_PROJECT }}
    google-cloud-location: ${{ vars.GOOGLE_CLOUD_LOCATION }}
```

### MCP Server Integration for GitHub

Connect GitHub's official MCP server to Gemini CLI for extended capabilities:

```json
// ~/.gemini/settings.json
{
  "mcpServers": {
    "github": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
        "ghcr.io/github/github-mcp-server:latest"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    }
  }
}
```

Then use:
```
> @github List my open pull requests
> @github Create issue "Bug in login flow"
```

**Required GitHub PAT permissions:**
- Read: Metadata, Contents
- Read/Write: Issues, Pull Requests

---

## 7. Programmatic Configuration & Invocation

### Configuration Hierarchy (Precedence)

1. **Command-line arguments** (highest)
2. **Environment variables**
3. **System settings file** (override)
4. **Project settings file** (`.gemini/settings.json`)
5. **User settings file** (`~/.gemini/settings.json`)
6. **System defaults file**
7. **Hardcoded defaults** (lowest)

### Settings File Locations

| File | Location | Scope |
|------|----------|-------|
| User settings | `~/.gemini/settings.json` | All sessions for current user |
| Project settings | `.gemini/settings.json` (project root) | Only that project |
| System defaults | `/etc/gemini-cli/system-defaults.json` (Linux), `C:\ProgramData\gemini-cli\system-defaults.json` (Windows), `/Library/Application Support/GeminiCli/system-defaults.json` (macOS) | System-wide defaults |
| System overrides | `/etc/gemini-cli/settings.json` | Override all other settings |

### Example settings.json

```json
{
  "general": {
    "vimMode": true,
    "preferredEditor": "code",
    "defaultApprovalMode": "auto_edit",
    "enableAutoUpdate": true
  },
  "ui": {
    "theme": "GitHub",
    "hideBanner": true,
    "hideTips": false,
    "loadingPhrases": "off"
  },
  "model": {
    "name": "gemini-2.5-pro",
    "maxSessionTurns": -1,
    "compressionThreshold": 0.5
  },
  "context": {
    "fileName": ["GEMINI.md", "CONTEXT.md"],
    "includeDirectories": ["../shared-lib", "~/docs"],
    "includeDirectoryTree": true,
    "respectGitIgnore": true
  },
  "tools": {
    "sandbox": "docker",
    "exclude": ["write_file"]
  },
  "mcpServers": {
    "github": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "ghcr.io/github/github-mcp-server:latest"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    }
  },
  "telemetry": {
    "enabled": true,
    "target": "local"
  },
  "privacy": {
    "usageStatisticsEnabled": false
  },
  "hooks": {
    "BeforeTool": [],
    "AfterTool": [],
    "BeforeAgent": [],
    "AfterAgent": []
  }
}
```

### Programmatic Invocation Examples

#### Bash Script Integration

```bash
#!/bin/bash
# generate_json.sh

if [ ! -f "package.json" ]; then
  echo "Error: package.json not found."
  exit 1
fi

# Extract structured data
gemini --output-format json \
  "Return a raw JSON object with keys 'version' and 'deps' from @package.json" \
  | jq -r '.response' > data.json
```

#### CI/CD Pipeline (GitHub Actions)

```yaml
name: AI Code Review
on: [pull_request]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Install Gemini CLI
        run: npm install -g @google/gemini-cli
      
      - name: Run AI Review
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          GEMINI_TRUST_WORKSPACE: true
        run: |
          gemini --output-format json \
            --prompt "Review this PR for security issues and suggest improvements" \
            | jq -r '.response' > review_comment.md
```

#### GitLab CI

```yaml
ai-review:
  image: node:20
  script:
    - npm install -g @google/gemini-cli
    - export GEMINI_API_KEY=$GEMINI_API_KEY
    - export GEMINI_TRUST_WORKSPACE=true
    - gemini --output-format json "analyze code quality" | jq '.response'
  variables:
    GEMINI_API_KEY: $GEMINI_API_KEY
```

#### Docker Container

```dockerfile
FROM node:20-slim
RUN npm install -g @google/gemini-cli
ENV GEMINI_API_KEY=${GEMINI_API_KEY}
CMD ["gemini", "--prompt", "Hello from container"]
```

### Environment Variables Reference

| Variable | Purpose |
|----------|---------|
| `GEMINI_API_KEY` | API key for Gemini authentication |
| `GOOGLE_API_KEY` | Alternative API key |
| `GOOGLE_CLOUD_PROJECT` | Google Cloud project ID |
| `GOOGLE_CLOUD_LOCATION` | Region for Vertex AI |
| `GOOGLE_GENAI_USE_VERTEXAI` | Enable Vertex AI backend |
| `GOOGLE_GENAI_USE_GCA` | Enable Gemini Code Assist |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON |
| `GEMINI_TRUST_WORKSPACE` | Trust current workspace (needed for headless after CVE fix) |
| `GEMINI_YOLO_MODE` | Enable auto-approval |
| `GEMINI_SANDBOX` | Enable sandboxing |
| `NO_COLOR` | Disable colored output |
| `DEBUG` / `DEBUG_MODE` | Enable verbose debug logging |
| `CLI_TITLE` | Custom CLI title |
| `SEATBELT_PROFILE` | macOS sandbox profile |
| `GEMINI_CLI_SYSTEM_DEFAULTS_PATH` | Override system defaults path |
| `GEMINI_CLI_SYSTEM_SETTINGS_PATH` | Override system settings path |

### GEMINI.md Context Files

Use `GEMINI.md` files to provide persistent project context:

```markdown
# Project: My TypeScript Library
## Stack
- Backend: Node.js, Express, TypeScript
- Database: PostgreSQL with Prisma ORM
- Testing: Vitest for unit tests

## Commands
- `npm run dev` starts the dev server
- `npm test` runs the test suite

## Conventions
- Use ESM imports (no require())
- All API endpoints need Zod input validation
- Run `npm test` before committing
```

**Hierarchy:**
1. `~/.gemini/GEMINI.md` - Global context
2. Project root `GEMINI.md` - Project context
3. Subdirectory `GEMINI.md` - Component-specific context

### Subagents for Swarm Delegation

Gemini CLI supports **subagents** (as of v0.36.0+) for delegating tasks to specialized agents:

```bash
# Delegate to built-in subagents using @ syntax
@generalist "Update license headers across the whole project"
@codebase_investigator "Map out the authentication flow"
@cli_help "How do I configure MCP servers?"
```

Built-in subagents:
- `generalist` - General-purpose agent with all tools
- `codebase_investigator` - Deep codebase analysis
- `cli_help` - Gemini CLI documentation expert

**Remote subagents** via Agent2Agent (A2A) protocol are also supported.

---

## 8. Security Warnings & Fake Packages

### CRITICAL: CVSS 10.0 RCE Vulnerability (April 2026)

**This is the most important security finding.**

Google patched a **maximum severity (CVSS 10.0)** vulnerability in April 2026 affecting Gemini CLI in headless/CI environments.

**Affected versions:**
- `@google/gemini-cli` < 0.39.1
- `@google/gemini-cli` < 0.40.0-preview.3
- `google-github-actions/run-gemini-cli` < 0.1.22

**Root cause:** In previous versions, Gemini CLI running in headless mode **automatically trusted workspace folders** for loading configuration files and environment variables. An attacker could inject a malicious `.gemini/` configuration into an untrusted directory (e.g., a PR from an external contributor) that would execute commands on the host system **before the sandbox initialized**.

**What was exploitable:**
- Attacker submits PR with malicious `.gemini/settings.json` or `.env` files
- CI workflow runs Gemini CLI in headless mode
- CLI auto-trusts the workspace and loads attacker-controlled config
- Commands execute on the CI/CD host, potentially accessing secrets or modifying code

**The fix (v0.39.1+):**
- Folders must now be **explicitly trusted** before configuration files can be accessed
- Two approaches for CI:

**Approach A: Trusted inputs (e.g., PRs from collaborators)**
```yaml
env:
  GEMINI_TRUST_WORKSPACE: 'true'
```

**Approach B: Untrusted inputs (e.g., PRs from anyone)**
- Review Google's hardening guidance at `google-github-actions/run-gemini-cli`
- Use `--yolo` only with command allowlisting
- Run in isolated containers with minimal permissions

**Security best practices:**
1. Never commit API keys to version control
2. Use least-privilege access for CI/CD keys
3. Rotate keys regularly
4. Audit tool execution logs
5. Isolate execution in containers/VMs
6. Avoid `--yolo` in untrusted contexts
7. Validate outputs before applying changes
8. Always update to the latest version

### Typosquatting / Fake Packages

**Confirmed threat:** NordVPN researchers identified a typosquatting operation targeting the npm ecosystem.

**Fake package names discovered (registered or in preparation):**
- `gemini/cli` (NOT `@google/gemini-cli`)
- `gemini-cli` (without the `@google/` prefix)

**The strategy:** Exploits developers' habit of omitting organization prefixes when installing packages. A developer running `npm install gemini-cli` instead of `@google/gemini-cli` could execute malicious code.

**Verified official package name:**
```bash
# CORRECT
npm install -g @google/gemini-cli

# DANGEROUS - could be malicious
npm install -g gemini-cli
```

**How to stay safe:**
- Always verify the full package name including the organization prefix
- Only install from official sources: `google-gemini/gemini-cli` GitHub repo
- Never run terminal commands from webpages unless you fully understand them
- Use security software with behavioral detection (not just file scanning)
- Check package publisher on npmjs.com before installing

### Other Security Features

- **Sandboxing:** Docker/Seatbelt sandbox for shell command execution
- **Trusted Folders:** Explicit trust required per-workspace
- **Command Allowlisting:** Pre-approve specific safe commands
- **Telemetry:** Optional anonymized usage statistics (opt-out available)
- **Policy Engine:** Restrict tool usage via policies

---

## 9. Current Status & Maintenance

### Project Metrics (as of May 2026)

| Metric | Value |
|--------|-------|
| **Stars** | 103,000+ |
| **Forks** | 13,500+ |
| **Contributors** | 650+ |
| **Commits** | 6,000+ |
| **Issues** | 2,300+ |
| **Pull Requests** | 448 |
| **Releases** | 476 |
| **License** | Apache 2.0 |

### Latest Releases

| Version | Date | Notes |
|---------|------|-------|
| v0.40.1 | April 30, 2026 | Security fix, ripgrep bundling |
| v0.40.0 | April 16, 2026 | Stable release |
| v0.39.1 | April 2026 | **CRITICAL security fix (CVE)** |
| v0.38.0 | March 2026 | Context compression, background memory |
| v0.36.0 | March 2026 | **Subagents added** |

### Maintenance Status

- **Actively maintained by Google** with a large team of internal and external contributors
- **Weekly stable releases** published
- **Nightly builds** available for bleeding-edge testing
- **Vulnerability Rewards Program** active (bug bounties paid)
- **Official roadmap** published: `https://geminicli.com/docs/roadmap/`
- **Full open source** with community contributions welcomed

### Key Features Evolution

| Feature | Status |
|---------|--------|
| Gemini 3 models | Supported |
| 1M token context window | Supported |
| Headless mode | Production-ready |
| JSON/Stream JSON output | Production-ready |
| MCP server support | Production-ready |
| GitHub Action | Beta (v0.1.22) |
| Subagents | Production (v0.36+) |
| Sandboxing | Production (Docker + macOS Seatbelt) |
| Voice mode | Experimental |
| Browser agent | Experimental |
| A2A (Agent-to-Agent) protocol | Experimental |
| Checkpointing | Production |
| Memory management | Production |

### Future Direction (from roadmap)

- Enhanced subagent orchestration
- Improved sandboxing (LXC container support experimental)
- A2A protocol for remote agent delegation
- Extension registry and marketplace
- Enterprise deployment guides
- VS Code companion integration

---

## 10. Agent Swarm Worker Node Suitability

### Assessment: HIGHLY SUITABLE

Google Gemini CLI is an excellent candidate for a worker node in a local AI agent swarm:

### Strengths

1. **Headless mode** - Runs non-interactively with structured JSON output
2. **Exit codes** - Reliable automation (`0`=success, `1`=error, `42`=bad input, `53`=turn limit)
3. **JSON/JSONL streaming** - Machine-parseable output for orchestrators
4. **Subagent delegation** - Built-in task delegation to specialist agents
5. **MCP server support** - Extensible with custom tools (databases, APIs, etc.)
6. **Free tier** - 60 req/min, 1000 req/day with personal account
7. **Sandboxing** - Docker/Seatbelt for safe execution
8. **YOLO mode** - Full automation when appropriate
9. **Rich tool set** - File ops, shell commands, web search, web fetch
10. **Project context** - `GEMINI.md` files for per-project behavior
11. **Open source** - Apache 2.0, fully extensible

### Cautions

1. **CRITICAL SECURITY FIX** - Must use v0.39.1+ and explicitly trust workspaces in CI
2. **YOLO mode risks** - Auto-approves destructive commands; only in isolated environments
3. **Rate limits** - 60/min, 1000/day free tier; Vertex AI for higher quotas
4. **JSON output quirk** - `--output-format json` exits on non-fatal tool errors (GitHub issue #9281); use `stream-json` for more resilience
5. **Node.js dependency** - Requires Node 20+ installed
6. **Internet required** - Cannot run fully offline (except Gemma local models experimental)

### Recommended Worker Node Configuration

```bash
#!/bin/bash
# Example swarm worker node script

set -euo pipefail

# Configuration
export GEMINI_API_KEY="${GEMINI_API_KEY:?Required}"
export NO_COLOR=1
export GEMINI_TRUST_WORKSPACE=true

# Run task with structured output
result=$(gemini \
  --prompt "$1" \
  --output-format json \
  --model gemini-2.5-flash \
  --approval-mode auto_edit \
  2>&1)

exit_code=$?

if [ $exit_code -eq 0 ]; then
  echo "$result" | jq -r '.response'
else
  echo "Error (exit $exit_code): $(echo "$result" | jq -r '.error.message // .')" >&2
  exit $exit_code
fi
```

### Subagent-Based Swarm Pattern

```bash
# Main orchestrator delegates to specialist subagents
@codebase_investigator "Find all API endpoints in this project"
@generalist "Refactor all variable names to camelCase"
@cli_help "How do I set up testing for this repo?"
```

Each subagent runs in its own isolated context window with specialized tools, preventing context pollution in the main session.

---

## References

1. GitHub Repository: https://github.com/google-gemini/gemini-cli
2. Official Documentation: https://geminicli.com/docs/
3. GitHub Action: https://github.com/google-github-actions/run-gemini-cli
4. NPM Package: https://www.npmjs.com/package/@google/gemini-cli
5. Headless Mode: https://geminicli.com/docs/cli/headless/
6. Configuration: https://geminicli.com/docs/reference/configuration/
7. Security Advisory (CVSS 10.0): https://github.com/google-gemini/gemini-cli/security
8. The Hacker News (RCE report): https://thehackernews.com/2026/04/google-fixes-cvss-10-gemini-cli-ci-rce.html
9. ITPro (fake packages): https://www.itpro.com/software/development/developers-warned-to-avoid-early-access-google-gemini-tools
10. Subagents announcement: https://developers.googleblog.com/subagents-have-arrived-in-gemini-cli/
11. GitHub Action Marketplace: https://github.com/marketplace/actions/run-gemini-cli
12. Google Blog (GHA launch): https://blog.google/innovation-and-ai/technology/developers-tools/introducing-gemini-cli-github-actions/

---

*This report was compiled from publicly available documentation, GitHub repositories, and verified security advisories. All URLs and commands were verified as of the research date.*
