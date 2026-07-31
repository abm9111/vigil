# VIGIL Domain Detail: Supply Chain Deep Analysis

**Parent cluster:** Security
**Loaded in:** siege mode, or `--only security --deep`
**Replaces:** Basic pip-audit/npm-audit checks with per-dependency risk assessment

## Per-Dependency Risk Assessment

For each direct dependency, evaluate using `gh` CLI:

### Step 1: Extract Dependencies

```bash
# Python
cat requirements.txt pyproject.toml 2>/dev/null | grep -E '^\w|dependencies' | head -50

# JavaScript
cat package.json 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); [print(k) for k in {**d.get('dependencies',{}), **d.get('devDependencies',{})}.keys()]" 2>/dev/null

# Go
cat go.mod 2>/dev/null | grep -E '^\t' | awk '{print $1}' | head -50

# Rust
cat Cargo.toml 2>/dev/null | grep -E '^\w.*=' | head -50
```

### Step 2: Per-Dependency Risk Check

For each dependency, query GitHub:

```bash
# Get repo info (stars, forks, updated_at, archived)
gh api repos/{owner}/{repo} --jq '{stars: .stargazers_count, forks: .forks_count, updated: .updated_at, archived: .archived, license: .license.spdx_id}' 2>/dev/null

# Get contributor count
gh api repos/{owner}/{repo}/contributors --jq 'length' 2>/dev/null

# Get open issues count
gh api repos/{owner}/{repo}/issues --jq 'length' 2>/dev/null

# Get recent releases
gh api repos/{owner}/{repo}/releases --jq '.[0:3] | .[] | {tag: .tag_name, date: .published_at}' 2>/dev/null

# Check for SECURITY.md
gh api repos/{owner}/{repo}/contents/SECURITY.md --jq '.name' 2>/dev/null || echo "NO SECURITY.md"
```

### Step 3: Risk Criteria

A dependency is **high-risk** if ANY of these apply:

| Risk Factor | Detection | Severity |
|-------------|-----------|----------|
| **Single maintainer** | `contributors <= 2` AND not org-backed | HIGH |
| **Anonymous maintainer** | GitHub profile has no real name, no company, no social links | HIGH |
| **Unmaintained** | No release or commit in >12 months | HIGH |
| **Archived/deprecated** | `archived: true` or README says "deprecated" | HIGH |
| **Low popularity** | Stars < 100 AND downloads < 1000/week | MEDIUM |
| **No security contact** | No SECURITY.md, no security email in README | MEDIUM |
| **Past CVEs** | >3 high/critical CVEs relative to popularity | MEDIUM |
| **High-risk features** | FFI, deserialization, code execution, native bindings | MEDIUM |
| **Typosquatting risk** | Name similar to popular package (Levenshtein distance <=2) | HIGH |
| **Unpinned version** | No lockfile or `>=` without upper bound | MEDIUM |

### Step 4: Report Template

```
Supply Chain Risk Assessment — {project}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Dependencies: {total} direct, {transitive} transitive
High-risk: {count}

HIGH-RISK DEPENDENCIES:
┌─────────────────┬──────────┬─────────────┬──────────────────────────┐
│ Package         │ Severity │ Risk Factor │ Suggested Alternative    │
├─────────────────┼──────────┼─────────────┼──────────────────────────┤
│ some-package    │ HIGH     │ 1 maintainer│ well-maintained-alt      │
│ old-lib         │ HIGH     │ Unmaintained│ new-lib (drop-in)        │
└─────────────────┴──────────┴─────────────┴──────────────────────────┘

KNOWN CVEs (from pip-audit / npm audit):
┌─────────────┬──────────┬──────────┬──────────────┐
│ Package     │ CVE      │ Severity │ Fix Version  │
├─────────────┼──────────┼──────────┼──────────────┤
│ package-x   │ CVE-XXX  │ CRITICAL │ >= 2.0.1     │
└─────────────┴──────────┴──────────┴──────────────┘

Executive Summary:
{1-3 sentences on overall supply chain health}

Recommendations:
1. {most critical action}
2. {second}
3. {third}
```

## Typosquatting Detection

```bash
# Python: check for known typosquat patterns
pip3 install -c "
known = ['requests', 'flask', 'django', 'numpy', 'pandas', 'boto3', 'cryptography']
# Check if any deps have Levenshtein distance <= 2 from known packages
# Flag: requets, flaskk, djang0, numpyy, etc.
" 2>/dev/null
```

## Transitive Dependency Depth

```bash
# Python: show dependency tree
pipdeptree --warn silence 2>/dev/null | head -60

# JavaScript: show dependency tree (direct only)
npm ls --depth=1 --json 2>/dev/null | head -60

# Flag: transitive depth > 5 levels = increased attack surface
```

## Lockfile Integrity

```bash
# Python: check if lockfile matches requirements
pip freeze 2>/dev/null > /tmp/vigil_frozen.txt
diff <(sort requirements.txt 2>/dev/null | grep -v '^#' | grep -v '^$') <(sort /tmp/vigil_frozen.txt) 2>/dev/null | head -20

# JavaScript: check lockfile sync
npm ls --json 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print('PROBLEMS:', len(d.get('problems',[])))" 2>/dev/null
```

## Advanced Patterns

| Pattern | Severity | Check |
|---------|----------|-------|
| Dependency with install scripts (`postinstall`) | HIGH | `grep -r 'postinstall\|preinstall' node_modules/*/package.json` |
| Binary dependencies (native compilation) | MEDIUM | Check for `.so`, `.dll`, `.dylib` in installed packages |
| Dependency from non-standard registry | HIGH | Check `.npmrc`, `pip.conf` for custom registries |
| Dependency with inline `eval` or `exec` | HIGH | Grep installed package source |
| Package.json with wide version ranges (`*`, `>=0`) | HIGH | Parse package.json ranges |
