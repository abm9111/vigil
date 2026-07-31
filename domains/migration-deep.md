# VIGIL Domain Detail: Migration Safety

**Parent cluster:** database
**Loaded in:** siege mode, or --only database --deep

## Deep Checks

### Zero-Downtime Migration Patterns

```bash
# Find dangerous migration operations (require table lock)
grep -rn "op\.alter_column\|ALTER COLUMN\|ALTER TABLE.*RENAME" \
  alembic/versions/ migrations/ db/migrate/ --include="*.py" --include="*.sql" --include="*.rb"

# Specifically find column type changes (require full table rewrite in Postgres)
grep -rn "ALTER.*TYPE\|type_=\|server_default=" alembic/versions/ --include="*.py" | head -20

# Find ADD COLUMN NOT NULL without default (will fail on large tables with existing rows)
grep -rn "nullable=False" alembic/versions/ --include="*.py" | grep -v "server_default\|default="
grep -rn "NOT NULL" alembic/versions/ --include="*.sql" | grep -v "DEFAULT\|existing"
```

| Operation | Lock Type | Zero-Downtime Pattern |
|-----------|-----------|----------------------|
| ADD COLUMN nullable | None (Postgres 11+) | Safe |
| ADD COLUMN NOT NULL | Full table lock | Add nullable, backfill, add constraint |
| DROP COLUMN | AccessExclusive | Soft-delete first, deploy, then drop |
| CREATE INDEX | ShareLock | Use `CONCURRENTLY` |
| ADD FOREIGN KEY | ShareRowExclusive | Use `NOT VALID`, then `VALIDATE` |
| RENAME TABLE | AccessExclusive | Create view, migrate, drop old |

### Backwards Compatibility

```bash
# Find migrations that break running old code:
# 1. Column renames (old code references old name)
grep -rn "op\.alter_column.*new_column_name\|RENAME COLUMN" alembic/versions/ --include="*.py"

# 2. Column drops (old code may still query dropped column)
grep -rn "op\.drop_column\|DROP COLUMN" alembic/versions/ --include="*.py" --include="*.sql"

# 3. Constraint additions on existing data
grep -rn "op\.create_unique_constraint\|op\.create_check_constraint\|ADD CONSTRAINT" \
  alembic/versions/ --include="*.py" | head -20

# Safe deploy order for removals:
# Phase 1: Deploy code that stops using old column
# Phase 2: Run migration to drop column (no old code left reading it)
# Check if there are pending phases by looking at TODO/FIXME in migration comments
grep -rn "TODO\|FIXME\|phase 2\|Phase 2" alembic/versions/ --include="*.py"
```

### Data Migration Testing

```bash
# Check if data migrations have tests
ls tests/migrations/ tests/test_migrations.py 2>/dev/null
grep -rn "def test.*migration\|def test.*migrate" tests/ --include="*.py"

# Verify data migrations are idempotent (can be re-run safely)
grep -rn "def upgrade" alembic/versions/ --include="*.py" -A 20 \
  | grep -v "op\.\|#" | grep -c "if\|exists\|count"  # guard checks

# Check for data migration size guard (avoid full-table scans on huge tables)
grep -rn "batch_size\|chunk_size\|BATCH\|limit(" alembic/versions/ --include="*.py" | head -10
```

### Rollback Verification

```bash
# Check all migrations have downgrade() implemented
grep -rn "def downgrade" alembic/versions/ --include="*.py" | wc -l
grep -rn "def upgrade" alembic/versions/ --include="*.py" | wc -l
# If upgrade count != downgrade count: missing rollback paths

# Find no-op downgrades (risky if rollback is needed)
grep -A3 "def downgrade" alembic/versions/ --include="*.py" | grep "pass\b"

# Test rollback dry-run
alembic downgrade -1 --sql > /tmp/rollback.sql  # generate without executing
alembic upgrade head --sql > /tmp/upgrade.sql    # compare symmetry
```

### Schema Diff Validation

```bash
# Alembic: detect model/DB drift (code says X, DB says Y)
alembic check  # returns non-zero if auto-generated migration would be non-empty

# Django: check for unapplied migrations
python manage.py migrate --check    # exit 1 if unapplied
python manage.py showmigrations     # list all migration states

# Prisma: schema drift detection
npx prisma migrate status           # shows pending migrations
npx prisma db pull                  # introspect current DB schema
# Then: npx prisma migrate diff --from-schema-datamodel prisma/schema.prisma --to-schema-datasource
```

### Foreign Key Constraint Ordering

```bash
# Find FK constraints added before referenced table is created
# Check migration file order — FKs must come after the table they reference
grep -rn "op\.create_foreign_key\|REFERENCES\|ForeignKey(" alembic/versions/ --include="*.py" \
  | grep -oP "(?<=REFERENCES |references='|to=')[a-z_\"]+" | sort | uniq

# Verify referenced tables exist in earlier migrations
grep -rn "op\.create_table(" alembic/versions/ --include="*.py" \
  | grep -oP "\"[a-z_]+\"" | sort | uniq

# Circular FK dependencies (A references B, B references A)
# Look for tables with mutual FKs
grep -rn "ForeignKey\|REFERENCES" alembic/versions/ --include="*.py" --include="*.sql" \
  | awk -F'[>|]' '{print $1, $2}' | head -30
```

### Enum Migration Safety

```bash
# PostgreSQL enum changes are notoriously dangerous
grep -rn "op\.execute.*ALTER TYPE\|CREATE TYPE.*AS ENUM\|add_enum_value" \
  alembic/versions/ --include="*.py" --include="*.sql"

# Safe enum addition: ALTER TYPE enum ADD VALUE 'new_val' (safe in Postgres 9.1+)
# Unsafe: removing a value or renaming requires full recreate + cast

# Check for enum removal (requires table rewrite)
grep -rn "op\.execute.*DROP TYPE\|\"type\": \"enum\"" alembic/versions/ | head -10
```

### Large Table ALTER Strategies

```bash
# Find migrations on known large tables (>1M rows)
# Cross-reference table names against data volume knowledge
grep -rn "op\.alter_column\|ADD COLUMN\|DROP COLUMN" alembic/versions/ --include="*.py" \
  | grep -E "users|orders|events|logs|transactions|messages"

# Check if pg_repack or pt-online-schema-change is referenced
grep -rn "pg_repack\|pt-online-schema-change\|gh-ost\|ALGORITHM=INPLACE" \
  alembic/ Makefile scripts/ --include="*.py" --include="*.sh"

# Verify CONCURRENTLY is used for new indexes
grep -rn "op\.create_index" alembic/versions/ --include="*.py" | grep -v "postgresql_concurrently=True"
```

## Advanced Patterns

### Migration Safety Scorecard

| Check | Safe Signal | Danger Signal |
|-------|------------|---------------|
| Index creation | `CONCURRENTLY` | Plain `CREATE INDEX` |
| FK addition | `NOT VALID` + `VALIDATE` | Inline on large table |
| NOT NULL column | Default value set | No default, existing rows |
| Column removal | Code deployed first | Migration before deploy |
| Enum changes | ADD VALUE only | DROP/rename value |
| Downgrade | Implemented | `pass` or missing |

### Deployment Sequence Checklist

```bash
# Verify migration is safe to run before or after code deploy
# Step 1: Does migration require new code? (backwards-compatible change)
#   - Add nullable column, add index, add FK NOT VALID → run BEFORE deploy
# Step 2: Does migration depend on code running first?
#   - Drop old column, rename table → run AFTER old code is gone
# Step 3: Is migration reversible within 1 hour if needed?
#   - Check downgrade time estimate from table size
```
