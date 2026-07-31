# VIGIL Domain Detail: CI/CD Pipeline Security

**Parent cluster:** ci
**Loaded in:** siege mode, or --only ci --deep

## Deep Checks

### Pipeline Privilege Escalation

```bash
# GitHub Actions — jobs with excessive permissions
grep -rn --include="*.yml" --include="*.yaml" \
  -E "permissions:\s*write-all|permissions:\s*\n\s+contents:\s*write" \
  .github/workflows/ 2>/dev/null

# Check for admin token usage
grep -rn --include="*.yml" --include="*.yaml" \
  -E "GITHUB_TOKEN|GH_TOKEN|PAT_TOKEN" .github/workflows/ 2>/dev/null | \
  grep -E "secrets\.\w+" | head -20

# Overprivileged GITHUB_TOKEN (write on all by default pre-2023)
grep -rn --include="*.yml" --include="*.yaml" \
  -E "^permissions:" .github/workflows/ 2>/dev/null || \
  echo "WARNING: No top-level permissions block — workflows use default (broad) permissions"

# Check if workflows use environment protection rules (production gates)
grep -rn --include="*.yml" --include="*.yaml" \
  -E "environment:\s*(production|prod|release)" .github/workflows/ 2>/dev/null

# GitLab CI — protected variables not used for sensitive jobs
grep -rn --include="*.gitlab-ci.yml" \
  -E "only:\s*\n\s+- main|\- master" . 2>/dev/null
```

### Secret Exfiltration Vectors

```bash
# Outbound curl/wget in CI steps (data exfiltration signal)
grep -rn --include="*.yml" --include="*.yaml" \
  -E "run:.*curl\s+http://|run:.*wget\s+http://" .github/workflows/ 2>/dev/null

# Secrets referenced in echo/print (accidental logging)
grep -rn --include="*.yml" --include="*.yaml" \
  -E "echo.*\$\{\{.*secrets\.|print.*\$\{\{.*secrets\." .github/workflows/ 2>/dev/null

# Secrets passed as env vars to untrusted scripts
grep -rn --include="*.yml" --include="*.yaml" \
  -B 5 "run:.*bash\|run:.*sh\|run:.*python" .github/workflows/ 2>/dev/null | \
  grep -A 2 "secrets\." | head -20

# ACTIONS_STEP_DEBUG leaking all secrets to log
grep -rn --include="*.yml" --include="*.yaml" \
  -E "ACTIONS_STEP_DEBUG:\s*true|ACTIONS_RUNNER_DEBUG:\s*true" .github/workflows/ 2>/dev/null
```

### Artifact Poisoning

```bash
# Download artifact without integrity check (sha256 verification missing)
grep -rn --include="*.yml" --include="*.yaml" \
  -A 5 "actions/download-artifact" .github/workflows/ 2>/dev/null | \
  grep -v "sha256\|checksum\|hash" | head -20

# Release artifacts published without signing
grep -rn --include="*.yml" --include="*.yaml" \
  -E "actions/upload-release-asset|softprops/action-gh-release" \
  .github/workflows/ 2>/dev/null | \
  xargs grep -L "cosign\|sigstore\|sha256" 2>/dev/null

# npm publish without 2FA / provenance
grep -rn --include="*.yml" --include="*.yaml" \
  -E "npm publish" .github/workflows/ 2>/dev/null | \
  grep -v "\-\-provenance\|NPM_OTP\|NPM_TOKEN.*otp"

# Docker push without content trust
grep -rn --include="*.yml" --include="*.yaml" \
  -E "docker push" .github/workflows/ 2>/dev/null | \
  grep -v "DOCKER_CONTENT_TRUST\|cosign sign"
```

### GitHub Actions Expression Injection (Critical Class)

```bash
# Untrusted input in run: steps — classic injection vector
# ${{ github.event.pull_request.title }} in run: = command injection
grep -rn --include="*.yml" --include="*.yaml" \
  -E "run:.*\$\{\{\s*github\.event\.(pull_request\.(title|body|head\.ref)|issue\.(title|body)|comment\.body|review\.body)" \
  .github/workflows/ 2>/dev/null

# head.ref / head.sha used in run commands (PR branch name injection)
grep -rn --include="*.yml" --include="*.yaml" \
  -E "\$\{\{\s*github\.head_ref\s*\}\}|\$\{\{\s*github\.event\.pull_request\.head\.ref" \
  .github/workflows/ 2>/dev/null | grep "run:" -A 2 2>/dev/null

# Dynamic env from untrusted event data
grep -rn --include="*.yml" --include="*.yaml" \
  -E "env:.*\$\{\{.*github\.event\." .github/workflows/ 2>/dev/null

# Safe pattern: assign to env var first, then use $VAR (not ${{ }})
# grep -rn -E "env:\n\s+\w+: \$\{\{.*\}\}" — OK if used as $VAR not ${{ }} in run
```

### Self-Hosted Runner Risks

```bash
# Workflows that run on self-hosted runners
grep -rn --include="*.yml" --include="*.yaml" \
  -E "runs-on:\s*(self-hosted|\[self-hosted)" .github/workflows/ 2>/dev/null

# Self-hosted + pull_request_target = CRITICAL (untrusted code runs on your infra)
grep -rn --include="*.yml" --include="*.yaml" \
  "pull_request_target" .github/workflows/ 2>/dev/null | \
  xargs grep -l "self-hosted" 2>/dev/null && \
  echo "CRITICAL: self-hosted runner + pull_request_target = RCE on your infra"

# Check if runner cleanup is enabled (shared state between runs)
grep -rn --include="*.yml" --include="*.yaml" \
  -E "ephemeral|cleanup|--once" .github/workflows/ 2>/dev/null || \
  echo "INFO: No ephemeral runner config found"
```

### Approval Bypass Patterns

```bash
# Environments without required reviewers (direct prod deploy)
grep -rn --include="*.yml" --include="*.yaml" \
  -E "environment:\s*\n\s+name:\s*(production|prod|release)\s*\n" \
  .github/workflows/ 2>/dev/null | \
  grep -v "url\|protection"  # No review gates

# Branch protection bypass via workflow_dispatch
grep -rn --include="*.yml" --include="*.yaml" \
  "workflow_dispatch" .github/workflows/ 2>/dev/null | \
  xargs grep -l "deploy\|release\|prod" 2>/dev/null

# GitLab — when: always on deployment jobs (bypasses failure gates)
grep -rn --include="*.gitlab-ci.yml" \
  -E "when:\s*always" . 2>/dev/null | head -10
```

### Deployment Credential Exposure

```bash
# AWS credentials in CI (check for OIDC vs static keys)
grep -rn --include="*.yml" --include="*.yaml" \
  -E "AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY" .github/workflows/ 2>/dev/null | \
  grep -v "aws-actions/configure-aws-credentials"  # Static keys bad; OIDC good

# OIDC (recommended pattern) — check if configured
grep -rn --include="*.yml" --include="*.yaml" \
  -E "id-token: write|aws-actions/configure-aws-credentials.*role-to-assume" \
  .github/workflows/ 2>/dev/null

# Kubeconfig / SSH keys stored as secrets (flat file risk)
grep -rn --include="*.yml" --include="*.yaml" \
  -E "secrets\.KUBECONFIG|secrets\.SSH_PRIVATE_KEY|secrets\.DEPLOY_KEY" \
  .github/workflows/ 2>/dev/null

# Terraform state with sensitive outputs in CI logs
grep -rn --include="*.yml" --include="*.yaml" \
  -E "terraform output\b(?! -json)" .github/workflows/ 2>/dev/null
```

## Advanced Patterns

| Vulnerability | Severity | Signal | Fix |
|---|---|---|---|
| Expression injection in `run:` | CRITICAL | `${{ github.event.*.title }}` in run | Set as env var, use `$ENV_VAR` in shell |
| `pull_request_target` + checkout | CRITICAL | Both in same job | Use `pull_request` or isolate secrets |
| Self-hosted + `pull_request_target` | CRITICAL | Untrusted code on your runner | Only use GitHub-hosted for PRs |
| Static AWS keys in secrets | HIGH | `AWS_ACCESS_KEY_ID` in workflow | Switch to OIDC `role-to-assume` |
| No permissions block | HIGH | Missing `permissions:` key | Add minimal `permissions: contents: read` |
| Artifact no integrity check | HIGH | Download without sha256 verify | Add `sha256sum -c` step |
| Secrets echoed in logs | HIGH | `echo ${{ secrets.X }}` | Never echo secrets directly |
| `ACTIONS_STEP_DEBUG: true` | HIGH | Debug mode in production | Remove from non-debug workflows |
| Third-party action not SHA-pinned | HIGH | `uses: foo/bar@v1` | Pin to `@sha256:...` commit hash |
| No env protection rules | MEDIUM | `environment: production` no reviewers | Add required reviewers in repo settings |
| npm publish no provenance | MEDIUM | `npm publish` without `--provenance` | Add `--provenance` flag |
| Workflow dispatch to prod | MEDIUM | Manual trigger can deploy to prod | Add environment protection gate |
