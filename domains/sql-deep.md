# VIGIL Domain Detail: SQL & ORM Patterns

**Parent cluster:** database
**Loaded in:** siege mode, or --only database --deep

## Deep Checks

### N+1 Detection

```bash
# Python SQLAlchemy: detect lazy loading (primary N+1 cause)
grep -rn "lazy=\"select\"\|lazy=True\|lazy=\"dynamic\"" src/ --include="*.py"
grep -rn "relationship(" src/ --include="*.py" | grep -v "lazy=\"joined\"\|lazy=\"subquery\"\|lazy=\"selectin\""

# Django ORM: missing select_related/prefetch_related
grep -rn "\.filter(\|\.all(\|\.get(" src/ --include="*.py" \
  | grep -v "select_related\|prefetch_related" | head -20

# TypeScript Prisma: detect N+1 (accessing relation without include)
grep -rn "findMany\|findFirst\|findUnique" src/ --include="*.ts" \
  | grep -v "include:\|select:" | head -20
# Each result without include: that later accesses a relation = N+1

# TypeORM: detect missing eager/join
grep -rn "find(\|findOne(\|findMany(" src/ --include="*.ts" \
  | grep -v "relations:\|eager:" | head -20
```

### Missing Indexes for Common Queries

```bash
# Find columns used in WHERE/JOIN that likely need indexes
grep -rn "WHERE\|JOIN.*ON\|filter_by(" src/ --include="*.py" --include="*.ts" --include="*.sql" \
  | grep -oP "(?<=WHERE |ON |filter_by\()[a-z_\.]+" | sort | uniq -c | sort -rn | head -20

# Compare against existing indexes in migration files
grep -rn "CREATE INDEX\|add_index\|op\.create_index\|Index(" \
  src/migrations/ alembic/ db/migrate/ --include="*.sql" --include="*.py" --include="*.rb"

# PostgreSQL: find slow queries via pg_stat_statements (if accessible)
psql $DATABASE_URL -c "
  SELECT query, calls, mean_exec_time, rows
  FROM pg_stat_statements
  WHERE mean_exec_time > 100
  ORDER BY mean_exec_time DESC LIMIT 20;"

# Find sequential scans on large tables
psql $DATABASE_URL -c "
  SELECT relname, seq_scan, idx_scan
  FROM pg_stat_user_tables
  WHERE seq_scan > idx_scan AND n_live_tup > 10000
  ORDER BY seq_scan DESC;"
```

| Query Pattern | Index Needed | ORM Equivalent |
|---------------|-------------|----------------|
| `WHERE user_id = ?` | `idx_table_user_id` | `Index('ix', Table.user_id)` |
| `WHERE status = ? AND created_at > ?` | Composite index | `Index('ix', status, created_at)` |
| `ORDER BY created_at DESC` | `idx_table_created_at` | BTree descending |
| `LIKE 'prefix%'` | BTree index | Standard index works |
| `LIKE '%substring%'` | GIN trigram | `pg_trgm` extension |

### Connection Pool Sizing

```bash
# Python: check pool configuration
grep -rn "pool_size\|max_overflow\|pool_timeout\|NullPool\|QueuePool" src/ --include="*.py"
grep -rn "ThreadedConnectionPool\|SimpleConnectionPool" src/ --include="*.py"

# Check for missing pool config (uses default which may be too small)
grep -rn "create_engine\|psycopg2.connect\|asyncpg.create_pool" src/ --include="*.py" \
  | grep -v "pool_size"

# Node.js: pg pool config
grep -rn "new Pool(\|createPool(" src/ --include="*.ts" --include="*.js"
grep -rn "max:\|idleTimeoutMillis:\|connectionTimeoutMillis:" src/ --include="*.ts"

# Rule of thumb: pool_size = (cpu_cores * 2) + disk_spindles. For 4-core: 9-10.
# max_overflow = 2x pool_size. Too large = memory exhaustion under load.
```

### Query Timeout Configuration

```bash
# PostgreSQL statement timeout
grep -rn "statement_timeout\|query_timeout\|STATEMENT_TIMEOUT" src/ --include="*.py" --include="*.ts"
grep -rn "SET statement_timeout\|command_timeout" src/ --include="*.py"

# Alembic/migration timeout
grep -rn "statement_timeout" alembic/ --include="*.py" --include="*.ini"

# Check for missing timeout (long queries will hold connections)
grep -rn "execute(\|fetchall(\|fetchone(" src/ --include="*.py" | grep -v "timeout" | wc -l

# Application-level timeout via asyncio
grep -rn "asyncio.wait_for\|async_timeout\|timeout=" src/ --include="*.py" | grep -i "db\|query\|sql" | wc -l
```

### Prepared Statement Usage

```bash
# Python psycopg2: parameterized queries (safe) vs string formatting (unsafe)
grep -rn "execute(" src/ --include="*.py" | grep -E '"%|f"' | head -20  # f-string in execute = SQLi
grep -rn "execute(" src/ --include="*.py" | grep -v "%" | grep -v "?" | head -20

# Find raw SQL string concatenation
grep -rn "\"SELECT.*\" +" src/ --include="*.py" --include="*.ts"
grep -rn "f\"SELECT\|f'SELECT\|\"SELECT.*{" src/ --include="*.py"

# Node.js: check for template literals in SQL
grep -rn "db.query\`\|pool.query\`" src/ --include="*.ts" | grep -v "?"  # should use placeholders
grep -rn '\$\{.*\}' src/ --include="*.ts" | grep -i "sql\|query\|select\|where"  # interpolation in SQL
```

### ORM Lazy Loading Pitfalls

```bash
# SQLAlchemy: verify lazy loading is not used in async context
grep -rn "async def\|await " src/ --include="*.py" | wc -l
grep -rn "lazy=\"select\"" src/ --include="*.py" | wc -l
# Async + lazy="select" = MissingGreenlet error at runtime

# Django: check for QuerySet iteration in loops
grep -B2 -A10 "for.*in.*queryset\|for.*in.*objects" src/ --include="*.py" | grep -c "objects\."

# Active Record / TypeORM: check for chained promises that create N+1
grep -rn "for.*await\|Promise.all" src/ --include="*.ts" | grep -i "find\|load\|fetch" | head -10
```

### Transaction Isolation Levels

```bash
# Check if isolation level is set (default READ COMMITTED may be too weak)
grep -rn "ISOLATION LEVEL\|isolation_level\|IsolationLevel\." src/ --include="*.py" --include="*.ts"

# SQLAlchemy
grep -rn "isolation_level=\|with_for_update" src/ --include="*.py"

# Check for missing transactions on multi-step operations
grep -rn "def create\|def update\|def delete" src/ --include="*.py" | wc -l
grep -rn "with.*Session\|begin()\|transaction()" src/ --include="*.py" | wc -l
# If create/update/delete >> transaction usage: data integrity risk
```

## Advanced Patterns

### Query Performance Audit

```bash
# EXPLAIN ANALYZE for slow query patterns (PostgreSQL)
# Find all distinct query shapes in codebase
grep -rn "\.filter(\|WHERE " src/ --include="*.py" --include="*.sql" \
  | grep -oP "(?<=filter\(|WHERE )[^)\"']+" | sort -u | head -20

# Use pg_badger to analyze slow query logs
# pg_badger /var/log/postgresql/postgresql.log -o report.html
```

### Anti-Patterns Summary

| Pattern | Detection | Severity |
|---------|-----------|----------|
| N+1 with lazy loading | Loop + DB call inside | CRITICAL |
| String interpolation in SQL | `f"SELECT...{var}"` | CRITICAL |
| Missing index on FK | Migration check | HIGH |
| No connection pool limit | `max_overflow` absent | HIGH |
| No query timeout | `statement_timeout` absent | HIGH |
| Transactions spanning HTTP requests | Long `begin()` blocks | HIGH |
| `SELECT *` in production | `SELECT *` in ORM/raw | MEDIUM |
