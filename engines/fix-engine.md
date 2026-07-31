# VIGIL Engine: Auto-Fix

**Purpose:** Automatically fix deterministic, safe issues and re-validate.

## Fix Categories

### Safe to Auto-Fix (no human review needed)

| Category | Tool | Fix Command |
|----------|------|-------------|
| Python lint (fixable) | ruff | `ruff check --fix {files}` |
| Python formatting | ruff | `ruff format {files}` |
| JS/TS lint (fixable) | eslint | `npx eslint --fix {files}` |
| JS/TS formatting | prettier | `npx prettier --write {files}` |
| Unused imports | ruff/eslint | Included in --fix above |
| Import sorting | ruff | `ruff check --select I --fix {files}` |
| Trailing whitespace | ruff | Included in format |
| Missing newline at EOF | ruff | Included in format |
| dotenv formatting | dotenv-linter | `dotenv-linter fix {files}` |

### Requires Confirmation (show diff before applying)

| Category | What | Why |
|----------|------|-----|
| Type annotation addition | Add missing type hints | May change runtime behavior with Pydantic |
| Security fix (simple) | Add `@login_required` decorator | Auth change needs verification |
| Dependency upgrade | `pip install --upgrade {pkg}` | May break API compatibility |
| Docker base image update | Update FROM tag | May change runtime environment |

### Never Auto-Fix (human only)

| Category | Why |
|----------|-----|
| Logic errors | Requires understanding intent |
| Architecture issues | Requires design decisions |
| SQL injection | Fix depends on ORM strategy |
| Business logic validation | Requires domain knowledge |
| Test failures | Need to understand expected behavior |
| Correlated findings | Multi-file changes need holistic review |

## Execution Flow

```
1. Collect all findings with fix_type = "auto" or "confirm"

2. For auto-fixable:
   a. Run fix commands (grouped by tool for efficiency)
   b. Re-run the originating tool to verify fix
   c. If verified: mark as FIXED
   d. If still failing: mark as FIX_FAILED, report to user

3. For confirm-fixable:
   a. Generate the fix diff
   b. Present to user: "Apply this fix? [Y/n]"
   c. If approved: apply and re-validate
   d. If declined: mark as SKIPPED

4. Report summary:
   "Fixed {N} issues automatically. {M} need manual fix. {K} skipped."
```

## Fix Order

Apply fixes in this order to avoid cascading issues:

1. **Formatting** first (ruff format, prettier) — changes whitespace only
2. **Import fixes** (unused imports, sorting) — changes imports only
3. **Lint fixes** (ruff --fix, eslint --fix) — changes code
4. **Re-validate ALL** after all fixes applied

## Re-Validation

After fixes are applied:
1. Re-run ALL tools that had findings (not just the fixed ones)
2. Recompute scores
3. Show before/after comparison:

```
Fix Summary:
  Before: 74/100 C
  After:  82/100 B  (+8)

  Auto-fixed: 14 issues
    - 6 unused imports removed
    - 5 formatting fixes
    - 3 lint violations fixed

  Remaining: 4 issues (manual fix required)
    VIGIL-SEC-003  HIGH    SQL injection in search handler
    VIGIL-DATA-001 HIGH    Missing migration for new column
    VIGIL-API-005  MEDIUM  No rate limit on /api/export
    VIGIL-PERF-002 MEDIUM  N+1 query in user list endpoint
```

## Safety Rules

1. **Never modify test files** unless the finding is IN the test file
2. **Never modify generated files** (migrations, lock files, dist/)
3. **Never fix across file boundaries** (if fix requires changing 2+ files, it's "confirm" category)
4. **Always re-validate** — a fix that introduces new errors is worse than the original finding
5. **Preserve git state** — stage fixes separately so user can review diff
6. **Dry-run first** — with `--fix --dry-run`, show what WOULD be fixed without applying
