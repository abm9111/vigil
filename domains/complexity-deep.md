# VIGIL Domain Detail: Code Complexity

**Parent cluster:** maintainability
**Loaded in:** siege mode, or --only maintainability --deep

## Deep Checks

### Cyclomatic Complexity Hotspots

```bash
# Python: radon cyclomatic complexity
pip install radon
radon cc src/ -s -n C    # show functions with grade C or worse (CC >= 10)
radon cc src/ -s -n F    # grade F (CC >= 25) = critical
radon cc src/ --json | jq '[.[] | .[] | select(.complexity >= 10)] | sort_by(-.complexity) | .[0:10]'

# JavaScript/TypeScript: complexity-report or eslint
npx eslint src/ --rule '{"complexity": ["error", {"max": 10}]}' --format=compact

# Per-file summary
radon cc src/ -a -s  # average CC per file, sorted
```

### Cognitive Complexity

```bash
# Python: wily for cognitive complexity (Halstead + MI + CC)
pip install wily
wily build src/
wily report src/ --metrics cognitive_complexity
wily diff HEAD~5  # complexity change over last 5 commits

# SonarQube cognitive complexity via sonar-scanner (if configured)
# JS/TS: @typescript-eslint/eslint-plugin complexity rules
npx eslint --rule '{"@typescript-eslint/no-explicit-any": "error"}' --format=json src/
```

| CC Score | Grade | Action |
|----------|-------|--------|
| 1-5 | A | Fine |
| 6-10 | B | Monitor |
| 11-15 | C | Refactor target |
| 16-25 | D | High priority |
| 25+ | F | Critical — block merge |

### Coupling Metrics (Afferent/Efferent)

```bash
# Python: pydeps for dependency graph
pip install pydeps
pydeps src/ --noshow --max-bacon 3 --output coupling.svg

# Count imports (efferent coupling = number of modules this one depends on)
for f in $(find src/ -name "*.py"); do
  count=$(grep -c "^import\|^from" "$f" 2>/dev/null || echo 0)
  echo "$count $f"
done | sort -rn | head -20

# TypeScript: madge for dependency graph
npx madge --circular src/           # circular dependencies
npx madge --summary src/            # per-file dependency count
npx madge src/ --json | jq 'to_entries | sort_by(-.value | length) | .[0:10]'
```

### Churn-Complexity Correlation

```bash
# Files that change frequently AND are complex = highest refactor priority
# Step 1: get churn (commits per file, last 90 days)
git log --since="90 days ago" --name-only --format="" | sort | uniq -c | sort -rn | head -30

# Step 2: get complexity for those files
# Cross-reference top churned files with CC scores from radon
git log --since="90 days ago" --name-only --format="" \
  | sort | uniq -c | sort -rn | head -20 \
  | awk '{print $2}' | xargs radon cc -s 2>/dev/null | grep -E "[CD-F]"

# Composite risk: files with churn > 10 AND CC > 10 = immediate refactor candidates
```

### Dead Code Analysis

```bash
# Python: vulture for dead code
pip install vulture
vulture src/ --min-confidence 80
vulture src/ --make-whitelist  # generate whitelist for intentional dead code

# TypeScript: ts-prune for unused exports
npx ts-prune --error   # exit 1 if unused exports found
npx ts-prune | grep -v "(used in module)"

# General: find functions defined but never called
grep -rn "^def " src/ --include="*.py" | awk -F: '{print $3}' | awk '{print $2}' \
  | while read fn; do
      count=$(grep -rn "\b${fn}\b" src/ | wc -l)
      [ "$count" -eq 1 ] && echo "DEAD: $fn"
    done
```

### Dependency Graph Cycles

```bash
# Python: detect circular imports
python -c "
import importlib, sys
# Attempt to import each module and catch circular import errors
"

# Better: use pydeps
pydeps src/ --noshow --show-cycles

# TypeScript: madge circular detection
npx madge --circular --extensions ts src/
npx madge --circular --extensions ts src/ | wc -l  # count circular paths

# Node.js runtime circular detection
node -e "require('./src/index'); console.log('No circular imports')" 2>&1 | grep -i "circular"
```

## Advanced Patterns

### Complexity Debt Heatmap

Run this to get a single ranked list of worst offenders across all dimensions:

```bash
# Python project complexity report
radon cc src/ --json > /tmp/cc.json
radon mi src/ --json > /tmp/mi.json
git log --since="90 days ago" --name-only --format="" | sort | uniq -c > /tmp/churn.txt

python3 -c "
import json
cc = json.load(open('/tmp/cc.json'))
# Flatten and sort by complexity
results = []
for f, fns in cc.items():
    for fn in fns:
        results.append((fn['complexity'], f, fn['name']))
results.sort(reverse=True)
for c, f, n in results[:20]:
    print(f'CC={c:3d}  {f}:{n}')
"
```

### Structural Anti-Patterns

| Pattern | Detection | Severity |
|---------|-----------|----------|
| God class (>500 LOC, >15 methods) | `wc -l` + method count | HIGH |
| Long parameter list (>5 params) | `radon` + grep | MEDIUM |
| Deep nesting (>4 levels) | indent analysis | HIGH |
| Shotgun surgery (change spreads across >10 files) | git diff stats | HIGH |
| Feature envy (method uses another class's data more than own) | manual/linting | MEDIUM |
