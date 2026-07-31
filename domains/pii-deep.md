# VIGIL Domain Detail: PII Handling

**Parent cluster:** compliance
**Loaded in:** siege mode, or --only compliance --deep

## Deep Checks

### Data Classification (PII/PHI/PCI)

```bash
# Find fields that commonly contain PII
grep -rn "email\|phone\|ssn\|passport\|national_id\|dob\|date_of_birth\|address\|ip_address" \
  src/ --include="*.py" --include="*.ts" | grep -E "Column|Field|schema|model" | head -30

# PHI (HIPAA): medical fields
grep -rn "diagnosis\|medication\|health_record\|patient\|mrn\|insurance_id" \
  src/ --include="*.py" --include="*.ts" | head -20

# PCI (payment card data)
grep -rn "card_number\|cvv\|pan\|cardholder\|track_data\|account_number" \
  src/ --include="*.py" --include="*.ts" | head -20

# Check if fields have classification markers (custom annotations or comments)
grep -rn "# PII\|# PHI\|# PCI\|@pii\|pii=True\|sensitive=True" src/ | wc -l
```

| Data Type | Regulation | Minimum Protection |
|-----------|-----------|-------------------|
| Email, Name, Phone | GDPR/CCPA | Encrypt at rest, access log |
| SSN, National ID | GDPR/US state | Encrypt + mask in logs |
| Medical records | HIPAA | Encrypt + audit trail + BAA |
| Card numbers | PCI-DSS | Tokenize — never store raw PAN |
| Passwords | Universal | bcrypt/argon2, never log |

### Encryption at Rest Patterns

```bash
# Check if sensitive columns use application-level encryption
grep -rn "encrypt\|decrypt\|Fernet\|AES\|cryptography" src/ --include="*.py" | head -20
grep -rn "pgcrypto\|encrypt(" src/ --include="*.py" --include="*.sql"  # DB-level encryption

# Check for Postgres column encryption
grep -rn "pgp_sym_encrypt\|pgp_pub_encrypt\|encrypt_iv" src/ --include="*.sql" --include="*.py"

# Check for unhashed/unencrypted sensitive fields (stored as plain text)
grep -rn "email.*String\|phone.*String\|ssn.*String\|national_id.*String" \
  src/ --include="*.py" | grep -v "encrypted\|hashed\|token" | head -10

# Verify password storage uses strong hashing
grep -rn "bcrypt\|argon2\|scrypt\|pbkdf2" src/ --include="*.py" --include="*.ts" | wc -l
grep -rn "md5.*password\|sha1.*password\|sha256.*password" src/ --include="*.py" --include="*.ts"  # BAD
```

### Masking Strategies

```bash
# Check for PII masking in logs
grep -rn "logging\.\|logger\." src/ --include="*.py" | grep -i "email\|phone\|password\|token" | head -20
# Any log line that includes raw PII = compliance violation

# Check for log sanitization middleware
grep -rn "mask\|redact\|sanitize\|obfuscate" src/ --include="*.py" --include="*.ts" | head -20

# Verify API responses don't leak sensitive fields
grep -rn "response_model\|ResponseSchema\|serializer" src/ --include="*.py" | head -20
grep -rn "password\|ssn\|card_number" src/ --include="*.py" | grep "response\|schema\|serializ" | head -10
# Sensitive fields should be excluded from response schemas

# Check for accidental PII in error messages
grep -rn "raise.*email\|raise.*phone\|Error.*user\b" src/ --include="*.py" | head -10
```

### Data Retention Implementation

```bash
# Check for retention policy implementation
grep -rn "retention\|expire\|purge\|soft_delete\|deleted_at" src/ --include="*.py" --include="*.ts" | head -20

# Check if old records are actually deleted (not just flagged)
grep -rn "DELETE FROM\|\.delete()\|hard_delete\|permanent_delete" src/ --include="*.py" | head -10

# Check for scheduled cleanup jobs
grep -rn "celery\|cron\|schedule\|APScheduler\|rq" src/ --include="*.py" | grep -i "purge\|clean\|expire\|delete" | head -10

# Verify retention periods are defined
grep -rn "RETENTION_DAYS\|RETENTION_PERIOD\|DATA_RETENTION\|MAX_AGE" src/ --include="*.py" --include="*.ts" | head -10
```

### Right to Erasure (GDPR Article 17)

```bash
# Check for account deletion functionality
grep -rn "def delete_account\|def gdpr_delete\|def right_to_erasure\|def erase_user" \
  src/ --include="*.py" --include="*.ts" | head -10

# Verify cascading deletes across tables
grep -rn "cascade\|CASCADE" src/ --include="*.py" --include="*.sql" | head -20

# Check if deletion also removes data from:
grep -rn "cache\|redis\|s3\|storage\|backup\|log" src/ --include="*.py" | grep -i "delete\|remove\|clear" | head -10
# Redis cache, S3 files, backup tables, and audit logs must all be addressed

# Soft-delete pattern (GDPR requires actual deletion, not just flagging)
grep -rn "is_deleted\|deleted_at\|is_active" src/ --include="*.py" | wc -l
# Soft-deleted records with PII still count as stored PII under GDPR
```

### Cross-Border Transfer Checks

```bash
# Check where external APIs send data (non-EU/non-UAE servers)
grep -rn "requests\.post\|httpx\.post\|aiohttp.*post" src/ --include="*.py" | head -20
grep -rn "openai\|groq\|anthropic\|bedrock\|azure" src/ --include="*.py" | head -10
# Each external API call that includes user data = potential cross-border transfer

# Check for EU/GCC data residency requirements
grep -rn "region\|REGION\|eu-west\|us-east\|ap-southeast" src/ --include="*.py" | head -10

# Look for data processing agreements (DPA) in config comments
grep -rn "DPA\|data processing agreement\|SCCs\|standard contractual\|adequacy" \
  src/ docs/ --include="*.py" --include="*.md" | head -10
```

### Audit Trail for PII Access

```bash
# Check for audit logging on sensitive operations
grep -rn "audit_log\|AuditLog\|audit_trail\|access_log" src/ --include="*.py" | wc -l
grep -rn "def get_user\|def fetch_user\|GET.*user" src/ --include="*.py" | wc -l
# If user reads >> audit log entries: access is not being logged

# Verify audit log includes: who accessed, what data, when, from where
grep -B2 -A10 "audit_log\|AuditLog" src/ --include="*.py" | grep -E "user_id|ip_address|timestamp|resource"

# Check if audit logs are tamper-evident (append-only, immutable)
grep -rn "audit" src/ --include="*.py" | grep "update\|delete\|modify" | head -10  # audit records should never be updated
```

### Anonymization and Pseudonymization

```bash
# Check for anonymization utilities
grep -rn "anonymize\|pseudonymize\|tokenize\|hash.*email\|faker\|generate_fake" \
  src/ --include="*.py" --include="*.ts" | head -20

# Check test data (tests must not use real PII)
grep -rn "real_email\|production_data\|@gmail.com\|@yahoo.com" tests/ --include="*.py" | head -10
grep -rn "\+[0-9]{10}\|[0-9]{3}-[0-9]{2}-[0-9]{4}" tests/ --include="*.py"  # real phone/SSN in tests

# Verify staging/dev environments use anonymized data
grep -rn "DATABASE_URL\|DB_HOST" .env.staging .env.development 2>/dev/null | head -5
# If staging points to production DB: direct PII exposure
```

## Advanced Patterns

### PII Risk Matrix

| Data | Stored | Encrypted | Logged | Masked in API | Deletable | Risk |
|------|--------|-----------|--------|---------------|-----------|------|
| Email | Yes | No | Yes | No | No | CRITICAL |
| Password | Yes | Hashed | No | No | Yes | LOW |
| Phone | Yes | No | No | No | No | HIGH |
| Payment | Tokenized | n/a | No | Masked | Yes | LOW |

### Compliance Mapping

- **GDPR:** Articles 5, 17, 20, 32 — data minimization, erasure, portability, security
- **CCPA:** Right to know, delete, opt-out of sale
- **HIPAA:** PHI encryption, audit logs, BAA with processors
- **PCI-DSS v4:** No raw PAN storage, TLS 1.2+, quarterly scans
- **UAE PDPL (2022):** Consent, cross-border transfer restrictions, 72-hour breach notification
