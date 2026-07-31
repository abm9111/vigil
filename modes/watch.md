# VIGIL Mode: Watch

**Time budget:** 15 seconds
**Depth:** Diff-only — changes since baseline or last commit
**Loads:** code-health, security clusters + [engines/preflight.md](../engines/preflight.md) + [engines/ci-adapter.md](../engines/ci-adapter.md)
**Purpose:** CI gate — fast pass/fail on changed files only

## Execution

### Step 1: Get Changed Files (2s)

```bash
# If baseline exists, diff against it
# Otherwise, diff against HEAD~1 or main branch
git diff --name-only HEAD~1 2>/dev/null || git diff --name-only main 2>/dev/null

# Also check staged files
git diff --cached --name-only 2>/dev/null
```

Filter to auditable files (skip .md, .txt, images, lock files).

### Step 2: Run Targeted Checks (8s)

Only run tools on changed files:

**Python files changed:**
```bash
ruff check {changed_py_files} 2>&1
bandit {changed_py_files} -ll --quiet 2>&1
```

**JS/TS files changed:**
```bash
npx eslint {changed_ts_files} 2>&1
```

**Any file — secrets check:**
```bash
grep -n -E '(password|secret|api_key|token|private_key)\s*=\s*["\x27][^"\x27]{8,}' {changed_files} 2>/dev/null
```

**Dockerfile changed:**
```bash
hadolint {changed_dockerfiles} 2>&1
```

### Step 3: Baseline Comparison (3s)

If `.vigil/baseline.json` exists:
1. Load baseline findings for changed files
2. Compare current findings against baseline
3. Classify: NEW (not in baseline), FIXED (in baseline, not in current), REGRESSED (was fixed, now back)

### Step 4: Verdict (2s)

## Output Template

```
VIGIL watch — {branch} ({N} files changed)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

+ {count} new findings
- {count} fixed
! {count} regressed

{if new CRITICAL/HIGH:}
BLOCKING:
  VIGIL-SEC-001  CRITICAL  {description}  {file:line}  [NEW]
  VIGIL-CODE-003  HIGH     {description}  {file:line}  [NEW]

{if new MEDIUM/LOW:}
WARNING:
  VIGIL-CODE-012  MEDIUM   {description}  {file:line}  [NEW]

FIXED (nice work):
  VIGIL-SEC-005  HIGH     {description}  [FIXED]

VERDICT: {PASS | FAIL | WARN | INCOMPLETE}
{reason for verdict}
```

## Evidence Gating (fail closed)

Watch is the CI gate, which makes it the mode where a silently-absent scanner does the most
damage: a runner whose `bandit` disappeared after a base-image change would emit PASS forever.

Run preflight ([engines/preflight.md](../engines/preflight.md)) before the clusters. Then:

| Preflight result | Verdict | `--ci` exit |
|---|---|---|
| All required tools present | PASS / FAIL / WARN as normal | 0 / 1 |
| Some required tools missing | normal verdict, annotated `(partial evidence: {tools})` | as normal |
| A cluster has **no** required tools | **INCOMPLETE** | **2** |

INCOMPLETE is never a pass. Emit the capability report — which tool, which cluster, the
install command — so the failure is actionable rather than mysterious. Never substitute
reasoning for a scanner that did not run; see [engines/scoring.md](../engines/scoring.md).

## Verdict Logic

| Condition | Verdict | Exit Code |
|-----------|---------|-----------|
| No new CRITICAL/HIGH findings | PASS | 0 |
| New MEDIUM findings only | WARN | 0 (or 1 with --strict) |
| Any new CRITICAL or HIGH | FAIL | 1 |
| Regressed CRITICAL/HIGH | FAIL | 1 |
| Tool execution error | ERROR | 2 |

## Rules for Watch Mode

- ONLY check changed files — never full codebase
- Speed is paramount — 15 second budget is HARD limit
- Skip slow tools (mypy full project, full test suite, trivy)
- No correlation engine (too slow, not enough context)
- Baseline is required — if missing, create one first (`/vigil-baseline`)
- Perfect for pre-commit hooks and CI pipeline gates

---

## Delta Report Mode (Retainer Delivery)

**Trigger:** `/vigil watch --delta [--period weekly|monthly] [--client CLIENT_NAME]`
**Time:** 2-5 minutes (runs full audit, compares against last report)
**Purpose:** Generate comparison report for ManagedVIGIL retainer clients showing what changed since last scan

### Execution

#### Step 1: Load Previous Report (10s)

```bash
# Find most recent baseline for this client
ls -t ~/.vigil/reports/{client}/*.json 2>/dev/null | head -1

# If no previous report, run /vigil-baseline first, then audit
```

#### Step 2: Run Current Audit (2-4min)

Run standard audit mode on the current codebase state. Save results to:
```bash
mkdir -p ~/.vigil/reports/{client}
# Save as ~/.vigil/reports/{client}/{date}-audit.json
```

#### Step 3: Compute Delta (30s)

Compare current audit against previous:

```
For each finding in CURRENT:
  If NOT in PREVIOUS → mark as NEW
  If in PREVIOUS with same severity → mark as EXISTING
  If in PREVIOUS with different severity → mark as CHANGED

For each finding in PREVIOUS:
  If NOT in CURRENT → mark as FIXED

Score delta = current_score - previous_score
```

#### Step 4: Dependency CVE Check (30s)

```bash
# Check for new CVEs since last scan
pip-audit --format=json 2>&1
npm audit --json 2>&1

# Compare against previous audit's dependency findings
```

### Delta Report Output

```
╔══════════════════════════════════════════════════════════╗
║  VIGIL Delta Report — {client}                          ║
║  Period: {previous_date} → {current_date}               ║
╚══════════════════════════════════════════════════════════╝

SCORE TREND
  Previous: {score}/100 ({grade}) → Current: {score}/100 ({grade})
  Change: {+/-N} points {▲ IMPROVED | ▼ DEGRADED | ═ STABLE}

CHANGES SUMMARY
  + {N} new findings introduced
  - {N} findings fixed (nice work!)
  ~ {N} findings changed severity
  = {N} findings unchanged

{if new_findings:}
━━━ NEW FINDINGS (introduced this period) ━━━━━━━━━━━━━━━

  VIGIL-SEC-XXX  {SEVERITY}  {title}
    File: {file}:{line}
    Introduced: {commit_hash} by {author} on {date}
    Impact: {description}
    Fix: {recommendation}

{if fixed_findings:}
━━━ FIXED (resolved since last scan) ━━━━━━━━━━━━━━━━━━━

  VIGIL-SEC-XXX  {was_SEVERITY}  {title}  [FIXED]
    Fixed in: {commit_hash} by {author}

{if changed_findings:}
━━━ CHANGED SEVERITY ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  VIGIL-SEC-XXX  {old_severity} → {new_severity}  {title}

DEPENDENCY UPDATES
  New CVEs since last scan: {N}
  {CVE-ID}  {severity}  {package}  {description}

CLUSTER COMPARISON
  ┌─────────────────┬──────────┬──────────┬────────┐
  │ Cluster         │ Previous │ Current  │ Change │
  ├─────────────────┼──────────┼──────────┼────────┤
  │ Security        │ {XX}     │ {XX}     │ {+/-}  │
  │ Code Health     │ {XX}     │ {XX}     │ {+/-}  │
  │ ...             │ ...      │ ...      │ ...    │
  ├─────────────────┼──────────┼──────────┼────────┤
  │ OVERALL         │ {XX}     │ {XX}     │ {+/-}  │
  └─────────────────┴──────────┴──────────┴────────┘

RECOMMENDATIONS FOR NEXT PERIOD
  1. {highest priority unfixed finding}
  2. {dependency update needed}
  3. {trend concern}

NEXT SCAN: {date based on period}
```

### Retainer Report Storage

```
~/.vigil/reports/
  {client_name}/
    2026-04-01-audit.json     # Full audit data
    2026-04-01-delta.md       # Human-readable delta
    2026-05-01-audit.json
    2026-05-01-delta.md
    ...
```

### Automation

For retainer clients, schedule with cron or `/vigil watch --delta --schedule weekly`:

```bash
# Weekly delta scan (add to crontab)
# 0 9 * * 1 cd /path/to/client/repo && claude -p "/vigil watch --delta --client ClientName"
```
