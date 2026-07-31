# VIGIL Domain Detail: Dependency Security Analysis

**Parent cluster:** deps
**Loaded in:** siege mode, or --only deps --deep

## Deep Checks

### Transitive Dependency Depth & Bloat

```bash
# Python — show full dependency tree (transitive)
pip install pipdeptree 2>/dev/null
pipdeptree --warn silence 2>/dev/null | head -100

# Show packages with the most transitive deps (bloat signal)
pipdeptree --json 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
for pkg in sorted(data, key=lambda x: len(x.get('dependencies',[])), reverse=True)[:15]:
    print(f\"{len(pkg.get('dependencies',[]))} deps: {pkg['package_name']}=={pkg['installed_version']}\")
"

# Node.js — transitive depth analysis
npm ls --all 2>/dev/null | grep -E "^.{0,60}$" | wc -l
npm ls --all --depth=10 2>/dev/null | grep "deduped\|UNMET" | head -20

# Check for dependency hell (version conflicts)
pip check 2>/dev/null
npm ls 2>/dev/null | grep -E "UNMET|invalid" | head -20
```

### Outdated Critical Dependencies

```bash
# Python — outdated packages with CVE potential
pip list --outdated 2>/dev/null | \
  grep -iE "flask|django|fastapi|sqlalchemy|requests|cryptography|pillow|pyjwt|paramiko|celery"

# pip-audit — known CVEs in installed packages
pip-audit 2>/dev/null || pip install pip-audit && pip-audit

# Node.js — npm audit with severity filter
npm audit --json 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
vulns = data.get('vulnerabilities', {})
for name, v in vulns.items():
    sev = v.get('severity','')
    if sev in ('high','critical'):
        print(f'[{sev.upper()}] {name}: {v.get(\"title\",\"\")}')
" 2>/dev/null || npm audit

# Check if requirements.txt pins exact versions (no ranges = reproducible builds)
grep -E "^[A-Za-z]" requirements.txt 2>/dev/null | grep -v "==" | \
  grep -v "^#" | head -20  # These are unpinned
```

### Known Malicious Package Detection

```bash
# Python typosquatting — common malicious package name patterns
python3 -c "
import subprocess, re
result = subprocess.run(['pip', 'list', '--format=freeze'], capture_output=True, text=True)
malicious_patterns = [
    r'python-binance(?!$)', r'colourama', r'crypt0', r'reque5ts',
    r'urllib4', r'botocore3', r'setup-tools', r'pip-tools2',
    r'opencve', r'seti0ols', r'loguru2', r'fastapi2',
]
for line in result.stdout.splitlines():
    pkg = line.split('==')[0].lower()
    for pattern in malicious_patterns:
        if re.search(pattern, pkg):
            print(f'SUSPICIOUS: {line}')
"

# Node.js — check for known malicious packages (cross-reference with npm)
node -e "
const fs = require('fs');
try {
  const lock = JSON.parse(fs.readFileSync('package-lock.json', 'utf8'));
  const pkgs = Object.keys(lock.packages || lock.dependencies || {});
  const suspicious = ['crossenv', 'event-stream', 'eslint-scope', 'getcookies',
    'flatmap-stream', 'rc', 'node-ipc', 'colors', 'faker'];
  pkgs.forEach(p => {
    const name = p.replace('node_modules/', '');
    if (suspicious.includes(name)) console.log('KNOWN MALICIOUS:', name);
  });
} catch(e) { console.log('No package-lock.json'); }
" 2>/dev/null
```

### Typosquatting Detection

```bash
# Compare installed packages against known good names (edit distance check)
python3 -c "
import subprocess
popular = ['requests', 'boto3', 'flask', 'django', 'numpy', 'pandas', 'pillow',
           'cryptography', 'pyjwt', 'sqlalchemy', 'celery', 'redis', 'fastapi',
           'uvicorn', 'httpx', 'aiohttp', 'click', 'pydantic', 'pytest']

result = subprocess.run(['pip', 'list', '--format=freeze'], capture_output=True, text=True)
installed = [l.split('==')[0].lower() for l in result.stdout.splitlines()]

def levenshtein(a, b):
    if len(a) < len(b): return levenshtein(b, a)
    if not b: return len(a)
    row = range(len(b) + 1)
    for c in a:
        row = [min(r + 1, prev + 1, row[j] + (c != b[j-1]))
               for j, (r, prev) in enumerate(zip(row[1:], row), 1)]
    return row[-1]

for pkg in installed:
    for pop in popular:
        if pkg != pop and levenshtein(pkg, pop) == 1:
            print(f'TYPOSQUAT?: {pkg} (similar to {pop})')
" 2>/dev/null
```

### License Chain Analysis

```bash
# Python license audit (GPL contamination check)
pip install pip-licenses 2>/dev/null
pip-licenses --format=csv 2>/dev/null | \
  grep -iE "GPL|AGPL|LGPL|CC-BY-SA" | \
  grep -v "^Package" | head -20

# Node.js license check
npm install -g license-checker 2>/dev/null
license-checker --csv --failOn "GPL-2.0;GPL-3.0;AGPL-3.0" 2>/dev/null | head -20

# Find packages with no license (risk: proprietary by default)
pip-licenses --format=csv 2>/dev/null | grep ",UNKNOWN\|,," | head -10
```

### Phantom Dependency Detection

```bash
# Python — imports not in requirements.txt (phantom = works locally, breaks in prod)
python3 -c "
import ast, os, subprocess, sys

# Get all imports from Python files
imports = set()
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in ['.venv', 'venv', '__pycache__', 'node_modules']]
    for f in files:
        if f.endswith('.py'):
            try:
                with open(os.path.join(root, f)) as fh:
                    tree = ast.parse(fh.read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names: imports.add(alias.name.split('.')[0])
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        imports.add(node.module.split('.')[0])
            except: pass

# Get declared requirements
req_pkgs = set()
try:
    with open('requirements.txt') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                import re
                m = re.match(r'[A-Za-z0-9_-]+', line)
                if m: req_pkgs.add(m.group().lower().replace('-','_'))
except: pass

stdlib = sys.stdlib_module_names if hasattr(sys, 'stdlib_module_names') else set()
for imp in sorted(imports - stdlib):
    if imp.lower().replace('-','_') not in req_pkgs and not imp.startswith('_'):
        print(f'PHANTOM IMPORT: {imp}')
" 2>/dev/null | head -30

# Node.js phantom deps (used but not in package.json)
node -e "
const fs = require('fs'), path = require('path');
const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'));
const declared = new Set([
  ...Object.keys(pkg.dependencies || {}),
  ...Object.keys(pkg.devDependencies || {}),
  ...Object.keys(pkg.peerDependencies || {})
]);
const required = new Set();
const walk = (dir) => {
  try { fs.readdirSync(dir).forEach(f => {
    const full = path.join(dir, f);
    if (f === 'node_modules' || f.startsWith('.')) return;
    try { const stat = fs.statSync(full);
      if (stat.isDirectory()) walk(full);
      else if (f.match(/\.(js|ts|mjs)$/)) {
        const src = fs.readFileSync(full, 'utf8');
        const re = /require\(['\"]([@a-z0-9._-]+)/g; let m;
        while ((m = re.exec(src)) !== null) {
          const dep = m[1].startsWith('@') ? m[1].split('/').slice(0,2).join('/') : m[1];
          if (!dep.startsWith('.')) required.add(dep);
        }
      }
    } catch(e) {}
  }); } catch(e) {}
};
walk('.');
required.forEach(dep => { if (!declared.has(dep)) console.log('PHANTOM:', dep); });
" 2>/dev/null | head -30
```

### Lockfile Integrity

```bash
# Verify package-lock.json not tampered (check integrity hashes present)
node -e "
const lock = require('./package-lock.json');
const pkgs = lock.packages || {};
let missing = 0;
Object.entries(pkgs).forEach(([k, v]) => {
  if (k && !v.integrity) { console.log('MISSING INTEGRITY:', k); missing++; }
});
console.log(missing ? \`WARNING: \${missing} packages missing integrity hashes\` : 'OK: all integrity hashes present');
" 2>/dev/null

# Python — check poetry.lock or pip hashes
grep -c "sha256:" poetry.lock 2>/dev/null && echo "Poetry lockfile has hashes" || true
grep -E "^[A-Za-z].*==" requirements.txt 2>/dev/null | grep -v "sha256" | \
  echo "WARNING: requirements.txt lacks --hash verification"

# Detect lockfile not committed (drift risk)
git ls-files package-lock.json poetry.lock requirements.txt 2>/dev/null | wc -l
```

## Advanced Patterns

| Risk | Severity | Indicator | Action |
|---|---|---|---|
| CVE in direct dep | CRITICAL | `pip-audit` or `npm audit` hit | Update immediately, check API compat |
| CVE in transitive dep | HIGH | Indirect chain | Force version constraint or replace top dep |
| Unpinned version | MEDIUM | `requests>=2.0` not `==2.31.0` | Pin exact in production `requirements.txt` |
| GPL in commercial project | HIGH | `pip-licenses` shows GPL | Replace or obtain commercial license |
| No lockfile committed | HIGH | `package-lock.json` not in git | `git add package-lock.json` |
| Phantom import | HIGH | Used but not declared | Add to requirements and test |
| Typosquatting (edit dist 1) | HIGH | Package name 1 char off popular | Verify publisher on PyPI/npm |
| Missing integrity hash | MEDIUM | `npm ls` missing SRI | `npm install --prefer-offline` with lock |
| Unpublished package | HIGH | `npm ls` shows 404 or missing | Replace with maintained alternative |
