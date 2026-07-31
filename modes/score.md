# VIGIL Mode: Score

**Time budget:** 30 seconds
**Depth:** Numeric — single score with trend
**Loads:** ALL clusters + scoring engine
**Purpose:** Quick health number for dashboards and tracking

## Execution

### Step 1: Fast Cluster Scoring (20s)

For each applicable cluster, run the MINIMUM tools needed to compute a score:

| Cluster | Quick Check |
|---------|-------------|
| Security | `grep` for secrets + `bandit -ll --quiet` (Python) or pattern scan |
| Code Health | `ruff check --statistics` (Python) or `eslint --format compact` (JS/TS) |
| API | Grep for endpoint patterns, check auth decorators |
| Data | Grep for raw SQL, check migration files exist |
| Infra | Check Dockerfile exists + `docker compose config --quiet` |
| Frontend | `tsc --noEmit` (if TS) |
| Performance | Pattern scan for N+1, sync in async, large payloads |
| Compliance | Check LICENSE, CHANGELOG, README exist |
| AI/ML | Check for model versioning, data validation |

### Step 2: Compute Score (5s)

Per [engines/scoring.md](../engines/scoring.md):
1. Count findings per severity per cluster
2. Apply penalty formula
3. Weight and aggregate
4. Compare to baseline

### Step 3: Trend (5s)

If `.vigil/baseline.json` exists:
- Compute delta from last score
- Determine trend direction
- Identify top driver of change

## Output Template

### Compact (default)

```
VIGIL: 74/100 C ▼-3 (security: -8pts drove decline)
```

If the score was capped by an unresolved finding, say so — a lowered number with no reason
reads as an arithmetic error:

```
VIGIL: 79/100 C (capped from 94 by VIGIL-CORR-001 HIGH)
```

If any applicable cluster is **N/E** (no evidence — its required tools were unavailable),
emit no grade letter at all. Per [engines/scoring.md](../engines/scoring.md) a grade is a
claim about evidence that does not exist:

```
VIGIL: INCOMPLETE — 1 of 6 clusters had no evidence (security: bandit, semgrep unavailable)
       Partial across examined clusters: 91/100 — NOT a pass verdict.
```

### Expanded (with --verbose or standalone invocation)

```
VIGIL score — {project} @ {commit_short}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SEC     65/100  D  ▼  (22%) ████████████░░░░░░░░
CODE    85/100  B  →  (10%) █████████████████░░░
API     80/100  B  ▲  (10%) ████████████████░░░░
DATA    70/100  C  →  (12%) ██████████████░░░░░░
INFRA   88/100  B  ▲  (10%) █████████████████░░░
PERF    82/100  B  →  ( 8%) ████████████████░░░░
COMP    90/100  A  →  ( 6%) ██████████████████░░

OVERALL: 74/100  C  ▼-3
NOT PRODUCTION READY (needs overall >= 80 AND full evidence coverage)

Trend driver: Security dropped 8pts (new hardcoded credential found)
Top fix: Remove API key from config.py:23 → +8pts estimated
```

## Rules for Score Mode

- Prioritize SPEED — 30 second hard budget
- Use lightweight tool invocations (--statistics, --quiet flags)
- No correlation engine (adds no value to a number)
- No compliance mapping (adds no value to a number)
- Always show trend if baseline exists
- Always show the #1 action to improve score
- Bar chart visualization makes cluster strengths/weaknesses obvious at a glance
