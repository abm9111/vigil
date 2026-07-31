# /vigil-baseline — Save Current State

**Trigger:** `/vigil-baseline`
**Time:** 10 seconds
**Purpose:** Save current audit state as comparison baseline

## Execution

### Step 1: Run Quick Score

Run the score mode to get current cluster scores and findings.

### Step 2: Save Baseline

Create `.vigil/` directory if it doesn't exist:

```bash
mkdir -p .vigil
```

Write `.vigil/baseline.json`:

```json
{
  "version": 1,
  "timestamp": "{ISO 8601 timestamp}",
  "commit": "{current git commit hash}",
  "branch": "{current branch name}",
  "overall_score": 74,
  "overall_grade": "C",
  "clusters": {
    "security": {
      "score": 65,
      "grade": "D",
      "finding_count": 8,
      "critical": 1,
      "high": 2,
      "medium": 3,
      "low": 2
    }
  },
  "findings": [
    {
      "id": "VIGIL-SEC-001",
      "severity": "HIGH",
      "title": "Hardcoded API key",
      "file": "config.py",
      "line": 23,
      "hash": "{content hash of finding for stable comparison}"
    }
  ]
}
```

### Step 3: Update .gitignore

Check if `.vigil/` is in `.gitignore`. If not, suggest adding it:

```
# VIGIL audit baselines
.vigil/
```

### Step 4: Confirm

```
Baseline saved: .vigil/baseline.json
  Commit: {hash}
  Score: {score}/100 {grade}
  Findings: {N} ({critical}C / {high}H / {medium}M / {low}L)

Use /vigil watch or /vigil compare to see changes against this baseline.
```

## Baseline History

If `--history` flag is passed, save as timestamped file instead:

```
.vigil/baseline.json          ← current baseline
.vigil/baseline-2026-03-27.json  ← historical
```

This enables trend analysis over time.

## Rules

- Baseline should be saved AFTER fixes, not before (capture the "good" state)
- One baseline per project (overwrite by default)
- Add .vigil/ to .gitignore (baselines are local, not shared)
- Baseline includes finding hashes for stable comparison even if line numbers shift
