# VIGIL Cluster: Data & Persistence

**Covers:** Database access, migrations, data integrity, backup, PII handling
**Weight:** 12%
**ID prefix:** VIGIL-DATA

## Deterministic Tools

### Database Access Patterns

```bash
# Raw SQL (potential injection)
grep -rn --include='*.py' -E '\.execute\(|\.executemany\(|\.raw\(|cursor\.' . \
  --exclude-dir={.venv,node_modules,.git,tests} 2>/dev/null

# ORM usage
grep -rn --include='*.py' -E 'from (sqlalchemy|django\.db|peewee|tortoise|prisma)' . \
  --exclude-dir={.venv,node_modules,.git} 2>/dev/null

# Parameterized vs string-formatted queries
grep -rn --include='*.py' -E '\.execute\(.*f["\x27]|\.execute\(.*%s.*%|\.execute\(.*\.format' . \
  --exclude-dir={.venv,node_modules,.git} 2>/dev/null

# Connection pool settings
grep -rn -E 'pool_size|max_connections|pool_recycle|connection_pool' . \
  --exclude-dir={node_modules,.venv,.git} 2>/dev/null
```

### Migration Safety

```bash
# Find migration files
find . -path '*/migrations/*' -name '*.py' -o -path '*/migrations/*' -name '*.sql' | \
  grep -v node_modules | grep -v .venv 2>/dev/null

# Dangerous migration patterns (data loss)
grep -rn --include='*.py' --include='*.sql' \
  -E 'DROP TABLE|DROP COLUMN|ALTER.*DROP|TRUNCATE|DELETE FROM.*WHERE 1|DELETE FROM.*;\s*$' \
  $(find . -path '*/migrations/*' 2>/dev/null | tr '\n' ' ') 2>/dev/null

# Missing down/rollback migrations
find . -path '*/migrations/*' -name '*.py' -exec grep -L 'def downgrade\|def backwards\|def reverse' {} \; 2>/dev/null
```

### Data Integrity

```bash
# Missing transaction boundaries
grep -rn --include='*.py' -E '\.commit\(\)|session\.add\(' . \
  --exclude-dir={.venv,node_modules,.git,tests} 2>/dev/null

# Check for atomic operations / transaction decorators
grep -rn --include='*.py' -E '@atomic|with.*transaction|BEGIN|COMMIT|ROLLBACK' . \
  --exclude-dir={.venv,node_modules,.git} 2>/dev/null

# N+1 query indicators
grep -rn --include='*.py' -E 'for.*in.*\.all\(\)|for.*in.*query|\.get\(.*\).*for' . \
  --exclude-dir={.venv,node_modules,.git,tests} 2>/dev/null
```

### PII & Sensitive Data

```bash
# PII field names in models
grep -rn --include='*.py' --include='*.ts' \
  -E '(email|phone|ssn|social_security|credit_card|date_of_birth|address|passport|national_id)' . \
  --exclude-dir={.venv,node_modules,.git,tests,docs} 2>/dev/null | head -20

# Encryption/hashing of sensitive fields
grep -rn --include='*.py' -E 'encrypt|decrypt|bcrypt|argon2|hashlib|hmac' . \
  --exclude-dir={.venv,node_modules,.git} 2>/dev/null
```

## Finding Patterns

### Query Safety (VIGIL-DATA-0xx)

| Pattern | Severity |
|---------|----------|
| String-formatted SQL query | CRITICAL |
| Raw SQL without parameterization | HIGH |
| No connection pooling | MEDIUM |
| Connection pool too large (>50) | LOW |
| No query timeout | MEDIUM |

### Migration Safety (VIGIL-DATA-1xx)

| Pattern | Severity |
|---------|----------|
| DROP TABLE in migration | HIGH |
| DROP COLUMN without data backup step | HIGH |
| No rollback/down migration | MEDIUM |
| Migration modifies data AND schema in one step | MEDIUM |
| No migration files at all (manual DDL) | HIGH |

### Data Integrity (VIGIL-DATA-2xx)

| Pattern | Severity |
|---------|----------|
| Multi-step DB operation without transaction | HIGH |
| N+1 query pattern in loop | MEDIUM |
| Missing unique constraints on business keys | MEDIUM |
| No foreign key constraints | LOW |
| Soft delete without index on deleted_at | LOW |

### PII Handling (VIGIL-DATA-3xx)

| Pattern | Severity |
|---------|----------|
| PII stored in plaintext | HIGH |
| PII in log output | HIGH |
| No data retention policy | MEDIUM |
| PII accessible via unauthenticated endpoint | CRITICAL |
| No encryption at rest for sensitive tables | MEDIUM |

### Backup & Recovery (VIGIL-DATA-4xx)

| Pattern | Severity |
|---------|----------|
| No backup strategy documented | MEDIUM |
| No point-in-time recovery capability | HIGH |
| Backup to same disk as data | HIGH |

## AI Reasoning Section

1. **Data flow mapping:** Trace PII from input to storage to output. Where is it exposed?
2. **Transaction safety:** Multi-step operations without transactions = data corruption risk.
3. **Migration review:** Would any migration cause downtime or data loss in production?
4. **Query efficiency:** Are there obvious N+1 patterns or missing indexes?
5. **Backup adequacy:** If the DB died right now, what's the recovery plan?
