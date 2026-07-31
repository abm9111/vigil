# VIGIL Cluster: Security

**Covers:** OWASP Top 10, secrets, dependency vulnerabilities, supply chain, auth/authz
**Weight:** 22% (highest — breaches are existential)
**ID prefix:** VIGIL-SEC

## Deterministic Tools

### Secrets Detection

```bash
# High-signal patterns (fast, no external tool needed)
grep -rn --include='*.py' --include='*.js' --include='*.ts' --include='*.yaml' --include='*.yml' --include='*.json' --include='*.toml' --include='*.cfg' --include='*.ini' \
  -E '(password|passwd|secret|api_key|apikey|token|private_key|access_key|secret_key|auth_token|bearer)\s*[=:]\s*["\x27][A-Za-z0-9+/=_\-]{8,}' . \
  --exclude-dir={node_modules,.venv,vendor,.git,dist,build,__pycache__} 2>/dev/null | head -30

# .env files with values (should be .env.example with placeholders)
find . -name '.env' -not -name '.env.example' -not -path '*node_modules*' -not -path '*.venv*' -exec grep -l '=' {} \; 2>/dev/null

# TruffleHog (if installed — verified secrets only)
trufflehog git file://. --only-verified --json 2>/dev/null | head -20

# FAIL-OPEN DEFAULTS — secrets with fallback values (Trail of Bits pattern)
# These are CRITICAL: app runs insecurely if env var is missing
grep -rn --include='*.py' \
  -E '(os\.getenv|os\.environ\.get)\(.*(secret|key|password|token).*,\s*["\x27][^"\x27]+["\x27]\)' . \
  --exclude-dir={node_modules,.venv,vendor,.git,dist,build,__pycache__} 2>/dev/null | head -20

# Fail-open patterns (JS/TS)
grep -rn --include='*.js' --include='*.ts' \
  -E 'process\.env\.[A-Z_]*(SECRET|KEY|PASSWORD|TOKEN)\s*\|\|\s*["\x27]' . \
  --exclude-dir={node_modules,.git,dist,build} 2>/dev/null | head -20

# Fail-open patterns (Ruby/Go)
grep -rn --include='*.rb' -E 'ENV\.fetch.*default:|ENV\[.*\]\s*\|\|' . --exclude-dir={vendor,.git} 2>/dev/null | head -10
grep -rn --include='*.go' -E 'os\.Getenv.*==\s*"".*=\s*"' . --exclude-dir={vendor,.git} 2>/dev/null | head -10
```

### Static Analysis (SAST)

```bash
# Python — Bandit
bandit -r . -ll --quiet --exclude='./.venv,./node_modules,./tests' -f json 2>&1

# Python — Semgrep (if installed)
semgrep scan --config=auto --json --quiet 2>/dev/null | head -100

# JS/TS — ESLint security plugin
npx eslint . --rule '{"no-eval": "error", "no-implied-eval": "error"}' --format compact 2>&1
```

### Dependency Vulnerabilities

```bash
# Python
pip-audit --format=json 2>&1

# JavaScript
npm audit --json 2>&1

# Go
govulncheck ./... 2>&1 || true

# Rust
cargo audit 2>&1 || true
```

### Injection Patterns

```bash
# SQL injection (Python)
grep -rn --include='*.py' \
  -E '\.execute\(.*f["\x27]|\.execute\(.*%|\.execute\(.*\.format\(|\.execute\(.*\+|\.raw\(' . \
  --exclude-dir={.venv,node_modules,tests,.git} 2>/dev/null

# Command injection
grep -rn --include='*.py' --include='*.js' --include='*.ts' \
  -E 'subprocess\.(call|run|Popen)\(.*shell\s*=\s*True|os\.system\(|child_process\.exec\(' . \
  --exclude-dir={.venv,node_modules,.git} 2>/dev/null

# Path traversal
grep -rn --include='*.py' --include='*.js' --include='*.ts' \
  -E 'open\(.*\+|os\.path\.join\(.*request|fs\.(read|write)File.*req\.' . \
  --exclude-dir={.venv,node_modules,.git} 2>/dev/null

# Template injection
grep -rn --include='*.py' \
  -E 'Template\(.*\+|render_template_string\(|Markup\(' . \
  --exclude-dir={.venv,node_modules,.git} 2>/dev/null
```

### CORS Credential Detection (Bounty-Grade)

```bash
# CORS configuration — look for credential leakage patterns
grep -rn -E 'allow_origins|Access-Control|CORS|cors' . \
  --exclude-dir={node_modules,.venv,.git} 2>/dev/null

# Pattern 1: Origin reflection (server mirrors any Origin header)
grep -rn --include='*.py' --include='*.js' --include='*.ts' --include='*.go' \
  -E 'origin.*header|request\.headers.*origin|Access-Control-Allow-Origin.*req' . \
  --exclude-dir={node_modules,.venv,.git} 2>/dev/null

# Pattern 2: Wildcard with credentials (fatal misconfiguration)
grep -rn -E 'allow_credentials.*[Tt]rue|credentials.*true' . \
  --exclude-dir={node_modules,.venv,.git} 2>/dev/null
grep -rn -E "allow_origins.*\*|Access-Control-Allow-Origin.*\*" . \
  --exclude-dir={node_modules,.venv,.git} 2>/dev/null

# Pattern 3: Null origin allowed (exploitable via sandboxed iframe)
grep -rn -E "null.*origin|origin.*null|allow_origin.*null" . \
  --exclude-dir={node_modules,.venv,.git} 2>/dev/null

# Pattern 4: Regex-based origin check (suffix bypass: evil-target.com matches target.com)
grep -rn --include='*.py' --include='*.js' --include='*.ts' \
  -E '\.endsWith\(|\.match\(.*origin|re\.(match|search).*origin|origin.*\.includes\(' . \
  --exclude-dir={node_modules,.venv,.git} 2>/dev/null

# Pattern 5: CORS middleware with permissive defaults
grep -rn --include='*.py' -E 'CORSMiddleware|add_middleware.*CORS' . \
  --exclude-dir={.venv,.git} 2>/dev/null
grep -rn --include='*.js' --include='*.ts' -E 'require.*cors|import.*cors|app\.use\(cors' . \
  --exclude-dir={node_modules,.git} 2>/dev/null
```

**Live CORS probe** (only for targets in scope with explicit authorization):
```bash
# Test a specific endpoint for CORS misconfig
# curl -sk -H "Origin: https://evil.com" -I {url} | grep -i access-control
# curl -sk -H "Origin: null" -I {url} | grep -i access-control
# curl -sk -H "Origin: https://evil-{domain}" -I {url} | grep -i access-control
```

### Dependency Confusion Detection

```bash
# Python — check for private package names that could be squatted
# Look for packages installed from private index
pip config list 2>/dev/null | grep -i 'index-url\|extra-index'
grep -rn -E 'index-url|extra-index-url|trusted-host' . \
  --exclude-dir={.venv,node_modules,.git} 2>/dev/null

# Check if private package names exist on PyPI (confusion attack surface)
grep -rn --include='*.txt' --include='*.cfg' --include='*.toml' \
  -E '^\s*[a-z][a-z0-9_-]+' requirements*.txt setup.cfg pyproject.toml 2>/dev/null

# JavaScript — check for private scope packages
grep -rn --include='*.json' -E '"@[a-z]+/' package.json 2>/dev/null
grep -rn -E 'registry.*https?://' .npmrc .yarnrc .yarnrc.yml 2>/dev/null

# GitHub Actions — expression injection via pull_request_target
grep -rn -E 'pull_request_target|github\.event\.(issue|pull_request)\.(title|body|head\.ref)' \
  .github/workflows/*.yml 2>/dev/null

# CI/CD pipeline secrets exposure
grep -rn -E 'echo.*\$\{.*SECRET\}|echo.*\$\{.*TOKEN\}|echo.*\$\{.*KEY\}' \
  .github/workflows/*.yml .gitlab-ci.yml Jenkinsfile 2>/dev/null
```

### Auth & Access Control

```bash
# Endpoints without auth decorators (Python/FastAPI)
grep -rn --include='*.py' -E '@(app|router)\.(get|post|put|delete|patch)\(' . \
  --exclude-dir={.venv,node_modules,.git,tests} 2>/dev/null

# Compare with auth-decorated endpoints
grep -rn --include='*.py' -E '(Depends|login_required|requires_auth|authenticate|@auth|@jwt_required)' . \
  --exclude-dir={.venv,node_modules,.git,tests} 2>/dev/null

# CORS configuration (basic — see CORS Credential Detection above for full check)
grep -rn -E 'allow_origins|Access-Control|CORS|cors' . \
  --exclude-dir={node_modules,.venv,.git} 2>/dev/null
```

## Finding Patterns

### Secrets (VIGIL-SEC-0xx)

| Pattern | Severity |
|---------|----------|
| Verified secret (TruffleHog confirmed) | CRITICAL |
| Hardcoded credential in source | HIGH |
| API key in config file (not .env) | HIGH |
| .env file committed to git | CRITICAL |
| Weak/default password in code | HIGH |
| Private key in repository | CRITICAL |
| Fail-open secret fallback (`getenv("SECRET", "default")`) | CRITICAL |
| Fail-open auth bypass (`AUTH_REQUIRED = env.get(X, "false")`) | CRITICAL |
| DB credentials with insecure fallbacks | HIGH |

### Injection (VIGIL-SEC-1xx)

| Pattern | Severity |
|---------|----------|
| SQL injection (string formatting in execute) | CRITICAL |
| Command injection (shell=True + user input) | CRITICAL |
| Template injection (user input in template) | HIGH |
| Path traversal (user input in file path) | HIGH |
| XSS (unescaped user input in HTML) | HIGH |
| LDAP/XML injection | HIGH |

### Auth & Access (VIGIL-SEC-2xx)

| Pattern | Severity |
|---------|----------|
| Endpoint with no auth check | HIGH (CRITICAL if sensitive data) |
| CORS allow_origins = ["*"] | HIGH |
| CORS origin reflection + credentials: true | CRITICAL |
| CORS null origin allowed + credentials: true | HIGH |
| CORS regex suffix bypass (endsWith/includes) | HIGH |
| JWT with no expiry | HIGH |
| Hardcoded JWT secret | CRITICAL |
| Missing CSRF protection | MEDIUM |
| No rate limiting on auth endpoints | MEDIUM |
| Password stored in plaintext | CRITICAL |
| Weak hashing (MD5, SHA1 for passwords) | HIGH |

### Supply Chain (VIGIL-SEC-5xx)

| Pattern | Severity |
|---------|----------|
| Private package name squattable on public registry | CRITICAL |
| Mixed public/private registry without priority | HIGH |
| GitHub Actions expression injection (pull_request_target) | CRITICAL |
| CI/CD secrets echoed to logs | CRITICAL |
| Unpinned GitHub Actions (uses: action@main) | HIGH |
| Dependency installed from HTTP (not HTTPS) | HIGH |
| No lock file for dependencies | MEDIUM |
| .npmrc/.pypirc with credentials | CRITICAL |

### Dependencies (VIGIL-SEC-3xx)

| Pattern | Severity |
|---------|----------|
| Critical CVE in direct dependency | CRITICAL |
| High CVE in direct dependency | HIGH |
| Critical CVE in transitive dependency | HIGH |
| Outdated dependency (>2 major versions behind) | MEDIUM |
| Unpinned dependency version | LOW |
| No lock file | MEDIUM |

### Configuration (VIGIL-SEC-4xx)

| Pattern | Severity |
|---------|----------|
| DEBUG=True in production config | HIGH |
| Verbose error messages to client | MEDIUM |
| HTTPS not enforced | HIGH |
| Insecure cookie settings | MEDIUM |
| Missing security headers (CSP, HSTS, X-Frame) | MEDIUM |
| Exposed admin panel | HIGH |

## AI Reasoning Section

After deterministic tools:

1. **Attack surface mapping:** Which endpoints accept external input? Trace data flow.
2. **Auth coverage:** What % of endpoints have auth? Which sensitive ones don't?
3. **Secret rotation:** Are any detected secrets still valid/active?
4. **Dependency risk:** Are vulnerable dependencies on critical paths?
5. **Defense in depth:** How many layers would an attacker need to bypass?
