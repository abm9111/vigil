# VIGIL Adapter: Portable (Any AI Coding Tool)

**Purpose:** Minimal VIGIL methodology for any AI assistant (Aider, Continue, Cline, OpenCode, etc.)

## Core Instruction Block

Copy this into your AI tool's system prompt or instructions file:

```
## VIGIL Audit Methodology

When auditing code, follow this process:

1. DETERMINISTIC FIRST: Run actual tools before forming opinions
   - Python: ruff check, bandit, mypy
   - JS/TS: tsc --noEmit, eslint
   - Docker: hadolint
   - Secrets: grep for hardcoded credentials

2. FINDINGS FORMAT: VIGIL-{CLUSTER}-{NNN} {SEVERITY} {description} {file:line}
   Clusters: SEC, CODE, API, DATA, INFRA, FE, PERF, COMP, AIML
   Severities: CRITICAL(25pt) HIGH(10pt) MEDIUM(4pt) LOW(1pt) INFO(0pt)

3. SCORING: Start at 100, subtract penalties per finding per cluster
   Weights: Security 22%, Data 12%, API 10%, Infra 10%, Code 10%, Perf 8%, Compliance 6%
   Grades: A+(95+) A(90+) B(80+) C(70+) D(60+) E(40+) F(<40)
   Production-ready: 80+ (B)

4. CORRELATION: Check if findings compound
   - 3+ on same endpoint → escalate
   - Auth gap + SQL injection + PII → always CRITICAL
   - Secret in deployed config → always CRITICAL

5. EVERY FINDING NEEDS: What, Where (file:line), Why (impact), Fix (code)
```

## Minimal vs Full

| Feature | Portable (any tool) | Claude Code (full) |
|---------|--------------------|--------------------|
| Tool execution | Manual/limited | Automated |
| Correlation engine | Simplified rules | 7 named patterns |
| Compliance mapping | Not included | SOC2, ISO27001, OWASP |
| Baseline tracking | Not included | .vigil/baseline.json |
| Auto-fix | Not included | engines/fix-engine.md |
| CI integration | Not included | SARIF/JSON output |
| Scoring | Manual | Automated with weights |

The portable adapter gives ~60% of VIGIL's value. For the full experience, use Claude Code.
