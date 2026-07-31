# /vigil-diff — Audit Changed Files Only

**Trigger:** `/vigil-diff`
**Time:** 30 seconds
**Purpose:** Quick audit of staged and unstaged changes (lighter than `watch` mode)

## Execution

### Step 1: Get Changes

```bash
# Staged changes
git diff --cached --name-only 2>/dev/null

# Unstaged changes
git diff --name-only 2>/dev/null

# Untracked files (potential concern)
git ls-files --others --exclude-standard 2>/dev/null | head -20
```

### Step 2: Filter to Auditable Files

Keep: `*.py`, `*.js`, `*.ts`, `*.tsx`, `*.jsx`, `*.go`, `*.rs`, `*.java`, `*.yaml`, `*.yml`, `*.json`, `*.toml`, `Dockerfile*`, `docker-compose*`

Skip: `*.md`, `*.txt`, `*.png`, `*.jpg`, `*.lock`, `*.sum`

### Step 3: Run Targeted Checks

For each changed file, run relevant tools from the applicable cluster:
- Python → ruff check, bandit (from security cluster)
- JS/TS → eslint, tsc on specific files
- Docker → hadolint
- Any → secrets grep

### Step 4: Report

```
/vigil-diff — {N} files changed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{file}:{line}  {severity}  {description}
{file}:{line}  {severity}  {description}

{N} findings in {M} changed files
{K} files clean

{if --fix available:}
Quick fix: /vigil-diff --fix
```

## Differences from Watch Mode

| Aspect | /vigil-diff | /vigil watch |
|--------|-------------|-------------|
| Scope | Git diff (staged + unstaged) | Baseline comparison |
| Speed | 30s | 15s |
| Baseline | Not required | Required |
| Trend | No | Yes (new/fixed/regressed) |
| Use case | Before staging/committing | CI gate |
