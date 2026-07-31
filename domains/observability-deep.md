# VIGIL Domain Detail: Observability & Monitoring Security

**Parent cluster:** observability
**Loaded in:** siege mode, or --only observability --deep

## Deep Checks

### Structured Logging Completeness

```bash
# Python — check for unstructured logging (plain string interpolation)
grep -rn --include="*.py" \
  -E "(logging|logger)\.(debug|info|warning|error|critical)\s*\(\s*[f'\"]" . 2>/dev/null | \
  grep -v "extra\s*=" | head -20  # No 'extra' dict = no structured fields

# Check for structlog / python-json-logger usage
grep -rn --include="*.py" -E "import structlog|from structlog|JsonFormatter" . 2>/dev/null || \
  echo "INFO: No structured logging library detected (structlog/python-json-logger)"

# Node.js — check for pino/winston structured logging
grep -rn --include="*.js" --include="*.ts" \
  -E "import.*pino|require.*pino|import.*winston|import.*bunyan" . 2>/dev/null || \
  echo "INFO: No structured logger detected — plain console.log is unstructured"

# Check log format in production config
grep -rn --include="*.py" --include="*.json" --include="*.yaml" \
  -E "(LOG_FORMAT|log_format|logging\.basicConfig).*json\|%(message)s" . 2>/dev/null | head -10

# Missing request correlation IDs (no traceability across services)
grep -rn --include="*.py" \
  -E "x.request.id|correlation.id|trace.id|request_id" . 2>/dev/null || \
  echo "INFO: No correlation ID pattern found in logs"
```

### PII Detection in Logs

```bash
# Email addresses logged
grep -rn --include="*.py" \
  -E "(log|logger)\.(info|debug|warning|error).*email\|print.*@.*\." . 2>/dev/null | head -10

# Phone numbers / SSN patterns in log calls
grep -rn --include="*.py" --include="*.js" --include="*.ts" \
  -E "(log|console)\.(log|info|error)\s*\(.*\b(phone|mobile|ssn|dob|passport|national_id)\b" \
  . 2>/dev/null | head -10

# Password/token logging (most critical PII leak)
grep -rn --include="*.py" --include="*.js" --include="*.ts" \
  -E "(log|console|print)\s*[\.(].*\b(password|passwd|token|secret|credit_card|cvv|card_number)\b" \
  . 2>/dev/null | head -20

# Request body logged wholesale (may contain PII/secrets)
grep -rn --include="*.py" \
  -E "(log|logger)\.(debug|info)\s*\(.*request\.(body|json|form|data)\|request\.get_json" . 2>/dev/null

# Check Sentry / error reporter sending PII
grep -rn --include="*.py" \
  -E "sentry_sdk\.(capture_exception|capture_message|set_user)" . 2>/dev/null | \
  xargs grep -B 5 -A 5 "set_user\|before_send" 2>/dev/null | head -30
```

### Log Injection Attacks

```bash
# CRLF / newline injection in logged user data
grep -rn --include="*.py" \
  -E "(log|logger)\.(info|debug|warning|error)\s*\(.*\+\s*(request\.|req\.|user\.|param)" \
  . 2>/dev/null | head -10

# Node.js log injection
grep -rn --include="*.js" --include="*.ts" \
  -E "console\.(log|error|warn|info)\s*\(\s*['\"\`].*\+\s*req\.(body|query|params|headers)" \
  . 2>/dev/null | head -10

# Log4Shell pattern (though primarily Java — check if any Java log4j dependencies)
find . -name "*.jar" 2>/dev/null | xargs -I{} unzip -l {} 2>/dev/null | \
  grep -i "log4j" | head -5

# Template injection via log messages (Python logging % format)
grep -rn --include="*.py" \
  -E "logger\.(info|debug|warning|error)\s*\(\s*['\"]%s['\"].*%\s*(request\.|user_input\|param)" \
  . 2>/dev/null
```

### Monitoring Blind Spots

```bash
# Unmonitored exception handlers (silent swallowing)
grep -rn --include="*.py" \
  -E "except\s*(\w+\s*)?:\s*pass$|except\s*(\w+\s*)?:\s*$" . 2>/dev/null | head -20

# Missing error monitoring on critical paths
grep -rn --include="*.py" \
  -E "def\s+(login|authenticate|payment|transfer|withdraw|deposit)\s*\(" . 2>/dev/null | \
  xargs grep -L "sentry\|monitor\|alert\|metric\|statsd\|prometheus" 2>/dev/null | head -10

# No health check endpoint
grep -rn --include="*.py" \
  -E "@.*route.*/health|@.*get.*/health|@.*health" . 2>/dev/null || \
  echo "WARNING: No health check endpoint found"

# Missing liveness/readiness in k8s/docker-compose
grep -rn --include="docker-compose*.yml" --include="*.yaml" \
  -E "healthcheck:|livenessProbe:|readinessProbe:" . 2>/dev/null || \
  echo "WARNING: No container health checks configured"

# Database query timing not tracked
grep -rn --include="*.py" \
  -E "cursor\.execute\s*\(|\.query\s*\(" . 2>/dev/null | \
  xargs grep -L "time\|timing\|duration\|latency\|histogram" 2>/dev/null | head -10
```

### Alerting Coverage

```bash
# Check for alert configurations (Prometheus alertmanager, PagerDuty, etc.)
find . -name "alertmanager*.yml" -o -name "alerts*.yaml" -o -name "alert_rules*" \
  2>/dev/null | head -10

# Prometheus — check critical alert rules exist
grep -rn --include="*.yml" --include="*.yaml" \
  -E "alert:\s*(HighErrorRate|DatabaseDown|HighLatency|OutOfMemory|DiskSpaceLow)" \
  . 2>/dev/null

# Check for dead man's switch / watchdog alert (catches total monitoring failure)
grep -rn --include="*.yml" --include="*.yaml" \
  -E "Watchdog|DeadMansSwitch|always_firing" . 2>/dev/null || \
  echo "INFO: No watchdog/dead-man's-switch alert found"

# Sentry alert rules
grep -rn --include="*.py" \
  -E "sentry_sdk\.init\s*\(" . 2>/dev/null | \
  xargs grep -A 10 "sentry_sdk.init" 2>/dev/null | \
  grep -E "traces_sample_rate|profiles_sample_rate|environment"
```

### Distributed Tracing

```bash
# OpenTelemetry configuration
grep -rn --include="*.py" --include="*.js" --include="*.ts" \
  -E "opentelemetry|from opentelemetry|require.*@opentelemetry" . 2>/dev/null || \
  echo "INFO: No OpenTelemetry instrumentation found"

# Jaeger / Zipkin / Datadog tracing
grep -rn --include="*.py" \
  -E "jaeger|zipkin|datadog\.(trace|api)|from ddtrace" . 2>/dev/null

# W3C trace context propagation
grep -rn --include="*.py" --include="*.js" --include="*.ts" \
  -E "traceparent|tracestate|X-B3-|X-Amzn-Trace" . 2>/dev/null || \
  echo "INFO: No distributed trace header propagation found"

# Async task tracing (Celery, background jobs)
grep -rn --include="*.py" \
  -E "@app\.task|@celery\.task|@shared_task" . 2>/dev/null | \
  xargs grep -L "bind=True\|request\.id\|correlation" 2>/dev/null | head -10
```

### Error Rate Tracking & SLO/SLI Measurement

```bash
# Prometheus metrics — check for RED method (Rate/Errors/Duration)
grep -rn --include="*.py" \
  -E "Counter\s*\(|Histogram\s*\(|Summary\s*\(|Gauge\s*\(" . 2>/dev/null | \
  grep -E "request|error|latency|duration" | head -20

# Check for SLO/SLI definitions
find . -name "slo*.yaml" -o -name "sli*.yaml" -o -name "*.slo" 2>/dev/null | head -5
grep -rn --include="*.yml" --include="*.yaml" \
  -E "slo:|objective:|error_budget:" . 2>/dev/null | head -10

# FastAPI / Flask — check metrics middleware
grep -rn --include="*.py" \
  -E "PrometheusMiddleware|prometheus_fastapi_instrumentator|flask_prometheus" . 2>/dev/null || \
  echo "INFO: No Prometheus middleware found — API metrics not auto-instrumented"

# Check p99 latency tracking (not just average)
grep -rn --include="*.py" \
  -E "Histogram.*observe\|Summary.*observe\|\.timing\s*\(" . 2>/dev/null | head -10

# Error budget burn rate alerts
grep -rn --include="*.yml" --include="*.yaml" \
  -E "burn_rate|error_budget\|slo_violation" . 2>/dev/null | head -5
```

## Advanced Patterns

| Gap | Severity | Signal | Fix |
|---|---|---|---|
| PII in error logs | HIGH | `logger.error(user_email)` or full request body | Scrub PII; use `before_send` hook in Sentry |
| Password/token logged | CRITICAL | `log.debug(password=...)` | Remove immediately; rotate leaked secrets |
| Silent exception swallow | HIGH | `except: pass` on critical path | At minimum log with `logger.exception()` |
| No structured logging | MEDIUM | `logging.info(f"User {id}")` | Add structlog/python-json-logger with fields |
| CRLF in user data logged | HIGH | `log(user_input)` raw | Strip `\r\n` or use structured fields only |
| No health check endpoint | HIGH | Missing `/health` or `/healthz` | Add liveness + readiness endpoints |
| No distributed tracing | MEDIUM | No OpenTelemetry/Jaeger | Add OTEL SDK + trace context propagation |
| No correlation ID | MEDIUM | No `request_id` in logs | Generate UUID per request, propagate via middleware |
| No error rate metric | HIGH | Missing Prometheus Counter for 5xx | Add RED method metrics to all endpoints |
| No watchdog alert | HIGH | Monitoring could silently fail | Add `always_firing` Alertmanager rule |
| `ACTIONS_STEP_DEBUG` logs secrets | HIGH | Debug mode enabled | Disable; use Sentry/OpenTelemetry instead |
| Sentry missing `before_send` | MEDIUM | Raw exceptions with user data | Add `before_send` to scrub PII from events |
| No SLO definitions | MEDIUM | No SLO/SLI YAML files | Define availability and latency targets |
