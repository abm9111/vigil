# VIGIL Domain Detail: Supply Chain Security

**Parent cluster:** supply-chain
**Loaded in:** siege mode, or --only supply-chain --deep

## Deep Checks

### npm/pip Package Publisher Verification

```bash
# npm — check package publisher and verify against known owner
npm info <package> --json 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
print('Name:', data.get('name'))
print('Latest:', data.get('dist-tags',{}).get('latest'))
print('Maintainers:', data.get('maintainers'))
print('Homepage:', data.get('homepage'))
print('Repository:', data.get('repository',{}).get('url','') if isinstance(data.get('repository'),dict) else data.get('repository',''))
"

# Check if package was recently transferred (ownership change = supply chain risk)
npm info <package> time --json 2>/dev/null | python3 -c "
import json, sys
from datetime import datetime, timedelta
data = json.load(sys.stdin)
if 'modified' in data:
    modified = datetime.fromisoformat(data['modified'].replace('Z','+00:00'))
    created = datetime.fromisoformat(data['created'].replace('Z','+00:00'))
    age = (datetime.now(modified.tzinfo) - modified).days
    print(f'Last modified: {modified.date()} ({age} days ago)')
    if age < 30: print('WARNING: Package modified in last 30 days')
"

# PyPI — verify package provenance
python3 -c "
import urllib.request, json
pkg = 'requests'  # replace with actual package
url = f'https://pypi.org/pypi/{pkg}/json'
with urllib.request.urlopen(url) as r:
    data = json.load(r)
    info = data['info']
    print('Author:', info.get('author'))
    print('Home:', info.get('home_page'))
    print('License:', info.get('license'))
    print('Requires:', info.get('requires_python'))
" 2>/dev/null
```

### Git Hook Integrity

```bash
# Check .git/hooks for unexpected modifications (hook injection)
ls -la .git/hooks/ 2>/dev/null
find .git/hooks -type f -executable 2>/dev/null | while read hook; do
    echo "=== $hook ==="
    head -5 "$hook"
    echo "---"
done

# Check for outbound network calls in hooks (data exfiltration)
grep -rn --include="*" \
  -E "(curl|wget|nc|ncat|python.*requests|node.*https)" .git/hooks/ 2>/dev/null

# Verify hooks match committed .githooks/ (if exists)
if [ -d .githooks ]; then
    diff -r .githooks .git/hooks/ 2>/dev/null | grep -v ".sample"
fi

# Check husky / lint-staged hook configs for tampering
cat .husky/pre-commit 2>/dev/null
cat .husky/pre-push 2>/dev/null
grep -r "exec\|eval\|curl\|wget" .husky/ 2>/dev/null
```

### CI Artifact Signing & Integrity

```bash
# GitHub Actions — check for artifact upload/download without hash verification
grep -rn --include="*.yml" --include="*.yaml" \
  -E "actions/upload-artifact|actions/download-artifact" .github/ 2>/dev/null | \
  head -20

# Check for sigstore/cosign usage (gold standard)
grep -rn --include="*.yml" --include="*.yaml" \
  -E "cosign|sigstore|slsa-framework" .github/ 2>/dev/null

# Docker image signing check
grep -rn --include="*.yml" --include="*.yaml" \
  -E "DOCKER_CONTENT_TRUST|docker trust" .github/ 2>/dev/null || \
  echo "WARNING: No Docker Content Trust enforcement found in CI"

# npm provenance (Node.js 2FA publish)
grep -rn --include="*.yml" --include="*.yaml" \
  -E "npm publish.*--provenance|provenance: true" .github/ 2>/dev/null
```

### Container Base Image Provenance

```bash
# Find all FROM statements and check if using digests (not mutable tags)
grep -rn --include="Dockerfile*" -E "^FROM\s+" . 2>/dev/null | \
  grep -v "@sha256:" | \
  head -20  # These use mutable tags — bad for reproducibility

# Check for latest tag (worst for supply chain)
grep -rn --include="Dockerfile*" -E "^FROM\s+[^:@]+:latest\b|^FROM\s+[^:@]+$" . 2>/dev/null

# Verify base image is from trusted registry (not random Docker Hub)
grep -rn --include="Dockerfile*" -E "^FROM\s+" . 2>/dev/null | \
  grep -v -E "gcr\.io|ghcr\.io|ecr\.aws|docker\.io/library|python:|node:|ubuntu:|alpine:" | \
  head -20

# Trivy scan base images for CVEs
for img in $(grep -rh "^FROM" . --include="Dockerfile*" 2>/dev/null | awk '{print $2}' | sort -u); do
    echo "Scanning: $img"
    trivy image --severity HIGH,CRITICAL --no-progress "$img" 2>/dev/null | tail -5
done
```

### SBOM Generation

```bash
# Generate CycloneDX SBOM for Python project
pip install cyclonedx-bom 2>/dev/null
cyclonedx-py environment --output sbom.json 2>/dev/null && \
  echo "SBOM generated: sbom.json" || echo "cyclonedx-py not available"

# Syft — universal SBOM generator (Docker, npm, pip, etc.)
syft . -o cyclonedx-json=sbom-cyclonedx.json 2>/dev/null || \
  syft dir:. 2>/dev/null | head -30

# Node.js — generate package-based SBOM
npx @cyclonedx/cyclonedx-npm --output-file sbom-node.json 2>/dev/null

# Docker image SBOM
docker sbom <image:tag> 2>/dev/null || \
  syft <image:tag> -o cyclonedx-json 2>/dev/null
```

### Reproducible Builds Check

```bash
# Python — check if setup.py/pyproject.toml pins all build tools
grep -E "setuptools|wheel|pip" requirements.txt pyproject.toml setup.cfg 2>/dev/null | head -10

# Node.js — verify package-lock.json lockfileVersion
node -e "
const lock = require('./package-lock.json');
console.log('lockfileVersion:', lock.lockfileVersion);
if (lock.lockfileVersion < 2) console.log('WARNING: Old lockfile format, upgrade npm');
" 2>/dev/null

# Check for .npmrc / pip.conf pointing to non-standard registries
cat .npmrc 2>/dev/null | grep -E "registry\s*=" | grep -v "registry.npmjs.org"
cat pip.conf 2>/dev/null | grep "index-url\|extra-index-url" | grep -v "pypi.org"
find . -name ".npmrc" -o -name "pip.conf" 2>/dev/null | grep -v node_modules
```

### GitHub Actions Pinning Analysis

```bash
# Find actions not pinned to full SHA (mutable tag = supply chain risk)
grep -rn --include="*.yml" --include="*.yaml" \
  -E "uses:\s+[a-zA-Z0-9/_-]+@(?!v?[0-9a-f]{40})" .github/ 2>/dev/null | \
  grep -v "uses:.*@v[0-9]"  # v tags are still mutable but common

# Ideally pinned to full SHA: uses: actions/checkout@a81bbbf8298c0fa03ea29cdc473d45769f953675
grep -rn --include="*.yml" --include="*.yaml" \
  -E "uses:\s+[a-zA-Z0-9/_-]+@[a-f0-9]{40}" .github/ 2>/dev/null | wc -l

# Check for third-party actions (higher risk than github-owned)
grep -rn --include="*.yml" --include="*.yaml" \
  -E "uses:\s+(?!actions/|github/|docker/)" .github/ 2>/dev/null | head -20

# Detect use of pull_request_target (known dangerous trigger)
grep -rn --include="*.yml" --include="*.yaml" \
  "pull_request_target" .github/ 2>/dev/null
```

## Advanced Patterns

| Risk | Severity | Signal | Mitigation |
|---|---|---|---|
| Mutable image tag `:latest` | HIGH | `FROM python:latest` in Dockerfile | Pin to `@sha256:digest` |
| Third-party GH Action not SHA-pinned | HIGH | `uses: some-org/action@v1` | Pin to commit SHA |
| `pull_request_target` with checkout | CRITICAL | Trigger + `actions/checkout` of PR code | Use `pull_request` or sandbox |
| Non-standard pip registry | HIGH | `index-url` not pypi.org | Audit + allowlist only |
| No SBOM generated | MEDIUM | No syft/cyclonedx in CI | Add SBOM generation step |
| Git hook exfiltration | CRITICAL | `curl` in `.git/hooks/` | Audit all hooks, use commit signing |
| Artifact without integrity check | HIGH | Download without hash verify | Use `sha256sum` verification step |
| Package ownership change | HIGH | npm info shows recent transfer | Pin to specific version, audit diff |
| No Docker Content Trust | MEDIUM | `DOCKER_CONTENT_TRUST` not set | Enable or use cosign |
| No cosign/sigstore signing | MEDIUM | Published artifacts unsigned | Add `cosign sign` to release pipeline |
