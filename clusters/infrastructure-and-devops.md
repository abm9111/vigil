# VIGIL Cluster: Infrastructure & DevOps

**Covers:** Docker, CI/CD, IaC, observability, cost, deployment
**Weight:** 10%
**ID prefix:** VIGIL-INFRA

## Deterministic Tools

### Docker

```bash
# Hadolint (Dockerfile best practices)
find . -name 'Dockerfile*' -not -path '*/node_modules/*' -not -path '*/.venv/*' | \
  xargs -I {} hadolint {} 2>&1

# Docker Compose validation
docker compose config --quiet 2>&1 || docker-compose config --quiet 2>&1

# Running as root check
grep -n 'USER' Dockerfile* 2>/dev/null
# If no USER directive → running as root

# Multi-stage build check
grep -c 'FROM' Dockerfile* 2>/dev/null
# If count = 1 → single stage (not ideal for production)

# HEALTHCHECK presence
grep -n 'HEALTHCHECK' Dockerfile* 2>/dev/null

# Sensitive files in Docker context
cat .dockerignore 2>/dev/null || echo "NO .dockerignore FOUND"
# Check for .env, .git, node_modules, .venv in context
```

### Trivy (Container Scanning)

```bash
# Scan Dockerfile for misconfigs
trivy config Dockerfile --severity HIGH,CRITICAL 2>&1

# Scan built image (if available)
trivy image --severity HIGH,CRITICAL $(docker images --format '{{.Repository}}:{{.Tag}}' | head -1) 2>&1 || true
```

### CI/CD

```bash
# Find CI config files
find . -name '*.yml' -path '*/.github/workflows/*' -o -name '.gitlab-ci.yml' -o -name 'Jenkinsfile' -o -name '.circleci/config.yml' 2>/dev/null

# Check for secret leakage in CI
grep -rn 'echo.*\$.*SECRET\|echo.*\$.*TOKEN\|echo.*\$.*KEY\|echo.*\$.*PASSWORD' .github/ .gitlab-ci* Jenkinsfile 2>/dev/null

# Check for pinned actions (GitHub Actions)
grep -rn 'uses:' .github/workflows/ 2>/dev/null | grep -v '@[a-f0-9]\{40\}\|@v[0-9]' 2>/dev/null

# Check for --no-verify in CI
grep -rn '\-\-no-verify\|--no-gpg-sign\|--force' .github/ .gitlab-ci* Jenkinsfile 2>/dev/null
```

### Observability

```bash
# Logging setup
grep -rn --include='*.py' -E 'import logging|getLogger|structlog|loguru' . \
  --exclude-dir={.venv,node_modules,.git} 2>/dev/null

# Monitoring/metrics
grep -rn -E 'prometheus|datadog|newrelic|sentry|opentelemetry|grafana' . \
  --exclude-dir={node_modules,.venv,.git} 2>/dev/null

# Error tracking
grep -rn -E 'sentry_sdk|bugsnag|rollbar|airbrake' . \
  --exclude-dir={node_modules,.venv,.git} 2>/dev/null
```

## Finding Patterns

### Docker (VIGIL-INFRA-0xx)

| Pattern | Severity |
|---------|----------|
| Running as root (no USER directive) | HIGH |
| No .dockerignore | MEDIUM |
| .env in Docker context (not in .dockerignore) | HIGH |
| No HEALTHCHECK | MEDIUM |
| Single-stage build (dev deps in prod image) | MEDIUM |
| Using `:latest` tag for base image | MEDIUM |
| apt-get without --no-install-recommends | LOW |
| No layer caching optimization | LOW |
| Critical Trivy vulnerability in base image | CRITICAL |
| COPY . . without .dockerignore | HIGH |

### CI/CD (VIGIL-INFRA-1xx)

| Pattern | Severity |
|---------|----------|
| No CI pipeline defined | HIGH |
| Secrets echoed in CI logs | CRITICAL |
| Unpinned GitHub Actions (no SHA) | MEDIUM |
| --no-verify in CI scripts | HIGH |
| No test step in CI | HIGH |
| No security scan step in CI | MEDIUM |
| CI allows force push to main | HIGH |

### Observability (VIGIL-INFRA-2xx)

| Pattern | Severity |
|---------|----------|
| No structured logging | MEDIUM |
| No error tracking (Sentry etc.) | MEDIUM |
| No health check endpoint | MEDIUM |
| No metrics/monitoring | MEDIUM |
| Log level hardcoded (not configurable) | LOW |
| Sensitive data in logs | HIGH |

### Deployment (VIGIL-INFRA-3xx)

| Pattern | Severity |
|---------|----------|
| No environment separation (dev/staging/prod) | HIGH |
| Hardcoded environment-specific values | MEDIUM |
| No rollback mechanism | HIGH |
| No blue-green or canary deployment | LOW |
| Manual deployment process (no automation) | MEDIUM |

## AI Reasoning Section

1. **Container security posture:** Is the Docker image minimal? Could an attacker pivot from container?
2. **CI/CD trust boundary:** What can a PR author execute? Are there privilege escalation paths?
3. **Observability coverage:** If an incident happens at 3am, how fast can you detect and diagnose?
4. **Deployment safety:** What happens if a bad deploy goes out? How fast can you rollback?
5. **Infrastructure as Code:** Is infra reproducible? Any manual snowflake configs?
