# VIGIL Cluster: Code Health

**Covers:** Linting, type safety, testing, coverage, git hygiene, developer experience
**Weight:** 10% (authoritative source: engines/scoring.md)
**ID prefix:** VIGIL-CODE

## Deterministic Tools

### Python

```bash
# Lint — all rules, statistics summary
ruff check . --statistics 2>&1

# Format check (dry run)
ruff format --check --diff . 2>&1

# Type checking — strict mode
mypy . --strict --no-error-summary 2>&1

# Dead code detection
vulture . --min-confidence 80 2>&1 || true

# Complexity
ruff check . --select C90 --statistics 2>&1
```

### JavaScript / TypeScript

```bash
# Type checking
npx tsc --noEmit 2>&1

# Lint
npx eslint . --format compact 2>&1

# Format check
npx prettier --check "**/*.{js,ts,jsx,tsx}" 2>&1 | tail -20
```

### Go

```bash
go vet ./... 2>&1
staticcheck ./... 2>&1
```

### Rust

```bash
cargo clippy -- -W clippy::all 2>&1
```

### Universal

```bash
# Test suite (with timeout)
pytest tests/ -v --timeout=60 --tb=short 2>&1 || npm test 2>&1 || go test ./... 2>&1

# Coverage (Python)
pytest --cov --cov-report=term-missing --cov-fail-under=0 2>&1

# Coverage (JS/TS)
npx vitest run --coverage 2>&1 || npx jest --coverage 2>&1
```

## Finding Patterns

### Lint Violations (VIGIL-CODE-0xx)

| Pattern | Severity | Auto-fix |
|---------|----------|----------|
| Syntax error (E999, parse error) | CRITICAL | No |
| Undefined name (F821) | HIGH | No |
| Unused import (F401) | LOW | Yes (`ruff --fix`) |
| Line too long (E501) | INFO | Yes (format) |
| Complexity >15 (C901) | MEDIUM | No |
| Unused variable (F841) | LOW | Yes |

### Type Safety (VIGIL-CODE-1xx)

| Pattern | Severity |
|---------|----------|
| `Any` type used explicitly | MEDIUM |
| Missing return type on public function | LOW |
| Type: ignore without explanation | MEDIUM |
| TypeScript `as any` cast | MEDIUM |
| Incompatible types in assignment | HIGH |

### Testing (VIGIL-CODE-2xx)

| Pattern | Severity |
|---------|----------|
| No test files found | HIGH |
| Test suite fails | CRITICAL |
| Coverage < 50% | HIGH |
| Coverage 50-79% | MEDIUM |
| Coverage 80-89% | LOW |
| No integration tests | MEDIUM |
| Flaky test (passes/fails inconsistently) | MEDIUM |

### Git Hygiene (VIGIL-CODE-3xx)

| Pattern | Severity | Check |
|---------|----------|-------|
| Merge conflict markers in code | CRITICAL | `grep -rn '<<<<<<<\|>>>>>>>' --include='*.py' --include='*.ts'` |
| Large binary in git | MEDIUM | `git ls-files --others --exclude-standard \| xargs file \| grep -i binary` |
| No .gitignore | LOW | File existence check |
| Uncommitted changes in CI | INFO | `git status --porcelain` |

### Developer Experience (VIGIL-CODE-4xx)

| Pattern | Severity |
|---------|----------|
| No README.md | LOW |
| No setup/install instructions | LOW |
| No .env.example when .env exists | MEDIUM |
| Lock file out of sync with manifest | HIGH |
| Circular imports | HIGH |

## AI Reasoning Section

After running deterministic tools, apply AI reasoning:

1. **Hotspot analysis:** Which files have the most findings? These are maintenance risks.
2. **Pattern detection:** Are lint violations clustered in specific modules? (suggests rushed code)
3. **Coverage gaps:** Which critical paths have no test coverage? (trace from API endpoints)
4. **Complexity assessment:** Are complex functions also untested? (dangerous combination)
5. **Dependency health:** Are core dependencies maintained? (check last release date)
