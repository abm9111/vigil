# VIGIL Cluster: API & Networking

**Covers:** REST/GraphQL design, endpoint patterns, client-side networking, error handling
**Weight:** 10%
**ID prefix:** VIGIL-API

## Deterministic Tools

### Endpoint Discovery

```bash
# FastAPI/Flask routes (Python)
grep -rn --include='*.py' -E '@(app|router)\.(get|post|put|delete|patch|options|head)\(' . \
  --exclude-dir={.venv,node_modules,.git,tests} 2>/dev/null

# Express routes (JS/TS)
grep -rn --include='*.js' --include='*.ts' -E '\.(get|post|put|delete|patch|all)\s*\(' . \
  --exclude-dir={node_modules,.git,dist,tests} 2>/dev/null

# Next.js API routes
find . -path '*/api/*' -name '*.ts' -o -name '*.js' | grep -v node_modules | grep -v .git 2>/dev/null

# OpenAPI/Swagger spec
find . -name 'openapi*' -o -name 'swagger*' | grep -v node_modules 2>/dev/null
```

### Request/Response Patterns

```bash
# Missing input validation
grep -rn --include='*.py' -E 'request\.(json|form|args|data)\[' . \
  --exclude-dir={.venv,node_modules,.git} 2>/dev/null

# Direct dict access without validation (no Pydantic model)
grep -rn --include='*.py' -E 'await request\.json\(\)|request\.get_json\(\)' . \
  --exclude-dir={.venv,node_modules,.git} 2>/dev/null

# PII in response (email, phone, SSN patterns)
grep -rn --include='*.py' --include='*.ts' -E '"(email|phone|ssn|password|credit_card|address)"' . \
  --exclude-dir={.venv,node_modules,.git,tests} 2>/dev/null

# Error responses exposing internals
grep -rn --include='*.py' -E 'traceback|str\(e\)|repr\(e\)|exception.*detail' . \
  --exclude-dir={.venv,node_modules,.git,tests} 2>/dev/null
```

### Rate Limiting & Throttling

```bash
# Rate limiter presence
grep -rn -E 'rate.?limit|throttl|slowapi|express-rate-limit|RateLimiter' . \
  --exclude-dir={node_modules,.venv,.git} 2>/dev/null

# Health/readiness endpoints
grep -rn --include='*.py' --include='*.ts' -E '/(health|ready|alive|ping|status)' . \
  --exclude-dir={node_modules,.venv,.git} 2>/dev/null
```

## Finding Patterns

### API Design (VIGIL-API-0xx)

| Pattern | Severity |
|---------|----------|
| No input validation (raw dict access) | HIGH |
| PII in response body without need | MEDIUM |
| Internal errors exposed to client (tracebacks) | MEDIUM |
| No pagination on list endpoints | MEDIUM |
| Inconsistent response format | LOW |
| No API versioning | LOW |
| Missing Content-Type headers | LOW |

### Rate Limiting (VIGIL-API-1xx)

| Pattern | Severity |
|---------|----------|
| No rate limiting on any endpoint | HIGH |
| No rate limiting on auth endpoints | MEDIUM |
| No rate limiting on resource-intensive endpoints | MEDIUM |

### Client Patterns (VIGIL-API-2xx)

| Pattern | Severity |
|---------|----------|
| No timeout on HTTP client requests | HIGH |
| No retry logic for external API calls | MEDIUM |
| Hardcoded external URLs | LOW |
| No circuit breaker for downstream services | MEDIUM |
| SSL verification disabled | CRITICAL |

### Health & Observability (VIGIL-API-3xx)

| Pattern | Severity |
|---------|----------|
| No health endpoint | MEDIUM |
| No readiness probe | MEDIUM |
| No request ID propagation | LOW |
| No request logging/tracing | MEDIUM |

## AI Reasoning Section

1. **Endpoint inventory:** Create a complete map of all routes with their HTTP methods, auth requirements, and input/output types.
2. **Data flow:** Trace user input from endpoint → handler → database. Identify unvalidated paths.
3. **Error handling:** Are errors handled consistently? Do any leak internal state?
4. **API surface area:** Is the API surface minimal? Any endpoints that expose more than needed?
5. **Client resilience:** For outbound HTTP calls, what happens when the remote service is down?
