# VIGIL Domain Detail: GraphQL Security & Patterns

**Parent cluster:** api
**Loaded in:** siege mode, or --only api --deep

## Deep Checks

### Query Depth Limiting

```bash
# Check if depth limiting middleware is configured
grep -rn "depthLimit\|depth_limit\|maxDepth\|max_depth" src/ --include="*.ts" --include="*.py" --include="*.js"

# graphql-depth-limit (Node.js)
grep -rn "graphqlDepthLimit\|depthLimit(" src/
# graphene (Python)
grep -rn "GRAPHQL_MAX_DEPTH\|max_depth" src/

# If absent, test manually: nested query attack
# { user { friends { friends { friends { friends { id name } } } } } }
# Unlimited depth = DoS vector
```

### Query Cost Analysis

```bash
# Check for cost/complexity analysis
grep -rn "costAnalysis\|cost_analysis\|queryComplexity\|query_complexity" src/ --include="*.ts" --include="*.py"
grep -rn "graphql-cost-analysis\|graphql-query-complexity" package.json

# Python graphene: check for complexity limits
grep -rn "GRAPHQL_MAX_COMPLEXITY\|MAX_QUERY_COMPLEXITY" src/ --include="*.py"

# Test for expensive query:
# { users { posts { comments { author { posts { comments { ... } } } } } } }
# Without cost analysis, this can consume unbounded DB resources
```

| Protection | Implementation | Severity if Missing |
|-----------|---------------|-------------------|
| Depth limit | `graphql-depth-limit`, max 5-7 | CRITICAL |
| Complexity limit | `graphql-query-complexity`, max 100-500 | HIGH |
| Query timeout | Server-level, 5-10s | HIGH |
| Rate limiting on query cost | Redis counter per token | MEDIUM |

### N+1 Detection with DataLoader

```bash
# Check DataLoader usage (Node.js)
grep -rn "DataLoader\|dataloader" src/ --include="*.ts" --include="*.js" | wc -l
grep -rn "new DataLoader(" src/ | wc -l

# Python: check for dataloader/strawberry loaders
grep -rn "DataLoader\|load_many\|batch_load" src/ --include="*.py" | wc -l

# Find resolvers that may cause N+1 (DB calls inside loops)
grep -rn "async resolve\|async def resolve_" src/ | wc -l
grep -B2 -A10 "async def resolve_" src/ --include="*.py" | grep -c "\.filter\|\.get\|await db"

# Strawberry (Python): check for lazy loading fields
grep -rn "strawberry.field\|@strawberry.type" src/ --include="*.py" | wc -l
# Each field that does a DB call without DataLoader = N+1 candidate
```

### Introspection in Production

```bash
# Check if introspection is disabled in production config
grep -rn "introspection\|ENABLE_INTROSPECTION\|disable_introspection" src/ --include="*.ts" --include="*.py" --include="*.js"

# Apollo Server
grep -rn "introspection: false\|introspection: process.env" src/

# graphene-django / strawberry
grep -rn "GRAPHIQL\|GRAPHQL_INTROSPECTION" src/ --include="*.py" settings.py

# Red flag: introspection enabled without auth check
grep -rn "introspection.*true\|GRAPHIQL.*True" src/ | grep -v "NODE_ENV\|DEBUG\|development"
```

### Field-Level Authorization

```bash
# Check for field-level permission checks
grep -rn "has_permission\|check_permission\|permission_required\|authorize" src/ --include="*.py" --include="*.ts" | wc -l

# Find resolvers WITHOUT authorization checks (fields that just return data)
grep -rn "def resolve_\|async def resolve_" src/ --include="*.py" | wc -l
grep -rn "def resolve_.*permission\|def resolve_.*auth\|def resolve_.*check" src/ --include="*.py" | wc -l
# If total resolvers >> authorized resolvers: field auth gaps exist

# graphql-shield (Node.js)
grep -rn "graphql-shield\|createRateLimitRule\|shield(" src/ --include="*.ts"
```

### Batching Attacks

```bash
# Check for query batching protection
grep -rn "batchRequests\|batch.*enabled\|allowBatchedHttpRequests" src/

# Without limits, attacker sends array of 1000 queries in one HTTP request:
# [{"query": "mutation login..."}, {"query": "mutation login..."}, ...]

# Check for max batch size
grep -rn "maxBatchSize\|max_batch_size\|GRAPHQL_MAX_BATCH" src/

# Alias attack protection (sending same mutation 100x with different aliases)
grep -rn "aliasLimit\|alias_limit\|MAX_ALIASES" src/
```

### Persisted Queries

```bash
# Check if persisted queries / automatic persisted queries (APQ) are configured
grep -rn "persistedQueries\|persisted_queries\|APQ\|PersistedQueryNotFound" src/
grep -rn "createPersistedQueryLink\|usePersistedQuery" src/ --include="*.ts"

# Persisted queries: only whitelisted query hashes allowed in production
# Without it: any arbitrary query string accepted = full attack surface
grep -rn "allowArbitraryQueries\|allow_arbitrary" src/  # red flag if true in prod
```

### Schema Stitching Security

```bash
# Check for schema stitching / federation
grep -rn "stitchSchemas\|makeExecutableSchema\|buildSubgraphSchema" src/ --include="*.ts"
grep -rn "federation\|subgraph\|gateway" src/ --include="*.ts" --include="*.py"

# Federation: check for @external fields that bypass local auth
grep -rn "@external\|@requires\|@provides" src/ | head -20

# Remote schema fetching: check if upstream schemas are trusted
grep -rn "buildClientSchema\|introspectSchema" src/ --include="*.ts"
# Remote schemas should be validated — malicious upstream can inject fields
```

## Advanced Patterns

### GraphQL Security Checklist

| Check | Tool/Pattern | Status Signal |
|-------|-------------|---------------|
| Depth limiting | `graphql-depth-limit` | Present in middleware |
| Cost limiting | `graphql-query-complexity` | Present with threshold |
| Introspection off in prod | Config check | `introspection: false` unless dev |
| DataLoader for all N+1 | Loader per entity | No raw DB calls in resolvers |
| Field auth on sensitive fields | graphql-shield / decorators | Rule for every mutation |
| Persisted queries | APQ or allowlist | Hash-based query registry |
| Rate limiting | Per-token cost bucket | Redis counter |

### Error Information Leakage

```bash
# Check if stack traces are exposed in GraphQL errors
grep -rn "formatError\|format_error\|extensions.*exception" src/ --include="*.ts" --include="*.py"

# In production, errors should be sanitized:
# Bad: { "message": "column users.password does not exist" }
# Good: { "message": "Internal server error", "extensions": { "code": "INTERNAL" } }
grep -rn "stacktrace\|stack_trace\|debug.*true" src/ | grep -v "test\|spec"
```
