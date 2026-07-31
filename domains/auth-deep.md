# VIGIL Domain Detail: Authentication & Authorization

**Parent cluster:** auth
**Loaded in:** siege mode, or --only auth --deep

## Deep Checks

### Session Management — Fixation & Hijacking

```bash
# Session fixation: session ID not regenerated on login
grep -rn --include="*.py" \
  -E "session\[|session\.update|flask\.session" . 2>/dev/null | \
  grep -v "session_id\|session\.regenerate\|new_session"

# Express.js — missing session regeneration after login
grep -rn --include="*.js" --include="*.ts" \
  -E "req\.session\.(user|userId|authenticated)\s*=" . 2>/dev/null | \
  xargs grep -L "req.session.regenerate\|session.destroy" 2>/dev/null

# Insecure cookie flags
grep -rn --include="*.py" \
  -E "set_cookie\s*\(|response\.set_cookie\s*\(" . 2>/dev/null | \
  grep -v "httponly\|secure\|samesite" | head -20

# Django SESSION_COOKIE_SECURE / HTTPONLY check
grep -rn --include="*.py" \
  -E "SESSION_COOKIE_SECURE\s*=\s*False|SESSION_COOKIE_HTTPONLY\s*=\s*False" . 2>/dev/null

# Session expiry — missing or too long
grep -rn --include="*.py" --include="*.js" --include="*.ts" \
  -E "maxAge\s*:\s*[0-9]{8,}|PERMANENT_SESSION_LIFETIME" . 2>/dev/null
```

### JWT Vulnerabilities

```bash
# Algorithm confusion — accepting 'none' algorithm
grep -rn --include="*.py" \
  -E "jwt\.decode\s*\(.*algorithms\s*=\s*\[.*none|options\s*=\s*\{.*verify_signature.*False" . 2>/dev/null

# PyJWT — missing algorithms parameter (defaults to ALL, including none)
grep -rn --include="*.py" \
  -E "jwt\.decode\s*\([^)]*\)" . 2>/dev/null | grep -v "algorithms="

# Symmetric secret used instead of asymmetric (weak if secret leaked)
grep -rn --include="*.py" --include="*.js" --include="*.ts" \
  -E "jwt\.(sign|encode)\s*\(.*HS256|algorithm.*=.*['\"]HS256['\"]" . 2>/dev/null

# No expiry on JWT (missing 'exp' claim)
grep -rn --include="*.py" \
  -E "jwt\.(encode|decode)" . 2>/dev/null | grep -v "exp\|expires"

# JWT secret hardcoded or weak
grep -rn --include="*.py" --include="*.js" --include="*.ts" \
  -E "(SECRET_KEY|JWT_SECRET|jwt_secret)\s*[=:]\s*['\"][^'\"]{1,30}['\"]" . 2>/dev/null

# Node.js jsonwebtoken — missing verify options
grep -rn --include="*.js" --include="*.ts" \
  -E "jwt\.verify\s*\(\s*token\s*,\s*[^,)]+\s*\)" . 2>/dev/null | \
  grep -v "algorithms\|clockTolerance\|maxAge"
```

### OAuth Misconfiguration

```bash
# Missing state parameter (CSRF in OAuth flow)
grep -rn --include="*.py" --include="*.js" --include="*.ts" \
  -E "oauth.*authorize|redirect.*oauth" . 2>/dev/null | grep -v "state"

# Open redirects in OAuth callback
grep -rn --include="*.py" \
  -E "redirect_uri\s*=\s*(request\.|req\.|params\.|args\.)" . 2>/dev/null

# Client secret in frontend code / public config
grep -rn --include="*.js" --include="*.ts" \
  -E "client_secret\s*[:=]\s*['\"][^'\"]{10,}['\"]" . \
  --include="*.json" 2>/dev/null

# Scope overpermission
grep -rn -E "scope.*['\"].*admin.*['\"]|scope.*write:.*['\"]|scope.*delete" . 2>/dev/null
```

### Password Storage

```bash
# bcrypt cost factor (should be >= 12 for production)
grep -rn --include="*.py" \
  -E "bcrypt\.(hashpw|hash)\s*\(.*rounds\s*=\s*[0-9]+" . 2>/dev/null | \
  grep -E "rounds\s*=\s*([0-9]|1[01])\b"  # flag < 12

# argon2 parameters
grep -rn --include="*.py" \
  -E "PasswordHasher\s*\(|argon2\.(hash|verify)" . 2>/dev/null

# Plaintext password storage
grep -rn --include="*.py" \
  -E "password\s*=\s*user_password|password\s*=\s*request\.form|password.*=.*plain" . 2>/dev/null

# MD5 or SHA1 for passwords (NEVER acceptable)
grep -rn --include="*.py" --include="*.js" --include="*.ts" \
  -E "hashlib\.(md5|sha1)\s*\(.*password|md5\s*\(.*password|sha1\s*\(.*password" . 2>/dev/null

# Django: PASSWORD_HASHERS using MD5
grep -rn --include="*.py" \
  -E "UnsaltedMD5PasswordHasher|MD5PasswordHasher" . 2>/dev/null
```

### MFA Bypass Patterns

```bash
# MFA check skippable via parameter
grep -rn --include="*.py" --include="*.js" --include="*.ts" \
  -E "mfa_required\s*=.*request\.|skip_mfa\s*=|bypass.*mfa\|mfa.*bypass" . 2>/dev/null

# TOTP without replay protection (no used-token store)
grep -rn --include="*.py" \
  -E "totp\.verify\s*\(" . 2>/dev/null | xargs grep -L "used_tokens\|redis\|cache" 2>/dev/null

# OTP sent over insecure channel
grep -rn --include="*.py" --include="*.js" \
  -E "otp.*sms\|twilio.*otp\|send_otp" . 2>/dev/null | grep -v "https\|TLS"
```

### Privilege Escalation Paths

```bash
# Role/permission checks missing on sensitive endpoints
grep -rn --include="*.py" \
  -E "@app\.route.*admin|@router\.(get|post|put|delete).*admin" . 2>/dev/null | \
  xargs grep -L "require_role\|admin_required\|permission_required\|is_admin" 2>/dev/null

# IDOR — using user-provided ID without ownership check
grep -rn --include="*.py" \
  -E "db.*get\s*\(\s*(request\.|req\.|args\.|params\.)" . 2>/dev/null | \
  grep -v "user_id\s*==\s*current_user\|owner\|created_by"

# JWT role in payload without server-side verification
grep -rn --include="*.py" --include="*.js" --include="*.ts" \
  -E "decoded\[.*(role|admin|permission)\]|payload\.(role|admin)\s*==" . 2>/dev/null
```

## Advanced Patterns

| Vulnerability | Severity | Signal | Fix |
|---|---|---|---|
| JWT alg:none accepted | CRITICAL | `algorithms=` missing or includes `none` | Explicit allowlist `["RS256"]` |
| No `exp` in JWT | HIGH | `jwt.encode()` without `exp` key | Always set `exp = now + timedelta` |
| bcrypt rounds < 12 | HIGH | `rounds=10` or lower | Increase to 12+ (adds ~250ms) |
| MD5/SHA1 passwords | CRITICAL | `hashlib.md5(password)` | Switch to argon2id or bcrypt |
| Session not regenerated | HIGH | Login without `session.regenerate()` | Regenerate on every privilege change |
| Missing `httponly` cookie | HIGH | `set_cookie()` without `httponly=True` | Add `httponly=True, secure=True, samesite='Strict'` |
| OAuth missing state param | HIGH | OAuth redirect without `state=` | Generate and verify CSRF state token |
| IDOR without ownership check | HIGH | `db.get(request.args['id'])` | Always filter by `current_user.id` |
| Hardcoded JWT secret | CRITICAL | Short literal in source | Load from env, rotate regularly |
| Role from JWT payload only | HIGH | `if payload['role'] == 'admin'` | Verify role from DB, not token |
| TOTP no replay protection | MEDIUM | No token blacklist | Store used OTPs for 30s window |
