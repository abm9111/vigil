# VIGIL Domain Detail: Infrastructure as Code

**Parent cluster:** infrastructure
**Loaded in:** siege mode, or --only infrastructure --deep

## Deep Checks

### Terraform State Security

```bash
# Check state backend configuration
grep -rn "backend\s*\"" terraform/ infra/ --include="*.tf" | head -10
grep -rn "\"local\"\|backend\s*{\s*}" terraform/ infra/ --include="*.tf"
# Local state = no locking, no encryption, accidental commit risk

# Verify remote state has encryption enabled
grep -rn "encrypt\s*=\s*true\|kms_key_id\|sse_algorithm" terraform/ infra/ --include="*.tf"
grep -A10 "backend.*s3" terraform/ infra/ --include="*.tf" | grep -c "encrypt"

# Check for state file in version control (critical: may contain secrets)
find . -name "*.tfstate" -o -name "*.tfstate.backup" 2>/dev/null
git ls-files | grep "\.tfstate"  # committed state files = secrets leaked

# State locking
grep -rn "dynamodb_table\|lock_table\|use_lockfile" terraform/ --include="*.tf" | head -5
```

### Hardcoded Values in IaC

```bash
# Hardcoded secrets / credentials
grep -rn "password\s*=\s*\"[^$]\|secret\s*=\s*\"[^$]\|api_key\s*=\s*\"" \
  terraform/ infra/ --include="*.tf" --include="*.tfvars"

# Hardcoded IPs (should use variables or data sources)
grep -rn '"[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}"' \
  terraform/ infra/ --include="*.tf" | grep -v "0.0.0.0\|127.0.0.1\|10\.\|172\.\|192\.168"

# Hardcoded AMI IDs (region-specific, drift over time)
grep -rn '"ami-[0-9a-f]\{8,17\}"' terraform/ --include="*.tf"
# Should use data source: data "aws_ami" ... { filter {...} }

# Hardcoded instance types (no flexibility for cost optimization)
grep -rn '"t2\.\|"t3\.\|"m5\.' terraform/ --include="*.tf" | grep -v "variable\|default"

# Check for .tfvars files with secrets committed
git ls-files | grep "\.tfvars\b" | xargs grep -l "password\|secret\|key\|token" 2>/dev/null
```

| Hardcoded Value | Risk | Fix |
|----------------|------|-----|
| Passwords/secrets | CRITICAL — leaked in git history | Use `var.` + vault/SSM |
| Public IPs | HIGH — breaks multi-region | Use CIDR variables |
| AMI IDs | MEDIUM — drift | `data "aws_ami"` source |
| Account IDs | MEDIUM — coupling | `data "aws_caller_identity"` |

### Drift Detection

```bash
# Terraform: detect infrastructure drift
terraform plan -detailed-exitcode -out=/tmp/tfplan
# Exit code 2 = changes detected (drift between state and reality)

# List resources with potential drift
terraform show -json /tmp/tfplan 2>/dev/null | jq '.resource_changes[] | select(.change.actions != ["no-op"]) | .address'

# Checkov for IaC policy violations (runs offline)
pip install checkov
checkov -d terraform/ --output cli --compact

# Infracost for cost drift
infracost diff --path terraform/ --format table 2>/dev/null | head -30
```

### Module Versioning

```bash
# Check all module sources for version pinning
grep -rn "source\s*=" terraform/ --include="*.tf" | grep -v "version\|ref=\|tag=" | head -20
grep -A3 'source\s*=' terraform/ --include="*.tf" | grep -v "version\s*=\|#" | head -30

# Modules without version pins = surprise breaking changes on next apply
grep -rn 'version\s*=\s*">=' terraform/ --include="*.tf"  # unpinned range (bad)
grep -rn 'version\s*=\s*"[0-9]' terraform/ --include="*.tf"  # pinned (good)

# Terraform provider version pinning
grep -B2 -A10 "required_providers" terraform/ --include="*.tf" | grep "version\s*=" | head -10
grep -rn '">= [0-9]\|"~> [0-9]' terraform/ --include="*.tf" | head -10
```

### Secret Management in IaC

```bash
# Check for plaintext secrets in variable defaults
grep -B5 "default\s*=" terraform/ --include="*.tf" \
  | grep -B5 "password\|secret\|key\|token\|credential" | head -30

# Verify secrets come from data sources (SSM, Vault, Secrets Manager)
grep -rn "data.*aws_ssm_parameter\|data.*aws_secretsmanager\|data.*vault_generic_secret" \
  terraform/ --include="*.tf" | wc -l

# Check environment variable usage for secrets (better than hardcoded)
grep -rn "TF_VAR_\|var\." terraform/ --include="*.tfvars" | head -20

# Ansible: check for plaintext secrets in playbooks/vars
grep -rn "password:\|secret:\|api_key:" ansible/ playbooks/ --include="*.yml" --include="*.yaml" \
  | grep -v "vault\|{{ \|lookup\|encrypted"

# Helm charts: check values files for secrets
grep -rn "password:\|secret:\|key:" helm/ charts/ --include="*.yaml" \
  | grep -v "secretRef\|valueFrom\|secretKeyRef" | head -20
```

### Resource Tagging Compliance

```bash
# Check for required tags on all resources
grep -rn "tags\s*=" terraform/ --include="*.tf" | wc -l
grep -rn "resource\s*\"" terraform/ --include="*.tf" | wc -l
# Resources without tags block = untagged resources

# Find resources missing mandatory tags
grep -rn "resource\s*\"aws_\|resource\s*\"azurerm_\|resource\s*\"google_" \
  terraform/ --include="*.tf" | wc -l
grep -rn "Environment\|Owner\|Project\|CostCenter\|Team" terraform/ --include="*.tf" | wc -l

# Run tflint for tag policy
tflint --enable-plugin=aws terraform/ 2>/dev/null | grep -i "tag\|label"

# OPA/Sentinel: policy as code for tags
# rego rule: deny if resource missing required_tags
```

### Cost Estimation

```bash
# Infracost: estimate monthly cost before apply
infracost breakdown --path terraform/ --format table 2>/dev/null | tail -20
infracost breakdown --path terraform/ --format json 2>/dev/null \
  | jq '.projects[].breakdown.totalMonthlyCost'

# Find expensive resource types
grep -rn "resource\s*\"aws_nat_gateway\|resource\s*\"aws_elasticsearch\|resource\s*\"aws_rds" \
  terraform/ --include="*.tf"  # NAT GW: ~$45/mo, ES: $$$, RDS multi-AZ: $$$

# Check for unnecessary resources left running
grep -rn "count\s*=\s*0\|enabled\s*=\s*false" terraform/ --include="*.tf" | head -10
grep -rn "lifecycle.*prevent_destroy" terraform/ --include="*.tf" | head -10  # protected resources
```

### Blast Radius Analysis

```bash
# Find resources that affect the most other resources
grep -rn "depends_on\|data\." terraform/ --include="*.tf" | wc -l

# Identify shared infrastructure (changes affect multiple services)
grep -rn "shared\|common\|base\|core" terraform/ --include="*.tf" | head -20
grep -rn "vpc_id\|subnet_ids\|security_group_ids" terraform/ --include="*.tf" | wc -l
# VPCs, security groups, IAM roles = high blast radius

# Find resources without deletion protection
grep -rn "deletion_protection\s*=\s*false\|skip_final_snapshot\s*=\s*true\|force_destroy\s*=\s*true" \
  terraform/ --include="*.tf"
# These resources can be permanently destroyed with a single `terraform destroy`

# Check for missing prevent_destroy on critical resources
grep -rn "aws_db_instance\|aws_s3_bucket\|aws_elasticsearch_domain" terraform/ --include="*.tf" \
  | wc -l
grep -rn "prevent_destroy\s*=\s*true" terraform/ --include="*.tf" | wc -l
# Critical resource count >> prevent_destroy count = accidental deletion risk
```

## Advanced Patterns

### IaC Security Scorecard

| Check | Safe Signal | Danger Signal |
|-------|------------|---------------|
| State backend | S3+DynamoDB, encrypted | Local file or committed |
| Secrets | SSM/Vault data source | Hardcoded in .tf/.tfvars |
| Module versions | Pinned exact `"1.2.3"` | Unpinned or `>=` |
| Provider versions | Pinned `"~> 5.0"` | No version constraint |
| Resource tagging | All resources tagged | Missing required tags |
| Deletion protection | `prevent_destroy = true` | `force_destroy = true` |
| Drift detection | Regular `plan` in CI | Manual apply only |

### CI/CD Integration

```bash
# Verify IaC is validated in CI before merge
cat .github/workflows/*.yml .gitlab-ci.yml | grep -E "terraform plan|checkov|tfsec|infracost" | head -10

# tfsec for security scanning
tfsec terraform/ --format=lovely 2>/dev/null | grep -E "CRITICAL|HIGH" | head -20
```
