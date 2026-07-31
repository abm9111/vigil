# VIGIL Domain Detail: Testing Strategy

**Parent cluster:** quality
**Loaded in:** siege mode, or --only quality --deep

## Deep Checks

### Test Pyramid Balance

```bash
# Count test types by directory/naming convention
find . -type f -name "*.test.*" -o -name "*.spec.*" | xargs grep -l "describe\|it(" | wc -l
find . -path "*/e2e/*" -o -path "*/integration/*" | wc -l

# Python: count unit vs integration vs e2e
grep -r "def test_" tests/unit/ | wc -l
grep -r "def test_" tests/integration/ | wc -l
grep -r "def test_" tests/e2e/ | wc -l

# JS/TS: identify test layers by import depth
grep -rn "supertest\|axios\|fetch" **/*.test.ts | wc -l   # integration signal
grep -rn "playwright\|cypress\|puppeteer" **/*.spec.ts | wc -l  # e2e signal
```

Ideal pyramid ratio: **70% unit / 20% integration / 10% e2e**. Inversion (more e2e than unit) signals slow, brittle suites.

### Mutation Testing

```bash
# JavaScript: Stryker
npx stryker run --reporters json
cat reports/mutation/mutation.json | jq '.mutationScore'

# Python: mutmut
mutmut run --paths-to-mutate src/
mutmut results
mutmut show   # show surviving mutants (code not tested for behavior)

# Threshold: mutation score < 60% = tests pass but don't verify behavior
```

### Property-Based Testing

```bash
# Check if property-based testing is in use
grep -r "hypothesis\|fast-check\|quickcheck\|jsverify" . --include="*.py" --include="*.ts"

# Python: hypothesis coverage check
grep -rn "@given\|@settings\|@example" tests/
```

| Signal | Meaning | Severity |
|--------|---------|----------|
| No property tests on parsers/serializers | Edge cases untested | HIGH |
| No property tests on financial calculations | Correctness risk | CRITICAL |
| Hypothesis strategies use only fixed examples | Defeats purpose | MEDIUM |

### Test Isolation

```bash
# Detect shared mutable state in tests
grep -rn "global\|module.exports\s*=" tests/ --include="*.js"
grep -rn "^[A-Z_]+ =" tests/ --include="*.py"  # module-level globals

# Detect missing teardown
grep -rn "beforeAll\|setUp" tests/ | wc -l
grep -rn "afterAll\|tearDown" tests/ | wc -l
# If beforeAll >> afterAll, teardown is missing

# Database test isolation
grep -rn "transaction\|rollback\|truncate" tests/conftest.py tests/fixtures/
```

### Flaky Test Detection

```bash
# Re-run tests N times to surface flakiness
pytest --count=5 tests/ -x  # pytest-repeat plugin
npx jest --testNamePattern="flaky" --runInBand --forceExit

# Grep for known flakiness signals
grep -rn "sleep\|time.sleep\|setTimeout\|setInterval" tests/
grep -rn "Date.now\|datetime.now\|time.time" tests/   # time-dependent tests
grep -rn "random\." tests/ --include="*.py"           # non-seeded randomness
```

### Fixture Management

```bash
# Python: audit fixture scope vs usage
grep -rn "@pytest.fixture" tests/ | grep -v "scope=" | wc -l  # no scope = function scope (default)
grep -rn 'scope="module"' tests/ | wc -l
grep -rn 'scope="session"' tests/ | wc -l

# JS: detect fixture duplication across test files
grep -rn "beforeEach.*createUser\|beforeEach.*mockDB" tests/ | wc -l
```

### Coverage Gap Analysis

```bash
# Python: branch coverage with missing lines
pytest --cov=src --cov-report=term-missing --cov-branch
coverage report --skip-covered --show-missing | head -40

# JS/TS
npx jest --coverage --coverageReporters=text-summary
npx c8 report --reporter=text --include="src/**"

# Find uncovered critical paths (error handlers, auth checks)
grep -rn "except\|catch\|raise\|throw" src/ | wc -l
coverage report --include="src/*" | grep " 0%" | grep -v test
```

## Advanced Patterns

### Test Data Management

| Pattern | Good Signal | Bad Signal |
|---------|-------------|------------|
| Factory pattern (factory_boy, fishery) | Explicit, composable test data | Hardcoded fixtures with magic values |
| DB seeding via migrations | Reproducible state | Shared test DB between runs |
| Snapshot testing for API responses | Regression detection | Committed snapshots never reviewed |

### Detected Anti-Patterns

- **`time.sleep()` in tests** — non-deterministic, use event/polling instead
- **Tests that test mocks** — mocking everything means testing nothing real
- **Test names without "should"/"when"** — signals poor BDD discipline
- **Shared DB state across test classes** — `session`-scoped fixtures on write operations
- **`assert True`** — placeholder test that always passes, falsely inflates coverage
