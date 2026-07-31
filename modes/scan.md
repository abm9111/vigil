# VIGIL Mode: Scan

**Time budget:** 30 seconds
**Depth:** Surface sweep — critical/high findings only
**Loads:** code-health, security clusters + scoring engine

## Execution

### Step 1: Stack Detection (5s)

Detect project stack by checking for marker files:

```
Python:     requirements.txt, pyproject.toml, setup.py, Pipfile
JavaScript: package.json (check for react, next, vue, angular in deps)
TypeScript: tsconfig.json
Go:         go.mod
Rust:       Cargo.toml
Java:       pom.xml, build.gradle
Docker:     Dockerfile, docker-compose.yml, compose.yml
CI:         .github/workflows/, .gitlab-ci.yml, Jenkinsfile
```

Record detected stack. Skip clusters that don't apply.

### Step 2: Critical Security Scan (10s)

Run ONLY high-signal security checks:

**Secrets:**
```bash
# Check for hardcoded secrets (high-signal patterns only)
grep -rn --include='*.py' --include='*.js' --include='*.ts' --include='*.yaml' --include='*.yml' --include='*.env' \
  -E '(password|secret|api_key|token|private_key)\s*=\s*["\x27][^"\x27]{8,}' . \
  --exclude-dir={node_modules,.venv,vendor,.git,dist,build} 2>/dev/null | head -20
```

**Known dangerous patterns:**
```bash
# SQL injection (string formatting in queries)
grep -rn --include='*.py' -E 'execute\(.*f["\x27]|execute\(.*%s.*%|execute\(.*\.format\(' . \
  --exclude-dir={node_modules,.venv,vendor,.git} 2>/dev/null | head -10

# eval/exec
grep -rn --include='*.py' --include='*.js' --include='*.ts' -E '\b(eval|exec)\s*\(' . \
  --exclude-dir={node_modules,.venv,vendor,.git,dist,build} 2>/dev/null | head -10
```

### Step 3: Code Health Quick Check (10s)

**Python (if detected):**
```bash
ruff check . --select E,F,W --statistics 2>&1 | tail -20
```

**TypeScript (if detected):**
```bash
npx tsc --noEmit 2>&1 | tail -20
```

### Step 4: Score and Report (5s)

Per [engines/scoring.md](../engines/scoring.md), compute scores for scanned clusters only.

## Output Template

```
VIGIL scan — {project} @ {subject} ({date})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Stack: {detected_stack}

SEC     {score}/100  {grade}  {trend}   {critical_count} critical, {high_count} high
CODE    {score}/100  {grade}  {trend}   {critical_count} critical, {high_count} high
{...other applicable clusters...}

OVERALL: {score}/100  {grade}  {trend} {delta}   ← SCANNED CLUSTERS ONLY
{NO CRITICAL/HIGH IN SCANNED SCOPE | CRITICAL/HIGH PRESENT — see below}
Scope: {N} of {M} applicable clusters scanned. Not a readiness verdict — run /vigil audit.

{if critical/high findings:}
━━━ Critical/High Findings ━━━
{VIGIL-ID}  {severity}  {one-line}  {file:line}
{...}

{if --fix: "Run /vigil audit --fix for auto-remediation"}
```

## Scan must never say PRODUCTION READY

Scan loads two clusters and skips missing tools by design. A data pipeline with clean
SEC/CODE tooling and catastrophic EGRESS defects would score 100/A — because egress was never
loaded. Not N/E, not N/A: simply out of scope.

"PRODUCTION READY" is the phrase `audit` uses as a ship gate, governed by severity floors and
N/E. Reusing it here launders a 30-second partial sweep into a release decision, and it is the
single most embarrassing thing this tool could say in public.

Scan reports **only** what it looked at:
- Verdict language is scoped — "no critical/high in scanned scope", never "production ready".
- The scanned/applicable cluster ratio is printed on the score line.
- Every skipped tool is named.

The same applies to any mode that narrows scope, including `--only`.

## Rules for Scan Mode

- Do NOT load domain detail files
- Do NOT run correlation engine (not enough data)
- Do NOT report LOW/INFO findings
- Do NOT run slow tools (mypy full, full test suite, trivy)
- MAX 15 seconds of tool execution, rest is parsing/reporting
- If a tool is not installed, skip it and **name it in the output**. Scan does not block on a
  missing tool the way `audit` and `watch` do (it is a 30s triage sweep, not a gate), which is
  exactly why it must never claim readiness — see below.
