# VIGIL Domain Detail: Secrets & Credential Leakage

**Parent cluster:** secrets
**Loaded in:** siege mode, or --only secrets --deep

## Deep Checks

### Entropy-Based Secret Detection

```bash
# High-entropy string detection (Shannon entropy > 4.5 = likely secret)
grep -rn --include="*.py" --include="*.js" --include="*.ts" --include="*.env" \
  -E "['\"][A-Za-z0-9+/]{32,}['\"]" . | \
  python3 -c "
import sys, math, re
for line in sys.stdin:
    m = re.search(r'[A-Za-z0-9+/]{20,}', line)
    if m:
        s = m.group()
        freq = {c: s.count(c)/len(s) for c in set(s)}
        ent = -sum(p * math.log2(p) for p in freq.values())
        if ent > 4.5: print(f'ENTROPY={ent:.2f} {line.rstrip()}')
"

# Use trufflehog for git history scanning (most thorough)
trufflehog git file://. --only-verified 2>/dev/null || \
  trufflehog git file://. --no-verification 2>/dev/null

# gitleaks on full history
gitleaks detect --source . --log-opts="--all" -v 2>/dev/null || \
  gitleaks detect --source . 2>/dev/null
```

### AWS Credential Patterns

```bash
# AWS Access Key ID: AKIA[0-9A-Z]{16}
grep -rn --include="*.py" --include="*.js" --include="*.ts" --include="*.json" \
  --include="*.yaml" --include="*.yml" --include="*.env" --include="*.conf" \
  -E "(AKIA|ASIA|ABIA|ACCA)[0-9A-Z]{16}" . 2>/dev/null

# AWS Secret Access Key (40-char base64)
grep -rn -E "aws_secret_access_key\s*=\s*[A-Za-z0-9/+]{40}" . 2>/dev/null

# AWS session tokens (long base64 blobs)
grep -rn -E "aws_session_token\s*=\s*[A-Za-z0-9/+=]{100,}" . 2>/dev/null

# Check ~/.aws/credentials leaking into repo
find . -name "credentials" -path "*/.aws/*" 2>/dev/null
find . -name "*.pem" -o -name "*.p12" -o -name "*.pfx" 2>/dev/null | grep -v node_modules
```

### GCP Service Account Patterns

```bash
# GCP service account JSON (contains "private_key_id")
grep -rn --include="*.json" \
  -E "\"private_key_id\"\s*:\s*\"[a-f0-9]{40}\"" . 2>/dev/null

# GCP API keys (AIza prefix)
grep -rn -E "AIza[0-9A-Za-z_-]{35}" . 2>/dev/null

# GCP OAuth client secrets
grep -rn -E "\"client_secret\"\s*:\s*\"[A-Za-z0-9_-]{24,}\"" . 2>/dev/null
```

### Azure & Other Cloud Patterns

```bash
# Azure connection strings
grep -rn -E "DefaultEndpointsProtocol=https;AccountName=[^;]+;AccountKey=[A-Za-z0-9+/=]{88}" . 2>/dev/null

# Azure SAS tokens
grep -rn -E "sv=20[0-9]{2}.*sig=[A-Za-z0-9%+/=]{43,}" . 2>/dev/null

# Azure client secrets / tenant IDs
grep -rn -E "client_secret.*[A-Za-z0-9._~-]{34,}" . 2>/dev/null

# Stripe keys
grep -rn -E "(sk|pk|rk)_(test|live)_[A-Za-z0-9]{24,}" . 2>/dev/null

# GitHub tokens (ghp_, gho_, ghs_, ghu_)
grep -rn -E "gh[pousr]_[A-Za-z0-9]{36,}" . 2>/dev/null
```

### JWT Analysis

```bash
# Find JWTs hardcoded in source (base64url.base64url.base64url)
grep -rn -E "eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}" . 2>/dev/null

# Decode and inspect JWT claims (check alg, exp, iss)
python3 -c "
import base64, json, sys
token = sys.argv[1] if len(sys.argv) > 1 else input('JWT: ')
parts = token.split('.')
for i, part in enumerate(parts[:2]):
    pad = 4 - len(part) % 4
    data = base64.urlsafe_b64decode(part + '=' * pad)
    print(f'Part {i}: {json.dumps(json.loads(data), indent=2)}')
" 2>/dev/null

# Check for weak JWT secrets in config
grep -rn -E "(jwt|secret|signing)[_-]?(key|secret)\s*[=:]\s*['\"][^'\"]{1,20}['\"]" . 2>/dev/null
```

### Certificate and PEM File Scanning

```bash
# Find private keys committed to repo
grep -rn "BEGIN.*PRIVATE KEY" . 2>/dev/null
grep -rn "BEGIN RSA PRIVATE KEY" . 2>/dev/null
grep -rn "BEGIN EC PRIVATE KEY" . 2>/dev/null
find . -name "*.key" -o -name "*.pem" -o -name "*.crt" 2>/dev/null | grep -v node_modules

# Check .gitignore actually excludes secrets
cat .gitignore 2>/dev/null | grep -E "(\.env|\.key|\.pem|secret|credential|password)"
# Warn if .env is NOT in .gitignore
grep -q "\.env" .gitignore 2>/dev/null || echo "WARNING: .env not in .gitignore"
```

### Environment Variable Leakage Patterns

```bash
# os.environ without defaults (may crash if secret missing = var used but not declared)
grep -rn --include="*.py" -E "os\.environ\[[\'\"]" . 2>/dev/null

# Secrets passed as CLI args (visible in ps aux)
grep -rn -E "(subprocess|exec|spawn).*password|secret|key|token" . 2>/dev/null

# Secrets in Docker ENV / ARG (baked into image metadata)
grep -rn --include="Dockerfile*" -E "^(ENV|ARG)\s+(PASSWORD|SECRET|KEY|TOKEN|PASS)" . 2>/dev/null

# Logging of secrets
grep -rn -E "(log|print|console)\.(debug|info|warn|error|log).*\b(password|secret|token|key|auth)\b" . 2>/dev/null
```

## Advanced Patterns

| Pattern | Severity | Regex |
|---|---|---|
| AWS AKIA key literal | CRITICAL | `AKIA[0-9A-Z]{16}` |
| GCP service account JSON | CRITICAL | `"private_key_id"` in JSON |
| Private key PEM | CRITICAL | `BEGIN.*PRIVATE KEY` |
| JWT with alg:none | CRITICAL | header `"alg":"none"` |
| Hardcoded JWT token | HIGH | `eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+` |
| Stripe live key | HIGH | `sk_live_[A-Za-z0-9]{24,}` |
| GitHub PAT | HIGH | `ghp_[A-Za-z0-9]{36,}` |
| Slack bot token | HIGH | `xoxb-[0-9]+-[A-Za-z0-9]+` |
| Generic API key in env | MEDIUM | `API_KEY\s*=\s*\S{16,}` |
| Short JWT secret | MEDIUM | jwt secret < 20 chars |
| Secret in log statement | MEDIUM | `log.*password` |
| .env not gitignored | MEDIUM | missing `.env` in `.gitignore` |
| Entropy > 4.5 in string literal | LOW-HIGH | calculated per string |
