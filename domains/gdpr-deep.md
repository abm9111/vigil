# VIGIL Domain Detail: GDPR / Privacy Deep-Dive

**Parent cluster:** security
**Loaded in:** siege mode, or --only security --deep

## Deep Checks

### Lawful Basis Documentation

```bash
# find personal data processing points
grep -rn "email\|phone\|name\|address\|dob\|ip_address\|user_id\|personal" src/ --include="*.py" --include="*.ts" | grep -v "//\|#\|test\|spec" | head -30

# check if processing purpose is documented
find . -name "privacy-policy*" -o -name "privacy_policy*" -o -name "PRIVACY*" -o -name "data-processing*" 2>/dev/null
grep -rn "lawful_basis\|legal_basis\|processing_purpose\|legitimate_interest" src/ --include="*.py" --include="*.ts" | head -10

# retention policies
grep -rn "retention\|ttl\|expires_at\|delete_after\|purge\|archive" src/ --include="*.py" --include="*.ts" | grep -v "//\|#\|test" | head -20

# data minimization — collecting more than needed
grep -rn "SELECT \*\|\.all()\|findAll()" src/ --include="*.py" --include="*.ts" | grep -v "test\|spec\|limit" | head -20
```

### Consent Management

```bash
# consent collection and storage
grep -rn "consent\|gdpr\|opted_in\|marketing_opt\|cookie_consent" src/ --include="*.py" --include="*.ts" | head -20

# consent version tracking (consent must be re-collected on policy changes)
grep -rn "consent_version\|policy_version\|terms_version\|accepted_at" src/ --include="*.py" --include="*.ts") | head -10

# pre-ticked boxes (invalid consent under GDPR)
grep -rn "defaultChecked.*true\|checked.*true\|default.*true" src/ --include="*.tsx") | grep -i "consent\|marketing\|newsletter\|terms\|opt" | head -10

# consent withdrawal mechanism
grep -rn "withdraw\|revoke\|unsubscribe\|opt_out\|delete_consent" src/ --include="*.py" --include="*.ts" | head -10

# cookie consent banner
grep -rn "CookieBanner\|CookieConsent\|cookie-consent\|cookiebanner\|OneTrust\|Cookiebot\|CookieYes" src/ --include="*.tsx" --include="*.ts" | head -10
```

### Data Subject Rights — Access (Article 15)

```bash
# data export / download endpoint
grep -rn "export_data\|download_data\|data_export\|subject_access\|SAR\|DSAR" src/ --include="*.py" --include="*.ts" | head -10

# all tables/collections containing user data
grep -rn "user_id\|userId\|subject_id" src/ --include="*.py" --include="*.ts" | grep -i "model\|schema\|table\|collection\|entity" | head -30

# audit trail of data access
grep -rn "audit_log\|access_log\|data_access\|accessed_at" src/ --include="*.py" --include="*.ts") | head -10
```

### Data Subject Rights — Erasure (Article 17 — Right to be Forgotten)

```bash
# delete account / data deletion endpoint
grep -rn "delete_account\|delete_user\|erase_data\|right_to_erasure\|gdpr_delete" src/ --include="*.py" --include="*.ts" | head -10

# soft delete vs hard delete
grep -rn "deleted_at\|is_deleted\|soft_delete\|deactivated" src/ --include="*.py" --include="*.ts") | head -20
# soft-deleted data should still be excluded from processing
grep -rn "where.*deleted_at.*null\|filter.*is_deleted.*False\|exclude.*deleted" src/ --include="*.py" --include="*.ts") | head -10

# cascading deletes across all tables
grep -rn "ON DELETE CASCADE\|cascade=.*delete\|orphan\|delete_orphans" src/ --include="*.py" --include="*.ts") | head -10

# third-party services notified on deletion
grep -rn "delete.*stripe\|delete.*mailchimp\|delete.*sendgrid\|delete.*segment\|delete.*amplitude" src/ --include="*.py" --include="*.ts") | head -10
```

### Data Subject Rights — Portability and Rectification

```bash
# data portability (machine-readable format)
grep -rn "json_export\|csv_export\|export.*json\|portable\|portability" src/ --include="*.py" --include="*.ts") | head -10

# update profile / rectification endpoint
grep -rn "update_profile\|edit_profile\|rectify\|correct.*data\|PATCH.*user\|PUT.*user" src/ --include="*.py" --include="*.ts") | head -10

# immutable audit fields (should not be rectifiable)
grep -rn "created_at\|event_log\|audit\|immutable" src/ --include="*.py" --include="*.ts") | head -10
```

### DPO Designation and DPIA

```bash
# DPO contact documented
grep -rn "dpo\|data_protection_officer\|privacy@\|dpo@" src/ docs/ --include="*.py" --include="*.ts" --include="*.md") | head -10

# DPIA (Data Protection Impact Assessment) for high-risk processing
find . -name "DPIA*" -o -name "dpia*" -o -name "impact-assessment*" 2>/dev/null

# high-risk processing detection (automated decisions, profiling, biometrics)
grep -rn "profil\|segment\|score.*user\|automat.*decision\|credit_score\|fraud_score\|risk_score" src/ --include="*.py" --include="*.ts") | head -20
grep -rn "biometric\|face_recog\|fingerprint\|voice_print" src/ --include="*.py" --include="*.ts") | head -10
```

### Breach Notification Process

```bash
# breach detection and logging
grep -rn "breach\|data_leak\|unauthorized_access\|security_incident\|incident_response" src/ --include="*.py" --include="*.ts") | head -10

# 72-hour notification window (Article 33)
find . -name "incident*" -o -name "breach*" -o -name "security-incident*" 2>/dev/null | head -10

# alerting infrastructure for anomalous access
grep -rn "alert\|pagerduty\|opsgenie\|sentry\|anomal" src/ --include="*.py" --include="*.ts") | grep -i "access\|breach\|leak\|unauthorized" | head -10
```

### Processor Agreements

```bash
# third-party data processors in use
grep -rn "SENDGRID\|MAILCHIMP\|STRIPE\|TWILIO\|AWS\|GCP\|AZURE\|SEGMENT\|MIXPANEL\|AMPLITUDE\|HUBSPOT\|SALESFORCE\|INTERCOM" src/ --include="*.py" --include="*.ts") | grep -v "//\|#\|test" | head -30

# Data Processing Agreement references
find . -name "DPA*" -o -name "dpa*" -o -name "*data-processing-agreement*" 2>/dev/null

# API keys for processors (should be in env, not code)
grep -rn "SENDGRID_API_KEY\|STRIPE_SECRET\|TWILIO_AUTH" src/ --include="*.py" --include="*.ts") | grep -v "os\.environ\|process\.env\|config\." | head -10
```

### Cross-Border Transfer Mechanisms

```bash
# data transfer to non-EEA countries
grep -rn "us-east\|us-west\|ap-southeast\|ap-northeast\|sa-east\|region.*us\|region.*ap" src/ --include="*.py" --include="*.ts") | grep -v "//\|#\|test" | head -20

# SCCs / adequacy decisions documented
find . -name "SCC*" -o -name "*standard-contractual*" -o -name "*adequacy*" 2>/dev/null

# EU data residency config
grep -rn "eu-west\|eu-central\|eu-north\|europe\|data_residency\|storage_location" src/ --include="*.py" --include="*.ts") | head -10

# LLM provider data region
grep -rn "azure_endpoint\|openai.api_base\|anthropic.*base_url\|aws_region" src/ --include="*.py" --include="*.ts") | head -10
```

## Advanced Patterns

| Pattern | Severity | GDPR Article |
|---------|----------|--------------|
| PII in application logs | High | Art. 5(1)(f) — Integrity & confidentiality |
| No data retention policy / TTL | High | Art. 5(1)(e) — Storage limitation |
| Blanket marketing consent pre-ticked | Critical | Art. 7 — Conditions for consent |
| No mechanism to honor deletion requests | Critical | Art. 17 — Right to erasure |
| User data sent to US processor without SCCs | High | Art. 46 — Transfers subject to safeguards |
| Analytics fingerprinting without consent | High | Art. 6 — Lawfulness of processing |
| Third-party scripts load before consent | High | ePrivacy Directive + GDPR |
| No data breach detection / notification plan | High | Art. 33 — 72h supervisory notification |
| Profiling/automated decisions without disclosure | High | Art. 22 — Automated individual decisions |
| Minors' data without parental consent mechanism | Critical | Art. 8 — Child consent |
| Backup systems not included in deletion scope | High | Art. 17 — Must delete all copies |
| No record of processing activities (RoPA) | Medium | Art. 30 — Records of processing activities |
