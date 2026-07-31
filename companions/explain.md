# /vigil-explain — Deep-Dive a Finding

**Trigger:** `/vigil-explain VIGIL-SEC-001` (or any finding ID)
**Time:** 1 minute
**Purpose:** Detailed explanation of a specific finding with context

## Execution

### Step 1: Locate the Finding

Parse the finding ID to determine:
- Cluster (SEC, CODE, API, DATA, INFRA, FE, PERF, COMP, AIML, CORR)
- Finding number

### Step 2: Gather Context

```bash
# Read the file containing the finding
# Read surrounding code (±20 lines)
# Check git blame for who introduced it and when
git blame -L {line-10},{line+10} {file} 2>/dev/null

# Check if this pattern exists elsewhere
grep -rn '{pattern}' . --exclude-dir={.venv,node_modules,.git} 2>/dev/null | head -10
```

### Step 3: Generate Explanation

```
VIGIL-{ID}: {title}
━━━━━━━━━━━━━━━━━━

Severity: {severity}
Cluster: {cluster}
File: {file}:{line}
Introduced: {date} by {author} in {commit_short}

WHAT:
{2-3 sentence explanation of what the finding is}

WHY IT MATTERS:
{Concrete impact — not generic "best practice" language}
{What could go wrong in production}

CODE:
```{lang}
{relevant code snippet with the issue highlighted}
```

FIX:
```{lang}
{corrected code snippet}
```

{If correlated:}
RELATED FINDINGS:
  VIGIL-{ID} — {description}
  VIGIL-{ID} — {description}

COMPLIANCE:
  {SOC2/ISO27001/OWASP controls if applicable}

REFERENCES:
  {CWE, CVE, or documentation link}
```

## Rules

- Always read the actual code before explaining
- Always check git blame for context (was this intentional?)
- Explanation must be specific to THIS code, not generic
- Fix must be copy-pasteable
- If the finding might be a false positive, say so with reasoning
