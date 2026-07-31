# VIGIL Engine: Semgrep/CodeQL Orchestrator

**Purpose:** Run Semgrep and CodeQL static analysis with parallel subagents, custom rulesets, and SARIF output.

## Prerequisites

```bash
# Check Semgrep
semgrep --version 2>/dev/null && echo "Semgrep: INSTALLED" || echo "Semgrep: NOT INSTALLED (pip install semgrep)"

# Check Semgrep Pro (cross-file taint analysis)
semgrep --pro --validate --config p/default 2>/dev/null && echo "Pro: AVAILABLE" || echo "Pro: OSS only"

# Check CodeQL
codeql version 2>/dev/null && echo "CodeQL: INSTALLED" || echo "CodeQL: NOT INSTALLED"
```

If neither is installed, fall back to VIGIL's built-in grep patterns. Report as SKIPPED with install instructions.

## Semgrep Scan Workflow

### Step 1: Detect Languages

```bash
# Count files per language
find . -name '*.py' -not -path '*/.venv/*' -not -path '*/node_modules/*' | wc -l
find . -name '*.js' -o -name '*.ts' -o -name '*.tsx' | grep -v node_modules | wc -l
find . -name '*.go' -not -path '*/vendor/*' | wc -l
find . -name '*.rs' | wc -l
find . -name '*.java' -o -name '*.kt' | wc -l
find . -name '*.sol' | wc -l
```

### Step 2: Select Rulesets

**Always include (if language detected):**

| Language | Official Rulesets | Third-Party Rulesets |
|----------|-------------------|---------------------|
| Python | `p/python`, `p/django`, `p/flask` | `p/trailofbits`, `p/bandit` |
| JavaScript/TS | `p/javascript`, `p/typescript`, `p/react`, `p/nextjs` | `p/trailofbits` |
| Go | `p/go` | `p/trailofbits`, `p/dgryski.semgrep-go` |
| Java/Kotlin | `p/java`, `p/kotlin` | `p/trailofbits` |
| Rust | `p/rust` | `p/trailofbits` |
| Solidity | `p/solidity` | `p/decurity-audit`, `p/trailofbits` |
| Docker | `p/dockerfile` | — |
| Generic | `p/secrets`, `p/owasp-top-ten` | — |

**CRITICAL:** Always use `--metrics=off` to prevent data leakage during security audits.

### Step 3: Scan Modes

| Mode | Use When | Flags |
|------|----------|-------|
| **Important only** | `/vigil scan` or `/vigil audit` | `--severity MEDIUM --severity HIGH --severity CRITICAL` |
| **Run all** | `/vigil siege` | No severity filter — catch everything |

### Step 4: Execute Scans

```bash
# Create output directory
mkdir -p .vigil/semgrep/raw .vigil/semgrep/results

# Run per-language scans (spawn as parallel agents in siege mode)
semgrep scan --config p/python --config p/trailofbits \
  --metrics=off --sarif --output .vigil/semgrep/raw/python.sarif \
  --severity MEDIUM --severity HIGH --severity CRITICAL \
  --exclude='.venv' --exclude='node_modules' --exclude='tests' \
  . 2>&1

semgrep scan --config p/secrets --config p/owasp-top-ten \
  --metrics=off --sarif --output .vigil/semgrep/raw/secrets.sarif \
  . 2>&1
```

**With Semgrep Pro (cross-file taint analysis):**
```bash
semgrep scan --pro -j 1 --config p/python \
  --metrics=off --sarif --output .vigil/semgrep/raw/python-pro.sarif \
  . 2>&1
```

### Step 5: Merge SARIF Results

```bash
# Merge all SARIF files into one
python3 -c "
import json, glob, sys
merged = {'version': '2.1.0', '\$schema': 'https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/schema/sarif-schema-2.1.0.json', 'runs': []}
for f in glob.glob('.vigil/semgrep/raw/*.sarif'):
    with open(f) as fh:
        data = json.load(fh)
        merged['runs'].extend(data.get('runs', []))
with open('.vigil/semgrep/results/results.sarif', 'w') as fh:
    json.dump(merged, fh, indent=2)
print(f'Merged {len(merged[\"runs\"])} runs')
"
```

### Step 6: Parse Into VIGIL Findings

Map Semgrep severity → VIGIL severity:
- `ERROR` → CRITICAL or HIGH (based on confidence)
- `WARNING` → MEDIUM
- `INFO` → LOW

Map Semgrep category → VIGIL cluster:
- `security` → SEC
- `correctness` → CODE
- `performance` → PERF
- `best-practice` → CODE

## CodeQL Workflow

### Step 1: Create Database

```bash
# Python
codeql database create .vigil/codeql-db --language=python --source-root=. 2>&1

# JavaScript
codeql database create .vigil/codeql-db --language=javascript --source-root=. 2>&1
```

### Step 2: Run Analysis

```bash
codeql database analyze .vigil/codeql-db \
  --format=sarif-latest \
  --output=.vigil/codeql-results.sarif \
  codeql/python-queries:codeql-suites/python-security-and-quality.qls 2>&1
```

### Step 3: Parse Into VIGIL Findings

Same SARIF → VIGIL finding mapping as Semgrep.

## Integration with VIGIL Modes

| Mode | Semgrep | CodeQL |
|------|---------|--------|
| scan | Skip (too slow) | Skip |
| audit | Important-only mode | Skip (too slow) |
| siege | Run-all mode + Pro | Full analysis |
| watch | Skip | Skip |
| score | Skip | Skip |

## Fallback

If neither Semgrep nor CodeQL is installed:
1. Report as SKIPPED in the tool status section
2. Use VIGIL's built-in grep patterns (always available)
3. Note: "Install Semgrep for deeper analysis: `pip install semgrep`"
