# RUFLO SWARM — Output Aggregation Documentation

> **Version:** 1.1.0  
> **Date:** 2026-05-05  
> **Authors:** Claude-v2 (Documentation/Integration Fixer)

---

## OUTPUT AGGREGATION ARCHITECTURE

The Ruflo Swarm implements a multi-stage output aggregation system that:
1. **Collects** individual agent outputs during swarm execution
2. **Compiles** them into structured JSON summaries
3. **Aggregates** insights across multiple agent perspectives
4. **Persists** results for downstream consumption

---

## OUTPUT DIRECTORY STRUCTURE

```
swarm_runs/ruflo-insights/
├── {agent_type}_output_{timestamp}.txt     # Individual agent raw output
├── COMPILED_latest.json                    # Latest compiled summary
├── COMPILED_{YYYYMMDD}_{HHMMSS}.json      # Historical compiled outputs
├── AGGREGATED_insights_{timestamp}.md     # Human-readable summary
├── CONSENSUS_{topic}.md                    # Multi-agent consensus reports
└── logs/
    └── swarm_{YYYYMMDD}_{HHMMSS}.log       # Execution logs
```

---

## AGENT OUTPUT FORMAT

### Individual Agent Output

Each agent produces output in this format (saved to `{agent_type}_output.txt`):

```json
{
  "agent_type": "audit_quant",
  "role": "coder",
  "model": "deepseek/deepseek-chat:free",
  "tier": "free",
  "status": "success",
  "timestamp": "2026-05-05T14:30:00Z",
  "execution_time_s": 45.2,
  "findings": [
    {
      "category": "metric_alert",
      "severity": "high",
      "asset_class": "FOREX",
      "metric": "profit_factor",
      "value": 0.27,
      "threshold": 1.0,
      "recommendation": "Investigate before kill - check resolver-v2 filtering"
    }
  ],
  "data_sources_checked": [
    "audit_trail/data/universal_resolved_picks.json",
    "audit_dashboard/data/dashboard_data.json"
  ],
  "errors": [],
  "unable_to_verify": []
}
```

### Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `success`, `partial`, `failed`, or `unable_to_verify` |
| `findings` | array | Discovered issues/recommendations |
| `data_sources_checked` | array | Files actually inspected |
| `errors` | array | Any errors encountered |
| `unable_to_verify` | array | Claims that couldn't be verified |

---

## COMPILED OUTPUT FORMAT

### COMPILED_latest.json

The compiled output aggregates all agents from the most recent swarm run:

```json
{
  "compiled_at": "2026-05-05T14:35:00Z",
  "swarm_type": "audit",
  "agents_run": 5,
  "agents_successful": 4,
  "agents_failed": 1,
  "total_execution_time_s": 245.3,
  "tier_used": "free",
  "failover_count": 2,
  "outputs": [
    {
      "file": "audit_researcher_output_2026-05-05_143000.txt",
      "agent": "audit_researcher",
      "role": "researcher",
      "model": "google/gemini-2.5-flash",
      "tier": "free",
      "elapsed_s": 45.2,
      "status": "success",
      "output": "{...parsed JSON...}",
      "parsed_findings_count": 12
    },
    {
      "file": "audit_quant_output_2026-05-05_143100.txt",
      "agent": "audit_quant",
      "role": "coder",
      "model": "deepseek/deepseek-chat:free",
      "tier": "free",
      "elapsed_s": 52.1,
      "status": "success",
      "output": "{...parsed JSON...}",
      "parsed_findings_count": 8
    }
  ],
  "summary_metrics": {
    "total_findings": 20,
    "findings_by_severity": {
      "critical": 1,
      "high": 5,
      "medium": 8,
      "low": 6
    },
    "findings_by_asset_class": {
      "CRYPTO": 5,
      "FOREX": 8,
      "EQUITY": 4,
      "COMMODITY": 3
    }
  },
  "consensus_findings": [
    {
      "finding": "FOREX profit factor below threshold",
      "agreement": "high",
      "supporting_agents": ["audit_researcher", "audit_quant"],
      "confidence": 0.95
    }
  ]
}
```

---

## AGGREGATION WORKFLOW

### Phase 1: Execution-Time Aggregation

```python
# In orchestrator.py run_swarm():
for agent in swarm_agents:
    result = await run_agent(agent)
    
    # Immediate parsing
    parsed = safe_json_parse(result['raw_output'])
    
    # Store individual output
    save_individual_output(agent, result)
    
    # Add to compilation buffer
    compilation_buffer.append({
        'agent': agent.type,
        'findings': parsed.get('findings', []),
        'status': result['status']
    })
```

### Phase 2: Post-Run Compilation

```python
# Compile phase - orchestrator.py compile_outputs()
def compile_outputs(agent_results: list) -> dict:
    compiled = {
        'compiled_at': now_iso(),
        'agents_run': len(agent_results),
        'agents_successful': count_successes(agent_results),
        'summary_metrics': calculate_metrics(agent_results),
        'outputs': agent_results
    }
    
    # Cross-reference findings for consensus
    compiled['consensus_findings'] = find_consensus(agent_results)
    
    return compiled
```

### Phase 3: Consensus Detection

Consensus detection identifies findings supported by multiple agents:

```python
def find_consensus(agent_results: list) -> list:
    """
    Find findings mentioned by multiple agents.
    Uses fuzzy string matching on finding descriptions.
    """
    all_findings = []
    for result in agent_results:
        if result['status'] == 'success':
            all_findings.extend(result.get('findings', []))
    
    # Group semantically similar findings
    consensus_groups = group_similar_findings(all_findings)
    
    return [
        {
            'finding': group['common_description'],
            'agreement': 'high' if len(group['agents']) >= 2 else 'medium',
            'supporting_agents': list(group['agents']),
            'confidence': calculate_confidence(group)
        }
        for group in consensus_groups
    ]
```

---

## CONSUMPTION PATTERNS

### For Human Review

```bash
# Pretty-print the compiled output
cat swarm_runs/ruflo-insights/COMPILED_latest.json | python3 -m json.tool

# View human-readable summary
cat swarm_runs/ruflo-insights/AGGREGATED_insights_20260505.md
```

### For Programmatic Use

```python
import json

# Load compiled swarm output
with open('swarm_runs/ruflo-insights/COMPILED_latest.json') as f:
    compiled = json.load(f)

# Extract high-severity findings
high_sev = [
    finding for agent in compiled['outputs']
    for finding in agent.get('parsed', {}).get('findings', [])
    if finding.get('severity') == 'high'
]

# Check consensus on critical issues
consensus = compiled.get('consensus_findings', [])
critical_agreement = [c for c in consensus if c['confidence'] > 0.9]
```

### For CI/CD Integration

```yaml
# .github/workflows/swarm-analysis.yml
- name: Run Swarm Audit
  run: |
    python3 .ruflo/orchestrator.py --swarm audit --tier paid
    
    # Check for critical findings
    CRITICAL=$(cat swarm_runs/ruflo-insights/COMPILED_latest.json | \
               jq '.summary_metrics.findings_by_severity.critical // 0')
    
    if [ "$CRITICAL" -gt 0 ]; then
      echo "::error::Critical findings detected in swarm audit"
      exit 1
    fi
```

---

## OUTPUT AGGREGATION API

### Python API

```python
from pathlib import Path
import json

class SwarmAggregator:
    """Client for consuming Ruflo Swarm aggregated outputs."""
    
    def __init__(self, insights_dir: str = "swarm_runs/ruflo-insights"):
        self.insights_dir = Path(insights_dir)
    
    def get_latest_compiled(self) -> dict:
        """Load the most recent compiled output."""
        compiled_file = self.insights_dir / "COMPILED_latest.json"
        with open(compiled_file) as f:
            return json.load(f)
    
    def get_findings_by_severity(self, severity: str) -> list:
        """Get all findings of a specific severity."""
        compiled = self.get_latest_compiled()
        findings = []
        for output in compiled.get('outputs', []):
            parsed = output.get('parsed', {})
            for finding in parsed.get('findings', []):
                if finding.get('severity') == severity:
                    findings.append(finding)
        return findings
    
    def get_consensus_findings(self, min_confidence: float = 0.8) -> list:
        """Get findings with high consensus confidence."""
        compiled = self.get_latest_compiled()
        consensus = compiled.get('consensus_findings', [])
        return [c for c in consensus if c['confidence'] >= min_confidence]
    
    def get_agent_outputs(self, agent_type: str = None) -> list:
        """Get outputs from specific agent or all agents."""
        compiled = self.get_latest_compiled()
        outputs = compiled.get('outputs', [])
        if agent_type:
            outputs = [o for o in outputs if o['agent'] == agent_type]
        return outputs

# Usage
aggregator = SwarmAggregator()
high_priority = aggregator.get_findings_by_severity('high')
consensus = aggregator.get_consensus_findings(min_confidence=0.9)
```

### CLI API

```bash
# Get latest compiled output as JSON
python3 .ruflo/orchestrator.py --get-compiled

# Filter findings by severity
python3 .ruflo/orchestrator.py --get-compiled --severity high

# Get consensus findings only
python3 .ruflo/orchestrator.py --get-compiled --consensus-only

# Export to specific format
python3 .ruflo/orchestrator.py --get-compiled --format markdown
```

---

## SWARM BRIDGE DOCUMENTATION

### Python → TypeScript Bridge

The swarm system provides a bridge for TypeScript/Node.js applications:

```typescript
// swarm-bridge.ts
import { execSync } from 'child_process';
import { readFileSync } from 'fs';

interface SwarmOutput {
  compiled_at: string;
  agents_run: number;
  summary_metrics: Record<string, any>;
  outputs: AgentOutput[];
  consensus_findings: ConsensusFinding[];
}

export class SwarmBridge {
  private insightsDir: string;
  
  constructor(insightsDir: string = 'swarm_runs/ruflo-insights') {
    this.insightsDir = insightsDir;
  }
  
  /**
   * Run a swarm and return compiled output
   */
  async runSwarm(
    swarmType: 'audit' | 'github' | 'bugs' | 'strategy',
    options: { tier?: 'free' | 'paid' | 'hybrid', timeout?: number } = {}
  ): Promise<SwarmOutput> {
    const tier = options.tier || 'free';
    const timeout = options.timeout || 300;
    
    // Execute swarm via WSL bridge
    const cmd = `wsl bash -c "cd /mnt/c/findtorontoevents_antigravity.ca && python3 .ruflo/orchestrator.py --swarm ${swarmType} --tier ${tier} --timeout ${timeout}"`;
    
    execSync(cmd, { encoding: 'utf-8' });
    
    // Read compiled output
    return this.loadCompiled();
  }
  
  /**
   * Load the latest compiled output
   */
  loadCompiled(): SwarmOutput {
    const compiledPath = `${this.insightsDir}/COMPILED_latest.json`;
    const data = readFileSync(compiledPath, 'utf-8');
    return JSON.parse(data) as SwarmOutput;
  }
  
  /**
   * Get findings by severity
   */
  getFindingsBySeverity(severity: 'critical' | 'high' | 'medium' | 'low'): any[] {
    const compiled = this.loadCompiled();
    return compiled.outputs
      .flatMap(o => o.parsed?.findings || [])
      .filter(f => f.severity === severity);
  }
  
  /**
   * Get consensus findings above confidence threshold
   */
  getConsensusFindings(minConfidence: number = 0.8): ConsensusFinding[] {
    const compiled = this.loadCompiled();
    return compiled.consensus_findings
      .filter(c => c.confidence >= minConfidence);
  }
}

// Usage
const bridge = new SwarmBridge();
const output = await bridge.runSwarm('audit', { tier: 'hybrid' });
console.log(`Found ${output.summary_metrics.total_findings} findings`);

const critical = bridge.getFindingsBySeverity('critical');
console.log(`Critical issues: ${critical.length}`);
```

### Bridge Configuration

```json
// swarm-bridge-config.json
{
  "wsl_workspace": "/mnt/c/findtorontoevents_antigravity.ca",
  "windows_workspace": "C:\\findtorontoevents_antigravity.ca",
  "insights_dir": "swarm_runs/ruflo-insights",
  "default_timeout": 300,
  "tier_preference": "hybrid",
  "model_specs": {
    "free": {
      "timeout": 300,
      "retries": 3
    },
    "paid": {
      "timeout": 120,
      "retries": 1
    }
  }
}
```

---

## ERROR HANDLING

### Unable to Verify Pattern

When agents cannot access required files, they return structured "unable to verify" responses:

```json
{
  "status": "unable_to_verify",
  "agent_type": "audit_quant",
  "reason": "data_source_unavailable",
  "unavailable_sources": [
    "audit_dashboard/data/dashboard_data.json",
    "alpha_engine/config.py"
  ],
  "attempted_checks": [
    "wr_by_asset_class_breakdown",
    "forward_resolution_tracker_broken_check"
  ],
  "recommendation": "Ensure data files exist and are accessible to the orchestrator"
}
```

### Failure Aggregation

Failed agents are tracked in the compiled output:

```json
{
  "agents_failed": 1,
  "failed_agents": [
    {
      "agent": "strategist",
      "role": "architect",
      "error_type": "timeout",
      "error_message": "Agent exceeded 300s timeout",
      "recovery_suggestion": "Increase timeout with --timeout 600 or use paid tier"
    }
  ]
}
```

---

## BEST PRACTICES

### For Agent Authors

1. **Always return valid JSON** - Even for errors
2. **Use "unable_to_verify"** - Never invent data
3. **Include data sources checked** - Enables debugging
4. **Set severity levels** - critical, high, medium, low
5. **Provide actionable recommendations** - Not just problems

### For Consumers

1. **Check status before parsing** - Handle "unable_to_verify" gracefully
2. **Respect consensus confidence** - Don't act on low-confidence findings
3. **Monitor failure rates** - High failure rates indicate tier/model issues
4. **Version your consumers** - Compiled format may evolve

### For CI/CD

1. **Gate on critical findings** - Block deploys with critical issues
2. **Warn on high findings** - Require manual review for high severity
3. **Track consensus over time** - Watch for degradation patterns
4. **Cache compiled outputs** - Don't re-run swarms unnecessarily

---

## TROUBLESHOOTING

### Empty Compiled Output

```bash
# Check if swarm actually ran
ls -la swarm_runs/ruflo-insights/*_output_*.txt

# Check logs for errors
cat swarm_runs/ruflo-insights/logs/swarm_*.log | grep -i error

# Verify Hermes is installed
which hermes
```

### Parser Warnings

If you see "Unable to parse JSON from output":

```bash
# Check raw output format
cat swarm_runs/ruflo-insights/audit_quant_output_*.txt | head -50

# Look for non-JSON content before/after JSON
# Common issues: log messages, ANSI color codes, markdown formatting
```

### Missing Consensus

If consensus findings are empty:

1. Check if multiple agents are running
2. Verify agents are finding similar issues
3. Adjust similarity threshold (default: 0.8 cosine similarity)

---

## RELATED DOCUMENTATION

- `RUFLO_SWARM_GUIDE.MD` - Main user guide
- `.ruflo/orchestrator.py` - Implementation
- `.ruflo/agents/*.yaml` - Agent definitions
- `tools/swarm/api_consult.py` - Direct API bridge
- `updates/SWARM_STYLE_DIFF.MD` - Benchmark comparisons
