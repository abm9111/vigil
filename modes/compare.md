# VIGIL Mode: Compare

**Time budget:** 2-5 minutes
**Depth:** Side-by-side comparison of two states
**Loads:** ALL clusters + scoring engine
**Purpose:** Branch comparison, PR review, before/after assessment

## Execution

### Step 1: Determine Comparison Points (5s)

Resolve what to compare:

```bash
# Default: current branch vs main
git diff --stat main...HEAD 2>/dev/null

# With --baseline: current vs saved baseline
# With explicit args: /vigil compare branch-a branch-b
```

| Input | Left Side | Right Side |
|-------|-----------|------------|
| No args | `main` | Current HEAD |
| `--baseline` | `.vigil/baseline.json` | Current state |
| `branch-a branch-b` | `branch-a` | `branch-b` |
| `commit-a commit-b` | `commit-a` | `commit-b` |

### Step 2: Score Both Sides (1-3min)

Run score mode (fast cluster scoring) on both comparison points:

**For branch comparison:**
```bash
# Score current state
# (run cluster tools on current working tree)

# Score comparison branch
git stash
git checkout {compare_branch} --quiet
# (run cluster tools)
git checkout - --quiet
git stash pop
```

**For baseline comparison:**
- Left side: load from `.vigil/baseline.json`
- Right side: run score mode on current state

### Step 3: Compute Deltas (30s)

For each cluster:
- Score delta (e.g., Security: 65→72 = +7)
- New findings (in right, not in left)
- Fixed findings (in left, not in right)
- Regressed findings (fixed in left, back in right)
- Changed severity (same finding, different severity)

### Step 4: Merge Recommendation (10s)

Based on deltas, provide a merge recommendation.

## Output Template

```
VIGIL compare — {left_label} → {right_label}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                {left_label}    {right_label}    Delta
SEC              65/100 D        72/100 C        +7  ▲
CODE             85/100 B        85/100 B         0  →
API              80/100 B        78/100 C        -2  ▼
DATA             70/100 C        75/100 C        +5  ▲
INFRA            88/100 B        90/100 A        +2  ▲

OVERALL:         74/100 C        78/100 C        +4  ▲

━━━ New Findings ({count}) ━━━
VIGIL-SEC-008  MEDIUM  New endpoint /api/export lacks rate limiting  src/api.py:142

━━━ Fixed Findings ({count}) ━━━
VIGIL-SEC-001  HIGH    Removed hardcoded API key  config.py:23

━━━ Regressions ({count}) ━━━
{none, or list}

━━━ Merge Recommendation ━━━
{RECOMMEND MERGE | MERGE WITH CAVEATS | BLOCK MERGE}

{reasoning — 1-3 sentences}
{if caveats: specific items to address}
```

## Merge Recommendation Logic

| Condition | Recommendation |
|-----------|---------------|
| Overall score improved, no new CRITICAL/HIGH | RECOMMEND MERGE |
| Overall score improved, new MEDIUM only | MERGE WITH CAVEATS |
| Any new CRITICAL | BLOCK MERGE |
| New HIGH findings | BLOCK MERGE (or CAVEATS if --lenient) |
| Score regressed >5 points | MERGE WITH CAVEATS |
| Score regressed >15 points | BLOCK MERGE |

## Rules for Compare Mode

- Both sides must be scored with identical tool versions and configs
- Delta is always RIGHT - LEFT (positive = improvement)
- Never compare across major refactors (too noisy) — warn user if >100 files changed
- Show ONLY meaningful deltas — if a cluster didn't change, collapse to one line
- Merge recommendation must be actionable (not just "needs review")
