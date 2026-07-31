# VIGIL Domain Detail: Injection Vulnerabilities

**Parent cluster:** injection
**Loaded in:** siege mode, or --only injection --deep

## Deep Checks

### SQL Injection — Union-Based & Blind Patterns

```bash
# Raw string concatenation in queries (all languages)
grep -rn --include="*.py" \
  -E "(execute|executemany|cursor\.execute)\s*\(\s*[f'\"].*(%s|{|format|%)" . 2>/dev/null

# Python — f-string or % format in SQL
grep -rn --include="*.py" \
  -E "SELECT.*\+|INSERT.*\+|UPDATE.*\+|DELETE.*\+" . 2>/dev/null

# JavaScript/TypeScript — template literals in SQL
grep -rn --include="*.js" --include="*.ts" \
  -E "(query|execute|raw)\s*\(\s*\`.*\$\{" . 2>/dev/null

# ORM raw() calls (Django, SQLAlchemy raw text)
grep -rn --include="*.py" \
  -E "\.(raw|execute|text)\s*\(\s*[f'\"]" . 2>/dev/null

# Knex/Sequelize raw queries
grep -rn --include="*.js" --include="*.ts" \
  -E "sequelize\.query\s*\(\s*['\"\`]|knex\.raw\s*\(\s*['\"\`]" . 2>/dev/null

# Time-based blind SQL: SLEEP/WAITFOR in input that reaches DB
grep -rn -E "(SLEEP|WAITFOR|BENCHMARK|pg_sleep)\s*\(" . 2>/dev/null
```

### Command Injection (OS / Shell)

```bash
# Python os.system / subprocess with shell=True + variable
grep -rn --include="*.py" \
  -E "os\.system\s*\(|subprocess\.(run|call|Popen|check_output).*shell\s*=\s*True" . 2>/dev/null

# Python eval/exec on user-controlled input
grep -rn --include="*.py" \
  -E "\b(eval|exec|compile)\s*\(" . 2>/dev/null

# Node.js child_process with variable interpolation
grep -rn --include="*.js" --include="*.ts" \
  -E "(exec|execSync|spawn|spawnSync)\s*\(\s*['\"\`].*\$\{|child_process" . 2>/dev/null

# Shell script variable injection
grep -rn --include="*.sh" \
  -E "\$\{?[A-Za-z_][A-Za-z0-9_]*\}?\s*[|;&]|\`[^']+\`" . 2>/dev/null

# PHP passthru / system / shell_exec
grep -rn --include="*.php" \
  -E "(passthru|system|shell_exec|exec|popen|proc_open)\s*\(\s*\$" . 2>/dev/null
```

### Server-Side Template Injection (SSTI)

```bash
# Jinja2 — render_template_string with user input (CRITICAL)
grep -rn --include="*.py" \
  -E "render_template_string\s*\(" . 2>/dev/null

# Jinja2 — Environment().from_string() with untrusted data
grep -rn --include="*.py" \
  -E "(Environment|Template)\s*\(.*\)\.render|from_string\s*\(" . 2>/dev/null

# Nunjucks/Twig render with user-controlled template string
grep -rn --include="*.js" --include="*.ts" \
  -E "nunjucks\.renderString\s*\(|env\.renderString\s*\(" . 2>/dev/null

# Handlebars compile() with user input
grep -rn --include="*.js" --include="*.ts" \
  -E "Handlebars\.compile\s*\(\s*(req\.|user\.|params\.|body\.)" . 2>/dev/null
```

### LDAP Injection

```bash
# LDAP search filters with unsanitized user input
grep -rn --include="*.py" \
  -E "ldap.*search.*filter.*(%s|\+|format|f['\"])" . 2>/dev/null

grep -rn --include="*.js" --include="*.ts" \
  -E "ldapClient\.(search|bind).*\`|\+.*dn\s*=" . 2>/dev/null

# Missing ldap3/ldapjs escape calls
grep -rn --include="*.py" \
  -E "import ldap3" . 2>/dev/null | \
  xargs -I{} grep -L "escape_filter_chars" {} 2>/dev/null
```

### XPath Injection

```bash
# XPath evaluate / selectNodes with string concatenation
grep -rn --include="*.py" \
  -E "xpath\s*\(.*\+|\.find\s*\(\s*[f'\"].*\{|\.findall\s*\(\s*[f'\"]" . 2>/dev/null

grep -rn --include="*.js" --include="*.ts" \
  -E "evaluate\s*\(\s*['\"\`].*\$\{|selectNodes\s*\(\s*['\"\`].*\+" . 2>/dev/null
```

### Header & Log Injection

```bash
# HTTP response header injection (CRLF injection — \r\n in header values)
grep -rn --include="*.py" \
  -E "response\[.*\]\s*=.*request\.|headers\[.*\]\s*=.*(req\.|user\.|param)" . 2>/dev/null

grep -rn --include="*.js" --include="*.ts" \
  -E "res\.setHeader\s*\(.*req\.|res\.header\s*\(.*req\." . 2>/dev/null

# Log injection (newline characters in logged user data)
grep -rn --include="*.py" \
  -E "(logging|logger)\.(info|debug|warning|error)\s*\(.*\+|%.*\(request\|user\|param" . 2>/dev/null

# Node log injection
grep -rn --include="*.js" --include="*.ts" \
  -E "console\.(log|error|warn|info)\s*\(.*req\.(body|query|params|headers)" . 2>/dev/null
```

## Advanced Patterns

| Injection Type | Severity | Key Indicator | Safe Alternative |
|---|---|---|---|
| SQL via f-string | CRITICAL | `f"SELECT ... {user}"` | Parameterized queries |
| SQL via string concat | CRITICAL | `"SELECT " + user_input` | Prepared statements |
| `shell=True` + var | CRITICAL | `subprocess.run(cmd, shell=True)` | `shlex.split()` + list |
| `os.system()` | CRITICAL | Direct call with variable | `subprocess` with list |
| SSTI `render_template_string` | CRITICAL | Any user data as template | `render_template()` only |
| `eval()` on user input | CRITICAL | `eval(request.args.get(...))` | AST literal_eval max |
| LDAP filter concat | HIGH | `filter = "(&(uid=" + user` | `ldap3.escape_filter_chars()` |
| XPath string concat | HIGH | `"//user[@id='" + id + "']"` | Parameterized XPath |
| Log + CRLF | MEDIUM | `log.info(user_input)` raw | Strip `\r\n` before log |
| ORM `.raw()` + format | HIGH | `.raw(f"... {id}")` | `.raw("... %s", [id])` |
| Header injection | HIGH | `set_header(name, user_val)` | Validate/strip CRLF |
| NoSQL injection (MongoDB) | HIGH | `{"$where": user_input}` | Schema validation |
