# VIGIL Cluster: Compliance & Documentation

**Covers:** Regulatory compliance, licensing, documentation completeness, audit trail
**Weight:** 6%
**ID prefix:** VIGIL-COMP

## Deterministic Tools

### License Compliance

```bash
# Check project license
find . -maxdepth 1 -name 'LICENSE*' -o -name 'LICENCE*' -o -name 'COPYING*' 2>/dev/null

# Python dependency licenses
pip-licenses --format=json 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
risky = [d for d in data if any(x in d.get('License','').upper() for x in ['GPL', 'AGPL', 'SSPL', 'UNKNOWN'])]
for d in risky: print(f\"{d['Name']} {d['Version']}: {d['License']}\")
" 2>/dev/null

# NPM dependency licenses
npx license-checker --production --failOn 'GPL-3.0;AGPL-3.0;SSPL' --json 2>/dev/null | head -40
```

### Documentation

```bash
# Key documentation files
for f in README.md CHANGELOG.md CONTRIBUTING.md SECURITY.md docs/ API.md; do
  [ -e "$f" ] && echo "EXISTS: $f" || echo "MISSING: $f"
done

# API documentation
find . -name 'openapi*' -o -name 'swagger*' -o -name '*.apib' | grep -v node_modules 2>/dev/null

# Inline documentation coverage (Python)
grep -rn --include='*.py' -c '""".*"""\|def\s' . --exclude-dir={.venv,node_modules,.git,tests} 2>/dev/null | \
  awk -F: '{files[$1]+=$2} END {for (f in files) print f, files[f]}' | head -10
```

### Audit Trail

```bash
# Audit logging
grep -rn -E 'audit_log|audit_trail|AuditLog|action_log' . \
  --exclude-dir={node_modules,.venv,.git} 2>/dev/null

# Data modification logging
grep -rn --include='*.py' -E 'logger\.(info|warning|error).*\b(create|update|delete|modify)\b' . \
  --exclude-dir={.venv,node_modules,.git} 2>/dev/null
```

### Privacy & Data Protection

```bash
# Privacy policy / data processing
find . -name '*privacy*' -o -name '*gdpr*' -o -name '*dpa*' -o -name '*data-protection*' 2>/dev/null | \
  grep -v node_modules

# Cookie consent
grep -rn -E 'cookie.?consent|cookie.?banner|GDPR|data.?protection' . \
  --exclude-dir={node_modules,.venv,.git} 2>/dev/null

# Data retention configuration
grep -rn -E 'retention|expir|ttl|purge|cleanup.*days' . \
  --exclude-dir={node_modules,.venv,.git} 2>/dev/null
```

## Finding Patterns

### Licensing (VIGIL-COMP-0xx)

| Pattern | Severity |
|---------|----------|
| No LICENSE file | MEDIUM |
| GPL/AGPL dependency in commercial project | HIGH |
| SSPL dependency | HIGH |
| Unknown license on dependency | MEDIUM |
| License incompatibility | HIGH |

### Documentation (VIGIL-COMP-1xx)

| Pattern | Severity |
|---------|----------|
| No README.md | LOW |
| No CHANGELOG.md | LOW |
| No SECURITY.md (reporting process) | MEDIUM |
| No API documentation | MEDIUM |
| Outdated documentation (references removed code) | LOW |

### Audit Trail (VIGIL-COMP-2xx)

| Pattern | Severity |
|---------|----------|
| No audit logging for data modifications | HIGH (for regulated industries) |
| No user action logging | MEDIUM |
| Audit logs without timestamps | MEDIUM |
| Audit logs without user attribution | MEDIUM |
| No log retention policy | LOW |

### Privacy (VIGIL-COMP-3xx)

| Pattern | Severity |
|---------|----------|
| PII collected without privacy policy | HIGH |
| No data retention mechanism | MEDIUM |
| No data export capability (right to portability) | MEDIUM |
| No data deletion capability (right to erasure) | MEDIUM |
| Cross-border data transfer without safeguards | HIGH |

## AI Reasoning Section

1. **Regulatory exposure:** What regulations apply based on the data types and jurisdictions?
2. **License compatibility:** Are all dependency licenses compatible with the project license?
3. **Documentation gaps:** What's most critical for a new developer to understand?
4. **Audit readiness:** Could you pass a SOC2/ISO27001 audit today? What's missing?
5. **Privacy posture:** Does the project handle PII? If so, are GDPR/CCPA basics covered?
