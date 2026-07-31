# VIGIL Compliance Map: OWASP Top 10 (2021)

**Standard:** OWASP Top 10 Web Application Security Risks (2021)
**Purpose:** Map VIGIL findings to OWASP categories

## OWASP Top 10 → VIGIL Finding Mapping

### A01:2021 — Broken Access Control

**VIGIL findings that map here:**
- VIGIL-SEC-2xx (Auth & Access): Missing auth on endpoints, broken RBAC
- VIGIL-API-0xx: Endpoints without authorization checks
- VIGIL-DATA-3xx: PII accessible without auth
- VIGIL-CORR: AUTH_BYPASS_WITH_SCOPE, DATA_EXPOSURE_CHAIN

**Deterministic checks:**
```bash
# Endpoints without auth decorators
grep -rn --include='*.py' -E '@(app|router)\.(get|post|put|delete)' . --exclude-dir={.venv,.git,tests} | \
  grep -v -E '(Depends|login_required|requires_auth|authenticate)' 2>/dev/null

# CORS wildcard
grep -rn 'allow_origins.*\*' . --exclude-dir={node_modules,.venv,.git} 2>/dev/null

# Missing CSRF
grep -rn -E 'csrf|CSRFProtect' . --exclude-dir={node_modules,.venv,.git} 2>/dev/null
```

**CWEs:** CWE-200, CWE-284, CWE-285, CWE-352, CWE-639

### A02:2021 — Cryptographic Failures

**VIGIL findings:**
- VIGIL-SEC-0xx: Hardcoded secrets, weak keys
- VIGIL-SEC-4xx: Missing HTTPS, insecure cookies
- VIGIL-DATA-3xx: PII without encryption

**Deterministic checks:**
```bash
# Weak hashing
grep -rn --include='*.py' -E 'md5|sha1|hashlib\.(md5|sha1)' . --exclude-dir={.venv,.git} 2>/dev/null

# HTTP without S
grep -rn 'http://' . --exclude-dir={node_modules,.venv,.git,docs} --include='*.py' --include='*.ts' 2>/dev/null | \
  grep -v localhost | grep -v 127.0.0.1 | grep -v '0.0.0.0'
```

**CWEs:** CWE-259, CWE-327, CWE-328, CWE-330

### A03:2021 — Injection

**VIGIL findings:**
- VIGIL-SEC-1xx: SQL, command, template, LDAP injection
- VIGIL-AIML-0xx: Prompt injection
- VIGIL-CORR: INJECTION_WITH_PRIVILEGE

**Deterministic checks:**
```bash
# SQL injection
grep -rn --include='*.py' -E '\.execute\(.*f["\x27]|\.execute\(.*%|\.execute\(.*\.format' . --exclude-dir={.venv,.git} 2>/dev/null

# Command injection
grep -rn --include='*.py' -E 'subprocess.*shell\s*=\s*True|os\.system\(' . --exclude-dir={.venv,.git} 2>/dev/null

# XSS
grep -rn --include='*.tsx' --include='*.jsx' 'dangerouslySetInnerHTML' . --exclude-dir={node_modules,.git} 2>/dev/null
```

**CWEs:** CWE-20, CWE-74, CWE-78, CWE-79, CWE-89

### A04:2021 — Insecure Design

**VIGIL findings:**
- VIGIL-API-0xx: Missing input validation, no rate limiting
- VIGIL-DATA-2xx: Missing transaction boundaries
- VIGIL-CORR: ENDPOINT_STACK (multiple issues on one endpoint = design problem)

**CWEs:** CWE-209, CWE-256, CWE-501, CWE-522

### A05:2021 — Security Misconfiguration

**VIGIL findings:**
- VIGIL-SEC-4xx: DEBUG mode, verbose errors, default credentials
- VIGIL-INFRA-0xx: Docker misconfigurations
- VIGIL-INFRA-1xx: CI/CD misconfigurations
- VIGIL-CORR: CONFIG_SECRET_EXPOSURE

**Deterministic checks:**
```bash
# Debug mode
grep -rn 'DEBUG.*True\|debug.*true\|NODE_ENV.*development' . --exclude-dir={node_modules,.venv,.git} 2>/dev/null

# Default credentials
grep -rn -iE 'password.*=.*(admin|password|changeme|123456|default)' . --exclude-dir={node_modules,.venv,.git} 2>/dev/null
```

**CWEs:** CWE-2, CWE-11, CWE-13, CWE-15

### A06:2021 — Vulnerable and Outdated Components

**VIGIL findings:**
- VIGIL-SEC-3xx: Dependency CVEs
- VIGIL-CORR: DEPENDENCY_AND_REACHABILITY

**Deterministic checks:**
```bash
pip-audit --format=json 2>&1
npm audit --json 2>&1
```

**CWEs:** CWE-1035, CWE-1104

### A07:2021 — Identification and Authentication Failures

**VIGIL findings:**
- VIGIL-SEC-2xx: Weak auth, no MFA, session issues
- VIGIL-API-1xx: No rate limiting on login

**CWEs:** CWE-255, CWE-259, CWE-287, CWE-384

### A08:2021 — Software and Data Integrity Failures

**VIGIL findings:**
- VIGIL-INFRA-1xx: Unpinned CI actions, insecure pipeline
- VIGIL-AIML-1xx: Untrusted model deserialization (pickle.load)
- VIGIL-SEC-3xx: Supply chain risk

**CWEs:** CWE-345, CWE-353, CWE-426, CWE-494, CWE-502

### A09:2021 — Security Logging and Monitoring Failures

**VIGIL findings:**
- VIGIL-INFRA-2xx: Missing logging, monitoring
- VIGIL-COMP-2xx: No audit trail
- VIGIL-CORR: OBSERVABILITY_BLINDSPOT

**CWEs:** CWE-117, CWE-223, CWE-532, CWE-778

### A10:2021 — Server-Side Request Forgery (SSRF)

**VIGIL findings:**
- VIGIL-API-2xx: Unvalidated URLs in server-side requests

**Deterministic checks:**
```bash
# URL from user input used in server request
grep -rn --include='*.py' -E 'requests\.(get|post)\(.*request\.|httpx\.(get|post)\(.*request\.' . \
  --exclude-dir={.venv,.git} 2>/dev/null
```

**CWEs:** CWE-918

## OWASP Summary Template

```
OWASP Top 10 Coverage — {project}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A01 Broken Access Control    {N findings}  {status}
A02 Cryptographic Failures   {N findings}  {status}
A03 Injection                {N findings}  {status}
A04 Insecure Design          {N findings}  {status}
A05 Security Misconfiguration {N findings} {status}
A06 Vulnerable Components    {N findings}  {status}
A07 Auth Failures            {N findings}  {status}
A08 Integrity Failures       {N findings}  {status}
A09 Logging Failures         {N findings}  {status}
A10 SSRF                     {N findings}  {status}

Status: PASS (no findings), WARN (LOW/MEDIUM only), FAIL (HIGH/CRITICAL)
```
