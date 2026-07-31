# VIGIL Domain Detail: REST API Patterns

**Parent cluster:** api
**Loaded in:** siege mode, or --only api --deep

## Deep Checks

### Resource Naming Consistency

```bash
# Find route definitions and check naming conventions
grep -rn "@app\.\(get\|post\|put\|patch\|delete\)\|router\.\(get\|post\|put\|patch\|delete\)" src/ \
  | grep -oP '["'"'"'][/][^"'"'"']+["'"'"']' | sort | uniq

# Python FastAPI / Flask
grep -rn "@router\.\|@app\." src/ --include="*.py" | grep -oP '"[/][^"]+"' | sort

# Checks to run manually on output:
# - Mixed plural/singular?  /user vs /users
# - Verb in URL?  /getUser, /createOrder (bad)
# - Nested more than 2 levels deep?  /a/b/c/d (bad)
# - camelCase vs kebab-case inconsistency?
```

| Anti-Pattern | Example | Fix |
|-------------|---------|-----|
| Verb in resource name | `GET /getUsers` | `GET /users` |
| Mixed plurality | `GET /user` + `GET /orders` | Consistent plural |
| Deep nesting | `GET /users/1/orders/2/items/3` | `GET /order-items?orderId=2` |
| Non-noun action | `POST /users/activate` | `PATCH /users/{id}` with `{status: active}` |

### HTTP Method Correctness

```bash
# Find GET routes that might be mutating state (should be POST/PUT/PATCH)
grep -rn 'GET.*creat\|GET.*delet\|GET.*updat\|GET.*remov' src/ -i --include="*.py" --include="*.ts"

# Find POST routes that might be safe reads (should be GET)
grep -rn 'POST.*search\|POST.*list\|POST.*get\|POST.*fetch' src/ -i --include="*.py" --include="*.ts"

# Find PUT vs PATCH usage (PUT = full replace, PATCH = partial update)
grep -rn "@router\.put\|@app\.put\|router\.put(" src/ --include="*.py" --include="*.ts"
# Audit: PUT handlers should replace the entire resource, not patch fields
```

### Status Code Usage

```bash
# Python FastAPI: find all status_code= usages
grep -rn "status_code=" src/ --include="*.py" | grep -oP "status_code=\K[0-9]+" | sort | uniq -c

# Express/Next.js: find res.status() calls
grep -rn "res\.status(" src/ --include="*.ts" | grep -oP "status\(\K[0-9]+" | sort | uniq -c

# Anti-patterns to look for:
grep -rn "status_code=200" src/ --include="*.py" | grep -i "creat"   # CREATE should be 201
grep -rn "status_code=200" src/ --include="*.py" | grep -i "delet"   # DELETE should be 204
grep -rn "raise HTTPException.*404" src/ --include="*.py"            # correct NOT FOUND
grep -rn "raise HTTPException.*500" src/ --include="*.py" | wc -l    # manual 500s (bad — let middleware handle)
```

| Scenario | Correct Code | Common Mistake |
|----------|-------------|----------------|
| Resource created | 201 | 200 |
| Async job accepted | 202 | 200 |
| Successful DELETE | 204 | 200 |
| Validation error | 422 | 400 or 500 |
| Auth missing | 401 | 403 |
| Auth present but forbidden | 403 | 401 |
| Rate limited | 429 | 503 |

### Pagination Implementation

```bash
# Check pagination patterns: cursor vs offset
grep -rn "offset\|skip\|page=" src/ --include="*.py" --include="*.ts" | head -20
grep -rn "cursor\|after\|before=" src/ --include="*.py" --include="*.ts" | head -20

# Verify pagination has a max limit (no unbounded queries)
grep -rn "limit=" src/ --include="*.py" | grep -v "max\|default\|min"
grep -B5 -A5 "limit" src/ --include="*.py" | grep -v "max_limit\|MAX_LIMIT" | head -30

# Check if total_count is returned (required for offset pagination UX)
grep -rn "total\|count\|X-Total-Count" src/ --include="*.py" --include="*.ts" | head -10
```

### Filtering and Sorting

```bash
# Find query parameter handling — check for SQL injection vectors
grep -rn "request\.args\|query_params\|request\.query" src/ --include="*.py" --include="*.ts"
# Each should go through validation (Pydantic QueryParams / Zod) before DB

# Check if sort fields are whitelisted (SQL injection via sort= is common)
grep -rn "sort_by\|order_by\|sortField" src/ --include="*.py" --include="*.ts" | head -20
grep -B3 "order_by" src/ --include="*.py" | grep "whitelist\|ALLOWED\|choices\|Literal"
```

### Idempotency Keys

```bash
# Check if POST/PUT handlers accept Idempotency-Key header
grep -rn "Idempotency-Key\|idempotency_key\|idempotencyKey" src/ --include="*.py" --include="*.ts"

# Payment and order creation endpoints MUST have idempotency
grep -rn "payment\|order\|charge\|transfer" src/ --include="*.py" | grep -i "post\|create" | head -20
# Cross-check those files for idempotency key handling
```

### Request/Response Schema Validation

```bash
# Python FastAPI: check all routes have response_model
grep -rn "@router\.\|@app\." src/ --include="*.py" | grep -v "response_model=" | grep -c "def "
# Any route without response_model leaks internal fields

# Check if request bodies are validated (not raw dict)
grep -rn "request\.json()\|await request\.body()" src/ --include="*.py" | wc -l
# These bypass Pydantic validation — should use typed body parameter instead

# TypeScript: check if request bodies are typed
grep -rn "req\.body\b" src/ --include="*.ts" | grep -v ": " | head -10  # untyped body access
```

## Advanced Patterns

### HATEOAS and Content Negotiation

```bash
# Check for HATEOAS links in responses
grep -rn '"links"\|"_links"\|"href"\|"rel"' src/ --include="*.py" --include="*.ts" | head -10

# Content negotiation
grep -rn "Accept\|Content-Type\|content_type" src/ --include="*.py" | grep -v "#" | head -10
grep -rn "application/json\|application/xml\|text/csv" src/ --include="*.py" | head -10
```

### API Versioning

```bash
# Check versioning strategy
grep -rn '"/v1/\|"/v2/\|/api/v' src/ --include="*.py" --include="*.ts" | head -10
grep -rn "Accept-Version\|API-Version\|X-API-Version" src/ | head -10

# Preferred: URL prefix (/v1/) or header (Accept: application/vnd.api+json;version=1)
# Avoid: query param versioning (?version=1) — breaks caching
```
