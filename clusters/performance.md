# VIGIL Cluster: Performance

**Covers:** Runtime performance, concurrency, resource usage, caching, query efficiency
**Weight:** 8%
**ID prefix:** VIGIL-PERF

## Deterministic Tools

### Concurrency & Async Patterns

```bash
# Sync operations in async context (Python)
grep -rn --include='*.py' -E 'def\s+\w+.*async|await' . \
  --exclude-dir={.venv,node_modules,.git,tests} 2>/dev/null > /tmp/vigil_async_funcs.txt
grep -rn --include='*.py' -E 'time\.sleep\(|requests\.(get|post|put)|open\(' . \
  --exclude-dir={.venv,node_modules,.git,tests} 2>/dev/null > /tmp/vigil_sync_calls.txt
# Cross-reference: sync calls in async-heavy files

# Thread safety
grep -rn --include='*.py' -E 'global\s+\w|threading\.Thread|multiprocessing' . \
  --exclude-dir={.venv,node_modules,.git} 2>/dev/null

# Blocking operations in event loop (Node.js)
grep -rn --include='*.ts' --include='*.js' \
  -E 'fs\.(read|write)FileSync|execSync|spawnSync' . \
  --exclude-dir={node_modules,.git,dist} 2>/dev/null
```

### Resource Usage

```bash
# Unbounded collections (memory leaks)
grep -rn --include='*.py' -E '\.append\(|\.extend\(' . \
  --exclude-dir={.venv,node_modules,.git,tests} 2>/dev/null | head -20

# Large file reads without streaming
grep -rn --include='*.py' -E '\.read\(\)|\.readlines\(\)|json\.load\(' . \
  --exclude-dir={.venv,node_modules,.git,tests} 2>/dev/null

# Missing connection/resource cleanup
grep -rn --include='*.py' -E 'open\(|connect\(|create_engine\(' . \
  --exclude-dir={.venv,node_modules,.git,tests} 2>/dev/null
grep -rn --include='*.py' -E '\.close\(\)|with\s+open|contextmanager|__exit__' . \
  --exclude-dir={.venv,node_modules,.git,tests} 2>/dev/null
```

### Query Performance

```bash
# N+1 query indicators
grep -rn --include='*.py' -E 'for.*in.*\.all\(\)|for.*in.*\.filter\(' . \
  --exclude-dir={.venv,node_modules,.git,tests} 2>/dev/null

# Missing pagination
grep -rn --include='*.py' -E '\.all\(\)|\.find\(\{?\}?\)' . \
  --exclude-dir={.venv,node_modules,.git,tests} 2>/dev/null

# SELECT * patterns
grep -rn --include='*.py' -iE "select\s+\*\s+from" . \
  --exclude-dir={.venv,node_modules,.git,tests} 2>/dev/null
```

### Caching

```bash
# Cache usage
grep -rn -E 'redis|memcache|@cache|lru_cache|functools\.cache|cachetools' . \
  --exclude-dir={node_modules,.venv,.git} 2>/dev/null

# Cache invalidation
grep -rn -E 'cache\.(delete|invalidate|clear|flush)|\.cache_clear\(' . \
  --exclude-dir={node_modules,.venv,.git} 2>/dev/null
```

## Finding Patterns

### Concurrency (VIGIL-PERF-0xx)

| Pattern | Severity |
|---------|----------|
| Sync I/O in async context (requests.get in async func) | HIGH |
| time.sleep() in async context | HIGH |
| Global mutable state without locks | HIGH |
| fs.readFileSync in request handler | MEDIUM |
| Thread pool exhaustion risk (unbounded threads) | MEDIUM |
| Missing async/await (fire-and-forget without error handling) | MEDIUM |

### Resource Usage (VIGIL-PERF-1xx)

| Pattern | Severity |
|---------|----------|
| Unbounded list growth in loop | MEDIUM |
| Large file read without streaming (.read() on unknown size) | MEDIUM |
| Missing resource cleanup (no close/context manager) | MEDIUM |
| Memory-intensive operation without limit | HIGH |
| No connection pooling for DB/HTTP | MEDIUM |

### Query Performance (VIGIL-PERF-2xx)

| Pattern | Severity |
|---------|----------|
| N+1 query in loop | HIGH |
| SELECT * without column restriction | LOW |
| No pagination on collection endpoint | MEDIUM |
| Missing database index (detected from slow query patterns) | MEDIUM |
| Unbounded query (no LIMIT) | MEDIUM |

### Caching (VIGIL-PERF-3xx)

| Pattern | Severity |
|---------|----------|
| No caching strategy for read-heavy paths | MEDIUM |
| Cache with no TTL/expiry | MEDIUM |
| Cache without invalidation on write | HIGH |
| Caching sensitive/user-specific data without user key | HIGH |

## AI Reasoning Section

1. **Hot path analysis:** Which code paths handle the most traffic? Are they optimized?
2. **Async audit:** Are all I/O operations properly async? Any sync blockers in the event loop?
3. **Memory profile:** Any patterns that could lead to OOM under load?
4. **Query audit:** For each DB query in a request handler, is it necessary? Can it be batched?
5. **Cache effectiveness:** Is caching applied where it matters most? Any cache stampede risks?
