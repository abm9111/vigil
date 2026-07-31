# VIGIL Domain Detail: Type Safety

**Parent cluster:** correctness
**Loaded in:** siege mode, or --only correctness --deep

## Deep Checks

### Strict Mode Coverage

```bash
# TypeScript: check tsconfig for strict flags
cat tsconfig.json | jq '.compilerOptions | {strict, noImplicitAny, strictNullChecks, noImplicitReturns, strictFunctionTypes}'

# Python: check mypy config
cat mypy.ini setup.cfg pyproject.toml 2>/dev/null | grep -A5 "\[mypy\]"
grep -r "# type: ignore" src/ | wc -l    # suppression count
grep -r "# type: ignore\[" src/ | wc -l  # narrow suppressions (better)
grep -r "# type: ignore$" src/ | wc -l  # blanket suppressions (worse)
```

### any/unknown Usage

```bash
# TypeScript: any usage
grep -rn ": any" src/ --include="*.ts" --include="*.tsx"
grep -rn "as any" src/ --include="*.ts" --include="*.tsx"
grep -rn "<any>" src/ --include="*.ts" --include="*.tsx"

# unknown is safer than any — check if team uses it
grep -rn ": unknown" src/ --include="*.ts" | wc -l

# Python: Any usage
grep -rn "Any\b" src/ --include="*.py" | grep -v "from typing import"
grep -rn ": Any" src/ --include="*.py"
grep -rn "cast(" src/ --include="*.py"   # explicit casts often hide type issues
```

| Pattern | Severity | Better Alternative |
|---------|----------|--------------------|
| `as any` | HIGH | `as unknown` then narrow |
| `: any[]` | HIGH | `unknown[]` then validate |
| `(x as any).field` | CRITICAL | Type guard + interface |
| `# type: ignore` (blanket) | HIGH | `# type: ignore[attr-defined]` |

### Type Guard Patterns

```bash
# TypeScript: check for type guards
grep -rn "is [A-Z]" src/ --include="*.ts"    # return type `x is Type`
grep -rn "instanceof\|typeof\|in " src/ --include="*.ts" | wc -l

# Check for unguarded JSON.parse (returns any)
grep -rn "JSON\.parse" src/ --include="*.ts"
# Each occurrence should be followed by validation or cast through Zod/type guard
```

### Generic Type Usage

```bash
# TypeScript: overly broad generics
grep -rn "function.*<T>.*: T" src/ --include="*.ts"   # unconstrained generics
grep -rn "<T extends" src/ --include="*.ts" | wc -l   # constrained (good)

# Python: Generic[T] usage
grep -rn "Generic\[" src/ --include="*.py"
grep -rn "TypeVar(" src/ --include="*.py"
```

### Discriminated Unions and Exhaustive Checks

```bash
# TypeScript: look for exhaustive switch patterns
grep -rn "assertNever\|exhaustiveCheck\|never" src/ --include="*.ts"

# Missing exhaustive check pattern:
# switch(action.type) { case 'A': ... case 'B': ... default: ??? }
grep -rn "switch.*\.type" src/ --include="*.ts" | wc -l
grep -rn "assertNever" src/ --include="*.ts" | wc -l
# If switch count >> assertNever count: exhaustive checks missing
```

### Branded Types

```bash
# Check for branded/nominal types (prevents mixing IDs)
grep -rn "__brand\|_brand\|Branded<\|Opaque<\|Nominal<" src/ --include="*.py" --include="*.ts"

# Python: NewType usage (safer than aliases)
grep -rn "NewType(" src/ --include="*.py"
grep -rn "UserId = str\|OrderId = str" src/ --include="*.py"  # bare aliases (bad)
```

### Runtime Type Validation (Pydantic/Zod)

```bash
# Python: Pydantic model coverage
grep -rn "class.*BaseModel" src/ --include="*.py" | wc -l
grep -rn "class.*TypedDict" src/ --include="*.py" | wc -l  # TypedDict = no runtime validation
grep -rn "model_validate\|parse_obj\|from_orm" src/ --include="*.py" | wc -l

# TypeScript: Zod/io-ts/arktype usage
grep -rn "z\.object\|z\.string\|z\.infer" src/ --include="*.ts" | wc -l
grep -rn "\.parse(\|\.safeParse(" src/ --include="*.ts" | wc -l

# Find unvalidated external input (JSON from requests not parsed through Zod/Pydantic)
grep -rn "request\.json\(\)\|req\.body" src/ --include="*.ts" | wc -l
grep -rn "\.parse(\|\.safeParse(" src/ --include="*.ts" | wc -l
# If json() >> parse(): external input bypasses runtime validation
```

### Type-Level Testing

```bash
# TypeScript: type tests with tsd or expect-type
grep -rn "expectTypeOf\|assertType\|expectType" tests/ --include="*.ts"
ls **/*.test-d.ts 2>/dev/null  # .test-d.ts files = type-level tests

# Python: type tests via pytest-mypy-plugins
ls tests/**/*.yml | xargs grep -l "reveal_type\|assert_type" 2>/dev/null
```

## Advanced Patterns

### Type Safety Scorecard

| Check | Green | Yellow | Red |
|-------|-------|--------|-----|
| `strict: true` | Yes | Partial flags | No |
| `any` usages | 0 | <10 | 10+ |
| Blanket `# type: ignore` | 0 | <5 | 5+ |
| External input validated | 100% | >80% | <80% |
| Discriminated unions exhaustive | All | Most | Some |
| Type guards on `unknown` | Consistent | Sometimes | Never |

### Python-Specific Pitfalls

- `dict` instead of `TypedDict` for structured data — no field validation
- `Optional[X]` vs `X | None` — prefer union syntax (Python 3.10+)
- Missing `__all__` in modules — re-exports of `Any` pollute callers
- `cast()` without validation — only cast after a runtime check, not instead of one
