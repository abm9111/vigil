# VIGIL Domain Detail: Database Query Optimization Deep-Dive

**Parent cluster:** backend
**Loaded in:** siege mode, or --only backend --deep

## Deep Checks

### EXPLAIN Plan Analysis

```bash
# PostgreSQL: get slow queries from pg_stat_statements
psql $DATABASE_URL -c "SELECT query, calls, mean_exec_time, total_exec_time, rows FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 20;"

# run EXPLAIN ANALYZE on a specific query
psql $DATABASE_URL -c "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) SELECT * FROM your_table WHERE col = 'val';" | python3 -m json.tool

# find sequential scans (Seq Scan in plans)
psql $DATABASE_URL -c "SELECT schemaname, tablename, seq_scan, seq_tup_read, idx_scan, idx_tup_fetch FROM pg_stat_user_tables WHERE seq_scan > 100 ORDER BY seq_scan DESC LIMIT 20;"

# MySQL: slow query log
mysql -e "SHOW VARIABLES LIKE 'slow_query_log%';"
mysql -e "SELECT * FROM information_schema.PROCESSLIST WHERE TIME > 5;"
mysqldumpslow -s t /var/log/mysql/mysql-slow.log | head -40

# SQLite: EXPLAIN QUERY PLAN
sqlite3 app.db "EXPLAIN QUERY PLAN SELECT * FROM laws WHERE jurisdiction = 'UAE';"
```

### Missing Index Detection

```bash
# PostgreSQL: tables with high seq_scan and no index hit
psql $DATABASE_URL -c "SELECT relname, seq_scan, idx_scan, n_live_tup FROM pg_stat_user_tables WHERE seq_scan > idx_scan AND n_live_tup > 1000 ORDER BY seq_scan DESC;"

# unused indexes (wasting write overhead)
psql $DATABASE_URL -c "SELECT indexrelname, idx_scan, pg_size_pretty(pg_relation_size(indexrelid)) as size FROM pg_stat_user_indexes WHERE idx_scan = 0 AND NOT indisprimary ORDER BY pg_relation_size(indexrelid) DESC;"

# missing foreign key indexes
psql $DATABASE_URL -c "SELECT tc.table_name, kcu.column_name FROM information_schema.table_constraints tc JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name WHERE tc.constraint_type = 'FOREIGN KEY';" > /tmp/fk_cols.txt

# ORM model audit: check indexed fields
grep -rn "db\.Column\|Column(\|Field(" src/ --include="*.py" | grep -v "index=True\|primary_key=True" | grep -v "#" | head -30
grep -rn "@Index\|@Column.*index\|createIndex" src/ --include="*.ts" | head -20
```

### Full Table Scan Indicators

```bash
# queries using LIKE with leading wildcard (kills index)
grep -rn "LIKE '%\|\.ilike('%\|ilike('%\|contains(" src/ --include="*.py" --include="*.ts" | head -20

# queries missing WHERE clause on large tables
grep -rn "\.all()\|SELECT \* FROM\|\.find({})\|\.findAll()" src/ --include="*.py" --include="*.ts" | grep -v "test\|spec\|limit\|LIMIT" | head -20

# function on indexed column prevents index use
grep -rn "WHERE.*LOWER(\|WHERE.*UPPER(\|WHERE.*DATE(\|WHERE.*CAST(" src/ --include="*.py" --include="*.ts" | head -10

# OR conditions that bypass composite indexes
grep -rn " OR \| or " src/ --include="*.py" --include="*.ts" | grep -i "WHERE\|filter\|query" | head -20
```

### Join Optimization

```bash
# Cartesian product risk (missing join condition)
grep -rn "FROM.*,.*,\|JOIN.*JOIN.*JOIN.*JOIN" src/ --include="*.py" --include="*.ts" | head -10

# N+1 query pattern detection (ORM)
grep -rn "for.*in.*\.all()\|for.*in.*await.*find\|\.forEach.*await.*find" src/ --include="*.py" --include="*.ts" | head -20

# SQLAlchemy: missing joinedload/selectinload
grep -rn "\.query(\|session\.execute" src/ --include="*.py" | xargs grep -L "joinedload\|selectinload\|subqueryload" 2>/dev/null | head -10

# TypeORM: missing eager/lazy relations config
grep -rn "\.find(\|\.findOne(\|\.findAll(" src/ --include="*.ts" | grep -v "relations:\|join:\|loadEagerRelations" | head -20

# Excessive JOIN depth (> 4 tables)
grep -rn "JOIN" src/ --include="*.py" --include="*.ts" | awk '{count=split($0,a,"JOIN")-1; if(count>3) print NR": "count" JOINs: "$0}' | head -10
```

### Subquery vs JOIN

```bash
# correlated subqueries in SELECT clause (executes per row)
grep -rn "SELECT.*\(SELECT\|\.extra(select\|annotate.*Subquery\|annotate.*RawSQL" src/ --include="*.py" | head -10

# IN (SELECT ...) that should be EXISTS or JOIN
grep -rn "IN (SELECT\|IN(SELECT\|\.filter.*__in.*\.values_list" src/ --include="*.py" | head -20

# NOT IN vs NOT EXISTS (NOT IN fails on NULLs)
grep -rn "NOT IN (SELECT\|NOT IN(SELECT" src/ --include="*.py" --include="*.ts" | head -10

# check if subqueries are materialized CTEs vs inline
grep -rn "WITH .*AS (\|\.cte(\|\.subquery(" src/ --include="*.py" | head -10
```

### Pagination Strategies

```bash
# offset-based pagination on large datasets (slow at high offsets)
grep -rn "\.offset(\|OFFSET\|\.skip(\|page.*\*.*limit" src/ --include="*.py" --include="*.ts" | grep -v "//\|test\|spec" | head -20

# missing limit on paginated queries (unbounded results)
grep -rn "\.all()\|\.find(\|SELECT \*" src/ --include="*.py" --include="*.ts" | grep -v "limit\|LIMIT\|first\|one()\|paginate" | head -20

# cursor-based pagination implementation
grep -rn "cursor\|after:\|before:\|last_id\|created_at.*>\|id.*>" src/ --include="*.py" --include="*.ts" | grep -i "paginat\|page\|cursor" | head -10

# missing index on sort column used for pagination
grep -rn "ORDER BY\|order_by(\|orderBy(" src/ --include="*.py" --include="*.ts" | head -20
```

### Materialized View Candidates

```bash
# aggregate queries called frequently
grep -rn "COUNT(\|SUM(\|AVG(\|GROUP BY" src/ --include="*.py" --include="*.ts" | grep -v "//\|test\|spec" | head -20

# check for existing materialized views
psql $DATABASE_URL -c "SELECT matviewname, pg_size_pretty(pg_total_relation_size(oid)) FROM pg_matviews;"

# report/analytics queries (good candidates)
grep -rn "analytics\|report\|dashboard\|stats\|metrics\|summary" src/ --include="*.py" --include="*.ts" | grep -i "query\|select\|find\|fetch" | head -20
```

### Query Caching

```bash
# Redis caching on hot read paths
grep -rn "cache\|redis\|memcached" src/ --include="*.py" --include="*.ts" | grep -i "get\|set\|fetch" | head -20

# ORM second-level cache configuration
grep -rn "cache_ok\|query_cache\|dogpile\|beaker\|@cache" src/ --include="*.py" | head -10

# HTTP-level caching headers on API responses
grep -rn "Cache-Control\|ETag\|Last-Modified\|max-age" src/ --include="*.py" --include="*.ts" | head -10

# missing cache invalidation on write
grep -rn "\.delete(\|\.update(\|\.save(\|\.create(" src/ --include="*.py" | xargs grep -L "cache\|invalidate\|evict\|del " 2>/dev/null | head -10
```

## Advanced Patterns

| Pattern | Severity | Fix |
|---------|----------|-----|
| `SELECT *` in production queries | Medium | Specify columns; reduces I/O, enables index-only scans |
| `OFFSET 100000` on large table | High | Switch to cursor pagination (id > last_seen_id) |
| Index on low-cardinality column (e.g. boolean) | Low | Drop index; partial index or composite more useful |
| Missing composite index for multi-column WHERE | High | (col_a, col_b) index for `WHERE col_a = X AND col_b = Y` |
| Implicit type cast in WHERE clause | High | Ensure query param type matches column type |
| `ORDER BY RANDOM()` on large table | High | Use offset with keyset or pre-randomize |
| Fetching 10K rows to count in app | High | Use `COUNT(*)` at DB level |
| No connection pool, new connection per request | Critical | Pool with min=2, max=10 per worker |
| Missing `VACUUM ANALYZE` schedule | Medium | Auto-vacuum enabled; check thresholds |
| Trigger-per-row on high-write table | Medium | Batch or statement-level trigger |
